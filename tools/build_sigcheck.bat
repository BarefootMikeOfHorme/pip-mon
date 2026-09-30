@echo off
REM Build the static AOB signature checker. Read-only: it maps the game
REM executable and scans it. It does not launch or attach to the game.
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if errorlevel 1 ( echo FATAL: vcvars64 failed & exit /b 1 )

set R=%~dp0..
for %%I in ("%R%") do set R=%%~fI
set OUT=%~dp0build
if not exist "%OUT%" mkdir "%OUT%"

REM Links the launcher's BuildIdentity.cpp rather than re-implementing PE
REM parsing. See the comment at the top of sigcheck.cpp for why a second
REM parser is a defect, not a convenience.
cl /nologo /W4 /WX /permissive- /Zc:__cplusplus /EHsc /std:c++20 /utf-8 ^
   /D_CRT_SECURE_NO_WARNINGS /DNOMINMAX /DWIN32_LEAN_AND_MEAN /DUNICODE /D_UNICODE ^
   /I"%R%\launcher\include" ^
   "%~dp0sigcheck.cpp" "%R%\launcher\src\BuildIdentity.cpp" ^
   /Fe:"%OUT%\sigcheck.exe" /link bcrypt.lib
if errorlevel 1 ( echo FAILED: compile & exit /b 1 )

REM Same artefact check as the other gates: never trust a green exit code on
REM its own. See the warning block in vprobe\build_vprobe.bat.
powershell -NoProfile -Command ^
  "$p='%OUT%\sigcheck.exe'; if (-not (Test-Path $p)) { exit 1 }; $b=[IO.File]::ReadAllBytes($p); if ($b[0] -ne 0x4D) { Write-Host 'FAILED: not a PE'; exit 1 }"
if errorlevel 1 exit /b 1
echo sigcheck.exe built
endlocal
exit /b 0
