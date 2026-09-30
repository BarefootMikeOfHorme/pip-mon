// ReadySignal.hpp
//
// The launcher's proof-of-life contract with the in-process runtime.
//
// WHY A HANDSHAKE AT ALL
//   Injection succeeding does not mean the runtime initialised. LoadLibraryW
//   returning non-zero only means the DLL mapped. If vprobe then fails to
//   start its pipe, or crashes during init, the user gets a game that runs
//   perfectly and produces no telemetry -- with no indication of why. That is
//   the worst outcome available to a diagnostic tool, because the game looks
//   fine, so the tool is assumed broken silently.
//
//   The handshake converts that into a bounded failure the launcher can
//   report in a sentence.
//
// WHY THE PARENT CREATES THE EVENT
//   Two rules, both learned the hard way (PAST MISTAKES M9 in the design doc):
//
//     1. The LAUNCHER creates the event, before injection. The runtime's
//        DllMain runs at injection time, while the process is still
//        suspended -- long before any wait would begin. If the event does not
//        exist yet, the runtime's OpenEvent fails and it will never retry.
//
//     2. The RUNTIME only ever opens and sets. A named kernel object is
//        destroyed when its last handle closes, so a runtime that did
//        CreateEvent + SetEvent + CloseHandle -- the obvious implementation --
//        destroys the very thing it just signalled.
//
// WHY THERE ARE TWO SIGNALS, NOT ONE
//   "The DLL loaded" and "the probes are live" are different facts, and
//   collapsing them would let a future reader believe the latter when only the
//   former happened. Before a real game is present, hooks cannot resolve and
//   probes cannot be trusted, so those two must stay separable.
//     pipmon_runtime_loaded   DllMain ran, module is mapped
//     pipmon_runtime_ready    init completed AND every probe resolved
//
//   The launcher treats "loaded without ready" as a DEGRADED outcome, not a
//   success. That distinction is the entire point of the two-signal design.
#pragma once

#include <windows.h>

#include <string>

namespace f4mon::runtime {

// Names are fixed so the launcher and the runtime cannot drift apart. If either
// side changes one, the handshake silently stops working -- which is exactly
// the failure this mechanism is meant to detect, so they are centralised here
// rather than duplicated as string literals in two projects.
inline constexpr const wchar_t* kLoadedEvent = L"Local\\pipmon_runtime_loaded";
inline constexpr const wchar_t* kReadyEvent  = L"Local\\pipmon_runtime_ready";

// Signalling half. Safe to call from DllMain: OpenEvent and SetEvent do not
// take a loader lock that DllMain already holds, and they do not load any
// further DLLs.
//
// Returns false only if the launcher is not listening. That is worth knowing
// but is NOT an error worth aborting init over: the runtime is equally useful
// when launched by hand or by a future loader that has not been written yet.
[[nodiscard]] bool signalLoaded();

// Called once init is complete. Reports how many probes resolved so the
// launcher can distinguish "fully live" from "running but blind".
void signalReady(std::size_t probesResolved, std::size_t probesTotal);

} // namespace f4mon::runtime
