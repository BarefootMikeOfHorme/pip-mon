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
                        resolver), IPCServer (the wire door)
     src/               main, PapyrusApi, VersionConfig, IPCServer, SelfTest
     papyrus/           the PipMon: surface: .psc, .ppj, flags, build
     libs/              per-build address database (.txt, tracked) and the
                        derived binary blob (.bin, NOT tracked)
     tests/             test_harness.exe drives the in-DLL self-test

   tools/             read-only inspectors and build-time generators
     attach_inject.ps1   live injection
     vlink_probe.py      live reader, with filters (see LOG_FORMAT.md)
     build_libbin.py     INI + game exe -> binary blob (build time)
     verify_libbin.py    independent blob validation
     read_addresslib.py  AddressLib .bin -> the per-build INI
     rtsig.cpp           read-only signature checker
     read_vtable.py      read-only vtable validator

   overseer_cli/      the T4 consumer: Textual dashboard
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

================================================================================
 12. HOW THE LAST SESSION WENT, SO THE PATTERNS ARE VISIBLE
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
