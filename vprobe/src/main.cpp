// PluginEntry.cpp
//
// F4SE plugin entry point for vprobe.dll.
//
// Responsibilities, in order:
//   1. Get out of the way as fast as possible. DllMain does no work beyond a
//      deferral decision; everything real happens on a worker thread once the
//      game module is mapped and F4SE has finished loading plugins.
//   2. Start the V-Link server and open the listening pipe, so the dashboard can
//      attach before the first frame and see the resolver report.
//   3. Install probes. Any probe that cannot be resolved is reported, skipped,
//      and the game keeps running normally.
//
// Version agnosticism: nothing here is keyed to a game build. AddressLib INIs
// are read when present; AOB signatures cover the rest. Old Gen (1.10.163) and
// Next Gen (1.10.980+) both run the same binary.

#include "IPCServer.hpp"
#include "Trace.hpp"
#include "PapyrusHooks.hpp"
#include "ReadySignal.hpp"
#include "VersionConfig.hpp"
#include "InternTable.hpp"

#include <Windows.h>

#include <algorithm>
#include <atomic>
#include <cstdarg>
#include <cstdio>
#include <memory>
#include <string>
#include <thread>

// F4SE plugin interface, provided by f4se_loader / the F4SE SDK at link time.
// The implementation now lives in PipmonEntry.cpp, which makes this an ADAPTER
// rather than a dependency: F4SE calls our entry points, not the other way
// round, and both paths share one implementation.
#include "PipmonEntry.hpp"

namespace f4mon::app {

namespace {

constexpr const wchar_t* kPipeName  = L"\\\\.\\pipe\\vlink_telemetry";

// WHERE OUR LIBRARIES LIVE, in the order they are tried.
//
// This ordering is a design decision, not a convenience, and it was wrong
// once. The only candidate originally was Data\F4SE\Plugins\vprobe\libs --
// which means a project whose entire premise is not needing F4SE was reading
// its own data out of F4SE's directory. That works on any machine that happens
// to have F4SE installed, and breaks on exactly the machine we are building
// for: a user with no extender at all. The dependency was invisible precisely
// because it was satisfied.
//
// The order below is deliberate:
//   1. Data\PIP-MON\libs        our own directory. Exists with or without
//                               F4SE, and is where the shipped mod (C) puts
//                               it. This is the path that must work.
//   2. <dll>\libs               the portable/B layout: libraries travel with
//                               the binary wherever it is deployed.
//   3. Data\F4SE\Plugins\...    LEGACY COMPAT ONLY. Kept so existing installs
//                               and coexisting F4SE users are not broken, and
//                               removed when we drop F4SE support entirely. It
//                               is last so it is a fallback rather than the
//                               mechanism -- if it silently becomes the only
//                               working path again, that is a regression, and
//                               it should fail loudly rather than quietly.
constexpr const wchar_t* kLibsPath  = L"Data\\PIP-MON\\libs";
constexpr const wchar_t* kLegacyLibsPath = L"Data\\F4SE\\Plugins\\vprobe\\libs";
constexpr const wchar_t* kIniFile   = L"vprobe.addresses.txt";

ipc::IPCServer    g_server;
vc::Resolver g_resolver;
telemetry::InternTable g_names;
std::unique_ptr<probe::HookManager> g_hooks;

std::atomic<bool> g_stop{false};
std::thread      g_worker;

  std::string nameTableProvider() {
      return g_names.dumpJson();
  }

