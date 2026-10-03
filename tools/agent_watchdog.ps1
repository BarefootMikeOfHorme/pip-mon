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
#  EXIT CODES
#    0  GREEN     every check in the pass ran and reported green
#    1  RED       papyrus or xedit ran and reported a failure
#    2  BROKEN    a tool this pass must run is absent, or a child reported a
#                 missing precondition
#    3  SKIP      at least one axis could not be established, and none failed
#
#    These existed in the header prose before any code produced them: the file
#    had no `exit` statement, so `powershell -File` returned 0 on every path and
#    `pipmon.ps1 verify` read that as GREEN. The verdict is now computed by
#    Get-WatchdogExit and this file exits with it.
#
#    Two axes -- deploy and link -- are exit codes and nothing else, and their
#    tools signal both "a check failed" and "a precondition is missing" with the
#    same code. So a non-zero from either is reported as SKIP, not RED: we can
#    say it is unestablished, and we cannot say which of the two it was.
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

# The four tools this pass drives. Checked for presence BEFORE running them,
# because invoking a missing script under ErrorActionPreference=Continue writes
# an error and leaves $LASTEXITCODE holding whatever the previous child left
# there -- so "the tool is absent" and "the tool ran and said something" would
# arrive as the same number.
$Tools = [ordered]@{
    papyrus = Join-Path $Repo 'tools\watch_papyrus.ps1'
    deploy  = Join-Path $Repo 'testfacility\ck\verify_deploy.ps1'
    link    = Join-Path $Repo 'tools\linksync.ps1'
    xedit   = Join-Path $Repo 'tools\validate_plugin.ps1'
}
$MissingTools = @($Tools.Keys | Where-Object { -not (Test-Path -LiteralPath $Tools[$_]) })

# Set by every pass and read once at the end. A script-scoped variable rather
# than a return value, because Invoke-Pass writes its narration to the output
# stream and `$v = Invoke-Pass` would collect that too.
$script:watchdogVerdict = $null

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

