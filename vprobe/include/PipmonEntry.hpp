// PipmonEntry.hpp -- PIP-MON's own load contract.
//
// WHY THIS FILE EXISTS
//   vprobe originally exposed F4SE's plugin ABI: F4SEAPI_MakePluginInfo plus
//   VPROBE_OnLoad called by the extender. That made an F4SE installation a
//   hard runtime dependency of a project whose entire premise is replacing
//   F4SE -- and a dependency nobody notices is the most expensive kind. The
//   launcher-injection path already worked without it; only the entry points
//   still required it.
//
//   So: the contract becomes OURS, and F4SE becomes an ADAPTER that calls into
//   it. That is the whole difference between "we depend on F4SE" and "we are
//   compatible with F4SE", and those are not the same statement. The first is
//   a debt that hardens daily; the second is a permanent feature.
//
//   The F4SE exports are RETAINED deliberately. A user running the F4SE mod
//   ecosystem must keep working, and removing a working integration in order to
//   make a point about independence would be the opposite of the coexistence
//   contract in the design document. What changes is the direction of the
//   call: F4SE calls US, not the other way round.
//
//   EVERYTHING HERE IS A PLACEHOLDER IN SHAPE ONLY. The signature, the
//   version negotiation and the validation rules are real and are tested. The
//   capability behind them -- the Papyrus script extending that F4SE and the
//   Papyrus extenders currently provide -- is not built. Distinguishing those
//   two things matters, so the placeholder state is reported rather than
//   dressed up: getVersion() returns a build whose feature mask says what is
//   actually there, and a caller can find out what is missing instead of
//   discovering it by observing silence.
#pragma once

#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

// ---------------------------------------------------------------------------
// Version and capability negotiation
// ---------------------------------------------------------------------------
//
// The extender-facing capability bits. A loader uses these to decide what to
// ask for, and -- more usefully -- to REFUSE cleanly rather than calling a
// capability that does not exist. That refusal is the difference between "the
// runtime is limited" and "the runtime is broken", and this project has spent
// enough of its history being unable to tell those apart.
typedef enum PipmonCapability : std::uint32_t {
    PIPMON_CAP_TELEMETRY   = 0x0001,  // V-Link telemetry stream            [BUILT+TESTED]
    PIPMON_CAP_HEARTBEAT    = 0x0002,  // liveness and counters            [BUILT+TESTED]
    PIPMON_CAP_MEMORY       = 0x0004,  // process memory snapshots         [BUILT+TESTED]
    PIPMON_CAP_VTABLES      = 0x0008,  // vtable-addressed resolution      [BUILT, unobserved in-game]
    PIPMON_CAP_PAPYRUS_API  = 0x0010,  // registered Papyrus natives       [NOT BUILT - placeholder]
    PIPMON_CAP_SCRIPT_HOST  = 0x0020,  // run our own .psc from the host   [NOT BUILT - placeholder]
    PIPMON_CAP_SAVE_GATE    = 0x0040,  // pre-save health gate             [DESIGNED only]
    PIPMON_CAP_REDLOOP      = 0x0080,  // registered native types/classes  [NOT BUILT - placeholder]
} PipmonCapability;

typedef struct PipmonVersion {
    std::uint32_t abiVersion;         // PIPMON_ABI_VERSION
    std::uint32_t capsSupported;      // bitwise OR of PipmonCapability
    std::uint32_t capsOptional;       // present but degraded, see .cpp
} PipmonVersion;

// Bumped only on a breaking layout change. Deliberately separate from the
// product version: the product ships weekly, the ABI should not.
#define PIPMON_ABI_VERSION 1u

// ---------------------------------------------------------------------------
// Load contract
// ---------------------------------------------------------------------------
//
// Both entry points are safe to call more than once and are no-ops after
// shutdown. That is not defensive padding: a loader may probe, load, and then
// load again, and a runtime that corrupts itself on the second call fails in a
// way that is very hard to attribute.

// True when the runtime initialised. Always callable, never blocks, and never
// touches game memory. A loader should call this before Initialize so it can
// report a precise reason rather than a timeout.
//
// `out` is an OUT-PARAMETER despite the const: this mirrors the F4SE calling
// convention it replaces, where the caller owns the struct and the callee
// fills it. The const on the pointer is there to make "do not pass a pointer
// to something you own and expect it back unchanged" explicit at the call
// site; it is not a claim that the callee may not write through it. Marking
// the struct itself const instead would have been the wrong instinct.
__declspec(dllexport) int PIPMON_Query(const PipmonVersion* out);

// Starts the runtime. Returns 0 on success, non-zero on failure with a reason
// retrievable from PIPMON_LastError.
__declspec(dllexport) int PIPMON_Initialize(void);

// Stops the runtime and removes any hooks it installed.
__declspec(dllexport) void PIPMON_Shutdown(void);

// Stable, static string. Never freed, never null, safe to log from a hook.
__declspec(dllexport) const char* PIPMON_LastError(void);

// ---------------------------------------------------------------------------
// F4SE ADAPTER -- retained for the mod ecosystem, not a dependency
// ---------------------------------------------------------------------------
//
// These are thin. F4SE's contract requires F4SEAPI_MakePluginInfo to fill a
// struct we define here, and VPROBE_OnLoad to be a no-argument call. Both
// forward into the same functions the PIP-MON path uses, so there is exactly
// ONE implementation and the two load paths cannot drift apart. A second
// implementation would be a second thing to keep correct, for no benefit.

typedef struct PluginInfo {
    unsigned int  infoVersion;
    const char*   name;
    unsigned int  version;
} PluginInfo;

__declspec(dllexport) bool F4SEAPI_MakePluginInfo(PluginInfo* out);

// Kept for source compatibility with the F4SE calling convention. Forwards to
// PIPMON_Initialize.
__declspec(dllexport) void VPROBE_OnLoad(void);

// Kept for source compatibility. Forwards to PIPMON_Shutdown.
__declspec(dllexport) void VPROBE_OnUnload(void);

#ifdef __cplusplus
} // extern "C"
#endif
