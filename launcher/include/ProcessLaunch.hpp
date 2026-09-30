// ProcessLaunch.hpp
//
// The core load path: create the target suspended, re-verify it, inject one
// known DLL, resume, and require a handshake before declaring success.
//
// WHY EACH STEP EXISTS
//
//   Suspended       We need the window between "process exists" and "process
//                   runs" to do the pre-flight checks. It is the same window
//                   F4SE uses, and the same reason.
//
//   Re-verify       Pre-flight validates the executable on DISK. Then we
//                   spawn. Between those two events the file can be
//                   replaced, and a pre-flight that only checks the file
//                   before the spawn is theatre. This step re-parses the PE
//                   from the target's own address space and compares the
//                   build identity. That closes the window: a swapped file
//                   produces a different header hash and we refuse.
//
//   Inject          One known DLL, by path, via LoadLibraryW. No shellcode
//                   caves, no unbacked executable memory, no memory-protect
//                   games. See guardrail A5 -- the injection heuristics that
//                   matter fire on a four-part combination, and deliberately
//                   doing only two of them is the cheap way to stay out of
//                   that set.
//
//   Resume          Only after injection has been queued.
//
//   Handshake       The failure this prevents: vprobe.dll loads, fails to
//                   initialise, and the user watches a game that will never
//                   produce telemetry, with no indication why. We require
//                   proof of life within a timeout, and if it does not
//                   arrive we kill the process we created and report.
//
// GUARDRAIL NOTE
//   Nothing in this file may be changed to make a launch "more reliable" by
//   adding error suppression. A refusal with a specific reason is worth more
//   than a launch that appears to work (G4).
#pragma once

#include <windows.h>

#include <cstdint>
#include <string>
#include <vector>

#include "BuildIdentity.hpp"

namespace f4mon::preflight {

// Outcome of a launch attempt. Deliberately granular: the caller reports the
// exact reason to the user rather than a generic failure, because "the game
// did not start" with no reason is the failure mode of every launcher that
// has ever confused someone.
enum class LaunchResult {
    Ok,
    CreateFailed,          // the process would not start at all
    ImageMismatch,         // TOCTOU: the file changed between check and spawn
    InjectFailed,          // could not place or run the loader
    HandshakeTimeout,      // process resumed, but the runtime never proved life
    Degraded,              // the runtime loaded but never reported ready
    NotConfigured,         // no DLL path supplied
};

[[nodiscard]] const char* toString(LaunchResult r);

struct LaunchRequest {
    std::wstring exePath;                  // the game
    std::wstring dllPath;                  // vprobe.dll
    std::wstring workingDir;               // empty = exe's own directory
    std::uint32_t handshakeTimeoutMs = 15000;
    // Two-stage handshake, matching vprobe's ReadySignal.hpp exactly.
    //
    //   loadedEvent  the DLL mapped. Fires from DllMain, while the process is
    //                still suspended, so this event must exist BEFORE the
    //                spawn. A launcher that only waited for "ready" would be
    //                relying on init completing inside a process that has not
    //                run a single instruction yet.
    //   readyEvent   init completed and probes were resolved. Fires later,
    //                from the worker thread.
    //
    // The distinction is load-bearing: "loaded" proves injection worked,
    // "ready" proves the runtime is useful. Outside a real game, probes cannot
    // resolve, so a launcher that treated ready as required would reject every
    // honest pre-game launch -- and one that treated loaded as sufficient would
    // report success for a runtime that can never see a script. Both signals
    // are therefore captured, and a launch that only gets "loaded" is reported
    // as DEGRADED rather than Ok.
    std::wstring loadedEvent;
    std::wstring readyEvent;
    std::vector<std::wstring> extraArgs;
};

// A launched process. Owns the handle and kills on destruction unless
// released, so an early return can never leak a suspended process.
class LaunchedProcess {
public:
    LaunchedProcess() = default;
    ~LaunchedProcess();

    LaunchedProcess(const LaunchedProcess&) = delete;
    LaunchedProcess& operator=(const LaunchedProcess&) = delete;
    LaunchedProcess(LaunchedProcess&& other) noexcept;
    LaunchedProcess& operator=(LaunchedProcess&& other) noexcept;

    [[nodiscard]] bool valid() const { return process_ != nullptr; }
    [[nodiscard]] DWORD pid() const { return pid_; }
    [[nodiscard]] HANDLE handle() const { return process_; }
    [[nodiscard]] HANDLE thread() const { return thread_; }
    [[nodiscard]] HANDLE threadHandle() const { return thread_; }
    [[nodiscard]] const BuildIdentity& imageIdentity() const { return imageIdentity_; }

    // Hand the process over to the caller; the destructor will no longer kill
    // it. Only call this on Ok.
    void release();

    void killIfOwned();

    // Adopt a process we created. Used by launch() and by the self-test,
    // which creates a suspended process directly in order to inspect it.
    void adopt(HANDLE process, HANDLE thread, DWORD pid) {
        killIfOwned();
        process_ = process;
        thread_ = thread;
        pid_ = pid;
        owned_ = true;
    }

    // Recorded by launch() after re-verification, so the caller can report
    // which build actually started rather than only that one did.
    void setImageIdentity(const BuildIdentity& id) { imageIdentity_ = id; }

private:
    HANDLE process_ = nullptr;
    HANDLE thread_ = nullptr;
    DWORD pid_ = 0;
    bool owned_ = true;
    BuildIdentity imageIdentity_;
};

struct LaunchOutcome {
    LaunchResult result = LaunchResult::NotConfigured;
    std::wstring detail;
    // Build identity read back out of the target's address space. Recorded
    // even on failure, because "the image we got was X" is the single most
    // useful thing to print when something goes wrong.
    BuildIdentity imageIdentity;
    // Two independent facts, never collapsed into one boolean.
    bool loadedSignalled = false;   // the DLL mapped
    bool readySignalled  = false;   // init completed and probes resolved
};

// Create suspended, verify, inject, resume, handshake. The process is killed
// on any failure except Ok.
[[nodiscard]] LaunchOutcome launch(const LaunchRequest& req,
                                   LaunchedProcess& out);

// Exposed for the self-test, which cannot rely on injection succeeding to
// prove that re-verification does its job.
// Re-read the PE from the TARGET's own address space and compare it against
// the identity captured during pre-flight. This is the TOCTOU gate: a file
// swapped between validation and spawn lands here and is refused.
//
// Returns a PeVerdict. ImplausibleImage is overloaded deliberately -- it is
// what a hash mismatch reports -- because the caller only needs to know that
// the image is not the one we validated.
[[nodiscard]] PeVerdict verifySpawnedImage(HANDLE process,
                                           const BuildIdentity& expected,
                                           BuildIdentity& actualOut);

} // namespace f4mon::preflight
