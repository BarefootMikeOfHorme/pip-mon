# SCRIPTING TASK BOARD

**Live, amendable.** Edit in place. Commit every amendment with a changelog line.
**Do not number this file** — it is the working copy. Numbered snapshots go in
`SCRIPTING-TASKBOARD.snapshot.txt` (see *Versions* at the bottom).

Machine-readable twin: [`scripting_status.json`](scripting_status.json)
Frozen original for archive/validation: [`SCRIPTING-TASKBOARD.original.txt`](SCRIPTING-TASKBOARD.original.txt)

Created 2026-10-03. Every row traces to `ai_context/spec/legacy_replacement.json`
(31 rows, `spec_lint`-clean) or to a file:line in this repo.

**Status key** — `COVERED` built+proven · `DECLARED` built, unproven · `PLANNED`
mechanism named · `DIFF` same job, different mechanism · `NOT` declined with a
reason · `REJECT` refused on measured evidence
**Host** — `none` = needs neither Fallout 4 nor the Creation Kit

---

## A. SCRIPTING — replace / enhance

| # | legacy | function it actually served | our mechanism | st | host |
|---|---|---|---|---|---|
| A1 | F4SE loader | get a native into a running game reliably, every launch | own `pipmon_preflight.exe`: `CREATE_SUSPENDED` → verify build identity → `LoadLibraryW` → resume. Host-agnostic already (zero product names in `ProcessLaunch.cpp`) | DIFF | game |
| A2 | F4SE hook install + native registration | let a native answer a Papyrus call — the capability everything else sits on | **Layer A**: one choke point on the VM's native-resolution path, reached through one *sourced* vtable slot. Register only into `PipMon:` | PLAN | game |
| A3 | AddressLib | name+build → address, so a patch doesn't silently rot | `vprobe.addresses.bin` resolved at **build** time. 8,617 records / 103,428 B, zero in-game alloc. **Build fails on a stale blob.** Reader refuses wrong image / unknown schema / non-zero reserved / bad stride | DIFF | **none** |
| A4 | po3 / Papyrus Utils | file I/O, parsing, math, arrays from script | Rust daemon + KaDag **off the game thread entirely**. Kills the defect, not just the implementation | PLAN | **none** |
| A5 | GoE Script Extender | big bundled Papyrus function library | covered by A4 | PLAN | game |
| A6 | PAP | perk/stat/quest Papyrus helpers | covered by A4 | PLAN | game |
| A7 | Buffout 4 / NSF | readable crash report — *after* the game is dead | out-of-process minidump + **proactive** rules: >500 ops/sec, >1000 handles, >50 identical errors/sec, stack over threshold. Catch it while the save is good | PLAN | **none** |
| A8 | Canary (Kinggath) | warn a save is corrupt; clean script cruft | Canary Redux: hook `SaveGame()`, read pending-event count, force drain, validate, allow write. Hold at >50 events, bounded 1500 ms | PLAN | game |
| A9 | Papyrus Compiler | `.psc` → `.pex` | Caprica + refusal-based errors. **Ends the undocumented-invocation class:** spaces-in-path breakage, missing `-f` flags file, Skyrim `.ppj` silently compiling nothing | PLAN | ck |
| A10 | MCM in-game settings | give players a settings page in-game | **none — refused on evidence.** `Terminal.psc` has 0 properties; `Holotape.psc` is 1 line; 0 of 339 vanilla fragments implement `OnMenuItemRun`; no `AddMenuItem`/`OpenMenu`/`CloseMenu` in 7,854 scripts. Menu data is CK/ESM-only | REJECT | game |

**Core dependency:** A2 blocks A4, A5, A6, A8 and A10's replacement path. A2 is
blocked on **one file** — see S1.

---

## B. TOOLING & RECORDS

