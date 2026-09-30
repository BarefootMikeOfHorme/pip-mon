// main.cpp -- the launcher driver.
//
// Two modes:
//   --self-test            run the pre-flight and load-path validation suite
//   <exe> --inject <dll>   pre-flight, then launch with the runtime injected
//
// The launch mode exists so the whole chain can be exercised against a real
// game, and it is deliberately conservative: it never resumes a target whose
// image it could not verify, and it treats "runtime loaded but not ready" as a
// distinct, reportable outcome rather than a success.
#include <windows.h>

#include <cstdio>
#include <string>
#include <vector>

#include "BuildIdentity.hpp"
#include "ProcessLaunch.hpp"
#include "ReadySignal.hpp"   // the real event names, shared with vprobe
#include "SelfTest.hpp"

namespace {

// Fallout 4 is a 100-second boot on a good machine and much longer with a
// heavily modded Data folder, and the runtime waits for the game module before
// it resolves anything. This is generous on purpose: a timeout that is too
// short reports a failure that is really just impatience, and a user reading
// "the runtime did not signal ready" would have no way to tell those apart.
constexpr std::uint32_t kDefaultHandshakeMs = 120000;

void pauseIfInteractive() {
    if (GetConsoleWindow() != nullptr) {
        std::printf("\nPress any key to close...");
        (void)getchar();
    }
}

void printUsage() {
    std::printf("usage:\n");
    std::printf("  pipmon_preflight --self-test\n");
    std::printf("  pipmon_preflight <path-to-exe>\n");
    std::printf("  pipmon_preflight <path-to-exe> --inject <runtime.dll>\n");
    std::printf("        [--timeout-ms N] [--no-wait] [-- arg1 arg2 ...]\n");
}

int runIdentify(const std::wstring& path) {
    using namespace f4mon::preflight;

    BuildIdentity id;
    std::wstring why;
    const PeVerdict verdict = identifyFile(path, id, why);

    if (verdict != PeVerdict::Ok) {
        if (why.empty()) {
            std::printf("REJECT  %ls\n        reason: %s\n", path.c_str(), toString(verdict));
        } else {
            std::printf("REJECT  %ls\n        reason: %ls\n", path.c_str(), why.c_str());
        }
        std::printf("\nThe game will not be started on an unidentified build.\n");
        return 1;
    }

    std::printf("ACCEPT  %ls\n", path.c_str());
    std::printf("  build key    %s\n", id.headerHashHex.c_str());
    std::printf("  timestamp    0x%08x\n", id.timeDateStamp);
    std::printf("  linker       %u.%u\n", id.majorLinker, id.minorLinker);
    std::printf("  image size   0x%x (file 0x%llx)\n", id.sizeOfImage,
                static_cast<unsigned long long>(id.fileSize));
    std::printf("  subsystem    %s\n", id.subsystemIsGui() ? "GUI" : "console");
    return 0;
}

int runLaunch(const std::wstring& exe, const std::wstring& dll,
              std::uint32_t timeoutMs, bool noWait,
              const std::vector<std::wstring>& extraArgs) {
    using namespace f4mon::preflight;

    LaunchRequest req;
    req.exePath = exe;
    req.dllPath = dll;
    req.loadedEvent = f4mon::runtime::kLoadedEvent;
    req.readyEvent  = f4mon::runtime::kReadyEvent;
    req.handshakeTimeoutMs = timeoutMs;
    req.extraArgs = extraArgs;

    // --no-wait still asks the runtime to report, we simply do not block on
    // it. Used when driving the game by hand: the launcher must not sit there
    // holding a console for two minutes while the user plays.
    if (noWait) {
        req.loadedEvent.clear();
        req.readyEvent.clear();
    }

    std::printf("pre-flight...\n");
    BuildIdentity id;
    std::wstring why;
    if (identifyFile(exe, id, why) != PeVerdict::Ok) {
        std::printf("  REJECTED: the build could not be identified, so the game\n");
        std::printf("            was not started. Reason: %s\n",
                    why.empty() ? "unusable PE image" : "");
        if (!why.empty()) std::printf("%ls\n", why.c_str());
        return 1;
    }
    std::printf("  build key   %s\n", id.headerHashHex.c_str());
    std::printf("  timestamp   0x%08x\n", id.timeDateStamp);

    std::printf("\nlaunching (runtime: %ls)...\n", dll.c_str());
    if (!noWait) {
        std::printf("  waiting up to %u ms for the runtime to report\n", timeoutMs);
    }

    LaunchedProcess proc;
    const LaunchOutcome out = launch(req, proc);

    std::printf("\nresult: %s\n", toString(out.result));
    if (!out.detail.empty()) {
        std::printf("        %ls\n", out.detail.c_str());
    }
    std::printf("  pid            %lu\n", proc.pid());
    std::printf("  build in game  %s\n", out.imageIdentity.headerHashHex.c_str());

    if (noWait) {
        // Say plainly that the signals were not checked. Printing "no" here
        // would be equally wrong -- it would claim the runtime failed to
        // report when in fact nobody was listening.
        std::printf("  handshake      NOT CHECKED (--no-wait)\n");
        std::printf("\nThe game was started without waiting for the runtime.\n"
                    "Injection is queued, but whether vprobe initialised is\n"
                    "unverified -- check the process for vprobe.dll before\n"
                    "trusting anything.\n");
    } else {
        std::printf("  loaded signal  %s\n", out.loadedSignalled ? "yes" : "NO");
        std::printf("  ready signal   %s\n", out.readySignalled ? "yes" : "NO");
    }

    if (out.result == LaunchResult::Degraded) {
        std::printf(
            "\nThe runtime is running but its probes are not live. The game is\n"
            "left running so you can play, and the reason is in the log. On a\n"
            "supported build this is a defect; with no game module present it is\n"
            "expected.\n");
    }

    if (out.result == LaunchResult::Ok && !noWait) {
        std::printf("\nRuntime initialised. The game is yours.\n");
        std::printf("This window will close in 5 seconds.\n");
        Sleep(5000);
    }
    return out.result == LaunchResult::Ok ? 0 : 1;
}

} // namespace

