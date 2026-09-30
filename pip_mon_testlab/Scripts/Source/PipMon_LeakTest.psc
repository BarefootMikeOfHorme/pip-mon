; PipMon_LeakTest.psc
;
; Synthetic handle-leak and array-inflation generator for PIP-MON.
;
; Purpose: validate OverseerCLI's `handle_leak` and `save_bloat` rules, which
; need a DIFFERENT signature from the runaway rules:
;
;   runaway_loop : a thread burning ops            -> PipMon_LoopTest
;   handle_leak  : references accumulating over   -> THIS script
;                   time with no op cost
;   save_bloat   : a hot loop AND growing memory  -> BOTH scripts together
;
; Note the asymmetry this creates. A leak is *silent*: it produces almost no
; Papyrus op traffic, so it is invisible to a pure profiler. It shows up in the
; handle count and the working set. That is precisely why PIP-MON watches
; Memory events and not just VM ticks.
;
; HOW A HANDLE LEAK WORKS IN PAPYRUS
; ----------------------------------
; Every reference Papyrus holds to a game object is a handle in the engine's
; reference table. A local Script variable going out of scope releases its
; handles. A reference stored in a script property, an array element, or a
; CustomEvent payload does NOT, for as long as the owning form is loaded.
;
; So the leak here is: create object references, and park them in a global
; array that outlives the function. Deliberate, bounded, and fully reversible.
;
; SAFETY
; ------
; Everything created is tracked in LeakTracker and released by Cleanup(). The
; script refuses to create more than MaxReferences and always offers a cleanup
; path on terminal close. A test tool that can corrupt a save is a bad test tool
; -- see pitfall 4 in docs/ENGINEERING_RULES.md.

Scriptname PipMon_LeakTest : 0x0002 pip_montestlab.esl

; 500 is chosen against the detector's 1500-per-window warn threshold: 1000
; references created in ~5 s clears it with a wide margin, while staying small
; enough that a failed cleanup is recoverable by a reload rather than by an
; emergency save.
int property MaxReferences = 1000 auto readonly
int property ReferencesPerTick = 20 auto readonly
float property TicksPerSecond = 4.0 auto readonly

int property LeakedCount = 0 auto readonly
float property BytesAtStart = 0.0 auto readonly
bool property Running = false auto readonly
bool property CleanedUp = true auto readonly

; THE LEAK ITSELF. This array is the object of the test: it is a global, so it
; survives function calls, terminal closes, and cell transitions. Every element
; is a live reference the engine cannot reclaim.
int property LeakTracker[] auto readonly

; --- spawnables, placed in the test cell ------------------------------------
ObjectReference property ActorSettler auto readonly
ObjectReference property ActorRaider auto readonly
ObjectReference property Workbench auto readonly

CustomEvent LeakTestStarted int
CustomEvent LeakTestTick int
CustomEvent LeakTestCleaned int

Event OnInit()
    ; Snapshot the process working set at baseline. OverseerCLI's save_bloat rule
    ; measures growth from ITS first sample, so this is the TestLab-side
    ; counterpart -- having both lets a human confirm the dashboard's number
    ; against an independent one.
    BytesAtStart = 0.0
    DebugNotification "PIP-MON LeakTest ready."
EndEvent

; ---------------------------------------------------------------------------
; Spawn one settler and one raider, so combat/AI script hooks and reference
; cleanup have something to exercise.
; ---------------------------------------------------------------------------
Function SpawnFixtures() ;
    if IsValidRef(LeakTracker) == 0
        ; nothing to do
    endif

    if ActorSettler == 0 || ActorRaider == 0
        DebugNotification "LeakTest: fixtures not placed. Place a settler and a raider in the cell."
        return
    endif

    ; Duplicate the placed markers, so each round gets a fresh pair whose
    ; references can be tracked and released individually.
    ActorSettler.PlaceAtMe()
    ActorRaider.PlaceAtMe()
    DebugNotification "LeakTest: fixtures spawned."
EndFunction

; ---------------------------------------------------------------------------
; StartLeak - the main test entry
; ---------------------------------------------------------------------------
Function StartLeak(int aPerTick) ;
    if Running
        DebugNotification "LeakTest: already running. Use lk_stop first."
        return
    endif

    if aPerTick < 1
        aPerTick = ReferencesPerTick
    endif

    Running = true
    CleanedUp = 0
    DebugNotification "LeakTest: creating " + aPerTick + " references per tick, cap " + MaxReferences
    SendEventAll None
EndFunction

