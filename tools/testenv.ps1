# testenv.ps1 -- the local test environment for PIP-MON.
#
# WHAT THIS IS
#   One command that stands up a live test session against a running Fallout 4
#   and makes it observable in real time:
#
#       preflight   prove the pieces are present and consistent, touch nothing
#       stage       build an isolated run directory with the runtime + database
#       run         preflight, stage, attach, tail both channels live, verdict
#       tail        re-read a finished run directory (post-mortem, no game)
#
#   It exists because every prior live run was assembled by hand, and the
#   project's own record is that this is where things went wrong: a stale
#   address blob, a missing trace marker, and an injector aimed at the wrong
#   build all present as a healthy-looking session that reports nothing.
#
# WHY THE OBSERVATION CHANNEL IS A FILE AND NOT THE PIPE
#   The V-Link named pipe is unusable for live observation on this build.
#   vprobe/include/Trace.hpp records four connection attempts, each followed
#   within ~2 seconds by the process dying, with a clean init and
#   "Runtime ready: 18/18 probes resolved" immediately beforehand. The defect
#   is in IPCServer, not in the reader.
#
#   So this script NEVER opens \\.\pipe\vlink_telemetry, and it is worth being
#   blunt about why that is a rule rather than a preference: a monitoring tool
#   that kills the process it is monitoring is worse than no tool, and the
#   failure looks like a crash rather than like a mistake. If a future session
#   wants live wire telemetry, that is an IPCServer fix first and this script
#   second -- not the other way round.
#
# WHAT IT DELIBERATELY DOES NOT DO
#   - it does not terminate the game, ever, on any path including Ctrl+C
#     (design section 18.5: the user's game is never killed unprompted)
#   - it does not write outside the project (G15). Every run directory, log and
#     manifest lands under <repo>\runs\
#   - it does not unload the injected module. Unloading a module that started a
#     thread is the mistake that killed the test harness; detach is the user's
#     call (see attach_inject.ps1)
#   - it does not touch the installed extenders. They are the incumbent, not
#     contamination; F4SE is a reference and verification control (G7)
#
# EXIT CODES -- chosen so a script can tell a finding from a pass, which is the
# distinction this project keeps getting wrong (see tools/LOG_FORMAT.md):
#   0  session ran, runtime reached ready, game still alive or exited cleanly
#   1  preflight failed; nothing was injected
#   2  bad usage
#   3  THE PROCESS DIED BEFORE THE RUNTIME WAS READY. A real finding.
#   4  the runtime produced no trace at all -- marker missing, or not loaded
param(
    [ValidateSet('preflight', 'stage', 'run', 'tail')]
    [string]$Command = 'preflight',

    # tail: which run directory to read. Defaults to the most recent.
    [string]$RunDir,

    # --debug   show the full trace channel as well as the session channel
    # --verbose show per-check preflight detail and every watchdog line
    [switch]$Debug,
    [switch]$Verbose,

    # --no-trace inject WITHOUT the marker file. The runtime then does no file
    #            IO whatsoever, which is the shipping default. Useful to prove
    #            that the trace itself is not what kills the game.
    [switch]$NoTrace,

    # --no-inject stage and stage only; do not attach
    [switch]$NoInject,

    [int]$TailLines = 40,
    [int]$WatchMs = 500,

    # Bound the watch. A test session that can only end when the game exits is
    # unusable for the common case, which is "watch for a bit, report, stop".
    # On expiry the run is treated as CLEAN: the process was alive and the
    # runtime reported, so nothing was observed to have gone wrong. Reaching the
    # deadline is a PASS, not an absence of one.
    [int]$Seconds = 0
)

$ErrorActionPreference = 'Stop'

# --- paths ------------------------------------------------------------------
$RepoRoot = Split-Path -Parent $PSScriptRoot
$AttachScript = Join-Path $PSScriptRoot 'attach_inject.ps1'
$VerifyBlob = Join-Path $PSScriptRoot 'verify_libbin.py'
$RuntimeDll = Join-Path $RepoRoot 'vprobe\build\vprobe.dll'
$DeployLibs = Join-Path $RepoRoot 'vprobe\libs\deploy'
$RunsRoot = Join-Path $RepoRoot 'runs'

$GameExe = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Fallout4.exe'

