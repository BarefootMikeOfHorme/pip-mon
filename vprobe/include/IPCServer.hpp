// IPCServer.hpp
//
// Asynchronous, non-blocking Win32 Named Pipe producer.
//
//   \\.\pipe\fo4_monitor
//
// Design constraints, in priority order:
//   1. The game thread must never block. Pushes go to a lock-free SPSC ring and
//      return immediately; a dedicated worker thread owns every Win32 call.
//   2. If the consumer is absent, slow, or dead, we degrade -- never stall.
//      Full ring => drop + count. Pipe write timeout => disconnect + reconnect.
//   3. No strings, no formatting, no locks on the game path. Raw struct bytes
//      are memcpy'd into the frame and the worker does the rest.
//
// I/O model: FILE_FLAG_OVERLAPPED + an I/O completion port. One thread services
// the port; it never sits in a blocking ReadFile/WriteFile. A single write is
// in flight at a time per server (frames are concatenated into a batch buffer),
// which keeps syscall count proportional to bytes, not to events.
#pragma once

#include <Windows.h>
#include <winioctl.h>

#include <atomic>
#include <cstdint>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "FrameQueue.hpp"
#include "TelemetryEvent.hpp"

namespace f4mon::ipc {

// A complete, ready-to-send frame. The queue stores these by value; the header
// is filled at push time on the game thread using only fixed-width stores.
struct Frame {
    wire::FrameHeader header{};
    std::uint8_t payload[2048]{};
};

inline constexpr std::size_t kMaxPayloadBytes = sizeof(Frame::payload);

struct ServerStats {
    std::uint64_t framesAccepted = 0;
    std::uint64_t framesDropped = 0;   // ring full or no consumer
    std::uint64_t bytesSent = 0;
    std::uint64_t reconnects = 0;
    std::uint64_t writeTimeouts = 0;
    std::uint64_t clientSessions = 0;
    bool          clientAttached = false;
};

class IPCServer {
public:
    IPCServer() = default;
    ~IPCServer();

    IPCServer(const IPCServer&) = delete;
    IPCServer& operator=(const IPCServer&) = delete;

    // `pipePath` defaults to \\.\pipe\fo4_monitor.
    bool start(const std::wstring& pipePath = L"\\\\.\\pipe\\fo4_monitor");
    void stop();

    [[nodiscard]] bool running() const noexcept { return running_.load(std::memory_order_acquire); }

    // --- game-thread safe -------------------------------------------------
    // Copies payload into a slot and enqueues. Returns false if the queue was
    // full. Never allocates, never locks, never touches Win32.
    bool publish(wire::EventType type, const void* payload, std::size_t size) noexcept;
    bool publish(wire::EventType type, const wire::PluginDiagPayload& diag, std::string_view text) noexcept;

    // Convenience for events with no payload body.
    bool publishEmpty(wire::EventType type) noexcept { return publish(type, nullptr, 0); }

    [[nodiscard]] ServerStats stats() const noexcept;
    [[nodiscard]] bool clientAttached() const noexcept { return clientAttached_.load(std::memory_order_acquire); }

    // Signals the worker to emit a PluginDiag carrying the intern table, so a
    // freshly connected dashboard can decode name ids immediately.
    void requestNameTableSync() noexcept { nameSyncRequested_.store(true, std::memory_order_release); }

    using NameTableProvider = std::string (*)();
    // Same shape, different content: the resolver report, re-derived on demand.
    using ReportProvider = std::string (*)();

    void setNameTableProvider(NameTableProvider provider) noexcept { nameProvider_ = provider; }
    void setReportProvider(ReportProvider provider) noexcept { reportProvider_ = provider; }

    // Coarse counters published by the hook layer. Relaxed stores only; these
    // are telemetry, not synchronisation, so a slightly stale value is correct
    // behaviour rather than a bug.
    void setFrameCount(std::uint32_t frames) noexcept {
        // The FIRST non-zero frame count is what proves a frame source is
        // actually attached. Until one exists, the phase tag has to admit it
        // cannot tell a menu from a world -- see the state line in
        // workerMain(). Deriving MENU from a counter that nothing increments is
        // a tag that is confidently wrong, which is the one thing a status
        // report must never be.
        if (frames > 0) {
            frameSourceLive_.store(true, std::memory_order_release);
        }
        frameCounter_.store(frames, std::memory_order_relaxed);
    }
    void setFrameTimeMs(float ms) noexcept { frameTimeMs_.store(ms, std::memory_order_relaxed); }
    void setThreadCounts(std::uint32_t active, std::uint32_t queued) noexcept {
        activeThreads_.store(active, std::memory_order_relaxed);
        queuedThreads_.store(queued, std::memory_order_relaxed);
    }
    void setStreamedCells(std::uint32_t count) noexcept {
        streamedCells_.store(count, std::memory_order_relaxed);
    }

private:
    // --- worker side ------------------------------------------------------
    void workerMain();
    bool createPipeInstance();
    void destroyPipe(HANDLE h) noexcept;
    void closeClient() noexcept;
    void queueConnect(HANDLE h);
    void queueWrite(HANDLE h, DWORD length);
    void handleIoCompletion(DWORD bytesTransferred, ULONG_PTR key, OVERLAPPED* ov, DWORD error);
    void writeBatch();                 // pump pending frames into the pipe
    void writeDiagBatch();             // worker-only string emission
    void emitHeartbeat();
    void emitMemory();
    void handleClientRead();           // consumer -> bridge control channel
    void startHeartbeatTimer();
    static std::uint32_t countProcessThreads() noexcept;

