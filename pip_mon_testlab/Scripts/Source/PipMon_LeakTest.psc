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

Scriptname PipMon_LeakTest

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

; THE LEAK ITSELF. This list is the object of the test: it is a property, so it
; survives function calls, terminal closes, and cell transitions. Every element
; is a live reference the engine cannot reclaim.
;
; FormList, not int[]. It was int[] and every use treated an element as a
; reference, which is a type error at each site: an int[] element is a FormID,
; not an ObjectReference, so `ref.Delete()` was never going to resolve. FormList
; is the container that carries its own size (GetSize/GetAt/AddForm), which is
; exactly what a plain array lacks -- there is no array length intrinsic in FO4
; Papyrus, so an int[] tracker could be appended to but never iterated. AddForm
; also takes a Form, so the cast at the call site is required, not optional.
; Verified by compiling this shape against 2.8.0.4 on 2026-10-01; the signatures
; are from FormList.psc. See ai_context/papyrus_syntax_rules.md section 1.
FormList property LeakTracker auto readonly

; --- spawnables, placed in the test cell ------------------------------------
ObjectReference property ActorSettler auto readonly
ObjectReference property ActorRaider auto readonly
ObjectReference property Workbench auto readonly

; Custom events are raised with the no-argument form. A CustomEvent is declared
; with no parameters and its payload travels in the Var[] passed to
; SendCustomEvent, read back by cast in the receiver's
; Event <SendingScript>.<EventName>(<SendingScript> akSender, Var[] args) handler.
; The call sites below previously carried a payload; it is not carried yet, so
; this is the compile-green shape, not the finished bridge. See
; ai_context/spec/in_game_surface_requirements.json.
CustomEvent LeakTestStarted
CustomEvent LeakTestTick
CustomEvent LeakTestCleaned
Event OnInit()
    ; Snapshot the process working set at baseline. OverseerCLI's save_bloat rule
    ; measures growth from ITS first sample, so this is the TestLab-side
    ; counterpart -- having both lets a human confirm the dashboard's number
    ; against an independent one.
    BytesAtStart = 0.0
    Debug.Notification("PIP-MON LeakTest ready.")
EndEvent

