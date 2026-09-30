================================================================================
 PIP-MON SESSION HANDOVER
  Written 2026-09-29. Supersedes the pre-scripting snapshot of the same name.
  Amended 2026-09-29 (later the same day): Tier 2 ground truth resolved, two
  claims in section 4 corrected, new gate step. See section 13.
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
    Expected: vprobe 15 pass / 0 fail / 2 skip, launcher 45, python 106, rust 5,
    "every declared vtable matches the binary" (18 targets),
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
     4/5  python    analysis tier + environment gate, 106 tests
     5/5  rust      vlink-protocol crate, 5 tests

   Two sub-stages also run inside stage 1, and both fail the build rather than
   warning:

     - the address blob is regenerated from the INI and verified, and a
       MISMATCH IS A BUILD FAILURE. That is the guard against a derived
       artefact going stale while the build reports success.
     - every vtable slot count declared in Signatures.hpp is measured against
       the real Fallout4.exe and must agree. Added 2026-09-29; see section 13.
       Expect 18 "[OK]" lines and "every declared vtable matches the binary".

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
   vprobe/libs/fo4_1_11_240.addresses.txt   TRACKED: the per-build database
   vprobe/libs/fo4_1_11_240.addresses.bin   NOT tracked: derived + machine-
                                            specific (see section 10)
   8617 records, 103,428 bytes.

   FORMAT -- 24 B header, then N x 12 B records, all little-endian:
     0   4   magic       "PLIB"
     4   4   schema      layout version; the reader REFUSES an unknown one
     8   4   buildKey    FNV-1a over the game PE HEADERS
     12  4   recordCount
     16  4   recordSize  12 in v1
     20  4   reserved    must be 0, and is validated
     record: nameHash(4) rva(4) classId(1) slot(1) flags(2)
   The parse happens at BUILD time. In-game it is one PE-header hash, one short
   scan, one binary search, zero per-entry allocation.

   WHY THE HEADER IS SHAPED THAT WAY:
     - schema_version exists because a same-size layout change would otherwise
       be read silently and yield plausible, wrong addresses. An earlier
       version had no version field at all, only a spare `reserved`.
     - buildKey is a hash of the PE HEADERS, not Bethesda's build-key STRING.
       A string would have forced a PE parser into the in-process tier, which
       this project deliberately does not have there. The header bytes are
       mapped 1:1 file-to-memory, so both sides agree with no parser on either
       end. It stops before the optional header because that region holds the
       ASLR-dependent image base.
     - `reserved` is validated rather than ignored, so a v2 that reuses those
       bytes cannot be misread as v1.

 VERSION CONTROL AND LICENCE: see section 10.

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

  A. TIER 2 (AOB) IS DEAD -- RESOLVED 2026-09-29. See section 13. Short
       version: the six symbol NAMES were wrong, confirmed by reading the
       game's own RTTI, and the real classes are now in the target table as
       18 sourced vtable targets. The dead AOB patterns are removed. NO SLOT
       IS HOOKED YET -- see section 13 for the one blocker.


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

  D. BSScript__IClientVM SLOT COUNT -- RESOLVED 2026-09-29, and this section
       was WRONG. See section 13. IClientVM has THREE vtable slots, not 8 and
       not 20. Every count in the signature table is now measured against the
       real binary and the build gate fails on any disagreement. The "20" came
       from counting through the following tables; the entries after a table's
       last method are the NEXT class's RTTI locator, not methods.


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

 THE BUILD PRODUCES A NAME THE RUNTIME DOES NOT LOOK FOR.
   The repository keeps one database PER GAME BUILD, named with the build
   version (fo4_1_11_240.addresses.txt). The runtime has a FIXED contract name
   (vprobe.addresses.txt / .bin) and will not enumerate a directory, because T2
   is not allowed to do work at runtime.
   Those two facts have to meet, and they meet at BUILD time -- T1 may be slow,
   T2 may not. build_libbin.bat now selects the per-build file and stages it
   under the runtime's name into vprobe/libs/deploy/, then verifies the contract
   name exists.

   This was a real, SILENT defect, found only by a documentation audit. The
   build produced one filename and the runtime searched for another, so the
   repository's own database could never be loaded -- and because the blob path
   is DERIVED from the INI path, a miss took the binary database down with it.
   It appeared to work only because a manual staging step happened to copy the
   file under the contract name. Nothing in the gate compared the two, so a
   green build shipped a database the runtime could not find. That presents as
   "text form unavailable", which is the silent-degradation class this project
   treats as its worst outcome.

 DO NOT USE ">" IN ANY echo IN A BUILD SCRIPT. cmd parses it as redirection and
   overwrites the artefact with the TEXT of the echo, after the gate has
   already printed success. This has happened twice.

