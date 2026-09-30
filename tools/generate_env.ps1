# =============================================================
#  generate_env.ps1 -- headless content generation for the test
#  facility, one piece at a time, verified after each piece.
#
#  WHY THIS EXISTS
#    The Creation Kit is the only tool that can author content here and also the
#    least reliable one: three crash dumps in a session, batch operations that
#    abort mid-dataset, and unsaved work lost each time. So the question for
#    every piece of content is not "can the CK do this" but "does this actually
#    need the CK". For a CELL record with an EditorID, it does not.
#
#  ONE PIECE AT A TIME
#    Each version of the generator script does one thing and reports three
#    outcomes: created, already-present, or failed. A generator that attempts
#    cell + fixtures + script attach + properties in one pass cannot be
#    debugged when it half-works, because the failure and the success are the
#    same file.
#
#  VERIFICATION IS THE POINT
#    The script is not trusted because it exited 0. After it runs, the plugin is
#    re-read: the size must have grown, the header must still be well formed,
#    and the snapshot of the previous state must exist so the change is
#    revertable. A generator that cannot prove it wrote something is a script
#    that reports success by exiting.
#
#  GUARD
#    Refuses to run while a Creation Kit process is open, for the same reason
#    validate_plugin.ps1 does: two tools writing the same plugin is how the
#    editor ends up saving over work it never saw.
# =============================================================
[CmdletBinding()]
param(
    [string]$Stage = 'cell',        # which piece to generate
    [string]$XEditDir = "$env:LOCALAPPDATA\Temp\opencode\xedit\x",
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4',
    [int]$TimeoutSec = 120
)

$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
$Plugin = Join-Path $GameDir 'Data\PipMonTestFacility.esp'
$SnapDir = Join-Path $Repo 'runs\tasks\facility-v0\snapshots'

function Report($status, $reason, $data) {
    $env_ = [ordered]@{
        schema = 'pipmon.generate/1'; stage = $Stage; status = $status
        ok = ($status -in 'GREEN', 'OK'); reason = $reason; data = $data
        provenance = [ordered]@{
            script = 'tools/generate_env.ps1'
            generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
        }
    }
    $env_ | ConvertTo-Json -Depth 6
}

# ---- guard ---------------------------------------------------------------
$ck = Get-Process CreationKit -ErrorAction SilentlyContinue
if ($ck) {
    Report 'SKIP' ("Creation Kit is running (pid $($ck.Id)); refusing to write the plugin underneath it") @{ creationKitPid = $ck.Id }
    exit 3
}
if (-not (Test-Path $Plugin)) {
    Report 'BROKEN' "plugin not found at $Plugin" @{}
    exit 2
}

$script = switch ($Stage) {
    'cell' { Join-Path $Repo 'testfacility\xedit\gen_facility.pas' }
    default { $null }
}
if (-not $script -or -not (Test-Path $script)) {
    Report 'BROKEN' "no generator script for stage '$Stage'" @{ stage = $Stage }
    exit 2
}

# ---- before state --------------------------------------------------------
New-Item -ItemType Directory -Path $SnapDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$before = (Get-Item $Plugin).Length
$revert = Join-Path $SnapDir "PipMonTestFacility.esp.pre-gen-$Stage.$stamp.bak"
Copy-Item -LiteralPath $Plugin -Destination $revert -Force

Write-Output "stage=$Stage  plugin=$before B  revert point: $(Split-Path $revert -Leaf)"

# ---- run -----------------------------------------------------------------
$exe = Join-Path $XEditDir 'xFOEdit64.exe'
if (-not (Test-Path $exe)) {
    Report 'BROKEN' "xEdit not found at $exe" @{ revertPoint = $revert }
    exit 2
}
$genReport = Join-Path $XEditDir 'gen-facility-report.json'
if (Test-Path $genReport) { Remove-Item -LiteralPath $genReport -Force }

$proc = Start-Process -FilePath $exe `
    -ArgumentList "`"$Plugin`"", '-auto', '-quickexit', "-script:`"$script`"" `
    -PassThru -NoNewWindow
if (-not $proc.WaitForExit($TimeoutSec * 1000)) {
    try { $proc.Kill() } catch { }
    Report 'SKIP' ("xEdit did not finish in ${TimeoutSec}s. It blocks on its first-run notice until that is" +
                   ' clicked through once; until then no headless generation can run.') @{ revertPoint = $revert; before = $before }
    exit 3
}

# ---- verify: did the file actually change, and is it still a plugin? ------
$after = (Get-Item $Plugin).Length
$detail = [ordered]@{
    beforeBytes = $before; afterBytes = $after
    grew        = ($after -gt $before)
    revertPoint = $revert
    xeditReport = $(if (Test-Path $genReport) { (Get-Content $genReport -Raw) } else { $null })
}

$b = [IO.File]::ReadAllBytes($Plugin)
$declared = [BitConverter]::ToUInt32($b, 4)
$version = [BitConverter]::ToUInt32($b, 20)
$detail['headerStillValid'] = ($b[0] -eq 0x54 -and $b[1] -eq 0x45 -and $b[2] -eq 0x53 -and $b[3] -eq 0x34 -and $version -eq 0x83 -and (8 + 16 + $declared) -le $b.Length)
Copy-Item -LiteralPath (Join-Path $SnapDir 'gen-facility-report.json') -Destination $SnapDir -ErrorAction SilentlyContinue
if (Test-Path $genReport) { Copy-Item -LiteralPath $genReport -Destination (Join-Path $SnapDir "gen-facility-report.$stamp.json") -Force }

if (-not $detail['headerStillValid']) {
    Report 'RED' 'the plugin header is no longer well formed after generation -- restore the revert point' $detail
    Write-Output "REVERT WITH: Copy-Item '$revert' '$Plugin' -Force"
    exit 1
}
if (-not $detail['grew']) {
    Report 'RED' 'xEdit finished but the plugin did not grow: nothing was written' $detail
    exit 1
}

Report 'GREEN' "generated '$Stage': $before -> $after bytes, header still valid" $detail
exit 0
