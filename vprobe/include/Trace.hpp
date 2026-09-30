// Trace.hpp -- opt-in file tracing, shared across translation units.
//
// WHY THIS EXISTS
//   The first live injection produced no evidence at all. vprobe.dll mapped,
//   the handshake reported LOADED, the game died three seconds later, and
//   there was no Application Error event, no dump, no Papyrus log -- because
//   every diagnostic went to the V-Link named pipe, and a pipe nobody has
//   connected to yet carries nothing. The one run that mattered taught us
//   nothing.
//
//   So: when a marker file named `vprobe.trace` sits beside the DLL, every
//   traceLine() is appended to `vprobe.trace.log` next to it, timestamped with
//   the thread id and flushed per line.
//
//   It is a header rather than a function in one .cpp because the interesting
//   failures are NOT all in the startup path. The second live run crashed
//   *after* `onLoad: bootstrap returned`, which put the fault in the IPC
//   worker's steady-state loop -- a different translation unit entirely.
//   Tracing that from main.cpp alone was not possible.
//
// DESIGN CONSTRAINTS, each of which is the point
//
//   - OFF unless the marker file exists. The default path is unchanged and a
//     shipped runtime does no file IO it was not asked to do.
//   - A marker FILE, not an environment variable. The game is launched by
//     whoever launched it, so an env var set in our shell would not reach it.
//     A file beside the DLL is found the same way every time.
//   - Opened, written and closed PER LINE. A buffered writer would lose
//     exactly the last few lines before a crash, which are the ones that
//     identify the fault.
//   - It must never be the cause of the failure it is diagnosing. Every call
//     is best-effort, no error path throws, and nothing here allocates
//     unboundedly. A trace that can crash the process is worse than no trace.
#pragma once

#include <Windows.h>
#include <cstdarg>
#include <cstdio>
#include <string>

namespace f4mon::trace {

inline std::wstring& path() {
    static std::wstring p;
    return p;
}

inline bool& checked() {
    static bool c = false;
    return c;
}

inline void init() {
    if (checked()) {
        return;
    }
    checked() = true;

    HMODULE self = nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                           GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       reinterpret_cast<LPCWSTR>(&init), &self);
    if (!self) {
        return;
    }
    wchar_t buf[MAX_PATH]{};
    const DWORD n = GetModuleFileNameW(self, buf, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) {
        return;
    }
    std::wstring selfPath(buf);
    const auto slash = selfPath.find_last_of(L"\\/");
    if (slash == std::wstring::npos) {
        return;
    }
    const std::wstring dir = selfPath.substr(0, slash + 1);
    if (GetFileAttributesW((dir + L"vprobe.trace").c_str())
        != INVALID_FILE_ATTRIBUTES) {
        path() = dir + L"vprobe.trace.log";
    }
}

// ---------------------------------------------------------------------------
//  SESSION STREAM -- the observation channel that does not kill the game
// ---------------------------------------------------------------------------
//  The V-Link named pipe is unusable for live observation on this build. Four
//  separate connection attempts, each followed within ~2 seconds by the process
//  dying, with the trace showing a clean init and "Runtime ready: 18/18 probes
//  resolved" immediately beforehand. The process dies when a client connects.
//  That is a defect in IPCServer, and no amount of care at the reader end fixes
//  it.
//
//  So telemetry goes to a file instead. A file append cannot fault the game,
//  costs one CreateFile/WriteFile/CloseHandle, and is readable by anything.
//
//  Three properties make it usable rather than just safe:
//
//  - PHASE TAGGED. Every line carries [STARTUP], [MENU], [IN_GAME] or [ERROR]
//    so a reader can tell WHERE the game is without inferring it.
//  - LOW VOLUME. emitHeartbeat runs at 2Hz; logging every one of those would
//    be 172,800 lines an hour. The caller samples.
//  - CAPPED. The file stops growing at kMaxBytes. An unbounded log inside a
//    live process is a new way to hurt the thing being observed, and the tail
//    only ever needs the recent past.

inline constexpr std::uint64_t kMaxBytes = 2ull * 1024ull * 1024ull;

inline void session(const char* phase, const char* fmt, ...) {
    if (!checked()) {
        init();
    }
    if (path().empty()) {
        return;
    }
    // Derived from the trace path so there is one place that decides "am I
    // observing at all", and so the session log always lands beside it.
    static std::wstring sp;
    if (sp.empty()) {
        std::wstring p = path();
        const auto dot = p.find_last_of(L'.');
        sp = (dot == std::wstring::npos ? p : p.substr(0, dot)) + L".session.log";
    }

    char    body[900]{};
    va_list ap;
    va_start(ap, fmt);
    const int w = _vsnprintf_s(body, sizeof(body), _TRUNCATE, fmt, ap);
    va_end(ap);
    if (w < 0) {
        return;
    }

    SYSTEMTIME st{};
    GetLocalTime(&st);
    char out[1100]{};
    const int n = _snprintf_s(out, sizeof(out), _TRUNCATE,
                              "[%02u:%02u:%02u] [%-7s] %s\r\n",
                              st.wHour, st.wMinute, st.wSecond, phase, body);
    if (n < 0) {
        return;
    }

    HANDLE h = CreateFileW(sp.c_str(), FILE_APPEND_DATA,
                           FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                           OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
        return;
    }
    LARGE_INTEGER sz{};
    if (GetFileSizeEx(h, &sz) && static_cast<std::uint64_t>(sz.QuadPart) > kMaxBytes) {
        CloseHandle(h);
        return;  // capped; the tail keeps what it needs from the recent past
    }
    DWORD written = 0;
    WriteFile(h, out, static_cast<DWORD>(n), &written, nullptr);
    CloseHandle(h);
}

inline void line(const char* fmt, ...) {
    if (!checked()) {
        init();
    }
    if (path().empty()) {
        return;
    }

    char    body[1024]{};
    va_list ap;
    va_start(ap, fmt);
    const int written = _vsnprintf_s(body, sizeof(body), _TRUNCATE, fmt, ap);
    va_end(ap);
    if (written < 0) {
        return;
    }

    SYSTEMTIME st{};
    GetLocalTime(&st);
    char   out[1200]{};
    const int n = _snprintf_s(out, sizeof(out), _TRUNCATE,
                              "[%02u:%02u:%02u.%03u tid=%lu] %s\r\n",
                              st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
                              GetCurrentThreadId(), body);
    if (n < 0) {
        return;
    }

    HANDLE h = CreateFileW(path().c_str(), FILE_APPEND_DATA,
                           FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                           OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
        return;
    }
    DWORD writtenBytes = 0;
    WriteFile(h, out, static_cast<DWORD>(n), &writtenBytes, nullptr);
    // No FlushFileBuffers: a write to an append handle is already ordered, and
    // this path must not be able to stall the game it is observing.
    CloseHandle(h);
}

} // namespace f4mon::trace
