# =============================================================
#  run_gen.ps1 -- drive testfacility/xedit/gen_facility.pas through xEdit,
#  headlessly, detached, and turn the result into a readable report.
#
#  WHY IT EXISTS
#    The plan's generation phase had the action "headless xEdit with the
#    generator" -- a phrase, not a command, so the orchestrator refused it and
#    the phase had never been runnable. This is that command. It is deliberately
#    the same shape as tools\validate_plugin.ps1, because that file is the only
#    xEdit runner on this machine that has actually produced a report, and a
#    second runner with a different structure would be a second set of bugs.
#
#  WHAT IS DIFFERENT FROM validate_plugin.ps1, and why
#    - It does NOT write to the game folder. The generator reaches a plugin and
#      reports; it creates nothing. So there is no snapshot/restore dance here,
#      and no risk of a half-written plugin in Data\. If the generator is ever
#      changed to save, that changes the risk profile and this file must grow a
#      snapshot step BEFORE that happens, not after.
#    - Its report is gen-facility-report.json, not the validator's, so the two
#      never overwrite each other's evidence.
#
#  MEASURED (2026-09-30 20:33, the validator run this was modelled on)
#    A full load of the curated core takes ~10s of loader time and ~1m42s of
#    script time over 2,287,300 records.
#
#  BUDGET -- was 420s, now 1800s. The 420s figure came from the validator's
#    1m42s walk and was "generous" for that. It was NOT generous for this
#    script: on 2026-10-01 00:02 the generator was killed at 200,000 of 2,287,300
#    records and the log shows "[EAbort] Operation aborted" in unit UserScript
#    line 200 -- which is the synchronous path's $proc.Kill() firing at the
#    deadline, not a script fault. The Process walk is byte-for-byte the same
#    shape as the validator's, which completes, so the abort was the budget and
#    nothing else. It aborted DURING the walk, so Finalize, Add and the save
#    never executed -- which is why no generator report and no scratch .esp were
#    ever produced, and why the three-argument FileWriteToStream looked untested.
#    It was never reached. 1800s leaves headroom over the measured walk without
#    hanging forever; a run that exceeds it is a real failure, not a slow one.

