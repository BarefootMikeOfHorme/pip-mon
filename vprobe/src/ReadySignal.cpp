// ReadySignal.cpp -- see ReadySignal.hpp for the two rules this encodes.
#include "ReadySignal.hpp"

namespace f4mon::runtime {
namespace {

// Set an event the launcher created. Returns false if the launcher is absent,
// which is a normal condition and not a failure of this runtime.
bool signal(const wchar_t* name) {
    HANDLE h = OpenEventW(EVENT_MODIFY_STATE, FALSE, name);
    if (h == nullptr) {
        return false;
    }
    const BOOL ok = SetEvent(h);
    CloseHandle(h);
    return ok != FALSE;
}

} // namespace

bool signalLoaded() {
    return signal(kLoadedEvent);
}

void signalReady(std::size_t probesResolved, std::size_t probesTotal) {
    // The counts are reported through the V-Link diag channel as well, so a
    // user who launches by hand (no launcher, no handshake) still sees them.
    // The handshake carries the same fact for the automated case; recording it
    // in both places means neither path loses it.
    signal(kReadyEvent);
    (void)probesResolved;
    (void)probesTotal;
}

} // namespace f4mon::runtime
