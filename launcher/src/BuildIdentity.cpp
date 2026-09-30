// BuildIdentity.cpp -- see BuildIdentity.hpp for rationale.
#include "BuildIdentity.hpp"

#include <windows.h>

#include <bcrypt.h>

#include <cstdio>
#include <cstring>

namespace f4mon::preflight {
namespace {

// Windows headers disagree with the disk format about the optional header
// size, and IMAGE_NT_HEADERS64 is not safe to copy onto a possibly-short
// buffer. We define the on-disk layout explicitly and read fields by offset so
// that a truncated or hostile file cannot make us trust a field we did not
// actually read.
#pragma pack(push, 1)
struct DosHeader {
    std::uint16_t e_magic;
    std::uint16_t e_cblp, e_cp, e_crlc, e_cparhdr, e_minalloc, e_maxalloc;
    std::uint16_t e_ss, e_sp, e_csum, e_ip, e_cs, e_lfarlc, e_ovno;
    std::uint16_t e_res[4];
    std::uint16_t e_oemid, e_oeminfo;
    std::uint16_t e_res2[10];
    std::int32_t  e_lfanew;   // offset to PE signature
};

struct CoffHeader {
    std::uint16_t machine;
    std::uint16_t numberOfSections;
    std::uint32_t timeDateStamp;
    std::uint32_t pointerToSymbolTable;
    std::uint32_t numberOfSymbols;
    std::uint16_t sizeOfOptionalHeader;
    std::uint16_t characteristics;
};

struct OptHeader64 {
    std::uint16_t magic;
    std::uint8_t  majorLinkerVersion, minorLinkerVersion;
    std::uint32_t sizeOfCode, sizeOfInitializedData, sizeOfUninitializedData;
    std::uint32_t addressOfEntryPoint, baseOfCode;
    std::uint64_t imageBase;
    std::uint32_t sectionAlignment, fileAlignment;
    std::uint16_t majorOperatingSystemVersion, minorOperatingSystemVersion;
    std::uint16_t majorImageVersion, minorImageVersion;
    std::uint16_t majorSubsystemVersion, minorSubsystemVersion;
    std::uint32_t win32VersionValue;
    std::uint32_t sizeOfImage, sizeOfHeaders, checkSum;
    std::uint16_t subsystem, dllCharacteristics;
    std::uint64_t sizeOfStackReserve, sizeOfStackCommit;
    std::uint64_t sizeOfHeapReserve, sizeOfHeapCommit;
    std::uint32_t loaderFlags, numberOfRvaAndSizes;
};
#pragma pack(pop)

// An image is implausible when the virtual size is far smaller than the
// headers, or when a 64-bit image claims less space than its own header
// table. Catches a wrong file (a .pdb, a redist) before it is spawned.
constexpr std::uint32_t kMinPlausibleImage = 0x10000;   // 64 KiB

template <typename T>
[[nodiscard]] bool readAt(const PeView& v, std::size_t off, T& out) {
    if (off > v.size || v.size - off < sizeof(T)) return false;
    std::memcpy(&out, v.base + off, sizeof(T));
    return true;
}

// Import directory walking. The RVA->file-offset map is derived from the
// section table because there is no guarantee SizeOfHeaders covers the whole
// import table.
struct Section {
    std::uint32_t virtualAddress = 0;
    std::uint32_t virtualSize   = 0;
    std::uint32_t rawSize       = 0;
    std::uint32_t rawPointer    = 0;
};

[[nodiscard]] std::uint32_t rvaToOffset(const std::vector<Section>& secs, std::uint32_t rva) {
    for (const Section& s : secs) {
        const std::uint32_t span = s.virtualSize ? s.virtualSize : s.rawSize;
        if (rva >= s.virtualAddress && rva < s.virtualAddress + span) {
            return s.rawPointer + (rva - s.virtualAddress);
        }
    }
    return 0;
}

// Only the modules we gate on. Listing every import of a 90 MB executable
// tells us nothing we act on.
const char* const kInteresting[] = {"KERNEL32.dll", "USER32.dll",  "d3d11.dll",
                                    "dxgi.dll",    "VERSION.dll", "WINMM.dll",
                                    "dinput8.dll", "ADVAPI32.dll"};

[[nodiscard]] bool isInteresting(const char* name) {
    if (name == nullptr) return false;
    for (const char* k : kInteresting) {
        if (_stricmp(k, name) == 0) return true;
    }
    return false;
}

void collectImports(const PeView& v, const std::vector<Section>& secs,
                    std::uint32_t importRva, std::vector<std::string>& out) {
    const std::uint32_t base = rvaToOffset(secs, importRva);
    if (base == 0) return;

    for (std::size_t n = 0; n < 512; ++n) {   // hard cap: never walk a cycle
        const std::size_t descOff = base + n * 20;
        std::uint32_t nameRva = 0;
        std::uint32_t nameOff = 0;
        if (!readAt(v, descOff, nameRva) || !readAt(v, descOff + 12, nameOff)) break;
        if (nameRva == 0 && nameOff == 0) break;   // null terminator

        const std::size_t nameFileOff = rvaToOffset(secs, nameRva);
        if (nameFileOff == 0 || nameFileOff >= v.size) break;
        const char* name = reinterpret_cast<const char*>(v.base + nameFileOff);
        const std::size_t maxLen = v.size - nameFileOff;
        if (maxLen > 64) {
            if (isInteresting(name)) out.emplace_back(name);
        }
    }
}

} // namespace

// Diagnostics are printed with printf("%ls"), so every literal the parser
// produces is widened once here rather than at each call site.
[[nodiscard]] std::wstring widen(const char* s) {
    if (s == nullptr) return {};
    const int n = MultiByteToWideChar(CP_UTF8, 0, s, -1, nullptr, 0);
    if (n <= 1) return {};
    std::wstring w(static_cast<std::size_t>(n - 1), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s, -1, w.data(), n);
    return w;
}

const char* toString(PeVerdict v) {
    switch (v) {
        case PeVerdict::Ok:                return "ok";
        case PeVerdict::NotPe:             return "not a PE image";
        case PeVerdict::Truncated:         return "truncated before required header";
        case PeVerdict::NotX64:            return "not an AMD64 image";
        case PeVerdict::NotPe32Plus:       return "not a PE32+ (64-bit) image";
        case PeVerdict::ImplausibleImage: return "implausible SizeOfImage";
        case PeVerdict::IsDll:           return "this is a DLL, not the game executable";
    }
    return "unknown";
}

std::uint64_t fnv1a64(const std::uint8_t* data, std::size_t len) {
    std::uint64_t h = 0xcbf29ce484222325ULL;
    for (std::size_t i = 0; i < len; ++i) {
        h ^= data[i];
        h *= 0x100000001b3ULL;
    }
    return h;
}

std::uint64_t buildLookupKey(std::uint8_t* header, std::size_t len, std::size_t optStart) {
    // ImageBase lives at optional-header offset 0x18 and is 8 bytes wide.
    // Zeroing it makes the key independent of where the loader happened to
    // relocate the image, so the same build hashes identically whether we read
    // it from disk or from a live process.
    constexpr std::size_t kImageBaseOffset = 0x18;
    constexpr std::size_t kImageBaseSize   = 8;

    if (header != nullptr && optStart + kImageBaseOffset + kImageBaseSize <= len) {
        std::memset(header + optStart + kImageBaseOffset, 0, kImageBaseSize);
    }
    return fnv1a64(header, len);
}

std::string toHex16(std::uint64_t v) {
    char buf[17];
    std::snprintf(buf, sizeof(buf), "%016llx", static_cast<unsigned long long>(v));
    return std::string(buf, 16);
}

PeVerdict parsePe(const PeView& view, BuildIdentity& out) {
    if (!view.valid()) return PeVerdict::NotPe;

    // Check the 2-byte magic BEFORE demanding the full 64-byte DOS header.
    // Otherwise a short non-PE file -- a text config, a .txt the user dragged
    // in by mistake -- is reported as "truncated", which sends them looking for
    // a corrupt download instead of telling them they passed the wrong file.
    std::uint16_t magic = 0;
    if (!readAt(view, 0, magic)) return PeVerdict::Truncated;
    if (magic != IMAGE_DOS_SIGNATURE) return PeVerdict::NotPe;

    DosHeader dos{};
    if (!readAt(view, 0, dos)) return PeVerdict::Truncated;
    if (dos.e_lfanew <= 0) return PeVerdict::NotPe;

    const std::size_t ntOff = static_cast<std::size_t>(dos.e_lfanew);
    std::uint32_t peSig = 0;
    if (!readAt(view, ntOff, peSig)) return PeVerdict::Truncated;
    if (peSig != IMAGE_NT_SIGNATURE) return PeVerdict::NotPe;

    CoffHeader coff{};
    if (!readAt(view, ntOff + 4, coff)) return PeVerdict::Truncated;
    if (coff.machine != IMAGE_FILE_MACHINE_AMD64) return PeVerdict::NotX64;

    const std::size_t optStart = ntOff + 4 + sizeof(CoffHeader);

    // The declared optional-header size must be fully present. This is
    // stricter than "the fields we read happen to fit", and the strictness is
    // load-bearing: the build lookup key is hashed over exactly the header
    // region the file declares, so if we accepted a short file and clamped
    // the length, the SAME build would hash differently depending on whether
    // it had been truncated. A build identity that changes when a file is
    // damaged is worse than no build identity at all.
    if (coff.sizeOfOptionalHeader < sizeof(OptHeader64) ||
        coff.sizeOfOptionalHeader > 0x1000 ||
        optStart + coff.sizeOfOptionalHeader > view.size) {
        return PeVerdict::Truncated;
    }

    OptHeader64 opt{};
    if (!readAt(view, optStart, opt)) return PeVerdict::Truncated;
    if (opt.magic != 0x20b) return PeVerdict::NotPe32Plus;
    if (opt.sizeOfImage < kMinPlausibleImage) return PeVerdict::ImplausibleImage;
    if ((coff.characteristics & IMAGE_FILE_DLL) != 0) return PeVerdict::IsDll;

    out.timeDateStamp = coff.timeDateStamp;
    out.peChecksum    = opt.checkSum;
    out.sizeOfImage   = opt.sizeOfImage;
    out.sizeOfHeaders = opt.sizeOfHeaders;
    out.characteristics = coff.characteristics;
    out.subsystem     = opt.subsystem;
    out.majorLinker   = opt.majorLinkerVersion;
    out.minorLinker   = opt.minorLinkerVersion;
    out.fileSize      = view.size;

    // Hash the declared header block only: DOS header, PE signature, COFF
    // header, optional header. Section contents are excluded so a repacked but
    // equivalent build still matches, and buildLookupKey normalises ImageBase
    // so the key agrees with the one computed from a live process.
    const std::size_t hashLen = optStart + coff.sizeOfOptionalHeader;
    std::vector<std::uint8_t> header(hashLen);
    std::memcpy(header.data(), view.base, hashLen);
    out.headerHash    = buildLookupKey(header.data(), header.size(), optStart);
    out.headerHashHex = toHex16(out.headerHash);

    // Section table, then the import directory.
    std::vector<Section> secs;
    const std::size_t secTab   = optStart + coff.sizeOfOptionalHeader;
    const std::size_t secCount = (coff.numberOfSections < 96) ? coff.numberOfSections : 0;
    for (std::size_t i = 0; i < secCount; ++i) {
        const std::size_t o = secTab + i * 40;
        std::uint32_t vSize = 0, vAddr = 0, rawSize = 0, rawPtr = 0;
        if (!readAt(view, o + 8, vSize) || !readAt(view, o + 12, vAddr) ||
            !readAt(view, o + 16, rawSize) || !readAt(view, o + 20, rawPtr)) {
            break;
        }
        secs.push_back({vAddr, vSize, rawSize, rawPtr});
    }

    // Data directory entry 1 is the import table. It lives in the optional
    // header at a fixed offset for PE32+.
    if (opt.numberOfRvaAndSizes > 1) {
        std::uint32_t importRva = 0;
        const std::size_t ddOff = ntOff + 4 + sizeof(CoffHeader) + 112 + 8;  // dir[1]
        if (readAt(view, ddOff, importRva) && importRva != 0) {
            collectImports(view, secs, importRva, out.importedModules);
        }
    }

    return PeVerdict::Ok;
}

std::vector<SectionInfo> parseSections(const PeView& view) {
    std::vector<SectionInfo> out;
    if (!view.valid() || view.size < sizeof(DosHeader)) return out;

    DosHeader dos{};
    if (!readAt(view, 0, dos) || dos.e_magic != IMAGE_DOS_SIGNATURE) return out;

    const std::size_t ntOff = static_cast<std::size_t>(dos.e_lfanew);
    CoffHeader coff{};
    if (!readAt(view, ntOff + 4, coff)) return out;

    const std::size_t secTab   = ntOff + 4 + sizeof(CoffHeader) + coff.sizeOfOptionalHeader;
    const std::size_t secCount = (coff.numberOfSections < 96) ? coff.numberOfSections : 0;

    for (std::size_t i = 0; i < secCount; ++i) {
        const std::size_t o = secTab + i * 40;
        SectionInfo s;
        std::uint32_t vSize = 0, vAddr = 0, rawSize = 0, rawPtr = 0, chars = 0;
        if (!readAt(view, o + 8, vSize) || !readAt(view, o + 12, vAddr) ||
            !readAt(view, o + 16, rawSize) || !readAt(view, o + 20, rawPtr) ||
            !readAt(view, o + 36, chars)) {
            break;   // truncated section table: stop, do not guess
        }
        char nameBytes[8] = {};
        if (!readAt(view, o, nameBytes)) break;
        std::memcpy(s.name, nameBytes, 8);
        s.name[8] = '\0';
        // A name can contain no terminator at all (all 8 bytes used), so trim
        // trailing junk rather than relying on NUL.
        for (int k = 7; k >= 0 && (s.name[k] == '\0' || s.name[k] == ' '); --k) {
            s.name[k] = '\0';
        }

        s.virtualAddress = vAddr;
        s.virtualSize   = vSize;
        s.rawPointer    = rawPtr;
        s.rawSize       = rawSize;
        s.characteristics = chars;
        out.push_back(s);
    }
    return out;
}

PeVerdict identifyFile(const std::wstring& path, BuildIdentity& out, std::wstring& why) {
    out = BuildIdentity{};
    out.path = path;

    HANDLE h = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
        why = L"cannot open (error " + std::to_wstring(GetLastError()) + L")";
        return PeVerdict::NotPe;
    }

