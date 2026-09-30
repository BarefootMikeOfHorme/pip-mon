// RuntimeLifecycle.hpp -- internal lifecycle hooks, shared across
// translation units.
//
// WHY THIS IS A HEADER
//   onLoad and onUnload are the only two functions in vprobe that cross a
//   translation-unit boundary: PipmonEntry.cpp calls them, main.cpp defines
//   them. They used to be invisible to each other because they sat beside
//   their own callers, which is exactly the arrangement that made the F4SE ABI
//   look like the interface -- the only way in was through a plugin struct.
//
//   Declared here so the load path is OUR code with OUR names, and the F4SE
//   exports in PipmonEntry.cpp are recognisable as adapters rather than
//   mistaken for the primary API.
//
// NOT a public header. Nothing outside vprobe may call these; the supported
// surface is PipmonEntry.hpp. These are declared non-inline so there is one
// definition, in main.cpp.
#pragma once

namespace f4mon::app {

// Starts the runtime: spins the worker, resolves addresses, installs probes,
// opens the V-Link pipe. Idempotent -- a second call while the worker is
// running returns immediately rather than initialising twice.
void onLoad();

// Stops the runtime and removes any hooks it installed. Idempotent.
void onUnload();

} // namespace f4mon::app
