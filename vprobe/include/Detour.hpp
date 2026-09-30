// Detour.hpp
//
// Minimal x64 trampoline detours. CommonLibF4's REL::Relocation and F4SE's
// common/ detour both work, but neither tolerates a target that was not
// validated first, and neither reports "I declined to patch this". This one
// does, which is the property that actually matters for a version-agnostic
// probe.
//
// Mechanics: 14-byte absolute indirect jump
//     FF 25 00 00 00 00   jmp qword ptr [rip+0]
//     <8-byte target address>
// placed over the first >=14 bytes of the prologue. If the prologue contains a
// relative call/jmp, the corresponding trampoline byte is rewritten to E9
// (rel32) with the displacement recomputed.
#pragma once

#include <Windows.h>

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace f4mon::hooks {

enum class DetourStatus {
    Ok,
    TargetNull,
    PrologueTooShort,   // fewer than 14 bytes before the first ret/int3 run
    UnsupportedReloc,   // rip-relative operand we cannot rewrite
    AlreadyPatched,
    WriteFailed,
};

class Detour {
public:
    Detour() = default;
    ~Detour() { Detour::remove(); }

    Detour(const Detour&) = delete;
    Detour& operator=(const Detour&) = delete;
    Detour(Detour&& other) noexcept { *this = std::move(other); }
    Detour& operator=(Detour&& other) noexcept {
        if (this != &other) {
            remove();
            target_ = other.target_;
            trampoline_ = other.trampoline_;
            stolen_.assign(other.stolen_.begin(), other.stolen_.end());
            originalBytes_.assign(other.originalBytes_.begin(), other.originalBytes_.end());
            status_ = other.status_;
            other.target_ = nullptr;
            other.trampoline_ = nullptr;
            other.stolen_.clear();
        }
        return *this;
    }

    // `target` must already have passed AddressResolver validation.
    // `hook` is the address execution is redirected to; it must share the
    // calling convention and stack layout of the target (i.e. it is a C++
    // function with the same signature).
    DetourStatus install(void* target, void* hook);

    // Restore the original bytes. Safe to call from a hook that is unwinding.
    void remove();

    // Trampoline address, or nullptr if not installed. Cast back to the
    // original function signature and call it to reach the unhooked code.
    [[nodiscard]] void* trampoline() const noexcept { return trampoline_; }
    [[nodiscard]] void* target() const noexcept { return target_; }
    [[nodiscard]] DetourStatus status() const noexcept { return status_; }

    // Human-readable reason the last install() was refused, e.g.
    // "unsupported instruction at +4: opcode 0xC7 44 24 08 ...". Empty after a
    // successful install. Surfaced through the console commands and the
    // resolver report so a disabled hook says WHICH signature needs work.
    [[nodiscard]] const std::string& lastError() const noexcept { return lastError_; }
    [[nodiscard]] std::size_t stolenLength() const noexcept { return stolen_.size(); }

private:
    void*   target_ = nullptr;
    void*   trampoline_ = nullptr;
    std::vector<std::uint8_t> stolen_{};
    std::vector<std::uint8_t> originalBytes_{};
    std::string lastError_{};
    DetourStatus status_ = DetourStatus::TargetNull;
};

const char* toString(DetourStatus s);

} // namespace f4mon::hooks
