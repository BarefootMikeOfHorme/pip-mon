// ConsoleCommands.cpp
//
// Console commands for PIP-MON, registered by OverseerEventBridge.esp.
//
// WHY CONSOLE COMMANDS AND NOT JUST A TUI
// ----------------------------------------
// OverseerCLI can already do most of what these do, and one could argue it
// should do all of it. The counter-argument is testability: a console command can
// be driven from a .bat, a CI job, or a bug-repro script, and it works when no
// terminal is open. A TUI button cannot. The two surfaces deliberately overlap
// -- a command exists wherever there is an action worth scripting.
//
// NAMING
// ------
//   mon_*   status, config, diagnostics        (mon_status, mon_config, ...)
//   tq_*    TestLab: thread/queue tests        (tq_run, tq_stop, tq_selfcheck)
//   lk_*    TestLab: leak tests                (lk_run, lk_clean, ...)
//   vpr_*   V-Probe internals                  (vpr_scan, vpr_stats, vpr_reset)
//
// All are two-or-three letter prefixed so they are trivially greppable, and
// none of them shadow a vanilla command. `~` and `help` list them.
//
// RULE 3
// ------
// A console command is already executing on the main thread -- the game calls it
// from the console handler. So these do NOT need the task queue that IPC
// commands need, and they must not use it either: it would add a frame of
// latency to something that can act immediately. The distinction is worth being
// explicit about, because "always go through the queue" is a reasonable-sounding
// rule that is wrong here.
//
// SAFETY
// ------
// Commands that terminate threads are the sharpest edge in this codebase, so:
//   * `tq_stop` is soft by default and only force-kills behind `vpr_force`,
//   * anything destructive prints exactly what it is about to do,
//   * nothing here writes VM memory from a non-main thread. Ever.

#include "ConsoleCommands.hpp"

#include "Bridge.hpp"

#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>

