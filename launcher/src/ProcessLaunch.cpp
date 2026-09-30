// ProcessLaunch.cpp -- see ProcessLaunch.hpp for the reasoning behind each step.
#include "ProcessLaunch.hpp"

#include <windows.h>
// TlHelp32 supplies module enumeration, which is the only reliable way to
// find the image base of a process whose entry point has not run yet.
#include <TlHelp32.h>

#include <cstdio>
#include <string>
#include <vector>

namespace f4mon::preflight {
namespace {

std::wstring widen(const char* s) {
    if (s == nullptr || *s == '\0') return {};
    const int n = MultiByteToWideChar(CP_UTF8, 0, s, -1, nullptr, 0);
    if (n <= 1) return {};
    std::wstring w(static_cast<std::size_t>(n - 1), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s, -1, w.data(), n);
    return w;
}

std::wstring lastError(const char* what) {
    return widen(what) + L" (win32 " + std::to_wstring(GetLastError()) + L")";
}

std::wstring widen(const std::string& s) {
    return widen(s.c_str());
}

// Build a quoted command line. Quoting is not optional here: a game path
// containing a space is the normal case on Windows ("Program Files (x86)"),
// and CreateProcessW's parsing rules are unforgiving.
std::wstring buildCommandLine(const LaunchRequest& req) {
    std::wstring cmd = L"\"" + req.exePath + L"\"";
    for (const std::wstring& a : req.extraArgs) {
        cmd += L" ";
        cmd += (a.find(L' ') != std::wstring::npos) ? (L"\"" + a + L"\"") : a;
    }
    return cmd;
}

// Where did the target actually map itself?
//
// Three approaches were tried. Two failed, and the reason is worth recording
// because both failures look like "the process is dead" rather than "you
// picked the wrong API".
//
// (1) Assume the standard 0x140000000 preferred base. WRONG. A
//     CREATE_SUSPENDED process is already ASLR-relocated -- measured base on
//     this machine was 0x7ff6c38c0000 -- so a fixed-address read returns
//     nothing and every verification fails closed.
//
// (2) Toolhelp module enumeration. WRONG for this case, and surprisingly so.
//     CreateToolhelp32Snapshot(TH32CS_SNAPMODULE) fails with ERROR_PARTIAL_COPY
//     (299) against a suspended process. The module list is not yet walkable
//     before the entry point runs, despite this being the API every DLL
//     injector uses -- because those injectors call it on an already-running
//     process, which is the difference that matters.
//
// (3) PEB->ImageBaseAddress via NtQueryInformationProcess. CORRECT. The PEB
//     IS allocated and populated for a suspended process; the loader has
//     mapped and relocated the image, it simply has not run the entry stub.
//
// The subtlety that cost time: the PROCESS_BASIC_INFORMATION struct must be
// exactly 48 bytes on x64. Omitting the padding after UniqueProcessId yields
// a 40-byte struct, which returns STATUS_INFO_LENGTH_MISMATCH
// (0xC0000004) and looks exactly like "the PEB is not available yet".
[[nodiscard]] std::uintptr_t queryImageBase(HANDLE process) {
    typedef LONG(WINAPI* NtQueryFn)(HANDLE, int, void*, ULONG, ULONG*);

    HMODULE ntdll = GetModuleHandleW(L"ntdll.dll");
    if (ntdll == nullptr) return 0;
    auto ntQuery = reinterpret_cast<NtQueryFn>(GetProcAddress(ntdll, "NtQueryInformationProcess"));
    if (ntQuery == nullptr) return 0;

    // Must be 48 bytes. The explicit pad is load-bearing: without it MSVC
    // packs the struct to 40 and the call fails with STATUS_INFO_LENGTH_MISMATCH.
    struct BasicInfo {
        ULONG_PTR exitStatus;
        void*    peb;
        ULONG_PTR affinityMask;
        LONG     basePriority;
        ULONG    uniqueProcessId;
        ULONG    padding;          // aligns the ULONG_PTR below
        ULONG_PTR inheritedFrom;
    } info{};
    static_assert(sizeof(BasicInfo) == 48, "PROCESS_BASIC_INFORMATION layout");

    if (ntQuery(process, 0, &info, sizeof(info), nullptr) < 0) return 0;
    if (info.peb == nullptr) return 0;

    // PEB64->ImageBaseAddress sits at offset 0x10.
    std::uintptr_t base = 0;
    SIZE_T got = 0;
    if (!ReadProcessMemory(process,
                           static_cast<LPCVOID>(reinterpret_cast<std::uint8_t*>(info.peb) + 0x10),
                           &base, sizeof(base), &got) ||
        got != sizeof(base)) {
        return 0;
    }
    return base;
}

std::wstring directoryOf(const std::wstring& path) {
    const std::size_t slash = path.find_last_of(L"\\/");
    if (slash == std::wstring::npos) return L".";
    return path.substr(0, slash);
}

} // namespace

const char* toString(LaunchResult r) {
    switch (r) {
        case LaunchResult::Ok:               return "ok";
        case LaunchResult::CreateFailed:     return "the process would not start";
        case LaunchResult::ImageMismatch:    return "the executable changed between check and launch";
        case LaunchResult::InjectFailed:     return "could not inject the runtime";
        case LaunchResult::HandshakeTimeout: return "the runtime did not report that it loaded";
        case LaunchResult::Degraded:        return "the runtime loaded but is not ready";
        case LaunchResult::NotConfigured:    return "no runtime configured";
    }
    return "unknown";
}

LaunchedProcess::~LaunchedProcess() { killIfOwned(); }

LaunchedProcess::LaunchedProcess(LaunchedProcess&& o) noexcept
    : process_(o.process_), thread_(o.thread_), pid_(o.pid_), owned_(o.owned_),
      imageIdentity_(std::move(o.imageIdentity_)) {
    o.process_ = nullptr;
    o.thread_ = nullptr;
    o.pid_ = 0;
    o.owned_ = false;
}

LaunchedProcess& LaunchedProcess::operator=(LaunchedProcess&& o) noexcept {
    if (this != &o) {
        killIfOwned();
        process_ = o.process_;
        thread_ = o.thread_;
        pid_ = o.pid_;
        owned_ = o.owned_;
        imageIdentity_ = std::move(o.imageIdentity_);
        o.process_ = nullptr;
        o.thread_ = nullptr;
        o.pid_ = 0;
        o.owned_ = false;
    }
    return *this;
}

void LaunchedProcess::killIfOwned() {
    if (process_ == nullptr || !owned_) return;
    // A process that never resumed has no main thread to finish with, so
    // TerminateProcess is the only correct teardown. Leaving a suspended
    // process alive would leak it for the rest of the session with no
    // window and no CPU, which is exactly the kind of silent resource loss
    // G4 warns about.
    if (WaitForSingleObject(process_, 0) == WAIT_TIMEOUT) {
        TerminateProcess(process_, 0xDEAD);
        WaitForSingleObject(process_, 2000);
    }
    CloseHandle(process_);
    if (thread_ != nullptr) CloseHandle(thread_);
    process_ = nullptr;
    thread_ = nullptr;
    pid_ = 0;
}

void LaunchedProcess::release() {
    owned_ = false;
}

// Re-read the PE from the TARGET's address space and compare against the
// identity captured during pre-flight. This is the TOCTOU gate: a file
// swapped between validation and spawn lands here and is refused.
PeVerdict verifySpawnedImage(HANDLE process,
                             const BuildIdentity& expected,
                             BuildIdentity& actualOut) {
    actualOut = BuildIdentity{};

    const std::uintptr_t imageBase = queryImageBase(process);
    if (imageBase == 0) {
        // A verification routine that cannot read anything is not a passing
        // check, it is a skipped one. Report it as a failure so the launch
        // does not proceed on an unverified image.
        return PeVerdict::Truncated;
    }
    const auto baseAddr = reinterpret_cast<std::uint8_t*>(imageBase);

    IMAGE_DOS_HEADER dos{};
    SIZE_T got = 0;
    if (!ReadProcessMemory(process, baseAddr, &dos, sizeof(dos), &got) ||
        got != sizeof(dos)) {
        return PeVerdict::Truncated;
    }
    if (dos.e_magic != IMAGE_DOS_SIGNATURE) return PeVerdict::NotPe;
    if (dos.e_lfanew <= 0) return PeVerdict::NotPe;

    IMAGE_NT_HEADERS64 nt{};
    got = 0;
    if (!ReadProcessMemory(process, baseAddr + dos.e_lfanew, &nt, sizeof(nt), &got) ||
        got != sizeof(nt)) {
        return PeVerdict::Truncated;
    }
    if (nt.Signature != IMAGE_NT_SIGNATURE) return PeVerdict::NotPe;
    if (nt.FileHeader.Machine != IMAGE_FILE_MACHINE_AMD64) return PeVerdict::NotX64;

    // We cannot reuse parsePe here: it wants a contiguous local buffer and
    // the target's image is remote. Instead we hash the same header span,
    // read in pieces. The span is bounded by the optional header, which we
    // now know the size of, so this is a small fixed number of reads.
    const std::size_t optStart = static_cast<std::size_t>(dos.e_lfanew) + 4 +
                                 sizeof(IMAGE_FILE_HEADER);
    const std::size_t optLen = nt.FileHeader.SizeOfOptionalHeader;
    if (optLen < sizeof(IMAGE_OPTIONAL_HEADER64) || optLen > 0x1000) {
        return PeVerdict::Truncated;
    }

    std::vector<std::uint8_t> header(optStart + optLen);
    got = 0;
    if (!ReadProcessMemory(process, baseAddr, header.data(),
                           static_cast<DWORD>(header.size()), &got) ||
        got != header.size()) {
        return PeVerdict::Truncated;
    }

    actualOut.timeDateStamp = nt.FileHeader.TimeDateStamp;
    actualOut.sizeOfImage = nt.OptionalHeader.SizeOfImage;
    actualOut.sizeOfHeaders = nt.OptionalHeader.SizeOfHeaders;
    actualOut.subsystem = nt.OptionalHeader.Subsystem;
    actualOut.characteristics = nt.FileHeader.Characteristics;
    actualOut.majorLinker = nt.OptionalHeader.MajorLinkerVersion;
    actualOut.minorLinker = nt.OptionalHeader.MinorLinkerVersion;
    actualOut.headerHash = buildLookupKey(header.data(), header.size(), optStart);
    actualOut.headerHashHex = toHex16(actualOut.headerHash);

    // The comparison that gives the check its meaning. A mismatch is not an
    // error to be tolerated or a warning to be logged and resumed past; it
    // means the thing we validated is not the thing we are about to run.
    if (actualOut.headerHash != expected.headerHash) {
        return PeVerdict::ImplausibleImage;
    }
    return PeVerdict::Ok;
}

LaunchOutcome launch(const LaunchRequest& req, LaunchedProcess& out) {
    LaunchOutcome outcome;

    if (req.exePath.empty() || req.dllPath.empty()) {
        outcome.result = LaunchResult::NotConfigured;
        outcome.detail = widen("both an executable and a runtime path are required");
        return outcome;
    }

    // Establish the readiness event BEFORE anything can signal it.
    //
    // The runtime's DllMain runs at injection time, while the process is
    // still suspended -- which is before the resume step, and therefore long
    // before a handshake wait would begin. If we create the event at wait
    // time, the runtime has already tried to open it, failed silently, and
    // will never try again. The parent must create the sync object first.
    // BOTH events are created here, before the spawn. The "loaded" signal is
    // raised from the runtime's DllMain, which under CREATE_SUSPENDED runs
    // before the process has executed a single instruction -- so an event
    // created at wait time would already be too late for it.
    auto makeEvent = [](const std::wstring& name) -> HANDLE {
        return name.empty() ? nullptr : CreateEventW(nullptr, TRUE, FALSE, name.c_str());
    };

    HANDLE loadedEvent = makeEvent(req.loadedEvent);
    if (!req.loadedEvent.empty() && loadedEvent == nullptr) {
        outcome.result = LaunchResult::HandshakeTimeout;
        outcome.detail = lastError("could not create the loaded event");
        return outcome;
    }
    HANDLE readyEvent = makeEvent(req.readyEvent);
    if (!req.readyEvent.empty() && readyEvent == nullptr) {
        if (loadedEvent != nullptr) CloseHandle(loadedEvent);
        outcome.result = LaunchResult::HandshakeTimeout;
        outcome.detail = lastError("could not create the ready event");
        return outcome;
    }

    // Every failure from here on tears the process down before returning, so
    // a caller holding `out` never has a suspended process to reason about.
    auto fail = [&out, &readyEvent, &loadedEvent](LaunchResult r, std::wstring detail) {
        if (readyEvent != nullptr) CloseHandle(readyEvent);
        if (loadedEvent != nullptr) CloseHandle(loadedEvent);
        out.killIfOwned();
        LaunchOutcome o;
        o.result = r;
        o.detail = std::move(detail);
        return o;
    };

    // Wait for one event. Returns false for an event we never created, which
    // is the whole point: "we did not ask" must not read as "yes".
    //
    // An earlier version returned true for a null handle, on the reasoning
    // that there was nothing to wait for. That printed "loaded signal: yes"
    // during a --no-wait launch where NO SIGNAL WAS CHECKED AT ALL -- a
    // fabricated success in a tool whose entire purpose is not fabricating
    // successes (G4). A skipped check reports as skipped.
    auto waitSignal = [](HANDLE h, DWORD ms) {
        if (h == nullptr) return false;
        return WaitForSingleObject(h, ms) == WAIT_OBJECT_0;
    };

    // The expected identity comes from the caller's pre-flight pass. Refuse
    // to launch if it was never taken: launching unverified is exactly the
    // behaviour this component exists to prevent.
    BuildIdentity expected;
    std::wstring why;
    if (identifyFile(req.exePath, expected, why) != PeVerdict::Ok) {
        outcome.result = LaunchResult::ImageMismatch;
        outcome.detail = L"pre-flight rejected the executable: " +
                         (why.empty() ? widen(toString(PeVerdict::NotPe)) : why);
        return outcome;
    }

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};

