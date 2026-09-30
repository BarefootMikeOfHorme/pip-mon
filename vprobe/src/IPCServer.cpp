// IPCServer.cpp

// Must precede <Windows.h>. PROCESS_MEMORY_COUNTERS::PrivateUsage is gated on
// the target version and is hidden entirely when _WIN32_WINNT is unset, which
// fails the build with "'PrivateUsage' is not a member of
// '_PROCESS_MEMORY_COUNTERS'".
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0A00 // Windows 10
#endif
#ifndef WINVER
#define WINVER 0x0A00
#endif

#include "IPCServer.hpp"
#include "Trace.hpp"

#include <Psapi.h>
#include <TlHelp32.h>

#include <chrono>
#include <cstring>

namespace f4mon::ipc {

namespace {
constexpr std::size_t   kWriteBatchBytes   = 32 * 1024; // one WriteFile per batch
constexpr std::size_t   kHeartbeatPeriodNs = 1'000'000'000ull;
constexpr std::size_t   kMemoryPeriodNs    = 500'000'000ull;
constexpr DWORD         kWriteTimeoutMs    = 250;
constexpr DWORD         kReadTimeoutMs     = 500;
constexpr std::uint64_t kNsPerSec          = 1'000'000'000ull;

// Completion-port keys distinguish operations. The OVERLAPPED pointers are
// reused, so the key is the authoritative discriminant.
enum CpKey : ULONG_PTR {
    kKeyConnect = 1,
    kKeyWrite   = 2,
    kKeyRead    = 3,
};
} // namespace

// ---------------------------------------------------------------------------
// Lifetime
// ---------------------------------------------------------------------------

IPCServer::~IPCServer() { stop(); }

std::uint64_t IPCServer::qpcTicks() {
    LARGE_INTEGER c;
    QueryPerformanceCounter(&c);
    return static_cast<std::uint64_t>(c.QuadPart);
}

double IPCServer::nowSeconds() {
    static const double freq = [] {
        LARGE_INTEGER f;
        QueryPerformanceFrequency(&f);
        return static_cast<double>(f.QuadPart);
    }();
    return static_cast<double>(qpcTicks()) / freq;
}

bool IPCServer::start(const std::wstring& pipePath) {
    if (running_.load(std::memory_order_acquire)) {
        return true;
    }
    pipePath_ = pipePath;

    QueryPerformanceFrequency(&qpcFrequency_);
    writeBuf_.resize(kWriteBatchBytes);
    startTicks_.store(qpcTicks(), std::memory_order_relaxed);

    stopEvent_ = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    if (!stopEvent_) {
        return false;
    }

    iocp_ = CreateIoCompletionPort(INVALID_HANDLE_VALUE, nullptr, 0, 1);
    if (!iocp_) {
        stop();
        return false;
    }

    if (!createPipeInstance()) {
        stop();
        return false;
    }

    // A periodic timer drives heartbeats and memory snapshots. The completion
    // port timer is heavyweight for a 1 Hz tick; a waitable timer posting a
    // no-op key is the cheaper option and keeps the worker responsive to it.
    startHeartbeatTimer();

    running_.store(true, std::memory_order_release);
    worker_ = std::thread([this] { workerMain(); });
    return true;
}

void IPCServer::stop() {
    if (!running_.exchange(false, std::memory_order_acq_rel)) {
        // Still clean up resources in case start() failed midway.
        if (iocp_ || pipeServer_ != INVALID_HANDLE_VALUE) {
            if (pipeServer_ != INVALID_HANDLE_VALUE) { destroyPipe(pipeServer_); pipeServer_ = INVALID_HANDLE_VALUE; }
            if (iocp_) { CloseHandle(iocp_); iocp_ = nullptr; }
            if (stopEvent_) { CloseHandle(stopEvent_); stopEvent_ = nullptr; }
        }
        return;
    }

    if (stopEvent_) {
        SetEvent(stopEvent_);
    }
    if (timer_) {
        CancelWaitableTimer(timer_);
        CloseHandle(timer_);
        timer_ = nullptr;
    }
    if (worker_.joinable()) {
        worker_.join();
    }

    closeClient();
    if (pipeServer_ != INVALID_HANDLE_VALUE) {
        destroyPipe(pipeServer_);
        pipeServer_ = INVALID_HANDLE_VALUE;
    }
    if (iocp_) {
        PostQueuedCompletionStatus(iocp_, 0, 0, nullptr); // unblock GQCS
        CloseHandle(iocp_);
        iocp_ = nullptr;
    }
    if (stopEvent_) {
        CloseHandle(stopEvent_);
        stopEvent_ = nullptr;
    }
    clientAttached_.store(false, std::memory_order_release);
}

// ---------------------------------------------------------------------------
// Pipe instances
// ---------------------------------------------------------------------------

bool IPCServer::createPipeInstance() {
    if (pipeServer_ != INVALID_HANDLE_VALUE) {
        return true;
    }

    // PIPE_UNLIMITED_INSTANCES lets a reconnecting consumer grab the next
    // instance while we tear the old one down.
    pipeServer_ = CreateNamedPipeW(
        pipePath_.c_str(),
        PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED | FILE_FLAG_FIRST_PIPE_INSTANCE,
        PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_UNLIMITED_INSTANCES,
        4,                       // max instances
        kWriteBatchBytes,        // out buffer (consumer read)
        kWriteBatchBytes,        // in buffer (we write)
        kWriteTimeoutMs,         // default timeout
        nullptr);

    if (pipeServer_ == INVALID_HANDLE_VALUE) {
        // ERROR_ACCESS_DENIED with FIRST_PIPE_INSTANCE means another instance
        // (our own previous one) still holds the name. Fall back to a normal
        // instance rather than failing the whole bridge.
        pipeServer_ = CreateNamedPipeW(
            pipePath_.c_str(),
            PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
            PIPE_UNLIMITED_INSTANCES,
            kWriteBatchBytes, kWriteBatchBytes, kWriteTimeoutMs, nullptr);
    }

    if (pipeServer_ == INVALID_HANDLE_VALUE) {
        return false;
    }

    if (!CreateIoCompletionPort(pipeServer_, iocp_, kKeyConnect, 0)) {
        destroyPipe(pipeServer_);
        pipeServer_ = INVALID_HANDLE_VALUE;
        return false;
    }

    queueConnect(pipeServer_);
    return true;
}

void IPCServer::destroyPipe(HANDLE h) noexcept {
    if (h && h != INVALID_HANDLE_VALUE) {
        CancelIoEx(h, nullptr);
        DisconnectNamedPipe(h);
        CloseHandle(h);
    }
}

void IPCServer::queueConnect(HANDLE h) {
    ZeroMemory(&ovConnect_, sizeof(ovConnect_));
    ovConnect_.hEvent = nullptr; // completion-port driven
    ovConnect_.Internal = static_cast<ULONG_PTR>(-1);
    connectInFlight_ = true;

    if (ConnectNamedPipe(h, &ovConnect_)) {
        // Immediate success; the completion still arrives.
        return;
    }
    const DWORD err = GetLastError();
    if (err == ERROR_IO_PENDING) {
        return;
    }
    if (err == ERROR_PIPE_CONNECTED) {
        // Client connected between CreateNamedPipe and ConnectNamedPipe. Synthesise
        // the completion because the API will not post one.
        PostQueuedCompletionStatus(iocp_, 0, kKeyConnect, &ovConnect_);
        return;
    }
    connectInFlight_ = false;
    destroyPipe(h);
    if (h == pipeServer_) {
        pipeServer_ = INVALID_HANDLE_VALUE;
    }
}

void IPCServer::queueWrite(HANDLE h, DWORD length) {
    ZeroMemory(&ovWrite_, sizeof(ovWrite_));
    ovWrite_.Internal = static_cast<ULONG_PTR>(-1);
    writeInFlight_ = true;

    DWORD written = 0;
    if (WriteFile(h, writeBuf_.data(), length, &written, &ovWrite_)) {
        bytesSent_.fetch_add(written, std::memory_order_relaxed);
        return;
    }
    const DWORD err = GetLastError();
    if (err == ERROR_IO_PENDING) {
        return;
    }
    // Hard failure: drop the batch and recycle the instance.
    writeInFlight_ = false;
    writeBufUsed_ = 0;
    closeClient();
    (void)h;
}

void IPCServer::startHeartbeatTimer() {
    timer_ = CreateWaitableTimerW(nullptr, FALSE, nullptr);
    if (!timer_) {
        return;
    }
    LARGE_INTEGER due;
    due.QuadPart = -static_cast<LONGLONG>(kHeartbeatPeriodNs / 100); // 100ms tick
    SetWaitableTimer(timer_, &due, 100, nullptr, nullptr, FALSE);
}

// ---------------------------------------------------------------------------
// Producer path -- called from game threads. Keep this branch-free-ish.
// ---------------------------------------------------------------------------

bool IPCServer::publish(wire::EventType type, const void* payload, std::size_t size) noexcept {
    if (!running_.load(std::memory_order_relaxed) || size > kMaxPayloadBytes) {
        dropped_.fetch_add(1, std::memory_order_relaxed);
        return false;
    }

    Frame f{};
    f.header.magic       = wire::kFrameMagic;
    f.header.version     = wire::kProtocolVersion;
    f.header.eventType   = static_cast<std::uint8_t>(type);
    f.header.flags       = 0;
    f.header.payloadSize = static_cast<std::uint32_t>(size);
    f.header.timestamp   = qpcTicks();
    f.header.sequence    = sequence_.fetch_add(1, std::memory_order_relaxed);
    f.header.threadId    = GetCurrentThreadId();

    if (payload && size) {
        std::memcpy(f.payload, payload, size);
    }

    if (queue_.tryPush(f)) {
        accepted_.fetch_add(1, std::memory_order_relaxed);
        return true;
    }
    dropped_.fetch_add(1, std::memory_order_relaxed);
    return false;
}

bool IPCServer::publish(wire::EventType type, const wire::PluginDiagPayload& diag,
                        std::string_view text) noexcept {
    if (!running_.load(std::memory_order_relaxed) ||
        text.size() + sizeof(diag) > kMaxPayloadBytes) {
        dropped_.fetch_add(1, std::memory_order_relaxed);
        return false;
    }
    // `type` is implied by `diag` for a diag event; the overload exists so call
    // sites read uniformly. It is unused in the body, hence the explicit
    // discard rather than a project-wide warning suppression.
    UNREFERENCED_PARAMETER(type);

    // Cache the most recent diagnostic so a consumer connecting later can be
    // told the current state instead of silently receiving nothing. See the
    // note on lastDiagText_ in IPCServer.hpp for why this is not optional.
    {
        const std::lock_guard<std::mutex> lock(lastDiagMutex_);
        lastDiagText_.assign(text);
    }

    // Build the frame and push it like every other event.
    //
    // THIS USED TO WRITE INTO A diagPending_ DOUBLE-BUFFER THAT NOTHING EVER
    // READ. The diagnostic channel had been dead since it was written: no
    // PluginDiag frame had ever reached the wire, so the resolver report -- the
    // one message that explains a broken runtime -- was silently absent while
    // the pipe looked perfectly healthy. The symptom was misread for months as
    // "the pipe has no replay backlog" and then as "the replay feature is
    // broken"; both were wrong, and the actual defect was that the producer had
    // no consumer at all.
    //
    // The mutex is held across the queue push so two diag publishers (the
    // bootstrap thread and the worker) cannot interleave a ring push. This
    // preserves the ring's single-producer assumption from the diagnostic
    // side; the periodic producers are worker-only and unaffected.
    // The payload header advertises the text length. It is computed HERE
    // rather than trusted from the caller, because every call site was setting
    // it to 0 -- including the 1426-byte resolver report, which therefore
    // arrived on the wire correctly sized but declared an empty body. A consumer
    // reading the header (as the probe does) saw nothing at all, which is how a
    // fully-delivered report stayed invisible.
    //
    // Deriving it in one place also means a new call site cannot reintroduce
    // the bug by forgetting the field; there is nothing to forget.
    wire::PluginDiagPayload hdr = diag;
    hdr.textLength = static_cast<std::uint32_t>(text.size());

    const std::lock_guard<std::mutex> lock(lastDiagMutex_);
    Frame f{};
    f.header.magic       = wire::kFrameMagic;
    f.header.version     = wire::kProtocolVersion;
    f.header.eventType   = static_cast<std::uint8_t>(wire::EventType::PluginDiag);
    f.header.flags       = 0;
    f.header.payloadSize = static_cast<std::uint32_t>(sizeof(hdr) + text.size());
    f.header.timestamp   = qpcTicks();
    f.header.sequence    = sequence_.fetch_add(1, std::memory_order_relaxed);
    f.header.threadId    = GetCurrentThreadId();

    std::memcpy(f.payload, &hdr, sizeof(hdr));
    if (!text.empty()) {
        std::memcpy(f.payload + sizeof(hdr), text.data(), text.size());
    }

    if (queue_.tryPush(f)) {
        accepted_.fetch_add(1, std::memory_order_relaxed);
        return true;
    }
    dropped_.fetch_add(1, std::memory_order_relaxed);
    return false;
}


// ---------------------------------------------------------------------------
// Worker loop
// ---------------------------------------------------------------------------

void IPCServer::workerMain() {
    heartbeatDueNs_ = 0;
    memoryDueNs_    = 0;

    // The startup trace ends at "bootstrap returned", so a crash from here on
    // is invisible without these. The first live crash proved the point: init
    // completed cleanly, 18/18 resolved, and the process died with no record of
    // what it was doing afterwards. Loop counter included so a hang and a crash
    // are distinguishable -- a counter that stops advancing means the loop
    // wedged, which is a different fault and a different fix.
    trace::line("worker: enter, iocp=%p pipe=%p", static_cast<void*>(iocp_),
                static_cast<void*>(pipeServer_));
    std::uint64_t loopCount = 0;
    const ULONGLONG startedTick = GetTickCount64();

    // The periodic state line. This is what the pipe was carrying and what the
    // pipe now cannot carry safely, so it is written to the session file
    // instead. Sampled every ~5s rather than at the 2Hz heartbeat rate, which
    // would be 172,800 lines an hour.
    //
    // The phase is derived, not asserted: a game sitting at a menu reports a
    // frame count of zero, and a game in a world does not. That is a real
    // signal from the engine rather than a label this code invented, which
    // matters because the whole point is to observe rather than to narrate.
    std::uint64_t lastStateLog = 0;

    while (running_.load(std::memory_order_acquire)) {
        // Service the completion port with a bounded wait so the periodic
        // producers (heartbeat/memory) still fire when I/O is idle.
        DWORD       bytes   = 0;
        ULONG_PTR   key     = 0;
        OVERLAPPED* ov      = nullptr;
        const DWORD waitMs  = 50;

        ++loopCount;
        if (loopCount <= 3 || (loopCount % 400) == 0) {
            trace::line("worker: loop %llu waiting",
                        static_cast<unsigned long long>(loopCount));
        }

        const BOOL ok = GetQueuedCompletionStatus(iocp_, &bytes, &key, &ov, waitMs);
        const DWORD err = ok ? ERROR_SUCCESS : GetLastError();

        if (ov) {
            handleIoCompletion(bytes, key, ov, err);
            continue;
        }

        if (!ok && err != WAIT_TIMEOUT) {
            // The port itself is broken; back off briefly and let start()'s
            // error path or a subsequent recreate take over.
            trace::line("worker: iocp error %lu, backing off",
                        static_cast<unsigned long>(err));
            Sleep(100);
            continue;
        }

        // Timeout: pump data and the periodic producers.
        //
        // GATED ON A CONSUMER, and this is a fix rather than an optimisation.
        //
        // The periodic producers used to run unconditionally from loop 1. That
        // means an injected runtime with nobody attached still executed
        // emitMemory() at 2Hz forever, and emitMemory() calls
        // countProcessThreads() -- a CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD)
        // walk over every thread in the system, from inside a heavily modded
        // game process. Five separate live injections each killed the process
        // within about two seconds, INCLUDING runs where no client ever
        // connected to the pipe, which rules the pipe out as the cause and
        // points here.
        //
        // A probe with no consumer should cost nothing. There is no reason to
        // enumerate the thread table for an audience of zero, and the tier rule
        // is explicit that a layer may not be made more expensive than its
        // consumer requires. Now it is quiet until someone is listening, and
        // the state line below reports that honestly instead of reporting a
        // heartbeat nobody asked for.
        if (clientAttached_.load(std::memory_order_acquire)) {
            if ((loopCount % 40) == 0) {
                trace::line("worker: loop %llu writeBatch hb mem",
                            static_cast<unsigned long long>(loopCount));
            }
            writeBatch();
            emitHeartbeat();
            emitMemory();
        } else if (loopCount == 200) {
            trace::line("worker: no consumer attached; periodic producers idle");
        }

        if ((loopCount - lastStateLog) >= 100) {
            lastStateLog = loopCount;
            const std::uint32_t frames = frameCounter_.load(std::memory_order_relaxed);
            const std::uint32_t pap    = activeThreads_.load(std::memory_order_relaxed);
            const std::uint64_t drop   = dropped_.load(std::memory_order_relaxed);
            const float          ft    = frameTimeMs_.load(std::memory_order_relaxed);
            trace::session(frames > 0 ? "IN_GAME" : "MENU",
                           "uptime=%llums frames=%u papyrusThreads=%u frameMs=%.2f "
                           "emitted=%llu dropped=%llu client=%d",
                           static_cast<unsigned long long>(
                               (GetTickCount64() - startedTick) / 1000),
                           frames, pap, static_cast<double>(ft),
                           static_cast<unsigned long long>(
                               accepted_.load(std::memory_order_relaxed)),
                           static_cast<unsigned long long>(drop),
                           clientAttached_.load(std::memory_order_relaxed) ? 1 : 0);
        }

        if (nameSyncRequested_.exchange(false, std::memory_order_acq_rel) && nameProvider_) {
            const std::string json = nameProvider_();
            wire::PluginDiagPayload d{};
            d.level      = wire::DiagLevel::Info;
            d.textLength = 0;
            publish(wire::EventType::PluginDiag, d, json);
        }

        // Replay the last diagnostic to a consumer that has just attached.
        // The snapshot is taken under the lock and RELEASED before publish(),
        // because publish() takes the same lock to cache its own text -- and
        // std::mutex is not recursive, so holding it across the call would
        // self-deadlock. That is not hypothetical: it is exactly what a first
        // draft of this did.
        if (diagReplayRequested_.exchange(false, std::memory_order_acq_rel)) {
            // Prefer a freshly-derived report over the cached last diagnostic.
            // The cache holds whichever diag was published most recently, and
            // at bootstrap that is a greeting rather than the report -- so a
            // consumer attaching later was told nothing about what resolved.
            // The report is derived state, so re-deriving it on request is both
            // more correct and simpler than keeping it cached.
            std::string snapshot;
            if (reportProvider_ != nullptr) {
                snapshot = reportProvider_();
            } else {
                const std::lock_guard<std::mutex> lock(lastDiagMutex_);
                snapshot = lastDiagText_;
            }
            if (!snapshot.empty()) {
                // textLength is derived inside publish(); nothing to set here.
                wire::PluginDiagPayload d{};
                d.level = wire::DiagLevel::Info;
                publish(wire::EventType::PluginDiag, d, snapshot);
            }
        }
    }
}

void IPCServer::handleIoCompletion(DWORD bytesTransferred, ULONG_PTR key, OVERLAPPED* ov, DWORD error) {
    UNREFERENCED_PARAMETER(ov);   // the key discriminates; the OVERLAPPED is not read
    switch (key) {
        case kKeyConnect: {
            connectInFlight_ = false;
            if (error != ERROR_SUCCESS || pipeServer_ == INVALID_HANDLE_VALUE) {
                reconnects_.fetch_add(1, std::memory_order_relaxed);
                return;
            }
            pipeClient_ = pipeServer_;
            pipeServer_ = INVALID_HANDLE_VALUE;
            clientAttached_.store(true, std::memory_order_release);
            sessions_.fetch_add(1, std::memory_order_relaxed);

              writeBufUsed_ = 0;
              nameSyncRequested_.store(true, std::memory_order_release);

              // Replay the cached diagnostic to this new consumer. The periodic
              // stream does not carry resolver state, so without this a client
              // attaching to a running game can never learn whether the address
              // database loaded or what the probe report said.
              //
              // A FLAG, not a publish(). The connect completion runs on the IOCP
              // thread, and publish() writes the diagPending_ double-buffer that
              // the worker's writeBatch() is using. Calling it here raced that
              // and wedged the server -- observed in-game as a hang once the
              // window idled. The worker does the publishing, below.
              diagReplayRequested_.store(true, std::memory_order_release);


            // Immediately queue the read so we notice the consumer vanishing
            // without relying on a write timeout.
            ZeroMemory(&ovRead_, sizeof(ovRead_));
            ovRead_.Internal = static_cast<ULONG_PTR>(-1);
            readInFlight_ = true;
            DWORD got = 0;
            if (!ReadFile(pipeClient_, readBuf_, sizeof(readBuf_), &got, &ovRead_)) {
                const DWORD e = GetLastError();
                if (e == ERROR_IO_PENDING) {
                    break;
                }
                readInFlight_ = false;
                closeClient();
                break;
            }
            break;
        }
        case kKeyWrite: {
            writeInFlight_ = false;
            if (error == ERROR_SUCCESS) {
                bytesSent_.fetch_add(bytesTransferred, std::memory_order_relaxed);
                // Compact: the completed region is now dead space.
                const std::size_t remaining = writeBufUsed_ > bytesTransferred
                                                  ? writeBufUsed_ - bytesTransferred
                                                  : 0;
                if (remaining) {
                    std::memmove(writeBuf_.data(), writeBuf_.data() + bytesTransferred, remaining);
                }
                writeBufUsed_ = remaining;
                writeBatch();
            } else if (error == WAIT_TIMEOUT) {
                writeTimeouts_.fetch_add(1, std::memory_order_relaxed);
                writeBufUsed_ = 0;
                closeClient();
            } else {
                // BROKEN_PIPE / NOT_CONNECTED: consumer died mid-write.
                writeBufUsed_ = 0;
                closeClient();
            }
            break;
        }
        case kKeyRead: {
            readInFlight_ = false;
            if (error != ERROR_SUCCESS || bytesTransferred == 0) {
                closeClient();
                break;
            }
            handleClientRead();
            ZeroMemory(&ovRead_, sizeof(ovRead_));
            ovRead_.Internal = static_cast<ULONG_PTR>(-1);
            readInFlight_ = true;
            DWORD got = 0;
            if (!ReadFile(pipeClient_, readBuf_, sizeof(readBuf_), &got, &ovRead_)) {
                if (GetLastError() != ERROR_IO_PENDING) {
                    readInFlight_ = false;
                    closeClient();
                }
            }
            break;
        }
        default:
            break;
    }

    if (pipeServer_ == INVALID_HANDLE_VALUE) {
        createPipeInstance();
    }
}

void IPCServer::closeClient() noexcept {
    if (pipeClient_ != INVALID_HANDLE_VALUE) {
        destroyPipe(pipeClient_);
        pipeClient_ = INVALID_HANDLE_VALUE;
    }
    clientAttached_.store(false, std::memory_order_release);
    writeInFlight_ = false;
    readInFlight_  = false;
    connectInFlight_ = false;
    writeBufUsed_  = 0;
    reconnects_.fetch_add(1, std::memory_order_relaxed);

    if (pipeServer_ == INVALID_HANDLE_VALUE) {
        createPipeInstance();
    }
}

void IPCServer::handleClientRead() {
    // Control channel. Currently only a NUL-ping heartbeat from the consumer,
    // which we use to prove liveness in the reverse direction. Kept trivial so
    // a slow consumer can never apply backpressure to the game thread.
    (void)readBuf_;
}

// ---------------------------------------------------------------------------
// Batching + periodic producers
// ---------------------------------------------------------------------------

void IPCServer::writeBatch() {
    if (!clientAttached_.load(std::memory_order_acquire) || writeInFlight_) {
        return;
    }
    if (pipeClient_ == INVALID_HANDLE_VALUE) {
        return;
    }
    if (writeBufUsed_ >= kWriteBatchBytes) {
        return;
    }

    Frame f{};
    while (writeBufUsed_ + sizeof(wire::FrameHeader) + kMaxPayloadBytes <= kWriteBatchBytes) {
        if (!queue_.tryPop(f)) {
            break;
        }
        const std::size_t total = sizeof(wire::FrameHeader) + f.header.payloadSize;
        if (writeBufUsed_ + total > kWriteBatchBytes) {
            // Cannot happen given the guard above unless payloadSize was
            // corrupted in transit; drop rather than overrun.
            dropped_.fetch_add(1, std::memory_order_relaxed);
            continue;
        }
        std::memcpy(writeBuf_.data() + writeBufUsed_, &f.header, sizeof(wire::FrameHeader));
        writeBufUsed_ += sizeof(wire::FrameHeader);
        if (f.header.payloadSize) {
            std::memcpy(writeBuf_.data() + writeBufUsed_, f.payload, f.header.payloadSize);
            writeBufUsed_ += f.header.payloadSize;
        }
    }

    if (writeBufUsed_ == 0) {
        return;
    }
    queueWrite(pipeClient_, static_cast<DWORD>(writeBufUsed_));
}

void IPCServer::emitHeartbeat() {
    // Convert QPC ticks to nanoseconds once, on the worker, so the periodic
    // producers never touch the game thread's clock state.
    const std::uint64_t nowNs =
        (qpcTicks() * kNsPerSec) / static_cast<std::uint64_t>(qpcFrequency_.QuadPart);
    if (nowNs < heartbeatDueNs_) {
        return;
    }
    heartbeatDueNs_ = nowNs + kHeartbeatPeriodNs;

    const std::uint64_t startNs =
        (startTicks_.load(std::memory_order_relaxed) * kNsPerSec) /
        static_cast<std::uint64_t>(qpcFrequency_.QuadPart);
    const double uptimeSec = static_cast<double>(nowNs - startNs) / 1e9;

    wire::HeartbeatPayload hb{};
    hb.uptimeSeconds          = uptimeSec;
    hb.gameFrameCount         = frameCounter_.load(std::memory_order_relaxed);
    hb.frameTimeMs            = frameTimeMs_.load(std::memory_order_relaxed);
    hb.activePapyrusThreads   = activeThreads_.load(std::memory_order_relaxed);
    hb.queuedPapyrusThreads   = queuedThreads_.load(std::memory_order_relaxed);
    hb.totalEventsEmitted     = accepted_.load(std::memory_order_relaxed);
    hb.totalEventsDropped     = dropped_.load(std::memory_order_relaxed);
    publish(wire::EventType::Heartbeat, &hb, sizeof(hb));
}

void IPCServer::emitMemory() {
    const std::uint64_t nowNs =
        (qpcTicks() * kNsPerSec) / static_cast<std::uint64_t>(qpcFrequency_.QuadPart);
    if (nowNs < memoryDueNs_) {
        return;
    }
    memoryDueNs_ = nowNs + kMemoryPeriodNs;

    // PrivateUsage lives in PROCESS_MEMORY_COUNTERS_EX, not the base
    // PROCESS_MEMORY_COUNTERS -- using the base struct here fails with
    // "'PrivateUsage' is not a member of '_PROCESS_MEMORY_COUNTERS'".
    PROCESS_MEMORY_COUNTERS_EX pmc{};
    pmc.cb = sizeof(pmc);
    wire::MemoryPayload mp{};
    if (GetProcessMemoryInfo(GetCurrentProcess(),
                             reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&pmc), sizeof(pmc))) {
        mp.workingSetBytes = pmc.WorkingSetSize;
        mp.privateBytes    = pmc.PrivateUsage;
        mp.virtualBytes    = pmc.PagefileUsage;
        mp.peakWorkingSet  = pmc.PeakWorkingSetSize;
    }
    DWORD handles = 0;
    if (GetProcessHandleCount(GetCurrentProcess(), &handles)) {
        mp.handleCount = handles;
    }
    // The hooks own the authoritative Papyrus counters; the process-wide thread
    // count is cheap to enumerate and gives the dashboard a leak signal.
    mp.threadCount        = countProcessThreads();
    mp.papyrusThreadCount = activeThreads_.load(std::memory_order_relaxed);
    mp.streamedCellCount  = streamedCells_.load(std::memory_order_relaxed);
    publish(wire::EventType::Memory, &mp, sizeof(mp));
}

