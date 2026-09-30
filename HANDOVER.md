================================================================================
 PIP-MON SESSION HANDOVER
 Written 2026-09-29. Supersedes the pre-scripting snapshot of the same name.
================================================================================

 PURPOSE
   A cold-start brief. Someone reading only THIS file and the design doc
   should be able to continue without re-deriving history, and without
   mistaking a proposal for a decision.

   This document is a SNAPSHOT and it rots. The design doc
   (PIP-MON_CONSOLIDATED.txt) is append-only and self-maintaining; this file
   is not. If the two ever disagree, THIS FILE IS WRONG -- see section 8.

 HOW TO VERIFY THIS FILE IS STILL TRUE
   cd <repo> && build_all.bat
   Expected: vprobe 15 pass / 0 fail / 2 skip, launcher 45, python 67, rust 5,
   "#  ALL GATES PASSED", exit 0.
   A different self-test count means this file is stale, not that the build
   broke. That specific lie is what the previous version of this file told.

================================================================================
 0. STANDING RULES -- READ BEFORE TOUCHING ANYTHING
================================================================================

 G1  Native/unreplaceable: Fallout4.exe, the Papyrus VM, .pex, Bethesda record
     and archive formats. Never reimplement; never monkey-patch.
 G2  Replace: F4SE's tooling role, extender plugins (po3/PCL/GoE Script
     Extender), Canary-style diagnostics, MCM-style tooling.
 G3  Peer tool, not a target: G.E.C.K. / Garden of Eden environment creation.
 G4  Vortex is a live A1/VFS case, not a runtime dependency.
 G5  Never modify or remove extenders during live gameplay. Main menu with no
     loaded save is the only automation-safe window.
 G6  CLI/library carries all functionality. The dashboard is an optional view
     (G16). No in-game UI on a game thread.
 G7  F4SE and existing extenders are backup / reference / verification controls.
     The decisive exit test is a game with NO F4SE and NO extender, where we
     register a native and call it from Papyrus.
 G8  Own script extension is NEXT. The general common-library / patcher engine
     is LAST. (Design section 22.)
 G9  Read, test, and validation are pre-approved. Never write or delete
     outside the project without naming the exact path and getting explicit
     permission. (G15, Q15.)
 G10 Never commit or push unless asked.
 G11 BUILD-BACKEND HEAVY, IN-GAME LIGHT. Over-engineer the machine/backend
     side; keep the in-game side small, fast, and validated. (Section 26.)
 G12 Refuse, do not guess. See section 5.

================================================================================
 1. THE TIER MODEL -- THE SPINE (design section 26)
================================================================================

   Tier  What it is                          Written for  Cost allowed
   ----  -----------------------------------  -----------  ----------------
   T0    Fallout4.exe as bytes                accuracy     raw, no comfort
   T1    Oracle: extracts facts from T0       provenance   slow, offline
   T2    Library: the facts, queryable        speed        zero-alloc in-game
   T3    Surface: PIPMON_*, V-Link, PipMon:  explicitness versioned, refuses
   T4    Consumer: dashboard, CLI, Papyrus    clarity      user's language

   T5 HALLWAY (section 26.5) is an ACCESS layer, not a sixth tier. It owns no
   data and holds no state. It provides: signage (capabilities), depth control
   (0 verdict / 1 tier summary / 2 per-fact with provenance / 3 raw bytes),
   provenance, and polite refusal.

   THE GOVERNING RULE:
     A layer may never be made more comfortable than its cost allows.
   And the constraint on the hallway:
     IT MAY ONLY RENDER OR DESCEND. IT MAY NEVER RAISE A TIER'S COST CEILING.
   "Go deeper" means dropping to a LOWER tier, never making T0 or T2 do
   user-level work.

   THE RULE THAT MATTERS MOST: a fact with no provenance may not exist.
   Hand-authored symbol names are QUERIES, never facts.

   Read design section 26 in full before adding a new subsystem. It is where
   new code gets reviewed against.