  // The resolver report, regenerated on demand.
  //
  // This exists because the first attempt at replaying diagnostics cached the
  // MOST RECENT PluginDiag and resent that. At bootstrap three diags are
  // published -- the resolver report, the hook install log, and a greeting --
  // so "most recent" was the greeting, and a consumer connecting later got
  // told nothing about what actually resolved. The report was 1434 bytes of
  // the single most useful thing the runtime knows, and it was being lost to a
  // last-write-wins cache.
  //
  // The report is DERIVED state, so caching it was the wrong shape anyway: a
  // provider re-derives it whenever a consumer asks, which means it is always
  // current and correct rather than current as of boot. Same pattern as
  // nameTableProvider, for the same reason.
  std::string resolverReportProvider() {
      return g_resolver.buildReportJson();
  }


// ---------------------------------------------------------------------------
//  FILE TRACE -- opt-in, and the reason this file exists at all
// ---------------------------------------------------------------------------
//  The first live injection taught us something expensive. vprobe.dll mapped,
//  the handshake reported LOADED, and the game was gone three seconds later --
//  with no Windows Application Error event, no crash dump, and no Papyrus log.
//  Worst of all, our own diagnostics were unavailable: logLine() publishes to
//  the V-Link named pipe, and a pipe nobody has connected to yet carries
//  nothing. So the one run that mattered produced no evidence at all.
//
//  This fixes that specific failure. When a marker file named `vprobe.trace`
//  sits beside the DLL, every traceLine() is appended to `vprobe.trace.log` in
//  the same directory, timestamped and flushed per line.
//
//  Design constraints, each of which is the point:
//
//  - OFF unless the marker exists. The default path is unchanged, and a
//    shipped runtime does no file IO it was not asked to do.
//  - A marker FILE, not an environment variable. The game is launched by
//    whoever launched it, so an env var set in our shell would not reach it.
//    A file beside the DLL is found the same way every time.
//  - Opened, written, flushed, closed PER LINE. A buffer would lose exactly
//    the last few lines before a crash, which are the ones that matter.
//  - It must never be the cause of the failure it is diagnosing. Every call is
//    best-effort and no return value is checked for anything but success;
//    a trace that can crash the process is worse than no trace.

std::wstring g_tracePath;
bool        g_traceChecked = false;

void traceLine(const char* fmt, ...) {
    if (!g_traceChecked) {
        g_traceChecked = true;

        HMODULE self = nullptr;
        GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                               GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           reinterpret_cast<LPCWSTR>(&traceLine), &self);
        if (self) {
            wchar_t selfPath[MAX_PATH]{};
            const DWORD n = GetModuleFileNameW(self, selfPath, MAX_PATH);
            if (n > 0 && n < MAX_PATH) {
                std::wstring selfPathW(selfPath);
                const auto slash = selfPathW.find_last_of(L"\\/");
                if (slash != std::wstring::npos) {
                    const std::wstring dir = selfPathW.substr(0, slash + 1);
                    if (GetFileAttributesW((dir + L"vprobe.trace").c_str())
                        != INVALID_FILE_ATTRIBUTES) {
                        g_tracePath = dir + L"vprobe.trace.log";
                    }
                }
            }
        }
    }
    if (g_tracePath.empty()) {
        return;
    }

    char    body[1024]{};
    va_list ap;
    va_start(ap, fmt);
    const int written = _vsnprintf_s(body, sizeof(body), _TRUNCATE, fmt, ap);
    va_end(ap);
    if (written < 0) {
        return;
    }

    SYSTEMTIME st{};
    GetLocalTime(&st);
    char   line[1200]{};
    const int n = _snprintf_s(line, sizeof(line), _TRUNCATE,
                              "[%02u:%02u:%02u.%03u tid=%lu] %s\r\n",
                              st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
                              GetCurrentThreadId(), body);
    if (n < 0) {
        return;
    }

    HANDLE h = CreateFileW(g_tracePath.c_str(), FILE_APPEND_DATA,
                           FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                           OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
        return;
    }
    DWORD writtenBytes = 0;
    WriteFile(h, line, static_cast<DWORD>(n), &writtenBytes, nullptr);
    // No FlushFileBuffers: WriteFile to an append handle is already ordered
    // and this runs on a path that must not be able to stall the game.
    CloseHandle(h);
}


void logLine(const char* level, const std::string& text) {
    traceLine("%s: %s", level, text.c_str());
    // Goes through the V-Link diag channel, not the game's log, so the dashboard
    // is the single place a user has to look.
    wire::PluginDiagPayload diag{};
    diag.level = (std::string(level) == "error")  ? wire::DiagLevel::Error
                 : (std::string(level) == "warn") ? wire::DiagLevel::Warning
                                                  : wire::DiagLevel::Info;
    diag.textLength = 0;
    g_server.publish(wire::EventType::PluginDiag, diag, text);
}

// Locate <game>\Data\F4SE\Plugins\vprobe\libs\vprobe.addresses.txt. Falls back
// to the plugin's own module directory so a portable install works too.
std::wstring findAddressLibIni() {
    wchar_t gameDir[MAX_PATH]{};
    GetModuleFileNameW(nullptr, gameDir, MAX_PATH);
    std::wstring root(gameDir);

    std::vector<std::wstring> candidates;
    // 1. our own directory (F4SE-independent; where the shipped mod puts it)
    candidates.push_back(root + L"\\" + kLibsPath + L"\\" + kIniFile);

    HMODULE self = nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                           GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       reinterpret_cast<LPCWSTR>(&findAddressLibIni), &self);
    if (self) {
        wchar_t selfPath[MAX_PATH]{};
        GetModuleFileNameW(self, selfPath, MAX_PATH);
        std::wstring selfDir(selfPath);
        const auto slash = selfDir.find_last_of(L"\\/");
        if (slash != std::wstring::npos) {
            // 2. portable layout: libraries travel with the binary
            candidates.push_back(selfDir.substr(0, slash + 1) + L"libs\\" + kIniFile);
            candidates.push_back(selfDir.substr(0, slash + 1) + kIniFile);
        }
    }

