// PapyrusApi.cpp -- the registered-native surface: dispatch core (Layer B).
//
// See PapyrusApi.hpp for why this exists and what it deliberately excludes.
// The short version: this is the code the eventual VM hook (Layer A) will
// call, and it is pure -- no game headers, no F4SE, no VM types -- so the
// surface can be proven correct while the VM-facing half is still unproven.
#include "PapyrusApi.hpp"

#include "PipmonEntry.hpp"

#include <cstring>

namespace f4mon::papyrus {
namespace {

// --- S0 handlers: the three that need no marshaling and no game --------------
//
// Each reads the SAME capability/ABI source the loader entry points use
// (PipmonEntry.hpp), so the in-process ABI and the Papyrus surface cannot
// drift into reporting different things. A caller asking the script
// GetCapabilities() and a loader asking PIPMON_Query() get one answer, from
// one place.

bool handleGetVersion(CallFrame& frame) {
    frame.result = static_cast<std::int64_t>(PIPMON_ABI_VERSION);
    frame.hasResult = true;
    frame.resultIsMarshaled = true;   // int crosses cleanly at S0
    return true;
}

bool handleGetCapabilities(CallFrame& frame) {
    PipmonVersion v{};
    if (PIPMON_Query(&v) != 0) {
        return false;   // the runtime could not report; refuse rather than lie
    }
    frame.result = static_cast<std::int64_t>(v.capsSupported);
    frame.hasResult = true;
    frame.resultIsMarshaled = true;
    return true;
}

// Currently the same mask as GetCapabilities, and that redundancy is
// deliberate rather than an oversight: GetRuntimeStatus is the function a
// live script will call most, and pinning it to the identical source today
// means the two can only diverge if someone edits one. It is expected to
// split later (status vs. feature negotiation are different questions) and
// the split should be a visible decision, not an accident.
bool handleGetRuntimeStatus(CallFrame& frame) { return handleGetCapabilities(frame); }

// --- The table --------------------------------------------------------------
//
// One row per function in the PapMon: surface. The names and arities here are
// the CONTRACT with vprobe/papyrus/PipMon.psc, and the self-test asserts the
// two agree in both directions -- a .psc function with no table row, or a
// table row with no .psc declaration, both fail the build. That two-way check
// is the whole point of the conformance test: a surface that exists only in
// C++ is invisible to a mod author, and one that exists only in Papyrus calls
// into nothing.
//
// A null handler means declared-but-not-built (S1+). See PapyrusApi.hpp.
const NativeEntry kTable[] = {
    // className          name                     arity  global  handler
    {kNamespace,        "GetVersion",              0,    true,   &handleGetVersion},
    {kNamespace,        "GetRuntimeStatus",        0,    true,   &handleGetRuntimeStatus},
    {kNamespace,        "GetCapabilities",         0,    true,   &handleGetCapabilities},

    // S1 -- marshaling probe. Not built: returning a String/String[] needs the
    // type bridge, which is the unproven part.
    {kNamespace,        "GetStringTest",           0,    true,   nullptr},
    {kNamespace,        "GetStringArrayTest",      0,    true,   nullptr},

    // S0-adjacent probes / triage. Not built: each needs the resolver, the
    // save gate, or the event ring, none of which are proven.
    {kNamespace,        "GetAdjudicationCount",    0,    true,   nullptr},
    {kNamespace,        "GetResolvedProbeCount",   0,    true,   nullptr},
    {kNamespace,        "GetResolvedProbes",       0,    true,   nullptr},
    {kNamespace,        "IsHookLive",              1,    true,   nullptr},
    {kNamespace,        "RegisterForEvents",       1,    true,   nullptr},
    {kNamespace,        "UnregisterFromEvents",    1,    true,   nullptr},
    {kNamespace,        "GetLibraryCount",         0,    true,   nullptr},
    {kNamespace,        "GetLibraryInventory",     0,    true,   nullptr},
};

constexpr int kTableSize = static_cast<int>(sizeof(kTable) / sizeof(kTable[0]));

} // namespace

int nativeCount() { return kTableSize; }

const NativeEntry* nativeAt(int index) {
    if (index < 0 || index >= kTableSize) {
        return nullptr;
    }
    return &kTable[index];
}

const NativeEntry* findNative(const char* className, const char* name, int arity) {
    if (className == nullptr || name == nullptr) {
        return nullptr;
    }
    for (const auto& e : kTable) {
        // strcmp rather than ==: the VM hands us C strings, and a length-based
        // compare would need a length we do not have here.
        if (std::strcmp(e.className, className) == 0 &&
            std::strcmp(e.name, name) == 0 &&
            e.arity == arity) {
            return &e;
        }
    }
    return nullptr;
}

bool invokeNative(const char* className, const char* name, CallFrame& frame) {
    const NativeEntry* e = findNative(className, name, frame.argCount);
    if (e == nullptr) {
        return false;   // unknown, or called with the wrong arity
    }
    if (e->handler == nullptr) {
        return false;   // declared but not built yet (S1+)
    }
    return e->handler(frame);
}

} // namespace f4mon::papyrus