    std::wstring cmd = buildCommandLine(req);
    const std::wstring cwd = req.workingDir.empty() ? directoryOf(req.exePath) : req.workingDir;

    // CREATE_SUSPENDED is the entire reason this component exists. The main
    // thread does not run a single instruction before we have verified the
    // image and queued the runtime.
    if (!CreateProcessW(req.exePath.c_str(), cmd.data(), nullptr, nullptr, FALSE,
                        CREATE_SUSPENDED, nullptr, cwd.c_str(), &si, &pi)) {
        return fail(LaunchResult::CreateFailed, lastError("CreateProcessW"));
    }

    // out.thread_ keeps the main-thread handle. We need it later for
    // ResumeThread, and the suspended main thread is what we are holding the
    // process hostage with, so closing it here would be a bug.
    out.adopt(pi.hProcess, pi.hThread, pi.dwProcessId);

    // Re-verify against the running (suspended) image. A failed launch tears
    // the process down via fail(), so `out` is left empty and the caller has
    // nothing to clean up.
    BuildIdentity actual;
    const PeVerdict verify = verifySpawnedImage(pi.hProcess, expected, actual);
    const std::wstring imageDetail = [&] {
        std::wstring w = widen(toString(verify));
        if (!actual.headerHashHex.empty()) {
            w += L" (expected " + widen(expected.headerHashHex) + L", got " +
                 widen(actual.headerHashHex) + L")";
        }
        return w;
    }();
    if (verify != PeVerdict::Ok) {
        LaunchOutcome o = fail(LaunchResult::ImageMismatch,
                               L"the spawned image did not match: " + imageDetail);
        o.imageIdentity = actual;
        return o;
    }
    out.setImageIdentity(actual);

