// TelemetryEvent.hpp
//
// Wire-format definitions for the fo4_monitor named-pipe transport.
// POD-only: every payload is trivially copyable, fixed-size, and endian-explicit
// so the consumer can decode with struct.Struct without ctypes or JSON parsing
// on the game thread.
//
// ABI RULES:
//   * Never reorder or resize an existing payload. Append only.
//   * Bump kProtocolVersion on any breaking change; the consumer is version-gated.
//   * All fixed-width integers are little-endian (x86-64 native, stated for clarity).
#pragma once

#include <cstdint>

namespace f4mon::wire {

inline constexpr std::uint16_t kProtocolVersion = 1;
inline constexpr std::uint32_t kFrameMagic = 0x4D4F4E34; // "F4MO"

// ---------------------------------------------------------------------------
// Frame header. Emitted immediately before every payload.
// ---------------------------------------------------------------------------
#pragma pack(push, 1)
struct FrameHeader {
    std::uint32_t magic;       // kFrameMagic
    std::uint16_t version;     // kProtocolVersion
    std::uint8_t  eventType;   // EventType
    std::uint8_t  flags;       // EventFlags (bitfield)
    std::uint32_t payloadSize; // bytes following the header
    std::uint64_t timestamp;   // QPC ticks since plugin init
    std::uint32_t sequence;    // monotonic per-process, wraps at UINT32_MAX
    std::uint32_t threadId;    // Win32 TID of the thread that emitted the event

