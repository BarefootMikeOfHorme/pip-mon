; PipMon_TerminalTest.psc
;
; Interactive in-game test bench. The single place a user runs the suite.
;
; This script exists so the test surface is discoverable without the user
; needing to know console commands or file paths. It is a thin dispatcher: every
; bench action calls one of the test scripts, and every action states what to
; expect on the OverseerCLI dashboard.
;
; ---------------------------------------------------------------------------
; WHY THERE IS NO MENU HERE
; ---------------------------------------------------------------------------
; This file used to carry the menu API, which this build does not declare:
;
;     Event OnAddToMenu(MenuButton aButton)
;     MenuButton "0. BASELINE (expect silence)" Button 0 id 1
;     Event OnMenuClick(int aButton)
;
; Fallout 4 Papyrus has no menu system at all. MEASURED, not assumed: the
; compile probe vprobe/papyrus/probe_papyrus.bat fails on this construct with
; "no viable alternative at input '\"\"'", and ScriptObject.psc in this build
; declares no MenuButton anywhere. It is not a naming difference -- the
; capability is absent from the language.
;
; So the bench is a TERMINAL the player activates, and WHICH action it runs is
; a property set in the Creation Kit. That is the ordinary FO4 idiom and it
; costs one property instead of a menu.
;
; The cost, stated plainly: the player picks an action in the editor rather than
; from a list in game. See ai_context/spec/in_game_surface_requirements.json,
; capability "in-game-menu", which records this as work rather than as a missing
; import -- a real in-game menu is a mechanism that does not exist yet.
;
; ---------------------------------------------------------------------------
; WHY CustomEvent CARRIES NO TYPE HERE
; ---------------------------------------------------------------------------
; `CustomEvent TestBenchStatus string` was the other engine-shaped. A CustomEvent is
; declared like a variable and takes NO parameters; the payload travels in the
; Var[] passed to SendCustomEvent at send time and is read back by cast at
; receive time. Confirmed against the CK Wiki and proven by compilation.
;
; The relationship to the console commands is unchanged and still deliberate:
; the bridge (.esp) registers console commands for the same actions, because the
; console is scriptable and reaches actions the terminal does not expose
; (force-kill, sampling rate). Automation uses the console; a human uses this.

Scriptname PipMon_TerminalTest

; Which bench action the terminal runs when activated. Set this in the CK.
;   0 baseline   1 runaway x1   2 runaway x8   3 leak slow
;   4 leak fast  5 combined      6 memory       9 clean up everything
int property BenchAction = 0 auto

CustomEvent TestBenchStatus

Event OnInit()
    Debug.Notification("PIP-MON Test Bench ready. Action " + BenchAction + " -- see the property list for what each number runs.")
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

Function Bench_Baseline() ;
    Debug.Notification("BASELINE: no test running. Expect " + ExpectedFor("baseline"))
    Debug.Notification("If findings appear now, they are from the ambient load order, not the test.")
EndFunction

Function Bench_RunawaySingle() ;
    Debug.Notification("Runaway x1 armed. Expect: " + ExpectedFor("runaway_1"))
    Debug.Notification("Open the PipMon_LoopTest terminal, or run 'tq_run 1' in the console.")
    Utility.Wait(0.1)
EndFunction

Function Bench_RunawayEight() ;
    Debug.Notification("Runaway x8 armed. Expect: " + ExpectedFor("runaway_8"))
    Debug.Notification("Open PipMon_LoopTest, or run 'tq_run 8'.")
EndFunction

Function Bench_LeakSlow() ;
    Debug.Notification("Slow leak armed. Expect: " + ExpectedFor("leak_slow"))
    Debug.Notification("Open the PipMon_LeakTest terminal, or run 'lk_run 20' in the console.")
EndFunction

Function Bench_LeakFast() ;
    Debug.Notification("Fast leak armed. Expect: " + ExpectedFor("leak_fast"))
    Debug.Notification("Open PipMon_LeakTest, or run 'lk_run 100' in the console.")
EndFunction

Function Bench_Combined() ;
    Debug.Notification("Combined test. Expect: " + ExpectedFor("combined"))
    Debug.Notification("Run BOTH terminals: leak for growth, loop for the op cost.")
EndFunction

Function Bench_Memory() ;
    Debug.Notification("Memory test armed. Expect working-set growth with NO op spike.")
    Debug.Notification("That combination is the point: growth without a loop is a different finding.")
EndFunction

Function Bench_CleanupAll() ;
    Debug.Notification("Releasing all test references. Watch the handle count fall.")
    Debug.Notification("Also run 'tq_stop' to clear any runaway threads.")
    ; A CustomEvent carries no declared parameters; the payload goes in the Var[]
    ; and the receiver casts it. Unused here, kept so the wiring is exercised.
    Var[] kArgs = new Var[1]
    kArgs[0] = "cleanup"
    SendCustomEvent("TestBenchStatus", kArgs)
EndFunction

; ---------------------------------------------------------------------------
; Activation -- the FO4 replacement for OnMenuClick
; ---------------------------------------------------------------------------
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
        if BenchAction == 0
            Bench_Baseline()
        elseif BenchAction == 1
            Bench_RunawaySingle()
        elseif BenchAction == 2
            Bench_RunawayEight()
        elseif BenchAction == 3
            Bench_LeakSlow()
        elseif BenchAction == 4
            Bench_LeakFast()
        elseif BenchAction == 5
            Bench_Combined()
        elseif BenchAction == 6
            Bench_Memory()
        elseif BenchAction == 9
            Bench_CleanupAll()
        else
            Debug.Notification("BenchAction " + BenchAction + " is not a known action. See the property list.")
        endif    endif
EndEvent
