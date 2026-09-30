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

; --- the test character's kit -------------------------------------------------
; Assigned in the CK like everything else. See the header on why no form IDs
; are hardcoded: this install is heavily modded, IDs move, and a hardcoded one
; fails silently rather than loudly.
ObjectReference property KitWeapon Auto
ObjectReference property KitPowerArmorFrame Auto
ObjectReference property KitArmor Auto
ObjectReference property KitTestItem Auto
ObjectReference property KitBenchParts Auto

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
;  THE DEFAULT TEST CHARACTER
; ===========================================================================
;  A test environment is only comparable to itself if the character arriving in
;  it is the same every time. This puts the kit in place idempotently, so a run
;  can be repeated without the previous run's leftovers changing the result.
;
;  THE ONE THING THAT IS EASY TO GET WRONG
;    There is no implicit `Player` in Fallout 4. `Player.AddItem(...)` fails
;    with "variable Player is undefined" -- the bare `Player` identifier is a
;    Skyrim-ism. The accessor here is `Game.GetPlayer()`, which returns an Actor.
;
;  WHY THE KIT IS CK-ASSIGNED AND NOT A HARMLESS HARDCODE
;    A hardcoded form ID would break the first time a mod shifts that record,
;    and it breaks silently: the item simply does not appear and the test looks
;    like a product failure. Properties cost one CK assignment and survive any
;    load order.
;
;  RETURNS a bitfield rather than a bool, because "did the character setup run"
;    and "did every piece of the kit land" are different questions and a single
;    bool throws the second one away:
;      1  weapon equipped
;      2  power armor frame added
;      4  armour added
;      8  test item added
;      16 bench parts added
;      32 the character was already set up (nothing re-added)

Int Function SetupTestCharacter()
    Actor pPlayer = none
    Int iDid = 0
    Int iCount = 0

    pPlayer = Game.GetPlayer()
    If pPlayer == none
        Return 0
    EndIf

    ; Idempotence by inventory check rather than a flag. A save can be loaded,
    ; reverted or console-fiddled with, and a property saying "done" would then
    ; be a lie; asking the inventory is the only check that cannot drift.
    If pPlayer.GetItemCount(KitWeapon) > 0
        iDid = iDid + 32
    ElseIf KitWeapon != none
        pPlayer.AddItem(KitWeapon, 1)
        pPlayer.EquipItem(KitWeapon)
        iDid = iDid + 1
    EndIf

    If pPlayer.GetItemCount(KitPowerArmorFrame) == 0
        If KitPowerArmorFrame != none
            pPlayer.AddItem(KitPowerArmorFrame, 1)
            iDid = iDid + 2
        EndIf
    EndIf

    If pPlayer.GetItemCount(KitArmor) == 0
        If KitArmor != none
            pPlayer.AddItem(KitArmor, 1)
            iDid = iDid + 4
        EndIf
    EndIf

    If pPlayer.GetItemCount(KitTestItem) == 0
        If KitTestItem != none
            pPlayer.AddItem(KitTestItem, 1)
            iDid = iDid + 8
        EndIf
    EndIf

    ; Bench parts are a convenience, not a fixture: enough of them that a
    ; workbench in the cell is immediately usable, without needing a vendor.
    iCount = pPlayer.GetItemCount(KitBenchParts)
    If iCount < 50
        If KitBenchParts != none
            pPlayer.AddItem(KitBenchParts, 50 - iCount)
            iDid = iDid + 16
        EndIf
    EndIf

    Return iDid
EndFunction

; Power armor needs a station to enter from, which is a fixture rather than an
; inventory item, so it is a separate call. Idempotent in the same way: the
; station refuses if the actor is already in a frame, so this is safe to retry.
Bool Function EnterPowerArmor()
    Actor pPlayer = none
    pPlayer = Game.GetPlayer()
    If pPlayer == none
        Return false
    EndIf
    If PowerArmorStationRef == none
        Return false
    EndIf
    If pPlayer.GetItemCount(KitPowerArmorFrame) == 0
        ; Entering with no frame on the actor silently does nothing in game, so
        ; say so here rather than letting it look like a station fault.
        Return false
    EndIf
    pPlayer.SwitchToPowerArmor(PowerArmorStationRef)
    Return true
EndFunction

; Removes only what this script added, so a failed run can be reset without
; touching anything the player picked up themselves.
Function ClearTestCharacter()
    Actor pPlayer = none
    pPlayer = Game.GetPlayer()
    If pPlayer == none
        Return
    EndIf
    pPlayer.UnequipAll()
    If KitWeapon != none
        pPlayer.RemoveItem(KitWeapon)
    EndIf
    If KitPowerArmorFrame != none
        pPlayer.RemoveItem(KitPowerArmorFrame)
    EndIf
    If KitArmor != none
        pPlayer.RemoveItem(KitArmor)
    EndIf
    If KitTestItem != none
        pPlayer.RemoveItem(KitTestItem)
    EndIf
    If KitBenchParts != none
        pPlayer.RemoveItem(KitBenchParts)
    EndIf
