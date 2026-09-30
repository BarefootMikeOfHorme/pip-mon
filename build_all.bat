@echo off
REM ===========================================================================
REM  PIP-MON: builds and validates EVERYTHING, in one command.
REM
REM  Usage:  build_all.bat   (no arguments; outputs beside each component)
REM
REM  Runs, in order:
REM    1. vprobe      the in-process runtime  (/W4 /WX, links, self-tests)
REM    2. papyrus     the PipMon: API surface (.psc to .pex; needs the CK)
REM    3. launcher    pre-flight + core load path, plus its fixtures
REM    4. python      the analysis tier test suite
REM    5. rust        the protocol crate
REM
REM  A failure in any stage stops the run. Non-zero exit means something is
REM  broken -- do not read the summary below and move on.
REM
REM  The papyrus stage is the one exception: it reports SKIP and continues when
REM  the Creation Kit is not installed, because a developer without it must
REM  still be able to build and test the native side. It never claims success
REM  with a stale .pex -- that case is a FAIL, not a skip.
REM
REM  Toolchain is pinned to VS 2022 BuildTools. Two Visual Studio installs
REM  exist on this machine and vswhere enumerates neither, so vcvars64.bat is
REM  called explicitly and cmake is not used for native code at all.
REM ===========================================================================
setlocal enabledelayedexpansion
set R=%~dp0
for %%I in ("%R%") do set R=%%~fI
set FAILED=0

echo.
REM NOTE: failure markers are written as "[FAIL]" rather than ">>> FAILED".
REM cmd treats an unquoted ">" as a redirection operator, so `echo >>> FAILED`
REM is a PARSE error that kills the whole script at the first such line, with a
REM message that points nowhere near the real problem.

echo ############################################################
echo #  1/5  vprobe -- the in-process runtime
echo ############################################################
call "%R%vprobe\build_vprobe.bat"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] vprobe build )

REM The address blob is DERIVED from the INI, and nothing else keeps the two in
REM step. This runs inside the vprobe step because it produces a vprobe artefact
REM and fails the same way: a blob that no longer matches its INI is a build
REM failure, because the runtime would otherwise serve stale addresses into
REM detour installation. Skip with PIPMON_SKIP_LIBBIN=1 where there is no game.
echo.
echo --- address blob (derived from the INI) ---
call "%R%vprobe\build_libbin.bat"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] address blob )

REM Same class of problem, one layer up. Signatures.hpp declares how many slots
REM each vtable target has, and the runtime validator trusts that number, so a
REM wrong one sends a detour into whatever function follows the table. The
REM counts were a hand-written uniform 8 that nothing measured. This measures
REM them against the real executable, confirms each table's RTTI class name,
REM and fails on any disagreement. Skip with PIPMON_SKIP_LIBBIN=1.
echo.
echo --- vtable targets (declared vs. the real binary) ---
call "%R%vprobe\build_vtables.bat"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] vtable targets )

echo.
echo ############################################################
echo #  2/5  papyrus -- the PipMon: API surface (.psc to .pex)
echo ############################################################
REM The Papyrus surface is gated here for the same reason the native table is
REM tested against the .psc: if PipMon.psc and PapyrusApi.cpp can drift, the
REM script an author writes calls a function nobody registered and the game
REM reports it hours later. Compiling it in the gate is what makes the .pex
REM and the C++ registry one artefact set rather than two that happen to
REM agree today.
REM
REM This step needs the Creation Kit (Steam app 1946160). It is allowed to be
REM absent: the toolchain check inside reports SKIP and does not fail the gate,
REM because a developer without the CK installed should still be able to build
REM and test the native side. What must never happen is a build that CLAIMS
REM success while the .pex is stale.
call "%R%vprobe\papyrus\build_papyrus.bat"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] papyrus build )

echo.
echo ############################################################
echo #  3/5  launcher -- pre-flight and core load path
echo ############################################################
if not exist "%R%launcher\build" mkdir "%R%launcher\build"
call "%R%launcher\build_all.bat" "%R%launcher\build" "%R%launcher"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] launcher build ) else (
  echo.
  echo --- launcher self-test ---
  "%R%launcher\build\pipmon_preflight.exe" --self-test
  if errorlevel 1 ( set FAILED=1 & echo [FAIL] launcher self-test )
)

echo.
echo ############################################################
echo #  4/5  python -- analysis tier
echo ############################################################
pushd "%R%overseer_cli"
python -m pytest -q
if errorlevel 1 ( set FAILED=1 & echo [FAIL] python tests )
popd

echo.
echo ############################################################
echo #  5/5  rust -- protocol crate
echo ############################################################
pushd "%R%overseer_cli\rust\vlink-protocol"
cargo test -q
if errorlevel 1 ( set FAILED=1 & echo [FAIL] rust tests )
popd

echo.
echo ############################################################
if %FAILED% EQU 0 (
  echo #  ALL GATES PASSED
) else (
  echo #  SOMETHING FAILED -- see above
)
echo ############################################################
echo.
echo Artefacts:
echo   vprobe.dll     %R%vprobe\build\vprobe.dll
echo   preflight      %R%launcher\build\pipmon_preflight.exe
exit /b %FAILED%