namespace f4mon::bridge {

namespace {

// --- command implementations ------------------------------------------------

void cmdStatus(Bridge& b) {
    wchar_t buf[512]{};
    _snwprintf_s(buf, _TRUNCATE,
                 L"V-Probe  |  bridge v%d  |  pipe: \\\\.\\pipe\\vlink_telemetry\n"
                 L"consumer : %s\n"
                 L"uptime   : %.0f s\n"
                 L"events   : %llu sent, %llu dropped\n"
                 L"threads  : %u tracked, %u active\n"
                 L"resolver : %d via AddressLib, %d via AOB, %d disabled",
                 b.protocolVersion(),
                 b.consumerAttached() ? L"connected" : L"NOT CONNECTED (is OverseerCLI running?)",
                 b.uptimeSeconds(),
                 static_cast<unsigned long long>(b.eventsSent()),
                 static_cast<unsigned long long>(b.eventsDropped()),
                 b.trackedThreads(),
                 b.activeThreads(),
                 b.resolverTier1Hits(),
                 b.resolverTier2Hits(),
                 b.resolverDisabledCount());
    b.consolePrint(buf);
}

void cmdScan(Bridge& b) {
    const auto report = b.resolverReport();
    b.consolePrint(L"Probes resolved on this build:");
    b.consolePrint(report);
}

void cmdStats(Bridge& b) {
    wchar_t buf[256]{};
    _snwprintf_s(buf, _TRUNCATE,
                 L"ring  : %llu / %u slots used, %llu dropped\n"
                 L"batch : %zu bytes in flight\n"
                 L"op tick: every %u ops",
                 static_cast<unsigned long long>(b.ringUsed()),
                 b.ringCapacitySetting(),
                 static_cast<unsigned long long>(b.ringDropped()),
                 b.bytesInFlight(),
                 b.vmSampleInterval());
    b.consolePrint(buf);
}

void cmdConfig(Bridge& b) {
    wchar_t buf[512]{};
    _snwprintf_s(buf, _TRUNCATE,
                 L"vprobe settings (Data\\F4SE\\Plugins\\vprobe\\vprobe_settings.jsonc)\n"
                 L"  vmSampleInterval : %u\n"
                 L"  ringCapacity     : %u\n"
                 L"  logLevel         : %ls\n"
                 L"  hooks enabled    : scriptExecute=%d threadExecute=%d debugPrint=%d",
                 b.vmSampleInterval(),
                 b.ringCapacitySetting(),
                 b.logLevelName(),
                 static_cast<int>(b.hookEnabled(HookId::ScriptExecute)),
                 static_cast<int>(b.hookEnabled(HookId::ThreadExecute)),
                 static_cast<int>(b.hookEnabled(HookId::DebugPrint)));
    b.consolePrint(buf);
    b.consolePrint(L"Edit the file and reload the save; changes are read at cell load.");
}

void cmdHelp(Bridge& b) {
    b.consolePrint(L"PIP-MON commands:");
    b.consolePrint(L"  mon_status      this summary");
    b.consolePrint(L"  mon_scan        re-run address resolution, show per-probe state");
    b.consolePrint(L"  mon_stats       ring buffer and sampling statistics");
    b.consolePrint(L"  mon_config      current settings and hook state");
    b.consolePrint(L"  mon_ping        verify the bridge<->OverseerCLI path end to end");
    b.consolePrint(L"  mon_clean       release all TestLab references and stop test threads");
    b.consolePrint(L"  vpr_reset       clear the resolver cache and re-scan");
    b.consolePrint(L"  vpr_dumpstack N request a stack dump for VM thread N");
    b.consolePrint(L"  vpr_softcancel N graceful Script.Cancel() -- try this first");
    b.consolePrint(L"  vpr_force N     FORCE-KILL. May corrupt quest state. Saves first? No.");
    b.consolePrint(L"  tq_run [N]      TestLab: start N runaway threads (default 1)");
    b.consolePrint(L"  tq_selfcheck    TestLab: 5s measured burst; prints expected result");
    b.consolePrint(L"  tq_stop         TestLab: abort all runaway threads (soft)");
    b.consolePrint(L"  lk_run [N]      TestLab: leak N references per tick (default 20)");
    b.consolePrint(L"  lk_clean        TestLab: release every leaked reference");
    b.consolePrint(L"  coc PipMonTestLabCell   teleport to the quarantined test cell");
}

void cmdPing(Bridge& b) {
    // A ping that never arrives at the dashboard means one of three things, and
    // the user needs to be able to tell them apart without opening a debugger.
    if (!b.bridgePresent()) {
        b.consolePrint(L"FAIL: OverseerEventBridge.esp is not loaded. "
                       L"Check that it is in Data\\ and enabled in FOMOD.");
        return;
    }
    if (!b.consumerAttached()) {
        b.consolePrint(L"vprobe OK, bridge OK, but no OverseerCLI consumer attached.");
        b.consolePrint(L"Start it:  overseer-cli");
        return;
    }
    const bool echoed = b.pingConsumerAndWait(/*timeoutMs=*/1500);
    if (echoed) {
        wchar_t buf[128]{};
        _snwprintf_s(buf, _TRUNCATE, L"OK: V-Probe -> V-Link -> OverseerCLI round trip in %llu ms",
                     static_cast<unsigned long long>(b.lastPingRttMs()));
        b.consolePrint(buf);
    } else {
        b.consolePrint(L"FAIL: consumer is attached but did not echo the ping within 1.5 s.");
        b.consolePrint(L"The pipe is open but the dashboard is not processing frames.");
    }
}

void cmdClean(Bridge& b) {
    // Deliberately soft. A user who runs this is tidying up, not debugging, and
    // a force-kill here would be a nasty surprise with no confirmation prompt.
    b.requestSoftCancelAll();
    b.requestTestLabCleanup();
    b.consolePrint(L"Requested: cancel all tracked threads, release TestLab references.");
    b.consolePrint(L"This takes effect on the next frame. Verify with mon_stats.");
}

void cmdReset(Bridge& b) {
    b.clearResolverCache();
    const auto report = b.resolverReport();
    b.consolePrint(L"Resolver cache cleared, re-scanned:");
    b.consolePrint(report);
}

void cmdDumpStack(Bridge& b, std::wstring_view arg) {
    const int threadId = parseInt(arg, -1);
    if (threadId < 0) {
        b.consolePrint(L"Usage: vpr_dumpstack <vmThreadId>");
        b.consolePrint(L"Get the id from OverseerCLI panel 1, or from mon_stats.");
        return;
    }
    b.requestStackDump(threadId);
    b.consolePrint(std::wstring(L"Stack dump requested for VM thread ") +
                    std::to_wstring(threadId) + L". Watch OverseerCLI panel 1.");
}

void cmdSoftCancel(Bridge& b, std::wstring_view arg) {
    const int threadId = parseInt(arg, -1);
    if (threadId < 0) {
        b.consolePrint(L"Usage: vpr_softcancel <vmThreadId>");
        return;
    }
    b.requestSoftCancel(threadId);
    b.consolePrint(std::wstring(L"Soft-cancel requested for thread ") + std::to_wstring(threadId) +
                    L". The script will unwind and release its locals.");
}

void cmdForce(Bridge& b, std::wstring_view arg) {
    const int threadId = parseInt(arg, -1);
    if (threadId < 0) {
        b.consolePrint(L"Usage: vpr_force <vmThreadId>");
        return;
    }
    // No confirmation prompt is possible from a console command, which is
    // exactly why the command is named `vpr_force` rather than something
    // friendlier, and why the dashboard's own force-kill is a blocking
    // confirm. The naming is the warning.
    b.consolePrint(L"*** FORCE-KILL ***");
    b.consolePrint(L"This terminates a VM thread without unwinding. Quest flags and");
    b.consolePrint(L"workshop state written by that script may be left inconsistent.");
    b.consolePrint(L"Save to a NEW slot if you care about this save.");
    b.consolePrint(L"Prefer vpr_softcancel unless the soft cancel did not work.");
    b.requestForceKill(threadId);
    b.consolePrint(std::wstring(L"Force-kill queued for thread ") + std::to_wstring(threadId) +
                    L"; executes next frame.");
}

void cmdTqRun(Bridge& b, std::wstring_view arg) {
    int n = parseInt(arg, 1);
    n = (n < 1) ? 1 : (n > 64 ? 64 : n);
    b.callTestLab("loop", n);
    wchar_t buf[256]{};
    _snwprintf_s(buf, _TRUNCATE,
                 L"TestLab: %d runaway thread(s) armed at 100 Hz (~4000 ops/s each).\n"
                 L"Expect runaway_loop after ~2 s. With N>=2 also expect vm_starvation.",
                 n);
    b.consolePrint(buf);
}

void cmdTqStop(Bridge& b) {
    b.callTestLab("loopstop", 0);
    b.consolePrint(L"TestLab: abort flag set. Threads unwind on their next iteration.");
}

void cmdTqSelfCheck(Bridge& b) {
    b.callTestLab("selfcheck", 0);
    b.consolePrint(L"TestLab: 5 s measured burst running.");
    b.consolePrint(L"A pass prints an op rate > 500. If OverseerCLI did NOT flag");
    b.consolePrint(L"runaway_loop during it, the DETECTOR is at fault, not the script.");
}

void cmdLkRun(Bridge& b, std::wstring_view arg) {
    int n = parseInt(arg, 20);
    n = (n < 1) ? 1 : (n > 100 ? 100 : n);
    b.callTestLab("leak", n);
    wchar_t buf[256]{};
    _snwprintf_s(buf, _TRUNCATE,
                 L"TestLab: leaking %d references per tick, cap 1000.\n"
                 L"Expect handle_leak after ~5 s. Runs SILENTLY on op rate -- that is\n"
                 L"the point: a leak is invisible to a pure profiler.",
                 n);
    b.consolePrint(buf);
}

void cmdLkClean(Bridge& b) {
    b.callTestLab("leakclean", 0);
    b.consolePrint(L"TestLab: releasing all references. Handle count should fall within ~1 s.");
}

} // namespace

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

void registerCommands(Bridge& b) {
    b.registerCommand(L"mon_status",  &cmdStatus,   L"PIP-MON status summary");
    b.registerCommand(L"mon_scan",    &cmdScan,     L"Re-run address resolution");
    b.registerCommand(L"mon_stats",   &cmdStats,    L"Ring buffer and sampling stats");
    b.registerCommand(L"mon_config",  &cmdConfig,   L"Show settings and hook state");
    b.registerCommand(L"mon_help",    &cmdHelp,     L"List all PIP-MON commands");
    b.registerCommand(L"mon_ping",    &cmdPing,     L"Verify the V-Link round trip");
    b.registerCommand(L"mon_clean",   &cmdClean,    L"Cancel test threads, release references");
    b.registerCommand(L"vpr_reset",   &cmdReset,    L"Clear resolver cache and re-scan");

    b.registerCommandArg(L"vpr_dumpstack", &cmdDumpStack,  L"Dump a VM thread's stack");
    b.registerCommandArg(L"vpr_softcancel",&cmdSoftCancel, L"Graceful Script.Cancel()");
    b.registerCommandArg(L"vpr_force",    &cmdForce,      L"FORCE-KILL a VM thread (unsafe)");

    b.registerCommandArg(L"tq_run",       &cmdTqRun,       L"Start N runaway threads");
    b.registerCommand(L"tq_stop",        &cmdTqStop,      L"Stop runaway threads");
    b.registerCommand(L"tq_selfcheck",   &cmdTqSelfCheck, L"Run the 5 s measured self-check");

    b.registerCommandArg(L"lk_run",       &cmdLkRun,       L"Start leaking N refs per tick");
    b.registerCommand(L"lk_clean",       &cmdLkClean,     L"Release all leaked references");
}

void unregisterCommands(Bridge& b) {
    b.unregisterAll();
}

} // namespace f4mon::bridge