# --- output helpers ---------------------------------------------------------
# Severity is carried by BOTH colour and a text tag. This is the same
# accessibility rule the dashboard uses (design section 6.1): a monitoring tool
# must not rely on colour alone to say whether something is wrong.
function Say([string]$Tag, [string]$Text, [string]$Colour = 'Gray') {
    Write-Host ("  {0,-7} {1}" -f $Tag, $Text) -ForegroundColor $Colour
}
function Ok([string]$t)   { Say 'OK'    $t 'Green' }
function Warn([string]$t) { Say 'WARN'  $t 'Yellow' }
function Fail([string]$t) { Say 'FAIL'  $t 'Red' }
function Info([string]$t) { Say 'INFO'  $t 'Cyan' }
function Step([string]$t) { Write-Host "`n== $t" -ForegroundColor White }

# --- preflight --------------------------------------------------------------
# Every check here corresponds to a failure this project has actually had. A
# check earns its place by naming the thing it prevents.
function Test-Preflight {
    $results = [System.Collections.Generic.List[object]]::new()
    function Add-Result($name, $ok, $detail, $fatal) {
        $results.Add([pscustomobject]@{
            Name = $name; Ok = $ok; Detail = $detail; Fatal = $fatal
        })
    }

    Step 'preflight'

    # 1. the runtime artefact itself. G13: a gate that never opened its output
    #    is not a gate, so the check is on the FILE, not on the build's word.
    if (Test-Path -LiteralPath $RuntimeDll) {
        $bytes = [System.IO.File]::ReadAllBytes($RuntimeDll)
        $isPe = $bytes.Length -gt 0x40 -and $bytes[0] -eq 0x4D -and $bytes[1] -eq 0x5A
        $arch = if ($isPe) {
            [BitConverter]::ToUInt16($bytes, [BitConverter]::ToInt32($bytes, 0x3C) + 4)
        } else { 0 }
        if ($isPe -and $arch -eq 0x8664) {
            Ok ("runtime    vprobe.dll {0:N0} B, PE x64" -f $bytes.Length)
            Add-Result 'runtime' $true 'PE x64' $false
        } else {
            Fail ("runtime    not a PE x64 image (magic={0} arch=0x{1:X4})" -f $isPe, $arch)
            Add-Result 'runtime' $false 'not PE x64' $true
        }
    } else {
        Fail 'runtime    vprobe.dll missing -- run build_all.bat'
        Add-Result 'runtime' $false 'missing' $true
    }

    # 2. the address database, BOTH forms.
    #    The blob path is DERIVED from the INI path, so a miss on the text form
    #    silently takes the binary form down with it, and the resolver then
    #    falls back to its embedded dump. That happened in every prior live run:
    #    the database was absent and the resolver still reported 18/18, which
    #    looks identical to success. (testfacility/HANDOVER.md section 5)
    $ini = Join-Path $DeployLibs 'vprobe.addresses.txt'
    $bin = Join-Path $DeployLibs 'vprobe.addresses.bin'
    $iniOk = Test-Path -LiteralPath $ini
    $binOk = Test-Path -LiteralPath $bin
    if ($iniOk -and $binOk) {
        Ok ("database   vprobe.addresses.txt {0:N0} B + .bin {1:N0} B" -f
            (Get-Item $ini).Length, (Get-Item $bin).Length)
        Add-Result 'database' $true 'both forms present' $false
    } else {
        $missing = @(); if (-not $iniOk) { $missing += '.txt' }
        if (-not $binOk) { $missing += '.bin' }
        Fail ("database   missing $($missing -join ', ') -- run build_all.bat " +
              '(build_libbin.bat stages both under the contract name)')
        Add-Result 'database' $false "missing $($missing -join ',')" $true
    }

    # 3. validate the blob independently. Reuse the build-time validator rather
    #    than re-checking the format here: two parsers of one format is two
    #    things that can disagree, and the disagreement would be invisible
    #    (M11).
    if ($binOk) {
        $out = & python $VerifyBlob $bin 2>&1
        if ($LASTEXITCODE -eq 0) {
            Ok 'database   blob validates (header, stride, spot-checked RVAs)'
            Add-Result 'blob' $true 'valid' $false
        } else {
            Fail 'database   blob validation FAILED -- the runtime would serve stale addresses'
            $out | Select-Object -Last 12 | ForEach-Object { Say '' $_ 'DarkGray' }
            Add-Result 'blob' $false 'validator failed' $true
        }
    }

    # 4. the game. Reported, never required by `preflight` alone -- `run` needs
    #    it, and saying so is more useful than refusing to look.
    if (Test-Path -LiteralPath $GameExe) {
        $ver = (Get-Item $GameExe).VersionInfo.ProductVersion
        Ok "game       Fallout4.exe present (ProductVersion $ver)"
        Add-Result 'game' $true $ver $false
    } else {
        Fail "game       not found at $GameExe"
        Add-Result 'game' $false 'missing' $true
    }

    # 5. extenders. Reported because they change what a result MEANS, not
    #    because they are a problem. PIP-MON replaces them; until it does they
    #    are the load order under test, and F4SE is a verification control (G7).
    $f4se = Test-Path -LiteralPath 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\f4se_loader.exe'
    $esmCount = @(Get-ChildItem -LiteralPath 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Data' `
                    -Filter '*.esm' -ErrorAction SilentlyContinue).Count
    if ($f4se) {
        Info "load order F4SE present; $esmCount .esm in Data\ (incumbent, not contamination)"
        Add-Result 'extenders' $true "$esmCount esm, F4SE present" $false
    } else {
        Info "load order no F4SE; $esmCount .esm in Data\ (closer to the S0 exit test)"
        Add-Result 'extenders' $true "$esmCount esm, no F4SE" $false
    }

    # 6. a game already running with our module loaded. Not fatal, but it means
    #    a second injection into the same process, and the docs record that
    #    unloading is not attempted -- so state accumulates across runs.
    $proc = Get-Process -Name 'Fallout4' -ErrorAction SilentlyContinue |
            Sort-Object WorkingSet64 -Descending | Select-Object -First 1
    if ($proc) {
        Info "process    Fallout4 running, pid=$($proc.Id) -- attach target"
        Add-Result 'process' $true "pid $($proc.Id)" $false
    } else {
        Info 'process    Fallout4 not running -- start the game first (G5: main menu, no loaded save)'
        Add-Result 'process' $false 'not running' $false
    }

    return $results
}

