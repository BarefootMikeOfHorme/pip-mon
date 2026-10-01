; OverseerBridge.psc
;
; Component 3 of PIP-MON: the in-game bridge.
;
; This is the Papyrus half of a pair. The native half is a plugin script in
; OverseerEventBridge.esp that registers console commands and forwards them to
; V-Probe. This .psc is the scriptable surface those commands map onto.
;
; WHY BOTH HALVES EXIST
; ---------------------
; A console command registered natively can call a Papyrus function, and that is
; the general case: `mon_forcekill` must reach the VM. But Papyrus cannot call
; back into C++ directly, so a script that wants *more* than the native commands
; expose needs a native hook to call it. This file is that entry point.
;
; So the split is:
;   native -> script : console commands and event firing (native calls Papyrus)
;   script -> native : results and bulk actions, via the events below
;
; WHAT THIS DELIBERATELY DOES NOT DO
; ----------------------------------
; It does not talk to V-Probe. It does not know the pipe exists. It has no
; knowledge of op rates, handles, or thresholds. A monitoring tool that also
; decides what is normal is a tool that can be wrong in a way the user cannot
; audit; this file is pure game-side state, and every judgement about it happens
; in OverseerCLI (Rule 4).

Scriptname OverseerBridge

; ---------------------------------------------------------------------------
; Bridge state
; ---------------------------------------------------------------------------
; OverseerCLI needs to know what is currently armed or running so its UI can
; show actionable buttons instead of a generic control panel. These are the
; only shared facts between the game and the dashboard.

int property BridgeProtocolVersion = 1 auto readonly
bool property MarkedForTermination = false auto readonly
int property PendingTerminationCount = 0 auto readonly
float property LastPingTime = 0.0 auto readonly
int property PingCount = 0 auto readonly

; Consumed by the native half on the main thread. This is the Rule 3 boundary
; made concrete: a script sets a flag here, and the main-thread task runner
; reads and acts on it on the next frame. Nothing crosses threads implicitly.
int property TerminationRequests = 0 auto readonly
int property StackDumpRequests = 0 auto readonly

; Custom events are raised with the no-argument form. A CustomEvent is declared
; with no parameters and its payload travels in the Var[] passed to
; SendCustomEvent, read back by cast in the receiver's
; Event <SendingScript>.<EventName>(<SendingScript> akSender, Var[] args) handler.
; The call sites below previously carried a payload; it is not carried yet, so
; this is the compile-green shape, not the finished bridge. See
; ai_context/spec/in_game_surface_requirements.json.
CustomEvent OverseerPing
CustomEvent OverseerStatusChanged
CustomEvent OverseerRequestStackDump
CustomEvent OverseerRequestTerminate
CustomEvent OverseerError
Event OnInit()
    ; Fired once at cell load. OverseerCLI treats the first ping as proof that
    ; the bridge is present, which is how its UI distinguishes "vprobe is
    ; loaded but the bridge is not installed" from "vprobe is not loaded at all".
    ; Those are very different problems with very different fixes.
    SendCustomEvent("OverseerPing")
EndEvent

; ---------------------------------------------------------------------------
; Liveness
; ---------------------------------------------------------------------------
; The native half pings this on a timer. A missed ping means either the bridge
; died or the game froze, and OverseerCLI surfaces that rather than continuing
; to show a frozen dashboard as if it were live.
Function Ping()
    LastPingTime = Utility.GetCurrentRealTime()
    PingCount += 1
    SendCustomEvent("OverseerPing")
EndFunction

; ---------------------------------------------------------------------------
; Rule 3 interface: requests in, deferred to the main thread
; ---------------------------------------------------------------------------
; These are called by the native main-thread runner, never by a raw IPC thread.
; Naming them explicitly is the point: the boundary is visible in the code.

; Ask the VM to stop one script thread gracefully. This is ALWAYS the right
; first action: Script.Cancel() unwinds the script, releasing its locals and
; letting it run any cleanup. Force-kill skips that and can leave quest state
; half-written (see pitfall 4 in docs/ENGINEERING_RULES.md).
Function RequestTerminate(int aThreadId, bool aForce)
    if aForce
        ; Recorded, not performed. The native runner is the only thing allowed
        ; to touch VM thread structures, and only from the main thread.
        TerminationRequests += 1
        PendingTerminationCount += 1
        MarkedForTermination = true
        SendCustomEvent("OverseerRequestTerminate")
        Utility.Wait(0.0)   ; yield so the native runner sees the counter
    else
        ; Soft cancel: ask the owning form to cancel itself. Pure Papyrus, so
        ; it is safe from anywhere.
        ObjectReference owner = GetOwningObjectOfThread(aThreadId)
        if owner != 0
            owner.Cancel()
            SendCustomEvent("OverseerStatusChanged")
        else
            SendCustomEvent("OverseerError")
        endif
    endif
