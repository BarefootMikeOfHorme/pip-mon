@echo off
REM Build the READ-ONLY live-process signature checker.
REM
REM SAFETY: this tool is only useful if it cannot harm the target, so the
REM access mask in rtsig.cpp is a deliberate design decision and not a detail.
REM If anyone adds VM_WRITE, VM_OPERATION or CREATE_THREAD to it, it stops
REM being a diagnostic and becomes an injector. Do not.
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if errorlevel 1 ( echo FATAL: vcvars64 failed & exit /b 1 )

set OUT=%~dp0build
if not exist "%OUT%" mkdir "%OUT%"

cl /nologo /W4 /WX /permissive- /Zc:__cplusplus /EHsc /std:c++20 /utf-8 ^
   /D_CRT_SECURE_NO_WARNINGS /DNOMINMAX /DWIN32_LEAN_AND_MEAN /DUNICODE /D_UNICODE ^
   "%~dp0rtsig.cpp" /Fe:"%OUT%\rtsig.exe"
if errorlevel 1 ( echo FAILED: compile & exit /b 1 )

REM Artefact check, same as every other gate here. A green exit code is a
REM claim about the compiler, not about the filesystem.
powershell -NoProfile -Command ^
  "$p='%OUT%\rtsig.exe'; if (-not (Test-Path $p)) { exit 1 }; $b=[IO.File]::ReadAllBytes($p); if ($b[0] -ne 0x4D) { Write-Host 'FAILED: not a PE'; exit 1 }"
if errorlevel 1 exit /b 1
echo rtsig.exe built
endlocal
exit /b 0
