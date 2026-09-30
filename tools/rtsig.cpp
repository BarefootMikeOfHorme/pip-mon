// rtsig.cpp -- READ-ONLY live-process signature check.
//
// WHAT THIS DOES NOT DO, stated first because it is the whole point:
//   It opens the target with PROCESS_VM_READ and PROCESS_QUERY_INFORMATION.
//   It never requests VM_WRITE, VM_OPERATION, CREATE_THREAD, or SUSPEND_RESUME.
//   It writes nothing into the target. It calls no function in the target. It
//   cannot crash the target, and it cannot affect the save.
//
// WHY IT IS SAFE AND STILL USEFUL
//   The static scan found one candidate: PapyrusScript::Execute at RVA
//   0x1b887c0, the only one of six signatures that matched at all. Static
//   analysis answers "does this byte pattern exist in the file". It cannot
//   answer the two questions that actually matter:
//
//     1. Does the same pattern exist in the LIVE image, after ASLR and after
//        the loader has patched relocations? (The answer can differ. A pattern
//        spanning a relocated address, or one the loader rewrites, exists on
//        disk and not in memory -- or worse, the reverse.)
//     2. Is the match at something that PLAUSIBLY LOOKS LIKE A FUNCTION?
//        A unique byte match can still sit in the middle of an unrelated
//        routine. Dumping the surrounding bytes lets a human judge.
//
//   Answering both in a live process, without touching it, is most of the
//   remaining distance between "a pattern that matches" and "a hook we could
//   trust".
//
// WHY NOT INJECT INSTEAD
//   Because it would be reckless. Injection writes memory, creates a thread,
//   and runs code in a live game with a save open. That is the test we do
//   later, deliberately, on a disposable profile -- not as a side effect of
//   wanting an answer sooner.
#include <windows.h>
// Module enumeration lives in TlHelp32.h, which windows.h does not pull in
// under WIN32_LEAN_AND_MEAN.
#include <TlHelp32.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace {

constexpr DWORD kReadOnlyAccess =
    PROCESS_QUERY_INFORMATION |   // locate modules
    PROCESS_VM_READ;               // read bytes, and nothing else

// The one candidate from the static scan, plus the section it lives in.
constexpr std::uint32_t kCandidateRva  = 0x01b887c0;
constexpr const char*   kCandidateName = "PapyrusScript::Execute";

// Pattern, kept byte-identical to Signatures.hpp for the one that matched.
const char* kPattern =
    "48 89 5C 24 ?? 48 89 6C 24 ?? 48 89 74 24 ?? 57 48 83 EC ?? 49 8B F0 48 8B DA 48 8B F9";

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

std::string hexDump(const std::uint8_t* p, std::size_t n) {
    std::string s;
    char buf[8];
    for (std::size_t i = 0; i < n; ++i) {
        if (i % 16 == 0) {
            if (i) s += "\n      ";
            std::snprintf(buf, sizeof(buf), "%04zx  ", i);
            s += buf;
        }
        std::snprintf(buf, sizeof(buf), "%02X ", p[i]);
        s += buf;
    }
    return s;
}

// Disassembly is deliberately NOT attempted here. Zydis is available, but
// dumping bytes and letting a human read the prologue is more honest than a
// machine that would happily label the wrong address as a function entry.
void showContext(HANDLE h, std::uintptr_t addr, const char* label) {
    std::uint8_t buf[96] = {};
    SIZE_T got = 0;
    if (!ReadProcessMemory(h, reinterpret_cast<LPCVOID>(addr), buf, sizeof(buf), &got)) {
        std::printf("  %s: could not read (error %lu)\n", label, GetLastError());
        return;
    }
    std::printf("  %s @ 0x%llx:\n      %s\n", label,
                (unsigned long long)addr, hexDump(buf, got).c_str());
}

} // namespace

