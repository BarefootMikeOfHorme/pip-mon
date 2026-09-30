// Bridge.hpp
//
// Component 3 of PIP-MON: the in-game bridge (OverseerEventBridge.esp).
//
// This is the ONLY place where the game side and V-Probe's telemetry meet, and
// it is deliberately thin. It does not analyse, threshold, or decide anything
// (Rule 4) -- it forwards facts and queues actions.
//
// What it owns:
//   * console command registration (ConsoleCommands.cpp)
//   * the Rule 3 boundary -- every action is queued, never executed inline
//   * the TestLab <-> dashboard signal path
//
// What it must never do:
//   * write VM memory from a non-main thread
//   * decide whether a script is "slow" (that is OverseerCLI's job)
//   * grow a buffer based on load (pitfall 2)

#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <string_view>
#include <vector>

namespace f4mon::bridge {

// Hook identity, so `mon_config` can report which probes are live without
// reaching into V-Probe's internals.
enum class HookId { ScriptExecute, ThreadExecute, DebugPrint, RunningThreadCount };

class Bridge {
public:
    virtual ~Bridge() = default;

    // --- console commands (registered against the game console) ----------
    using CommandFn = std::function<void(Bridge&)>;
    using CommandArgFn = std::function<void(Bridge&, std::wstring_view)>;

    virtual void registerCommand(std::wstring_view name, CommandFn fn,
                                 std::wstring_view help) = 0;
    virtual void registerCommandArg(std::wstring_view name, CommandArgFn fn,
                                    std::wstring_view help) = 0;
    virtual void unregisterAll() = 0;

    // --- output ----------------------------------------------------------
    // Console echo. Goes through the game's console, never to a file from a
    // game thread (Rule 1).
    virtual void consolePrint(const wchar_t* text) = 0;

    // Overload for composed messages. Without it, every call site that builds a
    // message with std::to_wstring has to reach for .c_str(), which is a
    // dangling-pointer hazard the moment such a call is moved out of the
    // expression it was written in.
    virtual void consolePrint(const std::wstring& text) {
        consolePrint(text.c_str());
    }

    // --- introspection for the commands ----------------------------------
    [[nodiscard]] virtual int  protocolVersion() const = 0;
    [[nodiscard]] virtual bool bridgePresent() const = 0;
    [[nodiscard]] virtual bool consumerAttached() const = 0;
    [[nodiscard]] virtual double uptimeSeconds() const = 0;
    [[nodiscard]] virtual std::uint64_t eventsSent() const = 0;
    [[nodiscard]] virtual std::uint64_t eventsDropped() const = 0;
    [[nodiscard]] virtual std::uint32_t trackedThreads() const = 0;
    [[nodiscard]] virtual std::uint32_t activeThreads() const = 0;
    [[nodiscard]] virtual int resolverTier1Hits() const = 0;
    [[nodiscard]] virtual int resolverTier2Hits() const = 0;
    [[nodiscard]] virtual int resolverDisabledCount() const = 0;
    [[nodiscard]] virtual std::wstring resolverReport() const = 0;
    [[nodiscard]] virtual std::size_t ringUsed() const = 0;
    [[nodiscard]] virtual std::size_t ringCapacity() const = 0;
    [[nodiscard]] virtual std::uint64_t ringDropped() const = 0;
    [[nodiscard]] virtual std::size_t bytesInFlight() const = 0;
    [[nodiscard]] virtual std::uint32_t vmSampleInterval() const = 0;
    [[nodiscard]] virtual std::uint32_t ringCapacitySetting() const = 0;
    [[nodiscard]] virtual const wchar_t* logLevelName() const = 0;
    [[nodiscard]] virtual bool hookEnabled(HookId id) const = 0;

    // --- liveness --------------------------------------------------------
    // Round-trips a ping through the pipe and waits briefly for the echo.
    // This is the single most useful diagnostic command in the set, because it
    // distinguishes three different failure modes a user cannot otherwise tell
    // apart from the outside.
    [[nodiscard]] virtual bool pingConsumerAndWait(std::uint32_t timeoutMs) = 0;
    [[nodiscard]] virtual std::uint64_t lastPingRttMs() const = 0;

    // --- actions (Rule 3: queued, executed on the main thread) -----------
    virtual void requestSoftCancel(std::uint32_t vmThreadId) = 0;
    virtual void requestSoftCancelAll() = 0;
    virtual void requestForceKill(std::uint32_t vmThreadId) = 0;
    virtual void requestStackDump(std::uint32_t vmThreadId) = 0;

    // --- TestLab ---------------------------------------------------------
    // Reaches PipMon_LoopTest / PipMon_LeakTest by event rather than by a
    // direct function call, so the TestLab works with the bridge absent.
    virtual void callTestLab(std::string_view test, int arg) = 0;
    virtual void requestTestLabCleanup() = 0;

    virtual void clearResolverCache() = 0;
};

// Entry points, called by the .esp's script blocks.
void registerCommands(Bridge&);
void unregisterCommands(Bridge&);

int parseInt(std::wstring_view s, int fallback);

} // namespace f4mon::bridge
