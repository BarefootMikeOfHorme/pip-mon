// sigcheck.cpp -- scan a real Fallout4.exe for our AOB signatures.
//
// WHY THIS TOOL EXISTS
//   Every signature in Signatures.hpp was written from documentation and
//   inference, never validated. Roadmap item C4 has been blocked on "is a real
//   Fallout4.exe available" for the whole project, and until this ran, the
//   honest status of every signature was [DESIGNED] / unverified -- which
//   means the entire hook layer was an assumption.
//
//   This is a static, read-only scan of the file on disk. It does not launch
//   the game, does not attach, and cannot touch the user's saves. It answers
//   exactly one question per signature: does this byte pattern occur in the
//   real .text section, and how many times?
//
// WHY MULTIPLICITY MATTERS MORE THAN PRESENCE
//   A signature that matches once is probably right. A signature that matches
//   thirty times is useless, and a signature that matches ZERO times on a
//   build we are about to instrument is worse than useless -- it is a hook
//   that will silently never install. The count is the finding; presence alone
//   would let a green tick hide a signature that matches the wrong function
//   three hundred times over.
//
// WHY "probably right" IS NOT "RIGHT"
//   A single hit is necessary but NOT sufficient: the pattern can match a
//   function that merely looks like the one we want. Confirmation needs a real
//   game, a debugger, and a human. This tool narrows the field to the
//   candidates worth checking; it does not close the question.
#include <windows.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

// The launcher's PE parser, used directly. A second hand-rolled copy was tried
// first and got TimeDateStamp wrong as uint16 instead of uint32, which shifted
// every field after it and produced a garbage section table while still looking
// like it worked. There is exactly one PE parser in this project and it has
// hostile-input tests behind it.
#include "BuildIdentity.hpp"

namespace {

struct SigCheck {
    const char* name;
    const char* pattern;
    int         functionOffset;
    const char* note;
};

// A copy of the table, NOT an include: this tool must be compilable without
// the vprobe headers, and more importantly the copy is what makes the check
// independent -- if the shared table is edited, this must not silently follow
// it. It is re-synced deliberately or not at all.
const SigCheck kSignatures[] = {
    {"PapyrusVM::PapyrusVM",             "48 8B ?? 48 89 5C 24 ?? 48 89 6C 24 ?? 48 8B DA 48 8B F9 E8 ?? ?? ?? ?? 48 8B 05 ?? ?? ?? ??", 0, "scheduler ctor"},
    {"PapyrusVM::GetRunningThreadCount", "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 ?? 48 8B 40 ?? 8B 90 ?? ?? ?? ?? 0F B6 C8 85 C9", 0, "thread-list walk"},
    {"PapyrusScript::Execute",           "48 89 5C 24 ?? 48 89 6C 24 ?? 48 89 74 24 ?? 57 48 83 EC ?? 49 8B F0 48 8B DA 48 8B F9", 0, "script interpreter"},
    {"PapyrusVM::DebugPrint",            "48 89 5C 24 ?? 48 89 6C 24 ?? 48 83 EC ?? 4C 8B C1 48 8B D9 ?? ?? 48 8B 01", 0, "script error print"},
    {"PapyrusThread::Execute",           "48 89 5C 24 ?? 48 89 6C 24 ?? 40 53 48 83 EC ?? 48 83 C4 ?? 49 8B F9", 0, "thread trampoline"},
    {"FormData::CellStream",             "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 ?? 48 8B 40 ?? 8B 88 ?? ?? ?? ?? 89 44 24 ?? C3", 0, "cell stream ptr"},
};

struct Pattern {
    std::vector<std::uint8_t> bytes;
    std::vector<bool>         wildcard;
    std::size_t               length = 0;
};

bool parsePattern(const char* text, Pattern& out) {
    const std::string s(text);
    std::size_t i = 0;
    auto hex = [](char c, int& v) {
        if (c >= '0' && c <= '9') { v = c - '0'; return true; }
        if (c >= 'a' && c <= 'f') { v = c - 'a' + 10; return true; }
        if (c >= 'A' && c <= 'F') { v = c - 'A' + 10; return true; }
        return false;
    };

    while (i < s.size()) {
        while (i < s.size() && s[i] == ' ') ++i;
        if (i >= s.size()) break;
        if (i + 1 >= s.size()) return false;

        if (s[i] == '?') {
            out.bytes.push_back(0);
            out.wildcard.push_back(true);
            i += (s[i + 1] == '?') ? 2 : 1;
        } else {
            int hi = 0, lo = 0;
            if (!hex(s[i], hi) || !hex(s[i + 1], lo)) return false;
            out.bytes.push_back(static_cast<std::uint8_t>((hi << 4) | lo));
            out.wildcard.push_back(false);
            i += 2;
        }
    }
    out.length = out.bytes.size();
    return out.length > 0;
}

// Count occurrences and collect the first few RVAs.
int scan(const std::uint8_t* data, std::size_t size, const Pattern& p,
         std::uint32_t sectionRva, std::vector<std::uint32_t>& hits, int collect) {
    if (p.length == 0 || size < p.length) return 0;
    int total = 0;
    const std::size_t last = size - p.length;
    for (std::size_t i = 0; i <= last; ++i) {
        std::size_t k = 0;
        for (; k < p.length; ++k) {
            if (!p.wildcard[k] && data[i + k] != p.bytes[k]) break;
        }
        if (k == p.length) {
            ++total;
            if (static_cast<int>(hits.size()) < collect) {
                hits.push_back(sectionRva + static_cast<std::uint32_t>(i));
            }
        }
    }
    return total;
}

struct Section {
    char     name[9] = {};
    std::uint32_t rva = 0, vsize = 0, raw = 0, rawSize = 0;
};

} // namespace