; ---------------------------------------------------------------------------
; Spawn one settler and one raider, so combat/AI script hooks and reference
; cleanup have something to exercise.
; ---------------------------------------------------------------------------
Function SpawnFixtures()
    ; IsValidRef is an SKSE function, absent from every FO4 base script
    ; (compile-verified 2026-10-01). The FO4 test for an unset reference is a
    ; comparison against `None`, which is a real value in this build -- not 0,
    ; which does not compare against an ObjectReference at all ("cannot compare
    ; a objectreference to a int").
    if LeakTracker != None
        ; nothing to do
    endif

    if ActorSettler == None || ActorRaider == None
        Debug.Notification("LeakTest: fixtures not placed. Place a settler and a raider in the cell.")
        return
    endif

    ; Duplicate the placed markers, so each round gets a fresh pair whose
    ; references can be tracked and released individually.
    ; PlaceAtMe's first argument is the Form to place and has NO default --
    ; ObjectReference.psc declares it `Form akFormToPlace` with no default,
    ; while aiCount onwards do default. So the marker is passed as the form, and
    ; the placed Actor is cast: PlaceAtMe returns ObjectReference.
    ObjectReference settlerCopy = ActorSettler.PlaceAtMe(ActorSettler) as Actor
    ObjectReference raiderCopy = ActorRaider.PlaceAtMe(ActorRaider) as Actor
    Debug.Notification("LeakTest: fixtures spawned.")
    Debug.Notification("LeakTest: fixtures spawned.")
EndFunction

; ---------------------------------------------------------------------------
; StartLeak - the main test entry
; ---------------------------------------------------------------------------
Function StartLeak(int aPerTick)
    if Running
        Debug.Notification("LeakTest: already running. Use lk_stop first.")
        return
    endif

    if aPerTick < 1
        aPerTick = ReferencesPerTick
    endif

    Running = true
    CleanedUp = 0
    Debug.Notification("LeakTest: creating " + aPerTick + " references per tick, cap " + MaxReferences)
    SendCustomEvent("LeakTestStarted")
    RunLeakLoop()
EndFunction

; The leak loop, driven by Utility.Wait rather than by a custom-named event.
;
; `Event OnLeakTick()` was a custom event, and a non-Native script cannot declare
; one: "new event onleaktick cannot be defined because the script is not flagged as
; native" -- compile-verified 2026-10-01, and StartTimer does not change it, the
; name is the problem. This script must stay non-Native or it gives up the
; compiler's checking, so the tick becomes a Wait-driven loop instead. That is
; the same shape LoopTest already uses, and it is also the more honest one: the
; loop re-checks its own exit condition every iteration, so a cap or a stop
; request is honoured on the next pass rather than whenever the event system
; gets round to it.
Function RunLeakLoop()
    ; Bounded. A test that can allocate without limit will eventually OOM the
    ; game, and an OOM is a much worse diagnostic failure than a clean refusal.
    if LeakedCount >= MaxReferences
        Debug.Notification("LeakTest: cap reached (" + MaxReferences + "). Run lk_clean to release.")
        SendCustomEvent("LeakTestTick")
        return
    endif

    int created = 0
    while created < ReferencesPerTick
        ; Spawn a lightweight object. The Workbench property is the template; if
        ; it is unassigned, fall back to a settler and then a raider. Any non-none
        ; reference exercises the same handle path, which is all this test needs.
        ;
        ; PlaceAtMe's shape is the Skyrim one, and the coordinate floats are the
        ; tell: the last variant here passed
        ;   PlaceAtMe(Workbench, 64.0, 32.0, 16.0, asObjectReference)
        ; which is six arguments including three coordinate floats and a bare
        ; `asObjectReference` token. FO4's is, from ObjectReference.psc:
        ;   ObjectReference Function PlaceAtMe(Form akFormToPlace, int aiCount = 1,
        ;       bool abForcePersist = false, bool abInitiallyDisabled = false,
        ;       bool abDeleteWhenAble = true) native
        ; So: form first, then the two zeros, then cast the result. The 0 for
        ; abForcePersist is deliberate -- a leaked reference that the engine is
        ; free to persist would be reclaimed differently from one it may not.
        ; PipMonTestFacility.psc line 504 uses exactly this call and compiles.
        ObjectReference spawned = none

        if Workbench != none
            spawned = Workbench.PlaceAtMe(Workbench, 0, 0)
        endif
        if spawned == none && ActorSettler != none
            spawned = ActorSettler.PlaceAtMe(ActorSettler, 0, 0)
        endif
        if spawned == none && ActorRaider != none
            spawned = ActorRaider.PlaceAtMe(ActorRaider, 0, 0)
        endif

        if spawned != none
            ; THE LEAK. Retaining the reference in a property keeps it alive past
            ; this function's scope, so the engine never reclaims it. The list is
            ; the handle; removing from it is the release. AddForm takes a Form,
            ; hence the cast.
            LeakTracker.AddForm(spawned as Form)
            LeakedCount += 1
        endif

        created += 1
    endwhile

    ; Adding to a property list is itself an op, so the loop is not silent --
    ; but the op cost is low compared to the reference churn, which is what
    ; distinguishes a leak from a runaway on the dashboard.

    ; The Wait is what yields the thread back to the VM. It goes at the END of the
    ; body, not the start, so the first tick allocates before yielding.
    Utility.Wait(1.0 / TicksPerSecond)
    SendCustomEvent("LeakTestTick")

    ; Two exits, checked each pass. Running is set false by StopLeak or by a cap
    ; hit, so a stop request is honoured on the next tick rather than whenever
    ; the event system gets to it. Without a second exit this is an infinite
    ; loop in the caller's thread, which is the exact failure LoopTest exists to
    ; provoke.
    if Running == false
        Debug.Notification("LeakTest: stopped after " + LeakedCount + " references.")
        return
    endif
    if LeakedCount >= MaxReferences
        Debug.Notification("LeakTest: cap reached (" + MaxReferences + "). Run lk_clean to release.")
        Running = false
        return
    endif
EndFunction

; ---------------------------------------------------------------------------
; Cleanup - always reachable, and idempotent
; ---------------------------------------------------------------------------
Function Cleanup()
    if CleanedUp
        Debug.Notification("LeakTest: already clean.")
        return
    endif

    int released = 0

    ; Delete the objects first, then drop the references. Doing it in this order
    ; means the list shrink does not try to release handles for objects that
    ; are already gone.
    ;
    ; The old form was LeakTracker.length - 1, and there is no array length
    ; intrinsic in FO4 Papyrus, so it never resolved. FormList carries its own
    ; size, which is the entire reason for the change.
    ; Walking forward and dropping each entry is also safer than walking backward
    ; through a list that is being emptied: RemoveAddedForm shifts the tail down,
    ; so a backward index would skip an element.
    int n = LeakTracker.GetSize()
    int i = 0
    while i < n
        Form f = LeakTracker.GetAt(i)
        ObjectReference ref = f as ObjectReference
        ; Not IsValidRef, which is SKSE. `none` is the value a collected or unset
        ; reference reads as; 0 does not compare against an ObjectReference.
        if ref != none
            ref.Delete()
            released += 1
        endif
        LeakTracker.RemoveAddedForm(f)
        i += 1
    endwhile

    LeakedCount = 0
    CleanedUp = 1
    Running = 0

    Debug.Notification("LeakTest: released " + released + " references. Handle count should fall.")
    SendCustomEvent("LeakTestCleaned")
EndFunction

; ---------------------------------------------------------------------------
; Cross-test: leak + loop together validates save_bloat
; ---------------------------------------------------------------------------
; The save_bloat rule needs BOTH signals. Run LeakTest and LoopTest at the same
; time and the dashboard should raise save_bloat in addition to runaway_loop
; and handle_leak. Neither test alone can produce that finding, which is the
; point of having them as separate components.
Function StartCombinedTest()
    Debug.Notification("Starting combined leak + loop test. Watch for save_bloat.")
    StartLeak(ReferencesPerTick)

    ; LoopTest lives on a different script; its thread is spawned by that
    ; script, so this only flags the shared abort state.
    Utility.Wait(0.1)
    Debug.Notification("Now run the LoopTest terminal in parallel for save_bloat.")
EndFunction

; ---------------------------------------------------------------------------
; Menu
; ---------------------------------------------------------------------------
; ---------------------------------------------------------------------------
; ACTIVATION, not a menu. See PipMon_TerminalTest.psc for why.
;   LeakAction  0 = slow 20/tick  1 = fast 100/tick  2 = spawn fixtures
;               3 = combined     4 = clean up
; ---------------------------------------------------------------------------
int property LeakAction = 0 auto

Event OnMenuOpenCloseEvent(string asMenuName, bool abOpening)
      ; OnMenuOpenCloseEvent is the in-build terminal hook: it is declared on
      ; ScriptObject for this build, and four shipped scripts handle it. It acts
      ; only on the open half of the pair, or closing the terminal would re-run
      ; whatever the property says.
      ;
      ; OnActivate was tried here and this compiler rejected it ("new event
      ; onactivate ... not flagged as native"). An earlier note in this file said
      ; FO4 has no OnActivate at all. That was WRONG: shipped non-Native scripts
      ; such as abAssaultronSelfDestruct.psc declare Event OnActivate and compile.
      ; The verified fact is the narrower one -- this compiler rejected it on these
      ; scripts -- and ScriptObject does not declare it for this build.
    if abOpening
        if LeakAction == 0
            StartLeak(20)
        elseif LeakAction == 1
            StartLeak(100)
        elseif LeakAction == 2
            SpawnFixtures()
        elseif LeakAction == 3
            StartCombinedTest()
        elseif LeakAction == 4
            Cleanup()
        endif
    endif
EndEvent