    // 3. legacy F4SE location, last. See the note on kLibsPath: this exists for
    // existing installs, not as the mechanism, and must never be the only path
    // that works.
    candidates.push_back(root + L"\\" + kLegacyLibsPath + L"\\" + kIniFile);

    for (const auto& c : candidates) {
        if (GetFileAttributesW(c.c_str()) != INVALID_FILE_ATTRIBUTES) {
            return c;
        }
    }
    return {};
}

// How many probes actually resolved, and how many were attempted. These are
// what separate "the runtime is ready" from "the runtime is running but
// blind", and the launcher reports the difference rather than rounding it to
// success.
struct ProbeTally {
    std::size_t resolved = 0;
    std::size_t total    = 0;
};

void bootstrap() {
    traceLine("bootstrap: enter"); trace::session("STARTUP", "bootstrap entered");
    if (!g_server.start(kPipeName)) {
        traceLine("bootstrap: FATAL could not open \\\\.\\pipe\\%ls", kPipeName);
        OutputDebugStringW(L"[vprobe] FATAL: could not open \\\\.\\pipe\\vlink_telemetry\n");
        // Even a failed start is reported. A runtime that cannot open its pipe
        // must not look identical to one that was never asked to. The return
        // is discarded deliberately: a launcher may not be listening, and
        // that is not a reason to change this path.
        (void)runtime::signalLoaded();
        return;
    }
    traceLine("bootstrap: pipe open"); trace::session("STARTUP", "vlink pipe opened");
    g_server.setNameTableProvider(&nameTableProvider);
    g_server.setReportProvider(&resolverReportProvider);
    traceLine("bootstrap: providers set");

    // --- address resolution ------------------------------------------------
    // The BINARY database is preferred: same data, one read, no parsing and no
    // per-entry allocation inside the game process. The text INI is loaded
    // alongside it as the fallback and the authoritative/diffable form, so a
    // missing or foreign-build blob degrades to slower rather than to broken.
    const auto ini = findAddressLibIni();
    traceLine("bootstrap: ini search done, found=%d path=%ls",
              ini.empty() ? 0 : 1, ini.c_str());
    bool haveIni = false;
    bool haveBin = false;
    if (!ini.empty()) {
        // The blob sits beside the INI with a .bin extension.
        std::wstring bin = ini;
        const auto dot = bin.find_last_of(L'.');
        if (dot != std::wstring::npos) {
            bin = bin.substr(0, dot);
        }
        bin += L".bin";
        traceLine("bootstrap: loading bin %ls", bin.c_str());
        haveBin = g_resolver.loadAddressLibBin(bin);
        traceLine("bootstrap: bin loaded=%d", haveBin ? 1 : 0);
        haveIni = g_resolver.loadAddressLib(ini);
        traceLine("bootstrap: ini loaded=%d", haveIni ? 1 : 0);
    }
    if (!haveIni && !haveBin) {
        // Tier 2 only. Not an error: AOB scanning is a complete fallback, it is
        // just slower to start.
        g_resolver.loadEmbeddedDump();
        logLine("info", "address database not found; using AOB scan tier only.");
    } else if (haveBin && haveIni) {
        logLine("info", "address database loaded (binary + text).");
    } else if (haveBin) {
        logLine("info", "address database loaded (binary only; text INI absent).");
    } else {
        logLine("info", "address database loaded (text only; binary blob absent).");
    }

    // --- install probes ----------------------------------------------------
    traceLine("bootstrap: building HookManager");
    g_hooks = std::make_unique<probe::HookManager>(g_server);
    traceLine("bootstrap: installing hooks");
    g_hooks->install(g_resolver);
    traceLine("bootstrap: hooks installed");

    // Report what came up, so a user on an unsupported build immediately sees
    // which probes are live instead of wondering why the dashboard is empty.
    traceLine("bootstrap: building resolver report");
    const std::string report = g_resolver.buildReportJson();
    traceLine("bootstrap: resolver report %u bytes", static_cast<unsigned>(report.size()));
    wire::PluginDiagPayload diag{};
    diag.level      = wire::DiagLevel::Info;
    diag.textLength = 0;
    g_server.publish(wire::EventType::PluginDiag, diag, report);
    traceLine("bootstrap: published resolver report");

    const std::string hooks = g_hooks->reportJson();
    g_server.publish(wire::EventType::PluginDiag, diag, hooks);
    traceLine("bootstrap: published hook report");

    // --- tell the launcher we are up ---------------------------------------
    // Probes are counted, not assumed. Outside a real game nothing resolves,
    // so the honest signal here is "loaded, zero probes live" -- and the
    // launcher is expected to report that as degraded rather than as success.
    const auto names = g_resolver.allNames();
    ProbeTally tally{};
    tally.total = names.size();
    for (const std::string& n : names) {
        if (g_resolver.stateOf(n) != vc::State::NotFound &&
            g_resolver.stateOf(n) != vc::State::Pending) {
            ++tally.resolved;
        }
    }
    runtime::signalReady(tally.resolved, tally.total);

    logLine("info", "Runtime ready: " + std::to_string(tally.resolved) + "/" +
                        std::to_string(tally.total) + " probes resolved.");

    // --- resolve the remaining watchdogs on a timer ------------------------
    // A probe that failed at t=0 (module not fully mapped yet) gets another
    // chance; this is what makes an early-loading plugin robust.
    // NOTE: no capture list. g_resolver, g_hooks and g_stop are namespace-scope
    // globals with static storage duration, and C++ forbids capture-initialising
    // them (`&g_resolver` is C3495). A plain [] references them directly.
    std::thread watchdog([] {
        for (int attempt = 1; attempt <= 30 && !g_stop.load(std::memory_order_acquire); ++attempt) {
            Sleep(1000);
            if (g_stop.load(std::memory_order_acquire)) {
                break;
            }
            if (!g_resolver.gameModule()) {
                continue; // still too early
            }
            const bool anyMissing =
                std::any_of(g_resolver.allNames().begin(), g_resolver.allNames().end(),
                            [](const std::string& n) {
                                return g_resolver.stateOf(n) == vc::State::NotFound;
                            });
            if (!anyMissing) {
                break;
            }
            if (attempt % 5 == 0) {
                logLine("warn", "Retry pass " + std::to_string(attempt) +
                                    ": some probes still unresolved.");
            }
        }
    });
    watchdog.detach();
}

} // namespace   // anonymous

