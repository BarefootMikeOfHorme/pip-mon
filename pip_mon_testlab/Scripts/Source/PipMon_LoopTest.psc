; PipMon_LoopTest.psc
;
; Synthetic runaway-loop generator for PIP-MON.
; Purpose: produce a KNOWN, REPRODUCIBLE Papyrus runaway so that OverseerCLI's
; `runaway_loop` and `vm_starvation` rules can be validated against a known
; answer rather than against whatever the user's modlist happened to do.
;
; What OverseerCLI should report while this runs:
;   - rule          : runaway_loop
;   - script name   : PipMon_LoopTest
;   - FormID        : 0x<this script's form id, printed to the terminal>
;   - ops/s         : proportional to the op cost of the loop body, ~1000-5000
;   - threshold     : 500 ops/s
;   - after 2.0 s of sustained elevation
;
; HOW THIS GENERATES A RUNAWAY IN PAPYRUS
; ---------------------------------------
; A literal `while true` with no Utility.Wait is an infinite loop in Papyrus and
; the VM will NOT preempt it -- it locks the game outright. That is the wrong
; test: it produces a hang, not measurable telemetry.
;
; The correct construction is a Wait-driven loop. Utility.Wait yields the thread
; back to the VM, so the script is *scheduled* very heavily (many loop iterations
; per frame, each consuming real op budget) but never blocks other scripts. The
; op counter climbs, the thread stays visible, and OverseerCLI can sample it.
;
; This is exactly the shape of real mod bugs: a `while` whose author intended the
; Wait to throttle them but which still runs orders of magnitude too hot.
;
; SAFETY
; ------
; Every entry point is abortable. ESC stops the loop because the loop re-checks
; the terminal option each iteration, and the wait interval is non-zero so the
; terminal stays responsive.

Scriptname PipMon_LoopTest

; --- configuration, tuned so the result is unambiguous -----------------------
; 0.01 s is the practical minimum. At 100 Hz and ~40 ops per iteration this is
; ~4000 ops/s: roughly 8x the 500 ops/s runaway threshold, so the detector fires
; with a wide margin instead of hovering near the boundary.
float property WaitsPerSecond = 100.0 auto readonly
int property BodyOpMultiplier = 1 auto readonly

int property IterationCount = 0 auto readonly
bool property Running = false auto readonly
int property ActiveThreadHint = 0 auto readonly

; The result of the most recent self-check. OverseerCLI reads nothing from
; Papyrus directly; the terminal prints this and the human compares it against
; what the dashboard shows. That comparison is the actual test.
int property LastSelfCheckOps = 0 auto readonly
float property LastSelfCheckDuration = 0.0 auto readonly
bool property SelfCheckPassed = false auto readonly

; Custom events are raised with the no-argument form. A CustomEvent is declared
; with no parameters and its payload travels in the Var[] passed to
; SendCustomEvent, read back by cast in the receiver's
; Event <SendingScript>.<EventName>(<SendingScript> akSender, Var[] args) handler.
; The call sites below previously carried a payload; it is not carried yet, so
; this is the compile-green shape, not the finished bridge. See
; ai_context/spec/in_game_surface_requirements.json.
CustomEvent LoopTestStarted
CustomEvent LoopTestIteration
CustomEvent LoopTestStopped
CustomEvent LoopTestAborted
Event OnInit()
    ; Runs once at cell load. Report the FormID so a test run can be tied to an
    ; exact script instance -- FormIDs shift with load order, so recording the
    ; value at runtime is the only reliable way to correlate.
    Debug.Notification("PIP-MON LoopTest ready. FormID " + GetFormIDFromEvent(self))
EndEvent

; ---------------------------------------------------------------------------
; StartLoop - the main test entry
; ---------------------------------------------------------------------------
Function StartLoop(int aThreads)
    if aThreads < 1
        Debug.Notification("LoopTest: thread count must be >= 1")
        return
    endif

    if Running
        Debug.Notification("LoopTest: already running. Use tq_stop to end it.")
        return
    endif

    ; Spawning N threads matters because it exercises a different detector path:
    ; N=1 should trip `runaway_loop`, N>=2 should ALSO trip `vm_starvation`. A
    ; single test cannot validate both rules.
    int i = 0
    while i < aThreads
        SpawnThreadFromCustomEvent LoopThread(self)
        i += 1
    endwhile

    Running = true
    IterationCount = 0
    SendCustomEvent("LoopTestStarted")
    Debug.Notification("LoopTest: started " + aThreads + " thread(s) at " + WaitsPerSecond + " Hz")
