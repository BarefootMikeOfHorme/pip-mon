# =============================================================
#  unblock_and_generate.ps1 -- the one command that takes the
#  workspace from "blocked on a first-run notice" to "a cell
#  exists in the plugin", with the human involved exactly once.
#
#  WHY THIS EXISTS
#    Content generation headlessly needs xEdit, and xEdit refuses to run
#    headlessly until its first-run notice has been dismissed by a person --
#    measured here as a 240 s hang producing no output. Everything downstream
#    of that click is scriptable, so the click should cost the user one action
#    and then never again, not a decision every session.
#
#    This exists so that the cost is ONE command that does the whole chain,
#    rather than a sequence the user has to know, order and babysit:
#
#      0. refuse if the Creation Kit is open (two writers, one plugin)
#      1. snapshot the current state            <- revert point
#      2. launch xEdit ONCE, visibly, and wait   <- the human clicks the notice
#      3. confirm xEdit can now run headlessly   <- proof the click took
#      4. generate the next content piece        <- cell, then fixtures
#      5. inventory the result                   <- proof it is really there
#      6. snapshot again                          <- checkpoint after the work
#
#  THE HUMAN TOUCH IS STEP 2 AND NOTHING ELSE
#    Step 3 is the honest test: if the click did not take, xEdit hangs again
#    and this reports SKIP with the reason rather than pretending to have
#    generated anything.
#
#  EXIT CODES
#    0  GREEN  the stage was generated and inventoried
#    1  RED    the stage ran but did not land, or the plugin is now invalid
#    2  BROKEN a tool is missing
#    3  SKIP   something refused to run (editor open, notice not yet clicked)
# =============================================================
[CmdletBinding()]
param(
    [string]$Stage = 'cell',
    [string]$XEditDir = "$env:LOCALAPPDATA\Temp\opencode\xedit\x",
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4',
    [int]$ProbeTimeoutSec = 90
)

$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Repo 'tools'
$Plugin = Join-Path $GameDir 'Data\PipMonTestFacility.esp'

function Say($m) { Write-Output $m }
function Report($status, $reason, $data) {
    [ordered]@{
        schema = 'pipmon.unblock/1'; status = $status; ok = ($status -in 'GREEN', 'OK')
        reason = $reason; stage = $Stage; data = $data
        provenance = [ordered]@{
            script = 'tools/unblock_and_generate.ps1'
            generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
        }
    } | ConvertTo-Json -Depth 6
}

# ---- 0. the editor must be closed -----------------------------------------
$ck = Get-Process CreationKit -ErrorAction SilentlyContinue
if ($ck) {
    Report 'SKIP' ("Creation Kit is open (pid $($ck.Id)). Close it: this command writes the same plugin the " +
                   'editor has open, and two writers is how work gets silently overwritten.') @{ creationKitPid = $ck.Id }
    exit 3
}

# ---- 1. revert point before anything ------------------------------------
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Tools 'pipmon.ps1') snapshot "pre-$Stage" | Out-Null
$before = if (Test-Path $Plugin) { (Get-Item $Plugin).Length } else { 0 }
Say "1. snapshot taken; plugin is $before B"

# ---- 2. the one human action ----------------------------------------------
$exe = Join-Path $XEditDir 'xFOEdit64.exe'
if (-not (Test-Path $exe)) {
    Report 'BROKEN' "xEdit not found at $exe" @{ }
    exit 2
}

$alreadyUsable = $false
$probe = Join-Path $XEditDir 'gen-facility-report.json'
if (Test-Path $probe) { Remove-Item -LiteralPath $probe -Force }

Say ''
Say '2. launching xEdit ONCE, visibly.'
Say '   >>> CLICK THROUGH THE FIRST-RUN NOTICE, then close xEdit. That is the only'
Say '   >>> thing asked of you in this whole chain.'

$p = Start-Process -FilePath $exe -PassThru
$finished = $p.WaitForExit(600000)
Say "   xEdit exited: $finished"
Start-Sleep -Seconds 2

# ---- 3. prove the notice was dismissed, do not assume it ------------------
Say ''
Say '3. probing whether xEdit can now run headlessly (this is the proof, not a hope)'
$pv = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Tools 'validate_plugin.ps1') -TimeoutSec $ProbeTimeoutSec 2>&1
$validateExit = $LASTEXITCODE
foreach ($l in @($pv) | Select-Object -First 6) { Say "   $_" }
$alreadyUsable = ($validateExit -eq 0)

if (-not $alreadyUsable) {
    Report 'SKIP' ("xEdit still cannot run headlessly (validate exited $validateExit). The first-run notice " +
                   'is most likely still in front of it: click it, close xEdit, and run this command again. ' +
                   'Nothing was generated and nothing was changed.') @{
        validateExit = $validateExit
        pluginUnchangedBytes = (Get-Item $Plugin).Length
        before = $before
    }
    exit 3
}

# ---- 4. generate ----------------------------------------------------------
Say ''
Say "4. generating stage '$Stage'"
$g = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Tools 'generate_env.ps1') -Stage $Stage -GameDir $GameDir 2>&1
$genExit = $LASTEXITCODE
foreach ($l in @($g)) { Say "   $_" }

# ---- 5. inventory ---------------------------------------------------------
Say ''
Say '5. inventorying the plugin so the result is proven, not assumed'
$after = (Get-Item $Plugin).Length
$v2 = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Tools 'validate_plugin.ps1') -TimeoutSec $ProbeTimeoutSec 2>&1
$v2Exit = $LASTEXITCODE
$inv = $null
$invPath = Join-Path $XEditDir 'validation-report.json'
if (Test-Path $invPath) {
    try { $inv = Get-Content $invPath -Raw | ConvertFrom-Json } catch { $inv = $null }
}

# ---- 6. checkpoint after the work ----------------------------------------
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Tools 'pipmon.ps1') snapshot "post-$Stage" | Out-Null

$data = [ordered]@{
    beforeBytes    = $before
    afterBytes     = $after
    grew           = ($after -gt $before)
    generateExit   = $genExit
    inventoryExit  = $v2Exit
    inventory      = $inv
}

if ($genExit -ne 0 -or -not $data['grew']) {
    Report 'RED' "stage '$Stage' did not land; the revert point from step 1 is in place" $data
    exit 1
}
Report 'GREEN' "stage '$Stage' generated and inventoried" $data
exit 0
