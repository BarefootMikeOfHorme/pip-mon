// Detour.cpp
#include "Detour.hpp"

// Zydis (vendored, MIT): exact x64 instruction lengths. See the comment above
// decode() for why this replaced a hand-rolled decoder.
#include <Zydis/Zydis.h>

#include <cstdio>
#include <cstring>
#include <vector>

namespace f4mon::hooks {

namespace {

constexpr std::size_t kPatchSize = 14; // FF 25 00 00 00 00 + 8-byte literal

// ---------------------------------------------------------------------------
// Instruction decoding: Zydis
// ---------------------------------------------------------------------------
//
// This replaces a hand-rolled x64 length decoder that was correct for a handful
// of prologue opcodes and silently unhandled the rest. The symptom was subtle
// and expensive: `shl rax, 1` (48 D1 E0) was enough to make a detour on a
// trivial four-statement function fail, and every real Papyrus function would
// have hit something unhandled in its first 14 bytes.
//
// It failed SAFE, so nothing crashed -- every probe simply refused to install.
// That is still a broken product, and it is worse than a crash to diagnose
// because it looks like "the signature is wrong".
//
// Bugs found in the old decoder while replacing it, kept here because each one
// is a class of bug a reader will assume is impossible:
//   * `sub rsp, imm8` (48 83 EC xx) computed as 5 bytes instead of 4.
//   * `mov r/m, imm32` (0xC7) treated as having no immediate.
//   * No SIB handling at all, so `mov qword [rsp+8], 0` was 8 bytes, not 9.
//   * `jcc rel8` / `jmp rel8` read as ModRM, which both mis-sized them and
//     marked a 1-byte field for a 4-byte rel32 rewrite -- a corruption path.
//   * The opcode whitelist and the length logic were two separate hand-written
//     lists that had to agree; 0xC7 was in neither consistently.
//
// Zydis is what production hooking code uses, is MIT licensed, and removes the
// entire class. It also gives us RIP-relative detection, which is the one
// property the detour layer genuinely cannot work around.

struct InsnInfo {
    std::size_t length = 0;
    bool        ripRelative = false;
    bool        isRelativeBranch = false;
    std::size_t relOffset = 0;    // byte offset of the 4-byte displacement
    bool        terminator = false; // ret / int3: end of prologue
};

// Decode one instruction at `p`, bounded by `avail` bytes.
//
// Zydis is used for exactly one thing: the instruction LENGTH, which is its
// core competency and the thing that was repeatedly wrong when hand-rolled.
// Everything else here is a direct read of the instruction bytes, because the
// set of encodings the detour layer must handle is small and fixed:
//
//   * relative branches to relocate  -- E8/E9/0F 8x (rel32) only
//   * relative branches to refuse    -- EB/7x/E0-E3 (rel8, unpatchable in place)
//   * RIP-relative memory operands  -- mod==00, rm==101
//   * ret / int3 as a terminator
//
// Keeping those four checks here rather than in Zydis's operand model also
// avoids depending on an API that was substantially reworked in Zydis 4.x,
// which is exactly the kind of churn a safety-critical hook layer should not
// be exposed to.
struct DecoderHandle {
    ZydisDecoder decoder{};
    bool ready = false;

