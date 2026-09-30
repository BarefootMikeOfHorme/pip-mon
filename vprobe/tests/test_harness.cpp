// test_harness.cpp
//
// Out-of-process driver for vprobe's native self-test.
//
// Loads vprobe.dll, calls the exported VPROBE_SelfTest(), and renders the
// report. Exists so the checks run in CI and locally without launching the
// game -- the same code path that runs in-game at cell load.
//
// This is the harness Gemini's plan called for, wired to the implementation.

#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0A00
#endif
#include <Windows.h>

#include <cstdio>
#include <cstring>
#include <string>

namespace {

using SelfTestFn  = const char* (*)();
using SelfTestFree = void (*)(char*);

int g_failures = 0;

void check(bool cond, const char* what) {
    std::printf("  [%s] %s\n", cond ? "PASS" : "FAIL", what);
    if (!cond) ++g_failures;
}

} // namespace

int main() {
    setvbuf(stdout, nullptr, _IONBF, 0);
    std::printf("PIP-MON native test harness (no game running)\n");
    std::printf("============================================\n\n");

    const HMODULE dll = LoadLibraryW(L"vprobe.dll");
    if (!dll) {
        std::printf("  [FAIL] LoadLibraryW: %lu\n", GetLastError());
        return 1;
    }
    check(true, "vprobe.dll loaded");

    auto selfTest = reinterpret_cast<SelfTestFn>(GetProcAddress(dll, "VPROBE_SelfTest"));
    auto selfFree = reinterpret_cast<SelfTestFree>(GetProcAddress(dll, "VPROBE_SelfTestFree"));
    auto selfText = reinterpret_cast<SelfTestFn>(GetProcAddress(dll, "VPROBE_SelfTestText"));

    check(selfTest != nullptr, "export VPROBE_SelfTest resolved");
    check(selfFree != nullptr, "export VPROBE_SelfTestFree resolved");
    if (!selfTest || !selfFree) {
        FreeLibrary(dll);
        return 1;
    }

    // --- run the in-DLL self-test -----------------------------------------
    std::printf("\n--- self-test (text) ---\n");
    if (selfText) {
        const char* text = selfText();
        if (text) {
            std::fputs(text, stdout);
            selfFree(const_cast<char*>(text));
        }
    }

    const char* json = selfTest();
    if (!json) {
        std::printf("  [FAIL] VPROBE_SelfTest returned null\n");
        FreeLibrary(dll);
        return 1;
    }
    const std::string report(json);
    selfFree(const_cast<char*>(json));

    // The JSON is what OverseerCLI's DegradedProbeRule consumes, so asserting
    // its shape here means the dashboard cannot be handed a malformed report.
    std::printf("\n--- report contract ---\n");
    check(report.find("\"kind\":\"selftest\"") != std::string::npos,
          "report carries kind=selftest");
    check(report.find("\"ok\":true") != std::string::npos,
          "report declares ok=true (no check failed)");
    check(report.find("\"pass\":") != std::string::npos, "report carries a pass count");
    check(report.find("abi_layout") != std::string::npos, "abi_layout check present");
    check(report.find("scanner_synthetic") != std::string::npos, "scanner check present");
    check(report.find("wire_roundtrip") != std::string::npos, "wire round-trip present");

    // --- plugin surface ----------------------------------------------------
    std::printf("\n--- plugin surface ---\n");
    using MakeInfoFn = bool (*)(void*);
    auto makeInfo = reinterpret_cast<MakeInfoFn>(
        GetProcAddress(dll, "F4SEAPI_MakePluginInfo"));
    struct PluginInfo { unsigned infoVersion; const char* name; unsigned version; };
    PluginInfo info{};
    check(makeInfo != nullptr && makeInfo(&info), "F4SEAPI_MakePluginInfo");
    check(info.name != nullptr && std::strcmp(info.name, "V-Probe") == 0,
          "plugin name is \"V-Probe\"");
    std::printf("         version=0x%08X\n", info.version);

    FreeLibrary(dll);
    std::printf("\n%s (%d failure%s)\n",
                g_failures == 0 ? "HARNESS PASS" : "HARNESS FAIL",
                g_failures, g_failures == 1 ? "" : "s");
    return g_failures == 0 ? 0 : 1;
}