================================================================================
 7. OPEN DECISIONS, IN THE ORDER THEY BLOCK THINGS
================================================================================

  1. ~~Ground truth for Tier 2.~~ **DONE 2026-09-29.** See section 13. The
     RTTI scan found the real classes and they are in the target table. What
     remains is narrower and is listed as its own item below.
  1a. **Slot indices for the 18 vtable targets.** This is the new critical
     path, and it is one specific thing: obtain a BSScript class declaration
     that lists methods in declaration order, and the indices follow
     mechanically. The pinned CommonLibF4 clone in third_party/ (Ryan-rsm-
     McKenzie, 1.10.163) carries vtable ADDRESSES but NO BSScript headers at
     all; the live fork is libxse/commonlibf4. Until a declaration exists,
     nothing is hooked -- a guessed index is a detour into an unrelated
     function, which is the failure this whole tier model prevents.

 2. hypothesis, scoped to binary serialization and boundary decoding, proving
    malformed input degrades gracefully. Favoured before the container work
    because the spec refactor will MOVE those tests rather than invalidate
    them.
 3. Container vs per-build blob. Many game folders are expected. A single
    PLBC container with N (buildKey, offset, count) entries would distribute
    one file; the tier rules hold either way, so this does not block.
 4. Single-source the format spec. STILL TRUE and not yet done. The schema
    constant lives in build_libbin.py AND VersionConfig.hpp; the layout in
    three places. A spec file plus a GENERATED C++ header removes the drift,
    and section 11 says where it should land (the SCHEMA DOOR).
 5. Consolidate the three separate "is it working?" answers
    (vlink_probe --summary-only, Resolver::explain, PipMon:IsHookLive) under
    one capability at three depths. Section 26.5, recorded as NOT DONE.
 6. Build Layer A, then S0. The answer decides 19, 20, and the event models.
 7. Fix the remaining documentation: ENGINEERING_RULES.md (stale, and its
    PITFALL 1 is uniquely valuable), ARCHITECTURE.md (superseded, but holds the
    thread model and the V-Probe/V-Link prefix constraint). Full per-file
    detail in section 11.
 8. Add an installer. Staging is a manual copy, which has now caused two
    separate problems and is the most user-visible gap.

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
     resume       HANDOVER.md (this file)          CURRENT as of 2026-09-29.
     readme       README.md                        CURRENT. Created late in
                                                    the session; states plainly
                                                    what WORKS and what does
                                                    NOT, because a README that
                                                    oversells is the first thing
                                                    a new reader trips over.
     licence      LICENSE                          CURRENT. Personal Use
                                                    Licence, not open source.
     protocol     docs/IPC_PROTOCOL.md             PARTLY FIXED. Sizes and
                                                    field orders corrected from
                                                    the static_asserts; still
                                                    documents a priority-drop
                                                    scheme, a control channel
                                                    and a config file that do
                                                    not exist. See section 11.
     rules        docs/ENGINEERING_RULES.md        STALE, not started. Its
                                                    PITFALL 1 is uniquely
                                                    valuable -- preserve it.
     anomalies    docs/ANOMALY_RULES.md            CURRENT. Verified line by
                                                    line against the code.
                                                    Nothing to do.
     arch         docs/ARCHITECTURE.md             SUPERSEDED by section 26,
                                                    but uniquely holds the
                                                    thread model and the
                                                    V-Probe/V-Link prefix
                                                    constraint. Do not delete.
     logging      tools/LOG_FORMAT.md              CURRENT.
     papyrus      vprobe/papyrus/papyrus_flags     CURRENT.
                  .flg.md

   The audit method is worth keeping: an agent cross-checked every doc claim
   against the actual code and found that the wire-protocol doc had three of
   ten payload sizes wrong. Documentation drift in this project is not
   cosmetic -- it had a reader-facing document disagreeing with three
   separately-asserted implementations, and the stale Heartbeat size was a bug
   the code comments said was already fixed.

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
   PIP-MON_CONSOLIDATED.txt         the design record. 26 sections.
   HANDOVER.md                      this file.
   README.md                        what it is, how to build, what WORKS and
                                    what does NOT. Honest by design.
   LICENSE                          Personal Use Licence. NOT open source:
                                    use/mod/share the binary, never publish
                                    the source, never sell, never claim it.
   .gitignore                       written before the first commit on
                                    purpose -- see section 11.

    vprobe/            in-process runtime (C++, x64)
      include/           PipmonEntry (load contract + capability bits),
                         PapyrusApi (Layer B dispatch), VersionConfig (T1/T2
                         resolver), Signatures (the target table: what is
                         resolved and how it is justified), IPCServer (the
                         wire door)
      src/               main, PapyrusApi, VersionConfig, IPCServer, SelfTest,
                         PapyrusHooks, Detour, DynamicScanner, ReadySignal
      papyrus/           the PipMon: surface: .psc, .ppj, flags, build
      libs/              per-build address database (.txt, tracked) and the
                         derived binary blob (.bin, NOT tracked)
      build_libbin.bat   INI -> blob, plus the stale-blob guard
      build_vtables.bat  declared vtable counts vs. the real binary
      tests/             test_harness.exe drives the in-DLL self-test

     tools/             read-only inspectors and build-time generators
       attach_inject.ps1   live injection
       testenv.ps1         THE TEST ENVIRONMENT. preflight / stage / run / tail.
                          Per-run dir under runs\, attaches, tails both file
                          channels live, writes run.json, classifies the exit.
                          Never opens the V-Link pipe; never kills the game.
       vlink_probe.py      live reader, with filters (see LOG_FORMAT.md)
      build_libbin.py     INI + game exe -> binary blob (build time)
      verify_libbin.py    independent blob validation
      read_addresslib.py  AddressLib .bin -> the per-build INI
      read_rtti.py        the game's own RTTI class names out of Fallout4.exe
      measure_vtable.py   vtable identity + extent, OFFLINE, gated
      read_vtable.py      vtable check against a LIVE process (superseded for
                          gating by measure_vtable.py; still useful in-game)
      rtsig.cpp           read-only signature checker

    overseer_cli/      the T4 consumer: Textual dashboard
      src/overseer_cli/envgate.py   THE ENVIRONMENT GATE. One protocol, three
                          Creation Engine hosts (game / GECK / offline). Every
                          check declares the host it needs; a check that could
                          not run is SKIP with a reason and never a pass.
                          `overseer-cli --verify --depth 2`
      rust/vlink-protocol/   the Rust protocol crate
   launcher/          pre-flight and process launch (45 tests)
   overseer_event_bridge/   in-game bridge: console commands + a .psc that
                           calls the PipMon: surface
   pip_mon_testlab/   three .psc probes (leak / loop / terminal) for driving
                      the surface from inside a save
   docs/              IPC_PROTOCOL, ENGINEERING_RULES, ANOMALY_RULES,
                      ARCHITECTURE -- see section 8, three of four need work
   stage/             deployment staging. NOT tracked. Not source.
   third_party/       vendored. NOT tracked. Not compiled.
   inspiration archive/  the original idea files. NOT design decisions; the
                      consolidated doc superseded them.