#  EXIT CODES (the project's standard vocabulary)
#    0  PASS    -- the generator ran and wrote its report
#    1  FAIL    -- it ran to exit without writing one
#    2  BROKEN  -- xEdit is not present
#    3  SKIP    -- it could not run, or nothing is in flight
#    4  RUNNING -- -Collect only: still in flight
#    5  LOCKED  -- an editor or another xEdit is already running
# =============================================================
[CmdletBinding()]
param(
    [string]$Plugin = 'PipMonTestFacility.esp',
    [string]$XEditDir = "$env:LOCALAPPDATA\Temp\opencode\xedit\x",
    [int]$TimeoutSec = 1800,
    [switch]$Async,
    [switch]$Collect,
    [switch]$GenOnly
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Repo 'runs\watch'
$Report = Join-Path $OutDir 'gen-facility-latest.json'
$Template = Join-Path $Repo 'testfacility\xedit\gen_facility.pas'
$GenScript = Join-Path $OutDir 'gen_facility.gen.pas'
$JobFile = Join-Path $OutDir 'gen-job.json'
$StdoutLog = Join-Path $OutDir 'gen-stdout.log'
$StderrLog = Join-Path $OutDir 'gen-stderr.log'
$XEditLog = Join-Path $XEditDir 'FO4Script_log.txt'
$XEditExcLog = Join-Path $XEditDir 'xFOEdit64Exception.log'
$ReportOut = Join-Path $OutDir 'gen-facility-report.json'

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

function Write-Report($status, $reason, $detail) {
    [ordered]@{
        generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
        status       = $status
        reason       = $reason
        plugin       = $Plugin
        tool         = 'xEdit (xFOEdit64.exe) via gen_facility.pas'
        detail       = $detail
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Report -Encoding utf8
    Write-Output "report: $Report"
}

# Same reader as the validator's, and for the same reason: xEdit reports a
# COMPILE failure to this file only, never to stdout, stderr or the run log.
# This log is UTF-16LE with a BOM.
function Get-Exc {
    if (-not (Test-Path $XEditExcLog)) {
        return [ordered]@{ present = $false; kind = 'none'; message = $null }
    }
    $fi = Get-Item -LiteralPath $XEditExcLog
    $raw = Get-Content -LiteralPath $XEditExcLog -Raw -ErrorAction SilentlyContinue
    if (-not $raw) { return [ordered]@{ present = $true; kind = 'empty'; message = $null; bytes = $fi.Length } }
    $blocks = ($raw -split '(?m)^=+\s*$') | Where-Object { $_.Trim() }
    $last = if ($blocks.Count) { $blocks[-1] } else { $raw }
    $msg = $null
    if ($last -match "(?m)^Message:\s*(.+?)\s*$") { $msg = $Matches[1] }
    $kind = 'runtime'
    if ($last -match 'CreateScript' -or ($msg -match 'expected but')) { $kind = 'compile' }
    elseif ($msg -match 'Undeclared Identifier') { $kind = 'compile' }
    return [ordered]@{ present = $true; kind = $kind; message = $msg
                       bytes = $fi.Length; mtime = $fi.LastWriteTime }
}

function Show-Exc($e) {
    if (-not $e.present) { Write-Output 'exception: none'; return }
    if ($e.kind -eq 'empty') { Write-Output ("exception: file present but EMPTY ({0} B)" -f $e.bytes); return }
    Write-Output ("exception: {0}" -f $e.kind)
    Write-Output ("  message: {0}" -f $e.message)
    if ($e.kind -eq 'compile') {
        Write-Output '  note   : the script was rejected before Initialize ran. Nothing was created.'
    }
}

# ---------------------------------------------------------------- COLLECT
if ($Collect) {
    if (-not (Test-Path $JobFile)) {
        Write-Output 'NO JOB IN FLIGHT: no gen-job.json. Nothing was launched, so no verdict.'
        Write-Report 'SKIP' 'no generator job was ever launched or none is recorded' $null
        exit 3
    }
    $job = Get-Content -LiteralPath $JobFile -Raw | ConvertFrom-Json
    $proc = Get-Process -Id $job.pid -ErrorAction SilentlyContinue
    $elapsed = [math]::Round(((Get-Date) - [datetime]$job.startedLocal).TotalSeconds, 1)

    if ($proc) {
        if ($elapsed -gt $job.timeoutSec) {
            Write-Output "SKIP: exceeded ${job.timeoutSec}s; stopping"
            try { $proc.Kill() } catch { }
            Write-Report 'SKIP' "generator exceeded its $($job.timeoutSec)s budget" @{ elapsedSec = $elapsed }
            exit 3
        }
        Write-Output ("RUNNING: xEdit pid {0}, {1}s of {2}s" -f $job.pid, $elapsed, $job.timeoutSec)
        $e = Get-Exc
        if ($e.present -and $e.kind -eq 'compile') {
            Write-Output '  BLOCKED: a COMPILE error is already on record; this run will not finish.'
            Show-Exc $e
        }
        if (Test-Path $XEditLog) {
            $lines = @(Get-Content $XEditLog -ErrorAction SilentlyContinue)
            $pip = @($lines | Where-Object { $_ -like 'PIPMON:*' })
            Write-Output ("  loader: {0} log lines; {1} PIPMON lines so far" -f $lines.Count, $pip.Count)
            $pip | Select-Object -Last 4 | ForEach-Object { "    $_" }
        }
        Write-Output 'poll again with: tools\run_gen.ps1 -Collect'
        exit 4
    }

    # Dead process. Only form a verdict if the log shows this job got as far as
    # the script -- otherwise a stale job file produces a FAIL about a run that
    # never happened. Measured 2026-09-30 21:33 on the validator: exactly that.
    $started = $null
    if (Test-Path $XEditLog) {
        $started = Get-Content $XEditLog -ErrorAction SilentlyContinue |
            Where-Object { $_ -match 'Start:\s*Applying script' } | Select-Object -Last 1
    }
    $logAge = if (Test-Path $XEditLog) { ((Get-Date) - (Get-Item $XEditLog).LastWriteTime).TotalSeconds } else { 99999 }
    $jobAge = $elapsed
    if (-not $started -and $logAge -gt 30 -and $jobAge -gt 15) {
        Write-Output ("NO JOB IN FLIGHT: pid {0} is gone and the log shows no run of it" -f $job.pid)
        Write-Output '  No verdict is issued: nothing was measured. This is UNVERIFIED, not FAIL.'
        Write-Report 'SKIP' 'recorded pid is gone and no run of it appears in the log; nothing was measured' @{
            recordedPid = $job.pid; elapsedSec = $elapsed }
        exit 3
    }

    Write-Output ("xEdit pid {0} exited after {1}s" -f $job.pid, $elapsed)
    $e = Get-Exc
    Show-Exc $e

    # Promote the staging file now that xEdit has exited and released its handle
    # on the loaded plugin. Until this point the CELL existed only in xEdit's
    # memory and the staging file was transport; the plugin in the game folder is
    # still the pre-run snapshot until the copy below succeeds.
    $stageEsp = Join-Path (Split-Path -Parent $Template) 'out\PipMonTestFacility.staging.esp'
    $gameTarget = Join-Path 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Data' $job.plugin
    if (Test-Path -LiteralPath $stageEsp) {
        $sz = (Get-Item -LiteralPath $stageEsp).Length
        Write-Output ("staging file: {0} B" -f $sz)
        if ($sz -le 66) {
            Write-Output 'NOT PROMOTED: staging file is header-only (66 B), so there is no CELL to install.'
            Write-Output '  Promoting it would replace a working plugin with an empty one.'
        } else {
            Copy-Item -LiteralPath $stageEsp -Destination $gameTarget -Force
            $now = (Get-Item -LiteralPath $gameTarget).Length
            Write-Output ("PROMOTED -> {0} ({1} B)" -f $gameTarget, $now)
            if ($now -le 66) { Write-Output '  WARNING: installed plugin is still 66 B. Verify before trusting it.' }
        }
    } else {
        Write-Output 'no staging file: the generator did not write one.'
    }

    if (Test-Path $ReportOut) {
        Copy-Item -LiteralPath $ReportOut -Destination $Report -Force
        Write-Output 'PASS: the generator wrote its report'
        Get-Content $ReportOut | Write-Output
        Write-Report 'PASS' 'generator ran and produced a report' @{ report = $ReportOut; elapsedSec = $elapsed }
        exit 0
    }
    $reason = if ($e.present -and $e.kind -eq 'compile') {
        "xEdit could not COMPILE the generator: $($e.message). Nothing was created."
    } else { 'generator ran to exit without writing a report' }
    Write-Output "FAIL: $reason"
    Write-Report 'FAIL' $reason @{
        exception = $e; elapsedSec = $elapsed
        logTail = (Get-Content $XEditLog -Tail 20 -ErrorAction SilentlyContinue)
    }
    exit 1
}

# ---------------------------------------------------------------- PRECHECKS
if (Get-Process CreationKit -ErrorAction SilentlyContinue) {
    Write-Output 'SKIP: Creation Kit is running; refusing to launch xEdit beside it'
    Write-Report 'SKIP' 'Creation Kit is running; this tool will not launch xEdit beside an editor session' $null
    exit 5
}
if (Get-Process xFOEdit64 -ErrorAction SilentlyContinue) {
    Write-Output 'LOCKED: xEdit is already running; refusing a second instance'
    Write-Report 'SKIP' 'xEdit is already running; a job is in flight. Collect it with -Collect' $null
    exit 5
}
$exe = Join-Path $XEditDir 'xFOEdit64.exe'
if (-not (Test-Path $exe)) { Write-Output "SKIP: xEdit not at $exe"; Write-Report 'SKIP' 'xEdit is not present at the configured path' $null; exit 2 }
if (-not (Test-Path $Template)) { Write-Output 'SKIP: gen_facility.pas missing'; Write-Report 'SKIP' 'the generator template is missing' $null; exit 3 }

# ---------------------------------------------------------------- SUBSTITUTE
foreach ($p in @($ReportOut, $StdoutLog, $StderrLog)) { if (Test-Path $p) { Remove-Item -LiteralPath $p -Force } }
$gameData = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Data'
$target = Join-Path $gameData $Plugin

# ---------------------------------------------------------------- WRITE TARGET
# xEdit CANNOT write the plugin in place, and this is not a workaround for
# something else. xEdit has the file open -- it loaded it, it is the load-order
# target -- and TFileStream.Create(..., fmCreate) needs exclusive access. The
# 2026-10-01 03:22 run proved it exactly:
#   [EFCreateError] Cannot create file "...\Data\PipMonTestFacility.esp".
#   The process cannot access the file because it is being used by another process
# The CELL was created first and only the write failed, so the create is fine and
# the destination was wrong.
#
# This is also why the shipped SaveAs.pas always saves to a DIFFERENT filename via
# a Save As dialog: xEdit has no in-place save, by construction. So the generator
# writes a STAGING file beside the source, and this runner promotes it into the
# game folder once xEdit has exited and released the handle. The plugin keeps its
# real name and real location; the staging file is a transport, not the artefact,
# and it is never the thing the game or the validator reads.
#
# The earlier arrangement wrote the staging file and left it there as
# 'PipMonTestFacility.probe.esp'. That was wrong twice: the file was not in the
# load order, so only the loaded plugin had a populated record group and the
# staging write serialised empty; and a '.probe' name for the output of a
# testfacility that must work in-game and in-engine is misnaming.
#
# The rollback that matters is the snapshot below, taken before every run.
$StageDir = Join-Path (Split-Path -Parent $Template) 'out'
if (-not (Test-Path -LiteralPath $StageDir)) {
    New-Item -ItemType Directory -Path $StageDir -Force | Out-Null
}
$StageEsp = Join-Path $StageDir 'PipMonTestFacility.staging.esp'
if (Test-Path -LiteralPath $StageEsp) { Remove-Item -LiteralPath $StageEsp -Force }

$gameData = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Data'
$target = Join-Path $gameData $Plugin
$WriteEsp = $StageEsp
if (Test-Path -LiteralPath $target) {
    $snapDir = Join-Path $Repo 'runs\tasks\facility-v0\snapshots'
    New-Item -ItemType Directory -Path $snapDir -Force | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $snap = Join-Path $snapDir ("$([IO.Path]::GetFileNameWithoutExtension($Plugin))-$stamp$([IO.Path]::GetExtension($Plugin))")
    Copy-Item -LiteralPath $target -Destination $snap -Force
    Write-Output "snapshot: $snap ($((Get-Item -LiteralPath $snap).Length) B)"
    Write-Output "restorable with: Copy-Item -LiteralPath '$snap' -Destination '$target' -Force"
}

$src = Get-Content -LiteralPath $Template -Raw
$src = $src.Replace('%%OUTPATH%%', $ReportOut).Replace('%%PLUGIN%%', $Plugin).Replace('%%SCRATCH%%', $WriteEsp)
if ($src -match '%%') {
    Write-Output 'FAIL: template still has unsubstituted placeholders'
    Write-Report 'FAIL' 'gen_facility.pas has unresolved placeholders' @{ template = $Template }
    exit 1
}
Set-Content -LiteralPath $GenScript -Value $src -Encoding utf8
Write-Output "script: $GenScript"

if (-not (Test-Path $target)) {
    Write-Output "SKIP: target plugin not found at $target"
    Write-Report 'SKIP' 'the target plugin does not exist in the game Data folder' @{ expected = $target }
    exit 3
}
Write-Output "target: $target"
Write-Output "writes to: $WriteEsp"

$argList = @("`"$target`"", '-auto', '-quickexit', "-script:`"$GenScript`"")

# ---------------------------------------------------------------- ASYNC
if ($Async) {
    if (Test-Path $JobFile) {
        try {
            $old = Get-Content -LiteralPath $JobFile -Raw | ConvertFrom-Json
            $op = Get-Process -Id $old.pid -ErrorAction SilentlyContinue
            if ($op) {
                $oa = ((Get-Date) - [datetime]$old.startedLocal).TotalSeconds
                if ($oa -gt $old.timeoutSec) {
                    Write-Output ("reaping orphan pid {0}: {1:N0}s old" -f $old.pid, $oa)
                    try { $op.Kill() } catch { }
                } else {
                    Write-Output ("a job is already in flight (pid {0}, {1:N0}s). Collect it." -f $old.pid, $oa)
                    exit 5
                }
            }
        } catch { Write-Output 'job file unreadable; treating as absent' }
    }
    # VISIBLE, deliberately. A hidden window cannot dismiss a modal dialog, and a
    # modal dialog is what an unattended compile error raises. The validator
    # learned that the hard way.
    $proc = Start-Process -FilePath $exe -ArgumentList $argList -PassThru `
        -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog
    [ordered]@{
        pid = $proc.Id; startedLocal = (Get-Date).ToString('o')
        deadlineLocal = (Get-Date).AddSeconds($TimeoutSec).ToString('o')
        timeoutSec = $TimeoutSec; plugin = $target
        reportOut = $ReportOut; stdoutLog = $StdoutLog; xeditLog = $XEditLog
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $JobFile -Encoding utf8
    Write-Output "launched detached: xEdit pid $($proc.Id), deadline in ${TimeoutSec}s"
    Write-Output 'poll with: tools\run_gen.ps1 -Collect'
    exit 0
}

# ---------------------------------------------------------------- SYNC
Write-Output "xEdit: running the generator against $Plugin (timeout ${TimeoutSec}s)"
$sw = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -NoNewWindow `
    -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog
if (-not $proc.WaitForExit($TimeoutSec * 1000)) {
    Write-Output "SKIP: did not finish within ${TimeoutSec}s"
    try { $proc.Kill() } catch { }
    $e = Get-Exc; Show-Exc $e
    Write-Report 'SKIP' "generator did not complete in ${TimeoutSec}s" @{ exception = $e }
    exit 3
}
$e = Get-Exc; Show-Exc $e
if (Test-Path $ReportOut) {
    Write-Output 'PASS: the generator wrote its report'
    Get-Content $ReportOut | Write-Output
    Write-Report 'PASS' 'generator ran and produced a report' @{ report = $ReportOut }
    exit 0
}
Write-Output 'FAIL: exited without writing a report'
Write-Report 'FAIL' 'generator ran to exit without writing a report' @{
    exception = $e; elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    logTail = (Get-Content $XEditLog -Tail 20 -ErrorAction SilentlyContinue) }
exit 1
