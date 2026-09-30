// Signatures.hpp
//
// AOB signature table. This is the file you edit when a new game build lands
// and AddressLib has not been regenerated yet -- it is also what a CI job diffs
// so regressions are reviewable.
//
// IMPORTANT: these signatures are *starting points*, not gospel. They are
// written against the shapes documented in Signatures.notes below and each one
// is validated by AddressResolver before use. If a signature stops matching,
// the hook disables itself and the dashboard reports it; nothing crashes.
//
// A good signature is:
//   * anchored on opcodes that appear once in .text,
//   * 24+ bytes long,
//   * located at a function entry (or a known offset from one).
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "VersionConfig.hpp"

namespace f4mon::vc {

// BSScript::PapyrusVM::PapyrusVM  -- constructor.
// Anchored on the debug-name RVA load that only PapyrusVM performs.
inline constexpr const char* kSigVmCtor =
    "48 8B ?? 48 89 5C 24 ?? 48 89 6C 24 ?? 48 8B DA 48 8B F9 E8 ?? ?? ?? ?? 48 8B 05 ?? ?? ?? ??";

// BSScript::PapyrusVM::GetRunningThreadCount / thread-list walk.
// The 0x400 (1024) stack-limit constant that gates Papyrus recursion lives in
// the same function; matching it is a strong signal we found the scheduler.
inline constexpr const char* kSigVmRunOnce =
    "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 ?? 48 8B 40 ?? 8B 90 ?? ?? ?? ?? 0F B6 C8 85 C9";

// BSScript::PapyrusScript::Execute -- the per-script interpreter entry.
// Matches the "call DebugPrint on error" tail that every generated script shares.
inline constexpr const char* kSigScriptExecute =
    "48 89 5C 24 ?? 48 89 6C 24 ?? 48 89 74 24 ?? 57 48 83 EC ?? 49 8B F0 48 8B DA 48 8B F9";

// BSScript::PapyrusVM::DebugPrint -- papyrus-side error reporting.
// The "%s" style indirect load chain is a 3-call signature that survives most
// retargets.
inline constexpr const char* kSigVmDebugPrint =
    "48 89 5C 24 ?? 48 89 6C 24 ?? 48 83 EC ?? 4C 8B C1 48 8B D9 ?? ?? 48 8B 01";

// BSScript::PapyrusThread::Execute -- the thread trampoline. A failed match here
// means we lose per-thread op counts but keep the rest of the probe.
inline constexpr const char* kSigThreadExecute =
    "48 89 5C 24 ?? 48 89 6C 24 ?? 40 53 48 83 EC ?? 48 83 C4 ?? 49 8B F9";

// FormData/heap object constructor used for cell-stream and object-count probes.
inline constexpr const char* kSigCellStream =
    "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 ?? 48 8B 40 ?? 8B 88 ?? ?? ?? ?? 89 44 24 ?? C3";

// ---------------------------------------------------------------------------
//  TIER 2 TARGETS -- vtables, from the AddressLib database
// ---------------------------------------------------------------------------
//  These are NOT AOB patterns. An empty pattern means "Tier 1 only": there is
//  no byte signature for a vtable, and inventing one would defeat the point.
//  They resolve from the address database and are validated by the vtable
//  rule -- a majority of consecutive slots must point into executable code.
//
//  These came from a static scan of the real Fallout4.exe for build
//  1.11.240, cross-checked against a live process. BSScript__IClientVM was
//  measured at 6 of 8 slots in .text, the remaining two being thunks in
//  .rdata, which is why the validator accepts a majority rather than all.
//
//  The empty pattern is also why these are worth having when the five AOB
//  signatures below match nothing. A byte pattern is a guess about one
//  function; a vtable address is data, exact for the build, and it opens up
//  every method on the interface at once instead of one at a time.

inline const Signature kDefaultSignatures[] = {
    // --- Tier 2: resolved from the address database ---------------------
    {"BSScript__IClientVM",              "", 0, "Papyrus VM client interface", 8, TargetKind::VTable},
    {"BSScript__IVMDebugInterface",      "", 0, "VM debug interface",           8, TargetKind::VTable},
    {"BSScript__IVMSaveLoadInterface",   "", 0, "VM save/load interface",       8, TargetKind::VTable},
    {"BSScript__IVMObjectBindInterface", "", 0, "VM object bind interface",     8, TargetKind::VTable},
    {"GameVM",                           "", 0, "game VM dispatch",             8, TargetKind::VTable},

    // --- Tier 3: AOB only, currently 1 of 6 verified --------------------
    // A note that matters when reading a failure: a zero here is NOT a
    // database failure. These are byte patterns written from documentation,
    // and the scan of the real binary found FIVE OF SIX MATCH NOTHING. They
    // fail safe, meaning the hook stays uninstalled and the game is
    // untouched -- correct behaviour, and also the reason the tier above
    // exists. See the SIGNATURE VALIDATION block in the design document.
    {"PapyrusVM::PapyrusVM",              kSigVmCtor,         0, "scheduler ctor", 8, TargetKind::Code},
    {"PapyrusVM::GetRunningThreadCount",  kSigVmRunOnce,       0, "thread-list walk", 8, TargetKind::Code},
    {"PapyrusScript::Execute",            kSigScriptExecute,  0, "script interpreter", 8, TargetKind::Code},
    {"PapyrusVM::DebugPrint",             kSigVmDebugPrint,    0, "script error print", 8, TargetKind::Code},
    {"PapyrusThread::Execute",            kSigThreadExecute,   0, "thread trampoline", 8, TargetKind::Code},
    {"FormData::CellStream",              kSigCellStream,      0, "cell stream ptr", 8, TargetKind::Code},
};

} // namespace f4mon::vc