EndFunction

Function ConsumeTerminationRequests()
    ; Drained by the main-thread runner. Returns the count and resets, so a
    ; request can never be executed twice.
    int n = TerminationRequests
    TerminationRequests = 0
    return n
EndFunction

; ---------------------------------------------------------------------------
; Stack dump request
; ---------------------------------------------------------------------------
; Mirrors what the dashboard's "dump stack" button sends. The native side
; re-reads the VM stack ON THE MAIN THREAD and answers with a StackDump frame.
; It cannot be answered from the IPC thread: walking a live VM stack while the
; VM is mid-transition is the deadlock described in pitfall 1.
Function RequestStackDump(int aThreadId)
    StackDumpRequests += 1
    SendCustomEvent("OverseerRequestStackDump")
    Utility.Wait(0.0)
EndFunction

Function ConsumeStackDumpRequests()
    int n = StackDumpRequests
    StackDumpRequests = 0
    return n
EndFunction

; ---------------------------------------------------------------------------
; Safe state access for the native side
; ---------------------------------------------------------------------------
; Papyrus exposes no way to enumerate script properties from C++ generically, so
; the bridge publishes the specific values OverseerCLI needs as plain events.
; This is the "dumb producer" boundary (Rule 4): facts out, no judgement.

Event OnGetGlobalState()
    ; One round-trip: a script name and its FormID. OverseerCLI uses this to
    ; resolve the FormID it sees in telemetry to something a human recognises,
    ; which is the difference between "05005678" and "SkyFC06.esp Script_TCMain".
    SendCustomEvent("OverseerStatusChanged")
        ; The state string belongs in a Var[] payload; the no-argument form is
        ; the compile-green shape and is documented at the top of this file.
EndEvent

; ---------------------------------------------------------------------------
; Test Bench integration
; ---------------------------------------------------------------------------
; The TestLab (pip_mon_testlab) generates load; this script observes it. Keeping
; them separate is what makes the TestLab usable WITHOUT the bridge installed,
; which matters because a user debugging a broken probe should still be able to
; generate a known signal.

Event OnTestLabEvent(int aEventKind)
    if aEventKind == 1
        ; LoopTest started
        SendCustomEvent("OverseerStatusChanged")
    elseif aEventKind == 2
        ; LeakTest started
        SendCustomEvent("OverseerStatusChanged")
    elseif aEventKind == 3
        ; LeakTest cleaned up
        SendCustomEvent("OverseerStatusChanged")
    endif
EndEvent

; ---------------------------------------------------------------------------
; Menu
; ---------------------------------------------------------------------------
; ---------------------------------------------------------------------------
; ACTIVATION, not a menu
; ---------------------------------------------------------------------------
; This used to be the menu API, which this build does not declare (OnAddToMenu / MenuButton / OnMenuClick).
; Fallout 4 Papyrus has no menu system: the compile probe fails on MenuButton
; with "no viable alternative at input '\"\"'", and ScriptObject.psc in this
; build declares no MenuButton at all. The dispatch below is the same logic,
; selected by a property the CK sets, which is the ordinary FO4 idiom.
;
;   BridgeAction  0 = ping   1 = publish global state   2 = cancel all
int property BridgeAction = 0 auto

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
        if BridgeAction == 0
            Ping()
            Debug.Notification("OverseerBridge ping " + PingCount + " (protocol v" + BridgeProtocolVersion + ")")
        elseif BridgeAction == 1
            SendCustomEvent("OverseerPing")
            Debug.Notification("Global state published. Check the OverseerCLI log.")
        elseif BridgeAction == 2
            ; self.Cancel() is the only universally safe way for a script to stop
            ; itself. Offered because it is the action a user reaches for in the
            ; console, and having it discoverable prevents them reaching for
            ; force-kill instead.
            SendCustomEvent("OverseerStatusChanged")
            self.Cancel()
        endif
    endif
EndEvent


