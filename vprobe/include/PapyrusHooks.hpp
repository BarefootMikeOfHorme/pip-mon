// PapyrusHooks.hpp
//
// In-process probe: intercepts the Papyrus VM and streams raw samples out.
//
// The threading model is the whole trick. Papyrus runs on its own pool of
// threads, separate from the game's main render thread, so:
//   * hook bodies must be re-entrant and must not take a lock that the main
//     thread also takes (a deadlock in Papyrus freezes the game visibly),
//   * per-thread state is kept in a fixed-size table indexed by the VM thread
//     handle, so there is no allocation and no map lookup on the hot path.
#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <vector>

#include "Detour.hpp"
#include "IPCServer.hpp"
#include "InternTable.hpp"
#include "VersionConfig.hpp"

namespace f4mon::probe {

inline constexpr std::size_t kMaxTrackedThreads = 64;

// Per-VM-thread scratch. POD only; lives in a lock-free array.
struct ThreadSlot {
    std::atomic<std::uint32_t> vmThreadId{0};
    std::atomic<std::uint32_t> opCounter{0};
    std::atomic<std::uint32_t> opTotal{0};
    std::atomic<std::uint32_t> depth{0};
    std::atomic<std::uint32_t> formId{0};
    std::atomic<std::uint32_t> waitMask{0};
    std::atomic<std::uint32_t> stackTruncated{0};
    std::atomic<std::uint64_t> lastTickNs{0};
    std::atomic<float>         windowMs{0.0f};
    std::atomic<std::uint8_t>  inUse{0};
};

class HookManager {
public:
    explicit HookManager(ipc::IPCServer& server) : server_(server) {}

    // Resolve, validate and install whatever the current build supports.
    // Never throws; unresolvable probes are recorded and skipped.
    void install(vc::Resolver& resolver);

    // Remove all detours. Called from the F4SE unload path.
    void uninstall();

    // Called from a frame hook, if one resolved. Keeps heartbeat counters live.
    void onFrame();

    [[nodiscard]] std::string reportJson() const;

    // Sampled every kVmSampleInterval opcodes by the interpreter hook.
    inline static constexpr std::uint32_t kVmSampleInterval = 64;

    // Detour entry points. PUBLIC because they are what the patched prologue
    // lands on: PapyrusHooks.cpp forwards to these from free functions with
    // C-linkage shapes, and a detour target must be reachable from outside the
    // class. They are not part of the intended public API -- the comment is
    // documentation for a reader, not an invitation.
    void onScriptExecute(void* vmThread);
    void onThreadExit(void* vmThread);
    void onDebugPrint(const char* message);

private:
    // NOT static: it indexes the per-instance `slots_` table. A static member
    // cannot reach a non-static member, and the compiler is right to reject it.
    ThreadSlot* slotFor(std::uint32_t vmThreadId) noexcept;

    void emitVmTick(ThreadSlot& slot, bool waiting);
    void emitStackDump(const ThreadSlot& slot);
    void trackOp(void* vmThread);

    // Nth call per script invocation, to amortise the counter increment.
    std::atomic<std::uint64_t> opTick_{0};
    std::atomic<std::uint32_t> frameCounter_{0};
    std::atomic<float>         frameMs_{0.0f};
    std::uint64_t lastFrameNs_ = 0;

    ipc::IPCServer& server_;
    vc::Resolver* resolver_ = nullptr;

    std::array<ThreadSlot, kMaxTrackedThreads> slots_{};

    hooks::Detour detourScriptExecute_;
    hooks::Detour detourThreadExecute_;
    hooks::Detour detourDebugPrint_;
    hooks::Detour detourRunOnce_;

    std::vector<std::string> installLog_;
    std::atomic<bool> installed_{false};
};

} // namespace f4mon::probe
