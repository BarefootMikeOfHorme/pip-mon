// SelfTest.hpp
//
// Native validation harness for vprobe.
//
// WHY THIS EXISTS
// ---------------
// vprobe's most dangerous failure mode is a signature that stopped matching, or
// a wire layout that drifted. Neither produces a visible error: the probe
// silently disables a hook, or the consumer decodes plausible-looking garbage.
// A monitoring tool that is quietly broken is worse than one that is absent,
// because the user trusts it.
//
// So the bridge validates ITSELF at init and says so out loud. A finding the
// dashboard shows because the probe asserted it is far more trustworthy than
// one the user has to take on faith.
//
// ONE IMPLEMENTATION, TWO CALLERS
// ------------------------------
//   * in-game   -- run by the bootstrap worker at cell load, results go out as
//                  PluginDiag so OverseerCLI shows them in the diagnostics pane
//   * CI        -- VPROBE_SelfTest() is exported, so test_harness.exe can
//                  LoadLibrary the DLL and call it with the game absent
//
// ONE RULE THAT MATTERS HERE
// --------------------------
// SelfTest must NEVER run on a game thread. It allocates, it scans buffers, it
// writes to executable memory to test a detour. Calling it from a hook would
// violate Rule 1 in the most spectacular way available. Every entry point here
// asserts that it is not running on the main thread, and says so loudly if it is.

#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace f4mon::selftest {

enum class Status {
    Pass,
    Fail,
    Skip,   // environment does not support this check (e.g. no game module)
};

struct Result {
    std::string name;
    Status      status = Status::Skip;
    std::string detail;

    [[nodiscard]] bool passed() const noexcept { return status == Status::Pass; }
};

struct Report {
    std::vector<Result> results;
    bool allPassed = true;
    int  passCount = 0;
    int  failCount = 0;
    int  skipCount = 0;
    double durationMs = 0.0;

    [[nodiscard]] std::string toJson() const;
    [[nodiscard]] std::string toText() const;
};

// Individual checks. Each is self-contained and returns a single Result, so a
// failure names the exact thing that broke rather than "self-test failed".
Result checkAbiLayout();
Result checkWireRoundTrip();
Result checkPatternParser();
Result checkScannerSynthetic();
Result checkPrologueValidation();
Result checkRingBuffer();
Result checkInternTable();
Result checkDetourLifecycle();
Result checkResolverState();   // Skip when the game module is absent

// Runs everything. Safe to call from any background thread.
Report runAll();

// Exported so test_harness.exe can drive it out-of-process.
extern "C" __declspec(dllexport) const char* VPROBE_SelfTest();
extern "C" __declspec(dllexport) void VPROBE_SelfTestFree(char*);

} // namespace f4mon::selftest
