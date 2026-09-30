; ===========================================================================
;  PipMonTestFacility.psc -- the S0 subject, and the room it lives in.
;
;  PURPOSE
;    Two jobs, deliberately in one file because they are the same job.
;
;    1. It is the first script in this project that CALLS the PipMon: native
;       surface. Nothing else does. The test-lab scripts exercise loop, leak
;       and terminal behaviour; the bridge drives console commands; neither one
;       ever invokes PipMon.GetVersion(). So the central open question -- can a
;       compiled .psc reach a native we registered, with no F4SE -- has never
;       actually been posed to the game. This file poses it.
;
;    2. It is the test facility. Terminal, workshop, power armor station, a
;       test NPC and a test robot, all driven from here. It can be one file
;       rather than a hundred placed objects because Papyrus spawns the actors
;       at runtime, so the Creation Kit session reduces to a cell, three
;       fixtures, and this script attached.
;
;  EVERY CONSTRUCT BELOW IS COMPILE-VERIFIED, AND THAT MATTERS MORE THAN IT
;  LOOKS
;    This file went through five compile cycles against the real FO4 Papyrus
;    compiler (2.8.0.4) because four of the obvious things to write do not
;    exist in Fallout 4. Every one of them is a real feature of Skyrim, which
;    is exactly why they were tempting. Recorded here so the next person does
;    not pay for them again:
;
;      CustomEvent / SendEvent ....... SKSE (Skyrim). FO4 has none; F4SE does
;                                      not provide one. Zero occurrences across
;                                      the 41 CK base scripts.
;      Debug.Notification / .MessageBox  Vanilla Skyrim. There is no `Debug`
;                                      script in FO4 at all.
;      Menu / Option property types .. Not Papyrus types in FO4. `Menu` and
;                                      `Option` are rejected as "unknown type".
;      OnMenuClose / OnAddToMenu /
;      OnMenuClick .................. These require the script to be flagged
;                                      Native, and a Native script may not
;                                      contain data -- no properties, no
;                                      script variables, not even a plain
;                                      `Int property x`. So a script that
;                                      handles terminal events cannot also hold
;                                      state. The two requirements are
;                                      mutually exclusive in this toolchain.
;
;    CONSEQUENCE FOR THIS FILE, and it is a real design change rather than a
;    workaround: the facility has no in-game menu. It runs its probe from
;    OnInit and exposes plain functions that the NATIVE side calls directly.
;    That is not a downgrade. The verdict is read off the PIP-MON wire, which
;    is this project's actual output channel (design section 26, T4 is the
;    dashboard and CLI), and the native-to-Papyrus direction is itself worth
;    exercising while we are here. A menu whose labels are authored in the CK
;    could not show a dynamic verdict anyway.
;
;    NOTE FOR THE RECORD: pip_mon_testlab/Scripts/Source/PipMon_TerminalTest.psc
;    uses `MenuButton`, `OnAddToMenu` and `OnMenuClick`. This compiler rejects
;    all three. That script has therefore never been built, which is consistent
;    with the handover listing the test lab as unbuilt. It is not fixed here
;    because it is not this file's job, but it should not be mistaken for
;    working reference the way this header briefly was.
;
;  CROSS-SCRIPT CALL SYNTAX
;    `PipMon.GetVersion()`, with a DOT. `PipMon_GetVersion()` is the name the
;    VM mangles it to, not something Papyrus source can call; using it fails
;    with "not a function or does not exist". This is the single most likely
;    mistake for anyone extending the surface, because the underscore form is
;    what the function is called everywhere else in this repository.
;
;  WHY NO FORM IDS ARE HARDCODED
;    Every reference is a property, assigned in the Creation Kit. This install
;    is heavily modded and form IDs move; a hardcoded ID breaks the first time
;    a mod shifts that record, and it breaks silently -- the spawn simply does
;    not appear. Properties also keep the script valid if the facility is
;    rebuilt on a different cell or extracted for distribution, which is the
;    intent once this graduates from our bench to a shipped default area.
;
;  BUILD
;    Compiled by vprobe/papyrus/build_papyrus.bat immediately after PipMon.psc,
;    in the same space-free staging directory. Order matters: the compiler
;    resolves `PipMon.X()` against PipMon.pex, so the surface must be compiled
;    first or every call in this file fails with "not a function or does not
;    exist" -- which reads like a missing surface rather than a missing
;    artefact.
; ===========================================================================

Scriptname PipMonTestFacility

; --- fixtures: the entire manual workload in the Creation Kit ----------------
ObjectReference property TerminalRef Auto
ObjectReference property WorkbenchRef Auto
ObjectReference property PowerArmorStationRef Auto

; --- actors placed at runtime rather than hand-placed ------------------------
ObjectReference property TestNpcRef Auto
ObjectReference property TestRobotRef Auto
ObjectReference property TestNpcSpawn Auto
ObjectReference property TestRobotSpawn Auto