    LARGE_INTEGER li{};
    if (!GetFileSizeEx(h, &li) || li.QuadPart <= 0) {
        CloseHandle(h);
        why = L"zero-length or unmeasurable";
        return PeVerdict::NotPe;
    }

    const std::size_t size = static_cast<std::size_t>(li.QuadPart);
    HANDLE mapping = CreateFileMappingW(h, nullptr, PAGE_READONLY, 0, 0, nullptr);
    CloseHandle(h);
    if (mapping == nullptr) {
        why = L"cannot map (error " + std::to_wstring(GetLastError()) + L")";
        return PeVerdict::Truncated;
    }

    const auto* base = static_cast<const std::uint8_t*>(
        MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0));
    if (base == nullptr) {
        CloseHandle(mapping);
        why = L"cannot map view (error " + std::to_wstring(GetLastError()) + L")";
        return PeVerdict::Truncated;
    }

    const PeView view{base, size};
    const PeVerdict verdict = parsePe(view, out);
    if (verdict != PeVerdict::Ok) {
        why = widen(toString(verdict));
    } else if (out.sizeOfImage > 0 && size > out.sizeOfImage) {
        // On-disk larger than virtual is legal for a few overlay-appended
        // formats but is a strong signal we were handed the wrong file.
        why = L"file larger than its own image; likely not the game";
    }

    UnmapViewOfFile(base);
    CloseHandle(mapping);
    return verdict;
}

