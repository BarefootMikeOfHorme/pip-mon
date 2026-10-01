# =============================================================
#  validate_plugin.ps1 -- run xEdit headlessly over a plugin and
#  turn the result into a JSON report an agent can read.
#
#  WHY THIS EXISTS
#    The workspace needed a way to check plugin files without the Creation Kit.
#    The CK crashes; xEdit headless does not, and it is the tool that already
#    parses this format correctly.
#
#  IT REFUSES TO PASS WHEN IT DID NOT RUN
#    A run that cannot produce a report emits {"status":"SKIP"} and exits 3.
#    SKIP is never collapsed into PASS anywhere downstream.
#
#  MEASURED BEHAVIOUR ON THIS MACHINE (2026-09-30)
#    - A full load of the curated core takes roughly 2m15s to reach the script's
#      Finalize, about 3 minutes wall clock. An earlier 90s and then 110s
#      timeout killed the process mid-load and reported SKIP. That was a false
#      negative caused by the harness, not a property of the plugin, so the
#      default is now 420s.
#    - The first run hung forever on xEdit's first-run notice. The user cleared
#      that interactively; the hang is gone and the tool now runs headlessly.
#    - The first successful-to-load run still produced NO report, because
#      validate_plugin.pas called GetPluginName, which does not exist in
#      FO4Edit 4.1.5f x64. It aborted in Finalize at 2m15s. The script no longer
#      calls any unproven API; its output path and plugin name are substituted
#      in as literals by this file.
#
#  WHY THIS RUNS DETACHED
#    A blocking 3-minute Start-Process -Wait made the agent unresponsive for the
#    whole run: no new input, no visibility, and a strong temptation to kill the
#    process instead of waiting for it. Long third-party runs are therefore
#    launched detached (-Async) and reaped by a later short poll (-Collect), so
#    the agent stays responsive and never guesses at progress.
#
#  LOCKS (refuse rather than stack instances)
#    - Refuses to start if CreationKit is running.
#    - Refuses to start if an xEdit process is already running. Two engines
#      writing the same Data folder is the failure this exists to prevent, and
#      an already-running xEdit means a job is in flight, not that it is safe
#      to add another.
#
#  EXIT CODES
#    0  PASS    -- xEdit parsed the plugin and a report was produced
#    1  FAIL    -- xEdit ran and the plugin did not validate
#    2  BROKEN  -- xEdit is missing entirely
#    3  SKIP    -- xEdit exists but could not run (see reason)
#    4  RUNNING -- -Collect only: job still in flight
#    5  LOCKED  -- an editor is already running; nothing was launched
# =============================================================
[CmdletBinding()]
param(
    [string]$Plugin = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Data\PipMonTestFacility.esp',
    [string]$XEditDir = "$env:LOCALAPPDATA\Temp\opencode\xedit\x",
    [int]$TimeoutSec = 420,
    [switch]$Async,
    [switch]$Collect
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Repo 'runs\watch'
$Report = Join-Path $OutDir 'xedit-latest.json'
$Template = Join-Path $Repo 'testfacility\xedit\validate_plugin.pas'
$GenScript = Join-Path $OutDir 'validate_plugin.gen.pas'
$JobFile = Join-Path $OutDir 'xedit-job.json'
$StdoutLog = Join-Path $OutDir 'xedit-stdout.log'
$StderrLog = Join-Path $OutDir 'xedit-stderr.log'
$XEditLog = Join-Path $XEditDir 'FO4Script_log.txt'

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

function Write-Report($status, $reason, $detail) {
    $obj = [ordered]@{
        generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
        status       = $status
        reason       = $reason
        plugin       = $Plugin
        tool         = 'xEdit (xFOEdit64.exe)'
        detail       = $detail
    }
    $obj | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Report -Encoding utf8
    Write-Output "report: $Report"
}

function Get-XEditLogTail {
    if (Test-Path $XEditLog) { return (Get-Content $XEditLog -Tail 25 -ErrorAction SilentlyContinue) }
    return @('(xEdit wrote no FO4Script_log.txt)')
}

# ---------------------------------------------------------------- COLLECT
if ($Collect) {
    if (-not (Test-Path $JobFile)) {
        Write-Output 'SKIP: no xEdit job to collect'
        Write-Report 'SKIP' 'no xEdit job was launched or none is recorded' $null
        exit 3
    }
    $job = Get-Content -LiteralPath $JobFile -Raw | ConvertFrom-Json
    $proc = Get-Process -Id $job.pid -ErrorAction SilentlyContinue
    $elapsed = [math]::Round(((Get-Date) - [datetime]$job.startedLocal).TotalSeconds, 1)

    if ($proc) {
        if ($elapsed -gt $job.timeoutSec) {
            Write-Output "SKIP: xEdit exceeded ${job.timeoutSec}s and is being stopped"
            try { $proc.Kill() } catch { }
            Write-Report 'SKIP' "xEdit exceeded its ${job.timeoutSec}s budget with no report" @{
                elapsedSec = $elapsed; xeditLog = Get-XEditLogTail
            }
            exit 3
        }
        Write-Output ("RUNNING: xEdit pid {0}, {1}s elapsed of {2}s" -f $job.pid, $elapsed, $job.timeoutSec)
        Write-Output 'poll again with: tools\validate_plugin.ps1 -Collect'
        exit 4
    }

    Write-Output ("xEdit pid {0} exited after {1}s" -f $job.pid, $elapsed)
    if (Test-Path $job.reportOut) {
        Copy-Item -LiteralPath $job.reportOut -Destination $Report -Force -ErrorAction SilentlyContinue
        $Report = $job.reportOut
    }
    if (Test-Path $job.reportOut) {
        Write-Output 'PASS: xEdit parsed the plugin and wrote a report'
        Get-Content $job.reportOut | Write-Output
        Write-Report 'PASS' 'xEdit parsed the plugin and produced a report' @{
            xeditReport = $job.reportOut; elapsedSec = $elapsed
            stdoutTail  = (Get-Content $StdoutLog -Tail 20 -ErrorAction SilentlyContinue)
        }
        exit 0
    }
    Write-Output 'FAIL: xEdit exited but produced no report -- script did not reach Finalize'
    Write-Report 'FAIL' 'xEdit ran to exit without writing a report; the script aborted before Finalize completed' @{
        elapsedSec = $elapsed
        xeditLog   = Get-XEditLogTail
        stdoutTail = (Get-Content $StdoutLog -Tail 30 -ErrorAction SilentlyContinue)
        stderrTail = (Get-Content $StderrLog -Tail 15 -ErrorAction SilentlyContinue)
    }
    exit 1
}

# ---------------------------------------------------------------- PRECHECKS
$ck = Get-Process CreationKit -ErrorAction SilentlyContinue
if ($ck) {
    Write-Output "SKIP: Creation Kit is running (pid $($ck.Id)) -- refusing to launch xEdit beside it"
    Write-Report 'SKIP' ("Creation Kit is running (pid $($ck.Id)). This tool will not launch xEdit while an " +
                         'editor session is open; the plugin is UNVERIFIED, not fine.') @{ creationKitPid = $ck.Id }
    exit 5
}
$existing = Get-Process xFOEdit64 -ErrorAction SilentlyContinue
if ($existing) {
    Write-Output "LOCKED: xEdit is already running (pid $($existing.Id)) -- refusing to start a second instance"
    Write-Report 'SKIP' ("xEdit is already running (pid $($existing.Id)). A job is almost certainly in flight; " +
                         'collect it with tools\validate_plugin.ps1 -Collect instead of launching another.') @{
        xeditPid = $existing.Id
        jobFile  = if (Test-Path $JobFile) { $JobFile } else { $null }
    }
    exit 5
}

$exe = Join-Path $XEditDir 'xFOEdit64.exe'
if (-not (Test-Path $exe)) {
    Write-Output "SKIP: xEdit not found at $exe"
    Write-Report 'SKIP' 'xEdit is not present at the configured path' $null
    exit 2
}
if (-not (Test-Path $Plugin)) {
    Write-Output "SKIP: plugin not found at $Plugin"
    Write-Report 'SKIP' 'the plugin to validate does not exist yet' $null
    exit 3
}
if (-not (Test-Path $Template)) {
    Write-Output "SKIP: script template not found at $Template"
    Write-Report 'SKIP' 'validate_plugin.pas template is missing' $null
    exit 3
}

# ---------------------------------------------------------------- SUBSTITUTE
# Bake the output path and plugin name into the script as literals. The template
# uses %%OUTPATH%% / %%PLUGIN%% precisely so that no xEdit API is needed to
# discover either one; GetPluginName was proven not to exist in 4.1.5f.
$reportOut = Join-Path $OutDir 'xedit-validation-report.json'
foreach ($p in @($reportOut, $StdoutLog, $StderrLog)) {
    if (Test-Path $p) { Remove-Item -LiteralPath $p -Force }
}
$src = Get-Content -LiteralPath $Template -Raw
$src = $src.Replace('%%OUTPATH%%', $reportOut).Replace('%%PLUGIN%%', (Split-Path $Plugin -Leaf))
if ($src -match '%%') {
    Write-Output 'FAIL: template still contains unsubstituted placeholders'
    Write-Report 'FAIL' 'validate_plugin.pas template has unresolved placeholders' @{ template = $Template }
    exit 1
}
Set-Content -LiteralPath $GenScript -Value $src -Encoding utf8
Write-Output "script: $GenScript"

$argList = @("`"$Plugin`"", '-auto', '-quickexit', "-script:`"$GenScript`"")

# ---------------------------------------------------------------- ASYNC
if ($Async) {
    # Reap orphans BEFORE launching. An async job is only bounded if something
    # collects it: without a collector it outlives its own budget silently. One
    # was launched and never collected, and sat for 191 minutes holding the
    # instance lock and blocking every later run. So the deadline goes in the
    # job file, and every launch enforces it. Self-healing, and deterministic.
    if (Test-Path $JobFile) {
        try {
            $old = Get-Content -LiteralPath $JobFile -Raw | ConvertFrom-Json
            $oldProc = Get-Process -Id $old.pid -ErrorAction SilentlyContinue
            if ($oldProc) {
                $oldAge = ((Get-Date) - [datetime]$old.startedLocal).TotalSeconds
                if ($oldAge -gt $old.timeoutSec) {
                    Write-Output ("reaping orphan xEdit pid {0}: {1:N0}s old against a {2}s budget" -f $old.pid, $oldAge, $old.timeoutSec)
                    try { $oldProc.Kill() } catch { }
                    Start-Sleep -Seconds 2
                } else {
                    Write-Output ("an xEdit job is already in flight (pid {0}, {1:N0}s of {2}s). Collect it with -Collect, or wait." -f $old.pid, $oldAge, $old.timeoutSec)
                    exit 5
                }
            }
        } catch {
            Write-Output "job file was unreadable; treating it as absent"
        }
    }

    # VISIBLE, deliberately. This used to be -WindowStyle Hidden, and that was
    # wrong in a way that looked like a broken tool: a hidden window cannot raise
    # or dismiss a modal dialog, so xEdit stalls at "Loading active plugin list"
    # with 0 bytes of stdout and no report. Observed twice, 191 minutes apart.
    #
    # The one run that demonstrably worked -- 35-plugin load, 2m15s, reached
    # Finalize -- was INTERACTIVE, with a real window. Documenting that as
    # "the mechanism works" and then running a hidden harness anyway is exactly
    # the green-gate-means-nothing failure, committed as fact. Match the proven
    # path: visible window, user-visible dialogs, nothing hidden.
    $proc = Start-Process -FilePath $exe -ArgumentList $argList -PassThru `
        -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog
    $job = [ordered]@{
        pid          = $proc.Id
        startedLocal = (Get-Date).ToString('o')
        deadlineLocal = (Get-Date).AddSeconds($TimeoutSec).ToString('o')
        timeoutSec   = $TimeoutSec
        plugin       = $Plugin
        reportOut    = $reportOut
        stdoutLog    = $StdoutLog
        xeditLog     = $XEditLog
    }
    $job | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $JobFile -Encoding utf8
    Write-Output "launched detached: xEdit pid $($proc.Id), deadline in ${TimeoutSec}s"
    Write-Output "poll with: tools\validate_plugin.ps1 -Collect"
    Write-Output "the job self-reaps: any later launch enforces the deadline, so it cannot leak again"
    exit 0
}

# ---------------------------------------------------------------- SYNC
Write-Output "xEdit: loading $(Split-Path $Plugin -Leaf) headlessly (timeout ${TimeoutSec}s)"
$sw = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -NoNewWindow `
    -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog

$finished = $proc.WaitForExit($TimeoutSec * 1000)
if (-not $finished) {
    Write-Output "SKIP: xEdit did not finish within ${TimeoutSec}s and was stopped"
    try { $proc.Kill() } catch { }
    Write-Report 'SKIP' ("xEdit did not complete headlessly in ${TimeoutSec}s. Measured on this machine a full " +
                         'load of the curated core takes roughly three minutes, so a shorter timeout is a false ' +
                         'negative and not a property of the plugin.') @{
        elapsedSec = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        timeoutSec = $TimeoutSec
        xeditLog   = Get-XEditLogTail
    }
    exit 3
}

Write-Output ("xEdit exited {0} after {1}s" -f $proc.ExitCode, [math]::Round($sw.Elapsed.TotalSeconds, 1))
if (Test-Path $reportOut) {
    Write-Output 'PASS: xEdit parsed the plugin and wrote a report'
    Get-Content $reportOut | Write-Output
    Write-Report 'PASS' 'xEdit parsed the plugin and produced a report' @{ xeditReport = $reportOut }
    exit 0
}
Write-Output 'FAIL: xEdit exited but produced no report -- script did not reach Finalize'
Write-Report 'FAIL' 'xEdit ran to exit without writing a report; the script aborted before Finalize completed' @{
    exitCode   = $proc.ExitCode
    elapsed    = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    xeditLog   = Get-XEditLogTail
    stdoutTail = (Get-Content $StdoutLog -Tail 30 -ErrorAction SilentlyContinue)
    stderrTail = (Get-Content $StderrLog -Tail 15 -ErrorAction SilentlyContinue)
}
exit 1