================================================================================
 2. WHAT IS BUILT AND VERIFIED
================================================================================

 BUILD GATE -- all five stages, run from the repo root
   build_all.bat

     1/5  vprobe    runtime: Zydis, compile /W4 /WX, link, 17 self-test checks
                    (15 pass, 0 fail, 2 skip -- see section 3)
     2/5  papyrus   PipMon.psc -> PipMon.pex, real Creation Kit compiler
     3/5  launcher  pre-flight and core load path, 45 tests
     4/5  python    analysis tier, 67 tests
     5/5  rust      vlink-protocol crate, 5 tests

   A sub-stage also runs inside stage 1: the address blob is regenerated from
   the INI and verified, and a MISMATCH IS A BUILD FAILURE. That is the guard
   against a derived artefact going stale while the build reports success.

 INDEPENDENCE (verified by inspection of the built artefact)
   vprobe.dll runtime imports:  KERNEL32.dll ONLY
   Link inputs:                 kernel32, user32, Psapi, vendored Zydis
   Exports:                     PIPMON_Query / Initialize / Shutdown / LastError
                                 plus F4SE forwarders (F4SE calls US)
   No F4SE, no CommonLibF4, no extender is linked, imported, or required.

 THE 17 SELF-TEST CHECKS (vprobe)
   abi_layout             wire_roundtrip         pattern_parser
   scanner_synthetic      prologue_validation    ring_buffer
   intern_table           detour_lifecycle       resolver_state   [skips]
   dispatch               script_conformance     libbin_format
   pe_header_hash  [skips] blob_two_source       tier_ordering
   report_fits_wire       diag_carries_text

 THE PAPYRUS PIPELINE (real, gated)
   vprobe/papyrus/PipMon.psc        13 Native Global functions
   vprobe/papyrus/PipMon.ppj        FO4 PapyrusProject schema (see section 6)
   vprobe/papyrus/papyrus_flags.flg user flags; format is NON-obvious
   vprobe/papyrus/build_papyrus.bat  stage, compile, verify PEX magic
   Output: vprobe/papyrus/build/PipMon.pex, 977 bytes, magic 0xFA57C0DE

 THE ADDRESS BLOB (real, gated)
   tools/build_libbin.py    INI + game exe -> compact binary, at build time
   tools/verify_libbin.py   independent validation of the result
   vprobe/libs/fo4_1_11_240.addresses.bin   8617 records, 103,428 B
   Format (24B header): magic "PLIB" | schema | buildKey | count |
                         recordSize | reserved
   The parse happens at BUILD time. In-game it is one hash, one short scan,
   one binary search, zero per-entry allocation.

 LIVE VALIDATION (in a real game, main menu, no extenders)
   Loaded, 25 frames, totalEventsDropped = 0, monotonic sequence.
   Tier 1 resolved 5 vtable targets from the validated blob:
     BSScript__IClientVM            0x25B85C8  (independently confirmed)
     BSScript__IVMObjectBindInterface, IVMSaveLoadInterface,
     IVMDebugInterface, GameVM
   0x25B85C8 matches the value confirmed earlier by an external reader, so the
   whole chain -- blob load, PE-header image identity validated against the live
   game, C++ binary search -- is confirmed working end to end.

================================================================================
 3. THE TWO SKIPS, AND WHY THEY ARE CORRECT
================================================================================

   resolver_state    needs a live game module; reports "nothing resolved"
                     without one, which is a pass not a failure
   pe_header_hash    runs 3 refusal cases offline and skips only the POSITIVE
                     case (hashing the live Fallout4.exe). It flips to a pass
                     in-game by design, rather than faking one.

   Both were written to skip rather than to claim. Do not "fix" a skip by
   making it assert something offline that it cannot know.