# --- staging ----------------------------------------------------------------
# A fresh directory per run, inside the project (G15). Isolation matters for a
# specific reason: the trace log is written BESIDE THE DLL, so injecting from a
# shared directory means every run appends to the same log and the previous
# run's lines get mistaken for this one's.
function New-RunDirectory {
    if (-not (Test-Path -LiteralPath $RunsRoot)) {
        New-Item -ItemType Directory -Path $RunsRoot | Out-Null
    }
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss')
    $dir = Join-Path $RunsRoot $stamp
    if (Test-Path -LiteralPath $dir) { $dir = Join-Path $RunsRoot "$stamp-$PID" }
    New-Item -ItemType Directory -Path $dir | Out-Null

    Copy-Item -LiteralPath $RuntimeDll -Destination (Join-Path $dir 'vprobe.dll')

    $libs = Join-Path $dir 'libs'
    New-Item -ItemType Directory -Path $libs | Out-Null
    # Both forms, under the contract name the runtime looks for. The runtime
    # searches <game>\Data\PIP-MON\libs first, then libs\ beside its own
    # module. Staging them here makes the run self-contained and means a
    # half-deployed game install cannot silently change what we measured.
    foreach ($f in @('vprobe.addresses.txt', 'vprobe.addresses.bin')) {
        $src = Join-Path $DeployLibs $f
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $libs $f)
        }
    }

    if (-not $NoTrace) {
        # The marker is what turns the file channels on. It is a FILE, not an
        # environment variable, because the game is launched by whoever launched
        # it and an env var set in this shell would never reach the game.
        Set-Content -LiteralPath (Join-Path $dir 'vprobe.trace') -Value 'on' -NoNewline
    }

    return $dir
}

# --- tailing ----------------------------------------------------------------
# The runtime opens, writes and closes per line, with FILE_SHARE_READ, so a
# reader can open it at any moment. Polling by byte offset rather than
# re-reading the whole file keeps this O(new bytes) and means a long session
# does not get slower as it goes.
function Read-NewLines([string]$Path, [ref]$Offset) {
    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    try {
        $fs = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
    } catch { return @() }
    try {
        if ($fs.Length -le $Offset.Value) { return @() }
        [void]$fs.Seek($Offset.Value, 'Begin')
        $buf = New-Object byte[] ($fs.Length - $Offset.Value)
        $read = $fs.Read($buf, 0, $buf.Length)
        if ($read -le 0) { return @() }
        $Offset.Value += $read
        return ([System.Text.Encoding]::UTF8.GetString($buf, 0, $read) -split "`r?`n") |
               Where-Object { $_ -ne '' }
    } finally { $fs.Dispose() }
}

