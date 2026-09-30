// PipmonEntry.cpp -- our own load contract, plus the F4SE adapter.
//
// The single most important structural fact in this file: there is ONE
// implementation, and both load paths reach it. F4SE is an adapter over our
// entry points, not a parallel way of doing the same work. Two
// implementations would be a second thing to keep correct, and the whole
// point of moving off the F4SE ABI is to stop having that.
#include "PipmonEntry.hpp"

#include <Windows.h>

#include <atomic>
#include <cstdio>
#include <cstring>
#include <string>

#include "ReadySignal.hpp"
#include "RuntimeLifecycle.hpp"

namespace {

std::atomic<bool> g_initialized{false};

// Written on the init path, read from anywhere. Deliberately a fixed buffer
// and a copy, never a std::string returned by pointer: a hook or a foreign
// loader may call PIPMON_LastError concurrently, and an allocation there would
// be a use-after-free on a path that exists precisely to explain a crash.
constexpr std::size_t kErrLen = 256;
char g_lastError[kErrLen] = "";

void setLastError(const char* text) {
    if (text == nullptr) {
        g_lastError[0] = '\0';
        return;
    }
    std::snprintf(g_lastError, kErrLen, "%s", text);
}

} // namespace

// The real initialisation lives in main.cpp, which already owns the worker
// thread, the resolver, the hooks and the IPC server. This entry point
// deliberately does not duplicate any of it -- it is the door, not the room.
// (Declared in RuntimeLifecycle.hpp; onLoad and onUnload are NOT in an
// anonymous namespace, precisely so this file can reach them.)

extern "C" {

const char* PIPMON_LastError(void) {
    return g_lastError;
}

int PIPMON_Query(const PipmonVersion* out) {
    if (out == nullptr) {
        return 1;   // EINVAL, by hand: this file stays dependency-free
    }
    // out is documented as an out-parameter despite the const pointer, so the
    // cast is the intended pattern rather than a way around a type check.
    auto* v = const_cast<PipmonVersion*>(out);

    v->abiVersion = PIPMON_ABI_VERSION;

    // What is ACTUALLY there, which is not the same as what is planned. These
    // bits are asserted by the self-test, so a bit cannot be set optimistically
    // without a check failing.
    v->capsSupported = PIPMON_CAP_TELEMETRY
                       | PIPMON_CAP_HEARTBEAT
                       | PIPMON_CAP_MEMORY
                       | PIPMON_CAP_VTABLES;

    // Present, but not yet trustworthy in a live game. vtable resolution is
    // written and unit-tested; it has been proven against a live process by an
    // external tool, but not yet observed resolving through the in-process
    // resolver. Reporting it as degraded rather than as either present or
    // absent is the honest position and is the whole reason the field exists.
    v->capsOptional = PIPMON_CAP_VTABLES;

    return 0;
}

int PIPMON_Initialize(void) {
    if (g_initialized.exchange(true, std::memory_order_acq_rel)) {
        // Idempotent by contract: a loader may probe then load then load again.
        return 0;
    }

    // Tell the launcher the module is mapped. Under injection this happens
    // while the process is still suspended, so the launcher must have created
    // the event before it injected us -- see ReadySignal.hpp.
    (void)f4mon::runtime::signalLoaded();

    f4mon::app::onLoad();

    setLastError("");
    return 0;
}

void PIPMON_Shutdown(void) {
    if (!g_initialized.exchange(false, std::memory_order_acq_rel)) {
        return;
    }
    f4mon::app::onUnload();
}

bool F4SEAPI_MakePluginInfo(PluginInfo* out) {
    if (out == nullptr) {
        return false;
    }
    out->infoVersion = 1;
    // The name is what F4SE shows in its plugin list, so it is a USER-FACING
    // string belonging to the compatibility surface, not to our identity.
    // Renaming it here was a mistake caught by the self-test: the runtime's
    // name is "V-Probe" and the product's is "PIP-MON", and conflating the two
    // would show the wrong one in F4SE's plugin list. They are different
    // things and this is where the F4SE-facing one lives.
    out->name        = "V-Probe";
    out->version     = 0x00010000;   // 1.0.0
    return true;
}

void VPROBE_OnLoad(void) {
    (void)PIPMON_Initialize();
}

void VPROBE_OnUnload(void) {
    PIPMON_Shutdown();
}

} // extern "C"
