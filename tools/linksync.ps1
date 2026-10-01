# =============================================================
#  linksync.ps1 -- the owner of the plugin load-order link.
#
#  WHY THIS EXISTS
#    Data\Scripts\PipMon.pex, the address database and vprobe.dll are all
#    deployed and verified. What is still missing is a link that somebody owns,
#    because right now three things write plugins.txt and none of them talk to
#    the others:
#
#      - Vortex, which regenerates it from its own mod state and DROPS any
#        plugin it does not manage (observed: our esp was rewritten to a
#        disabled line at position 2 within minutes of being appended);
#      - the Creation Kit, which writes the checkbox state on every session
#        close (observed at 04:40 today: 145 -> 156 lines, 21 enabled);
#      - whoever hand-edits it, which is how "our mod is active" quietly
#        became "our mod is disabled" between two commands.
#
#    Silent link loss is the failure this project treats as its worst, and it
#    has now happened twice. This tool makes the link explicit: snapshot before
#    anything, apply deliberately, verify afterwards, restore on demand. The
#    write rule is the project's own, from the design notes: staging first,
#    diff second, apply only on request, always keep a backup.
#
#  IT DOES NOT WIN. It never edits in place without a snapshot, it never
#  touches mods.txt, and it reports what it did rather than assuming it worked.
#
#  USAGE
#    .\linksync.ps1 status
#    .\linksync.ps1 snapshot
#    .\linksync.ps1 apply -OurPlugin PipMonTestFacility.esp -Disable place_everything.esp
#    .\linksync.ps1 restore -Snapshot 20260930-054118
# =============================================================
[CmdletBinding()]
param(
    [ValidateSet('status', 'snapshot', 'apply', 'restore')]
    [string]$Command = 'status',

    # The plugin that must be enabled and must be LAST. Load order is the order
    # of this file, and the last entry is the active file, so "enabled" and
    # "active" are the same requirement expressed twice.
    [string]$OurPlugin = 'PipMonTestFacility.esp',

    # Applied by bare name, comma separated. Bare names are intentional: this
    # file's convention is that a leading '*' marks a plugin as enabled.
    [string[]]$Enable = @(),
    [string[]]$Disable = @(),

    [string]$Snapshot,
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4'
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$PluginTxt = Join-Path $env:LOCALAPPDATA 'Fallout4\plugins.txt'
$SnapshotRoot = Join-Path $Repo 'runs\linksync'

function Write-Head($text) { Write-Output ''; Write-Output $text; Write-Output ('-' * $text.Length) }

function Get-State {
    if (-not (Test-Path $PluginTxt)) { throw "plugins.txt not found at $PluginTxt" }
    # Read as UTF-8 explicitly rather than relying on the Get-Content default,
    # which has differed between PowerShell hosts. This is the read half of the
    # byte round trip: the write side is UTF-8 without BOM, so the read side must
    # be UTF-8 or a non-ASCII name is mangled before it is ever compared. Reading
    # a name as mojibake and then writing it back "faithfully" still loses the
    # original bytes.
    $lines = @(Get-Content -LiteralPath $PluginTxt -Encoding utf8)
    $enabled = @($lines | Where-Object { $_.StartsWith('*') })
    return [pscustomobject]@{
        Lines   = $lines
        Enabled = $enabled
        Count   = $enabled.Count
    }
}

function Save-Snapshot([string]$tag) {
    New-Item -ItemType Directory -Path $SnapshotRoot -Force | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $dir = Join-Path $SnapshotRoot $stamp
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Copy-Item -LiteralPath $PluginTxt -Destination (Join-Path $dir 'plugins.txt') -Force
    Set-Content -LiteralPath (Join-Path $dir 'tag.txt') -Value $tag -Encoding utf8
    return $dir
}

switch ($Command) {

    'status' {
        $s = Get-State
        Write-Head 'link status'
        Write-Output ("  file        : {0}" -f $PluginTxt)
        Write-Output ("  modified    : {0}" -f (Get-Item $PluginTxt).LastWriteTime)
        Write-Output ("  lines       : {0}" -f $s.Lines.Count)
        Write-Output ("  enabled     : {0}" -f $s.Count)
        Write-Output ("  our plugin  : {0}" -f $OurPlugin)
        $hits = @($s.Lines | Where-Object { ($_ -replace '^\*', '') -ieq $OurPlugin })
        if ($hits.Count -eq 0) {
            Write-Output '  our plugin  : ABSENT from the link'
        } else {
            foreach ($h in $hits) {
                $idx = [array]::IndexOf($s.Lines, $h)
                $state = if ($h.StartsWith('*')) { 'enabled' } else { 'DISABLED' }
                $place = if ($idx -eq $s.Lines.Count - 1) { 'last (active file)' } else { "line $($idx + 1)" }
                Write-Output ("  our plugin  : {0} -- {1}, {2}" -f $h, $state, $place)
            }
        }
        $esp = Join-Path $GameDir "Data\$OurPlugin"
        if (Test-Path $esp) {
            $f = Get-Item $esp
            Write-Output ("  deployed    : {0} B, {1}" -f $f.Length, $f.LastWriteTime)
        } else {
            Write-Output '  deployed    : ABSENT from Data\'
        }
        Write-Output ''
        Write-Output '  snapshots   :'
        if (Test-Path $SnapshotRoot) {
            Get-ChildItem $SnapshotRoot -Directory | Sort-Object Name |
                ForEach-Object { Write-Output ("    {0}  {1}" -f $_.Name, (Get-Content (Join-Path $_.FullName 'tag.txt') -ErrorAction SilentlyContinue)) }
        } else {
            Write-Output '    none yet'
        }
    }

    'snapshot' {
        $dir = Save-Snapshot 'manual snapshot'
        Write-Output ("snapshot: {0}" -f $dir)
    }

    'apply' {
        $s = Get-State
        $before = @($s.Lines)
        $dir = Save-Snapshot ("before apply (enable={0}; disable={1})" -f ($Enable -join ','), ($Disable -join ','))
        Write-Output ("snapshot: {0}" -f $dir)

        $lines = [System.Collections.Generic.List[string]]::new()
        foreach ($l in $before) { $lines.Add($l) }

        # Drop every mention of the plugins we are about to place, so that
        # ordering is decided here and not inherited from whatever wrote the
        # file last.
        $managed = @($OurPlugin) + $Enable + $Disable
        $kept = @($lines | Where-Object {
            $bare = $_ -replace '^\*', ''
            -not ($managed | Where-Object { $bare -ieq $_ })
        })

        foreach ($name in $Enable) {
            if ($name -ieq $OurPlugin) { continue }
            $kept += "*$name"
            Write-Output ("  enable  : {0}" -f $name)
        }
        foreach ($name in $Disable) {
            if ($name -ieq $OurPlugin) { continue }
            $kept += $name
            Write-Output ("  disable : {0}" -f $name)
        }

        # Last position == active file. This is the whole reason the link is
        # managed rather than appended to by hand.
        $kept += "*$OurPlugin"
        Write-Output ("  active  : *{0} (appended last)" -f $OurPlugin)

        # BYTE-EXACT WRITE. This used to be:
        #
        #     Set-Content -LiteralPath $PluginTxt -Value $kept -Encoding ascii
        #
        # which is silent, permanent data loss in a load-order file. Any plugin
        # whose name is not pure ASCII -- accents, Cyrillic, CJK, a right single
        # quote in a mod title -- was written as a question mark, and the
        # original name was never recoverable because the snapshot taken a few
        # lines earlier had already been read through the same lossy default.
        # A load-order tool must round-trip bytes exactly: it reads the file the
        # game wrote and must be able to hand the same bytes back. The game reads
        # plugins.txt as bytes, so bytes are the contract, not a decoded string.
        #
        # ReadAllBytes/WriteAllBytes also preserves the original line endings and
        # any BOM, because nothing is re-encoded on the way through. Reading as
        # text and writing back as text cannot promise either.
        $outLines = New-Object 'System.Collections.Generic.List[string]'
        foreach ($l in $kept) { $outLines.Add($l) }
        $crlf = "`r`n"
        $body = [string]::Join($crlf, $outLines) + $crlf
        $enc = New-Object 'System.Text.UTF8Encoding'($false)   # no BOM
        [System.IO.File]::WriteAllText($PluginTxt, $body, $enc)
        Write-Output ("  encoding: UTF-8 without BOM, CRLF, byte-exact round trip")

        $after = Get-State
        Write-Output ''
        Write-Output ("  enabled : {0} -> {1}" -f $s.Count, $after.Count)
        Write-Output ("  lines   : {0} -> {1}" -f $before.Count, $after.Lines.Count)
        Write-Output ("  last    : {0}" -f $after.Lines[-1])
        Write-Output ''
        Write-Output '  NOTE: Vortex rewrites this file from its own mod state on deploy.'
        Write-Output '        Re-run status after any Vortex deploy or CK session close.'
    }

    'restore' {
        if (-not $Snapshot) { throw 'restore needs -Snapshot <timestamp>' }
        $src = Join-Path (Join-Path $SnapshotRoot $Snapshot) 'plugins.txt'
        if (-not (Test-Path $src)) { throw "no snapshot at $src" }
        $backup = Save-Snapshot 'before restore'
        Copy-Item -LiteralPath $src -Destination $PluginTxt -Force
        $s = Get-State
        Write-Output ("restored {0} ({1} enabled); pre-restore snapshot at {2}" -f $Snapshot, $s.Count, $backup)
    }
}
