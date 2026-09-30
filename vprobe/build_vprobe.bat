@echo off
REM ===========================================================================
REM  PIP-MON native build + validation gate.
REM    1. compile vprobe at /W4 /WX   (warnings are errors)
REM    2. link vprobe.dll
REM    3. run the in-DLL self-test via test_harness.exe (game absent)
REM
REM  Usage: build_vprobe.bat
REM  Toolchain pinned to VS 2022 BuildTools; see launcher\build_all.bat for
REM  why that is explicit rather than inherited from the environment.
REM ===========================================================================
setlocal

call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if errorlevel 1 ( echo FATAL: vcvars64 failed & exit /b 1 )

set R=%~dp0..
for %%I in ("%R%") do set R=%%~fI
set Z=%R%\third_party\zydis\zydis-4.1.1
set ZCORE=%Z%\dependencies\zycore
set OUT=%~dp0build
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%OUT%\libs" mkdir "%OUT%\libs"

REM Zydis is required, not optional: the detour layer needs exact x64
REM instruction lengths and RIP-relative detection.
REM
REM Compiled directly with cl rather than through cmake, because cmake cannot
REM see either Visual Studio installation on this machine -- both
REM -G "Visual Studio 17 2022" and -G "Visual Studio 18 2026" fail with
REM "could not find any instance of Visual Studio", because vswhere does not
REM enumerate the toolchain here. Direct cl needs only vcvars64.bat, which
REM build_all.bat already relies on, so the whole project builds without cmake.
REM
REM The four defines are load-bearing:
REM   ZYDIS_STATIC_BUILD / ZYCORE_STATIC_BUILD  static libs, no extra exports.
REM     The Zycore macro is ZYCORE_STATIC_BUILD, NOT ZYAN_STATIC_BUILD; Zycore
REM     renamed it, and the wrong one leaves ZYCORE_EXPORT as dllimport and
REM     fails with "definition of dllimport function not allowed" in String.c.
REM   ZYAN_NO_LIBC     Zydis bundles its own allocator dependencies.
REM   ZYDIS_NO_MARGIN  removes the 64-byte read-ahead margin. This matters for
REM     safety here, not for size: we decode inside the live game's mapped
REM     image and must never touch a page we have not proven readable.
echo === 0/3 building Zydis ===
if not exist "%OUT%\zydis" mkdir "%OUT%\zydis"
REM The doubled backslash in the /Fo path is not a typo and must be kept.
REM cl parses the argument as C-quoted, so a single trailing backslash
REM escapes the closing quote and the whole switch is silently dropped --
REM which surfaces much later as the baffling "D8003: missing source
REM filename" with no mention of paths at all.
cl /nologo /c /O2 /W3 /GS- /DZYDIS_STATIC_BUILD /DZYCORE_STATIC_BUILD ^
   /DZYAN_NO_LIBC /DZYDIS_NO_MARGIN ^
   /I"%Z%\include" /I"%Z%\src" /I"%ZCORE%\include" /I"%ZCORE%\src" ^
   /Fo"%OUT%\zydis\\" "%Z%\src\*.c" "%ZCORE%\src\*.c"
if errorlevel 1 ( echo FAILED: zydis compile & exit /b 1 )
lib /nologo /OUT:"%OUT%\zydis_static.lib" "%OUT%\zydis\*.obj"
if errorlevel 1 ( echo FAILED: zydis lib & exit /b 1 )

set FLAGS=/nologo /std:c++20 /W4 /WX /permissive- /EHsc /Zc:__cplusplus /utf-8 ^
  /DWIN32_LEAN_AND_MEAN /DNOMINMAX /DUNICODE /D_UNICODE /D_CRT_SECURE_NO_WARNINGS ^
  /DZYDIS_STATIC_BUILD /DZYCORE_STATIC_BUILD /DZYAN_NO_LIBC /DZYDIS_NO_MARGIN ^
  /I"%Z%\include" /I"%Z%\src" /I"%ZCORE%\include" /I"%ZCORE%\src"

cd /d "%R%\vprobe\src"
echo === 1/3 compiling (/W4 /WX) ===
REM Same escaped-quote trap as above: the trailing backslash before the
REM closing quote would drop the /Fo switch entirely. Double it.
cl %FLAGS% /c /DVPROBE_EMBEDDED_ADDRESS_DUMP=0 /Fo"%OUT%\\" /I"%R%\vprobe\include" ^
   Detour.cpp DynamicScanner.cpp IPCServer.cpp PapyrusHooks.cpp ^
   VersionConfig.cpp PapyrusApi.cpp SelfTest.cpp ReadySignal.cpp PipmonEntry.cpp main.cpp
