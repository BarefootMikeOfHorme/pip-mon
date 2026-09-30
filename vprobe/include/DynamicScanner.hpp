// PatternScanner.hpp
//
// Address Library is the fast path, but it goes stale whenever:
//
//   * a new game build lands and the INI has no entry yet,
//   * a runtime patch shifts the target (Script Extender plugins, ASI loaders,
//     Bethesda's own Next Gen retargeting),
//   * the user runs a private/localized executable.
//
// AOB scanning is the safety net. This scanner is deliberately paranoid: every
// candidate is validated against a module-relative RVA whitelist, and a hit that
// lands inside a non-executable section or outside the main module is rejected.
// That is what stops "loads safely without crashing on unmapped runtime patches".
#pragma once

#include <Windows.h>

#include <cstdint>
#include <cstring>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace f4mon::scan {

// A parsed pattern. `??` is a full wildcard, `?` a single-nibble nibble match.
struct BytePattern {
    std::vector<std::uint8_t> bytes;    // concrete bytes, 0x00 where masked
    std::vector<std::uint16_t> masks;   // 0x00FF = both nibbles must match
    std::size_t length = 0;

    [[nodiscard]] std::string describe() const;
};

// "48 8B ?? 5B C3" / "488B??5BC3" -> BytePattern
[[nodiscard]] std::optional<BytePattern> parsePattern(std::string_view pattern);

// Any executable section of a loaded module, as [begin, end) pairs.
struct ModuleRange {
    HMODULE handle = nullptr;
    std::string name;
    std::uint64_t base = 0;
    // Total mapped image size, needed to tell "inside the image but not
    // executable" (a thunk, tolerated) from "outside the image" (corruption or
    // simply the wrong address, rejected). Without it a vtable check cannot
    // distinguish the two.
    std::uint64_t imageSize = 0;
    std::vector<std::pair<std::uint8_t*, std::uint8_t*>> execSections;
};

[[nodiscard]] std::optional<ModuleRange> describeModule(const char* moduleName);

struct ScanResult {
    std::uint8_t* address = nullptr;
    std::uint32_t rva = 0;
    std::size_t   matchCount = 0;   // >1 means "ambiguous", caller should refuse
    bool          exact = true;     // matched the pattern verbatim at that RVA
};

// Scans a single module's executable sections. Returns nullopt on zero hits or
// on ambiguity when `requireUnique` is set.
[[nodiscard]] std::optional<ScanResult> scanModule(const ModuleRange& mod,
                                                   const BytePattern& pattern,
                                                   bool requireUnique = true);

// Scans all executable sections of Fallout4.exe plus any module whose name
// contains one of `extraModuleHints` (e.g. "f4se_loader", "AddressLib").
[[nodiscard]] std::optional<ScanResult> scanGameAndPlugins(const BytePattern& pattern,
                                                           const std::vector<std::string>& extraModuleHints = {});

// Post-hit validation. A candidate must:
//   * sit inside an executable section we scanned,
//   * sit at a plausible function boundary for its own class (see classify),
//   * and pass the caller's semantic probe.
// The RVA ceiling guards against a match in a string table that happens to be
// mapped executable.
[[nodiscard]] bool isPlausibleCodeAddress(const ModuleRange& mod, std::uint8_t* address);

// A vtable is not code, and the code check is actively wrong for it.
//
// isPlausibleCodeAddress requires the address to be inside an EXECUTABLE
// section and to look like a function entry. A vtable lives in read-only data
// (.rdata), so every genuine vtable fails both tests. That is not a near miss:
// running the check on the first vtable database entries rejected 100% of them,
// which would have looked like "the database is bad" rather than "the
// validator assumes the wrong thing".
//
// So vtables get their own check, and it is STRONGER than the code one rather
// than merely weaker. "This pointer is in a readable section" proves almost
// nothing -- any address in the image satisfies it. What actually identifies a
// vtable is that it is a run of POINTERS INTO EXECUTABLE CODE. A random
// address in .rdata fails this immediately; a real vtable passes.
//
// `requiredSlots` is the number of consecutive pointers to require. Demanding
// a high count is the difference between "points at something executable" and
// "is a method table", and it is what keeps a single coincidental pointer
// from passing as a vtable.
[[nodiscard]] bool isPlausibleVTableAddress(const ModuleRange& mod, std::uint8_t* address,
                                            std::size_t requiredSlots = 4);

// Prologues we accept as a function entry: push rbp / mov rbp,rsp / sub rsp,
// plus the hot-patch NOP/INT3 forms. Deliberately conservative.
[[nodiscard]] bool looksLikeFunctionEntry(const std::uint8_t* address);

} // namespace f4mon::scan
