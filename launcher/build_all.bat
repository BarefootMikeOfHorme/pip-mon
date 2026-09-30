@echo off
REM ===========================================================================
REM  PIP-MON launcher: builds the pre-flight driver and the load-path fixtures.
REM
REM  Toolchain is pinned to VS 2022 BuildTools explicitly. Two Visual Studio
REM  installations are present on this machine, vswhere does not enumerate the
REM  toolchain, and cl.exe is not on PATH -- so a bare "cl" or a cmake
REM  generator default is not reliable here. VS 18 Community in particular
REM  fails with "could not find any instance of Visual Studio".
REM
REM  Usage:  build_all.bat <output-dir> [launcher-dir]
REM ===========================================================================
setlocal

set VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe
set VCVARS=
if exist "%VSWHERE%" (
  for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
    if exist "%%i\VC\Auxiliary\Build\vcvars64.bat" set VCVARS=%%i\VC\Auxiliary\Build\vcvars64.bat
  )
)
if not defined VCVARS set VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat
call "%VCVARS%" >nul 2>&1
if errorlevel 1 (
  echo FATAL: could not initialise the MSVC toolchain from "%VCVARS%"
  exit /b 1
)

if "%~1"=="" (set OUT=%TEMP%\pipmon_launcher) else (set OUT=%~1)
if "%~2"=="" (set "SRC=%~dp0") else (set "SRC=%~2\")
if not exist "%OUT%" mkdir "%OUT%"

cd /d "%OUT%"

set CFLAGS=/nologo /W4 /WX /permissive- /Zc:__cplusplus /EHsc /std:c++20 /utf-8 /D_CRT_SECURE_NO_WARNINGS /DNOMINMAX /DWIN32_LEAN_AND_MEAN /DUNICODE /D_UNICODE
set INC=/I"%SRC%include" /I"%SRC%include" /I"%SRC%..\vprobe\include"

echo --- pipmon_preflight
cl %CFLAGS% %INC% "%SRC%src\BuildIdentity.cpp" "%SRC%src\ProcessLaunch.cpp" "%SRC%src\SelfTest.cpp" "%SRC%src\main.cpp" /Fe:pipmon_preflight.exe /link bcrypt.lib
if errorlevel 1 (echo MAIN=FAIL & exit /b 1)
echo MAIN=OK

REM The helper target links nothing extra: a suspended process has not loaded
REM user32 yet, so a fixture that imports it drags in a dependency the target
REM has not initialised. kernel32 alone is enough and keeps the test honest.
echo --- pf_helper_target
cl %CFLAGS% "%SRC%tests\test_helper_target.cpp" /Fe:pf_helper_target.exe
if errorlevel 1 (echo TARGET=FAIL & exit /b 1)
echo TARGET=OK

REM The fixtures compile vprobe's REAL ReadySignal.cpp, not a copy. The point
REM of the exercise is that the launcher and the runtime agree on the contract,
REM and a reimplemented stand-in could agree with itself while disagreeing with
REM vprobe. Linking the real source removes that possibility.
set READYSRC="%SRC%..\vprobe\src\ReadySignal.cpp"

echo --- pf_helper_dll (loaded + ready)
cl %CFLAGS% /LD %INC% "%SRC%tests\test_helper_dll.cpp" %READYSRC% /Fe:pf_helper_dll.dll
if errorlevel 1 (echo DLL=FAIL & exit /b 1)
echo DLL=OK

echo --- pf_helper_dll_noready (loaded only -> Degraded)
cl %CFLAGS% /LD %INC% /D PIPMON_DLL_NO_READY=1 "%SRC%tests\test_helper_dll.cpp" %READYSRC% /Fe:pf_helper_dll_noready.dll
if errorlevel 1 (echo DLL_NOREADY=FAIL & exit /b 1)
echo DLL_NOREADY=OK

echo --- pf_helper_dll_noloaded (silent -> timeout)
cl %CFLAGS% /LD %INC% /D PIPMON_DLL_NO_LOADED=1 "%SRC%tests\test_helper_dll.cpp" %READYSRC% /Fe:pf_helper_dll_noloaded.dll
if errorlevel 1 (echo DLL_NOLOADED=FAIL & exit /b 1)
echo DLL_NOLOADED=OK

echo.
REM Same artefact check as the vprobe gate, for the same reason: a green exit
REM code is not evidence that the file on disk is usable. See the warning block
REM in vprobe\build_vprobe.bat for the bug that motivated it.
echo --- verifying artefacts are real PE images ---
powershell -NoProfile -Command ^
  "foreach ($f in @('pipmon_preflight.exe','pf_helper_target.exe','pf_helper_dll.dll','pf_helper_dll_noready.dll','pf_helper_dll_noloaded.dll')) { $p = Join-Path '%OUT%' $f; if (-not (Test-Path $p)) { Write-Host ('FAILED: missing ' + $f); exit 1 }; $b=[IO.File]::ReadAllBytes($p); if ($b[0] -ne 0x4D -or $b[1] -ne 0x5A) { Write-Host ('FAILED: ' + $f + ' is not a PE image'); exit 1 } }; Write-Host '  OK  all 5 launcher artefacts are PE images'"
if errorlevel 1 exit /b 1

echo All targets built in "%OUT%".
echo Run: "%OUT%pipmon_preflight.exe" --self-test
endlocal
