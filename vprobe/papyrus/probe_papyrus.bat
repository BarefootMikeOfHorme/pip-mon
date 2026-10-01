@echo off
REM ============================================================================
REM  probe_papyrus.bat -- settle a Papyrus availability question by COMPILING.
REM
REM  WHY THIS EXISTS
REM    ai_context/spec/papyrus_constructs.json marks CustomEvent and SendEvent as
REM    exists_in_fo4: false. That claim makes tools/check_item.py FAIL four of our
REM    own scripts over a construct that is almost certainly valid -- and a gate
REM    that fails correct code is worse than no gate, because the fix people
REM    reach for is switching it off.
REM
REM    Three sources of evidence were consulted and NONE of them settled it:
REM      - the captured FO4 papyrus indexes: zero hits, which is absence of
REM        evidence rather than evidence of absence
REM      - the CK's Data\Scripts\Source: the base scripts ship COMPILED, so
REM        ScriptObject.psc is not readable
REM      - ai_context/papyrus_syntax_rules.md: lists the the other engine-isms that fail,
REM        and does not list these
REM
REM    So it is measured. The compiler is the authority: if PapyrusCompiler.exe
REM    accepts a construct, the construct exists in this build. Cheap -- a compile
REM    is ~90ms, against ~2m15s for an xEdit load, so this is a question worth
REM    answering by running the compiler rather than by reading about it.
REM
REM    Each probe is a separate .psc so a failure names itself. One file with all
REM    the constructs would fail on the first bad one and tell you nothing about
REM    the rest.
REM
REM  USAGE:  vprobe\papyrus\probe_papyrus.bat
REM  EXIT :  0 = every probe compiled (each construct EXISTS)
REM          1 = a probe did not compile (see which, and the compiler's message)
REM ============================================================================
setlocal enabledelayedexpansion

set FO4=C:\Program Files (x86)\Steam\steamapps\common\Fallout 4
set CC=%FO4%\Papyrus Compiler\PapyrusCompiler.exe
set PAPYRUS=%~dp0
set STAGE=%TEMP%\pipmon_probe

if not exist "%CC%" ( echo FAILED: compiler not at "%CC%" & exit /b 1 )
if not exist "%STAGE%" mkdir "%STAGE%" >nul 2>nul

REM The base scripts are the compiler's own dependencies, and they are NOT in
REM Data\Scripts\Source -- that directory holds 12 J-container files. They are in
REM Data\Scripts\Source\Base: 2,422 .psc including ScriptObject.psc, 19,380 B.
REM
REM Getting this wrong is invisible and total. Mirroring the parent staged 12
REM files, every probe then failed with "unable to locate script scriptobject",
REM and a broken harness is indistinguishable from a genuinely-missing construct.
REM That is why the control probe below is not optional.
set BASESRC=%FO4%\Data\Scripts\Source\Base
if not exist "%BASESRC%\ScriptObject.psc" (
  echo FAILED: no ScriptObject.psc under "%BASESRC%"
  echo   Without it every probe fails for the harness's reasons, not the language's.
  exit /b 2
)
robocopy "%BASESRC%" "%STAGE%" *.psc /MIR /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 ( echo FAILED: could not mirror the base scripts & exit /b 2 )
copy /y "%PAPYRUS%papyrus_flags.flg" "%STAGE%\" >nul
del /q "%STAGE%\*.pex" >nul 2>nul
echo   base scripts: %BASESRC% ^(%PAPYRUS%.. exists^)
for /f %%N in ('dir /b /a-d "%STAGE%\*.psc" 2^>nul ^| find /c /v ""') do echo   staged %%N .psc

REM ---------------------------------------------------------------------------
REM  Probe A -- POSITIVE: the FO4 custom-event API, using the names that the
REM  build's own ScriptObject.psc declares (lines 63, 155, 183, 207):
REM      CustomEvent <Name>              declaration, no parameters
REM      SendCustomEvent("Name", kArgs)  raise
REM      RegisterForCustomEvent(o, "N")  subscribe
REM  The first attempt at this probe used the names this build does not declare RegisterForEvent and
REM  SendEvent, so it was testing an API FO4 does not have and would have
REM  "confirmed" the opposite conclusion. The names are the whole question.
REM ---------------------------------------------------------------------------
(
echo Scriptname ProbeFo4CustomEvent
echo ; Mirrors AOScript.psc:50 and :99, a script that ships with this build
echo ; and therefore compiles against this build's own declarations.
echo customEvent EvtA
echo Event OnInit^(^)
echo   RegisterForCustomEvent^(Self, "EvtA"^)
echo   SendCustomEvent^("EvtA"^)
echo EndEvent
echo Event ProbeFo4CustomEvent.EvtA^(ProbeFo4CustomEvent akSender, Var[] args^)
echo EndEvent
echo Bool Function Fire^(^)
echo   SendCustomEvent^("EvtA"^)
echo   Return True
echo EndFunction
) > "%STAGE%\ProbeFo4CustomEvent.psc"

REM ---------------------------------------------------------------------------
REM  Probe B -- the names this build does not declare, expected to FAIL. If this COMPILES then the
REM  harness is not actually checking the language, and every other result in
REM  this run is worthless.
REM  NOTE the parentheses. A missing paren is a SYNTAX error, and a syntax error
REM  looks identical in the output to a missing function -- which would make this
REM  control pass for entirely the wrong reason. That is the second bug this
REM  probe has already caught in itself.
REM ---------------------------------------------------------------------------
(
echo Scriptname ProbeUndeclaredEventNames
echo CustomEvent EvtA
echo Event OnInit^(^)
echo   RegisterForEvent^(Self, "EvtA"^)
echo EndEvent
echo Bool Function Fire^(^)
echo   Var[] kArgs := New Var[1]
echo   SendEvent^(Self, "EvtA", kArgs^)
echo   Return True
echo EndFunction
) > "%STAGE%\ProbeUndeclaredEventNames.psc"

REM ---------------------------------------------------------------------------
REM  Probe C -- menu API, absent from this build, expected to FAIL.
REM  papyrus_syntax_rules.md lists these as the other engine-isms, and ScriptObject.psc in
REM  this build declares no MenuButton at all.
REM ---------------------------------------------------------------------------
(
echo Scriptname ProbeMenu
echo MenuButton "" Button 0 id 0
echo Event OnAddToMenu^(MenuButton aButton^)
echo EndEvent
echo Event OnMenuClick^(int aButton^)
echo EndEvent
) > "%STAGE%\ProbeMenu.psc"

REM ---------------------------------------------------------------------------
REM  Probe D -- timer API, absent from this build, expected to FAIL. Second control.
REM ---------------------------------------------------------------------------
(
echo Scriptname ProbeTimer
echo Function Begin^(^)
echo   Start^(2.0^)
echo   Return True
echo EndFunction
) > "%STAGE%\ProbeTimer.psc"

REM ---------------------------------------------------------------------------
REM  Probe E -- our real surface, as a canary. If THIS fails the environment is
REM  broken in a way that would invalidate every other reading.
REM ---------------------------------------------------------------------------
copy /y "%PAPYRUS%PipMon.psc" "%STAGE%\" >nul 2>nul

REM ---------------------------------------------------------------------------
REM  Run them. want=0 means "this SHOULD compile"; want=-1 means "this should NOT".
REM  A failed compile exits -1 on this compiler, not 1. Measured, not assumed.
REM  the first version of this loop passed 0 for all four probes and so reported
REM  a harness that was working as HARNESS INVALID. A default is a silent lie.
REM ---------------------------------------------------------------------------
set FAILED=0
set BAD=0
call :expect ProbeFo4CustomEvent 0
call :expect PipMon               0
call :expect ProbeUndeclaredEventNames    -1
call :expect ProbeMenu           -1
call :expect ProbeTimer          -1
echo.
echo ============================================================================
if not "%BAD%"=="0" ( echo HARNESS INVALID: a probe that should have failed compiled, so nothing above is trustworthy & exit /b 3 )
if "%FAILED%"=="0" ( echo PROBE SET VALID -- results above are trustworthy & exit /b 0 )
echo PROBE SET VALID, and at least one probe did not compile
exit /b 1

:expect
set "NAME=%1"
set "WANT=%2"
echo.
echo === %NAME%  (expect exit %WANT%) ===
pushd "%STAGE%"
"%CC%" %NAME%.psc -f=papyrus_flags.flg
set RC=!errorlevel!
popd
if exist "%STAGE%\%NAME%.pex" ( set HAVE=1 ) else ( set HAVE=0 )
if "%HAVE%"=="1" del /q "%STAGE%\%NAME%.pex" >nul 2>nul
if "!RC!"=="!WANT!" (
  echo   AS EXPECTED: exit !RC!
) else (
  echo   UNEXPECTED: exit !RC!, wanted %WANT%
  if "!WANT!"=="0" ( set "FAILED=1" ) else ( set "BAD=1" )
)