| # | legacy | function | our mechanism | st | host |
|---|---|---|---|---|---|
| B1 | xEdit — read/report | what's in this plugin, what conflicts | KaDag: Rust DAG + record analyser + BA2 validator, as a library not a GUI | PLAN | **none** |
| B2 | xEdit — patch gen | emit a corrected `.esp` | **none — declined.** A wrong report you notice; a silently mis-written record corrupts a save and surfaces later, elsewhere, blamed on something else | NOT | none |
| B3 | Archive2 — read | do loose files and archives agree | `.ba2` validator. 4 prior-art sources already captured in `ba2_format/` | PLAN | **none** |
| B4 | Archive2 — write | repack archives | **none** (C17) | NOT | none |
| B5 | CKPE | stop the editor crashing / rendering slowly | in-house Win32 shim. **12 of 20 techniques portable.** First move is `DisableProcessWindowsGhosting` — one call, no hooking, no offsets | PLAN | ck |
| B6 | Vortex | which mods are installed and enabled | read-only `probe()` / `enabledSet()` / **`disagreements()`** | DIFF | **none** |
| B7 | MO2 | virtualised profiles | same three questions. **Not installed here — stated, not glossed** | DIFF | **none** |
| B8 | FOMOD | what the installer claims it did | 4th independent opinion feeding `disagreements()` | DIFF | **none** |
| B9 | Engine Fixes | patch engine bugs at runtime | **none.** A product that ships patches for a competitor's bugs has stopped being a product | NOT | none |
| B10 | Wrye SSC | auto-fix records | **none.** Skyrim product · post-install rewriter vs CK's pre-install authoring · `WryeESP.esp` is a generated master that breaks the 2,287,300-record baseline | NOT | none |
| B11 | Nexus / CurseForge | find, download, install | **none.** The measured failure is about *link state*, not downloading | NOT | none |
| B12 | Creation Kit | author content | **none — permanently.** C14: *"Attempting the second is how this project stops shipping anything at all."* Exteriors need CK-command-line precombine anyway | NOT | ck |
| B13 | G.E.C.K. | FO3/FNV worldspace editor | **none — peer tool, must never break.** Row exists mainly to keep it distinct from the GoE *Script Extender* | NOT | none |

---

## C. ADDITIONS — replace nothing

| # | addition | what it is | st | host |
|---|---|---|---|---|
| C1 | **V-Link wire** | 28-byte packed frames, memcpy on the producer. **Never parses, formats, or allocates on a game thread.** 3 compile-time asserts (C++/Python/Rust) pin the frame. Verified live: 25 frames, `totalEventsDropped=0` | **COVERED** | game |
| C2 | **One-envelope control plane** | 11 verbs, one JSON envelope, one exit vocabulary. *"SKIP is never PASS"* as code | DECL | **none** |
| C3 | **Papyrus/CE function index** | generated from the **7,854 base `.psc`**: signature per function, **observed usage counts**, compile-probed **negative table**, hard **FO4-only** assert | PLAN | **none** |
| C4 | **Capability + evidence registry** | 23 capabilities × `requires` / `exercise` / `evidence`. The only **enforced** `requires` in the repo (`taskrun.ps1:508`) | DECL | **none** |
| C5 | **In-game cartridge** | Terminal `.esp` (pre-authored) + thin Papyrus shim + **live sync to the outside client** + light mode ~1 Hz / 0% VRAM | PLAN | game |
| C6 | **Curated CK staging** | *owner idea* — add content CE-style **after** first compile instead of loading mods the hard way. 80% built (`ck_session.ps1` present, `prepare` inert; `session-profiles.json` 35+5) | PLAN | ck |
| C7 | **Compiled-env toggle** | *owner idea* — compile once, snapshot, then toggle from the terminal. **Mechanism already existed**; forwarding landed in `e103b6e` | PLAN | **none** |
| C8 | **5-rung reachability ladder** | declared → compiled → **registered → reachable → dispatchable**. Rungs 1–2 checkable **today** and are the goal-coverage gate `goal_alignment.md` says is missing. Turns S0 from binary into a coverage figure | PLAN | none |

---

## D. TASK BOARD — little tasks, each independently verifiable

### D1. Unblock Layer A (blocks the most)