    DecoderHandle() {
        // Zydis 4.x is instance-based: the decoder is configured once, then
        // reused. `ok` is not enough -- a silent failure here would make every
        // decode return length 0, which looks exactly like "every hook is
        // wrong" rather than "the decoder never initialised".
        ready = ZYAN_SUCCESS(ZydisDecoderInit(&decoder, ZYDIS_MACHINE_MODE_LONG_64,
                                              ZYDIS_STACK_WIDTH_64));
    }
};

const DecoderHandle& decoder() {
    static const DecoderHandle h;
    return h;
}

InsnInfo decode(const std::uint8_t* p, std::size_t avail) {
    InsnInfo info;
    if (avail == 0) {
        return info;
    }

    // int3 padding between functions. Zydis decodes it, but we treat it as a
    // terminator so a prologue never steals bytes past a function boundary.
    if (p[0] == 0xCC) {
        info.length = 1;
        info.terminator = true;
        return info;
    }

    const DecoderHandle& h = decoder();
    if (!h.ready) {
        return info;
    }

    ZydisDecodedInstruction insn{};
    ZydisDecoderContext ctx{};
    const ZyanStatus st = ZydisDecoderDecodeInstruction(&h.decoder, &ctx, p, avail, &insn);
    if (!ZYAN_SUCCESS(st) || insn.length == 0 || insn.length > avail) {
        return info; // length 0 -> caller refuses the detour
    }
    info.length = insn.length;

    // --- RIP-relative memory operand: cannot be relocated -----------------
    // mod==00, rm==101 is the canonical RIP-relative encoding. The displacement
    // is measured from the end of the instruction, so moving the bytes to a
    // trampoline invalidates it and the instruction must not be stolen.
    if (insn.raw.modrm.mod == 0 && insn.raw.modrm.rm == 5) {
        info.ripRelative = true;
    }

    // --- relative branches -------------------------------------------------
    // Only the legacy encodings matter; a VEX/EVEX relative branch does not
    // occur in a function prologue.
    const std::uint8_t b0 = p[0];
    const bool twoByte = (b0 == 0x0F) && avail >= 2;

    if (b0 == 0xE8 || b0 == 0xE9) {                 // call/jmp rel32
        info.isRelativeBranch = true;
        info.relOffset = insn.length - 4;
    } else if (twoByte && (p[1] & 0xF0) == 0x80) { // jcc rel32
        info.isRelativeBranch = true;
        info.relOffset = insn.length - 4;
    } else if (b0 == 0xEB || (b0 >= 0x70 && b0 <= 0x7F) ||
               (b0 >= 0xE0 && b0 <= 0xE3)) {
        // rel8: not relocatable in place. The 8-bit field cannot reach the
        // moved target, and expanding it to rel32 would shift instruction
        // boundaries and break the trampoline's byte accounting. Refuse.
        //
        // KNOWN LIMITATION, stated plainly: a function whose first 14 bytes
        // contain a short branch cannot be detoured. Irrelevant for the Papyrus
        // targets (large VM functions, and MSVC emits the rel32 forms for
        // anything spanning more than 127 bytes), but it is the first thing to
        // revisit if a probe that validated cleanly refuses to install in-game.
        return InsnInfo{};
    }

    // --- ret as a prologue terminator --------------------------------------
    if (b0 == 0xC3 || b0 == 0xC2 || b0 == 0xCB || b0 == 0xCA) {
        info.terminator = true;
    }

    return info;
}
// Compute the whole prologue length we need to steal. RIP-relative operands are
// fatal: the trampoline lives at a different address, so we cannot relocate
// them, and a hook that cannot be relocated must not be installed.
//
// `detail` (optional) receives a human-readable explanation of any refusal.
// This is not only a debugging aid: when a probe disables a hook on a new game
// build, "unsupported relocation" tells the user nothing about which signature
// needs updating. The reason text is surfaced through the console commands and
// the resolver report so the failure is actionable.
std::size_t planPrologue(const std::uint8_t* code, std::size_t maxLen,
                         std::string* detail = nullptr) {
    std::size_t taken = 0;
    while (taken < maxLen) {
        // Stop as soon as there is enough to cover the patch. Decoding the whole
        // 32-byte window is both wasteful and WRONG: the window is not the
        // function, so the tail usually ends mid-instruction, the final decode
        // fails, and a perfectly good target is refused because of bytes past
        // the end of the window. This is what made every detour report
        // "unsupported instruction at +30" on a function that was fine.
        if (taken >= kPatchSize) {
            break;
        }
        const InsnInfo info = decode(code + taken, maxLen - taken);
        if (info.length == 0) {
            if (detail) {
                char buf[128];
                _snprintf_s(buf, _TRUNCATE,
                            "unsupported instruction at +%zu: opcode 0x%02X %02X %02X %02X",
                            taken, code[taken], code[taken + 1], code[taken + 2],
                            code[taken + 3]);
                *detail = buf;
            }
            return 0;
        }
        if (info.ripRelative) {
            if (detail) {
                char buf[128];
                _snprintf_s(buf, _TRUNCATE,
                            "RIP-relative operand at +%zu (opcode 0x%02X); cannot be "
                            "relocated to a trampoline",
                            taken, code[taken]);
                *detail = buf;
            }
            return 0;
        }
        taken += info.length;
        if (info.terminator) {
            break;
        }
    }
    if (taken < kPatchSize) {
        if (detail) {
            char buf[96];
            _snprintf_s(buf, _TRUNCATE,
                        "prologue is only %zu bytes; a %zu-byte absolute jump needs at "
                        "least %zu",
                        taken, kPatchSize, kPatchSize);
            *detail = buf;
        }
        return 0;
    }
    return taken;
}

} // namespace

const char* toString(DetourStatus s) {
    switch (s) {
        case DetourStatus::Ok: return "ok";
        case DetourStatus::TargetNull: return "target null";
        case DetourStatus::PrologueTooShort: return "prologue too short";
        case DetourStatus::UnsupportedReloc: return "unsupported relocation";
        case DetourStatus::AlreadyPatched: return "already patched";
        case DetourStatus::WriteFailed: return "write failed";
    }
    return "unknown";
}

DetourStatus Detour::install(void* target, void* hook) {
    remove();
    if (!target) {
        status_ = DetourStatus::TargetNull;
        return status_;
    }
    if (!hook) {
        status_ = DetourStatus::TargetNull;
        return status_;
    }
    target_ = target;

    // Bound the scan window: real prologues are well under 32 bytes.
    constexpr std::size_t kWindow = 32;
    auto* code = static_cast<std::uint8_t*>(target);
    if (IsBadReadPtr(code, kWindow)) {
        status_ = DetourStatus::PrologueTooShort;
        return status_;
    }

    // Refuse if someone already owns the first bytes (re-entrant install, or a
    // conflicting ASI). We treat "starts with our own jump" as already-patched.
    if (code[0] == 0xFF && code[1] == 0x25 && code[2] == 0x00) {
        status_ = DetourStatus::AlreadyPatched;
        return status_;
    }

    std::string why;
    const std::size_t stolenLen = planPrologue(code, kWindow, &why);
    if (stolenLen == 0) {
        lastError_ = why;
        // Two distinct causes with two distinct fixes: "cannot relocate" means
        // the signature matched something we cannot hook, "too short" means it
        // matched a stub rather than the real body. Collapsing them into one
        // status would leave the user guessing which signature to fix.
        status_ = (why.rfind("prologue is only", 0) == 0) ? DetourStatus::PrologueTooShort
                                                         : DetourStatus::UnsupportedReloc;
        return status_;
    }
    lastError_.clear();

    // Allocate an executable trampoline adjacent-ish to nothing in particular;
    // the position does not matter because we fixed up relative branches.
    trampoline_ = VirtualAlloc(nullptr, stolenLen + kPatchSize, MEM_COMMIT | MEM_RESERVE,
                                PAGE_EXECUTE_READWRITE);
    if (!trampoline_) {
        status_ = DetourStatus::WriteFailed;
        return status_;
    }

    stolen_.assign(code, code + stolenLen);
    originalBytes_ = stolen_;

    auto* tramp = static_cast<std::uint8_t*>(trampoline_);
    std::memcpy(tramp, code, stolenLen);

    // Rewrite relative branches in the trampoline so they target the original
    // destination, which is now stolenLen further along in the real function.
    std::size_t off = 0;
    while (off < stolenLen) {
        const InsnInfo info = decode(tramp + off, stolenLen - off);
        if (info.length == 0) {
            break;
        }
        if (info.isRelativeBranch) {
            auto* disp = reinterpret_cast<std::int32_t*>(tramp + off + info.relOffset);
            const std::int64_t branchTarget =
                static_cast<std::int64_t>(reinterpret_cast<std::intptr_t>(code + off + info.relOffset + 4)) + *disp;
            const std::int64_t newTarget = branchTarget + static_cast<std::int64_t>(stolenLen);
            const auto newDisp = static_cast<std::int32_t>(newTarget -
                                                           static_cast<std::int64_t>(
                                                               reinterpret_cast<std::intptr_t>(tramp + off + info.relOffset + 4)));
            *disp = newDisp;
        }
        off += info.length;
    }



    // Append the jump back into the original function, past the stolen bytes.
    //
    // ENCODING, precisely: `FF 25 disp32` is `jmp qword ptr [rip+disp32]` and
    // occupies bytes 0..5. So at execution time rip == back + 6, and with
    // disp32 == 0 the 8-byte target is read from `back + 6`. It must therefore
    // be WRITTEN at offset 6, not 8.
    //
    // Writing it at offset 8 was a genuine, serious bug: the jump read the
    // wrong qword, and the 8-byte store overran both this 14-byte slot and the
    // trampoline's heap allocation. The self-test caught it as an access
    // violation on the trampoline's very first call -- which, left alone,
    // would have crashed the game on the first hook ever installed.
    auto* back = tramp + stolenLen;
    back[0] = 0xFF; back[1] = 0x25; back[2] = 0x00; back[3] = 0x00;
    back[4] = 0x00; back[5] = 0x00; back[6] = 0x00; back[7] = 0x00;
    const auto retAddr = reinterpret_cast<std::uint64_t>(code + stolenLen);
    std::memcpy(back + 6, &retAddr, sizeof(retAddr));

    // Build the 14-byte absolute jump: FF 25 00 00 00 00 <8-byte hook address>.
    // Same encoding, same off-by-two trap: the literal goes at offset 6.
    std::uint8_t patch[kPatchSize];
    patch[0] = 0xFF; patch[1] = 0x25;
    patch[2] = 0x00; patch[3] = 0x00; patch[4] = 0x00; patch[5] = 0x00;
    patch[6] = 0x00; patch[7] = 0x00;
    const auto hookAddr = reinterpret_cast<std::uint64_t>(hook);
    std::memcpy(patch + 6, &hookAddr, sizeof(hookAddr));

    // Write the patch over the target prologue.
    DWORD oldProtect = 0;
    if (!VirtualProtect(code, kPatchSize, PAGE_EXECUTE_READWRITE, &oldProtect)) {
        VirtualFree(trampoline_, 0, MEM_RELEASE);
        trampoline_ = nullptr;
        status_ = DetourStatus::WriteFailed;
        return status_;
    }
    std::memcpy(code, patch, kPatchSize);
    FlushInstructionCache(GetCurrentProcess(), code, kPatchSize);
    DWORD ignored = 0;
    VirtualProtect(code, kPatchSize, oldProtect, &ignored);

    status_ = DetourStatus::Ok;
    return status_;
}

void Detour::remove() {
    if (target_ && !originalBytes_.empty()) {
        DWORD old = 0;
        if (VirtualProtect(target_, originalBytes_.size(), PAGE_EXECUTE_READWRITE, &old)) {
            std::memcpy(target_, originalBytes_.data(), originalBytes_.size());
            FlushInstructionCache(GetCurrentProcess(), target_, originalBytes_.size());
            VirtualProtect(target_, originalBytes_.size(), old, &old);
        }
    }
    if (trampoline_) {
        VirtualFree(trampoline_, 0, MEM_RELEASE);
        trampoline_ = nullptr;
    }
    target_ = nullptr;
    stolen_.clear();
    originalBytes_.clear();
    status_ = DetourStatus::TargetNull;
}

} // namespace f4mon::hooks