# THE VERDICT, as a pure function of what the pass observed.
#
# WHY THIS EXISTS AT ALL -- F2.4. This file contained no `exit` statement, so
# `powershell -File tools\agent_watchdog.ps1` returned 0 on every path, and
# `pipmon.ps1 verify` mapped 0 to GREEN. The dashboard was regenerated and the
# surface said "dashboard regenerated" -- which was true, and was the only thing
# it had verified. A check that cannot fail is decoration.
#
# It is a separate function rather than inline at the end of Invoke-Pass so that
# the decision can be exercised without running the pass. The pass compiles
# Papyrus and drives xEdit; AGENT-POLICY section 8 forbids both.
#
#   $missingTools  names of tools this pass must run and did not find on disk
#   $exits         ordered has papyrus / deploy / link / xedit -- child exit codes
#   $reports       ordered has papyrus / xedit -- the status each child RECORDED,
#                  read from the report it wrote during THIS pass, or $null
#
# Two distinctions the numbers alone cannot make, and which are therefore not
# guessed here:
#   * deploy and link are exit codes and nothing else. verify_deploy.ps1 exits 1
#     both for "a check failed" and for "the game directory is not there", and
#     linksync.ps1 exits 1 for a wrong result and for a thrown precondition (that
#     one is F2.5 and is unfixed). So a non-zero from either lands on SKIP --
#     "unestablished" -- and never on RED, which would claim the thing ran and is
#     wrong, and never on GREEN either.
#   * papyrus and xedit DO record what they found, so those two are read as
#     evidence rather than guessed from a code.
function Get-WatchdogExit($missingTools, $exits, $reports) {
    $unverified = @()
    if ($missingTools.Count -gt 0) {
        return [ordered]@{ exit = 2; verdict = 'BROKEN'
            reason = "a tool this pass must run is not on disk: $($missingTools -join ', ')" }
    }
    foreach ($k in 'papyrus', 'xedit') {
        if ($reports[$k] -eq 'BROKEN') {
            return [ordered]@{ exit = 2; verdict = 'BROKEN'
                reason = "$k reported a missing precondition (BROKEN); read the section below" }
        }
    }
    foreach ($k in 'papyrus', 'xedit') {
        if ($reports[$k] -in 'RED', 'FAIL') {
            return [ordered]@{ exit = 1; verdict = 'RED'
                reason = "$k ran and reported $($reports[$k]); the thing is wrong, not missing" }
        }
    }
    foreach ($k in 'papyrus', 'xedit') {
        if (-not $reports[$k]) { $unverified += "$k (no report produced)" }
        elseif ($reports[$k] -notin 'GREEN', 'PASS') { $unverified += "$k ($($reports[$k]))" }
    }
    foreach ($k in 'deploy', 'link') {
        # An exit code with no report behind it cannot say which of two different
        # things happened, so it is recorded as unestablished rather than guessed.
        if ($exits[$k] -ne 0) { $unverified += "$k (exit $($exits[$k]); its own vocabulary, not read here)" }
    }
    if ($unverified.Count -gt 0) {
        return [ordered]@{ exit = 3; verdict = 'SKIP'
            reason = "could not establish: $($unverified -join '; '). SKIP is not PASS." }
    }
    return [ordered]@{ exit = 0; verdict = 'GREEN'
        reason = 'every check in this pass ran and reported green' }
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
    # Was not captured at all. The load-order link has therefore never
    # contributed to this script's verdict, and could not have.
    $lsExit = $LASTEXITCODE
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
    # The verdict is computed BEFORE the dashboard is written, so the file on
    # disk states what this pass concluded rather than leaving a reader to
    # re-derive it from the table underneath.
    $script:watchdogVerdict = Get-WatchdogExit $MissingTools `
        ([ordered]@{ papyrus = $papyrusExit; deploy = $vdExit; link = $lsExit; xedit = $xeditExit }) `
        ([ordered]@{ papyrus = if ($pr) { $pr.status } else { $null }
                     xedit   = if ($xr) { $xr.status } else { $null } })

    $summary = [ordered]@{}
    $summary['verdict'] = "$($script:watchdogVerdict.verdict) (exit $($script:watchdogVerdict.exit))"
    $summary['verdictReason'] = $script:watchdogVerdict.reason
    $summary['papyrus'] = if ($pr) { $pr.status } else { 'UNKNOWN' }
    $summary['deploy'] = if ($vdExit -eq 0) { 'GREEN' } else { 'UNVERIFIED' }
    $summary['link'] = if ($lsExit -eq 0) { 'GREEN' } else { 'UNVERIFIED' }
    $summary['pluginValidation'] = if ($xr) { $xr.status } else { 'NOT RUN' }
    $summary['xEditExit'] = $xeditExit
    $summary['missingTools'] = if ($MissingTools.Count) { $MissingTools -join ', ' } else { 'none' }

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

# F2.4, the whole of it: this line did not exist, which is why the file returned
# 0 for everything. `pipmon.ps1 verify` maps the child's exit onto its own
# vocabulary, so a verdict computed here and thrown away here is a verdict the
# surface never sees.
#
# The last two lines are a net under the net. If Invoke-Pass somehow did not set
# a verdict, that is a broken pass and not a passing one, so it lands on BROKEN.
# A code outside 0-3 is not something the surface can mean, and BROKEN is the
# honest landing for a claim about the tool rather than about the subject.
$verdict = $script:watchdogVerdict
if (-not $verdict) {
    $verdict = [ordered]@{ exit = 2; verdict = 'BROKEN'
        reason = 'the pass produced no verdict at all, so nothing here is verified' }
}
$code = $verdict.exit
if ($code -notin 0, 1, 2, 3) { $code = 2 }
Write-Output "verdict: $($verdict.verdict) (exit $code) -- $($verdict.reason)"
exit $code