    // Total wire size of a frame: the header plus its payload. Present on all
    // three language bindings (C++ / Python / Rust) so a consumer never has to
    // re-derive it and risk disagreeing with the producer.
    [[nodiscard]] constexpr std::size_t frameSize() const noexcept {
        return sizeof(FrameHeader) + static_cast<std::size_t>(payloadSize);
    }
};
#pragma pack(pop)
static_assert(sizeof(FrameHeader) == 28, "FrameHeader must stay 28 bytes");

enum class EventType : std::uint8_t {
    Heartbeat          = 0x01,  // periodic liveness + coarse counters
    ThreadState        = 0x02,  // Papyrus thread created/entered/exited
    StackFrame         = 0x03,  // one VM frame (script, formid, op, depth)
    StackDump          = 0x04,  // full stack snapshot for a thread
    VmTick             = 0x05,  // per-interpreter-loop op/latency sample
    VmException        = 0x06,  // Papyrus runtime error / exception signal
    Memory             = 0x07,  // process memory snapshot
    ModLoad            = 0x08,  // plugin load record (formid range + source)
    PluginDiag         = 0x09,  // bridge-level diagnostic string
    SaveBloat          = 0x0A,  // save-suspect heuristic signal
};

enum EventFlags : std::uint8_t {
    kFlagNone          = 0x00,
    kFlagOverflow      = 0x01,  // ring buffer dropped events before this
    kFlagScanFallback  = 0x02,  // address resolved via AOB, not AddressLib
    kFlagRecovered     = 0x04,  // bridge hit a recoverable fault
    kFlagSynthetic     = 0x08,  // emitted by the .esp patch, not a native hook
};

// ---------------------------------------------------------------------------
// Heartbeat: emitted at ~1 Hz from the bridge's own worker thread, never the
// game thread. Doubles as a clock-sync beacon for the consumer.
// ---------------------------------------------------------------------------
#pragma pack(push, 1)
struct HeartbeatPayload {
    double   uptimeSeconds;
    std::uint32_t gameFrameCount;
    float    frameTimeMs;       // smoothed
    std::uint32_t activePapyrusThreads;
    std::uint32_t queuedPapyrusThreads;
    std::uint64_t totalEventsEmitted;
    std::uint64_t totalEventsDropped;
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// ThreadState: the Papyrus VM scheduler creating/retiring a script thread.
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// ThreadState: the Papyrus VM scheduler creating/retiring a script thread.
//
// NOTE ON `depth`: this is u16, not u8. Papyrus' stack limit is 1024, so a u8
// depth silently truncates at 255 and makes the consumer's stack_depth rule
// (warn at 820, overflow at 1024) unreachable. That bug shipped in the first
// draft of this file and was caught by the detector tests. Any field carrying a
// Papyrus stack depth must be at least u16.
// ---------------------------------------------------------------------------
enum class ThreadPhase : std::uint8_t {
    Created = 0,
    Entered = 1,
    Yielded = 2,
    Exited  = 3,
    Errored = 4,
};

#pragma pack(push, 1)
struct ThreadStatePayload {
    std::uint32_t vmThreadId;    // VM-assigned handle, not an OS TID
    std::uint32_t waitEventMask; // TES::srEventMask bits the thread is blocked on
    std::uint32_t formId;        // owning form, 0 if none
    float         waitSeconds;
    std::uint16_t depth;         // call depth, 0..1024. u16, see note above.
    ThreadPhase   phase;
    std::uint8_t  waiting;       // 1 if parked on an event or delay
    std::uint8_t  reserved;
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// StackFrame: one entry of a Papyrus call chain. `scriptNameId` is a
// small-interned index resolved to a string by the consumer via a side table
// (see ScriptNameTable) -- the bridge never formats strings inline.
// ---------------------------------------------------------------------------
#pragma pack(push, 1)
struct StackFramePayload {
    std::uint32_t formId;        // TESForm the frame belongs to
    std::uint32_t scriptNameId;  // interned script name
    std::uint32_t opCode;        // Papyrus opcode
    std::uint16_t depth;         // 0 == outermost
    std::uint16_t sourceLine;    // debug info if compiled with -debug
    float         selfTimeUs;    // time attributed to this frame
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// StackDump: bounded snapshot. Depth is clamped to kMaxStackDepth; the
// truncated flag tells the consumer the tail is missing.
// ---------------------------------------------------------------------------
inline constexpr std::uint16_t kMaxStackDepth = 64;

#pragma pack(push, 1)
struct StackDumpPayload {
    std::uint32_t vmThreadId;
    std::uint16_t depth;
    std::uint8_t  truncated;
    std::uint8_t  reserved;
    float         totalTimeUs;
    StackFramePayload frames[kMaxStackDepth];
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// VmTick: sampled by the interpreter hook, once per N opcodes, to keep the
// game thread cost near-zero while still measuring throughput.
// ---------------------------------------------------------------------------
#pragma pack(push, 1)
struct VmTickPayload {
    std::uint32_t vmThreadId;
    std::uint32_t opCounter;      // ops executed in this window
    std::uint32_t opTotal;        // lifetime ops for this thread
    float         windowMs;
    float         opRatePerSec;
    std::uint32_t formId;         // currently executing form
    std::uint16_t depth;          // u16, not u8 -- see the note on ThreadStatePayload
    std::uint16_t opCode;
    std::uint8_t  waiting;        // 1 if blocked on an event/delay
    std::uint8_t  reserved;
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// VmException: Papyrus runtime error, script fault, and stack-overflow trip.
// ---------------------------------------------------------------------------
enum class VmErrorClass : std::uint8_t {
    StackOverflow = 0,   // 0x400 stack limit -- runaway recursion
    RuntimeError  = 1,   // type mismatch, nil deref, bad arg
    EventTimeout  = 2,
    Compile       = 3,   // source -> PE failure
    Unknown       = 255,
};

#pragma pack(push, 1)
struct VmExceptionPayload {
    std::uint32_t formId;
    std::uint32_t scriptNameId;
    VmErrorClass  errorClass;
    std::uint8_t  depth;
    std::uint16_t opCode;
    std::uint16_t depthAtThrow;
    std::uint32_t sourceLine;
    float         intervalUs;   // VM tick interval that triggered detection
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// Memory: emitted from the bridge worker thread at ~2 Hz.
// ---------------------------------------------------------------------------
#pragma pack(push, 1)
struct MemoryPayload {
    std::uint64_t workingSetBytes;
    std::uint64_t privateBytes;
    std::uint64_t virtualBytes;
    std::uint64_t peakWorkingSet;
    std::uint32_t handleCount;
    std::uint32_t threadCount;
    std::uint32_t papyrusThreadCount;
    std::uint32_t streamedCellCount;
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// ModLoad: formid -> source file mapping used to attribute anomalies to mods.
// ---------------------------------------------------------------------------
#pragma pack(push, 1)
struct ModLoadPayload {
    std::uint32_t formId;
    std::uint32_t modIndex;      // load-order slot
    std::uint32_t sourceNameId;  // interned "Skyrim.esm"-style string
    std::uint32_t loadFlags;     // bit0 active, bit1 esm, bit2 light
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// PluginDiag: UTF-8 payload. The ONLY string-bearing event, and it is always
// emitted from the worker thread, never inline in a hook.
// ---------------------------------------------------------------------------
enum class DiagLevel : std::uint8_t { Info = 0, Warning = 1, Error = 2 };

#pragma pack(push, 1)
struct PluginDiagPayload {
    DiagLevel level;
    std::uint8_t reserved[3];
    std::uint32_t textLength;    // bytes of UTF-8 following this struct
    // char text[textLength];
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// SaveBloat: raised when the bridge correlates unbounded per-frame script
// mutation with a growing object count in the active cell.
// ---------------------------------------------------------------------------
enum class BloatReason : std::uint8_t {
    UnboundedLoop      = 0,  // high op rate with no progress
    PropertyFlood      = 1,  // SetProperty called at anomalous rate
    CellStreamChurn    = 2,  // stream in/out thrash on a stable player cell
    Unknown            = 255,
};

#pragma pack(push, 1)
struct SaveBloatPayload {
    BloatReason reason;
    std::uint8_t reserved[3];
    std::uint32_t formId;
    std::uint32_t sourceNameId;
    std::uint32_t scriptNameId;
    std::uint64_t estimatedRecordsAdded;
    float         confidence;   // 0..1
};
#pragma pack(pop)

// ---------------------------------------------------------------------------
// ABI SIZES -- INViolable, asserted at compile time.
//
// Every one of these is duplicated in overseer_cli/src/overseer_cli/protocol.py
// and again in tests/test_protocol.py. The C++ side is what guarantees the
// value is never wrong here; the Python side catches it being wrong there.
//
// History: the Heartbeat size WAS wrong once (44 vs the real 40) because the
// Python struct carried a phantom field AND the test's expected value was
// derived from that same wrong string, so the two errors cancelled and the size
// test passed while packing failed. A size assertion alone is necessary but not
// sufficient -- hence round-trip tests too.
// ---------------------------------------------------------------------------
static_assert(sizeof(HeartbeatPayload)    == 40, "HeartbeatPayload");
static_assert(sizeof(ThreadStatePayload)  == 21, "ThreadStatePayload");
static_assert(sizeof(StackFramePayload)   == 20, "StackFramePayload");
static_assert(sizeof(StackDumpPayload)    == 12 + kMaxStackDepth * 20, "StackDumpPayload");
static_assert(sizeof(VmTickPayload)       == 30, "VmTickPayload");
static_assert(sizeof(VmExceptionPayload) == 22, "VmExceptionPayload");
static_assert(sizeof(MemoryPayload)       == 48, "MemoryPayload");
static_assert(sizeof(ModLoadPayload)      == 16, "ModLoadPayload");
static_assert(sizeof(PluginDiagPayload)   == 8,  "PluginDiagPayload");
static_assert(sizeof(SaveBloatPayload)    == 28, "SaveBloatPayload");

// The bridge's frame buffer must be able to hold the largest fixed payload.
static_assert(sizeof(StackDumpPayload) <= 2048, "IPCServer::Frame::payload is too small for a stack dump");

} // namespace f4mon::wire
