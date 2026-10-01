@echo off
REM ===========================================================================
REM  build_papyrus.bat - compile the PipMon: API surface to PipMon.pex.
REM
REM  Four non-obvious things this script exists to encode, each of which cost a
REM  real debugging cycle the first time:
REM
REM  1. THE COMPILER CANNOT PARSE SPACED PATHS.
REM     PapyrusCompiler.exe has its own argument splitter, and it splits on
REM     spaces inside a path. Handing it an absolute path containing a space
REM     yields "Unknown command line argument" or "Improperly formed command
REM     line argument" with no useful context. Both this repo's path and the
REM     game's own install path contain spaces. The fix is to run from a
REM     SPACE-FREE staging directory and pass only relative names, so no spaced
REM     path ever reaches the argument parser. %STAGE% is that directory.
REM
REM  2. THE BASE SCRIPTS MUST BE IMPORTABLE.
REM     Every Papyrus script implicitly extends ScriptObject, so the compiler
REM     needs ScriptObject.psc. It is not shipped with the compiler; the
REM     Creation Kit installs it under Data\Scripts\Source. Without it:
REM     "unable to locate script scriptobject". We stage that folder to
REM     %STAGE%\base and import it with a relative -i=base.
REM
REM  3. A FLAGS FILE IS REQUIRED, AND ITS FORMAT IS NOT OBVIOUS.
REM     ScriptObject.psc and the base scripts use user flags (hidden, quest,
REM     the JSkyLuaScript j* family). Without a -f flags file the compiler
REM     fails with "Unknown user flag hidden". The format is
REM     "Flag <Name> <index> { <types> }" with // comments, NOT one word per
REM     line and NOT semicolon comments. papyrus_flags.flg is generated from the
REM     base sources; see papyrus_flags.flg.md.
REM
REM  4. THE SCRIPT MUST BE FLAGGED Native.
REM     Not just its functions. "ScriptName PipMon" compiles to thirteen
REM     "function X cannot be defined as native because the script is not
REM     flagged as native" errors. The ScriptName line carries Native.
REM
REM  Usage: build_papyrus.bat
REM  Output: %~dp0build\PipMon.pex
REM ===========================================================================
setlocal

set R=%~dp0..
for %%I in ("%R%") do set R=%%~fI
REM %~dp0 is already "<repo>\vprobe\papyrus\", so after the normalisation
REM below %R% IS the vprobe directory. PAPYRUS is therefore %R%\papyrus --
REM writing %R%\vprobe\papyrus yields a doubled "vprobe\vprobe" and every
REM source copy silently no-ops while the FO4 copy (which uses a different
REM variable) still succeeds, so the stage ends up holding base scripts and
REM nothing of ours. That is the exact failure this comment is here to stop.
set PAPYRUS=%R%\papyrus
set FO4=C:\Program Files (x86)\Steam\steamapps\common\Fallout 4
set CC=%FO4%\Papyrus Compiler\PapyrusCompiler.exe
set STAGE=%TEMP%\pipmon_papyrus_stage

echo === checking the compiler is present ===
if not exist "%CC%" (
  echo FAILED: PapyrusCompiler.exe not found at "%CC%"
  echo   The Creation Kit is Steam app 1946160 ^(Fallout 4: Creation Kit^).
  echo   It installs into the game folder, not a separate program directory.
  exit /b 1
)

echo === staging into a space-free directory ===
REM The import source is the CK-installed base scripts. Without this the compiler
REM cannot resolve ScriptObject (see note 2).
REM
REM THE BASE SCRIPTS ARE NOT AT Source\ ROOT. On this install (CK 1.11.240)
REM they are at Data\Scripts\Source\Base\*.psc, with the user's own scripts in a
REM sibling Source\User tree. An earlier revision looked for them flat under
REM Source\, found nothing, and reported a missing Creation Kit on a machine
REM with a perfectly good one. Both layouts are accepted, because which one a
REM given CK uses is not ours to decide.
set BASESRC=
if exist "%FO4%\Data\Scripts\Source\Base\ScriptObject.psc" set BASESRC=%FO4%\Data\Scripts\Source\Base
if not defined BASESRC if exist "%FO4%\Data\Scripts\Source\ScriptObject.psc" set BASESRC=%FO4%\Data\Scripts\Source
if not defined BASESRC (
  echo FAILED: ScriptObject.psc not found under "%FO4%\Data\Scripts\Source"
  echo         nor under "%FO4%\Data\Scripts\Source\Base"
  echo   Reinstall the Creation Kit ^(Steam app 1946160^).
  exit /b 1
)
echo   base scripts: %BASESRC%
REM THE STAGING STEP IS THE BUILD. Measured on this machine: 2,422 base scripts,
REM 4,711 KB. Copy-Item for all of them costs 6,763 ms, and the two compiles
REM together cost 182 ms -- 97% of the wall clock was file copying, not
REM compilation. Wiping the directory first made it worse by adding a delete
REM pass every run.
REM
REM So the staging directory is PERSISTENT and re-mirrored instead of rebuilt.
REM robocopy /MIR copies only what differs: 2,812 ms on the first run (a cold
REM mirror) and 56 ms when nothing changed. /MIR also removes stale files, which
REM is what the old rmdir was there for -- but it removes OUR files too, so the
REM mirror has to run BEFORE our sources are copied in, not after.
if not exist "%STAGE%" mkdir "%STAGE%" 2>nul || ( echo FAILED: could not create %STAGE% & exit /b 1 )
where robocopy >nul 2>nul
if errorlevel 1 (
  echo FAILED: robocopy not found. It ships with Windows; without it this build
  echo         re-copies 2,422 base scripts on every run, which measured at
  echo         6,763 ms against 182 ms of actual compilation.
  exit /b 1
)
robocopy "%BASESRC%" "%STAGE%" *.psc /MIR /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 ( echo FAILED: robocopy could not mirror the base scripts & exit /b 1 )
copy /y "%PAPYRUS%\PipMon.psc"        "%STAGE%\" >nul
copy /y "%PAPYRUS%\PipMonTestFacility.psc" "%STAGE%\" >nul
copy /y "%PAPYRUS%\papyrus_flags.flg" "%STAGE%\" >nul

