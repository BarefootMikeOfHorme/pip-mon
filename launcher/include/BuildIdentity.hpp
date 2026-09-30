// BuildIdentity.hpp
//
// Identifies WHICH Fallout 4 build we are about to instrument, before the
// process is resumed and before a single hook is installed.
//
// Why this exists and why it runs while the game is suspended:
//   Fallout 4 executable builds are version-locked data. A signature that was
//   correct for 1.10.163 will land in the wrong function on 1.10.984. The
//   consequence of guessing wrong is not a bad diagnostic, it is a crash on
//   the next Papyrus call. So the launcher refuses to proceed on a build it
//   cannot positively identify, rather than letting the runtime discover the
//   mismatch after the fact.
//
//   This is the part of the design that replaces F4SE's
//   `f4se_1_10_xxx.dll` -- one binary per game patch, maintained by hand for
//   every release. Here there is ONE runtime binary for every build, plus a
//   table that maps build -> offset profile. An unrecognised build is a
//   clean refusal, not a wrong-address crash.
//
// Two hashes, deliberately different jobs:
//   headerHash  FNV-1a 64 over the DOS + PE headers. Cheap, deterministic, and
//               stable across re-downloads of the same build. Used as the
//               build LOOKUP KEY.
//   contentHash SHA-256 (BCrypt) over the whole file. Costs one linear read,
//               so it is only computed when we are verifying an existing
//               profile rather than discovering a new one. Used for TAMPER
//               detection, not for identity.
#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace f4mon::preflight {

// Header-only view of a mapped PE. Holds borrowed pointers into the mapping,
// so it must not outlive the mapping it was created from.
struct PeView {
    const std::uint8_t* base = nullptr;
    std::size_t         size = 0;

    [[nodiscard]] bool valid() const { return base != nullptr && size != 0; }
};

// Failure reasons are enumerated rather than bool+string so the integrity core
// can decide pass/warn/fail per reason without string matching.
enum class PeVerdict {
    Ok,
    NotPe,                 // MZ or PE\0\0 missing
    Truncated,             // file ends inside a header we needed
    NotX64,                // Machine is not AMD64
    NotPe32Plus,           // optional header magic is not 0x20b
    ImplausibleImage,      // SizeOfImage inconsistent with the file
    IsDll,                 // a library was passed where the game exe was expected
};

[[nodiscard]] const char* toString(PeVerdict v);

// What we learned about a specific executable.
struct BuildIdentity {
    std::wstring path;

    std::uint32_t timeDateStamp = 0;   // PE COFF header
    std::uint16_t majorLinker   = 0;
    std::uint16_t minorLinker   = 0;
    std::uint32_t peChecksum    = 0;   // as stored, NOT recomputed
    std::uint32_t sizeOfImage   = 0;   // virtual
    std::uint32_t sizeOfHeaders = 0;
    std::uint64_t fileSize      = 0;   // on disk
    std::uint16_t characteristics = 0; // COFF characteristics (DLL bit lives here)
    std::uint32_t subsystem     = 0;   // 2 = GUI, 3 = console

    // A launcher that pointed at a DLL would resolve fine and then fail in a
    // far more confusing way later, so the image type is part of identity.
    [[nodiscard]] bool isDll() const { return (characteristics & 0x2000) != 0; }

    std::uint64_t headerHash = 0;     // FNV-1a 64, the build lookup key
    std::string   headerHashHex;      // zero-padded 16 chars

    // Imports found in the import directory. Only the names we actually gate
    // on are collected; this is not a general import lister.
    std::vector<std::string> importedModules;

    [[nodiscard]] bool subsystemIsGui() const { return subsystem == 2; }
};

// Parse a mapped PE. Never throws, never reads out of bounds: every field
// access is bounds-checked against `size`, and a truncated file yields
// `Truncated` rather than a read violation.
[[nodiscard]] PeVerdict parsePe(const PeView& view, BuildIdentity& out);

// Map a file and parse it. `why` receives a human-readable reason on failure.
[[nodiscard]] PeVerdict identifyFile(const std::wstring& path, BuildIdentity& out,
                                     std::wstring& why);

// FNV-1a 64 over the header region. Exposed for the self-test.
[[nodiscard]] std::uint64_t fnv1a64(const std::uint8_t* data, std::size_t len);

// THE BUILD LOOKUP KEY.
//
// The loader rewrites the optional header's ImageBase field in place when it
// relocates an ASLR image. Measured on this machine, those 8 bytes are the ONLY
// difference between the header block on disk and the same block in a running
// process: diffing the two regions byte-by-byte gives exactly four differing
// bytes, all inside ImageBase.
//
// So a naive hash of the header region produces a different key for the same
// build depending on whether you hashed the file or the process, which would
// make the TOCTOU check fail on every honest launch. Both sides therefore
// normalise ImageBase to zero before hashing, and both call THIS function so
// they cannot drift apart again.
//
// `header` is modified in place. `optStart` is the offset of the optional
// header within it.
[[nodiscard]] std::uint64_t buildLookupKey(std::uint8_t* header, std::size_t len,
                                           std::size_t optStart);

// SHA-256 (BCrypt) over a whole file, lower-case hex. Empty on failure.
[[nodiscard]] std::string sha256File(const std::wstring& path);

[[nodiscard]] std::string toHex16(std::uint64_t v);

// Section table, bounds-checked, from an already-validated header.
//
// WHY THIS LIVES HERE AND NOT IN A TOOL
//   A second hand-rolled PE parser was written for tools/sigcheck.cpp and got
//   TimeDateStamp wrong as uint16 instead of uint32, which shifted every field
//   after it and produced a garbage section table while still looking like it
//   worked. There is now exactly ONE PE parser in this project, and it is this
//   one, because it has hostile-input tests behind it. A second copy has no
//   tests and will drift.
struct SectionInfo {
    char        name[9] = {};       // NUL-terminated for printing
    std::uint32_t virtualAddress = 0;
    std::uint32_t virtualSize   = 0;
    std::uint32_t rawPointer    = 0;
    std::uint32_t rawSize       = 0;
    std::uint32_t characteristics = 0;

    [[nodiscard]] bool executable() const {
        return (characteristics & 0x20000000u) != 0;   // IMAGE_SCN_MEM_EXECUTE
    }
    // True when the section's on-disk bytes are actually present. A section
    // with virtualSize but no rawSize occupies no file bytes, and scanning
    // "past the end" of it would read into whatever follows -- producing
    // matches that span a section boundary and look like genuine hits.
    [[nodiscard]] bool hasFileBytes() const { return rawSize != 0; }
};

// Parse the section table. Entries that would fall outside `view` stop the
// scan rather than reading past the mapping. Call after parsePe returned Ok.
[[nodiscard]] std::vector<SectionInfo> parseSections(const PeView& view);

} // namespace f4mon::preflight