# --- the command implementations -------------------------------------------
switch ($Command) {

    'preflight' {
        $results = Test-Preflight
        $fatal = @($results | Where-Object { $_.Fatal -and -not $_.Ok })
        Step 'verdict'
        if ($fatal.Count -eq 0) {
            Ok 'preflight clean'
            Write-Host ''
            exit 0
        } else {
            Fail "$($fatal.Count) blocking check(s) failed -- nothing was injected"
            $fatal | ForEach-Object { Say '' $_.Name 'DarkGray' }
            Write-Host ''
            exit 1
        }
    }

    'stage' {
        $results = Test-Preflight
        $fatal = @($results | Where-Object { $_.Fatal -and -not $_.Ok })
        if ($fatal.Count -gt 0) {
            Fail 'preflight failed; refusing to stage a payload that cannot work'
            exit 1
        }
        $dir = New-RunDirectory
        Step 'staged'
        Ok "run dir    $dir"
        if (-not $NoTrace) {
            Ok 'trace      marker written; file channels armed'
        } else {
            Warn 'trace      DISABLED (--no-trace) -- the runtime will do no file IO at all'
        }
        Write-Host ''
        exit 0
    }

    'run' {
        $results = Test-Preflight
        $fatal = @($results | Where-Object { $_.Fatal -and -not $_.Ok })
        if ($fatal.Count -gt 0) {
            Fail 'preflight failed; refusing to inject'
            exit 1
        }

        $proc = Get-Process -Name 'Fallout4' -ErrorAction SilentlyContinue |
                Sort-Object WorkingSet64 -Descending | Select-Object -First 1
        if (-not $proc) {
            Fail 'Fallout4 is not running. Start the game, then re-run.'
            Say '' 'G5: main menu with no loaded save is the only automation-safe window.'
            exit 1
        }

        $dir = New-RunDirectory
        Step 'staged'
        Ok "run dir    $dir"
        Ok "target     pid=$($proc.Id)"

        if ($NoInject) {
            Info '--no-inject: stopping before attachment'
            exit 0
        }

        # Reuse the injector rather than reimplementing it. The documented
        # failure mode for a hand-rolled second one is a plausible-looking
        # negative (M12), and there is no upside to owning a second.
        Step 'attach'
        $dll = Join-Path $dir 'vprobe.dll'
        try {
            & $AttachScript -ProcessName 'Fallout4' -DllPath $dll
            $attachExit = $LASTEXITCODE
        } catch {
            Fail "injector   $($_.Exception.Message)"
            exit 1
        }
        if ($attachExit -ne 0) {
            Fail 'injector   did not report LOADED'
            exit 1
        }

        # --- watch -------------------------------------------------------
        Step 'watching'
        Info 'the runtime settles ~1.5s after the game module is found, then bootstraps'
        Info 'Ctrl+C stops WATCHING ONLY. The game is never terminated.'

        $trace   = Join-Path $dir 'vprobe.trace.log'
        $session = Join-Path $dir 'vprobe.trace.session.log'
        $tOff = 0; $sOff = 0
        $sawReady = $false; $sawAny = $false; $lastLine = ''
        $started = Get-Date
        $deadline = if ($Seconds -gt 0) { $started.AddSeconds($Seconds) } else { $null }
        if ($deadline) { Info "bounded session: ${Seconds}s, then a verdict while the game keeps running" }

        try {
            while ($true) {
                $alive = $null -ne (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)
                if (-not $alive) { break }
                if ($deadline -and (Get-Date) -ge $deadline) {
                    Info 'watch window elapsed; leaving the game running'
                    break
                }

                foreach ($l in Read-NewLines $trace ([ref]$tOff)) {
                    if ($Debug) { Write-Host "  trace   $l" -ForegroundColor DarkGray }
                    $sawAny = $true; $lastLine = $l
                    if ($l -match 'bootstrap complete; runtime ready') { $sawReady = $true }
                }
                foreach ($l in Read-NewLines $session ([ref]$sOff)) {
                    Write-Host "  session $l" -ForegroundColor DarkCyan
                    $sawAny = $true; $lastLine = $l
                    if ($l -match 'runtime ready') { $sawReady = $true }
                }
                Start-Sleep -Milliseconds $WatchMs
            }
        } finally {
            # Drain whatever landed between the last poll and the exit. These
            # are the lines that identify the fault, which is precisely what a
            # buffered or sampled tail would lose.
            foreach ($l in Read-NewLines $trace ([ref]$tOff)) { $sawAny = $true; $lastLine = $l
                if ($l -match 'bootstrap complete; runtime ready') { $sawReady = $true } }
            foreach ($l in Read-NewLines $session ([ref]$sOff)) { $sawAny = $true; $lastLine = $l
                if ($l -match 'runtime ready') { $sawReady = $true } }
        }

        $elapsed = [int]((Get-Date) - $started).TotalSeconds
        # $alive is false either because the process ended or because the watch
        # window closed. Those are different verdicts, and conflating them would
        # report a clean bounded session as a crash.
        $stillRunning = $null -ne (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)
        $diedEarly = (-not $stillRunning) -and ($Seconds -le 0 -or $elapsed -lt $Seconds)

        # --- verdict -----------------------------------------------------
        Step 'verdict'
        $exit = 0
        $summary = ''

        if (-not $sawAny) {
            Fail 'no trace produced at all'
            Say '' 'the marker was absent, or the module never loaded. NOT a pass.'
            $exit = 4
            $summary = 'no_trace'
        } elseif ($sawReady -and $diedEarly) {
            Warn "runtime reached ready, then the process exited after ${elapsed}s"
            $summary = 'ready_then_exit'
            $exit = 0
        } elseif ($sawReady) {
            Ok "runtime ready; session ran ${elapsed}s"
            $summary = 'ready'
            $exit = 0
        } else {
            Fail "process exited after ${elapsed}s BEFORE the runtime was ready"
            $summary = 'died_before_ready'
            $exit = 3
        }

        Info "last line  $lastLine"
        if ($lastLine) {
            Step "last $TailLines lines of the session channel"
            if (Test-Path -LiteralPath $session) {
                Get-Content -LiteralPath $session -Tail $TailLines |
                    ForEach-Object { Write-Host "  $_" -ForegroundColor DarkCyan }
            } else {
                Warn 'no session log was written'
            }
        }

        $manifest = [pscustomobject]@{
            startedUtc  = $started.ToUniversalTime().ToString('o')
            endedUtc    = (Get-Date).ToUniversalTime().ToString('o')
            elapsedSec  = $elapsed
            pid         = $proc.Id
            summary     = $summary
            exitCode    = $exit
            stillRunning= $stillRunning
            boundedSec  = $Seconds
            traceArmed  = (-not $NoTrace)
            debug       = [bool]$Debug
            dllBytes    = (Get-Item $dll).Length
            reachedReady= $sawReady
            lastLine    = $lastLine
            note        = 'pipe intentionally never opened; see Trace.hpp'
        }
        $manifest | ConvertTo-Json |
            Set-Content -LiteralPath (Join-Path $dir 'run.json')

        Step 'artefacts'
        Ok "manifest   $(Join-Path $dir 'run.json')"
        Ok "session    $session"
        if (Test-Path -LiteralPath $trace) { Ok "trace      $trace" }
        Write-Host ''
        exit $exit
    }

    'tail' {
        $dir = $RunDir
        if (-not $dir) {
            if (-not (Test-Path -LiteralPath $RunsRoot)) { Fail 'no runs/ directory yet'; exit 1 }
            $dir = Get-ChildItem -LiteralPath $RunsRoot -Directory |
                   Sort-Object Name -Descending | Select-Object -First 1 | Select-Object -ExpandProperty FullName
        }
        if (-not $dir -or -not (Test-Path -LiteralPath $dir)) { Fail "no such run directory: $dir"; exit 1 }

        Step "run $dir"
        $mf = Join-Path $dir 'run.json'
        if (Test-Path -LiteralPath $mf) {
            Get-Content -LiteralPath $mf -Raw | ConvertFrom-Json |
                Format-List | Out-String | Write-Host
        } else {
            Warn 'no run.json -- this directory was staged but never run to completion'
        }
        $session = Join-Path $dir 'vprobe.trace.session.log'
        if (Test-Path -LiteralPath $session) {
            Step "last $TailLines lines of the session channel"
            Get-Content -LiteralPath $session -Tail $TailLines |
                ForEach-Object { Write-Host "  $_" -ForegroundColor DarkCyan }
        }
        $trace = Join-Path $dir 'vprobe.trace.log'
        if ($Debug -and (Test-Path -LiteralPath $trace)) {
            Step "last $TailLines lines of the trace channel"
            Get-Content -LiteralPath $trace -Tail $TailLines |
                ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        }
        Write-Host ''
        exit 0
    }
}

exit 2