    static void CALLBACK timerProc(PVOID param, BOOLEAN);

    // Pipe instance state.
    HANDLE pipeServer_ = INVALID_HANDLE_VALUE;   // the listening instance
    HANDLE pipeClient_ = INVALID_HANDLE_VALUE;   // connected consumer (or INVALID)
    HANDLE iocp_ = nullptr;
    HANDLE stopEvent_ = nullptr;
    HANDLE timer_ = nullptr;
    HANDLE writeEvent_ = nullptr;

    OVERLAPPED ovConnect_{};
    OVERLAPPED ovWrite_{};
    OVERLAPPED ovRead_{};
    bool       writeInFlight_ = false;
    bool       connectInFlight_ = false;
    bool       readInFlight_ = false;

    // Coalesced write buffer: header + N payloads per syscall.
    std::vector<std::uint8_t> writeBuf_;
    std::size_t                writeBufUsed_ = 0;

    std::uint8_t readBuf_[256]{};

    // Double-buffered diag queue so the worker never allocates while writing.

    std::wstring pipePath_;

    std::thread worker_;
    telemetry::SpscQueue<Frame> queue_;

    std::atomic<std::uint32_t> sequence_{0};
    std::atomic<std::uint64_t> accepted_{0};
    std::atomic<std::uint64_t> dropped_{0};
    std::atomic<std::uint64_t> bytesSent_{0};
    std::atomic<std::uint64_t> reconnects_{0};
    std::atomic<std::uint64_t> writeTimeouts_{0};
    std::atomic<std::uint64_t> sessions_{0};
    std::atomic<bool>          running_{false};
    std::atomic<bool>          clientAttached_{false};
    std::atomic<bool>          nameSyncRequested_{false};
    std::atomic<std::uint64_t> startTicks_{0};

    // Coarse counters owned by the hook layer and read (never written) by the
    // worker, so heartbeats can report them without touching game state.
    std::atomic<std::uint32_t> frameCounter_{0};
    std::atomic<float>         frameTimeMs_{0.0f};
    // True only once something has actually reported a frame. Distinguishes
    // "the counter is zero because we are at a menu" from "the counter is
    // zero because nothing is driving it".
    std::atomic<bool>          frameSourceLive_{false};
    std::atomic<std::uint32_t> activeThreads_{0};
    std::atomic<std::uint32_t> queuedThreads_{0};
    std::atomic<std::uint32_t> streamedCells_{0};

    NameTableProvider nameProvider_ = nullptr;
    ReportProvider      reportProvider_ = nullptr;

    // The most recent PluginDiag text, cached so it can be REPLAYED to every
    // newly connected consumer.
    //
    // WHY THIS EXISTS: the bootstrap diagnostic (which reports whether the
    // address database loaded, how many probes resolved, and so on) is emitted
    // once during startup -- before any consumer has connected. The pipe has no
    // replay backlog, so every diagnostic read afterwards saw only the
    // periodic Heartbeat/Memory stream and no explanation of the resolver at
    // all. That made the single most important startup fact unobservable, and
    // it is invisible in exactly the situation you most need it: attaching to
    // an already-running game.
    //
    // Caching the last one and re-emitting it on connect makes the state
    // visible to whoever asks, whenever they ask. A diagnostic that is only
    // available to a consumer that happened to be running at boot is not a
    // diagnostic.
    std::string lastDiagText_;
    std::mutex lastDiagMutex_;
    // Set from the IOCP thread on connect; consumed and acted on by the WORKER
    // thread. A flag rather than a direct publish(), because publishing from
    // the completion handler is a cross-thread write into the ring's producer
    // state; in-game it presented as a hang once the window went idle, and it
    // would have become memory corruption rather than a hang. This mirrors
    // nameSyncRequested_, which exists for exactly the same reason.
    std::atomic<bool>          diagReplayRequested_{false};

    // Injectable clock so tests can be deterministic.
    static double nowSeconds();
    static std::uint64_t qpcTicks();

    LARGE_INTEGER qpcFrequency_{};
    std::uint64_t heartbeatDueNs_ = 0;
    std::uint64_t memoryDueNs_ = 0;
};

} // namespace f4mon::ipc