std::string sha256File(const std::wstring& path) {
    HANDLE h = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return {};

    BCRYPT_ALG_HANDLE alg = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    std::string hex;
    std::vector<std::uint8_t> buffer(1 << 20);

    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0) {
        CloseHandle(h);
        return {};
    }
    if (BCryptCreateHash(alg, &hash, nullptr, 0, nullptr, 0, 0) < 0) {
        BCryptCloseAlgorithmProvider(alg, 0);
        CloseHandle(h);
        return {};
    }

    bool ok = true;
    for (;;) {
        DWORD got = 0;
        if (!ReadFile(h, buffer.data(), static_cast<DWORD>(buffer.size()), &got, nullptr)) {
            ok = false;
            break;
        }
        if (got == 0) break;
        if (BCryptHashData(hash, buffer.data(), got, 0) < 0) {
            ok = false;
            break;
        }
    }

    if (ok) {
        // The 4th parameter of BCryptFinishHash is dwFlags, not an out-count,
        // so the digest length has to come from the provider, not from the
        // call. Assuming 32 would be wrong for any future algorithm swap.
        ULONG digestLen = 0, lenBytes = sizeof(digestLen), got = 0;
        if (BCryptGetProperty(hash, BCRYPT_HASH_LENGTH,
                              reinterpret_cast<PUCHAR>(&digestLen), lenBytes, &got, 0) < 0 ||
            digestLen == 0 || digestLen > 64) {
            ok = false;
            digestLen = 0;
        }

        std::uint8_t digest[64] = {};
        if (ok && BCryptFinishHash(hash, digest, digestLen, 0) >= 0) {
            static const char* kHex = "0123456789abcdef";
            hex.reserve(digestLen * 2);
            for (ULONG i = 0; i < digestLen; ++i) {
                hex.push_back(kHex[digest[i] >> 4]);
                hex.push_back(kHex[digest[i] & 0x0f]);
            }
        } else {
            ok = false;
        }
    }

    if (hash) BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(alg, 0);
    CloseHandle(h);
    return ok ? hex : std::string{};
}

} // namespace f4mon::preflight
