// PapyrusApi.hpp -- the registered-native surface: our Layer B dispatch core.
//
// WHY THIS FILE EXISTS
//   The design (section 24) splits Papyrus integration into two layers:
//
//     LAYER A  the registration choke point. ONE hook on the game's VM
//              native-function resolution. When Papyrus asks the VM to resolve
//              a native, we get asked first and hand back a NativeFunction.
//              This is the part that cannot be written until we can observe
//              the VM, and it is what the S0 viability test is about.
//
//     LAYER B  the dispatch core. A pure mapping from (namespace, name, arity)
//              to a handler, with no dependency on the game whatsoever.
//
//   LAYER B is this file, and it is deliberately the whole of what exists
//   today. It is the part that is genuinely finished and testable, and it is
//   exactly the code Layer A will call when it eventually gets hooked. Writing
//   the surface first and the hook second means the risky, VM-dependent part
//   is reduced to "call findNative and build a NativeFunction" -- which is a
//   few dozen lines -- instead of a rewrite once the VM is finally visible.
//
//   Nothing here includes a game header, and nothing here links against F4SE.
//   That is not a stylistic preference: it is what makes the surface testable
//   with the game absent, which is the only way to keep it honest while the
//   VM-facing half is still unproven.
//
// THE NAMESPACE IS A REGISTRATION KEY, NOT A LABEL
//   "PipMon" is a field in the VM's function descriptor that the engine
//   matches on. Getting it wrong does not produce a warning; it produces a
//   script that calls into nothing. So it is a compile-time constant here and
//   the self-test asserts the table is keyed on it, rather than being a
//   string literal repeated across the codebase where a typo would be silent.
#pragma once

#include <cstdint>

namespace f4mon::papyrus {

// ---------------------------------------------------------------------------
// A marshaling-agnostic call frame
// ---------------------------------------------------------------------------
//
// The real thing is a VMValue. This is not, and pretending otherwise would
// make the surface untestable without the game. It is a fixed set of typed
// slots, which is enough to express every signature in the S0/S1 surface and
// enough to prove the dispatcher routes correctly.
//
// The distinction matters: the DISPATCH decision (which handler) is separable
// from the MARSHALING decision (how a VMValue becomes a slot). We can be
// certain about the first while the second is still unproven, so the two are
// kept apart instead of entangled in one VMValue-shaped struct.
struct CallFrame {
    static constexpr int kMaxArgs = 4;

    // Arguments, positional. Only the first `argCount` are meaningful.
    std::int64_t args[kMaxArgs]{};
    int argCount = 0;

    // Return slot. `hasResult` distinguishes "returned 0" from "returned
    // nothing", which matters for a Void function and for a native that
    // failed -- both would otherwise be indistinguishable from a real zero.
    std::int64_t result = 0;
    bool hasResult = false;

    // False for String / String[] / struct returns in the current build. It is
    // carried rather than implied so that a caller can refuse cleanly instead
    // of reading a marshaling slot that was never filled. See S1 in the
    // design: this is the flag that will flip when the type bridge is proven.
    bool resultIsMarshaled = false;
};

// A handler. Returns false when it could not service the call, which is
// different from succeeding with a zero result.
using NativeHandler = bool (*)(CallFrame& frame);

// ---------------------------------------------------------------------------
// The registry
// ---------------------------------------------------------------------------
//
// A descriptor per registered native. Mirrors, field for field, the parts of
// BSScript::NativeFunctionBase that the VM actually matches on -- name,
// class, arity, and static-ness -- so that populating a real NativeFunction
// from an entry is a copy rather than a reinterpretation. Anything that cannot
// be expressed here is a sign the surface has outgrown the assumption.
struct NativeEntry {
    const char*   className;   // "PipMon" -> NativeFunctionBase::m_className
    const char*   name;        // "GetVersion" -> m_fnName
    int           arity;       // m_params.realNumParams
    bool          isGlobal;    // m_isStatic. Every entry here is Global: these
                               // are callable as PipMon:Foo() from anywhere and
                               // need no script instance, which is the point of
                               // an API class.
    NativeHandler handler;     // null => declared but NOT BUILT (see below)
};

// Declared-but-unbuilt is a first-class state, deliberately not an error.
// The design splits the build into S0..S3, and S1/S2/S3 functions exist in
// the surface before their marshaling is proven. Encoding them as present but
// inert means a script referencing one gets a clean "not available" from
// invokeNative() rather than a call into a null pointer, and means the
// conformance check can assert the full intended surface from day one.
//
// The alternative -- only listing what works -- hides the target. The whole
// point of the staged build is that the shape of the finished surface is known
// now and the parts that are proven are marked, not the parts that are absent.
const NativeEntry* findNative(const char* className, const char* name, int arity);

// The whole table, for introspection and for the conformance self-test. The
// index is stable; a script that caches a pointer across our own reloads is
// relying on something we do not promise.
int nativeCount();
const NativeEntry* nativeAt(int index);

// Routes a call. Returns false -- cleanly, never by crashing -- when the
// (class, name, arity) triple is unknown or the entry is not yet built. The
// arity check is deliberate: a script that calls GetVersion with an argument
// is a caller bug, and silently servicing it would hide a real mismatch
// between the .psc and the table.
bool invokeNative(const char* className, const char* name, CallFrame& frame);

// ---------------------------------------------------------------------------
// The namespace, as a constant
// ---------------------------------------------------------------------------
//
// Per section 23.3/23.4: our own class, never a vanilla type. Every entry is
// keyed on this. Exposed so the self-test can assert the invariant rather
// than trusting that nobody added a System: entry.
inline constexpr const char* kNamespace = "PipMon";

} // namespace f4mon::papyrus
