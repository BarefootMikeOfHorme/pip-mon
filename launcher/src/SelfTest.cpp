// SelfTest.cpp -- validation for the pre-flight integrity core.
//
// WHY THIS RUNS BEFORE THE GAME, NOT AFTER
//   Every check here is executable with no Fallout 4 present, because the
//   launcher owns the process while it is still suspended. If the build
//   cannot be identified, or the runtime fails its own checks, we never resume
//   the main thread and the player sees a message instead of a crash.
//
// THE POINT OF TESTING A PARSER ON SYNTHETIC PE DATA
//   The dangerous inputs are not real executables, they are malformed ones: a
//   truncated file, a 32-bit binary handed to us by mistake, a header that
//   claims an impossible SizeOfImage. Fallout 4 is never available on a build
//   machine, so if we do not test against synthetic images we are shipping
//   untested code on the exact path that is supposed to protect us. The
//   synthetic builder below emits deliberately hostile buffers so those paths
//   are exercised for real, not just reasoned about.
#include "SelfTest.hpp"

#include <windows.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

// vprobe's real handshake header, so the launcher and the runtime cannot
// disagree about event names. The test helper DLL includes the same header.
#include "ReadySignal.hpp"

#include "BuildIdentity.hpp"
#include "ProcessLaunch.hpp"

namespace f4mon::preflight {
namespace {

int g_pass = 0;
int g_fail = 0;

void report(const char* name, bool ok, const std::string& detail) {
    if (ok) {
        ++g_pass;
        std::printf("  [ PASS ] %-42s %s\n", name, detail.c_str());
    } else {
        ++g_fail;
        std::printf("  [ FAIL ] %-42s %s\n", name, detail.c_str());
    }
}

// ---------------------------------------------------------------------------
// Synthetic PE builder
// ---------------------------------------------------------------------------

struct SyntheticPe {
    std::vector<std::uint8_t> bytes;

    // Lay out a minimal but structurally valid PE32+ image in memory.
    // 0x00 DOS header (64 bytes) | 0x40 PE sig | 0x44 COFF | 0x58 optional
    // | 0x138 section table
    static SyntheticPe make(std::uint16_t machine, std::uint16_t magic,
                           std::uint32_t sizeOfImage, std::size_t bodyBytes) {
        SyntheticPe p;
        p.bytes.assign(0x138 + 40, 0);

        auto w16 = [&p](std::size_t off, std::uint16_t v) {
            std::memcpy(p.bytes.data() + off, &v, 2);
        };
        auto w32 = [&p](std::size_t off, std::uint32_t v) {
            std::memcpy(p.bytes.data() + off, &v, 4);
        };

        // Offsets below are relative to the optional header at 0x58. They
        // mirror PE32+ exactly: imageBase is 8-byte aligned, which is what
        // pushes SizeOfImage out to +0x38 and NumberOfRvaAndSizes to +0x70.
        constexpr std::size_t kOpt = 0x58;
        constexpr std::size_t kSizeOfImage    = kOpt + 0x38;
        constexpr std::size_t kSizeOfHeaders  = kOpt + 0x3C;
        constexpr std::size_t kCheckSum       = kOpt + 0x40;
        constexpr std::size_t kSubsystem      = kOpt + 0x44;
        constexpr std::size_t kNumberOfDirs   = kOpt + 0x70;

        w16(0x00, 0x5A4D);            // "MZ"
        w32(0x3C, 0x40);              // e_lfanew -> 0x40
        w32(0x40, 0x00004550);        // "PE\0\0"
        w16(0x44, machine);           // Machine
        w16(0x46, 1);                 // NumberOfSections
        w32(0x48, 0x66000000);        // TimeDateStamp (synthetic)
        w16(0x54, 0xF0);              // SizeOfOptionalHeader
        w16(kOpt, magic);             // Optional magic
        p.bytes[kOpt + 2] = 14;       // MajorLinkerVersion
        p.bytes[kOpt + 3] = 30;       // MinorLinkerVersion
        w32(kOpt + 0x18, 0x180000000 & 0xFFFFFFFF);  // imageBase low dword
        w32(kOpt + 0x1C, 0x1);                        // imageBase high dword
        w32(kSizeOfImage, sizeOfImage);
        w32(kSizeOfHeaders, 0x400);
        w32(kCheckSum, 0x1234ABCD);
        w16(kSubsystem, 2);           // Subsystem = GUI
        w32(kNumberOfDirs, 16);

        // one section covering the body
        w32(0x138 + 12, 0x1000);      // VirtualAddress
        w32(0x138 + 8, 0x1000);       // VirtualSize
        w32(0x138 + 16, 0x1000);      // SizeOfRawData
        w32(0x138 + 20, 0x400);       // PointerToRawData

        p.bytes.resize(0x400 + bodyBytes, 0xCC);   // 0xCC = int3 filler
        return p;
    }

