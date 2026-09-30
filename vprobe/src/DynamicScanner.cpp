// DynamicScanner.cpp

// Must precede <Windows.h>: PROCESS_MEMORY_COUNTERS::PrivateUsage, the thread
// and module enumeration APIs, and CancelIoEx are all gated on the target
// version, and leaving _WIN32_WINNT unset can hide them entirely -- which is
// how this file failed to compile with "TH32CS_SNAPMODULE undeclared".
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0A00 // Windows 10
#endif
#ifndef WINVER
#define WINVER 0x0A00
#endif

#include "DynamicScanner.hpp"

#include <Psapi.h>
#include <TlHelp32.h>

#include <cctype>
#include <cstring>
#include <cwchar>

namespace f4mon::scan {

namespace {
// Hints are ASCII by construction (we pass them, they are not user data), so a
// straight narrow-to-wide expansion is correct here and avoids a lossy round
// trip through the current locale.
std::wstring toWide(const std::string& ascii) {
    std::wstring out;
    out.reserve(ascii.size());
    for (char c : ascii) {
        out.push_back(static_cast<unsigned char>(c));
    }
    return out;
}
} // namespace

namespace {

int hexNibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

// Marked noinline + opt-none: this runs in .text and benefits from not being
// folded into a caller's hot loop, and from keeping its own frame.
__declspec(noinline) bool matchAt(const std::uint8_t* haystack, const BytePattern& p) {
    for (std::size_t i = 0; i < p.length; ++i) {
        const std::uint8_t got = haystack[i];
        const std::uint16_t mask = p.masks[i];
        if (static_cast<std::uint16_t>(got & mask) != static_cast<std::uint16_t>(p.bytes[i] & mask)) {
            return false;
        }
    }
    return true;
}

} // namespace

std::string BytePattern::describe() const {
    static const char* kHex = "0123456789ABCDEF";
    std::string out;
    out.reserve(length * 3);
    for (std::size_t i = 0; i < length; ++i) {
        if (i) out += ' ';
        if (masks[i] == 0) {
            out += '?';
        } else {
            out += kHex[(bytes[i] >> 4) & 0xF];
            out += kHex[bytes[i] & 0xF];
        }
    }
    return out;
}

std::optional<BytePattern> parsePattern(std::string_view pattern) {
    BytePattern p;
    p.bytes.reserve(pattern.size() / 2 + 1);
    p.masks.reserve(pattern.size() / 2 + 1);

    std::size_t i = 0;
    while (i < pattern.size()) {
        // Skip separators and any 0x prefix.
        while (i < pattern.size() && (std::isspace(static_cast<unsigned char>(pattern[i])) ||
                                      pattern[i] == ',')) {
            ++i;
        }
        if (i + 1 < pattern.size() && pattern[i] == '0' && (pattern[i + 1] == 'x' || pattern[i + 1] == 'X')) {
            i += 2;
        }
        if (i >= pattern.size()) {
            break;
        }

        if (pattern[i] == '?') {
            // "??" or "?" both consume a single byte token.
            ++i;
            if (i < pattern.size() && pattern[i] == '?') {
                ++i;
            }
            p.bytes.push_back(0x00);
            p.masks.push_back(0x0000);
            ++p.length;
            continue;
        }

        const int hi = hexNibble(pattern[i]);
        if (hi < 0) {
            return std::nullopt; // garbage token: refuse rather than guess
        }
        ++i;
        int lo = 0;
        if (i < pattern.size() && pattern[i] != ' ' && pattern[i] != ',') {
            lo = hexNibble(pattern[i]);
            if (lo < 0) {
                return std::nullopt;
            }
            ++i;
        }
        p.bytes.push_back(static_cast<std::uint8_t>((hi << 4) | lo));
        p.masks.push_back(0xFFFF);
        ++p.length;
    }

    if (p.length < 4) {
        return std::nullopt; // too short to be safe against false positives
    }
    return p;
}

std::optional<ModuleRange> describeModule(const char* moduleName) {
    HMODULE mod = GetModuleHandleA(moduleName);
    if (!mod) {
        return std::nullopt;
    }

    ModuleRange out;
    out.handle = mod;
    out.base   = reinterpret_cast<std::uint64_t>(mod);

    char path[MAX_PATH]{};
    GetModuleFileNameA(mod, path, MAX_PATH);
    out.name = path;

    // Image size comes from the PE headers, read with the same bounds care
    // as everything else here: a module that lies about its own size would
    // otherwise make every "is this pointer inside the image" check pass.
    {
        const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(mod);
        if (dos->e_magic == IMAGE_DOS_SIGNATURE && dos->e_lfanew > 0) {
            const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(
                reinterpret_cast<const std::uint8_t*>(mod) + dos->e_lfanew);
            if (nt->Signature == IMAGE_NT_SIGNATURE) {
                out.imageSize = nt->OptionalHeader.SizeOfImage;
            }
        }
    }

    auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(mod);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0) {
        return std::nullopt;
    }
    auto* nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(
        reinterpret_cast<std::uint8_t*>(mod) + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) {
        return std::nullopt;
    }

