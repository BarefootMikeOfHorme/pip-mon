// FrameQueue.hpp
//
// Lock-free SPSC ring used to hand frames from the hooked game threads to the
// bridge's IPC worker. The producer side is the only code path the game thread
// touches, and it is strictly: one relaxed atomic store plus a bounds check.
//
// Why SPSC and not MPMC: exactly one consumer (the IPC worker) and the
// producers are serialised by the fact that a given VM thread only publishes
// from its own context. If you later need multiple simultaneous producers,
// swap in a Vyukov MPMC bounded queue -- the interface stays identical.
#pragma once

#include <atomic>
#include <cstdint>
#include <cstring>
#include <memory>

namespace f4mon::telemetry {

inline constexpr std::size_t kDefaultQueueCapacity = 8192; // power of two

template <typename T, std::size_t kCapacity = kDefaultQueueCapacity>
class SpscQueue {
    static_assert(kCapacity >= 2, "capacity too small");
    static_assert((kCapacity & (kCapacity - 1)) == 0, "capacity must be a power of two");

public:
    SpscQueue() = default;
    SpscQueue(const SpscQueue&) = delete;
    SpscQueue& operator=(const SpscQueue&) = delete;

    [[nodiscard]] bool tryPush(const T& item) noexcept {
        const std::size_t head = head_.load(std::memory_order_relaxed);
        const std::size_t next = (head + 1) & (kCapacity - 1);
        if (next == tail_.load(std::memory_order_acquire)) {
            ++dropped_;
            return false; // full: drop, never block the caller
        }
        slots_[head] = item;
        head_.store(next, std::memory_order_release);
        return true;
    }

    [[nodiscard]] bool tryPop(T& out) noexcept {
        const std::size_t tail = tail_.load(std::memory_order_relaxed);
        if (tail == head_.load(std::memory_order_acquire)) {
            return false;
        }
        out = slots_[tail];
        tail_.store((tail + 1) & (kCapacity - 1), std::memory_order_release);
        return true;
    }

    [[nodiscard]] std::size_t size() const noexcept {
        const auto h = head_.load(std::memory_order_acquire);
        const auto t = tail_.load(std::memory_order_acquire);
        return (h - t) & (kCapacity - 1);
    }

    [[nodiscard]] std::uint64_t dropped() const noexcept { return dropped_.load(std::memory_order_relaxed); }
    [[nodiscard]] bool empty() const noexcept { return size() == 0; }

private:
    // C4324: "structure was padded due to alignment specifier". That padding is
    // the entire point -- head_, tail_ and dropped_ sit on separate cache lines
    // so the producer's store and the consumer's load never contend for the
    // same line. Suppressing locally rather than project-wide, so a genuine
    // padding warning elsewhere still fires.
#pragma warning(push)
#pragma warning(disable : 4324)
    alignas(64) std::atomic<std::size_t> head_{0};
    alignas(64) std::atomic<std::size_t> tail_{0};
    alignas(64) std::atomic<std::uint64_t> dropped_{0};
#pragma warning(pop)

    T slots_[kCapacity]{};
};

} // namespace f4mon::telemetry