Event OnLeakTick()
    ; Bounded. A test that can allocate without limit will eventually OOM the
    ; game, and an OOM is a much worse diagnostic failure than a clean refusal.
    if LeakedCount >= MaxReferences
        DebugNotification "LeakTest: cap reached (" + MaxReferences + "). Run lk_clean to release."
        SendEventAll None
        return
    endif

    int created = 0
    while created < ReferencesPerTick
        ; Spawn a lightweight object. Form 000B15A2 is a metal crafter's bench
        ; placeholder in the TestLab cell; if it is absent, fall back to the
        ; bench, and if that is absent too, fall back to the actors. Any
        ; non-none reference exercises the same handle path.
        ObjectReference spawned = 0

        if Workbench != 0
            spawned = Workbench.PlaceAtMe(Workbench, 64.0, 32.0, 16.0, asObjectReference)
        endif
        if spawned == 0 && ActorSettler != 0
            spawned = ActorSettler.PlaceAtMe()
        endif
        if spawned == 0 && ActorRaider != 0
            spawned = ActorRaider.PlaceAtMe()
        endif

        if spawned != 0
            ; THE LEAK. Appending to a global array keeps the reference alive
            ; past this function's scope, so the engine never reclaims it. The
            ; array is the handle; removing it is the release.
            LeakTracker.Insert(spawned)
            LeakedCount += 1
        endif

        created += 1
    endwhile

    ; Inserting to a global array is itself an op, so the thread is not silent --
    ; but the op cost is low compared to the reference churn, which is what
    ; distinguishes a leak from a runaway on the dashboard.
    Utility.Wait(1.0 / TicksPerSecond)
EndFunction

; ---------------------------------------------------------------------------
; Cleanup - always reachable, and idempotent
; ---------------------------------------------------------------------------
Function Cleanup() ;
    if CleanedUp
        DebugNotification "LeakTest: already clean."
        return
    endif

    int released = 0

    ; Delete the objects first, then drop the references. Doing it in this order
    ; means the array shrink does not try to release handles for objects that
    ; are already gone.
    int i = LeakTracker.length - 1
    while i >= 0
        ObjectReference ref = LeakTracker[i]
        if IsValidRef(ref)
            ref.Delete()
            released += 1
        endif
        i -= 1
    endwhile

    LeakTracker.Clear()
    LeakedCount = 0
    CleanedUp = 1
    Running = 0

    DebugNotification "LeakTest: released " + released + " references. Handle count should fall."
    SendEventAll LeakTestCleaned(released)
EndFunction

; ---------------------------------------------------------------------------
; Cross-test: leak + loop together validates save_bloat
; ---------------------------------------------------------------------------
; The save_bloat rule needs BOTH signals. Run LeakTest and LoopTest at the same
; time and the dashboard should raise save_bloat in addition to runaway_loop
; and handle_leak. Neither test alone can produce that finding, which is the
; point of having them as separate components.
Function StartCombinedTest() ;
    DebugNotification "Starting combined leak + loop test. Watch for save_bloat."
    StartLeak(ReferencesPerTick)

    ; LoopTest lives on a different script; its thread is spawned by that
    ; script, so this only flags the shared abort state.
    Utility.Wait(0.1)
    DebugNotification "Now run the LoopTest terminal in parallel for save_bloat."
EndFunction

; ---------------------------------------------------------------------------
; Menu
; ---------------------------------------------------------------------------
Event OnAddToMenu(MenuButton aButton)
    MenuButton "Start leaking (20 refs / tick)" Button 0 id 1
    MenuButton "Start fast leak (100 refs / tick)" Button 1 id 2
    MenuButton "Spawn fixtures (settler + raider)" Button 2 id 3
    MenuButton "Combined test (leak; run LoopTest too)" Button 3 id 4
    MenuButton "CLEAN UP - release all references" Button 4 id 5
EndEvent

Event OnMenuClick(int aButton)
    if aButton == 1
        StartLeak(20)
    elseif aButton == 2
        StartLeak(100)
    elseif aButton == 3
        SpawnFixtures()
    elseif aButton == 4
        StartCombinedTest()
    elseif aButton == 5
        Cleanup()
    endif
EndEvent

Event OnTimer()
    ; Closing the terminal must not leave a leak running: the whole point of the
    ; TestLab is that a test can be stopped by walking away from it.
    int aButton = GetEventParameter(MenuClickEvent, "MenuItemID") as int
    if aButton == 0 && Running
        DebugNotification "LeakTest: terminal closed, releasing references."
        Cleanup()
    endif
EndEvent