// Forward declaration: DllMain starts the worker, and DllMain is below.
DWORD WINAPI startWorkerThunk(LPVOID param);

void onLoad() {
    // Idempotent by construction, and that matters more now than it used to.
    //
    // There are two ways in:
    //   - F4SE calls VPROBE_OnLoad after plugin load (the old path)
    //   - the PIP-MON launcher injects the DLL directly and nothing calls us,
    //     so DllMain starts the same worker itself
    // Both can happen, in either order, and neither may initialise twice. The
    // joinable() guard is the whole mechanism; there is no separate flag that
    // could disagree with it.
    if (g_worker.joinable()) {
        return;
    }
    g_worker = std::thread([] {
        // Wait for the main module and F4SE to settle. Installing detours while
        // the loader is still resolving imports gets us a stale trampoline.
        //
        // Bounded, and the bound is reported rather than silently waited out:
        // a runtime that cannot find the game must not look identical to one
        // that was never supposed to find it. This is the no-game case that
        // decides whether the launcher reports Ok or Degraded.
        bool foundGame = false;
        for (int i = 0; i < 600; ++i) {
            HMODULE game = GetModuleHandleW(L"Fallout4.exe");
            if (game) {
                foundGame = true;
                break;
            }
            Sleep(100);
        }

    if (!foundGame) {
        // No game in this process. Say so, and DO NOT signal ready: a
        // runtime with no game has no probes and cannot see a script, and
        // the launcher must report that as Degraded rather than success.
        traceLine("onLoad: no Fallout4.exe in process after 60s; idle");
        logLine("error", "No Fallout4.exe in this process. Runtime is idle.");
        OutputDebugStringW(L"[vprobe] no game module; not becoming ready\n");
        return;
    }

    traceLine("onLoad: game module found, settling 1500ms"); trace::session("STARTUP", "game module located; settling");
    Sleep(1500);
    traceLine("onLoad: calling bootstrap");
    bootstrap();
    traceLine("onLoad: bootstrap returned"); trace::session("STARTUP", "bootstrap complete; runtime ready");
    });
}