int wmain(int argc, wchar_t** argv) {
    if (argc < 2) {
        std::printf("usage: sigcheck <Fallout4.exe> [--dump N]\n");
        return 2;
    }

    HANDLE f = CreateFileW(argv[1], GENERIC_READ, FILE_SHARE_READ, nullptr,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) {
        std::printf("cannot open\n");
        return 1;
    }
    LARGE_INTEGER li{};
    GetFileSizeEx(f, &li);
    const auto size = static_cast<std::size_t>(li.QuadPart);

    HANDLE map = CreateFileMappingW(f, nullptr, PAGE_READONLY, 0, 0, nullptr);
    CloseHandle(f);
    const auto* base = static_cast<const std::uint8_t*>(
        MapViewOfFile(map, FILE_MAP_READ, 0, 0, 0));
    if (!base) { std::printf("cannot map\n"); return 1; }

    // --- header and sections, via the launcher's validated parser ----------
    f4mon::preflight::BuildIdentity id;
    std::wstring why;
    if (f4mon::preflight::identifyFile(argv[1], id, why) != f4mon::preflight::PeVerdict::Ok) {
        // why is wide; narrow it once here rather than at every call site.
        const int n = WideCharToMultiByte(CP_UTF8, 0, why.c_str(), -1, nullptr, 0,
                                          nullptr, nullptr);
        std::string reason(n > 1 ? static_cast<std::size_t>(n - 1) : 0, '\0');
        if (n > 1) {
            WideCharToMultiByte(CP_UTF8, 0, why.c_str(), -1, reason.data(), n,
                                nullptr, nullptr);
        }
        std::printf("rejected: %s\n",
                    reason.empty() ? "not a usable PE image" : reason.c_str());
        return 1;
    }

    const f4mon::preflight::PeView view{base, size};
    const auto sections = f4mon::preflight::parseSections(view);
    if (sections.empty()) {
        std::printf("no sections parsed -- refusing to report matches, because a\n"
                    "zero result caused by a parse failure is indistinguishable\n"
                    "from a zero result caused by genuinely absent signatures.\n");
        return 1;
    }

    std::printf("image   %ls\n", argv[1]);
    std::printf("size    %.1f MB\n", size / 1048576.0);
    std::printf("ts      0x%08x   linker %u.%u\n", id.timeDateStamp, id.majorLinker, id.minorLinker);
    std::printf("build   %s   (launcher build-key)\n", id.headerHashHex.c_str());
    std::printf("image   size 0x%x  subsystem %u\n", id.sizeOfImage, id.subsystem);
    std::printf("\nsections (%zu):\n", sections.size());
    for (const auto& s : sections) {
        std::printf("  %-8s rva 0x%08x  vsize 0x%08x  raw 0x%08x  rawsize 0x%08x%s\n",
                    s.name, s.virtualAddress, s.virtualSize, s.rawPointer, s.rawSize,
                    s.executable() ? "  [exec]" : "");
    }

    // --- scan executable sections only ------------------------------------
    // Data and reloc sections contain the bytes that make patterns ambiguous,
    // and hooking into them would be nonsense. The real .text is the target.
    std::printf("\nAOB scan (executable sections only):\n");
    std::printf("%-36s %8s  %s\n", "signature", "matches", "first RVAs");

    int zero = 0, one = 0, many = 0;
    for (const SigCheck& sc : kSignatures) {
        Pattern p;
        if (!parsePattern(sc.pattern, p)) {
            std::printf("%-36s %8s  [pattern parse failed]\n", sc.name, "-");
            ++zero;
            continue;
        }

        int total = 0;
        std::vector<std::uint32_t> hits;
        std::size_t sectionsScanned = 0;
        for (const auto& s : sections) {
            if (!s.executable() || !s.hasFileBytes()) continue;
            if (static_cast<std::size_t>(s.rawPointer) + s.rawSize > size) continue;
            ++sectionsScanned;

            // Bound the search to SIZE OF RAW DATA, not virtual size: reading
            // past raw size can read into an adjacent section, and a pattern
            // that "matches" across a section boundary is a false positive
            // that looks exactly like a hit.
            total += scan(base + s.rawPointer, s.rawSize, p, s.virtualAddress, hits, 8);
        }
        if (sectionsScanned == 0) {
            std::printf("%-36s %8s  [no executable section had file bytes]\n", sc.name, "-");
            ++zero;
            continue;
        }

        std::string rvas;
        for (std::size_t i = 0; i < hits.size() && i < 6; ++i) {
            if (i) rvas += " ";
            char buf[16];
            std::snprintf(buf, sizeof(buf), "0x%llx", (unsigned long long)hits[i]);
            rvas += buf;
        }
        if (total > 6) rvas += " ...";
        if (total == 0) rvas = "(none)";

        std::printf("%-36s %8d  %s\n", sc.name, total, rvas.c_str());
        if (total == 0) ++zero; else if (total == 1) ++one; else ++many;
    }

    std::printf("\nsummary: %d zero, %d unique, %d ambiguous (out of %d)\n",
                zero, one, many, static_cast<int>(sizeof(kSignatures) / sizeof(kSignatures[0])));
    std::printf("\nReminder: a unique hit is NECESSARY, not sufficient. A pattern can\n"
                "match a function that merely resembles the target. Confirmation\n"
                "needs a live process, and no amount of static analysis replaces it.\n");

    UnmapViewOfFile(base);
    CloseHandle(map);
    return 0;
}