int wmain(int argc, wchar_t** argv) {
    if (argc < 3) {
        std::printf("usage: rtsig <pid> <module>\n");
        std::printf("  read-only. opens the target with VM_READ only.\n");
        return 2;
    }
    const DWORD pid = static_cast<DWORD>(_wtoi64(argv[1]));
    const std::wstring moduleName = argv[2];

    // The access mask is the safety property. If this line ever gains
    // VM_WRITE, this tool becomes a different and much more dangerous thing.
    HANDLE h = OpenProcess(kReadOnlyAccess, FALSE, pid);
    if (h == nullptr) {
        std::printf("OpenProcess(VmRead only) failed: %lu\n", GetLastError());
        std::printf("(a game running elevated would deny this, which is correct)\n");
        return 1;
    }
    std::printf("attached to pid %lu -- READ ONLY, no writes performed\n\n", pid);

    // --- locate the module base -------------------------------------------
    std::uintptr_t base = 0;
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    if (snap == INVALID_HANDLE_VALUE) {
        std::printf("module snapshot failed: %lu\n", GetLastError());
        CloseHandle(h);
        return 1;
    }
    MODULEENTRY32W me{};
    me.dwSize = sizeof(me);
    if (!Module32FirstW(snap, &me)) {
        std::printf("Module32First failed: %lu\n", GetLastError());
        CloseHandle(snap);
        CloseHandle(h);
        return 1;
    }
    do {
        if (_wcsicmp(me.szModule, moduleName.c_str()) == 0) {
            base = reinterpret_cast<std::uintptr_t>(me.modBaseAddr);
            break;
        }
    } while (Module32NextW(snap, &me));
    CloseHandle(snap);

    if (base == 0) {
        std::printf("module '%ls' not found in pid %lu\n", moduleName.c_str(), pid);
        CloseHandle(h);
        return 1;
    }
    std::printf("module %ls\n", moduleName.c_str());
    std::printf("  base   0x%llx\n", (unsigned long long)base);
    std::printf("  size   0x%lu\n", me.modBaseSize);
    // modBaseAddr is already an ABSOLUTE address as the OS reports it, so it
    // must not be added to base again. Printing base+base would look
    // plausible and be nonsense, which is the failure mode G4 warns about.
    std::printf("  entry  0x%llx\n", (unsigned long long)me.modBaseAddr);

    // --- 1. does the candidate still hold in live memory? -----------------
    const std::uintptr_t candidate = base + kCandidateRva;
    std::printf("\n1. candidate from the static scan\n");
    std::printf("   %s at RVA 0x%X -> absolute 0x%llx\n",
                kCandidateName, kCandidateRva, (unsigned long long)candidate);

    Pattern p;
    if (!parsePattern(kPattern, p)) {
        std::printf("   pattern failed to parse\n");
        CloseHandle(h);
        return 1;
    }

    std::uint8_t live[256] = {};
    SIZE_T got = 0;
    if (ReadProcessMemory(h, reinterpret_cast<LPCVOID>(candidate - 64), live,
                          sizeof(live), &got)) {
        bool matchAt = (got >= 64 + p.length);
        if (matchAt) {
            for (std::size_t k = 0; k < p.length; ++k) {
                if (!p.wildcard[k] && live[64 + k] != p.bytes[k]) { matchAt = false; break; }
            }
        }
        std::printf("   pattern present at that address: %s\n", matchAt ? "YES" : "NO");

        // Context before the match: if this lands mid-instruction or inside an
        // unrelated routine, the prologue bytes will not look like a function
        // entry. Cheap heuristic, and it is only a heuristic.
        std::printf("\n   64 bytes BEFORE the match (looking for a prologue):\n");
        std::printf("      %s\n", hexDump(live, 64).c_str());
        std::printf("   the 4 bytes straddling the boundary:\n");
        std::printf("      %02X %02X %02X %02X | %02X %02X %02X %02X\n",
                    live[60], live[61], live[62], live[63],
                    live[64], live[65], live[66], live[67]);
        std::printf("   a C3 (ret), CC (int3) or 90 (nop) just before the match\n"
                    "   suggests a real function entry; arbitrary bytes suggest\n"
                    "   we are in the middle of something else.\n");
    } else {
        std::printf("   could not read candidate: error %lu\n", GetLastError());
    }

    // --- 2. rescan the whole live .text for the pattern -------------------
    // The single most useful number in this tool: how many times the pattern
    // occurs in the LIVE image. A count of 1 in the file but 6 in memory would
    // mean something is generating code or patching it at runtime, and every
    // assumption downstream would be wrong.
    std::printf("\n2. rescanning the live image for the same pattern\n");
    // .text is the first executable section; approximate with the first
    // 40 MB, which comfortably covers it and costs one read.
    const std::size_t kScan = 40u * 1024u * 1024u;
    std::vector<std::uint8_t> big(kScan);
    SIZE_T bigGot = 0;
    if (!ReadProcessMemory(h, reinterpret_cast<LPCVOID>(base), big.data(),
                           static_cast<DWORD>(big.size()), &bigGot)) {
        std::printf("   could not read the image body: error %lu\n", GetLastError());
        CloseHandle(h);
        return 1;
    }
    std::printf("   read %llu bytes of the live image\n", (unsigned long long)bigGot);

    // A naive O(n*m) scan over 40 MB is roughly a second and a half, which is
    // fine here. It is worth noting the cost only because the same loop runs
    // against a live game on every invocation; if this ever moves into a
    // polling loop, it needs a Boyer-Moore-Horspool first-byte skip.
    int hits = 0;
    // Absolute addresses, 64-bit. Storing these in a 32-bit vector truncated
    // every real hit to garbage, and the RVA printed from it was meaningless.
    std::vector<std::uintptr_t> hitAddrs;
    for (std::size_t i = 0; i + p.length <= bigGot; ++i) {
        std::size_t k = 0;
        for (; k < p.length; ++k) {
            if (!p.wildcard[k] && big[i + k] != p.bytes[k]) break;
        }
        if (k == p.length) {
            ++hits;
            if (hitAddrs.size() < 12) hitAddrs.push_back(base + i);
        }
    }
    std::printf("   LIVE matches: %d\n", hits);
    for (std::uintptr_t a : hitAddrs) {
        std::printf("     0x%llx (RVA 0x%llX)\n", (unsigned long long)a,
                    (unsigned long long)(a - base));
    }
    if (hits == 1) {
        std::printf("   -> unique in the live image. Consistent with the static\n"
                    "      scan, and worth a human confirming the prologue.\n");
    } else if (hits == 0) {
        std::printf("   -> NOT FOUND LIVE, though it was found on disk. Something\n"
                    "      patches the image at runtime, or the static hit was a\n"
                    "      false positive. Either way, do not trust the signature.\n");
    } else {
        std::printf("   -> %d matches LIVE. This signature is ambiguous and must not\n"
                    "      be used to locate a function.\n", hits);
    }

    showContext(h, candidate, "bytes at the candidate");

    std::printf("\nno writes were made to pid %lu. closing.\n", pid);
    CloseHandle(h);
    return 0;
}