================================================================================
 4. KNOWN NOT-WORKING -- READ THIS BEFORE TRUSTING A NUMBER
================================================================================

 A. TIER 2 (AOB) IS DEAD. This is the single biggest gap.
      tier2: 0 across the board. PapyrusScript::Execute returns state
      "rejected"; PapyrusThread::Execute, PapyrusVM::DebugPrint, ::PapyrusVM,
      ::GetRunningThreadCount and FormData::CellStream are "missing".

      WHY, per research (design section 26.2 and the provenance rule): the
      six symbol NAMES are almost certainly wrong, not stale. Fallout 4's VM
      is BSScript::Internal::VirtualMachine / GameVM. There is no PapyrusVM,
      PapyrusThread, PapyrusScript or FormData::CellStream in the RTTI. The
      patterns were hand-authored for functions nobody ever observed.

      CONSEQUENCE: RVA 0x1B887C0 for PapyrusScript::Execute is UNSOURCED. It
      was "confirmed" by our own tooling against our own unverified signature,
      which is circular. Treat it as a hypothesis.

      ALSO: two of the patterns share a byte-identical 12-byte prefix
      (48 8B 05 ?? ?? ?? ?? 48 85 C0 74 ?? 48 8B 40) -- the standard optional-
      singleton idiom. A scan will match hundreds of unrelated functions and
      the prologue gate will correctly reject them. No gate can save a pattern
      that generic.

      WHAT IS NEEDED: ground truth from T0/T1 (RTTI class-name extraction), not
      better hand-tuned bytes.

 B. DIAGNOSTIC CHANNEL HAD THREE INDEPENDENT BUGS, all fixed and now tested.
      All three presented identically -- a healthy pipe with no information.
      1. publish() wrote diagnostics into a buffer NOTHING READ. No PluginDiag
         had ever reached the wire.
      2. The replay resent the most RECENT diag, which at boot is a greeting,
         not the resolver report. Now re-derived on request via a provider.
      3. Every call site set textLength = 0, so a correctly-sized 1426-byte
         report declared an EMPTY body. Now derived inside publish().
      LESSON, because it recurred: a silent drop is the worst failure shape.
      Every one of these had a passing build and a healthy-looking pipe.

 C. S0 IS UNPROVEN. The viability question (section 24.7) stands: can we
      register a native and have a COMPILED .psc call it, with no F4SE? Nothing
      has attempted it. Layer B (the dispatch table) is built and tested;
      Layer A (the VM hook) does not exist.

 D. BSScript__IClientVM HAS 20 VTABLE SLOTS but the signature says 8.
      Under-counting, not breaking -- 6 of 8 validated and matched the real
      binary. Fix before Layer A.

================================================================================
 5. REFUSE, DO NOT GUESS (section 26.4)
================================================================================

   Demonstrated, deliberate refusals -- not intentions:
     blob for a different image      refused; text INI takes over
     unknown schema version          refused
     non-zero reserved header bytes  refused
     wrong record stride/truncation  refused
     hash collision (ambiguous)      treated as a miss
     wrong arity                     refused
     foreign namespace (System:...)  refused  <- enforces G7 mechanically
     declared-but-unbuilt native     refused, with a reason
     non-vtable address              refused by the gate
     thunk slot                      refused; caller tries another slot

   WHY IT IS A RULE: the failure prevented is not an error message, it is a
   detour in an unintended function, in a process whose only symptom is a
   crash. A wrong answer is worse than no answer.

================================================================================
 6. BUILDING IT -- THE FIVE THINGS THAT ARE NOT OBVIOUS