void onUnload() {
    g_stop.store(true, std::memory_order_release);
    if (g_hooks) {
        g_hooks->uninstall();
        g_hooks.reset();
    }
    g_server.stop();
    if (g_worker.joinable()) {
        g_worker.join();
    }
}

// Defined after onLoad so the call is visible rather than forward-guessed.
DWORD WINAPI startWorkerThunk(LPVOID) {
    onLoad();
    return 0;
}

} // namespace f4mon::app

// ---------------------------------------------------------------------------
// DllMain
// ---------------------------------------------------------------------------

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved) {
    UNREFERENCED_PARAMETER(reserved);

    // `thread` is declared outside the switch on purpose. A declaration inside
    // a case label is crossed by the initialisation of any later case, which
    // is a hard error, and braces do not help because case labels jump rather
    // than fall through.
    HANDLE thread = nullptr;

    switch (reason) {
        case DLL_PROCESS_ATTACH:
            // Loader lock is held here. Spawning a thread from DllMain is legal
            // but discouraged, so we only record the module handle and let the
            // F4SE entry point (or a std::thread parked on a semaphore) do the
            // real work once the lock is released.
            DisableThreadLibraryCalls(inst);

            // The one thing we DO do while the lock is held, because it has to
            // happen now: tell the launcher the module mapped. Under launcher
            // injection this runs while the process is still suspended, so the
            // event must already exist. signalLoaded() only opens and sets, and
            // pulls in no further DLLs, so it is safe here.
            //
            // "loaded" is deliberately NOT "ready". Ready means init finished
            // AND probes resolved, and collapsing the two would let a launch
            // that found zero probes look identical to a healthy one.
            // Fully qualified: DllMain is at global scope, outside
            // f4mon::app, so the unqualified name does not resolve here.
            (void)f4mon::runtime::signalLoaded();

            // Start our own init, so the DLL works when the PIP-MON launcher
            // injects it directly and nobody calls VPROBE_OnLoad. This is the
            // F4SE-independence work: without it, injecting vprobe alone
            // produces a DLL that maps, reports "loaded", and then does
            // nothing -- the exact silent failure the handshake exists to
            // catch, caused from the inside.
            //
            // Safe under the loader lock: CreateThread is permitted from
            // DllMain and the thread's first action is to wait, so no real work
            // happens until the lock is released. onLoad() is idempotent, so
            // F4SE calling VPROBE_OnLoad afterwards is a no-op.
            //
            // GUARDED ON THE HOST PROCESS, and this is not optional. A DLL that
            // starts a thread in DllMain CANNOT be safely FreeLibrary'd: the
            // unload pulls the code out from under a thread that is still
            // running in it, and the process dies with 0xC0000409. That is not
            // hypothetical -- the self-test harness loads this DLL in a
            // non-game process to run VPROBE_SelfTest, and it was killed by
            // exactly this before the guard existed.
            //
            // So: only self-start when we are actually inside Fallout4. In
            // any other host (the harness, a hex editor, a stray LoadLibrary)
            // the DLL stays inert, which is also the correct behaviour for a
            // runtime that has nothing to instrument.
            if (GetModuleHandleW(L"Fallout4.exe") != nullptr) {
                thread = CreateThread(nullptr, 0, &f4mon::app::startWorkerThunk,
                                     nullptr, 0, nullptr);
                if (thread != nullptr) CloseHandle(thread);
            }
            break;

        case DLL_PROCESS_DETACH:
            // Only safe to tear hooks down if the process is exiting; on a
            // FreeLibrary the game is still running and other code may be
            // mid-script.
            if (!reserved) {
                f4mon::app::onUnload();
            }
            break;

        default:
            break;
    }
    return TRUE;
}

// ---------------------------------------------------------------------------
// Load entry points now live in PipmonEntry.cpp.
//
// VPROBE_OnLoad / VPROBE_OnUnload used to be defined here as the PRIMARY
// interface, with no PIP-MON equivalent at all. That made an F4SE
// installation a hard runtime dependency of a project built to replace F4SE's
// role -- and the kind of dependency nobody notices is the expensive kind.
//
// They are now ADAPTERS in PipmonEntry.cpp, which forwards them into
// PIPMON_Initialize / PIPMON_Shutdown. The F4SE exports are kept so the mod
// ecosystem that runs on F4SE keeps working, which is the coexistence
// contract; what changed is the DIRECTION of the call. F4SE now calls us.
//
// Exactly one implementation exists, so the two load paths cannot drift.
// ---------------------------------------------------------------------------
