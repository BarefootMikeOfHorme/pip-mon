# =============================================================
#  ck_session.ps1 -- apply a curated load order for a Creation
#  Engine session, and put the previous one back afterwards.
#
#  WHY THIS EXISTS
#    The load order in plugins.txt is the single most valuable and most
#    fragile file in this workspace, and THREE programs want to write it:
#
#      - the user, by hand, which is how the current 61 entries got curated;
#      - the Creation Kit, on every session close;
#      - Vortex, which REGENERATES the list from its own mod state.
#
#    That last one is now measured rather than suspected: 36 of the 61 enabled
#    plugins have no Vortex staging entry at all, so Vortex does not know they
#    exist. Any Vortex deploy that rewrites plugins.txt therefore strips them
#    out of the load order -- which is exactly what happened to our own plugin
#    earlier today. Unmanaged files survive on disk but vanish from the order.
#
#    So this tool takes ownership of the swap in both directions:
#      prepare  snapshot what is live, then write the curated profile
#      restore  put the snapshot back
#      inspect  diff the live order against a profile, and report editor state
#
#  IT DOES NOT TOUCH THE EDITOR
#    No signals, no writes into Data\, nothing while a Creation Kit process is
#    up beyond plugins.txt itself, which the editor reads at startup. Loading
#    the data files remains a human action: the CK has no scriptable interface
#    here, and driving it by keystroke fights the user for the keyboard.
# =============================================================
[CmdletBinding()]
param(
    [Parameter(Position = 0)][ValidateSet('prepare', 'restore', 'inspect')]
    [string]$Action = 'inspect',

    [string]$Profile = 'core',
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4'
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$Profiles = Join-Path $Repo 'tasks\session-profiles.json'
$PluginTxt = Join-Path $env:LOCALAPPDATA 'Fallout4\plugins.txt'
$SessionRoot = Join-Path $Repo 'runs\ck-session'
$Latest = Join-Path $SessionRoot 'runtime-latest.txt'

if (-not (Test-Path $SessionRoot)) { New-Item -ItemType Directory -Path $SessionRoot -Force | Out-Null }

function Get-Profile($name) {
    $doc = Get-Content $Profiles -Raw | ConvertFrom-Json
    $p = $doc.profiles.$name
    if (-not $p) { throw "no such profile '$name' in $Profiles" }
    return $p
}

function Get-Live {
    if (-not (Test-Path $PluginTxt)) { return @() }
    # -Encoding utf8 is required, not cosmetic. Under Windows PowerShell 5.1
    # Get-Content with no encoding falls back to the system ANSI codepage, so a
    # UTF-8 plugins.txt with no BOM is MISREAD - and every downstream decision is
    # then made about a plugin name that does not exist. linksync.ps1:67 already
    # carries this; this file did not, which is the same bug twice.
    return @(Get-Content -LiteralPath $PluginTxt -Encoding utf8 | Where-Object { $_.Trim() -ne '' })
}

function Get-Enabled($lines) {
    return @($lines | Where-Object { $_.StartsWith('*') } | ForEach-Object { $_.Substring(1) })
}

switch ($Action) {

    'prepare' {
        $p = Get-Profile $Profile
        $live = Get-Live
        $liveEnabled = Get-Enabled $live

        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $dir = Join-Path $SessionRoot $stamp
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Copy-Item -LiteralPath $PluginTxt -Destination (Join-Path $dir 'plugins.txt') -Force
        Copy-Item -LiteralPath $PluginTxt -Destination $Latest -Force
        [ordered]@{
            takenUtc = (Get-Date).ToUniversalTime().ToString('o')
            enabled  = $liveEnabled.Count
            lines    = $live.Count
            note     = 'the load order that was live before this session; restore puts it back'
        } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'manifest.json') -Encoding utf8

        # Build the new order from the profile, preserving its order. The entry
        # marked alwaysLast goes last: in this file the last entry is the active
        # file, which is the whole reason the order is curated rather than
        # appended to.
        $head = @(); $tail = @()
        foreach ($e in @($p.entries)) {
            $line = if ($e.alwaysLast) { $e.name } else { "*$($e.name)" }
            if ($e.alwaysLast) { $tail += "*$($e.name)" } else { $head += $line }
        }
        $want = @($head + $tail)

        # Every profile entry must exist in Data\ before the order is written.
        # The first version of this guard tested existence and then exempted
        # every .esp/.esm/.esl from the test, which is to say it tested nothing:
        # a profile naming three masters that were not installed produced a
        # clean report and a Creation Kit that could not start. The exemption
        # was a typo-shaped mistake with a real consequence, so the check now
        # has no escape hatch.
        $missing = @()
        foreach ($e in @($p.entries)) {
            $n = $e.name
            if (-not (Test-Path (Join-Path $GameDir "Data\$n"))) {
                $missing += $n
            }
        }

        # INERT. This used to be:
        #
        #     Set-Content -LiteralPath $PluginTxt -Value $want -Encoding ascii
        #
        # which replaced the whole load-order file from a hard-coded profile
        # order. Two things were wrong with that and both bit.
        #
        # 1. It destroyed the live order. Anything set in the Creation Kit Data
        #    tab was erased on the next prepare, and the run still printed
        #    "prepared profile ..." as if that were the intent. The profile is a
        #    wish, not an authority: it cannot know what is currently staged.
        # 2. It wrote $PluginTxt (plugins.txt), which is not the file the editor
        #    and Vortex resolve from. So it wiped one order and set a different
        #    one, then reported success.
        #
        # So it now writes a proposal next to the file it would have replaced,
        # and says so. Nothing is applied. Restore stays available, and applying
        # a profile is now a separate, deliberate act.
        $proposal = "$PluginTxt.proposed.txt"
        # UTF-8 WITHOUT BOM, written the way linksync.ps1 does it at lines 178-183.
        # This was `Set-Content -Encoding ascii`, which is the bug commit 2ad0485
        # fixed in linksync.ps1 and left behind here: a non-ASCII plugin name
        # becomes "?" in the proposal. The proposal is the file a human reviews
        # and then applies, so it is the last place to mangle a name.
        # Set-Content is also avoided entirely - reading text and writing text
        # cannot promise no BOM and no re-encoding.
        $outLines = New-Object 'System.Collections.Generic.List[string]'
        foreach ($l in $want) { $outLines.Add($l) }
        $body = [string]::Join("`r`n", $outLines) + "`r`n"
        $enc = New-Object 'System.Text.UTF8Encoding'($false)
        [System.IO.File]::WriteAllText($proposal, $body, $enc)

        $after = $want
        $added = @($want | ForEach-Object { $_.Substring(1) } | Where-Object { $liveEnabled -notcontains $_ })
        $dropped = @($liveEnabled | Where-Object { $want -notcontains "*$_" })

        Write-Output "INERT: profile '$($p.label)' written as a proposal only"
        Write-Output ("  live file : {0}  ({1} entries) -- UNCHANGED" -f $PluginTxt, $liveEnabled.Count)
        Write-Output ("  proposal  : {0}  ({1} entries) -- not applied" -f $proposal, $want.Count)
        Write-Output ("  snapshot  : {0}" -f $dir)
        Write-Output ("  would add : {0}" -f $added.Count)
        Write-Output ("  would drop: {0}" -f $dropped.Count)
        if ($dropped.Count -gt 0) {
            Write-Output '  WOULD BE DROPPED (these are set live and the profile omits them):'
            foreach ($d in $dropped) { Write-Output "    - $d" }
        }
        if ($added.Count -gt 0) {
            Write-Output '  WOULD BE ADDED:'
            foreach ($a in $added) { Write-Output "    + $a" }
        }
        if ($missing.Count -gt 0) {
            Write-Output '  NOT ON DISK (the CK will report a missing master):'
            foreach ($m in $missing) { Write-Output "    ! $m" }
        }
        exit 0
    }

    'restore' {
        if (-not (Test-Path $Latest)) {
            Write-Output 'no snapshot to restore'
            exit 2
        }
        Copy-Item -LiteralPath $Latest -Destination $PluginTxt -Force
        $after = Get-Live
        Write-Output ("restored the pre-session load order: {0} enabled, last line '{1}'" -f (Get-Enabled $after).Count, $after[-1])
        exit 0
    }

    'inspect' {
        $p = Get-Profile $Profile
        $live = Get-Live
        $enabled = Get-Enabled $live
        $want = @($p.entries | ForEach-Object { $_.name })

        Write-Output "live load order: $($enabled.Count) enabled"
        Write-Output "profile '$($p.label)': $($want.Count) entries"
        Write-Output ''
        Write-Output 'in the profile but not live:'
        foreach ($n in $want) { if ($enabled -notcontains $n) { Write-Output "  - $n" } }
        Write-Output ''
        Write-Output 'live but not in the profile:'
        foreach ($n in $enabled) { if ($want -notcontains $n) { Write-Output "  + $n" } }

        $ck = Get-Process CreationKit -ErrorAction SilentlyContinue
        Write-Output ''
        Write-Output ("Creation Kit : {0}" -f $(if ($ck) { "RUNNING pid $($ck.Id)" } else { 'closed' }))
        $dump = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'CrashDumps') -Filter 'CreationKit*' -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($dump) {
            Write-Output ("last CK crash : {0} ({1} min ago, {2} MB)" -f $dump.Name, [math]::Round(((Get-Date) - $dump.LastWriteTime).TotalMinutes), [math]::Round($dump.Length / 1MB))
        }
        $w = Join-Path $GameDir 'EditorWarnings.txt'
        if (Test-Path $w) {
            Write-Output ("warnings file: {0} lines, written {1}" -f @(Get-Content $w).Count, (Get-Item $w).LastWriteTime)
        }
        exit 0
    }
}