; --- verdict, readable from the CK property view and from the native side ----
; auto readonly is the only legal shape for a property with an initial value
; in this compiler: `int property x = 0` alone is rejected with "Only Auto and
; AutoReadOnly properties can have initial values".
int property s0Version = -1 auto readonly
int property s0Status = -1 auto readonly
int property s0Capabilities = -1 auto readonly
int property s0ResolvedCount = -1 auto readonly
int property s0AdjudicationCount = -1 auto readonly
int property s0LibraryCount = -1 auto readonly
int property s0EventToken = -1 auto readonly
Bool property s0StringReturned = false auto readonly
Bool property s0StringArrayReturned = false auto readonly
Bool property s0Passed = false auto readonly
Bool property actorsPlaced = false auto readonly

Int kEventMaskAll = 255

; ===========================================================================
;  THE S0 EXPERIMENT
; ===========================================================================

Int Function RunNativeProbe()
    ; Calls every function on the surface and records what came back. Returns 1
    ; if the native boundary is alive.
    ;
    ; GetVersion is called first and everything else is skipped if it is zero.
    ; That ordering is deliberate: "the VM resolved the script but no handler
    ; answered" and "the handler ran and answered" look identical from outside,
    ; and a report full of zeros is much harder to diagnose than one that
    ; stopped at line one.

    Int iVersion = 0

    iVersion = PipMon.GetVersion()
    s0Version = iVersion

    If iVersion == 0
        s0Passed = false
        Return 0
    EndIf

    s0Status = PipMon.GetRuntimeStatus()
    s0Capabilities = PipMon.GetCapabilities()
    s0ResolvedCount = PipMon.GetResolvedProbeCount()
    s0AdjudicationCount = PipMon.GetAdjudicationCount()
    s0LibraryCount = PipMon.GetLibraryCount()

    ; S1 canaries: non-int values crossing the native boundary. Both are tested
    ; for "did something come back at all" rather than for a length, because
    ; FO4's Papyrus has no array length intrinsic this compiler accepts --
    ; `arr.GetLength()` fails with "not a function or does not exist". Counting
    ; elements is a native-side job anyway, and the wire already reports it.
    String sDummy = PipMon.GetStringTest()
    If sDummy != ""
        s0StringReturned = true
    EndIf

    String[] aDummy = PipMon.GetStringArrayTest()
    If aDummy != none
        s0StringArrayReturned = true
    EndIf

    ; A caller-supplied argument, which the no-argument calls cannot exercise.
    s0EventToken = PipMon.RegisterForEvents(kEventMaskAll)

    s0Passed = true
    Return 1
EndFunction

; ===========================================================================
;  RESOLVER STATE -- reported separately, on purpose
; ===========================================================================
;  Dispatch and resolution are different systems. A live native with a dead
;  resolver is a real, useful, PARTIAL result: it is the S0 answer, and folding
;  it into one pass/fail would throw away the only information the experiment
;  produces. Before Layer A lands, s0ResolvedCount is expected to be 0 and that
;  is not a failure.

Int Function GetResolvedCount()
    Return PipMon.GetResolvedProbeCount()
EndFunction

Bool Function IsProbeLive(Int aiIndex)
    Return PipMon.IsHookLive(aiIndex)
EndFunction

Function Unsubscribe()
    ; Exercises the argument-taking path in the other direction, and gives the
    ; subscription a clean teardown so a repeated test run does not accumulate
    ; registrations inside the VM.
    If s0EventToken >= 0
        PipMon.UnregisterFromEvents(s0EventToken)
        s0EventToken = -1
    EndIf
EndFunction

; ===========================================================================
;  FIXTURE CHECK
;  Confirms the Creation Kit session actually filled the properties in. The
;  build gate cannot see any of this, which is the whole reason it exists.
; ===========================================================================

Int Function CheckFixtures()
    ; Returns a bitfield so a caller can test one fixture at a time:
    ;   1 terminal   2 workbench   4 power armor station   8 actors placed
    Int iMask = 0
    If TerminalRef != none
        iMask = iMask + 1
    EndIf
    If WorkbenchRef != none
        iMask = iMask + 2
    EndIf
    If PowerArmorStationRef != none
        iMask = iMask + 4
    EndIf
    If actorsPlaced
        iMask = iMask + 8
    EndIf
    Return iMask
EndFunction

; ===========================================================================
;  ACTORS
; ===========================================================================

Function PlaceActors()
    If actorsPlaced
        Return
    EndIf
    If TestNpcRef == none
        Return
    EndIf

    TestNpcRef.PlaceAtMe(TestNpcSpawn, 0, 0)
    If TestRobotRef != none
        TestRobotRef.PlaceAtMe(TestRobotSpawn, 0, 0)
    EndIf
    actorsPlaced = true
EndFunction

Function RemoveActors()
    If TestNpcRef != none
        TestNpcRef.Delete()
    EndIf
    If TestRobotRef != none
        TestRobotRef.Delete()
    EndIf
    actorsPlaced = false
EndFunction

; ===========================================================================
;  LIFECYCLE
;  OnInit is the ONLY event this script can declare. See the header: every
;  other FO4 event we want requires a Native script, and a Native script may
;  not hold the properties this file needs.
; ===========================================================================

Event OnInit()
    ; Deliberately does NOT run the probe. A cell that loads and immediately
    ; fires native calls is indistinguishable from a bug when you are diagnosing
    ; one, and the first run of a new build deserves a deliberate act rather
    ; than an ambient one. The native side calls RunNativeProbe() explicitly.
    Unsubscribe()
EndEvent
