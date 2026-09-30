// test_helper_target.cpp -- a deliberately trivial "game".
//
// WHY THIS EXISTS
//   The core load path cannot be validated against Fallout 4 on a build
//   machine, and a test that asserts "injection works" without injecting
//   anything proves nothing (G1). So the load path is exercised against a
//   real Win32 process instead: it really is created suspended, really is
//   injected into, really is resumed, and really can fail to signal ready.
//
//   What this validates: CreateProcessW + CREATE_SUSPENDED, the TOCTOU
//   re-verification against the live address space, ordinary LoadLibraryW
//   injection, resume, and the handshake timeout.
//   What this does NOT validate: anything about Papyrus, or about
//   vprobe.dll specifically. Those remain unverified until a real game is
//   available. Pretending otherwise would be the exact failure G1 describes.
#include <windows.h>

#include <cstdio>

int wmain() {
    // Tell the launcher we are alive and past the entry point. Without this
    // the test cannot distinguish "resumed successfully" from "resumed into
    // nothing", which is the whole point of testing the resume step.
    HANDLE ev = OpenEventW(EVENT_MODIFY_STATE, FALSE, L"Local\\pipmon_pf_target_running");
    if (ev != nullptr) {
        SetEvent(ev);
        CloseHandle(ev);
    }

    // Exit on our own after a bounded time so a failing test cannot leave a
    // stray process behind. The launcher kills anything it still owns, but
    // only on a non-Ok path -- after release() the launcher has no handle,
    // so the process has to be able to leave on its own.
    Sleep(30000);
    return 0;
}
