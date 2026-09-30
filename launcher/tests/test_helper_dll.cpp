// test_helper_dll.cpp -- a stand-in for vprobe.dll.
//
// It exercises the SAME two-stage contract as the real runtime, because the
// contract is the thing under test and a simplified version of it would prove
// nothing. The real ReadySignal.hpp is INCLUDED rather than reimplemented, so
// the event names cannot drift between the two sides.
//
//   pipmon_runtime_loaded   from DllMain   (proves the DLL mapped)
//   pipmon_runtime_ready    after init     (proves it is useful)
//
// Three build variants cover the three states a launcher must tell apart:
//
//   default        both signals            -> Ok
//   NO_LOADED      signals neither         -> HandshakeTimeout (injection lies)
//   NO_READY       loaded only             -> Degraded (running but blind)
//
// The last two matter more than the first. A launcher that always reports
// success is indistinguishable from one that works until the one time a
// runtime fails to initialise in the field.
#include <windows.h>

// The real header, so event names cannot drift between launcher and runtime.
#include "ReadySignal.hpp"

#if defined(PIPMON_DLL_NO_LOADED) && defined(PIPMON_DLL_NO_READY)
#error "build at most one negative variant"
#endif

// Init completion stands in for a worker thread. The real runtime does this
// after its probes are installed; here the timing is what matters, not the
// work, so a short thread reproduces the ordering.
namespace {
DWORD WINAPI initThread(LPVOID) {
    Sleep(150);
#if !defined(PIPMON_DLL_NO_READY)
    f4mon::runtime::signalReady(0, 0);
#endif
    return 0;
}
} // namespace

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID reserved) {
    (void)reserved;

    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);

        // Runs under the loader lock, while the process is still suspended
        // under launcher injection. signalLoaded() only opens and sets, so it
        // is safe here -- and it must happen here, because the event has to
        // already exist.
#if !defined(PIPMON_DLL_NO_LOADED)
        // A no-launcher run is a legitimate state, not a failure: the fixture
        // must stay useful when loaded by hand. The return is deliberately
        // discarded rather than asserted on, because there is no launcher in
        // that case to be listening.
        (void)f4mon::runtime::signalLoaded();
#endif

        HANDLE t = CreateThread(nullptr, 0, initThread, nullptr, 0, nullptr);
        if (t != nullptr) CloseHandle(t);
    }
    return TRUE;
}
