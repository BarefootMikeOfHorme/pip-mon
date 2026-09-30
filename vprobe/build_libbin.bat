@echo off
REM ===========================================================================
REM  build_libbin.bat - compile the address INI into the .bin blob, and verify
REM  it. Runs in the main build gate because the blob is a DERIVED artefact and
REM  derived artefacts are exactly what goes stale.
REM
REM  WHY THIS IS IN THE GATE
REM    The .bin is produced from the .txt by tools/build_libbin.py. Nothing else
REM    connects them: edit the .txt, and the blob on disk keeps serving the old
REM    RVAs while the build reports success. That is the same drift class as the
REM    .psc/registry mismatch the conformance test exists to catch, and it is
REM    worse because the failure is silent AND lands as a wrong address in a
REM    detour rather than as a compile error.
REM
REM    So this regenerates from source, verifies the result, and -- crucially --
REM    FAILS if the regenerated blob differs from the committed one. A blob that
REM    is out of date with its INI is a failure, not a warning.
REM
REM  Usage: build_libbin.bat
REM  Skip:  set PIPMON_SKIP_LIBBIN=1 to skip (no game installed, CI, etc.)
REM ===========================================================================
setlocal

set R=%~dp0..
for %%I in ("%R%") do set R=%%~fI
set LIBDIR=%R%\vprobe\libs
set INI=%LIBDIR%\fo4_1_11_240.addresses.txt
set BIN=%LIBDIR%\fo4_1_11_240.addresses.bin

if "%PIPMON_SKIP_LIBBIN%"=="1" (
  echo SKIP: PIPMON_SKIP_LIBBIN=1
  endlocal & exit /b 0
)

REM The blob records a PE header hash of the game executable so the runtime can
REM refuse a blob built for a different patch. Without the exe we cannot produce
REM a valid blob, and producing one with a placeholder identity would defeat the
REM entire point -- so this is a skip, not a fallback.
REM
REM Written with goto rather than if exist ( ... ) blocks ON PURPOSE. The
REM default Steam path contains "(x86)", and cmd tracks parenthesis nesting
REM inside those blocks even within a quoted string -- so the block closes
REM early and the script dies with "was unexpected at this time", pointing at
REM the Steam path rather than at the real cause. Any path containing
REM parentheses must be tested with goto labels, not a block.
set "FO4EXE=C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Fallout4.exe"
if exist "%FO4EXE%" goto :have_exe
set "FO4EXE=C:\Games\Fallout 4\Fallout4.exe"
if exist "%FO4EXE%" goto :have_exe
set "FO4EXE="

echo SKIP: no Fallout4.exe found; the blob needs a real image identity
echo       to be produced, and a placeholder one would defeat its purpose.
endlocal & exit /b 0

:have_exe

if not exist "%INI%" (
  echo FAILED: source INI not found: %INI%
  exit /b 1
)

echo === regenerating the address blob from the INI ===
REM Write to a temp path first, then compare, so a failure part-way through
REM cannot leave a half-written blob that the next build would trust.
set TMPBIN=%TEMP%\pipmon_libbin_check.bin
if exist "%TMPBIN%" del /q "%TMPBIN%"

python "%R%\tools\build_libbin.py" "%INI%" "%TMPBIN%" "%FO4EXE%"
if errorlevel 1 ( echo FAILED: blob generation & exit /b 1 )

echo === verifying the generated blob ===
python "%R%\tools\verify_libbin.py" "%TMPBIN%"
if errorlevel 1 ( echo FAILED: blob verification & exit /b 1 )

echo === checking the blob is not stale ===
REM Compare against the committed blob. A difference means the INI changed and
REM the blob was never regenerated -- exactly the drift this step exists to
REM catch, so it is a hard failure rather than a note.
if not exist "%BIN%" (
  copy /y "%TMPBIN%" "%BIN%" >nul
  echo   new: blob created at %BIN%
  endlocal & exit /b 0
)

fc /b "%TMPBIN%" "%BIN%" >nul 2>&1
if errorlevel 1 (
  echo FAILED: the committed blob is STALE -- it differs from what the INI
  echo         now generates. The runtime would serve old RVAs.
  echo         Overwrite it and commit:
  echo           copy /y "%TMPBIN%" "%BIN%"
  exit /b 1
)

del /q "%TMPBIN%"
echo   OK  blob is current with the INI

REM ---------------------------------------------------------------------------
REM  DEPLOY NAMING. The repository keeps one file PER GAME BUILD, named with
REM  the build key, because several game installs and several patches are
REM  expected. The RUNTIME, however, has a fixed contract name and will not
REM  enumerate a directory: it looks for vprobe.addresses.txt / .bin in three
REM  known places.
REM
REM  Those two facts have to meet somewhere, and it is HERE, at build time,
REM  because build time is the heavy end (section 26: T1 may be slow, T2 may
REM  not). The runtime picks the build by hashing its own PE headers; choosing
REM  WHICH file to install for that build is a build-time decision.
REM
REM  This was a real defect, and a silent one: the build produced
REM  fo4_1_11_240.addresses.txt while the runtime searched for
REM  vprobe.addresses.txt, so the repository's own libs directory could never be
REM  loaded. It only appeared to work because a manual staging step happened to
REM  copy the file under the contract name. Nothing in the gate compared the
REM  two, so a green build shipped a database the runtime could not find --
REM  which presents as "text form unavailable" and, because the blob is derived
REM  from the INI's path, takes the binary database down with it.
echo === verifying the runtime's deploy name resolves ===
set DEPLOY=%LIBDIR%\deploy
if not exist "%DEPLOY%" mkdir "%DEPLOY%"

REM Select the source for THIS build. No key parsing is needed: the blob we
REM just generated and verified IS the one for the active build, so its own
REM basename names the matching per-build INI. (The build key inside the blob
REM is a header-hash identity, not the version string used in filenames -- an
REM earlier draft tried to extract it and produced a name that matched nothing.)
for %%F in ("%BIN%") do set BASENAME=%%~nF
set "SRC=%LIBDIR%\%BASENAME%.txt"

if not exist "%SRC%" (
  echo FAILED: no per-build source named "%SRC%"
  echo   The repo must ship one file per game build, next to the blob.
  exit /b 1
)

copy /y "%SRC%" "%DEPLOY%\vprobe.addresses.txt" >nul
copy /y "%BIN%" "%DEPLOY%\vprobe.addresses.bin" >nul
echo   deploy\vprobe.addresses.txt  (from %BASENAME%.txt)

REM Prove the runtime can find what we just staged, by checking for the exact
REM names main.cpp searches for. Cheap, and it is the check that was missing.
if not exist "%DEPLOY%\vprobe.addresses.txt" (
  echo FAILED: deploy name missing - the runtime would not find it
  exit /b 1
)
if not exist "%DEPLOY%\vprobe.addresses.bin" (
  echo FAILED: deploy blob missing - the runtime would not find it
  exit /b 1
)
echo   OK  runtime contract name present

endlocal
exit /b 0
