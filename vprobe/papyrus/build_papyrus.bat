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
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%" 2>nul || ( echo FAILED: could not create %STAGE% & exit /b 1 )
if not exist "%STAGE%\base" mkdir "%STAGE%\base"
REM The import source is the CK-installed base scripts. Without this the
REM compiler cannot resolve ScriptObject (see note 2).
if not exist "%FO4%\Data\Scripts\Source\ScriptObject.psc" (
  echo FAILED: base script sources not found under "%FO4%\Data\Scripts\Source"
  echo   Reinstall the Creation Kit ^(Steam app 1946160^).
  exit /b 1
)
REM The import is the stage root itself. The compiler's own help states that
REM "the current working directory ... is implied to be first in the import
REM list", and that is what actually resolves ScriptObject: the base sources
REM must sit in the SAME directory we run from, flat. An earlier revision put
REM them in a base\ subdirectory and passed -i=base, which does NOT work --
REM the compile failed with "Unable to find flags file" plus "unable to locate
REM script PipMon". Flattening into the run directory is the verified layout.
copy /y "%FO4%\Data\Scripts\Source\*.psc" "%STAGE%\" >nul
copy /y "%PAPYRUS%\PipMon.psc"        "%STAGE%\" >nul
copy /y "%PAPYRUS%\papyrus_flags.flg" "%STAGE%\" >nul
echo   staged base scripts + PipMon.psc + flags into %STAGE%

echo.
echo === compiling PipMon.psc ===
REM Every argument below is relative and space-free. See note 1.
pushd "%STAGE%"
"%CC%" PipMon.psc -f=papyrus_flags.flg
set RC=%errorlevel%
popd
if not "%RC%"=="0" ( echo FAILED: Papyrus compile exited %RC% & exit /b %RC% )

echo.
if not exist "%STAGE%\PipMon.pex" (
  echo FAILED: the compiler reported success but produced no PipMon.pex
  exit /b 1
)

REM Verify the artefact rather than trusting the compiler's own exit code,
REM for the same reason the native build does: a compiler that exits 0 having
REM written nothing is a failure mode that has already bitten this project once.
powershell -NoProfile -Command ^
  "$b=[IO.File]::ReadAllBytes('%STAGE%\PipMon.pex'); if ($b.Length -lt 8 -or $b[0] -ne 0xDE -or $b[1] -ne 0xC0 -or $b[2] -ne 0x57 -or $b[3] -ne 0xFA) { Write-Host 'FAILED: PipMon.pex is not a PEX image (bad magic)'; exit 1 } else { Write-Host ('  OK  PipMon.pex is a PEX image, ' + $b.Length + ' bytes') }"
if errorlevel 1 exit /b 1

if not exist "%PAPYRUS%\build" mkdir "%PAPYRUS%\build"
copy /y "%STAGE%\PipMon.pex" "%PAPYRUS%\build\PipMon.pex" >nul

echo.
echo PipMon.pex  built at %PAPYRUS%\build\PipMon.pex
endlocal
exit /b 0
