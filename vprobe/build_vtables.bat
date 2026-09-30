@echo off
REM ===========================================================================
REM  build_vtables.bat - verify every vtable target in Signatures.hpp against
REM  the real game executable, and fail the build on any disagreement.
REM
REM  WHY THIS IS IN THE GATE
REM    Signatures.hpp declares, for each vtable target, how many method slots
REM    the table has. That number is a load-bearing safety property, not
REM    documentation. The validator trusts it: it reads that many consecutive
REM    pointers and requires a majority to point into executable code. Get it
REM    wrong in one direction and the validator walks off the end of the table
REM    and treats the NEXT class's CompleteObjectLocator as a method slot, then
REM    detours into an unrelated interface. Get it wrong in the other and real
REM    slots at the tail are silently dropped.
REM
REM    Those numbers used to be a uniform, hand-written 8 for every target,
REM    and nothing compared them to the binary. The gate was green, the report
REM    was green, and the numbers were a fiction. That is the same failure
REM    class as the stale-blob guard next door: a claim nothing measures.
REM
REM    So this measures them. tools/measure_vtable.py reads the real tables out
REM    of Fallout4.exe, confirms each one's RTTI class name against the name it
REM    was looked up by, walks to the next class's locator to find the true
REM    extent, and exits non-zero if any declared count disagrees.
REM
REM    The class-name confirmation matters as much as the count. A vtable
REM    address in the database and a mangled name emitted by the compiler are
REM    independent sources; their agreeing is evidence rather than tautology.
REM
REM  Usage: build_vtables.bat
REM  Skip:  set PIPMON_SKIP_LIBBIN=1, or simply have no game installed.
REM ===========================================================================
setlocal

set R=%~dp0..
for %%I in ("%R%") do set R=%%~fI
set SIGS=%R%\vprobe\include\Signatures.hpp
set INI=%R%\vprobe\libs\fo4_1_11_240.addresses.txt
set TOOL=%R%\tools\measure_vtable.py

if "%PIPMON_SKIP_LIBBIN%"=="1" (
  echo SKIP: PIPMON_SKIP_LIBBIN=1
  endlocal & exit /b 0
)

if not exist "%SIGS%" (
  echo FAILED: signature table not found: %SIGS%
  exit /b 1
)

if not exist "%INI%" (
  echo FAILED: address database not found: %INI%
  exit /b 1
)

REM The default Steam path contains "(x86)". cmd tracks parenthesis nesting
REM inside if-blocks even within a quoted string, so the block closes early and
REM the script dies with "was unexpected at this time", blaming the path
REM instead of the real cause. Any path with parentheses is tested with goto
REM labels, never with a block. Same constraint as build_libbin.bat.
set "FO4EXE=C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Fallout4.exe"
if exist "%FO4EXE%" goto :have_exe
set "FO4EXE=C:\Games\Fallout 4\Fallout4.exe"
if exist "%FO4EXE%" goto :have_exe

echo SKIP: no Fallout4.exe found; vtable extents cannot be measured without it.
echo       This is a skip and NOT a pass. On a machine with the game, a count
echo       that disagrees with the binary is a build failure.
endlocal & exit /b 0

:have_exe

REM The tool's own refusal tests run first and unconditionally. They are cheap,
REM they need no game, and they are what makes the measurement below worth
REM anything: a vtable measurer that silently mis-parses a section table or
REM mis-decodes a jump stub would otherwise report confident nonsense.
echo === measuring the tool before trusting it ===
python "%TOOL%" --self-test
if errorlevel 1 ( echo FAILED: measure_vtable.py self-test & exit /b 1 )

echo === measuring declared vtables against the real binary ===
python "%TOOL%" --exe "%FO4EXE%" --ini "%INI%" --signatures "%SIGS%"
if errorlevel 1 (
  echo FAILED: vtable verification errored - see above.
  echo         The tool refuses to report when its own control does not
  echo         measure correctly, so this is a tooling problem, not a
  echo         disagreement about slot counts.
  exit /b 1
)
if errorlevel 2 (
  echo FAILED: a declared vtable slot count disagrees with the binary.
  echo         The boundary evidence for each is printed above, so the
  echo         correct number can be read off the real table rather than
  echo         guessed. Do not relax the check to make the build pass.
  exit /b 1
)

echo   OK  every declared vtable matches the binary
endlocal & exit /b 0