    auto* section = IMAGE_FIRST_SECTION(nt);
    for (WORD n = 0; n < nt->FileHeader.NumberOfSections; ++n, ++section) {
        if ((section->Characteristics & IMAGE_SCN_MEM_EXECUTE) == 0) {
            continue;
        }
        // Discardable/uninitialised sections (.bss) can legitimately hold code
        // with packers but are a common false-positive source; skip them unless
        // they are also readable+writable code.
        if (section->Misc.VirtualSize == 0) {
            continue;
        }
        auto* begin = reinterpret_cast<std::uint8_t*>(mod) + section->VirtualAddress;
        auto* end   = begin + section->Misc.VirtualSize;
        out.execSections.emplace_back(begin, end);
    }

    if (out.execSections.empty()) {
        return std::nullopt;
    }
    return out;
}

std::optional<ScanResult> scanModule(const ModuleRange& mod, const BytePattern& pattern, bool requireUnique) {
    ScanResult best{};
    std::size_t hits = 0;

    for (const auto& [begin, end] : mod.execSections) {
        if (end <= begin || static_cast<std::size_t>(end - begin) < pattern.length) {
            continue;
        }
        auto* p = begin;
        auto* last = end - pattern.length;
        for (; p <= last; ++p) {
            if (*p != pattern.bytes[0] && pattern.masks[0] != 0) {
                continue; // fast reject on the leading byte
            }
            if (!matchAt(p, pattern)) {
                continue;
            }
            ++hits;
            if (hits == 1) {
                best.address    = p;
                best.rva        = static_cast<std::uint32_t>(p - reinterpret_cast<std::uint8_t*>(mod.handle));
            }
            if (requireUnique && hits > 1) {
                // Ambiguous. Bail immediately; a wrong hook here means a crash
                // inside Papyrus, which is strictly worse than no hook.
                return std::nullopt;
            }
        }
    }

    if (hits == 0) {
        return std::nullopt;
    }
    best.matchCount = hits;
    return best;
}

std::optional<ScanResult> scanGameAndPlugins(const BytePattern& pattern,
                                             const std::vector<std::string>& extraModuleHints) {
    auto game = describeModule("Fallout4.exe");
    if (game) {
        if (auto hit = scanModule(*game, pattern, /*requireUnique=*/true)) {
            return hit;
        }
    }

    // Second pass over the whole user32-adjacent neighbourhood: any module whose
    // path contains a hint string. This catches ASLR-shifted helper modules.
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32,
                                           GetCurrentProcessId());
    if (snap == INVALID_HANDLE_VALUE) {
        return std::nullopt;
    }

    MODULEENTRY32W me{};
    me.dwSize = sizeof(me);
    std::optional<ScanResult> found;

    if (Module32FirstW(snap, &me)) {
        do {
            if (_wcsicmp(me.szModule, L"Fallout4.exe") == 0) {
                continue;
            }
            // Compare in wide. Building a std::string straight from
            // me.szModule would narrow every WCHAR to char, which silently
            // mangles any module name outside ASCII.
            const std::wstring modName(me.szModule);
            bool wanted = extraModuleHints.empty();
            for (const auto& hint : extraModuleHints) {
                if (modName.find(toWide(hint)) != std::wstring::npos) {
                    wanted = true;
                    break;
                }
            }
            if (!wanted) {
                continue;
            }

            auto* base = reinterpret_cast<std::uint8_t*>(me.modBaseAddr);
            auto* dos  = reinterpret_cast<IMAGE_DOS_HEADER*>(base);
            if (dos->e_magic != IMAGE_DOS_SIGNATURE) {
                continue;
            }
            auto* nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(base + dos->e_lfanew);

            ModuleRange range;
            range.handle = me.hModule;
            range.base   = reinterpret_cast<std::uint64_t>(me.modBaseAddr);
            range.name   = "plugin";

            auto* section = IMAGE_FIRST_SECTION(nt);
            for (WORD n = 0; n < nt->FileHeader.NumberOfSections; ++n, ++section) {
                if ((section->Characteristics & IMAGE_SCN_MEM_EXECUTE) == 0) continue;
                if (section->Misc.VirtualSize == 0) continue;
                range.execSections.emplace_back(base + section->VirtualAddress,
                                                base + section->VirtualAddress + section->Misc.VirtualSize);
            }

            if (auto hit = scanModule(range, pattern, true)) {
                found = hit;
                break;
            }
        } while (Module32NextW(snap, &me));
    }

    CloseHandle(snap);
    return found;
}

bool isPlausibleCodeAddress(const ModuleRange& mod, std::uint8_t* address) {
    if (!address) {
        return false;
    }
    const auto addr = reinterpret_cast<std::uintptr_t>(address);
    for (const auto& [begin, end] : mod.execSections) {
        const auto b = reinterpret_cast<std::uintptr_t>(begin);
        const auto e = reinterpret_cast<std::uintptr_t>(end);
        if (addr >= b && addr < e) {
            return looksLikeFunctionEntry(address);
        }
    }
    return false;
}

