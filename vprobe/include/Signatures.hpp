// Signatures.hpp
//
// The target table: what vprobe tries to resolve, and how each one is
// justified. This is the file a new build lands in, and the file the build
// gate verifies against the real binary.
//
// THE ONE RULE THIS FILE ENFORCES
//   Every target below is a NAME THAT EXISTS IN THE GAME, or it is not here.
//   A target is not admitted because a plausible byte pattern was written for
//   it. It is admitted because the game's own emitted strings prove the class
//   is there, and the per-build address database says where it is.
//
//   That rule exists because of what happened the first time it was not
//   followed. Six "Tier 3" targets were hand-authored against six plausible
//   Papyrus class names -- PapyrusScript, PapyrusThread, PapyrusVM,
//   FormData::CellStream. Reading the RTTI out of the actual executable shows
//   there is no such thing as a class named PapyrusVM, PapyrusThread or
//   PapyrusScript in Fallout 4, and the only "FormData" hits are
//   SavedFormData, SavedFormData again inside a template, and
//   BGSLoadFormData. The patterns were not stale. They were written for
//   classes the game does not contain, so no amount of retuning them could
//   ever have matched, and "5 of 6 unresolved" read exactly like a database
//   that needed refreshing. Run tools/read_rtti.py to reproduce that finding.
//
//   What the game actually contains is BSScript::Internal::VirtualMachine
//   (and its BSScript::IVirtualMachine interface). Those are in the table
//   below, with measured slot counts.
//
// ON THE SLOT COUNTS
//   Every vtableSlots value here is MEASURED, not chosen. tools/
//   measure_vtable.py reads the real table out of Fallout4.exe, walks it until
//   it finds the CompleteObjectLocator of the NEXT class, and reports the
//   number of method slots in between. The build gate fails if this file and
//   the binary disagree, so these numbers cannot silently rot into a fiction
//   the way the previous uniform "8" did.
//
//   The measurement is not a formality. It corrected two things. The old
//   "8 for everything" over-read BSScript::IClientVM and BSScript::IVMDebugInterface,
//   claiming slots that belong to the following class, and under-read
//   BSScript::IVMSaveLoadInterface by eighteen. An over-read is the dangerous
//   direction: the slot past the end of a table is the next class's locator,
//   so a validator that trusts it will happily detour into an unrelated
//   interface. Measured, IClientVM has three methods and GameVM has three.
//
//   Note also that many slots resolve to the same address. That is MSVC
//   identical COMDAT folding, and it means "most slots point at code" is a
//   weak signal -- the runtime validator's real work is the boundary, not the
//   count. See the non-vtable refusal in the self-test.
//
//   An earlier handover recorded IClientVM as having 20 slots. It has three.
//   The 20 came from counting through the following tables; the boundary is
//   what stops that, and it is why the boundary rule is the load-bearing part
//   of measure_vtable.py rather than an afterthought.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "VersionConfig.hpp"

