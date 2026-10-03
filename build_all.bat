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
REM    6. retrieval   the knowledge base invariants
REM
REM  A failure in any stage stops the run. Non-zero exit means something is
REM  broken -- do not read the summary below and move on.
REM
REM  STAGE 6 IS NOT COSMETIC. Every rule this project relies on about its own
REM  knowledge base was at some point true only because someone remembered it.
REM  System documents outranked the domain files they quoted; configuration
REM  came back as search hits; an objective went missing and a whole component
REM  became invisible. Each shipped with every other stage green, because no
REM  stage looked. This one looks.
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
echo #  1/6  vprobe -- the in-process runtime
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
echo #  2/6  papyrus -- the PipMon: API surface (.psc to .pex)
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
echo #  3/6  launcher -- pre-flight and core load path
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
echo #  4/6  python -- analysis tier
echo ############################################################
pushd "%R%overseer_cli"
python -m pytest -q
if errorlevel 1 ( set FAILED=1 & echo [FAIL] python tests )
popd

echo.
echo ############################################################
echo #  5/6  rust -- protocol crate
echo ############################################################
pushd "%R%overseer_cli\rust\vlink-protocol"
cargo test -q
if errorlevel 1 ( set FAILED=1 & echo [FAIL] rust tests )
popd

echo.
echo ############################################################
echo #  6/6  retrieval -- knowledge base invariants
echo ############################################################
REM Self-alignment runs FIRST, because validating a stale derivation produces a
REM green gate that means nothing. Repair is limited to things that are DERIVED:
REM a function of on-disk state, where re-deriving cannot lose anything. The
REM gate also names what it REFUSES to repair -- the artifact baseline, the
REM authority tiers, the compat statuses -- because a gate that repairs its own
REM signals is not a gate. The refusals are printed on every run on purpose.
python "%R%tools\selfalign.py" --repair
if errorlevel 1 ( set FAILED=1 & echo [FAIL] self-align )

REM The index is a derived artifact, so it is gitignored rather than committed.
REM Asserting that here as well, because a committed index is a second,
REM silently diverging copy of the truth and gitignore alone is a convention.
git check-ignore -q rag/index.sqlite3
if errorlevel 1 ( set FAILED=1 & echo [FAIL] retrieval index is committed and must be derived )

python "%R%tools\rag_selftest.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] retrieval selftest )

REM Specs are the machine-readable half of the knowledge base. Unvalidated JSON
REM drifts from both the prose and the code, and a spec that claims coverage it
REM does not have is worse than no spec. spec_lint checks shape, types and
REM honesty -- including that a component whose own status says it is unproven
REM does not claim gate coverage. It has already caught exactly that once.
python "%R%tools\spec_lint.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] spec lint )

REM The artifact gate is the one that knows WHAT is passing through. Stages 1-5
REM ask "does it compile". This asks "is the thing being compiled something
REM Fallout 4 can actually run", using the detect lists in ai_context/spec. Known
REM pre-existing violations are reported as acknowledged and listed; only a NEW
REM construct in a NEW place fails the build. Run with --write-baseline only
REM after deliberately reviewing the current findings.
python "%R%tools\artifact_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] artifact gate )

REM Does the artifact gate actually DISCRIMINATE? A green artifact gate above
REM only means no detect list matched. It cannot tell the difference between a
REM list that catches the thing and a list that has quietly stopped matching --
REM and the "array length intrinsic" entry shipped a 'Count' stem of
REM 'array.Count', which word_hit() matches literally, so it fired only on a
REM variable named 'array' and let Roster.Count through. Green gate, spec
REM reading correctly, nothing enforced. This stage asserts the behaviour on a
REM synthetic file in a temp dir, so a stem that matches nothing and an
REM exemption that is one step too wide both fail here instead of passing quietly.
python "%R%tools\gate_selftest.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] gate self-test )

REM Per-side status. Every other stage is GLOBAL, which is its weakness: a green
REM gate says the thing builds, not that any side of the work functions. Two of
REM three sides are currently unavailable while the gate is green. This stage
REM reports the split, so "everything passes" can never be mistaken for "the
REM engine side works".
python "%R%tools\side_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] side gate )

REM Surface inventory: a promise that names a path which is not there is worse
REM than no inventory, so every claimed path is confirmed to exist.
python "%R%tools\surfaces_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] surfaces gate )

REM Per-side ownership: knowledge exists, excluded is really excluded, and
REM documented gaps have not quietly stopped being gaps.
python "%R%tools\ownership_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] ownership gate )

REM ---------------------------------------------------------------------------
REM Three gates added 2026-10-03 by a delegated agent, wired here by the
REM coordinator because build_all.bat was not the agent's file to change.
REM
REM Each exists because a MISSING CHECK, not a missing fix, let a defect
REM through: the changelog drifted twice, an undeclared spec field survived a
REM clean revert, and surfaces.json advertised a verb that existed in no code
REM path for eight months.
REM
REM They run in the default, non-strict mode on purpose. Each carries a table
REM of KNOWN open defects with tracking ids, reported rather than failed,
REM because a permanently red gate is decoration and gets ignored. Drain the
REM tables with --strict; each entry names its fix.
REM ---------------------------------------------------------------------------
REM An entry may not use a field its kind does not declare. Found by reverting
REM the schema commit alone: clean revert, spec_lint green, spec layer lying.
python "%R%tools\entry_field_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] entry field gate )

REM Claimed / advertised / implemented verb sets must be equal. A verb is not
REM a path, so surfaces_gate could not see this class of drift.
python "%R%tools\verb_parity_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] verb parity gate )

REM Every status reaching Emit must have a key in $EXIT, and $EXIT, caps and
REM the published contract must agree. An unknown status used to exit 0.
python "%R%tools\exit_table_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] exit table gate )

REM The changelog is the walkable index; a commit message is per-commit. This
REM gate exists because that index drifted twice before the gate existed.
python "%R%tools\changelog_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] changelog gate )

REM The replacement map cannot quietly change its mind. A status flipped from
REM REJECTED to PLANNED turns a measured refusal into an aspiration and
REM nothing else notices. Also fails a refusal with no reason given.
python "%R%tools\compat_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] compat gate )

REM Goal coverage: build integrity is not goal alignment. goal_alignment.md
REM records that six goals have NO check at all. This reports per goal whether
REM any check can be attributed, so the hole is visible rather than a footnote.
REM Fails only on regression from its recorded baseline - a gate red on
REM arrival teaches people to ignore it.
python "%R%tools\goal_coverage_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] goal coverage gate )

REM The FO4 Papyrus index: every negative-table claim measured against the
REM 7,854 shipped base scripts, so "FO4 has no such function" is a finding
REM rather than a memory.
python "%R%tools\papyrus_index_gate.py"
if errorlevel 1 ( set FAILED=1 & echo [FAIL] papyrus index gate )

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