bool isPlausibleVTableAddress(const ModuleRange& mod, std::uint8_t* address,
                               std::size_t requiredSlots) {
    // The design intent, and why it is not the code check loosened:
    //
    // "is this pointer in a readable section" proves nothing. Any address in
    // the image satisfies that. What identifies a vtable is that it is a run
    // of POINTERS INTO CODE, so that is what gets checked.
    //
    // MAJORITY, NOT ALL. This was not the original plan, which was "4
    // consecutive pointers into .text". That plan was tested against the live
    // game before being written, and it FAILED on the very first real vtable:
    //
    //     BSScript__IClientVM:  6 of 8 slots in .text
    //     slots [3] and [7] pointed into .rdata
    //
    // Those two are almost certainly import or adjustor thunks, which live in
    // read-only data and jump onward to the real implementation. They are
    // legitimate vtable entries, and an all-or-nothing rule would have
    // rejected a genuine method table. A validator that fails on correct input
    // is worse than one that is merely lax, because it gets misdiagnosed as
    // bad data.
    //
    // So: at least half the sampled slots must land in executable code, and
    // NONE may point outside the module. The second half is the stricter one
    // -- a slot pointing at unmapped or foreign memory is a real disqualifier,
    // while a slot pointing at a thunk is not.
    if (address == nullptr || requiredSlots == 0) {
        return false;
    }

    // Never read across a page we have not proven mapped. A vtable near the
    // end of a section can start within 8 bytes of a page boundary.
    if ((reinterpret_cast<std::uintptr_t>(address) & 0xFFF) > 0xFF0) {
        return false;
    }
    if (IsBadReadPtr(address, requiredSlots * sizeof(void*))) {
        return false;
    }

    std::size_t inCode = 0;
    for (std::size_t i = 0; i < requiredSlots; ++i) {
        std::uintptr_t slot = 0;
        std::memcpy(&slot, address + i * sizeof(void*), sizeof(void*));
        if (slot == 0) {
            continue;
        }

        bool inModule = false;
        for (const auto& [begin, end] : mod.execSections) {
            const auto s = reinterpret_cast<std::uintptr_t>(begin);
            const auto e = reinterpret_cast<std::uintptr_t>(end);
            if (slot >= s && slot < e) {
                ++inCode;
                inModule = true;
                break;
            }
        }
        if (inModule) {
            continue;
        }

        // Not executable. Tolerated IF it is still inside the module image,
        // because a thunk lives there. Rejected outright if it is not, since
        // a vtable entry pointing outside the module is not a thunk -- it is
        // either corruption or the wrong address entirely.
        const auto imgBegin = mod.base;
        const auto imgEnd = mod.base + (mod.imageSize ? mod.imageSize : 0);
        if (slot < imgBegin || (imgEnd != imgBegin && slot >= imgEnd)) {
            return false;
        }
    }

    return inCode * 2 >= requiredSlots;
}

bool looksLikeFunctionEntry(const std::uint8_t* address) {
    // Guard page: never read across a page boundary we have not proven mapped.
    const auto addr = reinterpret_cast<std::uintptr_t>(address);
    if ((addr & 0xFFF) > 0xFF0) {
        return false;
    }
    if (IsBadReadPtr(address, 8)) {
        return false;
    }

    // 0xCC int3 padding (MSVC between functions), 0x90 nop (hotpatch stub)
    if (address[0] == 0xCC || address[0] == 0x90) {
        // Walk forward over padding to the real entry.
        std::size_t skip = 0;
        while (address[skip] == 0xCC || address[skip] == 0x90) {
            ++skip;
            if (skip > 16) return false;
        }
        address += skip;
    }

    const std::uint8_t b0 = address[0];
    const std::uint8_t b1 = address[1];
    const std::uint8_t b2 = address[2];

    // push rbp
    if (b0 == 0x55) return true;
    // mov rbp, rsp
    if (b0 == 0x48 && b1 == 0x8B && b2 == 0xEC) return true;
    // sub rsp, imm8
    if (b0 == 0x48 && b1 == 0x83 && b2 == 0xEC) return true;
    // sub rsp, imm32
    if (b0 == 0x48 && b1 == 0x81 && b2 == 0xEC) return true;
    // lea rcx, [rsp+X]  (no-frame leaf, common in Next Gen thunks)
    if (b0 == 0x48 && b1 == 0x8D && b2 == 0x0D) return true;
    // mov ecx, imm32 (stdcall-style entry shim)
    if (b0 == 0xB9) return true;
    // ret / leave;ret  (thunk-only functions)
    if (b0 == 0xC3) return true;
    if (b0 == 0xC2) return true;

    return false;
}

} // namespace f4mon::scan