================================================================================

 THE COMPILER CANNOT PARSE SPACED PATHS. PapyrusCompiler.exe has its own
   argument splitter and breaks on spaces, and both this repo's path and
   "Program Files (x86)" contain them. build_papyrus.bat stages into a
   space-free temp dir and passes only relative arguments. The CK installs
   INTO the game folder (installdir is "Fallout 4"), not beside it.

 BASE SCRIPTS AND A FLAGS FILE ARE BOTH REQUIRED. ScriptObject is not shipped
   with the compiler; the CK installs its source under Data\Scripts\Source.
   Without a -f flags file the build fails on "Unknown user flag hidden".
   Bethesda's Institute_Papyrus_Flags.flg is referenced by their own
   ScriptCompile.bat but NOT distributed, so papyrus_flags.flg is ours.
   Its format is "Flag <Name> <index> { <types> }" with // comments. NOT one
   word per line, NOT semicolon comments; both produce walls of ANTLR errors.

 THE SCRIPT ITSELF MUST BE FLAGGED Native, not just its functions, or all
   thirteen are rejected with "cannot be defined as native because the script
   is not flagged as native".

 THE .ppj SCHEMA IS GAME-SPECIFIC. Fallout 4 uses PapyrusProject/Imports/
   Scripts per the shipped PapyrusProject.xsd. The Skyrim shape is accepted
   silently and produces NO OUTPUT -- a green invocation that compiled nothing.

 DO NOT USE ">" IN ANY echo IN A BUILD SCRIPT. cmd parses it as redirection and
   overwrites the artefact with the TEXT of the echo, after the gate has
   already printed success. This has happened twice.

================================================================================
 7. OPEN DECISIONS, IN THE ORDER THEY BLOCK THINGS
================================================================================

 1. Ground truth for Tier 2 (section 4A). Blocks Layer A. Suggested order:
      (a) check the installed AddressLib .bin for VM-internal IDs -- cheap, and
          it is the authoritative per-build answer
      (b) RTTI class-name extraction from the binary (~50 lines, no new deps)
      (c) then pefile/capstone only if (b) shows deeper analysis is needed
 2. hypothesis, scoped to binary serialization and boundary decoding, proving
    malformed input degrades gracefully. Favoured before the container work
    because the spec refactor will MOVE those tests rather than invalidate
    them.
 3. Container vs per-build blob. Many game folders are expected. A single
    PLBC container with N (buildKey, offset, count) entries would distribute
    one file; the tier rules hold either way, so this does not block.
 4. Single-source the format spec. The schema constant currently lives in
    build_libbin.py AND VersionConfig.hpp, and the layout in three places. A
    spec file plus a GENERATED C++ header removes the drift.
 5. Consolidate the three separate "is it working?" answers
    (vlink_probe --summary-only, Resolver::explain, PipMon:IsHookLive) under
    one capability at three depths. Section 26.5, recorded as NOT DONE.
 6. Build Layer A, then S0. The answer decides 19, 20, and the event models.

 LIBRARY DECISIONS (design section 25.3)
   Adopt: pefile, capstone, hypothesis, libxse/commonlibf4, commonlib-shared,
           AddressLibDecoder.
   REJECTED: phnt -- a sparse RTTI extraction, or none at all, since MSVC
             type descriptors are a pointer to a name string and the ~50-line
             scanner needs no kernel headers. The full COL/BCD/CHD chain is
             only needed for inheritance queries we do not have.
   REJECTED: sonic-rs (redundant second JSON stack), retour (we already have a
             tested detour engine; replacing it would be a regression).
   NOTE: CommonLibF4 is a DATA source only. It is not compiled, not linked,
   and cannot cause API drift. third_party/CommonLibF4 is a full .git clone
   of the STALE Ryan-rsm-McKenzie fork (pinned 1.10.163). Exactly one file is
   consumed: include/RE/VTABLE_IDs.h, to name AddressLib IDs. The live fork
   is libxse/commonlibf4.

================================================================================
 8. DOCUMENTATION -- THE DOORS