| id | task | done when | verify |
|---|---|---|---|
| **S1** | obtain a BSScript class declaration in method order | slot indices derivable, not guessed | header present at `third_party/CommonLibF4/CommonLibF4/include/RE/Bethesda/BSScript.h` |
| **S2** | count rungs A/B — declared vs compiled | a number, per function | parse `PipMon.psc` natives vs `PipMon.pex` symbols |
| **S3** | declare rung C — first native handler | `PipMon.GetVersion()` returns a correct int | S0 criterion, `PIP-MON_CONSOLIDATED.txt` §24.7 |
| **S4** | declare rung D — reachable from a compiled `.psc` | S3 plus a caller | same, no F4SE present |
| **S5** | rung E — poll model drains a real event | S2 works first | §24.5, B before A. **No A before B** |
| **S6** | surface reports which resolver tier produced each probe | triage can explain itself | already partly true; expose per-verb |

### D2. Honesty — `tools/pipmon.ps1`

| id | task | done when | state |
|---|---|---|---|
| **S7** | `validate` maps `PASS`/`FAIL`/`SKIP` onto the surface vocabulary | FAIL → RED/1, not BROKEN/2 | open (F2.12) |
| **S8** | `status` checks report freshness | stale report cannot read as truth | open (F2.3) |
| **S9** | `verify` can return SKIP or BROKEN | watchdog has a real exit | open (F2.4) |
| **S10** | `link` distinguishes a thrown precondition from a wrong result | needs `linksync.ps1` to say which | open (F2.5) |
| **S11** | `caps` gains a per-verb `requires` | 19 host-free verbs declared as such | open (F4.1) |
| **S12** | `caps` carries a `provenance` block | stops breaking its own published invariant | open (F2.10) |
| **S13** | write `PIPMON_INTERFACE.md` | the docs door stops owing it | open |
| **S14** | what does `ATTENTION` mean | owner's decision | **owed** (F2.1b) |

### D3. The index (C3) — biggest host-free asset

| id | task | done when |
|---|---|---|
| **S15** | generate a machine-readable signature per function from `Data\Scripts\Source\Base` | arity, param types, return type, `Native`/`Hidden`/`Event` |
| **S16** | observed usage counts across 7,854 scripts | dead functions and legacy habits become measurements |
| **S17** | negative table by compile probe | what does *not* exist is as trusted as what does |
| **S18** | hard FO4-only assertion | Skyrim contamination impossible |
| **S19** | add query words to `ai_context/vocabulary.json` — never to code | retrievable |

### D4. Environment & records

| id | task | done when |
|---|---|---|
| **S20** | P4 gate: replace `records_created > 0` with what the stage can prove | gate can pass |
| **S21** | P4 poll budget 60 s vs **measured 102 s** | budget exceeds reality |
| **S22** | `wbCopyElementToFile` — documented, never executed | one CELL on disk |
| **S23** | `FileWriteToStream` takes **3** args; `xedit_api.json` says 2 | spec matches the binary |
| **S24** | `esp_cells.py` GRUP parser — cannot read any FO4 plugin | reads `Fallout4.esm` |
| **S25** | remove F4SE-dependent plugins from `dplugins.txt` (`XDI.esm`, `FCOM.esp`, `Cheat Terminal`) | **known active violation of the binding F4SE prohibition** |
| **S26** | gate that detects an absent runtime | the validator would otherwise report green |

### D5. Paths & hygiene

| id | task | risk if ignored |
|---|---|---|
| **S27** | `linksync.ps1` ignores `-GameDir` for the plugin list | always writes the **live** file; no test dir possible |
| **S28** | xEdit lives in `%TEMP%` | silently disappears; fails with no code change |
| **S29** | `build_papyrus.bat` hardcodes the game dir, ignoring `-GameDir` | two notions of "game dir" in one call chain |
| **S30** | `plans.schema.json` claims `requires` enforcement that `orchestrate.py` only **prints** | a documented guarantee that does not exist |
| **S31** | lint: a `compat_mapping` entry using an undeclared field | the spec layer lies and no tool notices |

### D6. Experiments — cheap, and they kill plans

| id | task | answers |
|---|---|---|
| **S32** | `read_rtti.py --exe CreationKit.exe` | does the CK have a live Papyrus VM? ~10 min |
| **S33** | `measure_vtable.py --exe CreationKit.exe` | do CK `BSScript` slot counts match the game's? |
| **S34** | `read_rtti.py --exe Fallout4.exe`, compare to `Signatures.hpp` | independent check of the 18 targets |
| **S35** | inject + pipe client on the modded install | the **5-times-reproduced, never-diagnosed** crash |