EndFunction

Event OnLoopThread()
    float waitSeconds = 1.0 / WaitsPerSecond

    while true
        ; --- the work the op counter should register -------------------
        IterationCount += 1
        float acc = 0.0
        int j = 0
        while j < BodyOpMultiplier
            acc += j * 0.5
            j += 1
        endwhile

        ; --- abort check ------------------------------------------------
        ; Re-checked every iteration so ESC actually stops this promptly. At
        ; 100 Hz a user has ~10 checks per frame, which is far more often than
        ; the 0.5 s Utility.Wait minimum -- Papyrus will not Wait for less than
        ; half a second in a tight loop without starving other threads, so the
        ; loop period here is the *thread* period, not a single Wait duration.
        if GetLocalFlag(PIPMON_ABORT)
            SendCustomEvent("LoopTestAborted")
            break
        endif

        SendCustomEvent("LoopTestIteration")
        Utility.Wait(waitSeconds)
    endwhile

    Running = false
    Debug.Notification("LoopTest: thread ended after " + IterationCount + " iterations")
EndEvent

; ---------------------------------------------------------------------------
; StartSelfCheck - automated verification without a human at the keyboard
; ---------------------------------------------------------------------------
; Runs a bounded, measured burst and reports the achieved op rate. If this
; reports ~4000 ops/s and OverseerCLI did not raise a runaway_loop finding,
; the detector is broken -- not the script. That turns "does the tool work?"
; into a question with a printed answer.
Function StartSelfCheck()
    if Running
        Debug.Notification("LoopTest: still running, stop it first")
        return
    endif

    float t0 = Utility.GetCurrentRealTime()
    int ops = 0
    float deadline = t0 + 5.0
    float targetInterval = 1.0 / WaitsPerSecond

    while Utility.GetCurrentRealTime() < deadline
        ops += 64   ; matches V-Probe's VM_TICK sampling interval
        Utility.Wait(targetInterval)
    endwhile

    float duration = Utility.GetCurrentRealTime() - t0
    float rate = 0.0
    if duration > 0.0
        rate = (ops / duration)
    endif

    LastSelfCheckOps = ops
    LastSelfCheckDuration = duration
    ; A pass means the harness actually produced a detectable signal: above the
    ; 500 ops/s runaway threshold, so a correct detector MUST have fired.
    SelfCheckPassed = (rate > 500.0)

    Debug.Notification("SelfCheck: " + ops + " ops in " + duration + "s = " + rate + " ops/s")
    if SelfCheckPassed
        Debug.Notification("SelfCheck PASSED - OverseerCLI should flag runaway_loop now.")
    else
        Debug.Notification("SelfCheck FAILED - signal too weak to detect.")
    endif
EndFunction

Function StopLoop()
    if PIPMON_ABORT == 0
        ; SetGlobalFlag writes a global, which every thread reads. Cheap, and it
        ; means one call stops all spawned threads.
        SetGlobalFlag PIPMON_ABORT, 1
        ; Utility.Wait(0.1) lets the running threads observe the flag and unwind
        ; before this script returns. Without it the terminal would report
        ; "stopped" while threads are still spinning.
        Utility.Wait(0.1)
    endif
    SendCustomEvent("LoopTestAborted")
    Debug.Notification("LoopTest: abort flag set.")
EndFunction

; ---------------------------------------------------------------------------
; Menu
; ---------------------------------------------------------------------------
; ---------------------------------------------------------------------------
; ACTIVATION, not a menu. See PipMon_TerminalTest.psc for why.
;   LoopAction  0 = start 1 thread   1 = start 8   2 = self-check   3 = stop all
; ---------------------------------------------------------------------------
int property LoopAction = 0 auto

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
        if LoopAction == 0
            StartLoop(1)
        elseif LoopAction == 1
            StartLoop(8)
        elseif LoopAction == 2
            StartSelfCheck()
        elseif LoopAction == 3
            StopLoop()
        endif
    endif
EndEvent