================================================================================

   The design doc is the record. This file is the resume. Everything else is a
   view onto one of them, and each is a DOOR in the hallway (section 26.5).

     DOOR         WHERE                            STATE
     -----------  -------------------------------  --------------------------
     design       PIP-MON_CONSOLIDATED.txt         CURRENT. 203 KB, 3551
                  (203,598 B, 3551 lines)          lines, 26 sections.
                                                    Sections 24/25/26 are
                                                    the recent work.
     resume       HANDOVER.md (this file)          CURRENT as of 2026-09-29.
     protocol     docs/IPC_PROTOCOL.md             ~25h old. VERIFY BEFORE
                                                    RELYING: predates the
                                                    libbin and papyrus work.
     rules        docs/ENGINEERING_RULES.md        ~25h old. Same caveat.
     anomalies    docs/ANOMALY_RULES.md            ~25h old. Same caveat.
     arch         docs/ARCHITECTURE.md             ~25h old, and now
                                                    COMPETES with section 26.
                                                    Reconcile or supersede.
     logging      tools/LOG_FORMAT.md              CURRENT.
     papyrus      vprobe/papyrus/papyrus_flags     CURRENT.
                  .flg.md
     MISSING      README.md, INSTALL.md            do not exist. No build or
                                                    install instructions for a
                                                    newcomer.

   NOT YET BUILT, and wanted in the hallway:
     - a SCHEMA DOOR: describe the address-blob format in one place, reachable
       and versioned, so the spec-sync work in open decision 4 has somewhere
       to land other than a comment in two languages.
     - a DOCS DOOR: an index that says which document answers which question,
       with its freshness, so a cold reader is directed instead of guessing.

================================================================================
 9. FILE MAP -- WHERE THINGS ARE
================================================================================

   build_all.bat                    the gate. Start here.
   PIP-MON_CONSOLIDATED.txt        the design record. 26 sections.
   HANDOVER.md                      this file.

   vprobe/include/PipmonEntry.hpp  PIP-MON's own load contract + capability bits
   vprobe/include/PapyrusApi.hpp   Layer B dispatch core (the 13 natives)
   vprobe/include/VersionConfig.hpp Tier-1 resolver, blob format contract
   vprobe/include/IPCServer.hpp    V-Link server, the hallway's wire door
   vprobe/src/PapyrusApi.cpp       the native table
   vprobe/src/VersionConfig.cpp    blob loader, peHeaderHash, lookupBin
   vprobe/src/SelfTest.cpp         the 17 checks
   vprobe/papyrus/                 the Papyrus surface + its build
   vprobe/libs/                    the address INI and derived blob

   tools/attach_inject.ps1         live injection
   tools/vlink_probe.py            live reader, now with filters (LOG_FORMAT.md)
   tools/build_libbin.py           INI + exe -> blob
   tools/verify_libbin.py          independent blob validation
   tools/rtsig.cpp                 read-only signature checker
   tools/read_vtable.py            read-only vtable validator

   overseer_cli/                   the T4 consumer: Textual dashboard
   overseer_cli/rust/vlink-protocol/   the Rust protocol crate
   launcher/                       pre-flight and process launch

================================================================================
 10. HOW THE LAST SESSION WENT, SO THE PATTERNS ARE VISIBLE
================================================================================

   Useful, because the failures were all silent:
     - a 541 KB text database was being parsed inside the game process; moving
       the parse to build time took it to 103 KB and zero in-game allocation
     - a blob loader stored its build key and never CHECKED it -- a blob for
       another patch would have fed wrong addresses into detour installation
     - six Papyrus targets were hand-authored and do not exist; the tier report
       finally made that visible
     - the diagnostic channel had three separate causes of total silence
     - a cross-thread publish() call hung the game once the window idled
   In every case the build was green and the pipe looked healthy. Treat "the
   gate passes" as necessary, never sufficient.

   What worked: verifying the TOOLS before using them on the live game caught
   a NameError and a protocol bug that would each have wasted a game session.
   Delegating a wire-format cross-check across the three language
   implementations found two real defects nobody had looked for.
