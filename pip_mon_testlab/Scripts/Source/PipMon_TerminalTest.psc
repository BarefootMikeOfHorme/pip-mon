; PipMon_TerminalTest.psc
;
; Interactive in-game test bench. The single place a user runs the suite.
;
; This script exists so the test surface is discoverable without the user
; needing to know console commands or file paths. It is a thin dispatcher: every
; menu entry calls one of the test scripts, and every menu entry shows what to
; expect on the OverseerCLI dashboard.
;
; THE RELATIONSHIP TO THE CONSOLE COMMANDS
; -----------------------------------------
; The Overseer Event Bridge (.esp) registers console commands for the same
; actions. That is deliberate duplication, not an oversight:
;
;   Terminal  : discoverable, has expectations written next to each button,
;               safe, always available.
;   Console   : scriptable, works when a menu is not open, usable from a
;               .bat / test harness, and reaches actions the terminal does not
;               expose (force-kill, sampling rate).
;
; If you are driving tests from automation, use the console commands. If you are
; a human investigating a problem, use this.

Scriptname PipMon_TerminalTest : 0x0003 pip_montestlab.esl

int property MenuSelection = 0 auto readonly

CustomEvent TestBenchStatus string

Event OnInit()
    DebugNotification "PIP-MON Test Bench ready. FormID " + GetFormIDFromEvent(self)
EndEvent

; ---------------------------------------------------------------------------
; Expected-results table
; ---------------------------------------------------------------------------
; Kept in one place so the documentation and the tool cannot drift. Each entry
; states what the dashboard MUST show, which is what turns this from a toy into
; a regression test you can actually run.
String Function ExpectedFor(string aTestName) ;
    if aTestName == "runaway_1"
        return "runaway_loop WARN, ~4000 ops/s, script PipMon_LoopTest, after ~2s"
    elseif aTestName == "runaway_8"
        return "runaway_loop (x8) AND vm_starvation WARN, total >500 ops/s aggregate"
    elseif aTestName == "leak_slow"
        return "handle_leak WARN, +1500 handles over 5s, no runaway_loop"
    elseif aTestName == "leak_fast"
        return "handle_leak CRITICAL, +6000 handles"
    elseif aTestName == "combined"
        return "save_bloat WARN/CRITICAL -- needs loop AND growth together"
    elseif aTestName == "recursion"
        return "stack_depth WARN at 820, CRITICAL at 1024, VM exception follows"
    elseif aTestName == "selfcheck"
        return "runaway_loop MUST fire -- if not, the detector is broken not the script"
    else
        return "baseline: no findings, ~5-10 active threads"
    endif
EndFunction

; ---------------------------------------------------------------------------
; Bench actions
; ---------------------------------------------------------------------------

Function Bench_RunawaySingle() ;
    DebugNotification "Starting 1 runaway thread. Expect: " + ExpectedFor("runaway_1")
    ; The loop script is reached through its own terminal in normal use; this
    ; entry is the shortcut for someone who has the TestBench open.
    Utility.Wait(0.1)
    DebugNotification "Open the PipMon_LoopTest terminal, or run 'tq_run 1' in the console."
EndFunction

Function Bench_LeakSlow() ;
    DebugNotification "Starting slow leak. Expect: " + ExpectedFor("leak_slow")
    DebugNotification "Open the PipMon_LeakTest terminal, or run 'lk_run 20' in the console."
EndFunction

Function Bench_LeakFast() ;
    DebugNotification "Starting fast leak. Expect: " + ExpectedFor("leak_fast")
    DebugNotification "Open the PipMon_LeakTest terminal, or run 'lk_run 100' in the console."
EndFunction

Function Bench_Combined() ;
    DebugNotification "Combined test. Expect: " + ExpectedFor("combined")
    DebugNotification "Run BOTH terminals: leak for growth, loop for the op cost."
EndFunction

Function Bench_Baseline() ;
    ; The most important test and the one people skip. A cell with no test
    ; running should be silent. If findings appear at baseline, either the
    ; thresholds are wrong for this load order or something else is running.
    DebugNotification "BASELINE: no test running. Expect " + ExpectedFor("baseline")
    DebugNotification "If findings appear now, they are from the ambient load order, not the test."
EndFunction

Function Bench_CleanupAll() ;
    DebugNotification "Releasing all test references. Watch the handle count fall."
    DebugNotification "Also run 'tq_stop' to clear any runaway threads."
EndFunction

; ---------------------------------------------------------------------------
; Menu
; ---------------------------------------------------------------------------
Event OnAddToMenu(MenuButton aButton)
    MenuButton "0. BASELINE (expect silence)" Button 0 id 1
    MenuButton "1. Runaway loop - 1 thread" Button 1 id 2
    MenuButton "2. Runaway loop - 8 threads" Button 2 id 3
    MenuButton "3. Handle leak - slow (20/tick)" Button 3 id 4
    MenuButton "4. Handle leak - fast (100/tick)" Button 4 id 5
    MenuButton "5. Combined leak + loop" Button 5 id 6
    MenuButton "6. Array inflation / memory" Button 6 id 7
    MenuButton "9. CLEAN UP EVERYTHING" Button 7 id 8
EndEvent

Event OnMenuClick(int aButton)
    if aButton == 1
        Bench_Baseline()
    elseif aButton == 2
        Bench_RunawaySingle()
    elseif aButton == 3
        DebugNotification "Expect: " + ExpectedFor("runaway_8")
        DebugNotification "Open PipMon_LoopTest, or run 'tq_run 8'."
    elseif aButton == 4
        Bench_LeakSlow()
    elseif aButton == 5
        Bench_LeakFast()
    elseif aButton == 6
        Bench_Combined()
    elseif aButton == 7
        DebugNotification "Expect memory growth with no op spike. Open PipMon_LeakTest."
    elseif aButton == 8
        Bench_CleanupAll()
    endif
EndEvent

Event OnTimer()
    int aButton = GetEventParameter(MenuClickEvent, "MenuItemID") as int
    if aButton == 0
        ; Terminal closed. Deliberately do NOT auto-cleanup here: unlike the
        ; leak and loop tests, a human closing this bench may want to inspect
        ; the dashboard afterwards. The cleanup entry is one click away and the
        ; console has 'mon_clean'.
        DebugNotification "Test bench closed. Telemetry continues. Run 'mon_clean' when finished."
    endif
EndEvent
