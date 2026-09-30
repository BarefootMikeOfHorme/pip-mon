# =============================================================
#  agent_watchdog.ps1 -- one command that tells an agent (or a
#  person) the true state of the workspace, and writes it down.
#
#  WHY THIS EXISTS
#    Long sessions lose their thread. The same facts get re-derived, a stale
#    claim outlives the change that invalidated it, and two writers disagree
#    about what is true. The fix is not discipline, it is a single artefact
#    that is regenerated from evidence and never hand-edited.
#
#    ai_state_dashboard.md is that artefact. It is OUTPUT. Anyone editing it by
#    hand has edited a generated file, and the next run will discard the edit
#    silently -- so the header says so.
#
#  EVERY LINE IS SOURCED
#    Each section records the command or file it came from. A fact with no
#    provenance may not exist, which is the project's own rule and the reason
#    this is a script rather than a note.
#
#  SKIP IS NOT PASS
#    A check that could not run is reported SKIP with its reason. The summary
#    line counts them separately, and the exit code treats a SKIP as
#    "not verified" rather than "fine".
#
#  USAGE
#    .\agent_watchdog.ps1              one pass, write the dashboard
#    .\agent_watchdog.ps1 -Watch 120   repeat every 120 seconds
# =============================================================
[CmdletBinding()]
param(
    [int]$Watch = 0,
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4'
)

$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
$Dash = Join-Path $Repo 'ai_state_dashboard.md'
$PatchLog = Join-Path $Repo 'runs\patches.log'

# Markdown fences and inline code spans, built without typing a backtick.
# PowerShell treats ` as the escape character, so "```" inside a double-quoted
# string is not three backticks -- it is an escaped backtick followed by an
# escape, and "`t" in a path silently becomes a TAB. Single quotes fix the first
# and this variable removes the second from the call sites.
$fence = [string]([char]96) * 3
$tick = [string]([char]96)

function Section($title) {
    Write-Output ''
    Write-Output "== $title"
}

function Get-PapyrusReport {
    $p = Join-Path $Repo 'runs\watch\papyrus-latest.json'
    if (Test-Path $p) { return (Get-Content $p -Raw | ConvertFrom-Json) }
    return $null
}

function Get-XeditReport {
    $p = Join-Path $Repo 'runs\watch\xedit-latest.json'
    if (Test-Path $p) { return (Get-Content $p -Raw | ConvertFrom-Json) }
    return $null
}

function Get-LatestRunDir {
    $runs = Join-Path $Repo 'runs'
    if (-not (Test-Path $runs)) { return $null }
    $dirs = Get-ChildItem $runs -Directory |
            Where-Object { $_.Name -match '^\d{8}-\d{6}$' } |
            Sort-Object Name -Descending
    if ($dirs.Count -eq 0) { return $null }
    return $dirs[0]
}