    // --- Inject one known DLL, by path, through the ordinary loader. -------
    LPVOID remote = VirtualAllocEx(pi.hProcess, nullptr, req.dllPath.size() + 2,
                                   MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (remote == nullptr) {
        return fail(LaunchResult::InjectFailed, lastError("VirtualAllocEx"));
    }

    std::vector<wchar_t> remotePath(req.dllPath.begin(), req.dllPath.end());
    remotePath.push_back(L'\0');
    SIZE_T wrote = 0;
    if (!WriteProcessMemory(pi.hProcess, remote, remotePath.data(),
                            remotePath.size() * sizeof(wchar_t), &wrote)) {
        VirtualFreeEx(pi.hProcess, remote, 0, MEM_RELEASE);
        return fail(LaunchResult::InjectFailed, lastError("WriteProcessMemory"));
    }

    // kernel32 is mapped at the same address in every process of the same
    // bitness, so the local LoadLibraryW address is valid in the target. We
    // assert that rather than assume it: a hardcoded absolute address here
    // would be the kind of assumption that works until it does not.
    HMODULE k32 = GetModuleHandleW(L"kernel32.dll");
    FARPROC loadLibrary = (k32 != nullptr) ? GetProcAddress(k32, "LoadLibraryW") : nullptr;
    if (loadLibrary == nullptr) {
        VirtualFreeEx(pi.hProcess, remote, 0, MEM_RELEASE);
        return fail(LaunchResult::InjectFailed, widen("could not resolve LoadLibraryW locally"));
    }

    auto loaderThread = CreateRemoteThread(pi.hProcess, nullptr, 0,
                                           reinterpret_cast<LPTHREAD_START_ROUTINE>(loadLibrary),
                                           remote, 0, nullptr);
    if (loaderThread == nullptr) {
        VirtualFreeEx(pi.hProcess, remote, 0, MEM_RELEASE);
        return fail(LaunchResult::InjectFailed, lastError("CreateRemoteThread"));
    }

    // The remote thread must complete before we resume, or the game can
    // execute while the loader is still mid-flight and the DLL is mapped
    // underneath it.
    WaitForSingleObject(loaderThread, 30000);
    DWORD loadResult = 0;
    GetExitCodeThread(loaderThread, &loadResult);
    CloseHandle(loaderThread);
    VirtualFreeEx(pi.hProcess, remote, 0, MEM_RELEASE);

    if (loadResult == 0) {
        return fail(LaunchResult::InjectFailed, widen("the runtime DLL was not found or failed to load"));
    }

    // --- Resume. From here the game runs. --------------------------------
    // The loader thread must finish before the main thread runs, or the game
    // can execute while the DLL is still being mapped underneath it. We
    // waited above; this is the single thread that is still held at zero.
    if (ResumeThread(out.threadHandle()) == static_cast<DWORD>(-1)) {
        return fail(LaunchResult::InjectFailed, lastError("ResumeThread"));
    }

    // --- Handshake, or we do not call this a successful launch. ----------
    //
    // "loaded" is checked first and is the one that can time out fatally: if
    // the DLL never reported that it mapped, injection did not really happen
    // and there is nothing further worth waiting for.
    //
    // "ready" is treated differently. It legitimately will NOT arrive in a
    // pre-game context, because probes cannot resolve without a game module.
    // So its absence is reported as Degraded, not as failure -- and the
    // process is still handed back, because a user on an unsupported build
    // should be able to play their game and see our diagnostics explain why
    // the probes are off. Killing it would be worse than useless.
    outcome.loadedSignalled = waitSignal(loadedEvent, req.handshakeTimeoutMs);
    if (loadedEvent != nullptr) {
        CloseHandle(loadedEvent);
        loadedEvent = nullptr;
    }
    if (!req.loadedEvent.empty() && !outcome.loadedSignalled) {
        return fail(LaunchResult::HandshakeTimeout,
                    L"the runtime did not report that it loaded within " +
                        std::to_wstring(req.handshakeTimeoutMs) + L" ms");
    }

    outcome.readySignalled = waitSignal(readyEvent, req.handshakeTimeoutMs);
    if (readyEvent != nullptr) {
        CloseHandle(readyEvent);
        readyEvent = nullptr;
    }

    // The build identity is what makes a launch reportable: the caller needs
    // to know WHICH build started, not merely that one did.
    outcome.imageIdentity = out.imageIdentity();

    // A runtime that loaded but never became ready is a real, distinct state.
    // Reporting it as Ok is the exact error G4 exists to prevent -- "it works"
    // when it does not -- so it gets its own result and its own message.
    if (!req.readyEvent.empty() && !outcome.readySignalled) {
        outcome.result = LaunchResult::Degraded;
        outcome.detail =
            L"the runtime loaded but never reported ready. It is running, but "
            L"its probes are not live -- expected outside a real game, and a "
            L"defect on a supported build.";
        out.release();
        return outcome;
    }

    outcome.result = LaunchResult::Ok;
    out.release();
    return outcome;
}

} // namespace f4mon::preflight