REM ---------------------------------------------------------------------------
REM  The rest of our Papyrus, which used to be in no gate at all.
REM
REM  Four scripts -- the event bridge and the three test bench probes -- sat in
REM  the tree for sessions with nothing compiling them, so a set of Skyrim-only
REM  constructs sat there failing nothing. A file that no gate reads is a file
REM  whose correctness is unknown rather than known-good, and "it is not in the
REM  build" is not the same as "it is not ours".
REM
REM  They are compiled here for that reason alone. They are NOT deployed and NOT
REM  copied to build\, because they are product code with their own placement and
REM  the CK session README still has to be walked through before any of it goes
REM  into a plugin. Compiling proves the language accepts it; it does not claim
REM  the content is right.
REM ---------------------------------------------------------------------------
REM  Single-line ifs on purpose. Inside a parenthesised block, %EXTRA% is
REM  expanded when the BLOCK is parsed, so every append would read the value
REM  from before the block ran and the list would come out as one literal
REM  "!EXTRA!" -- which is exactly what happened on the first attempt. A
REM  single-line if is parsed on its own, so plain %VAR% is correct here and no
REM  delayed expansion is needed.
set TOP=%~dp0..\..
set EXTRA=
if exist "%TOP%\overseer_event_bridge\Scripts\Source\OverseerBridge.psc" copy /y "%TOP%\overseer_event_bridge\Scripts\Source\OverseerBridge.psc" "%STAGE%\" >nul
if exist "%TOP%\overseer_event_bridge\Scripts\Source\OverseerBridge.psc" set EXTRA=%EXTRA% OverseerBridge
if exist "%TOP%\pip_mon_testlab\Scripts\Source\PipMon_LoopTest.psc" copy /y "%TOP%\pip_mon_testlab\Scripts\Source\PipMon_LoopTest.psc" "%STAGE%\" >nul
if exist "%TOP%\pip_mon_testlab\Scripts\Source\PipMon_LoopTest.psc" set EXTRA=%EXTRA% PipMon_LoopTest
if exist "%TOP%\pip_mon_testlab\Scripts\Source\PipMon_LeakTest.psc" copy /y "%TOP%\pip_mon_testlab\Scripts\Source\PipMon_LeakTest.psc" "%STAGE%\" >nul
if exist "%TOP%\pip_mon_testlab\Scripts\Source\PipMon_LeakTest.psc" set EXTRA=%EXTRA% PipMon_LeakTest
if exist "%TOP%\pip_mon_testlab\Scripts\Source\PipMon_TerminalTest.psc" copy /y "%TOP%\pip_mon_testlab\Scripts\Source\PipMon_TerminalTest.psc" "%STAGE%\" >nul
if exist "%TOP%\pip_mon_testlab\Scripts\Source\PipMon_TerminalTest.psc" set EXTRA=%EXTRA% PipMon_TerminalTest
if defined EXTRA echo   also staging:%EXTRA%
REM Stale .pex from a previous run must not be able to satisfy the verification
REM below. A leftover artefact that passes its own check is the failure mode this
REM project keeps re-learning.
del /q "%STAGE%\*.pex" >nul 2>nul
echo   staged base scripts + PipMon.psc + PipMonTestFacility.psc + flags
echo   into %STAGE%

echo.
echo === compiling PipMon.psc ===
REM Every argument below is relative and space-free. See note 1.
pushd "%STAGE%"
"%CC%" PipMon.psc -f=papyrus_flags.flg
set RC=%errorlevel%
popd
if not "%RC%"=="0" ( echo FAILED: Papyrus compile exited %RC% & exit /b %RC% )