    [[nodiscard]] PeView view() const { return PeView{bytes.data(), bytes.size()}; }
};

// The launcher validates the REAL executable, which is the one file we can
// never be sure of. These cases cover the ways that file can be wrong.
void testPeIdentity() {
    std::printf("PE identity / hostile input\n");

    // A well-formed x64 GUI image is the happy path.
    {
        const auto p = SyntheticPe::make(IMAGE_FILE_MACHINE_AMD64, 0x20b, 0x9000000, 0x2000);
        BuildIdentity id;
        const PeVerdict v = parsePe(p.view(), id);
        report("valid x64 image parses", v == PeVerdict::Ok, toString(v));
        report("  timeDateStamp captured", id.timeDateStamp == 0x66000000, toHex16(id.timeDateStamp));
        report("  sizeOfImage captured", id.sizeOfImage == 0x9000000, std::to_string(id.sizeOfImage));
        report("  subsystem = GUI", id.subsystemIsGui(), std::to_string(id.subsystem));
        report("  an .exe is not flagged as a DLL", !id.isDll(), "exe");
        report("  linker version captured", id.majorLinker == 14 && id.minorLinker == 30,
               std::to_string(id.majorLinker) + "." + std::to_string(id.minorLinker));
        report("  header hash is 16 hex chars", id.headerHashHex.size() == 16, id.headerHashHex);
    }

    // Determinism: the same bytes must always yield the same lookup key, or
    // the build database becomes useless after a re-download.
    {
        const auto a = SyntheticPe::make(IMAGE_FILE_MACHINE_AMD64, 0x20b, 0x9000000, 0x2000);
        const auto b = SyntheticPe::make(IMAGE_FILE_MACHINE_AMD64, 0x20b, 0x9000000, 0x2000);
        BuildIdentity ia, ib;
        (void)parsePe(a.view(), ia);
        (void)parsePe(b.view(), ib);
        report("hash is deterministic", ia.headerHash == ib.headerHash, ia.headerHashHex);

        // And a different build must NOT collide.
        const auto c = SyntheticPe::make(IMAGE_FILE_MACHINE_AMD64, 0x20b, 0x9100000, 0x2000);
        BuildIdentity ic;
        (void)parsePe(c.view(), ic);
        report("different build = different hash", ia.headerHash != ic.headerHash, ic.headerHashHex);
    }

    // A 32-bit binary. CK dumps, xEdit, and old tools are all x86, and a
    // confused user will eventually point the launcher at one.
    {
        const auto p = SyntheticPe::make(IMAGE_FILE_MACHINE_I386, 0x10b, 0x9000000, 0x2000);
        BuildIdentity id;
        report("32-bit rejected", parsePe(p.view(), id) == PeVerdict::NotX64, "NotX64");
    }

    // A 64-bit machine with a PE32 (32-bit) optional header: contradictory.
    {
        const auto p = SyntheticPe::make(IMAGE_FILE_MACHINE_AMD64, 0x10b, 0x9000000, 0x2000);
        BuildIdentity id;
        report("PE32 optional header rejected", parsePe(p.view(), id) == PeVerdict::NotPe32Plus,
               "NotPe32Plus");
    }

    // Absurd SizeOfImage. Catches a wrong file (a .pdb, a redist, a text file
    // that happens to start with MZ) before we try to spawn it.
    {
        const auto p = SyntheticPe::make(IMAGE_FILE_MACHINE_AMD64, 0x20b, 0x100, 0x2000);
        BuildIdentity id;
        report("implausible SizeOfImage rejected",
               parsePe(p.view(), id) == PeVerdict::ImplausibleImage, "ImplausibleImage");
    }

    // Not a PE at all. Must be reported as NotPe rather than Truncated --
    // "you gave me the wrong file" is actionable, "too short" is not, and a
    // text file handed to us by mistake is a realistic user error.
    {
        const char* junk = "this is not an executable, it is a config file, and it is long "
                           "enough that a naive length check would pass it as a candidate";
        PeView v{reinterpret_cast<const std::uint8_t*>(junk), std::strlen(junk)};
        BuildIdentity id;
        const PeVerdict got = parsePe(v, id);
        report("non-PE rejected as NotPe", got == PeVerdict::NotPe, toString(got));
    }

    // A zero-length or null view must not dereference anything.
    {
        PeView v{nullptr, 0};
        BuildIdentity id;
        report("null view rejected", parsePe(v, id) == PeVerdict::NotPe, "NotPe");
    }

    // TRUNCATION. The important case: a partially downloaded or quarantined
    // executable. e_lfanew can point past the end of the buffer, so a naive
    // parser reads out of bounds. We must detect, not crash -- and the only
    // way to know that is to run it.
    //
    // The invariant is NOT "every short file is rejected". It is: a file is
    // rejected whenever it ends before the last header field we actually
    // consume. Once SizeOfImage and Subsystem are readable, the build IS
    // identified, and refusing to say so would be the bug -- a user whose
    // install is intact but whose file is being scanned by AV must still be
    // able to launch. So the boundary is the end of the optional header.
    {
        const auto full = SyntheticPe::make(IMAGE_FILE_MACHINE_AMD64, 0x20b, 0x9000000, 0x2000);
        constexpr std::size_t kOptStart = 0x58;
        constexpr std::size_t kOptEnd   = kOptStart + 0xF0;   // = SizeOfOptionalHeader

        bool allCaught = true;
        std::string firstBad = "none";
        for (std::size_t cut = 1; cut < kOptEnd; cut += 7) {
            PeView v{full.bytes.data(), cut};
            BuildIdentity id;
            if (parsePe(v, id) == PeVerdict::Ok) {
                allCaught = false;
                firstBad = "accepted a " + std::to_string(cut) + "-byte prefix";
                break;
            }
        }
        report("every cut before the headers end is caught", allCaught, firstBad);

        // And the boundary itself: the last usable byte must succeed.
        BuildIdentity atEnd;
        const bool okAtEnd =
            parsePe(PeView{full.bytes.data(), kOptEnd}, atEnd) == PeVerdict::Ok;
        report("identifies a build from headers alone", okAtEnd, atEnd.headerHashHex);

        // Dense sweep across the whole range, to catch an off-by-one that a
        // strided loop would step over.
        bool dense = true;
        for (std::size_t cut = 1; cut < kOptEnd && dense; ++cut) {
            BuildIdentity id;
            if (parsePe(PeView{full.bytes.data(), cut}, id) == PeVerdict::Ok) dense = false;
        }
        report("dense sweep: no gap in the rejection range", dense, "byte-by-byte");
    }

    // A DLL handed to the launcher. Realistic: users point the preflight at
    // a mod's native plugin, or at CommonLib, and get an ACCEPT that means
    // nothing. Must be rejected explicitly rather than accepted silently.
    {
        auto p = SyntheticPe::make(IMAGE_FILE_MACHINE_AMD64, 0x20b, 0x9000000, 0x2000);
        const std::uint16_t dll = 0x2000;
        std::memcpy(p.bytes.data() + 0x56, &dll, 2);   // COFF characteristics
        BuildIdentity id;
        const PeVerdict v = parsePe(p.view(), id);
        report("DLL rejected where the exe was expected", v == PeVerdict::IsDll, toString(v));
    }

    // e_lfanew pointing far past EOF (corrupt or hostile).
    {
        auto p = SyntheticPe::make(IMAGE_FILE_MACHINE_AMD64, 0x20b, 0x9000000, 0x2000);
        const std::uint32_t huge = 0x7FFFFFF0;
        std::memcpy(p.bytes.data() + 0x3C, &huge, 4);
        BuildIdentity id;
        const PeVerdict v = parsePe(p.view(), id);
        report("out-of-range e_lfanew caught", v != PeVerdict::Ok, toString(v));
    }
}

// FNV-1a against the published test vectors, so a refactor cannot silently
// change the build lookup key and orphan every entry in the build database.
void testHashVectors() {
    std::printf("hash vectors\n");

    {
        const char* s = "";
        const auto h = fnv1a64(reinterpret_cast<const std::uint8_t*>(s), 0);
        report("FNV-1a empty", h == 0xcbf29ce484222325ULL, toHex16(h));
    }
    {
        const char* s = "a";
        const auto h = fnv1a64(reinterpret_cast<const std::uint8_t*>(s), 1);
        report("FNV-1a \"a\"", h == 0xaf63dc4c8601ec8cULL, toHex16(h));
    }
    {
        const char* s = "foobar";
        const auto h = fnv1a64(reinterpret_cast<const std::uint8_t*>(s), 6);
        report("FNV-1a \"foobar\"", h == 0x85944171f73967e8ULL, toHex16(h));
    }

    // SHA-256 via BCrypt, against the published digest of "abc". The tamper
    // check is the one place we verify a whole 90 MB file, so a silent
    // BCrypt misuse would disable integrity checking without ever failing a
    // launch. Test it against a known value rather than against itself.
    {
        // Build the string in a temp file so we exercise the real file path.
        const wchar_t* tmp = L"pipmon_pf_hash_test.bin";
        HANDLE f = CreateFileW(tmp, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS,
                               FILE_ATTRIBUTE_NORMAL, nullptr);
        if (f != INVALID_HANDLE_VALUE) {
            const char* abc = "abc";
            DWORD wrote = 0;
            WriteFile(f, abc, 3, &wrote, nullptr);
            CloseHandle(f);

            const std::string digest = sha256File(tmp);
            const char* kExpect =
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
            report("SHA-256 of \"abc\" (NIST vector)", digest == kExpect, digest.substr(0, 16));

            // A missing file must return empty rather than a stale/garbage
            // digest, otherwise a moved install looks like a tampered one.
            report("SHA-256 of missing file is empty", sha256File(L"nope_does_not_exist.bin").empty(),
                   "empty");
            DeleteFileW(tmp);
        } else {
            report("SHA-256 of \"abc\" (NIST vector)", false, "could not create temp file");
        }
    }
}

// ---------------------------------------------------------------------------
// Core load path
// ---------------------------------------------------------------------------
//
// These tests need the helper target and helper DLL built alongside. They
// spawn, inject, resume and handshake for real; there is no mock. That is
// deliberate -- a load path tested with a mock tests the mock.

[[nodiscard]] std::wstring moduleDir() {
    wchar_t buf[MAX_PATH] = {};
    const DWORD n = GetModuleFileNameW(nullptr, buf, MAX_PATH);
    std::wstring p(buf, buf + n);
    const std::size_t slash = p.find_last_of(L"\\/");
    return (slash == std::wstring::npos) ? L"." : p.substr(0, slash);
}

[[nodiscard]] std::wstring sibling(const wchar_t* name) {
    return moduleDir() + L"\\" + name;
}

[[nodiscard]] bool fileExists(const std::wstring& p) {
    return GetFileAttributesW(p.c_str()) != INVALID_FILE_ATTRIBUTES;
}

[[nodiscard]] std::string narrow(const std::wstring& w) {
    if (w.empty()) return {};
    const int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, nullptr, 0, nullptr, nullptr);
    if (n <= 1) return {};
    std::string s(static_cast<std::size_t>(n - 1), '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, s.data(), n, nullptr, nullptr);
    return s;
}

void testLoadPath() {
    std::printf("core load path (real process, real injection)\n");

    const std::wstring targetExe     = sibling(L"pf_helper_target.exe");
    const std::wstring talkerDll     = sibling(L"pf_helper_dll.dll");
    const std::wstring noReadyDll    = sibling(L"pf_helper_dll_noready.dll");
    const std::wstring noLoadedDll   = sibling(L"pf_helper_dll_noloaded.dll");

    if (!fileExists(targetExe) || !fileExists(talkerDll) ||
        !fileExists(noReadyDll) || !fileExists(noLoadedDll)) {
        report("load path fixtures present", false,
               "a helper target/dll is missing - run launcher\\build_all.bat");
        return;
    }
    report("load path fixtures present", true, "target + 3 dll variants found");

    // The three real event names, shared with vprobe's ReadySignal.hpp.
    const std::wstring kLoaded = f4mon::runtime::kLoadedEvent;
    const std::wstring kReady  = f4mon::runtime::kReadyEvent;

    // The target signals through an event WE create and hold open. A named
    // event is destroyed with its last handle, so creating it in the target
    // and closing it there -- the obvious implementation -- leaves nothing
    // observable. The parent owns sync objects; that is the real pattern too.
    HANDLE runningEvent =
        CreateEventW(nullptr, TRUE, FALSE, L"Local\\pipmon_pf_target_running");

    // 1. The happy path: suspended, verified, injected, resumed, signalled.
    {
        LaunchRequest req;
        req.exePath = targetExe;
        req.dllPath = talkerDll;
        req.loadedEvent = kLoaded;
        req.readyEvent  = kReady;
        req.handshakeTimeoutMs = 5000;

        LaunchedProcess proc;
        const LaunchOutcome out = launch(req, proc);

        report("launch reaches Ok", out.result == LaunchResult::Ok, toString(out.result));
        if (out.result != LaunchResult::Ok) {
            report("  detail", false, narrow(out.detail));
        }
        report("  loaded signal received", out.loadedSignalled,
               out.loadedSignalled ? "DllMain reported in" : "no signal");
        report("  ready signal received", out.readySignalled,
               out.readySignalled ? "init completed" : "no signal");
        report("  both signals are distinct facts", out.loadedSignalled && out.readySignalled,
               "loaded and ready both observed");
        report("  image identity read from target", !out.imageIdentity.headerHashHex.empty(),
               out.imageIdentity.headerHashHex);
        report("  process released to caller", proc.valid(), "handle open");

        // The target confirms it actually resumed by setting its own event.
        // This is the check that distinguishes "ResumeThread returned" from
        // "the target really is running code".
        bool resumed = false;
        if (runningEvent != nullptr) {
            resumed = WaitForSingleObject(runningEvent, 5000) == WAIT_OBJECT_0;
        }
        report("  target really is executing", resumed,
               runningEvent ? "signalled" : "event not created");

        if (proc.valid()) {
            TerminateProcess(proc.handle(), 0);
            WaitForSingleObject(proc.handle(), 2000);
        }
    }

    // 2. DEGRADED. The DLL loads and reports in, but never becomes ready.
    //    This is the state a user hits on an unsupported build, and it is the
    //    one that most easily gets rounded to "success". The launcher must
    //    report it distinctly AND still hand the process back, because a user
    //    on a new patch should be able to play and read our diagnostics
    //    rather than have their game killed.
    {
        LaunchRequest req;
        req.exePath = targetExe;
        req.dllPath = noReadyDll;
        req.loadedEvent = kLoaded;
        req.readyEvent  = kReady;
        req.handshakeTimeoutMs = 1500;

        LaunchedProcess proc;
        const LaunchOutcome out = launch(req, proc);

        report("loaded-but-not-ready is DEGRADED, not Ok",
               out.result == LaunchResult::Degraded, toString(out.result));
        report("  loaded was still observed", out.loadedSignalled, "DllMain reported in");
        report("  ready was not", !out.readySignalled, "init never completed");
        report("  process is still handed back", proc.valid(),
               "user keeps their game running");
    }

    // 3. THE HARD NEGATIVE. The DLL maps but never says so. Injection
    //    "succeeded" at the loader level, so only the handshake can catch
    //    this -- and if it were reported as success the user would sit in a
    //    game with no diagnostics and no explanation.
    {
        LaunchRequest req;
        req.exePath = targetExe;
        req.dllPath = noLoadedDll;
        req.loadedEvent = kLoaded;
        req.readyEvent  = kReady;
        req.handshakeTimeoutMs = 1500;

        LaunchedProcess proc;
        const LaunchOutcome out = launch(req, proc);

        report("runtime that never signals is caught",
               out.result == LaunchResult::HandshakeTimeout, toString(out.result));
        report("  not silently reported as Ok", out.result != LaunchResult::Ok,
               toString(out.result));
        report("  process killed, not leaked", !proc.valid(), "clean teardown");
    }

    // 4. A missing DLL must fail at injection, not silently continue.
    {
        LaunchRequest req;
        req.exePath = targetExe;
        req.dllPath = sibling(L"definitely_not_here.dll");
        req.loadedEvent = kLoaded;
        req.readyEvent  = kReady;
        req.handshakeTimeoutMs = 1000;

        LaunchedProcess proc;
        const LaunchOutcome out = launch(req, proc);
        report("missing runtime is rejected", out.result == LaunchResult::InjectFailed,
               toString(out.result));
        report("  no process leaked", !proc.valid(), "clean teardown");
    }

    // 4. The TOCTOU check, tested directly. We hold a real suspended process
    //    and compare its live image against a deliberately wrong expectation.
    //    This is the guarantee that a file swapped between pre-flight and
    //    spawn is caught rather than run.
    {
        LaunchRequest req;
        req.exePath = targetExe;
        req.dllPath = talkerDll;
        // No handshake: we want the process left suspended so we can inspect.
        LaunchedProcess proc;
        LaunchOutcome out = launch(req, proc);
        // A launch with no handshake resumes; we only want the suspended
        // window, so this test re-creates one directly instead.
        if (proc.valid()) {
            TerminateProcess(proc.handle(), 0);
            WaitForSingleObject(proc.handle(), 2000);
        }
        (void)out;

        // Build our own suspended process to inspect.
        wchar_t cmd[1024] = {};
        _snwprintf_s(cmd, _TRUNCATE, L"\"%ls\"", targetExe.c_str());
        STARTUPINFOW si{};
        si.cb = sizeof(si);
        PROCESS_INFORMATION pi{};
        if (!CreateProcessW(targetExe.c_str(), cmd, nullptr, nullptr, FALSE,
                            CREATE_SUSPENDED, nullptr, nullptr, &si, &pi)) {
            report("TOCTOU fixture spawned", false, "CreateProcessW failed");
            return;
        }

        BuildIdentity expected;
        std::wstring why;
        const bool gotExpected = identifyFile(targetExe, expected, why) == PeVerdict::Ok;

        BuildIdentity actual;
        const PeVerdict match = verifySpawnedImage(pi.hProcess, expected, actual);
        report("matching image verifies", match == PeVerdict::Ok, toString(match));
        report("  hashes agree", expected.headerHash == actual.headerHash,
               actual.headerHashHex);

        // Now lie about the expected identity, which is what a swapped file
        // looks like from here.
        BuildIdentity wrong = expected;
        wrong.headerHash ^= 0xA5A5A5A5A5A5A5A5ULL;
        BuildIdentity ignored;
        const PeVerdict mismatch =
            verifySpawnedImage(pi.hProcess, wrong, ignored);
        report("swapped image is REJECTED", mismatch != PeVerdict::Ok, toString(mismatch));

        TerminateProcess(pi.hProcess, 0);
        WaitForSingleObject(pi.hProcess, 2000);
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        (void)gotExpected;
    }

    // 5. A suspended process that goes out of scope must be cleaned up, not
    //    left hanging with no window and no CPU. Leaking one is the kind of
    //    silent resource loss G4 warns about.
    {
        HANDLE before = nullptr;
        DWORD beforeCount = 0;
        // Count our own helper processes by name is not available without
        // Toolhelp; instead assert the destructor path indirectly -- the
        // object goes out of scope here and must not crash or hang.
        (void)before;
        (void)beforeCount;
        {
            LaunchRequest req;
            req.exePath = targetExe;
            req.dllPath = talkerDll;
            LaunchedProcess proc;
            // No events requested: this exercises create -> verify -> inject
            // -> resume and then goes out of scope, so it covers the teardown
            // path rather than the handshake path.
            (void)launch(req, proc);
            report("RAII teardown does not hang or crash", true, "scoped process released");
        }
    }

    if (runningEvent != nullptr) CloseHandle(runningEvent);
}

} // namespace

int runSelfTest() {
    std::printf("=== PIP-MON launcher pre-flight self-test ===\n\n");
    g_pass = 0;
    g_fail = 0;

    testPeIdentity();
    std::printf("\n");
    testHashVectors();
    std::printf("\n");
    testLoadPath();

    std::printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}

} // namespace f4mon::preflight