namespace f4mon::vc {

// ---------------------------------------------------------------------------
//  TIER 2 TARGETS -- vtables, from the per-build address database
// ---------------------------------------------------------------------------
//  An empty pattern means "no byte signature", and for a vtable that is not a
//  gap: a vtable is data, so there is nothing to pattern-match. These resolve
//  from the address database and are validated by the vtable rule in
//  VersionConfig -- a run of slots pointing into executable code, bounded by
//  the next class's RTTI locator.
//
//  The advantage over a byte pattern is the whole reason this table prefers
//  them: a pattern is a guess about ONE function, and it is wrong silently.
//  A vtable address is exact for the build, it is confirmed by the RTTI name
//  the compiler itself emitted, and it opens every method on the interface at
//  once instead of one per attempt.
//
//  slot counts below are measured by tools/measure_vtable.py; the gate
//  enforces them. Do not adjust one to make a check pass -- if a count is
//  wrong, the binary is what it is and the target name is what needs checking.

inline const Signature kDefaultSignatures[] = {
    // --- the VM core -------------------------------------------------------
    // BSScript::Internal::VirtualMachine is the class the old "PapyrusVM"
    // targets were reaching for. 62 slots.
    {"BSScript__Internal__VirtualMachine", "", 0, "the Papyrus VM itself",           62, TargetKind::VTable},
    {"BSScript__IVirtualMachine",          "", 0, "VM interface, no impl",          62, TargetKind::VTable},
    {"GameVM",                             "", 0, "game VM dispatch",                3, TargetKind::VTable},

    // --- VM sub-interfaces, all on the same object graph --------------------
    {"BSScript__IClientVM",                "", 0, "Papyrus VM client interface",      3, TargetKind::VTable},
    {"BSScript__IVMDebugInterface",        "", 0, "VM debug interface",               6, TargetKind::VTable},
    {"BSScript__IVMSaveLoadInterface",     "", 0, "VM save/load interface",          26, TargetKind::VTable},
    {"BSScript__IVMObjectBindInterface",   "", 0, "VM object bind interface",        11, TargetKind::VTable},

    // --- compilation and loading -------------------------------------------
    // CodeTasklet and ScriptFunction are what a "PapyrusScript::Execute"
    // target was reaching for: the compiled script and its function object.
    {"BSScript__Internal__CodeTasklet",    "", 0, "compiled script tasklet",         2, TargetKind::VTable},
    {"BSScript__Internal__ScriptFunction", "", 0, "one script function",            21, TargetKind::VTable},
    {"BSScript__CompiledScriptLoader",     "", 0, "loads compiled scripts",          4, TargetKind::VTable},
    {"BSScript__ILoader",                  "", 0, "script loader interface",         4, TargetKind::VTable},
    {"BSScript__IStore",                   "", 0, "script store interface",         12, TargetKind::VTable},

    // --- object model, policies, diagnostics --------------------------------
    {"BSScript__IObjectProcessor",         "", 0, "object processor",                4, TargetKind::VTable},
    {"BSScript__IFunction",                "", 0, "function interface",             21, TargetKind::VTable},
    {"BSScript__IComplexType",             "", 0, "complex type interface",          2, TargetKind::VTable},
    {"BSScript__IProfilePolicy",           "", 0, "VM profile policy",               5, TargetKind::VTable},
    {"BSScript__IMemoryPagePolicy",        "", 0, "VM memory page policy",           6, TargetKind::VTable},
    {"BSScript__ErrorLogger",              "", 0, "Papyrus error logger",            3, TargetKind::VTable},
};

// ---------------------------------------------------------------------------
//  QUARANTINED -- removed targets, kept so the reasoning is not repeated
// ---------------------------------------------------------------------------
//  These are the six dead Tier-3 AOB targets. They are NOT in
//  kDefaultSignatures and nothing resolves them, on purpose. They are
//  recorded here because the reasoning behind their removal is expensive to
//  re-derive and cheap to get wrong again.
//
//  A target                                     real class, if one exists
//  ------------------------------------------  --------------------------------
//  PapyrusVM::PapyrusVM                         BSScript::Internal::VirtualMachine
//  PapyrusVM::GetRunningThreadCount            (no per-thread class; a method of
//                                               the VM above)
//  PapyrusVM::DebugPrint                        BSScript::IVMDebugInterface
//  PapyrusScript::Execute                       BSScript::Internal::CodeTasklet
//                                               / ScriptFunction
//  PapyrusThread::Execute                       (no such class)
//  FormData::CellStream                         (no such class; BGSLoadFormData
//                                               is unrelated)
//
//  The "real class" column is a ROUTE, not a slot index. Which of the 62 slots
//  on BSScript::Internal::VirtualMachine is the one that reports a running
//  thread count is NOT derivable from a vtable -- it comes from a C++ class
//  declaration in declaration order, and the vendored CommonLibF4 clone in
//  third_party/ carries vtable ADDRESSES but no BSScript method declarations.
//  So that mapping is unsourced today and stays unsourced here. Filling it in
//  with a plausible guess is the exact mistake that produced this section.
//
//  The old patterns are gone rather than kept disabled, because a disabled
//  pattern still reads as a target in the tier report, and a report with six
//  permanently-dead rows trains the reader to stop reading it.
//
//  The two that were structurally hopeless regardless of naming, and are worth
//  remembering: kSigVmRunOnce and kSigCellStream both begin
//      48 8B 05 ?? ?? ?? ?? 48 85 C0 74 ?? 48 8B 40 ??
//  which is the standard optional-singleton idiom and matches hundreds of
//  unrelated functions. No prologue gate can save a pattern that generic: the
//  gate is what makes a narrow pattern safe, and these were never narrow.
//
//  To add a code target legitimately, the order is: find the class with
//  tools/read_rtti.py, get its address from the database, measure its table
//  with tools/measure_vtable.py, and only then decide whether a vtable slot
//  is enough or a byte pattern is genuinely required.

} // namespace f4mon::vc
