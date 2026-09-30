param(
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4'
)
# verify_deploy.ps1 -- did the CK session actually land?
#
# READ-ONLY. It inspects and reports; it changes nothing and starts nothing.
#
# WHY IT EXISTS
#   Every stage of this has failed silently at least once. The address database
#   was absent from the game folder for every live run so far, and the resolver
#   quietly fell back to its embedded dump -- 18/18 resolved, so nothing looked
#   wrong. That is precisely the shape of failure this project treats as its
#   worst, and a check that only runs when someone thinks to run it is not a
#   check.
$ErrorActionPreference = 'SilentlyContinue'

$fail = 0
function Row($ok, $what, $detail) {
    $tag = if ($ok) { ' OK ' } else { 'FAIL' }
    Write-Output ("  [{0}] {1,-34} {2}" -f $tag, $what, $detail)
    if (-not $ok) { $script:fail++ }
}

Write-Output ''
Write-Output 'PIP-MON deploy verification'
Write-Output ("  game dir : {0}" -f $GameDir)
if (-not (Test-Path $GameDir)) {
    Write-Output '  game directory not found -- nothing to check'
    exit 1
}
Write-Output ''

Write-Output 'Papyrus surface'
$pex = Join-Path $GameDir 'Data\Scripts\PipMon.pex'
if (Test-Path $pex) {
    $b = [IO.File]::ReadAllBytes($pex)
    $magic = ($b.Length -ge 4 -and $b[0] -eq 0xDE -and $b[1] -eq 0xC0 -and $b[2] -eq 0x57 -and $b[3] -eq 0xFA)
    Row $magic 'Data\Scripts\PipMon.pex' ("{0} B, magic {1}" -f $b.Length, $(if ($magic) { 'valid' } else { 'BAD' }))
} else {
    Row $false 'Data\Scripts\PipMon.pex' 'absent -- the 13 natives are unreachable'
}

$fac = Join-Path $GameDir 'Data\Scripts\PipMonTestFacility.pex'
if (Test-Path $fac) {
    $b = [IO.File]::ReadAllBytes($fac)
    $magic = ($b.Length -ge 4 -and $b[0] -eq 0xDE -and $b[1] -eq 0xC0 -and $b[2] -eq 0x57 -and $b[3] -eq 0xFA)
    Row $magic 'Data\Scripts\PipMonTestFacility.pex' ("{0} B, magic {1}" -f $b.Length, $(if ($magic) { 'valid' } else { 'BAD' }))
} else {
    Row $false 'Data\Scripts\PipMonTestFacility.pex' 'absent -- the test facility cannot run'
}

Write-Output ''
Write-Output 'Address database'
$libs = Join-Path $GameDir 'Data\PIP-MON\libs'
if (Test-Path $libs) {
    $t = Join-Path $libs 'vprobe.addresses.txt'
    $b = Join-Path $libs 'vprobe.addresses.bin'
    Row (Test-Path $t) 'Data\PIP-MON\libs\vprobe.addresses.txt' $(if (Test-Path $t) { ("{0} B" -f (Get-Item $t).Length) } else { 'absent' })
    Row (Test-Path $b) 'Data\PIP-MON\libs\vprobe.addresses.bin'  $(if (Test-Path $b) { ("{0} B" -f (Get-Item $b).Length) } else { 'absent' })
} else {
    Row $false 'Data\PIP-MON\libs' 'absent -- resolver falls back to the embedded dump'
}

Write-Output ''
Write-Output 'Plugin'
# The extension test is done with Where-Object rather than -Include. -Include is
# ignored on a literal (non-wildcard) -Path in PowerShell, so the original form
# of this row returned NOTHING for any input -- the plugin check could never
# pass, whether or not the plugin existed. A check that cannot pass is worse
# than no check, because it reads as a finding rather than as a broken tool.
$dataDir = Join-Path $GameDir 'Data'
$plug = @(Get-ChildItem $dataDir -File -ErrorAction SilentlyContinue |
          Where-Object { $_.Extension -in '.esp', '.esl' -and $_.Name -like 'PipMonTestFacility*' })
if ($plug.Count -gt 0) {
    foreach ($p in $plug) { Row $true $p.Name ("{0} B  {1}" -f $p.Length, $p.LastWriteTime.ToString('MM-dd HH:mm')) }
} else {
    Row $false 'PipMonTestFacility plugin' 'not found in Data\ -- the CK session has not produced one yet'
}

Write-Output ''
Write-Output 'Toolchain'
$ck = Join-Path $GameDir 'CreationKit.exe'
if (Test-Path $ck) {
    $v = (Get-Item $ck).VersionInfo.ProductVersion
    Row $true 'CreationKit.exe' $v
    $g = (Get-Item (Join-Path $GameDir 'Fallout4.exe')).VersionInfo.ProductVersion
    Row ($v -eq $g) 'CK matches game build' ("CK {0} / game {1}" -f $v, $g)
} else {
    Row $false 'CreationKit.exe' 'absent'
}

$ckpe = @(Get-ChildItem (Join-Path $GameDir 'Data') -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*PlatformExtended*' -or $_.Name -like '*CKPE*' })
Row ($ckpe.Count -gt 0) 'CKPE installed' $(if ($ckpe.Count -gt 0) { ($ckpe | Select-Object -ExpandProperty Name) -join ', ' } else { 'absent -- render crashes likely on large cells' })

Write-Output ''
if ($fail -eq 0) {
    Write-Output '  all checks passed'
    exit 0
}
Write-Output ("  {0} check(s) failed" -f $fail)
exit 1