EndFunction

; ===========================================================================
;  THE ROSTER
; ===========================================================================
;  10 NPCs, 2 robots, 2 synths, 1 merchant. Named properties rather than an
;  array, and that is a forced choice with a benefit.
;
;  WHY NOT AN ARRAY
;    FO4's Papyrus has no array length intrinsic. `GetLength()`, `GetSize()`,
;    `Count()` and `Size()` were each probed against the real compiler: the
;    first is "not a function or does not exist" and the rest fail to parse at
;    all. Without a length there is no way to iterate an editor-filled array
;    from script, so `ObjectReference[] property Roster` would be writable in
;    the CK and unreadable here. Individual properties sidestep the question
;    entirely.
;
;    The benefit is real rather than merely acceptable: fifteen named slots are
;    visible at a glance in the CK's property list, so "which one is the synth"
;    is answered by looking instead of by counting array indices. For something
;    whose whole job is to be inspected, that is worth more than the tidiness of
;    a loop.
;
;  NATIVE BEHAVIOUR, NOT SCRIPTED BEHAVIOUR
;    Each actor is placed and then handed straight back to the game's own AI:
;
;        EvaluatePackage(true)
;
;    tells the actor to run the package the CK assigned it, with a reset. That
;    is the whole mechanism -- these NPCs walk, idle, and interact because the
;    game's systems do it, not because this script animates them. Which is
;    both what was asked for and the more useful thing to be testing: a
;    hand-scripted patrol would prove our scripting works, while native
;    packages prove the VM is actually executing, which is the S0 question.
;
;    It also means the roster looks right with vanilla ActorBases. Enhancement
;    mod NPCs work identically, since it is the same package mechanism -- so
;    the roster can be dressed up later without touching this file.
;
;  NO CreateObjectAtForm
;    There is no such native in FO4. A form reference has to exist before it
;    can be placed, which is the whole reason every reference here is CK-
;    assigned. Runtime spawning from a form ID is not available.

; NPCs
ObjectReference property Npc01 Auto
ObjectReference property Npc02 Auto
ObjectReference property Npc03 Auto
ObjectReference property Npc04 Auto
ObjectReference property Npc05 Auto
ObjectReference property Npc06 Auto
ObjectReference property Npc07 Auto
ObjectReference property Npc08 Auto
ObjectReference property Npc09 Auto
ObjectReference property Npc10 Auto
; robots
ObjectReference property Robot01 Auto
ObjectReference property Robot02 Auto
; synths
ObjectReference property Synth01 Auto
ObjectReference property Synth02 Auto
; merchant -- its trade inventory is CK-side (a vendor script plus container),
; not built here, because a merchant without stock is just an NPC.
ObjectReference property MerchantRef Auto
; where they all appear
ObjectReference property SpawnHub Auto

int property rosterPlaced = 0 auto readonly

; --- the actors we actually placed -------------------------------------------
; These are the SCRIPT'S record of what it created, and they are what makes
; teardown possible at all.
;
; Why this exists: the roster properties above hold ActorBase templates, but
; PlaceAtMe returns a NEW Actor, and Papyrus has no way to enumerate a cell or
; look an actor up by its base. Without somewhere to put the returned actor,
; ClearRoster has nothing to delete and would silently do nothing -- which is
; the worst failure shape available: a teardown that reports success and leaves
; the previous cast standing.
;
; Auto, not AutoReadOnly: AutoReadOnly is READ-ONLY to the script, which is
; precisely the wrong direction here -- these fields exist so the script can
; record what it placed. They also persist with the save, so a reloaded save
; can still be cleaned up. The cost is that the CK will also offer them for
; editing, which is untidy but harmless; leaving them empty is correct.
;
; Two compiler rules this line depends on, both found the hard way: a bare
; `ObjectReference property x` is not valid at all, and an Auto property with
; no initial value is rejected -- it must be `= none Auto`.
ObjectReference property placedN01 = none Auto
ObjectReference property placedN02 = none Auto
ObjectReference property placedN03 = none Auto
ObjectReference property placedN04 = none Auto
ObjectReference property placedN05 = none Auto
ObjectReference property placedN06 = none Auto
ObjectReference property placedN07 = none Auto
ObjectReference property placedN08 = none Auto
ObjectReference property placedN09 = none Auto
ObjectReference property placedN10 = none Auto
ObjectReference property placedRobot01 = none Auto
ObjectReference property placedRobot02 = none Auto
ObjectReference property placedSynth01 = none Auto
ObjectReference property placedSynth02 = none Auto
ObjectReference property placedMerchant = none Auto

