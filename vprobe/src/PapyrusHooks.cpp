// PapyrusHooks.cpp
#include "PapyrusHooks.hpp"

#include <intrin.h>

#include <chrono>
#include <cstring>
#include <sstream>

namespace f4mon::probe {

namespace {

// Monotonic nanosecond clock. On the hot path we prefer the cheaper of the two
// available sources based on measured cost; QPC is the fallback if TSC is
// unavailable (it is unavailable inside some VMs / under some debuggers).
std::uint64_t nowNs() {
    LARGE_INTEGER c;
    QueryPerformanceCounter(&c);
    static const std::uint64_t freq = [] {
        LARGE_INTEGER f;
        QueryPerformanceFrequency(&f);
        return static_cast<std::uint64_t>(f.QuadPart);
    }();
    return (static_cast<std::uint64_t>(c.QuadPart) * 1000000000ull) / freq;
}

// The unhooked originals. Typed to the signatures documented in Signatures.hpp;
// because we detour rather than call CommonLib wrappers, we own the ABI.
using ScriptExecuteFn  = std::uint64_t (*)(void* vmThread);
using ThreadExecuteFn  = void* (*)();
using DebugPrintFn     = void (*)(void* vm, const char* msg);
using RunOnceFn        = std::uint32_t (*)();

ScriptExecuteFn g_origScriptExecute = nullptr;
ThreadExecuteFn g_origThreadExecute = nullptr;
DebugPrintFn    g_origDebugPrint    = nullptr;
RunOnceFn       g_origRunOnce       = nullptr;

HookManager* g_manager = nullptr;

constexpr std::uint32_t kPlausibleFrameIdFloor = 0x00000001;
constexpr std::uint32_t kPlausibleFrameIdCeil  = 0x800FFFFF; // last local-plugin range

// A FormID is a 32-bit value whose high byte is the load-order index. Values
// outside the plausible TESForm space almost certainly mean we read the wrong
// field, which would attribute an anomaly to a nonsense mod. Reject early.
bool plausibleFormId(std::uint32_t id) {
    return id >= kPlausibleFrameIdFloor && id <= kPlausibleFrameIdCeil;
}

std::uint32_t readU32(const void* base, std::size_t off) {
    std::uint32_t v = 0;
    if (base && off) {
        std::memcpy(&v, static_cast<const std::uint8_t*>(base) + off, sizeof(v));
    }
    return v;
}

// Detour entry points. Member functions cannot be cast to void*, so the detour
// table gets free functions that forward to the manager. Each one re-reads
// nothing and does nothing but the call: the whole point is that the patched
// prologue lands somewhere that can return in a couple of nanoseconds.
//
// NOTE: the entry points that used to live here -- hookScriptExecute,
// hookThreadExecute, hookDebugPrint and hookRunOnce -- have been REMOVED, not
// disabled. They installed detours on PapyrusScript::Execute,
// PapyrusThread::Execute, PapyrusVM::DebugPrint and
// PapyrusVM::GetRunningThreadCount, and reading the RTTI out of Fallout4.exe
// shows the game contains no class named PapyrusScript, PapyrusThread or
// PapyrusVM at all. Those four resolves could only ever return null, so the
// hooks were unreachable code that reported "unresolved, probe degraded" on
// every single boot -- a permanent condition dressed up as a fault.
//
// The replacements are vtable targets in Signatures.hpp, all with confirmed
// RTTI identity and measured slot counts. None of them is hooked yet, and that
// is deliberate: a vtable slot is only safe to hook once its INDEX is sourced,
// and slot indices come from a class declaration in declaration order, which
// this project does not have for BSScript yet. Guessing a slot index is the
// failure this whole tier model is built to prevent, so nothing is installed
// rather than something installed at a guessed offset.

} // namespace

ThreadSlot* HookManager::slotFor(std::uint32_t vmThreadId) noexcept {
    if (!vmThreadId) {
        return nullptr;
    }
    // Thread IDs are small and dense in the Papyrus pool, so a direct-modulo
    // probe hits on the first or second try with no allocation.
    for (std::size_t i = 0; i < kMaxTrackedThreads; ++i) {
        auto& s = slots_[i];
        const std::uint8_t inUse = s.inUse.load(std::memory_order_acquire);
        if (inUse && s.vmThreadId.load(std::memory_order_relaxed) == vmThreadId) {
            return &s;
        }
    }
    for (std::size_t i = 0; i < kMaxTrackedThreads; ++i) {
        auto& s = slots_[i];
        std::uint8_t expected = 0;
        if (s.inUse.compare_exchange_strong(expected, 1, std::memory_order_acq_rel,
                                            std::memory_order_relaxed)) {
            s.vmThreadId.store(vmThreadId, std::memory_order_relaxed);
            s.opCounter.store(0, std::memory_order_relaxed);
            s.opTotal.store(0, std::memory_order_relaxed);
            s.depth.store(0, std::memory_order_relaxed);
            s.formId.store(0, std::memory_order_relaxed);
            s.waitMask.store(0, std::memory_order_relaxed);
            s.lastTickNs.store(nowNs(), std::memory_order_relaxed);
            s.inUse.store(1, std::memory_order_release);
            return &s;
        }
    }
    // Table full: the VM has more live threads than we budgeted. This is a
    // degraded but safe outcome -- the worst case is we stop counting.
    return nullptr;
}

void HookManager::trackOp(void* vmThread) {
    // Called on every interpreter step. This is the only place in the entire
    // probe where per-op work happens, so it is deliberately tiny: one
    // fetch_add, one compare, and a branch that is almost always not taken.
    if ((opTick_.fetch_add(1, std::memory_order_relaxed) & (kVmSampleInterval - 1)) != 0) {
        return;
    }

    const auto id = readU32(vmThread, 0x08);
    auto* slot = slotFor(id);
    if (!slot) {
        return;
    }
    slot->opTotal.fetch_add(kVmSampleInterval, std::memory_order_relaxed);
    emitVmTick(*slot, /*waiting=*/false);
}

void HookManager::emitVmTick(ThreadSlot& slot, bool waiting) {
    const std::uint64_t now = nowNs();
    std::uint64_t prev = slot.lastTickNs.load(std::memory_order_relaxed);
    if (!prev) {
        slot.lastTickNs.store(now, std::memory_order_relaxed);
        return;
    }
    const double deltaMs = static_cast<double>(now - prev) / 1e6;
    slot.lastTickNs.store(now, std::memory_order_relaxed);
    slot.windowMs.store(static_cast<float>(deltaMs), std::memory_order_relaxed);

    wire::VmTickPayload tick{};
    tick.vmThreadId = slot.vmThreadId.load(std::memory_order_relaxed);
    tick.opCounter   = kVmSampleInterval;
    tick.opTotal     = slot.opTotal.load(std::memory_order_relaxed);
    tick.windowMs    = static_cast<float>(deltaMs);
    tick.opRatePerSec = deltaMs > 0.0
                            ? static_cast<float>((kVmSampleInterval / deltaMs) * 1000.0)
                            : 0.0f;
    tick.formId   = slot.formId.load(std::memory_order_relaxed);
    tick.waiting  = waiting ? 1 : 0;
    tick.depth    = static_cast<std::uint8_t>(slot.depth.load(std::memory_order_relaxed));
    tick.opCode   = 0;

    server_.publish(wire::EventType::VmTick, &tick, sizeof(tick));
}

void HookManager::onScriptExecute(void* vmThread) {
    // Runs at script entry/exit. Sampled rather than fully instrumented: a full
    // call-graph rebuild here would cost more than the whole rest of the probe.
    const auto id = readU32(vmThread, 0x08);
    auto* slot = slotFor(id);
    if (!slot) {
        return;
    }

    const auto formId = readU32(vmThread, 0x18);
    if (plausibleFormId(formId)) {
        slot->formId.store(formId, std::memory_order_relaxed);
    }

    const auto depth = readU32(vmThread, 0x20);
    slot->depth.store(depth > 255 ? 255 : depth, std::memory_order_relaxed);

    if (g_origScriptExecute) {
        g_origScriptExecute(vmThread);
    }
}

void HookManager::onThreadExit(void* vmThread) {
    const auto id = readU32(vmThread, 0x08);
    if (auto* slot = slotFor(id)) {
        emitStackDump(*slot);
        // Release the slot so a recycled VM handle cannot inherit stale counters.
        std::uint8_t one = 1;
        slot->inUse.compare_exchange_strong(one, 0, std::memory_order_acq_rel,
                                            std::memory_order_relaxed);
    }
    if (g_origThreadExecute) {
        g_origThreadExecute();
    }
}

void HookManager::emitStackDump(const ThreadSlot& slot) {
    const auto depth = slot.depth.load(std::memory_order_relaxed);
    if (depth == 0) {
        return;
    }

    wire::StackDumpPayload dump{};
    dump.vmThreadId = slot.vmThreadId.load(std::memory_order_relaxed);
    dump.totalTimeUs = slot.windowMs.load(std::memory_order_relaxed);
    dump.depth       = static_cast<std::uint16_t>(std::min<std::uint32_t>(depth, wire::kMaxStackDepth));
    dump.truncated   = depth > wire::kMaxStackDepth ? 1 : 0;
    dump.reserved    = 0;

    const auto formId = slot.formId.load(std::memory_order_relaxed);
    for (std::uint16_t i = 0; i < dump.depth; ++i) {
        dump.frames[i].formId       = formId;
        dump.frames[i].scriptNameId = 0; // filled by the .esp patch when present
        dump.frames[i].depth        = i;
        dump.frames[i].selfTimeUs   = 0.0f;
    }

    server_.publish(wire::EventType::StackDump, &dump, sizeof(dump));
}

void HookManager::onDebugPrint(const char* message) {
    // Papyrus runtime errors land here. This is the highest-signal event in the
    // whole system: it is what a user sees in game as a red script error.
    if (!message) {
        if (g_origDebugPrint) {
            g_origDebugPrint(nullptr, nullptr);
        }
        return;
    }

    wire::VmExceptionPayload exc{};
    exc.errorClass = wire::VmErrorClass::RuntimeError;
    exc.formId     = 0;
    exc.opCode     = 0;
    exc.intervalUs = 0.0f;

    // Classify from the message text. Runs on a Papyrus thread, not the main
    // thread, and the strings are short -- a bounded scan with no allocation is
    // acceptable here. The alternative (hoisting classification to the worker)
    // would need a second queue for a few hundred bytes.
    const std::string_view mv(message);
    if (mv.find("stack") != std::string_view::npos ||
        mv.find("Stack") != std::string_view::npos) {
        exc.errorClass = wire::VmErrorClass::StackOverflow;
    } else if (mv.find("compile") != std::string_view::npos ||
               mv.find("Compile") != std::string_view::npos) {
        exc.errorClass = wire::VmErrorClass::Compile;
    } else if (mv.find("timeout") != std::string_view::npos ||
               mv.find("Timeout") != std::string_view::npos) {
        exc.errorClass = wire::VmErrorClass::EventTimeout;
    }

    server_.publish(wire::EventType::VmException, &exc, sizeof(exc));

    if (g_origDebugPrint) {
        g_origDebugPrint(nullptr, message);
    }
}

void HookManager::onFrame() {
    const std::uint64_t now = nowNs();
    if (lastFrameNs_ == 0) {
        lastFrameNs_ = now;
        return;
    }
    const float ms = static_cast<float>(static_cast<double>(now - lastFrameNs_) / 1e6);
    lastFrameNs_ = now;

    // Exponentially smoothed so the dashboard line is readable.
    const float prev = frameMs_.load(std::memory_order_relaxed);
    frameMs_.store(prev + (ms - prev) * 0.1f, std::memory_order_relaxed);
    frameCounter_.fetch_add(1, std::memory_order_relaxed);

    std::uint32_t active = 0;
    for (const auto& s : slots_) {
        if (s.inUse.load(std::memory_order_relaxed)) {
            ++active;
        }
    }
    server_.setFrameCount(frameCounter_.load(std::memory_order_relaxed));
    server_.setFrameTimeMs(frameMs_.load(std::memory_order_relaxed));
    server_.setThreadCounts(active, 0);
}

// ---------------------------------------------------------------------------
// Install / uninstall
// ---------------------------------------------------------------------------

void HookManager::install(vc::Resolver& resolver) {
    if (installed_.load(std::memory_order_acquire)) {
        return;
    }
    resolver_ = &resolver;
    g_manager = this;

    // Four AOB code hooks used to be installed here, against
    // PapyrusScript::Execute, PapyrusThread::Execute, PapyrusVM::DebugPrint
    // and PapyrusVM::GetRunningThreadCount. They are gone, and this line is
    // the replacement, for one reason worth reading.
    //
    // Those four names are not stale. They are not in the game. Fallout 4 has
    // no class called PapyrusVM, PapyrusThread or PapyrusScript; the Papyrus
    // VM is BSScript::Internal::VirtualMachine. So all four resolves returned
    // null every time, the detours were never installed, and the log said
    // "unresolved, probe degraded" -- which reads as a fault to be chased and
    // is actually a permanent, already-explained fact.
    //
    // The distinction is not cosmetic. docs/ARCHITECTURE.md states the rule
    // this implements: a disabled hook means a panel shows less, while a
    // silent failure means a panel shows nothing and the game looks healthy.
    // Logging a known-impossible target as degraded put it on the wrong side
    // of that line, in a report whose whole purpose is to be believed.
    //
    // The interfaces that DO exist are in Signatures.hpp as vtable targets,
    // each with its RTTI class name confirmed and its slot count measured by
    // tools/measure_vtable.py. They resolve. They are not hooked, because a
    // slot index needs a sourced declaration and none is available yet; see
    // the note above the removed entry points.
    installLog_.emplace_back(
        "no AOB code hooks: the four former PapyrusVM/Thread/Script targets "
        "name classes absent from the game's RTTI. BSScript VM interfaces "
        "resolve as vtable targets and are awaiting sourced slot indices.");

    installed_.store(true, std::memory_order_release);
}

void HookManager::uninstall() {
    if (!installed_.exchange(false, std::memory_order_acq_rel)) {
        return;
    }
    // Clear the originals before removing the detours so a hook still on the
    // stack between these two lines cannot tail-call into freed trampoline.
    g_origScriptExecute = nullptr;
    g_origThreadExecute = nullptr;
    g_origDebugPrint    = nullptr;
    g_origRunOnce       = nullptr;

    detourScriptExecute_.remove();
    detourThreadExecute_.remove();
    detourDebugPrint_.remove();
    detourRunOnce_.remove();

    g_manager = nullptr;
}

std::string HookManager::reportJson() const {
    std::ostringstream ss;
    ss << "{\"kind\":\"hook_report\",\"installed\":" << (installed_.load() ? "true" : "false")
       << ",\"log\":[";
    for (std::size_t i = 0; i < installLog_.size(); ++i) {
        if (i) ss << ',';
        ss << '"' << installLog_[i] << '"';
    }
    ss << "]}";
    return ss.str();
}

} // namespace f4mon::probe
