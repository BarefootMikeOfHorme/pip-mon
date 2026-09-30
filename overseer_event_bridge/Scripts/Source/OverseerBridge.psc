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

Scriptname OverseerBridge : 0x0010 overseereventbridge.esp

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

CustomEvent OverseerPing int
CustomEvent OverseerStatusChanged string
CustomEvent OverseerRequestStackDump int
CustomEvent OverseerRequestTerminate int
CustomEvent OverseerError string

Event OnInit()
    ; Fired once at cell load. OverseerCLI treats the first ping as proof that
    ; the bridge is present, which is how its UI distinguishes "vprobe is
    ; loaded but the bridge is not installed" from "vprobe is not loaded at all".
    ; Those are very different problems with very different fixes.
    SendEventAll OverseerPing(BridgeProtocolVersion)
EndEvent

; ---------------------------------------------------------------------------
; Liveness
; ---------------------------------------------------------------------------
; The native half pings this on a timer. A missed ping means either the bridge
; died or the game froze, and OverseerCLI surfaces that rather than continuing
; to show a frozen dashboard as if it were live.
Function Ping() ;
    LastPingTime = Utility.GetCurrentRealTime()
    PingCount += 1
    SendEventAll OverseerPing(BridgeProtocolVersion)
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
Function RequestTerminate(int aThreadId, bool aForce) ;
    if aForce
        ; Recorded, not performed. The native runner is the only thing allowed
        ; to touch VM thread structures, and only from the main thread.
        TerminationRequests += 1
        PendingTerminationCount += 1
        MarkedForTermination = true
        SendEventAll OverseerRequestTerminate(aThreadId)
        Utility.Wait(0.0)   ; yield so the native runner sees the counter
    else
        ; Soft cancel: ask the owning form to cancel itself. Pure Papyrus, so
        ; it is safe from anywhere.
        ObjectReference owner = GetOwningObjectOfThread(aThreadId)
        if owner != 0
            owner.Cancel()
            SendEventAll OverseerStatusChanged("soft-cancel requested for thread " + aThreadId)
        else
            SendEventAll OverseerError("no owning form for thread " + aThreadId)
        endif
    endif
EndFunction

Function ConsumeTerminationRequests() ;
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
Function RequestStackDump(int aThreadId) ;
    StackDumpRequests += 1
    SendEventAll OverseerRequestStackDump(aThreadId)
    Utility.Wait(0.0)
EndFunction

Function ConsumeStackDumpRequests() ;
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
    SendEventAll OverseerStatusChanged(
        "state: ping=" + PingCount +
        " term=" + TerminationRequests +
        " dump=" + StackDumpRequests +
        " marked=" + MarkedForTermination
    )
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
        SendEventAll OverseerStatusChanged("testlab: runaway loop armed")
    elseif aEventKind == 2
        ; LeakTest started
        SendEventAll OverseerStatusChanged("testlab: handle leak armed")
    elseif aEventKind == 3
        ; LeakTest cleaned up
        SendEventAll OverseerStatusChanged("testlab: references released")
    endif
EndEvent

; ---------------------------------------------------------------------------
; Menu
; ---------------------------------------------------------------------------
Event OnAddToMenu(MenuButton aButton)
    MenuButton "Ping V-Probe" Button 0 id 1
    MenuButton "Publish global state" Button 1 id 2
    MenuButton "Cancel all my scripts" Button 2 id 3
EndEvent

Event OnMenuClick(int aButton)
    if aButton == 1
        Ping()
        DebugNotification "OverseerBridge ping " + PingCount + " (protocol v" + BridgeProtocolVersion + ")"
    elseif aButton == 2
        SendEventAll OverseerPing(BridgeProtocolVersion)
        DebugNotification "Global state published. Check the OverseerCLI log."
    elseif aButton == 3
        ; Script.Cancel() on self is the only universally safe way for a script
        ; to stop itself. Offered here because it is the action a user reaches
        ; for in the console, and having it discoverable prevents them from
        ; reaching for force-kill instead.
        SendEventAll OverseerStatusChanged("bridge: cancel-all requested")
        self.Cancel()
    endif
EndEvent