int wmain(int argc, wchar_t** argv) {
    using namespace f4mon::preflight;

    if (argc >= 2 && std::wstring(argv[1]) == L"--self-test") {
        return runSelfTest();
    }
    if (argc < 2) {
        printUsage();
        pauseIfInteractive();
        return 2;
    }

    const std::wstring exe = argv[1];

    // Bare path: identify only. This is the pre-flight mode and it is the safe
    // default -- nothing is launched unless --inject is given explicitly.
    if (argc == 2) {
        const int rc = runIdentify(exe);
        pauseIfInteractive();
        return rc;
    }

    // Everything else is launch mode, and it is parsed strictly. An
    // unrecognised flag is an error rather than a silently ignored argument,
    // because "I typed a flag and it did nothing" is indistinguishable from
    // "the launch succeeded".
    std::wstring dll;
    std::uint32_t timeoutMs = kDefaultHandshakeMs;
    bool noWait = false;
    std::vector<std::wstring> extra;
    bool inPassthrough = false;

    for (int i = 2; i < argc; ++i) {
        const std::wstring a = argv[i];
        if (inPassthrough) {
            extra.push_back(a);
        } else if (a == L"--") {
            inPassthrough = true;
        } else if (a == L"--inject" && i + 1 < argc) {
            dll = argv[++i];
        } else if (a == L"--timeout-ms" && i + 1 < argc) {
            timeoutMs = static_cast<std::uint32_t>(_wtoi64(argv[++i]));
        } else if (a == L"--no-wait") {
            noWait = true;
        } else {
            std::printf("unrecognised argument: %ls\n\n", a.c_str());
            printUsage();
            pauseIfInteractive();
            return 2;
        }
    }

    if (dll.empty()) {
        std::printf("--inject requires a runtime DLL path\n\n");
        printUsage();
        pauseIfInteractive();
        return 2;
    }

    const int rc = runLaunch(exe, dll, timeoutMs, noWait, extra);
    pauseIfInteractive();
    return rc;
}