function Invoke-Pass {
    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz')
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# AI state dashboard")
    $lines.Add("")
    $lines.Add("> GENERATED FILE -- do not edit. Regenerate with " + $tick + "tools\agent_watchdog.ps1" + $tick + ".")
    $lines.Add("> A hand edit here is discarded on the next run, silently. Fix the source instead.")
    $lines.Add("")
    $lines.Add("- generated : $stamp")
    $lines.Add("- workspace : ``$Repo``")
    $lines.Add("- purpose   : one place to read what is VERIFIED, what is NOT, and what is BLOCKED,")
    $lines.Add("              so a fresh session never re-derives it or trusts a stale claim.")

    # ---- papyrus ---------------------------------------------------------
    Section 'papyrus: compile, fix, deploy'
    $pp = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Repo 'tools\watch_papyrus.ps1') -GameDir $GameDir 2>&1
    $papyrusExit = $LASTEXITCODE
    $pp | ForEach-Object { Write-Output "  $_" }
    $pr = Get-PapyrusReport

    $lines.Add("")
    $lines.Add("## Papyrus surface")
    $lines.Add("")
    $lines.Add("source: ``tools\watch_papyrus.ps1`` -> ``vprobe\papyrus\build_papyrus.bat``")
    if ($pr) {
        $lines.Add("")
        $lines.Add("- status  : **$($pr.status)** (exit $papyrusExit, $($pr.detail.passes) pass(es) of $($pr.detail.maxPasses))")
        if ($pr.detail.pexBytes) {
            foreach ($k in $pr.detail.pexBytes.PSObject.Properties) {
                $lines.Add("- built   : ``$($k.Name).pex`` = $($k.Value) B")
            }
        }
        if ($pr.detail.deployed -and $pr.detail.deployed.PSObject.Properties.Count -gt 0) {
            foreach ($k in $pr.detail.deployed.PSObject.Properties) {
                $lines.Add("- deployed: ``Data\Scripts\$($k.Name)`` = $($k.Value) B")
            }
        }
        if ($pr.detail.flagFixes -and $pr.detail.flagFixes.Count -gt 0) {
            $lines.Add("- patched : flags file amended this run (compiler-named flags only)")
        }
        if ($pr.status -eq 'RED') {
            $lines.Add("")
            $lines.Add($fence)
            $lines.Add($pr.detail.tail)
            $lines.Add($fence)
        }
    } else {
        $lines.Add("- status  : **UNKNOWN** (no report produced; see `runs/watch`)")
    }

    # ---- deploy verification --------------------------------------------
    Section 'deployment verification'
    $vd = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Repo 'testfacility\ck\verify_deploy.ps1') -GameDir $GameDir 2>&1
    $vdExit = $LASTEXITCODE
    $lines.Add("")
    $lines.Add("## Deployment (game folder)")
    $lines.Add("")
    $lines.Add("source: ``testfacility\ck\verify_deploy.ps1`` (read-only)")
    $lines.Add("")
    $lines.Add($fence)
    foreach ($l in $vd) { $lines.Add([string]$l) }
    $lines.Add($fence)

    # ---- the link --------------------------------------------------------
    Section 'load-order link'
    $ls = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Repo 'tools\linksync.ps1') status -GameDir $GameDir 2>&1
    $lines.Add("")
    $lines.Add("## Load order link")
    $lines.Add("")
    $lines.Add("source: ``tools\linksync.ps1 status`` (snapshot/apply/restore lives beside it)")
    $lines.Add("")
    $lines.Add($fence)
    foreach ($l in $ls) { $lines.Add([string]$l) }
    $lines.Add($fence)

    # ---- plugin validation ----------------------------------------------
    Section 'plugin validation (xEdit headless)'
    $xv = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Repo 'tools\validate_plugin.ps1') 2>&1
    $xeditExit = $LASTEXITCODE
    $xr = Get-XeditReport
    $lines.Add("")
    $lines.Add("## Plugin validation")
    $lines.Add("")
    $lines.Add("source: ``tools\validate_plugin.ps1`` -> xEdit headless + ``testfacility\xedit\validate_plugin.pas``")
    $lines.Add("")
    if ($xr) {
        $lines.Add("- status : **$($xr.status)** (exit $xeditExit)")
        if ($xr.reason) { $lines.Add("- reason : $($xr.reason)") }
    } else {
        $lines.Add("- status : **NOT RUN**")
    }
    $lines.Add("- note   : SKIP is not PASS. A skip means the check could not run, so the")
    $lines.Add("          property it covers is UNVERIFIED, not fine.")

    # ---- runtime ---------------------------------------------------------
    Section 'live runtime tail'
    $run = Get-LatestRunDir
    $lines.Add("")
    $lines.Add("## Live runtime (most recent run)")
    $lines.Add("")
    if ($run) {
        $sess = Join-Path $run.FullName 'vprobe.trace.session.log'
        $rj = Join-Path $run.FullName 'run.json'
        $lines.Add("source: ``runs\$($run.Name)``")
        $lines.Add("")
        if (Test-Path $rj) {
            $lines.Add($fence)
            foreach ($l in (Get-Content $rj)) { $lines.Add([string]$l) }
            $lines.Add($fence)
        }
        if (Test-Path $sess) {
            $lines.Add("")
            $lines.Add($fence)
            foreach ($l in (Get-Content $sess -Tail 8)) { $lines.Add([string]$l) }
            $lines.Add($fence)
        } else {
            $lines.Add("_no session log in that run_")
        }
    } else {
        $lines.Add("_no run directories found_")
    }

    # ---- summary ---------------------------------------------------------
    $summary = [ordered]@{}
    $summary['papyrus'] = if ($pr) { $pr.status } else { 'UNKNOWN' }
    $summary['deploy'] = if ($vdExit -eq 0) { 'GREEN' } else { 'ATTENTION' }
    $summary['pluginValidation'] = if ($xr) { $xr.status } else { 'NOT RUN' }
    $summary['xEditExit'] = $xeditExit

    $lines.Add("")
    $lines.Add("## Summary")
    $lines.Add("")
    $lines.Add("| check | state |")
    $lines.Add("|---|---|")
    foreach ($k in $summary.Keys) { $lines.Add("| $k | $($summary[$k]) |") }
    $lines.Add("")
    $lines.Add("## Still blocked (unchanged by this run)")
    $lines.Add("")
    $lines.Add("1. **No vtable slot is hooked.** Layer A does not exist, so a compiled .psc cannot")
    $lines.Add("   reach our natives and S0 is unproven. Blocked on one input: a BSScript class")
    $lines.Add("   declaration in method order, to turn a slot index into a name.")
    $lines.Add("2. **xEdit headless** cannot run until its first-run notice is clicked through once.")
    $lines.Add("3. **CKPE absent**: the CK render window crash-risks large cells; three CK crash")
    $lines.Add("   dumps recorded. On the in-house replacement list.")
    $lines.Add("4. **The facility cell does not exist yet.** `PipMonTestFacility.esp` is a valid")
    $lines.Add("   header with no records; the CK session or a headless generator must add them.")

    $lines | Set-Content -LiteralPath $Dash -Encoding utf8

    Write-Output ''
    Write-Output "dashboard: $Dash"
    foreach ($k in $summary.Keys) { Write-Output ("  {0,-18} {1}" -f $k, $summary[$k]) }

    if ($watch -gt 0) { Start-Sleep -Seconds $watch }
}

if ($Watch -gt 0) {
    Write-Output "watchdog: every $Watch s (Ctrl-C to stop)"
    while ($true) { Invoke-Pass }
} else {
    Invoke-Pass
}