std::uint32_t IPCServer::countProcessThreads() noexcept {
    // Toolhelp32 rather than GetProcessInformation, which needs a larger buffer
    // and gives us nothing extra here. Runs on the worker at 2 Hz.
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (snap == INVALID_HANDLE_VALUE) {
        return 0;
    }
    THREADENTRY32 te{};
    te.dwSize = sizeof(te);
    std::uint32_t count = 0;
    const DWORD pid = GetCurrentProcessId();
    if (Thread32First(snap, &te)) {
        do {
            if (te.th32OwnerProcessID == pid) {
                ++count;
            }
        } while (Thread32Next(snap, &te));
    }
    CloseHandle(snap);
    return count;
}

ServerStats IPCServer::stats() const noexcept {
    ServerStats s;
    s.framesAccepted = accepted_.load(std::memory_order_relaxed);
    s.framesDropped  = dropped_.load(std::memory_order_relaxed) + queue_.dropped();
    s.bytesSent      = bytesSent_.load(std::memory_order_relaxed);
    s.reconnects     = reconnects_.load(std::memory_order_relaxed);
    s.writeTimeouts  = writeTimeouts_.load(std::memory_order_relaxed);
    s.clientSessions = sessions_.load(std::memory_order_relaxed);
    s.clientAttached = clientAttached_.load(std::memory_order_relaxed);
    return s;
}

} // namespace f4mon::ipc
