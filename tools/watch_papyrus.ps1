# =============================================================
#  watch_papyrus.ps1 -- compile the Papyrus sources, fix what the
#  compiler names, deploy, verify, and log every action.
#
#  WHY THIS EXISTS
#    The agent-facing workflow this project wanted was "monitor the Papyrus
#    source folder, compile any changes, and if the compiler throws an error,
#    fix the script automatically and log the patch". It was being done by hand
#    in an ad-hoc shell loop, which is how the same mistake was made twice in
#    one session: a loop whose exit codes did not distinguish "fixed something"
#    from "nothing to do", so it stopped after a single pass while the build was
#    still red.
#
#    This is that loop, made into a tool with a real exit contract:
#       0  green  -- both .pex built, verified, and (optionally) deployed
#       1  red    -- the compiler still refuses, and the reason is in the report
#       2  broken -- the toolchain itself is missing (compiler, CK sources)
#       3  skip   -- nothing to do because a precondition was absent
#
#  WHAT IT IS ALLOWED TO FIX
#    Only what the compiler itself names:
#      - "Unknown user flag X"          -> declare X
#      - "Flag X is not allowed on Y"   -> widen X's scope
#    Both are mechanical and reversible, and both are applied by
#    tools/fix_papyrus_flags.py, which appends rather than regenerates so the
#    hand-written rationale comments in the flags file survive.
#
#    It does NOT guess at script semantics. A syntax error in a .psc is
#    reported with file and line and left for a human, because the project's
#    rule is to refuse rather than guess and a wrong "fix" to Papyrus is worse
#    than a red build.
#
#  EVERY ACTION IS LOGGED
#    runs/patches.log is an append-only record: timestamp, action, outcome.
#    "Log the patch" is only meaningful if the log is not written by the same
#    step that could have silently done nothing.
# =============================================================
[CmdletBinding()]
param(
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4',
    [switch]$NoDeploy,
    [int]$MaxPasses = 6
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$BuildBat = Join-Path $Repo 'vprobe\papyrus\build_papyrus.bat'
$FlagsFlg = Join-Path $Repo 'vprobe\papyrus\papyrus_flags.flg'
$FixTool = Join-Path $Repo 'tools\fix_papyrus_flags.py'
$WatchDir = Join-Path $Repo 'runs\watch'
$PatchLog = Join-Path $Repo 'runs\patches.log'
$ReportJson = Join-Path $WatchDir 'papyrus-latest.json'

New-Item -ItemType Directory -Path $WatchDir -Force | Out-Null

function Write-Log($message, $level = 'INFO') {
    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $line = "[$stamp] [$level] $message"
    Write-Output $line
    Add-Content -LiteralPath $PatchLog -Value $line -Encoding utf8
}

function Save-Report($status, $detail) {
    $obj = [ordered]@{
        generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
        status       = $status
        detail       = $detail
        buildBat     = $BuildBat
        flagsFile    = $FlagsFlg
        deployed     = (-not $NoDeploy)
        deploySuppressedBy = $deployBlockedBy
        gameDir      = $GameDir
        patchLog     = $PatchLog
    }
    $obj | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ReportJson -Encoding utf8
    Write-Output "report: $ReportJson"
}

# ---- preconditions -------------------------------------------------------
if (-not (Test-Path $BuildBat)) {
    Write-Log "build_papyrus.bat not found at $BuildBat" 'ERROR'
    Save-Report 'BROKEN' 'build_papyrus.bat missing'
    exit 2
}
$compiler = Join-Path $GameDir 'Papyrus Compiler\PapyrusCompiler.exe'
if (-not (Test-Path $compiler)) {
    Write-Log "PapyrusCompiler.exe not found at $compiler -- Creation Kit absent" 'ERROR'
    Save-Report 'BROKEN' 'PapyrusCompiler.exe missing'
    exit 2
}

Write-Log "papyrus watch starting (max $MaxPasses passes, deploy=$(if ($NoDeploy) {'off'} else {'on'}))"

# ---- GUARD: do not deploy into a game folder while the editor is open ------
# Compiling is safe and stays repo-local. Writing into the game folder is not
# something to do underneath an open Creation Kit session: Vortex and the CK
# both own files under Data\ and either may be mid-write. So the deploy step is
# suppressed and the reason is recorded, rather than being attempted and
# discovered later.
$ck = Get-Process CreationKit -ErrorAction SilentlyContinue
$deployBlockedBy = $null
if ($ck -and -not $NoDeploy) {
    $deployBlockedBy = $ck.Id
    $NoDeploy = [switch]$true
    Write-Log "Creation Kit is running (pid $($ck.Id)): compiling, but DEPLOY SUPPRESSED" 'WARN'
}

$log = Join-Path $WatchDir ("papyrus-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
$finalExit = 1
$passes = 0
$fixes = @()

for ($i = 1; $i -le $MaxPasses; $i++) {
    $passes = $i
    Write-Log "compile pass $i/$MaxPasses"
    cmd /c "`"$BuildBat`"" *> $log
    $rc = $LASTEXITCODE

    if ($rc -eq 0) {
        Write-Log "pass ${i}: BUILD GREEN" 'OK'
        $finalExit = 0
        break
    }

    # Ask the tool whether the compiler named a fixable flag problem. Exit code
    # 3 means it changed the file; 0 means there is nothing it may fix. Any other
    # code is a tool failure and must not be mistaken for "nothing to do".
    $out = & python $FixTool --log $log --flags $FlagsFlg 2>&1
    $fixRc = $LASTEXITCODE
    foreach ($o in $out) { Write-Output "  fix: $o" }

    if ($fixRc -eq 3) {
        $fixes += ($out -join ' | ')
        Write-Log "pass ${i}: flags file updated, recompiling" 'PATCH'
        continue
    }
    if ($fixRc -eq 0) {
        Write-Log "pass ${i}: build failed and no mechanical fix applies" 'ERROR'
        $finalExit = 1
        break
    }
    Write-Log "pass ${i}: fix tool itself failed (exit $fixRc)" 'ERROR'
    $finalExit = 2
    break
}

# ---- verification --------------------------------------------------------
$pex = @{}
if ($finalExit -eq 0) {
    foreach ($name in 'PipMon', 'PipMonTestFacility') {
        $src = Join-Path $Repo "vprobe\papyrus\build\$name.pex"
        if (-not (Test-Path $src)) {
            Write-Log "compiler reported success but $name.pex is missing" 'ERROR'
            $finalExit = 1
            break
        }
        $b = [IO.File]::ReadAllBytes($src)
        $magic = $b.Length -ge 8 -and $b[0] -eq 0xDE -and $b[1] -eq 0xC0 -and $b[2] -eq 0x57 -and $b[3] -eq 0xFA
        if (-not $magic) {
            Write-Log "$name.pex is not a PEX image (bad magic)" 'ERROR'
            $finalExit = 1
            break
        }
        $pex[$name] = $b.Length
        Write-Log ("verified {0}.pex: {1} B, magic valid" -f $name, $b.Length) 'OK'
    }
}

# ---- deployment ----------------------------------------------------------
$deployed = @{}
if ($finalExit -eq 0 -and -not $NoDeploy) {
    $target = Join-Path $GameDir 'Data\Scripts'
    if (-not (Test-Path $target)) {
        Write-Log "game Scripts directory missing at $target" 'ERROR'
        $finalExit = 2
    } else {
        foreach ($name in $pex.Keys) {
            Copy-Item (Join-Path $Repo "vprobe\papyrus\build\$name.pex") (Join-Path $target "$name.pex") -Force
            $live = (Get-Item (Join-Path $target "$name.pex")).Length
            $deployed["$name.pex"] = $live
            Write-Log ("deployed {0}.pex -> Data\Scripts ({1} B)" -f $name, $live) 'OK'
        }
    }
}

$status = switch ($finalExit) {
    0 { 'GREEN' }
    1 { 'RED' }
    2 { 'BROKEN' }
    default { 'UNKNOWN' }
}
Save-Report $status ([ordered]@{
    passes      = $passes
    maxPasses   = $MaxPasses
    pexBytes    = $pex
    deployed    = $deployed
    flagFixes   = $fixes
    buildLog    = $log
    tail        = ((Get-Content $log -Tail 12 -ErrorAction SilentlyContinue) -join "`n")
})

Write-Log "papyrus watch finished: $status"
exit $finalExit