REM The facility script is compiled in the SAME gate, and this is the whole
REM point of putting it here. It is the only script in the project that CALLS
REM the native surface, so it is the only thing that can catch a .psc that no
REM longer matches PipMon.psc. A gate that compiled only the surface would
REM report green while the one script that talks to it was broken -- which is
REM the exact shape of failure this project keeps re-learning.
REM
REM It is deliberately NOT flagged Native (see the script's own header): it is
REM an ordinary script that happens to call natives, and flagging it Native
REM would make the VM hunt for a body for every function in it.
echo.
echo === compiling PipMonTestFacility.psc ===
pushd "%STAGE%"
"%CC%" PipMonTestFacility.psc -f=papyrus_flags.flg
set RC2=%errorlevel%
popd
if not "%RC2%"=="0" ( echo FAILED: facility compile exited %RC2% & exit /b %RC2% )

echo.
if not exist "%STAGE%\PipMon.pex" (
  echo FAILED: the compiler reported success but produced no PipMon.pex
  exit /b 1
)
if not exist "%STAGE%\PipMonTestFacility.pex" (
  echo FAILED: the compiler reported success but produced no
  echo         PipMonTestFacility.pex
  exit /b 1
)

REM Verify the artefacts rather than trusting the compiler's own exit code,
REM for the same reason the native build does: a compiler that exits 0 having
REM written nothing is a failure mode that has already bitten this project once.
powershell -NoProfile -Command ^
  "$b=[IO.File]::ReadAllBytes('%STAGE%\PipMon.pex'); if ($b.Length -lt 8 -or $b[0] -ne 0xDE -or $b[1] -ne 0xC0 -or $b[2] -ne 0x57 -or $b[3] -ne 0xFA) { Write-Host 'FAILED: PipMon.pex is not a PEX image (bad magic)'; exit 1 } else { Write-Host ('  OK  PipMon.pex is a PEX image, ' + $b.Length + ' bytes') }; $f=[IO.File]::ReadAllBytes('%STAGE%\PipMonTestFacility.pex'); if ($f.Length -lt 8 -or $f[0] -ne 0xDE -or $f[1] -ne 0xC0 -or $f[2] -ne 0x57 -or $f[3] -ne 0xFA) { Write-Host 'FAILED: PipMonTestFacility.pex is not a PEX image (bad magic)'; exit 1 } else { Write-Host ('  OK  PipMonTestFacility.pex is a PEX image, ' + $f.Length + ' bytes') }"
if errorlevel 1 exit /b 1

if not exist "%PAPYRUS%\build" mkdir "%PAPYRUS%\build"
copy /y "%STAGE%\PipMon.pex" "%PAPYRUS%\build\PipMon.pex" >nul
copy /y "%STAGE%\PipMonTestFacility.pex" "%PAPYRUS%\build\PipMonTestFacility.pex" >nul

echo.
echo === compiling the rest of our Papyrus (compile-only; not deployed) ===
REM Each is named on failure, because "one of them did not compile" is not
REM actionable and four unnamed scripts is the exact shape of the problem this
REM section was added to fix.
REM
REM No list variable and no for-loop. The first attempt built a space-separated
REM %EXTRA% inside if-blocks and read it back inside a for-loop, which needs
REM delayed expansion that this script does not enable -- the loop ran once with
REM the literal text "!EXTRA!" as the script name. Four explicit calls have no
REM expansion to get wrong, and the set of scripts is not going to grow often.
set EXFAIL=0

call :compile_one OverseerBridge
call :compile_one PipMon_LoopTest
call :compile_one PipMon_LeakTest
call :compile_one PipMon_TerminalTest

if "%EXFAIL%"=="1" (
  echo.
  echo FAILED: not every Papyrus source compiles. See above.
  exit /b 1
)

echo.
echo PipMon.pex               built at %PAPYRUS%\build\PipMon.pex
echo PipMonTestFacility.pex   built at %PAPYRUS%\build\PipMonTestFacility.pex
echo compiled, not deployed :%EXTRA%
endlocal
exit /b 0

:compile_one
echo.
echo --- %~1 ---
pushd "%STAGE%"
"%CC%" %~1.psc -f=papyrus_flags.flg
set RC=%errorlevel%
popd
if exist "%STAGE%\%~1.pex" (
  if "%RC%"=="0" (
    echo   OK  %~1 compiles
  ) else (
    echo   FAILED: %~1 exit=%RC%
    set EXFAIL=1
  )
  del /q "%STAGE%\%~1.pex" >nul 2>nul
) else (
  echo   FAILED: %~1 did not compile. The compiler's message is above.
  set EXFAIL=1
)
exit /b 0
exit /b 0