================================================================================
 10. VERSION CONTROL AND LICENCE -- THE GROUND RULES
================================================================================

   THERE IS NOW A LOCAL GIT REPO. There was none until the end of the previous
   session, which means that work has no history. That cannot be recovered; it
   can only not be repeated.

     commit 2d5f832  "PIP-MON: initial commit"
     115 files, branch master, NO REMOTE, working tree clean.

   NO REMOTE IS CONFIGURED, deliberately. This is a local repository. Do not
   add one and do not push without being asked (G10).

   WHAT IS DELIBERATELY NOT TRACKED, and why each one matters:
     third_party/            a full .git clone of a THIRD-PARTY repo (19.5 MB).
                             Flattening it would mix their history into ours.
                             It is a DATA reference; nothing compiles it.
     vprobe/libs/*.bin      derived, regenerated and byte-compared by the
                             build, AND machine-specific: its header carries a
                             hash of the local Fallout4.exe, so a committed
                             copy would be wrong on every other machine.
     stage/                 a deployment staging area, not source.
     *.pex *.dll *.exe      build outputs. The build regenerates and verifies
                             each one.
     vprobe/libs/*.txt      IS TRACKED. That is the per-build database
                             everything derives from, not an artefact.

   THE .gitignore WAS WRITTEN BEFORE THE FIRST COMMIT, on purpose. The rule it
   encodes: a build gate that regenerates a derived artefact must never be able
   to commit that artefact by accident, because then a stale copy gets reviewed
   and merged as though it were source. That is not hypothetical -- it is the
   same class of bug as the stale-blob guard the build now enforces.

   LICENSE: the project Personal Use Licence in LICENSE. It is NOT open source
   and NOT OSI-licensed. The short form, which README repeats:
     ALLOWED    use it, mod with it, modify it for yourself, read the source,
                share the COMPILED binary, contribute changes back
     NOT ALLOWED publish the source anywhere, redistribute source (including
                inside a mod or a tutorial zip), sell or licence it, use it
                commercially, strip the copyright, or claim authorship
   One judgement call was made and is open to reversal: clause 1e ALLOWS private
   sharing of the compiled binary. Tighten it to single-machine if preferred.

   Nothing proprietary is in the tree: no game asset, no extender binary, no
   Creation Kit file. Verified by extension sweep at commit time (zero .dll,
   .exe, .pex, .bin).

   FROM NOW ON: commit at meaningful boundaries, not every edit. A commit
   message should state what is VERIFIED and what is NOT -- the initial commit
   does this, and that is the standard to keep.

================================================================================
 11. THE DOCS DOORS -- AND AN AUDIT THAT HAS NOT BEEN ACTED ON
================================================================================

   The hallway (26.5) wants two doors. Neither is built yet:
     - a SCHEMA DOOR: the address-blob format described in ONE place,
       versioned, instead of a spec in build_libbin.py, a LAYOUT table in
       verify_libbin.py, and constants in VersionConfig.hpp. That is the drift
       risk in section 7 item 4.
     - a DOCS DOOR: an index saying which document answers which question and
       how fresh it is, so a cold reader is directed instead of guessing.

   A full audit of docs\ was performed at the end of the previous session. Only
   part of it has been acted on. THE REST IS OUTSTANDING WORK:

     FILE                       VERDICT      DONE?
     -------------------------  -----------  -------------------------------
     docs\IPC_PROTOCOL.md       WRONG        PARTLY. Payload sizes corrected
                                                (Heartbeat 44->40, ThreadState
                                                20->21, VmTick 28->30) and two
                                                field ORDERS corrected from the
                                                static_asserts. STILL WRONG:
                                                  - claims priority-aware frame
                                                    dropping exists; it does
                                                    not, and never has
                                                  - documents a control channel
                                                    (soft_cancel, force_kill,
                                                    dump_stack, set_sampling)
                                                    with no sender and no
                                                    receiver
                                                  - documents a
                                                    vprobe_settings.jsonc
                                                    config file; the probe has
                                                    NO config reader at all
                                                  - omits the address blob and
                                                    the Papyrus surface
                                                entirely
     docs\ENGINEERING_RULES.md  STALE        NOT STARTED. Rule 2 says
                                                "two-tier" (now four), gives a
                                                demoted INI path as the primary
                                                location, and Rule 3 states as
                                                implemented a control-channel
                                                queue that does not exist. Its
                                                PITFALL 1 (the silent VM freeze
                                                with no crash) is the single most
                                                valuable thing in docs/ and is
                                                covered by NO other document.
                                                Preserve it.
     docs\ANOMALY_RULES.md      CURRENT      Nothing to do. Verified line by
                                                line against detector.py and
                                                rules_config.py: every threshold,
                                                formula, severity and key
                                                matches.
     docs\ARCHITECTURE.md       SUPERSEDED   NOT STARTED. It presents a
                                                COMPETING 5-row component table
                                                with no cost-ceiling column, so
                                                a reader follows it instead of
                                                section 26. It also cites a
                                                README.md that did not exist
                                                until the same session. DO NOT
                                                DELETE IT -- it uniquely holds:
                                                  the THREAD MODEL and its
                                                  ownership rule (section 26
                                                  does not cover which thread
                                                  does what)
                                                  degradation-as-a-state: "a
                                                  disabled hook means this panel
                                                  shows less; a silent failure
                                                  means this panel shows nothing
                                                  and you think the game is
                                                  healthy"
                                                  the V-Probe/V-Link shared
                                                  PREFIX rationale -- a
                                                  wire-compatibility constraint
                                                  on a deployed public name.
                                                  HIGHEST RISK ITEM TO LOSE.
                                                  trademark discipline: no
                                                  official logos, no "official
                                                  tool" language
                                                Rewrite it as a pointer plus
                                                those sections.

===============================================================================
 12. HOW THE LAST SESSION WENT, SO THE PATTERNS ARE VISIBLE
===============================================================================

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


================================================================================
 13. SESSION 2026-09-29 -- TIER 2 GROUND TRUTH, AND TWO CORRECTIONS
===============================================================================

  Full reasoning is in the design doc, section 27. This is the resume view.

  THE GATE CHECKS ONE MORE THING NOW
    Still five stages -- the count in section 2 is unchanged, so a self-test
    count that shifts is a different problem. What changed is that stage 1
    gained a second sub-step between the address blob and Papyrus:

      --- vtable targets (declared vs. the real binary) ---

    It runs tools/measure_vtable.py, which reads the real vtables out of
    Fallout4.exe and fails the build if any slot count in Signatures.hpp
    disagrees. It skips cleanly with no game installed, exactly like the
    address blob. Expected output is now 18 "[OK]" lines and
    "every declared vtable matches the binary".

    If your run does not show that line, the gate is not what this file
    describes.

  THE TWO TOOLS
    tools/read_rtti.py     reads the game's own mangled type names. 12,262 of
                           them, all in .data, zero rejected. Was written in a
                           previous session and never committed -- it is the
                           reason the "wrong names" conclusion could be
                           upgraded from an inference to a measurement.
    tools/measure_vtable.py measures vtable extents OFFLINE. This exists
                           because tools/read_vtable.py needs a live process,
                           and a design gate that needs the game running is a
                           gate nobody runs. Imports the PE parser and RTTI
                           walk from read_rtti.py rather than duplicating
                           them.

  THE FINDING, IN ONE LINE
    Fallout 4 has no class named PapyrusVM, PapyrusThread or PapyrusScript.
    The VM is BSScript::Internal::VirtualMachine. The three "FormData" hits
    are SavedFormData, SavedFormData inside a template, and BGSLoadFormData --
    none of them a class called FormData. So the six dead AOB patterns were
    written for classes that do not exist, and no byte tuning could have saved
    them.

  WHAT CHANGED
    - Signatures.hpp: 5 targets -> 18, all vtable, all with RTTI-confirmed
      identity and MEASURED slot counts. The six dead AOB patterns are gone.
    - PapyrusHooks.cpp: the four detours on dead names are DELETED, and the
      install log now states the truth instead of logging "degraded" on every
      boot.
    - build_all.bat / vprobe/build_vtables.bat: the new gate step.
    - The runtime target table is 18 entries, so the self-test report grew
      from 1376B to 1442B. Still 70% of the wire cap, and report_fits_wire
      asserts it.

  THE BOUNDARY RULE -- the one thing worth remembering
    MSVC lays x64 vtables out back to back with no sentinel:

        [COL for N][method][method]...[COL for N+1][method]...

    The 8 bytes after the last method are the NEXT class's
    CompleteObjectLocator and they look exactly like a slot. Counting until
    pointers stop pointing at code runs straight through into the neighbours.
    A slot ends the table only if it is a locator: first DWORD 1, AND its
    type-descriptor RVA resolves to a name starting ".?A". Two conditions, so
    arbitrary data does not pass. 11 of 18 tables end that way; 7 end on a
    pointer outside the image, which is a debug string sitting right after.

  MEASURED SLOT COUNTS, for anyone who needs them without running the tool
    BSScript__Internal__VirtualMachine   62     BSScript__IFunction       21
    BSScript__IVirtualMachine            62     BSScript__IStore         12
    BSScript__IVMSaveLoadInterface       26     BSScript__IVMObjectBind.. 11
    BSScript__IVMDebugInterface           6     BSScript__IProfilePolicy   5
    BSScript__IMemoryPagePolicy          6     BSScript__CompiledScript..  4
    BSScript__IClientVM                   3     BSScript__ILoader          4
    GameVM                                3     BSScript__IObjectProcessor 4
    BSScript__Internal__ScriptFunction  21     BSScript__ErrorLogger      3
    BSScript__Internal__CodeTasklet      2     BSScript__IComplexType     2

  A WARNING ABOUT THE VALIDATOR, learned the hard way
    Many slots in these tables resolve to the SAME address (0x022C46A2
    throughout). That is MSVC identical COMDAT folding, and it means the
    "majority of slots point into executable code" rule is a weak signal --
    the merged stub satisfies it trivially. The boundary is what carries the
    weight, not the count.

  STILL NOT DONE
    No vtable slot is hooked. See open decision 1a: one specific input is
    missing (a BSScript class declaration) and guessing around it is the one
    thing this project must not do. Layer A and S0 are both still ahead, and
    S0 still decides design decisions 19 and 20.
===============================================================================