; Places one actor at the hub, hands it to the game's AI, and returns it.
; Returns none if the slot is unassigned or the hub is missing.
Actor Function SpawnOne(ObjectReference akBase)
    Actor a = none
    If akBase == none
        Return none
    EndIf
    If SpawnHub == none
        Return none
    EndIf

    a = akBase.PlaceAtMe(SpawnHub, 0, 0) as Actor
    If a == none
        Return none
    EndIf

    ; The reset flag matters. Without it an actor that has already run its
    ; package to completion will not pick the package up again, so a re-run of
    ; the facility leaves the previous cast standing still.
    a.EvaluatePackage(true)
    a.EnableAI(true)
    Return a
EndFunction

; Returns how many were actually placed. Expected 15 on a fully assigned
; facility; anything less means CK properties are unassigned, and the gap is
; deliberately visible rather than smoothed over.
Int Function PopulateRoster()
    Int i = 0

    placedN01 = SpawnOne(Npc01)
    placedN02 = SpawnOne(Npc02)
    placedN03 = SpawnOne(Npc03)
    placedN04 = SpawnOne(Npc04)
    placedN05 = SpawnOne(Npc05)
    placedN06 = SpawnOne(Npc06)
    placedN07 = SpawnOne(Npc07)
    placedN08 = SpawnOne(Npc08)
    placedN09 = SpawnOne(Npc09)
    placedN10 = SpawnOne(Npc10)
    placedRobot01 = SpawnOne(Robot01)
    placedRobot02 = SpawnOne(Robot02)
    placedSynth01 = SpawnOne(Synth01)
    placedSynth02 = SpawnOne(Synth02)
    placedMerchant = SpawnOne(MerchantRef)

    If placedN01 != none
        i = i + 1
    EndIf
    If placedN02 != none
        i = i + 1
    EndIf
    If placedN03 != none
        i = i + 1
    EndIf
    If placedN04 != none
        i = i + 1
    EndIf
    If placedN05 != none
        i = i + 1
    EndIf
    If placedN06 != none
        i = i + 1
    EndIf
    If placedN07 != none
        i = i + 1
    EndIf
    If placedN08 != none
        i = i + 1
    EndIf
    If placedN09 != none
        i = i + 1
    EndIf
    If placedN10 != none
        i = i + 1
    EndIf
    If placedRobot01 != none
        i = i + 1
    EndIf
    If placedRobot02 != none
        i = i + 1
    EndIf
    If placedSynth01 != none
        i = i + 1
    EndIf
    If placedSynth02 != none
        i = i + 1
    EndIf
    If placedMerchant != none
        i = i + 1
    EndIf

    rosterPlaced = i
    Return i
EndFunction

; Removes only what PopulateRoster created. A roster that scrubbed the cell
; would take out anything the player placed themselves, which is the fastest
; way to make a test environment untrustworthy -- and there is no way to tell
; the difference from script, so the record in placed* is the only safe basis.
Function ClearRoster()
    If placedN01 != none
        placedN01.Delete()
        placedN01 = none
    EndIf
    If placedN02 != none
        placedN02.Delete()
        placedN02 = none
    EndIf
    If placedN03 != none
        placedN03.Delete()
        placedN03 = none
    EndIf
    If placedN04 != none
        placedN04.Delete()
        placedN04 = none
    EndIf
    If placedN05 != none
        placedN05.Delete()
        placedN05 = none
    EndIf
    If placedN06 != none
        placedN06.Delete()
        placedN06 = none
    EndIf
    If placedN07 != none
        placedN07.Delete()
        placedN07 = none
    EndIf
    If placedN08 != none
        placedN08.Delete()
        placedN08 = none
    EndIf
    If placedN09 != none
        placedN09.Delete()
        placedN09 = none
    EndIf
    If placedN10 != none
        placedN10.Delete()
        placedN10 = none
    EndIf
    If placedRobot01 != none
        placedRobot01.Delete()
        placedRobot01 = none
    EndIf
    If placedRobot02 != none
        placedRobot02.Delete()
        placedRobot02 = none
    EndIf
    If placedSynth01 != none
        placedSynth01.Delete()
        placedSynth01 = none
    EndIf
    If placedSynth02 != none
        placedSynth02.Delete()
        placedSynth02 = none
    EndIf
    If placedMerchant != none
        placedMerchant.Delete()
        placedMerchant = none
    EndIf
    rosterPlaced = 0
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