---

## E. LOCATIONS — amendable index

Where the plan, the evidence, and the diffs for each area actually live. Add a
line when you create a plan or report; do not renumber existing ones.

| area | file | what it holds |
|---|---|---|
| capability map | `ai_context/spec/legacy_replacement.json` | 31 rows; `spec_lint`-clean; 1 COVERED / 2 DECLARED / 14 PLANNED / 5 DIFF / 8 NOT / 1 REJECT |
| map schema | `ai_context/spec/schema.json` | declares `function_served`, `measured_failure`, `enhancement`, `requires_host`, `depends_on` on `compat_mapping` |
| API-level compat | `ai_context/spec/compat_f4se_map.json` | 10 rows, per-API. **0 of 10 proven.** Cited by the map, not rewritten |
| blockers | `ai_context/spec/blockers_to_environment.json` | B1–B8. **B5 is the long pole** |
| component state | `ai_context/spec/program_components.json` | 14 components; `gate_covered` is a real boolean and is `false` more often than is comfortable |
| capability IDs | `tasks/capabilities.json` | 23 caps. No `status`, no `provenance` — both owed |
| staged work | `ai_context/plans/create_environment.pyr` | P0–P5 with gates and rollbacks |
| roadmap | `tasks/roadmap/README.md` | family order and what wires to what |
| honesty defects | `tasks/roadmap/families/F2-truth-honesty/PLAN.md` | 13 defects; **4 fixed** |
| status research | `tasks/roadmap/families/F2-truth-honesty/VOCABULARY.md` | 18 vocabularies found; 5 candidate states already exist unused |
| replacement tiers | `tasks/roadmap/families/F1-replacement-map/PLAN.md` | Commitment / Named mechanism / Idea + back-door register |
| changelog | `tasks/roadmap/CHANGELOG.md` | every commit, VERIFIED / NOT VERIFIED |
| versioning rules | `tasks/roadmap/VERSIONING.md` | change classes; **revert newest-first, or expect a conflict** |
| measured xEdit API | `runs/xedit/fo4edit-4.1.5f-pascal-api.md` | what works, what doesn't exist |
| FO4 Papyrus rules | `ai_context/papyrus_syntax_rules.md` | compile-probed. Negative table is the valuable half |
| Papyrus corpus | `ai_context/engine/papyrus_surface/part01-06.md` | 7.5 MB generated from the 7,854 base scripts |
| binding prohibition | `ai_context/f4se_prohibition.md` | `ACTIVE — BINDING CONSTRAINT`. **S25 violates it today** |
| CKPE portability | `ai_context/systems/ckpe/ckpe-insights.md` | 12 yes / 5 maybe / 3 no |
| product shape | `PIP-MON_CONSOLIDATED.txt` | the original spec, §24.7 holds the S0 criterion |

---

## F. VERSIONS

| file | role |
|---|---|
| `SCRIPTING-TASKBOARD.md` | **this file — the live working copy.** Amend in place |
| `SCRIPTING-TASKBOARD.original.txt` | **ORIGINAL — DO NOT DELETE. Archive and validation only.** Never amended |
| `SCRIPTING-TASKBOARD.snapshot.txt` | numbered snapshots, `<date>-<n>.snapshot.txt`. Created when a board-wide rewrite happens |
| `scripting_status.json` | machine-readable twin. Lints against nothing; read it, do not trust it blindly |

**Validation rule:** the original and this file are meant to **differ**. If they
ever match, a board-wide rewrite happened without a snapshot, and the history of
what changed and why is gone. Diff them:

```
git diff --no-index scripting/SCRIPTING-TASKBOARD.original.txt scripting/SCRIPTING-TASKBOARD.md
```

**Three closed lanes, recorded so they are not re-proposed a third time:** the
Terminal-as-MCM replacement, the MCM config translation, and the probe serving
both hosts without measurement. Evidence in `tasks/roadmap/CHANGELOG.md` C1–C4.