if errorlevel 1 ( echo FAILED: compile & exit /b 1 )

echo.
echo === 2/3 linking vprobe.dll ===
if not exist "%OUT%\vprobe.def" copy /y "%~dp0tests\vprobe.def" "%OUT%\vprobe.def" >nul
link /nologo /DLL /OUT:"%OUT%\vprobe.dll" /DEF:"%OUT%\vprobe.def" ^
  "%OUT%\Detour.obj" "%OUT%\DynamicScanner.obj" "%OUT%\IPCServer.obj" ^
  "%OUT%\PapyrusHooks.obj" "%OUT%\VersionConfig.obj" "%OUT%\PapyrusApi.obj" "%OUT%\SelfTest.obj" ^
  "%OUT%\ReadySignal.obj" "%OUT%\PipmonEntry.obj" "%OUT%\main.obj" "%OUT%\zydis_static.lib" ^
  /MACHINE:X64 kernel32.lib user32.lib Psapi.lib
if errorlevel 1 ( echo FAILED: link & exit /b 1 )

echo.
REM The export list lives in a .def rather than relying on __declspec(dllexport)
REM alone, because the F4SE entry point and the self-test entry points are both
REM part of the contract and a missing one is a load-time failure, not a
REM compile error.
echo === building test_harness.exe ===
cl %FLAGS% /Fo"%OUT%\\" /Fe"%OUT%\test_harness.exe" "%~dp0tests\test_harness.cpp"
if errorlevel 1 ( echo FAILED: harness build & exit /b 1 )

echo.
set PIPMON_PSC_PATH=%R%\vprobe\papyrus\PipMon.psc
"%OUT%\test_harness.exe"
set RC=%errorlevel%

echo.
REM The harness prints its own verdict, but its EXIT CODE is what gates. Both
REM are checked deliberately: a harness that prints PASS and returns non-zero
REM has failed, and one that prints FAIL and returns zero has also failed.
REM Trusting either alone is how a gate ends up reporting the wrong thing.
if not "%RC%"=="0" ( echo GATE FAILED - harness returned %RC% & exit /b %RC% )
echo GATE PASSED
echo.
REM ===========================================================================
REM  DO NOT USE ">" IN ANY echo HERE.
REM
REM  `echo vprobe.dll  -> %OUT%\vprobe.dll` does not print a line. cmd parses the
REM  ">" as a redirection operator and writes the TEXT of the echo into
REM  %OUT%\vprobe.dll, replacing the DLL that was just linked.
REM
REM  It fails silently in the worst way: the corruption happens AFTER the
REM  self-test, so the gate prints GATE PASSED and the artefact on disk is 15
REM  bytes of text. The same trap was already fixed in the root build_all.bat
REM  (an `echo >>> FAILED` marker) and then walked into again here, which is
REM  the clearest possible argument for verifying artefacts rather than
REM  trusting a green gate.
REM
REM  Rule for this repo: use "-" or the word "to", never ">", in any echo.
REM ===========================================================================

REM --- verify the artefact, do not trust the exit code ---------------------
REM A successful link says the linker ran. It does not say the file it produced
REM is a PE image. A build gate that reports success without looking at the
REM artefact it produced is a gate that can pass for the wrong reason, which
REM is exactly what happened here once already.
REM NOTE %~dp0 already ends with a backslash, so OUT is "...\vprobe\build" and
REM every use of it must be written as %OUT%\file, never %OUT%file. Getting
REM that wrong yields a check against a path that cannot exist -- which is
REM what happened the first time this verification ran, and it failed loudly,
REM which is the correct outcome for a check like this.
for %%F in ("%OUT%\vprobe.dll") do (
  if not exist "%%~F" ( echo FAILED: vprobe.dll was not produced & exit /b 1 )
  if %%~zF LSS 1024 ( echo FAILED: vprobe.dll is %%~zF bytes - truncated, not an image & exit /b 1 )
)
echo.
echo --- verifying artefact is a real PE image ---
powershell -NoProfile -Command ^
  "$b=[IO.File]::ReadAllBytes('%OUT%\vprobe.dll'); if ($b[0] -ne 0x4D -or $b[1] -ne 0x5A) { Write-Host 'FAILED: vprobe.dll is not a PE image (no MZ header)'; exit 1 } else { Write-Host ('  OK  vprobe.dll is a PE image, ' + $b.Length + ' bytes') }"
if errorlevel 1 exit /b 1

echo.
echo vprobe.dll  built at %OUT%\vprobe.dll
echo To stage into a game, copy vprobe.dll and libs\ into
echo   Data\F4SE\Plugins\vprobe\
endlocal
exit /b 0
