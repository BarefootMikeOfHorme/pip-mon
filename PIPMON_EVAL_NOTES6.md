# PIP-MON Evaluation Notes (single running document)

Repo: https://github.com/BarefootMikeOfHorme/pip-mon (main @ e05dd7a RESUME.md, 23 commits, 371 files, cloned shallow 2026-10-01; earlier notes were against da52ad4)
Owner framing: "A script management system first; the rest is bells and whistles."
Revise THIS file each session. Do not create new versions.

## 0. STATE CARD (read this first; everything below is detail)

**Subject:** github.com/BarefootMikeOfHorme/pip-mon, evaluated at main e05dd7a (371 files). Owner: "script management system first; the rest is bells and whistles."
**Owner facts:** repo is public only for this eval; licence undecided (GitHub would not take PolyForm); some gate blockers fixed locally but NOT pushed, so every "gate red" below is "as of GitHub main".
**Progress:** Pass 1 done (skim). Pass U (usability, Section 8) done. CLI design (Section 9) done. Product shape (Section 10) done. Pass 2 partial (design doc s1, s6, s14, s18). Pass 3 partial (linksync, build_papyrus.bat, validate_plugin, pipmon validate, orchestrate.py, create_environment plan). Passes 4-6 not started. Nothing was executed; all findings are from reading.
**Thesis (what I believe so far):** most of the real, gated investment IS script management (tools/ ~13k lines vs native runtime ~7k). `pipmon.ps1` is already a good product surface. The native runtime (Layer A hook) is unproven and is a separate, larger track. The best unbuilt, best-justified feature is the provider registry (design s18).
**Top 6 findings by impact:**
1. B1: the Papyrus build is a hard-coded list of 6 own scripts, not a general script manager (the core gap).
2. X1: no single config; FO4/plugins.txt/xEdit/stage paths hard-coded and divergent across .bat/.ps1/.py.
3. L1/L3/L5: linksync round-trips through ASCII, has a read-modify-write race with Vortex/CK, and never checks masters.
4. V1/V2/V3: `pipmon validate` can report a stale verdict, cannot run async, and exit codes mean different things in two tools.
5. O1/O3: orchestrator splits commands on spaces (paths contain spaces); P4 has the wall gate AND a 60 s poll budget vs a measured 102 s run (second part unconfirmed).
6. D-series: documentation drift (README stub, stale handover/dashboard/comments, licence unrecorded in the design doc).
**Usability headline (Section 8):** the pictured UI is a VS Code-style workbench over the existing pipmon envelopes; in-game, the FO4-native menu is a Terminal-type holotape (no F4SE, no Scaleform), which answers the spec's open "in-game menu MUST BE BUILT"; one-way cartridges are testable before Layer A, two-way are not; do not build a general mod manager (ladder in 8.8); the missing piece for semi-automated repair is a closed finding->remedy->verify loop (8.7).
**CLI headline (Section 9):** make `pipmon` one noun-verb surface (existing verbs map 1:1), add envelope v2 (run_id, findings, remedies, next), one exit table, a `doctor` + `fix` closed loop, and drive the VS-style workbench from `pipmon caps --json` so UI and CLI cannot drift. First slice: caps + doctor + link plan/apply + fix + workbench Problems panel (9.13). Open owner decision: Python front vs keep PowerShell (9.11).
**Product-shape headline (Section 10):** daemon (`pipmon serve`, always-on, owns V-Link, recorder, guardrails) + clients (custom lightweight workbench, CLI, AI adapter, cartridges); two probe profiles LIGHT/HEAVY with hot switching when hooks are pre-installed (restart only if a hook is missing); three launch modes Watch / Debug-live / Tandem (`pipmon open <project>`); protocol profiles OBSERVE/HUMAN/ASSIST/MACHINE as guardrails; the launcher ALREADY does F4SE's suspended-start-and-inject, so a hard pre-game HOLD until the daemon sets a `synced` event is buildable now (10.12), while a hard main-menu gate still needs Layer A; the undiagnosed injection crash on the owner's modded install (PS11) blocks all modes; boot art licensing needs a check before copying anything; virtual desktop is best-effort only.
**Corrections made to my own earlier claims:** P3 (validator blind to exception log) is already fixed on main; D1 (public push) downgraded to stale handover text.
**Not read yet (do not assume):** design doc s2-5, s7-13, s15-17, s19-27; taskrun.ps1; artifact_gate.py; gen_papyrus_ref.py; ck_session.ps1; run_gen.ps1; all C++ (vprobe, launcher), overseer_cli, Rust crate; ai_context (spec, RAG, vendored third-party licences); tests; remaining inspiration archive files; docs/*; tasks/*.json.

### 0b. Findings register (ID | severity H/M/L | one line | status as of main e05dd7a)

| ID | Sev | Finding | Status |
|---|---|---|---|
| A1 | M | Repo has no stated spine (script mgmt vs F4SE replacement) | OPEN (owner decision) |
| A2 | H | Core thesis unproven: no Layer A hook, S0 never attempted | OPEN (separate track) |
| D1 | L | Handover says local/master/no remote/Personal Use licence | DOWNGRADED: stale text |
| D2 | M | Handover calls README current; remote README is a 2-line stub (local README differs) | OPEN |
| D3 | M | LICENSE header text contradicts PolyForm body; NOASSERTION on GitHub | OPEN (owner choosing licence) |
| D4 | L | ai_state_dashboard.md committed, stale, leaks a local path | OPEN |
| D5 | M | Documented xEdit abort cause (GetPluginName) contradicted by logs | OPEN, verify |
| D6 | L | Handover test counts unverifiable without game/CK | UNVERIFIABLE here |
| P1 | H | Gates red: door_lint, rag_selftest, P4 wall; bare orchestrate.py exits 2 | PARTIAL: owner says some fixed locally; re-verify after push |
| P2 | M | Validator never run against committed .pas | RE-VERIFY after push |
| P3 | - | Validator blind to xFOEdit64Exception.log | CORRECTED: already reads it on main |
| P4 | M | Orchestrator: no checkpoint/resume; gate output discarded (FIX-BACKLOG E1/E2) | OPEN; E2 may be fixed (transcript now captures output) |
| P5 | L | Backup file committed (rag_query.py.bak-unicodefix); backups no longer ignored | OPEN |
| P6 | M | xEdit loads full active load order (~2m15s) for one plugin | OPEN (design choice) |
| P7 | M | Windows-only, hard-coded paths, no CI, no .github | OPEN |
| R1 | H | Vendored third-party code in repo; licences unaudited | OPEN (Pass 5) |
| R2 | M | Injection plus detour into a shipping game | ACCEPTED (mitigated by refuse rules) |
| R3 | M | 213 KB design doc, 96 md files, blank README | OPEN |
| DD1 | - | "Script management" is the END state (phase D) | INFORMATION |
| DD2 | L | Design doc numbering broken (1-14, 18-25, 24.8, 15-17) | OPEN |
| DD3 | M | s6.2 two-pane CLI and s18 provider registry unbuilt | OPEN (roadmap 6) |
| DD4 | L | s6.4 log object model, s6.7 dedup: check in overseer_cli | TODO Pass 4 |
| DD5 | - | Inspiration archive shows self-correction (CommonLib/CBOR dropped) | INFORMATION |
| L1 | H | linksync writes ASCII: non-ASCII plugin names become ? | OPEN |
| L2 | M | apply has no dry-run/diff despite header promise | OPEN |
| L3 | H | read-modify-write race with Vortex/CK | OPEN |
| L4 | L | second-granularity snapshot names with -Force; no retention | OPEN |
| L5 | H | No master check on enable/order | OPEN |
| L6 | M | Hard-coded GameDir and plugins.txt location | OPEN (see X1) |
| B1 | H | Build covers 6 fixed scripts; not a general script manager | OPEN (core gap) |
| B2 | L | Header note says -i=base and %STAGE%\base; code does neither | OPEN |
| B3 | M | Shared persistent stage in %TEMP%; concurrent builds race | OPEN |
| B4 | M | Hard-coded FO4 path | OPEN (see X1) |
| B5 | L | Fragile .bat quoting; thin wrapper over a testable driver advised | OPEN |
| B6 | - | Duplicate exit /b 0 | TRIVIAL |
| V1 | H | pipmon validate can return a previous run's report (no run-id) | OPEN, unverified by execution |
| V2 | M | pipmon validate cannot -Async/-Collect | OPEN |
| V3 | M | Exit code 4 means RUNNING vs usage across tools | OPEN |
| V4 | L | XEditDir default under %LOCALAPPDATA%\Temp\opencode | OPEN |
| V5 | L | 35-plugin vs 61-plugin load order inconsistent in docs | OPEN, reconcile |
| O1 | H | cmd.split(): arguments cannot contain spaces | OPEN |
| O2 | M | Allowlist hard-coded in orchestrate.py; 17 tools unregistered per door_lint | OPEN |
| O3 | H | P4: wall gate plus 60 s poll budget vs ~102 s generator | OPEN (budget part unconfirmed) |
| O4 | L | Essay-length prose inside plan JSON | OPEN |
| O5 | L | .pyr is JSON with a custom extension | OPEN |
| O6 | L | -ExecutionPolicy Bypass everywhere | NOTE (personal tool) |
| O7 | L | Fixed .tmp name in _atomic_write | OPEN |
| U1 | H | Spec decision_owed (in-game surface) answered by owner: build cartridges; spec correction owed (Terminal data-layer menus) | OPEN (8.3) |
| U2 | M | Concept images are an IDE shell only; no image for in-game/cartridge UI | INFORMATION (8.1) |
| U3 | M | V-Link single handle; multi-client hub from archive not built | OPEN (8.9) |
| U4 | M | Two-way cartridge needs Layer A; interim one-way via user log | OPEN (8.6) |
| U6 | L | Archive says Rust/Ratatui, code is Python/Textual | OPEN |
| U7 | M | No closed loop finding -> remedy -> authority -> verify -> rollback | OPEN (8.7) |
| VL1 | M | IPCServer first CreateNamedPipeW passes 255 in mode flags (suspected, unverified) | OPEN, verify on Windows |
| D3b | M | overseer_cli pyproject says MIT; repo is PolyForm | OPEN |
| P5b | L | Duplicate, unnamed images in archive | OPEN |
| C1 | H | Five-plus entry points, three languages, two flag conventions; only pipmon.ps1 honours the envelope | OPEN (9.1) |
| C2 | M | `caps` has no appliesTo/risk/authority, so a UI cannot be generated from it | OPEN (9.8) |
| C3 | M | No `doctor`, no `fix` verbs; no findings/remedies in the envelope | OPEN (9.6, 9.7) |
| C4 | M | No streaming contract for `watch`; single-subscriber V-Link | OPEN (9.9, U3) |
| C5 | M | Surface language decision (Python front vs keep PowerShell) not made | OPEN (owner, 9.11) |
| PS11 | H | Injection crash reproduced 5x on modded install, undiagnosed; blocks every launch mode | OPEN (measure on clean install) |
| PS12 | M | Launcher resumes right after inject; no HOLD/synced event or --profile flag | OPEN (10.12) |
| PS13 | M | No path for platform-provider starts to get the probe (no launcher in the chain) | OPEN (owner, 10.12) |
| PS14 | L | testfacility/ENV-SETUP.md still launches via f4se_loader.exe | OPEN |
| PS1 | H | Three launch modes and two probe profiles not modelled in code or spec; V-Link has no profile id/ack | OPEN (10.3, 10.4) |
| PS2 | M | Hard MAIN-MENU gate needs Layer A; hard PRE-GAME gate is buildable now at the suspended launch (corrected, 10.12) | OPEN (10.5, 10.12) |
| PS3 | H | No daemon/UI split; overseer_cli is both; blocks minimised monitoring and multi-client | OPEN (10.2) |
| PS4 | M | No bounded recorder or `review` replay | OPEN (10.3) |
| PS5 | H | Boot-art provenance and Bethesda trademark/asset-terms question unresolved | OPEN (owner, 10.8) |
| PS6 | M | UI toolkit undecided; VS Code extension lean withdrawn | OPEN (owner, 10.7) |
| PS7 | L | Virtual-desktop creation relies on undocumented Windows interfaces | OPEN (10.9) |
| PS8 | M | No edit/ref/hunk contract for fast diff and amend | OPEN (10.7) |
| PS9 | M | No project file concept tying env, load order, scripts, probe profile | OPEN (10.10) |
| PS10 | L | Theme tokens undefined | OPEN (10.8) |
| X1 | H | No single config resolver | OPEN (roadmap 2) |
| X2 | M | Three languages share loose JSON/exit codes; no enforced envelope | OPEN (roadmap 3) |
| X3 | L | Lessons live in code comments that go stale | OPEN |

Severity is my judgement from reading, not from running anything. U-series and VL1 come from Section 8.

## Pass status

| Pass | Scope | State |
|---|---|---|
| 1 | Repo shape, inspiration archive (prompt + ideas + separation only), README, both HANDOVERs, dashboard, FRONT-LIST, FIX-BACKLOG, POSITIONING (head), RESUME.md | DONE (skim depth); rest of inspiration archive TODO |
| 2 | PIP-MON_CONSOLIDATED.txt (213 KB, 27 sections), remaining inspiration files, docs/*, tasks/*.json | PARTIAL: outline, s1, s6, s14, s18, roadmap tier 2/3 read; s2-s5, s7-s13, s15-s17, s19-s27 TODO |
| 3 | Script-management core: tools/pipmon.ps1, linksync.ps1, build_papyrus.bat, validate_plugin.ps1, orchestrate.py, gen_papyrus_ref.py, artifact_gate.py, taskrun.ps1 | PARTIAL: linksync, build_papyrus.bat, validate_plugin (header+exit paths), pipmon validate verb, orchestrate.py (header, sh, classify, SHELL), create_environment.pyr read; TODO: taskrun.ps1, artifact_gate.py, gen_papyrus_ref.py, ck_session.ps1, run_gen.ps1, rest of orchestrate.py |
| 4 | vprobe C++ (src/include, Zydis use, detour, IPC), launcher, overseer_cli, Rust crate | TODO |
| 5 | ai_context (spec/*.json, RAG, vendored third-party), testfacility, tests, licence audit | TODO |
| 6 | Final report: architecture, defects, roadmap | TODO |

## 1. What the repo is (measured)

- Origin (inspiration archive "pip-mon prompt.txt"): a Pip-Boy Monitoring and Diagnostics Suite. Three parts: V-Probe (in-process C++ DLL), OverseerCLI (external TUI, anomaly detector), PipMon_TestLab (sandbox cell + synthetic leak/loop scripts). Telemetry first, not script management.
- Later direction (docs/POSITIONING.md): replace the F4SE and extender layer; Papyrus VM and .pex stay native. Hierarchy: T0 exe bytes, T1 Oracle (offline fact extraction), T2 Library (zero-alloc in-game), T3 Surface (PIPMON_*, V-Link, PipMon: Papyrus API), T4 Consumer, plus a T5 "hallway" access layer.
- Where "script management" actually lives today (scattered, no single owner):
  - `tools/pipmon.ps1` envelope CLI: status, verify, build, link, validate
  - `vprobe/papyrus/build_papyrus.bat` (stage to space-free dir, compile, verify PEX magic)
  - `tools/linksync.ps1` (owns plugins.txt: snapshot/apply/restore/status)
  - `tools/validate_plugin.ps1` + xEdit Pascal scripts (headless validation)
  - `gen_papyrus_ref.py` (34 KB Papyrus reference generator), RAG knowledge base, `tools/orchestrate.py` (phased plans P1-P4)
- Composition: 96 md, 49 py, 34 cpp, 26 h, 25 pas, 20 hpp, 14 ps1, 9 bat, 8 psc, 5 cs. 50 files in tools/.

## 2. Architect-level findings (pass 1)

### Identity
A1. The repo has no stated spine. Tagline says script management; the code investment is a native runtime replacement for F4SE. Decide the spine explicitly (see roadmap).
A2. Core thesis is unproven. S0 (register a native, call it from a compiled .psc, no F4SE) has never been attempted. Layer A (VM hook) does not exist. No vtable slot is hooked. Everything built so far is backend, gates and tooling.

### Documentation drift (the project's own named worst failure class)
D1. (DOWNGRADED, see 2d) HANDOVER s10 says: local repo, master, no remote, 115 files, "Personal Use Licence". Reality: public GitHub, main, 370 files, PolyForm Noncommercial 1.0.0 (commit 10e9bb7). Also G10 ("never push unless asked") vs a public push: confirm intended.
D2. HANDOVER s8 marks README "CURRENT, states what WORKS and what does NOT". Actual README is a 2-line placeholder (commit da52ad4). The honest README was lost or never landed.
D3. LICENSE header text reads "Use is granted. Modification and redistribution are not." PolyForm Noncommercial 1.0.0 does permit noncommercial modification and distribution of copies with notice. Header contradicts the licence body: verify the full file (pass 5).
D4. ai_state_dashboard.md (generated 09-30) is stale against HANDOVER-SESSION 10-01: dashboard shows CKPE as [FAIL]; session handover reclassified it as [INFO]. Dashboard shows plugin 973 B deployed; FRONT-LIST says live plugin is 66 B and 973 B is PRIOR-WORK. The dashboard is a GENERATED file committed to git, which violates the repo's own .gitignore rule about derived artefacts, and it leaks a local path (C:\Users\Administrator\Desktop\...).
D5. FIX-BACKLOG A/B: the documented root cause of the xEdit abort (GetPluginName missing) is contradicted by the log evidence (parse error at CreateScript, never compiled). Two docs (HANDOVER s4C, surfaces.json creation.xedit) still record the unsupported cause.
D6. HANDOVER "verify" block (15 pass / 0 fail / 2 skip, launcher 45, python 106, rust 5) cannot be confirmed without the game and CK on disk; treat as unverified from here.

### Process and quality
P1. Gates reported RED and left: rag_selftest, door_lint (pre-existing), orchestrator P4 gate is a "wall" (requires records_created > 0 from a generator that could not create records). Bare `orchestrate.py` exits 2 instead of usage + 0.
P2. Validator has never run against the committed source (FIX-BACKLOG C): last executed artefact differs from committed .pas, so no result describes current code.
P3. [CORRECTED Session 1] FIX-BACKLOG A said validate_plugin.ps1 did not read xFOEdit64Exception.log. Re-checked against main e05dd7a: it DOES (Get-XEditException, verdictSource = xFOEdit64Exception.log; xedit_log.py decodes the UTF-16LE log). Backlog item A is stale or already fixed. Residual risk is V1 (stale report), not blindness.
P4. Orchestrator has no checkpoint/resume, discards gate output (FIX-BACKLOG E1, E2).
P5. Backup/stray files committed: `tools/rag_query.py.bak-unicodefix`; commit 3746bcf "Stop excluding session backups".
P6. Stage-2 cost: xEdit loads the entire active load order (~2m15s for 61 plugins) even for one plugin. Undecided (scratch Data folder vs plugins.txt swap vs accept).
P7. Windows-only, hardcoded-path tooling (.bat/.ps1). Acceptable for the target, but nothing is portable or CI-able; no GitHub Actions evident.

### Risk
R1. Vendored third-party code in a PolyForm-licensed public repo: ai_context/systems/F4SE-Plugins (20 files), ckpe/verbatim (15), pyo3 (15), ba2_format/verbatim, mxpf, xEditScripts. HANDOVER says "nothing proprietary" but that was verified at 115 files. Re-audit each upstream licence (pass 5).
R2. Process-injection plus detour engine into a shipping game: failure mode is a crash with no symptom. The project's refuse-do-not-guess rules are the right mitigation; keep them.
R3. Documentation volume (213 KB design doc, 96 md) versus a blank README: onboarding cost is high and drift is already measured.


## 2b. Pass 2 findings (design doc, partial)

DD1. "Script management" is the END STATE, not the current build. Design doc roadmap Tier 2 / POSITIONING phase D: "A user installs PIP-MON and needs nothing else for papyrus instrumentation, a script console, and script management." Phases: A dual load, B own plugin loading + own Papyrus host, C own command/script API, D extender no longer required. So the owner's "script management first" matches the destination, but today's working code is Phase-A-adjacent tooling.
DD2. Doc numbering is broken: sections run 1-14, 18-25, then 24.8, then 15-17 appended later ("added from 1moreideas.txt"). Section 24.8 sits after 25. Fix when the DOCS DOOR is built.
DD3. The design doc has two real script-management designs not yet built: s6.2 two-pane CLI (`compile <file>`, `sort`, `exec`, `kill`) with Caprica build pipeline, and s18 provider registry (probe / enabledSet / disagreements across Bethesda, F4SE, Vortex, MO2, FOMOD; read-only providers; a published survey manifest). s18 is marked "nothing built yet" and is the best-justified feature in the repo: it came from a measured failure (Vortex state deleted, 65 enabled vs 0 deployed). Strong candidate for the real spine.
DD4. s6.4 log object model (raw text, path, line/col, FormID) and s6.7 dedup (hash, collapse above 50/s) are sound and cheap; check whether overseer_cli implements them (pass 4).
DD5. Inspiration archive is a prompt-to-design lineage: "pip-mon prompt.txt" (original 3-part monitor spec, CommonLibF4 + CBOR assumptions) was superseded by the measured design (no CommonLib linked, own wire format, KERNEL32-only imports). Good evidence the project self-corrects; "updated ideas.txt" lists libraries (Mutagen, esplugin, Champollion, minidump, zerocopy, Capstone) of which only capstone/pefile are adopted per HANDOVER s7.

## 2c. Tier notes, Session 1 continued

OWNER UPDATE (Session 1): some of the gate blockers listed in 2/P1-P3 were fixed after the last push. GitHub copy may lag local. Treat P1-P3, D4, D5 as "as of GitHub main (da52ad4)"; re-verify against a fresh push before reporting them as current.

Size (non-vendored, measured by line count): tools/ 13,085 | vprobe src+include ~6,960 | overseer_cli src 4,510 + tests 1,745 | launcher 2,219 | testfacility 803. The largest code area is the script-management tooling (tools/), not the native runtime. Evidence for the owner's framing: the working investment IS script management.
No .github/ directory: no CI. Tests exist for overseer_cli (3 py files), vprobe (test_harness.cpp), launcher (helpers); tools/ has self-tests (orchestrate_selftest, rag_selftest) but no unit test directory.
pipmon.ps1 (479 lines) is a clean product surface: one JSON envelope schema `pipmon.surface/1`, one exit-code vocabulary (0 GREEN/OK, 1 RED, 2 BROKEN, 3 SKIP, 4 usage), SKIP is never PASS, every envelope names provenance. Commands: status, verify, build, link, validate, snapshot. This is the best candidate to declare as the script-management API.

Design doc s1 and s14 (read):
- s1 component map still lists vprobe as replacing "F4SE injection + hook layer" and states KaDag is a xEdit replacement; says NOT replaced: Creation Kit, Archive2 writing, gameplay fixes. Note: HANDOVER-SESSION 10-01 says the CK is the authoring host and extensions (CKPE) are what get replaced, consistent.
- s14 Q5 asks "Does the DLL stay MIT if loot-cli is invoked?" The repo is now PolyForm Noncommercial. Stale question, licence decision never recorded in the design doc. Fold into D1/D3.
- s14 Q13: the F4SE load path is "temporary" with no expiry trigger set (G12). Needs a deletion criterion.
- s14 Q14: unlisted game patch makes the launcher refuse to start the game; no shareable-profile path decided. User-facing risk.
- s14 Q15: standing consent for read/test/validate; writing outside project, system config, commit, push still ask. (Matches G9/G10.)
- s14 Q4/Q10 are partly stale (Tier 2 AOB resolved 09-29). The design doc is append-only so resolved questions are not closed in place: add RESOLVED markers.
- s14 Q11 answered by observation: Vortex is the provider (vortex.deployment.dinput.json); MO2 not installed. Provider registry (s18) should target Vortex first.

## 2d. Owner clarifications (Session 1)

- Repo is public ONLY so it can be evaluated. Public push is not a design decision; G10 is not violated in spirit. D1 (public/remote mismatch) downgraded to "handover text is stale".
- Licence is unsettled: GitHub would not take PolyForm, so another licence must be chosen. D3 and design-doc s14 Q5 (MIT) both stay open until chosen. Practical note: a LICENSE file with any text can be committed by hand; GitHub only fails to auto-classify it (shows as unrecognised). Also: before choosing, re-audit vendored third-party code under ai_context (R1), since it constrains what licence the repo can carry.
- Gate blockers partly fixed locally since last push (see 2c).

## 2e. Pass 3 findings: the script-management code (Session 1)

New commit e05dd7a added RESUME.md. It confirms: P4 gate is a wall and step 1 of 4; plugin still 66 B / 0 records; gates green = spec_lint, artifact_gate, surfaces_gate; red = door_lint (2 problems, 17 unregistered), rag_selftest, P4. Local README claims ALL GATES PASSED while two are red (OWNER NOTE: some blockers fixed locally since). Licence shows NOASSERTION because the PolyForm text was written, not pasted canonically (fix: paste the canonical text from polyformproject.org verbatim).

### linksync.ps1 (178 lines) - verdict: sound design, 5 defects
Strengths: snapshot before every write, restore, never touches mods.txt, writes ONLY after snapshot, appends our plugin last (= active file), reports before/after counts.
- L1 (real): `Set-Content -Encoding ascii` silently turns any non-ASCII plugin name in plugins.txt into `?`. A load-order tool must round-trip bytes. Read and write raw bytes (or UTF-8 no BOM) and preserve line endings.
- L2: header promises "staging first, diff second, apply only on request" but `apply` writes directly; no -WhatIf / diff preview. (ck_session writes plugins.txt.proposed.txt, so the pattern exists; linksync should reuse it.)
- L3: read-modify-write race. Vortex and the CK both rewrite plugins.txt (the file's own header documents this). No re-read-and-compare before the write, no post-write verify beyond counts. Add: hash before, hash immediately before write, abort on change; after write, re-read and assert our plugin is last and enabled.
- L4: snapshot name is second-granularity with -Force, so two snapshots in one second overwrite silently. No retention policy (runs\linksync grows forever).
- L5: no master check. apply enables names blindly; it never confirms the plugin's masters are present, enabled, and earlier in the order. That is the first thing a real load-order manager must do.
- L6: GameDir default and %LOCALAPPDATA%\Fallout4 are hard-coded (Steam path; breaks GOG, MS Store, FO4VR, non-default library).

### build_papyrus.bat (251 lines) - verdict: excellent comments, narrow scope
Strengths: space-free staging (the compiler cannot parse spaced paths), robocopy /MIR persistent stage (measured 6,763 ms -> 56 ms), stale .pex deleted before verify, PEX magic bytes (DE C0 57 FA) checked on BOTH PipMon.pex and PipMonTestFacility.pex, exit code not trusted (artefact existence checked), every extra script named on failure.
- B1 (scope, the key script-management gap): the build is a hard-coded list of 2 products + 4 compile-only scripts. It is a build of THIS project's scripts, not a script manager. Missing for the stated purpose: discover sources (Source\User), resolve imports and dependency order, incremental build (hash/mtime), per-script result in the JSON envelope, deploy to Data\Scripts with a manifest, and undeploy.
- B2: header note 2 says base scripts are staged to `%STAGE%\base` and imported with `-i=base`; the code mirrors Base into the stage ROOT and passes no -i. Stale comment, the project's own named failure class in miniature.
- B3: the stage is a shared persistent directory in %TEMP% and `del /q %STAGE%\*.pex` runs every build: two concurrent builds (manual + orchestrator) race. Use a per-run subdirectory or a lock file.
- B4: FO4 install path hard-coded (same as L6). One resolver (env var > registry/Steam library scan > default) should serve .bat, .ps1 and .py.
- B5: Windows .bat with fragile quoting and delayed-expansion workarounds (the file documents two of its own such bugs). A short Python or PowerShell driver would be testable; keep the .bat as a thin wrapper.
- B6: trailing duplicate `exit /b 0` (harmless).

### validate_plugin.ps1 + `pipmon validate` - verdict: refusal logic strong, one integration gap
Strengths: SKIP never PASS; refuses if CK or xEdit running; every non-run path writes a SKIP report; detached -Async / -Collect so the agent is never blocked; 420 s timeout measured, not guessed.
- V1: `pipmon.ps1 validate` ignores validate_plugin's exit code and takes status only from xedit-latest.json via Read-Report, which has no run-id or timestamp. If validate_plugin throws before writing (it runs under $ErrorActionPreference='Stop'), pipmon reports the PREVIOUS run's verdict. This is the stale-evidence failure RESUME.md warns about. Fix: validate writes a run-id; pipmon passes it in and rejects a report that does not carry it.
- V2: `pipmon validate` cannot launch -Async / -Collect (only -Plugin is forwarded), so the one command that exposes validation blocks for ~3 min, the exact problem the validator's header says it solved.
- V3: exit-code vocabularies differ: validate_plugin 0 PASS,1 FAIL,2 BROKEN,3 SKIP,4 RUNNING,5 LOCKED; pipmon 0 GREEN,1 RED,2 BROKEN,3 SKIP,4 usage. 4 means different things. Unify in one documented table.
- V4: XEditDir default is under %LOCALAPPDATA%\Temp\opencode\xedit\x, a temp location for a tool the whole pipeline depends on. Move to a configured tools dir.
- V5: plan assumes a "curated 35-plugin load order"; the validator header measures a 2m15s load (earlier notes say 61 plugins). Reconcile which load order the validator really uses.

### orchestrate.py (935 lines) + plans - verdict: right architecture, three sharp edges
Strengths: plan is declarative and reviewable (ai_context/plans/*.pyr, JSON, schema.json present); runner never reorders, retries, or decides; allowlist by executable token; allowed() and classify() share one membership test after a real "P1 verified but never ran" bug; atomic state writes; gate output always captured to transcript; detached actions + bounded polls so it is interruptible.
- O1 (real): commands are tokenised with `cmd.split()`, so no argument may contain a space. The repo path and the game path both contain spaces (the project says so itself). Use shlex.split with posix=False or store argv arrays in the plan.
- O2: the allowlist (SHELL dict) is hard-coded in orchestrate.py while 50 tools exist and door_lint already reports 17 unregistered. Registry belongs in one data file that door_lint also reads.
- O3: P4 problems are two, not one: records_created > 0 wall (RESUME step 1) AND poll budget_sec 60 vs a measured generator run of 1m42s script time (plan text). Check whether the orchestrator re-enters; if not, P4 cannot converge even after the wall is fixed.
- O4: plan JSON carries essay-length prose ("why", "gate_repair_2026_09_30") beside machine fields. Ordering and determinism rules live as prose; nothing enforces them. Move narrative to docs, keep plans diffable.
- O5: `.pyr` is JSON with a custom extension: editors give no highlighting and no comments. Use .json (or add schema association).
- O6: every subprocess passes `-ExecutionPolicy Bypass`. Acceptable for a personal local tool; note it before any distribution.
- O7: fixed `.tmp` name in _atomic_write: two writers collide. Use a unique temp name.

### Cross-cutting
- X1: no single config. FO4 path, plugins.txt path, xEdit dir, stage dir are repeated across .bat/.ps1/.py with different defaults. One `config` resolver is the single highest-leverage refactor for a script manager.
- X2: three languages (bat, ps1, py) talk through exit codes and loose JSON. Fix with ONE envelope schema (pipmon.surface/1 already exists) emitted by every tool, and validated in surfaces_gate.
- X3: the project documents its own bugs in code comments at length. Excellent for lessons, but several comments are already stale (B2). Add a gate that greps a path/flag named in a comment against the code, or move lessons to one LESSONS.md.

## 3. Strengths worth keeping

- Tier model with a cost ceiling per layer; "a fact with no provenance may not exist".
- Build-time derivation (541 KB text DB to 103 KB blob, zero in-game allocation) with a stale-blob guard that fails the build.
- Refusal catalogue (wrong schema, non-zero reserved bytes, wrong arity, foreign namespace, non-vtable address).
- Measured, not assumed: RTTI proved the six AOB targets named classes that do not exist; vtable slot counts measured from the binary and gated.
- Honest SKIP semantics (a skip is never a pass).
- Lessons-learned sections (Do not repeat) are accurate and useful.

## 4. Open questions for the owner

1. Is "script management" the spine (build, deploy, load-order, validate, reference, RAG), with the native runtime as a later track? Pass 1 evidence says the working, gated parts are exactly the script-management parts.
2. Is the public push and PolyForm licence intentional?
3. Is the next goal "records exist and load" (nearly done) or "something executes in-game" (needs Layer A)?

## 5. Proposed roadmap (draft, revised after Pass 3; final after Pass 5)

1. Truth pass (1 commit): canonical PolyForm text (or chosen licence) pasted verbatim; real README; one DOCS DOOR index; RESOLVED markers in the design doc; delete committed generated and backup files; fix stale comments (B2) and stale handover facts (D1, D2, D4).
2. One config resolver (X1): FO4 dir, plugins.txt, xEdit dir, stage dir; env var > registry/Steam scan > default; used by .bat, .ps1 and .py.
3. One envelope and one exit-code table (X2, V3), every tool emits pipmon.surface/1; validate carries a run-id so a stale report is rejected (V1); pipmon validate gains -Async/-Collect (V2).
4. Harden linksync (L1 raw-byte round trip, L2 dry-run diff, L3 hash-compare race guard, L5 master check) and make it a pipmon verb with envelope output.
5. Generalise the build (B1): discover Source\User, dependency order, incremental, per-script results, deploy manifest plus undeploy. This is the actual "script manager".
6. Provider registry (design s18) targeting Vortex first: read-only probe, enabled-set, disagreements. Biggest justified new feature.
7. Fix orchestrator edges (O1 argv arrays, O2 registry shared with door_lint, O3 P4 poll budget plus wall gate, O7 unique temp names); add CI for gates that need no game (spec_lint, artifact_gate, surfaces_gate, door_lint, rag_selftest).
8. Only then Layer A / S0 (hook, native call from compiled .psc) as a separate track.

### 5b. Usability track (from Section 8; parallel to 2-5)
U-a. Finish test env records (RESUME steps 1-4). U-b. `doctor` verb plus status --watch. U-c. Spec correction for Terminal menus plus compile probe. U-d. Status cartridge plus Beacon, one-way. U-e. Workbench v0 (VS Code extension lean WITHDRAWN, see 10.7). U-f. Settings cart with MCM-compatible reader/writer. U-g. Broker plus VL1 fix. U-h. Two-way after Layer A.

## 6. Resume block (paste into a new window with this file)

"Continue the pip-mon evaluation using PIPMON_EVAL_NOTES.md. Read section 0 first. Clone with git (github.com is reachable from the sandbox; pull for new commits). Read sections 8, 9 and 10 too. Next: finish Pass 3 per section 7, then Pass 2 remainder; verify VL1 and the Terminal-menu claims if a Windows/game session is available. Revise the notes file in place; do not create new versions. Warn me when context is getting heavy."

## 7. Session log

- Session 1 (2026-10-01): Pass 1 (skim), Pass 2 partial (s1, s6, s14, s18, outline), Pass 3 partial (see 2e). Cloned da52ad4, pulled e05dd7a. Owner clarified: repo public only for eval; licence undecided; some gate blockers fixed locally but unpushed. Compaction/realign done at end of session 1 (see section 0). Corrected P3 after re-verification.
- Session 1b: Usability pass (Section 8): viewed both concept images, read archive UI/bus ideas, in-game surface spec, V-Link server and client, checked FO4 Holotape/Terminal and MCM facts online. New findings U1-U7, VL1, D3b, P5b.
- Session 1c: owner confirmed images = VS-style workbench concept art; CLI ideas were not concrete. Wrote Section 9 (CLI design) and findings C1-C5.
- Session 1d: owner brief on UI identity, launch modes, probe profiles, guardrails. Wrote Section 10, findings PS1-PS10; withdrew VS Code extension lean; checked Windows virtual desktop API facts.
- Session 1e: owner pointed at the F4SE-style pause; confirmed launcher already creates the process suspended and injects; added 10.12, PS11-PS14, corrected PS2.
- Next window: finish Pass 3 (taskrun.ps1, artifact_gate.py, gen_papyrus_ref.py, ck_session.ps1, run_gen.ps1, rest of orchestrate.py), then Pass 2 remainder, then 4-6.

## 8. Usability and wire-up pass (Session 1b)

Inputs read: 2 distinct concept images (4 files; 2 are byte-identical duplicates), inspiration archive (dual-mode event bus, compatibility/overlay, another clarifying list, 1moreideas), spec/in_game_surface_requirements.json, systems_core/t5_highway_bus.md, overseer_cli (CLI flags, protocol, ipc_client, ui/app.py size), vprobe/src/IPCServer.cpp, testfacility COVERAGE.md, PipMon_TerminalTest.psc. Web-checked: FO4 Holotape/Terminal CK pages, MCM and F4SE Menu Framework pages. Nothing executed.

### 8.1 What the images show (layout only; all text is garbled generation noise)
Both are a VS Code-style IDE shell titled "NemoAid (IDE)". Owner: names are placeholders, only positions matter. Regions and my mapping to PIP-MON:

| Image region | Meaning in PIP-MON |
|---|---|
| Activity bar (explorer, search, git, run, extensions, flask) | Workbench modes: Workspace, Search/RAG, Link/Git state, Run (verbs), Cartridges, Test lab |
| Project Explorer tree | Workspace: scripts (Source\User), plugins, cartridges, profiles |
| 2nd pane "Resource & usable files" (Crates, Modules, Plugins with versions, Dependencies nodes) | Provider registry (design s18): game build, F4SE, Vortex deployment, CK, xEdit, vendored libs; each with version and "disagreements" |
| Editor with breadcrumbs, tabs, minimap | Script/psc/pex/config viewer with provenance |
| Right-click menu (Apply <X> Mod, Inspect Mod Options, Convert to Crate, Check Dependencies, Go to Definition, Refactor submenu with Settings/Scripts/Plugin Settings, Add to Favorites, Properties) | Context verbs bound to `pipmon.ps1` verbs on the selected item: build, link, validate, snapshot, inspect, check dependencies |
| Bottom panel Terminal/Output + Problems (0) | Envelope viewer (pipmon.surface/1) + Actionable Error List (archive "atomic items with checkboxes") |
| Status bar (branch, "Build: Succeeded", line/col, language version, "Agent" mode) | Gates GREEN/RED/SKIP, game build identity, link state, probe connected, AI autonomy level |
| Outline pane, Timeline pane (image 2) | Symbols of the open script; snapshots/runs timeline (linksync, ck_session, orchestrator archive) |

Not shown anywhere: any in-game surface, Pip-Boy, cartridge, or settings page. Those are new requirements from the owner (below).

### 8.2 Decision conflict to record
- Archive decision: out-of-process only, "zero in-game overlay", MCM replaced by an external Ratatui TUI on a second monitor. Implementation drift: the dashboard is Python Textual (375-line app.py), and rust/ holds only a vlink-protocol crate. Neither is wrong, but docs and code disagree.
- spec/in_game_surface_requirements.json holds an open `decision_owed`: build a real in-game surface or keep terminal-as-trigger plus external UI. Status of "in-game-menu" is NOT_MET, mechanism "MUST BE BUILT".
- Owner direction now (Session 1b): build the in-game surface as Pip-Boy cartridges, usable alongside the external CLI/UI. This answers decision_owed. Reconciliation: the external workbench stays the primary developer surface; cartridges are an additional in-game CONSUMER (T4) of the same backend. Single-monitor players cannot use an external TUI in fullscreen, which is the practical case for cartridges.

### 8.3 The FO4-native mechanism for an in-game menu (answers "MUST BE BUILT")
The spec is right that Papyrus-the-language has no menu. But FO4 has menus in the DATA layer: Terminal forms.
- Holotape types (CK): Sound, Voice, Terminal, Program (Flash SWF). A Terminal-type holotape displays a Terminal on the Pip-Boy.
- Terminal forms carry Menu Items and Submenus; nested menus are separate Terminal forms linking like web pages; Terminal has `ShowOnPipboy()` and `OnMenuItemRun(int, ObjectReference)` (both present in the repo's own Papyrus reference, part06). "Holds Holotape" on a placed terminal lets a world terminal carry a default cartridge, which is the "assign it to a terminal" idea, supported by vanilla.
- Consequence: a Terminal-holotape cartridge needs no F4SE, no Scaleform, no new native, and no per-build address, so it survives game updates better than MCM does. Menu-item actions run ordinary Papyrus fragments (the existing spec constraint holds: in-game surface scripts must be ordinary, not Native).
- Limits to state honestly: text and list menus only; numeric settings need +/- step menus; no free text entry; display text bound to live values needs verification (Terminal text replacement tokens such as Global-bound text are believed supported, UNVERIFIED here). Program (SWF) holotapes allow rich UI but need an ActionScript 3 toolchain (tech_stack.md already notes FO4 Scaleform is AS3) and are the riskier second step.
- Action: spec correction owed, same shape as the CustomEvent one the spec already records: in-game-menu mechanism_status becomes "EXISTS in the data layer (Terminal forms), not in the language", plus a compile probe for a fragment calling Terminal functions and a measured in-game test (COVERAGE.md already plans a holotape-in-inventory test and terminals in two rooms).

### 8.4 Cartridge catalogue (proposal)
1. Status cart (read-only): probe connected, gates, build identity, link state. Smallest first cartridge; proves the path.
2. Settings cart ("setting cart", the MCM replacement). Owner expects 2-3 MCM-type categories, not mod management:
   a. PIP-MON itself: probes on/off, telemetry rate, HUD verbosity, pre-save valve, profile presets.
   b. Script and framework settings: per-mod pages. Compatibility trick: read the existing MCM layout (Data\MCM\Config\<Mod>\config.json) and write the same Data\MCM\Settings\<Mod>.ini that MCM writes, so existing mods' pages appear without MCM. Precedent: the F4SE Menu Framework mod ships exactly such a translation layer. Facts checked: MCM is an F4SE plugin (no F4SE running means no menu), keeps settings in per-mod INI not the save, and game updates have broken F4SE and MCM before (an NG patch of an MCM add-on was required).
   c. Performance and compatibility profiles: named presets, snapshot and rollback hooks.
3. Diagnostics and Repair cart: Actionable Error List atoms with their repair choices (8.7).
4. Load-order cart, later and read-only first (provider registry view).
Rule: a cartridge is a view, not an owner. Anything it changes goes through a pipmon verb (snapshot, apply, verify), never a direct write.

### 8.5 Probes: how "a few light probes" can coexist
Define a probe taxonomy with a cost ceiling per kind (the tier model already has the idea):
- Core: vprobe.dll, one in-process, owns the V-Link pipe, runs its sampler on its own thread, read-only by default.
- Beacon (pure Papyrus): an ordinary script emitting a heartbeat via Debug.OpenUserLog / TraceUser (both in the repo's Papyrus reference) and StartTimer; zero hooks, zero natives. Proves a one-way path before Layer A exists. PipMon_TestFacility.psc already uses the FO4 timer form.
- Satellites (out of process): file watchers on Papyrus logs, plugins.txt, crash dumps, xEdit logs. Zero in-game cost; these already fit the overseer design.
- Cartridge as a probe with a face: terminal menus reading beacon state.
Non-conflict rules (proposed): every probe declares capabilities in the signage layer (T5) and a cost ceiling; at most one hook per address (check the door registry at registration); satellites report via the core or files, never open a second hook; every probe has a control-channel kill switch; hooks are refused, not guessed, on unknown build identity (existing rule).

### 8.6 Honest wiring status: what can be tested now vs not
| Rung | Needs | State |
|---|---|---|
| L0 UI/CLI against a fake probe (no game) | tests/fake_probe.py (real Win32 named pipe, real framing, scenarios), `overseer-cli --mode headless` or TUI | EXISTS in repo; Windows-only; not run here |
| L1 CLI/TUI with real game and vprobe | vprobe built and loaded via the temporary F4SE path, launcher, V-Link | Built per handover; not hooked into scripts; telemetry path untested by me |
| L2 In-game cartridge, one-way (game to outside) | Beacon script plus Terminal holotape in the facility esp, tail of the user log | Possible with NO Layer A once the facility esp has records (RESUME.md: about 30 min after P4 wall fix) |
| L3 Cartridge two-way (outside to game) | Layer A (native or engine write path) | NOT POSSIBLE yet; this is the already-known long pole. Interim: player drives via terminal menus that set Globals through fragments; anything the probe writes must pass the refuse rules |
| L4 Multi-client (HUD + logger + AI + workbench at once) | broker or fan-out | NOT BUILT (see VL1, U3) |

So the test environment being finished quickly (owner point) is on the critical path: L2 cannot start until PipMonTestFacility.esp has records.

### 8.7 The single-source / closed-loop idea (owner's hypothesis)
Hypothesis: if scripting, sorting, environment variables and frameworks live in one defined source, and logging, monitoring and output formats all align with repair paths for a user or an AI, problem-solving can be semi-automated. Assessment: this is the right architecture and much is already present: spec JSON registries, surfaces.json, door_registry.json, vocabulary.json, the one envelope (pipmon.surface/1), LOG_FORMAT.md, and the atomic error items in the overseer design. What is missing is the CLOSED LOOP between them. Proposed contract:
- Finding: id, source, severity, evidence[], provenance (existing rule: a fact with no provenance may not exist), remedies[].
- Remedy: pipmon verb plus args, risk class (read | reversible | irreversible), required authority (auto | agent | user), rollback token (snapshot id), verification step (a status command that must return GREEN).
- Autonomy ladder (matches the project's own write rule: staging first, diff second, apply on request, always back up): observe, propose (writes .proposed, as ck_session already does), apply-reversible (snapshot, apply, verify, auto-rollback on failed verify), confirm (irreversible, user only).
- Example: Vortex rewrote plugins.txt and our plugin is disabled (the project's measured worst failure) -> finding from linksync status -> remedy `link apply` (reversible, snapshot) -> verify `link status` shows enabled and last. This is semi-automatable today once L1/L3/L5 in 2e are fixed.
- Guard: the control channel is fire-and-forget by design and queued by the probe; keep that. An AI remedy must never be able to skip the verify step or the snapshot.

### 8.8 Mod manager question
Recommendation: do not build a general mod manager inside PIP-MON. The measured failure (Vortex dropped our plugin; 65 enabled vs 0 deployed) is about LINK STATE, not downloading or installing. A scope ladder:
- R0 read-only provider registry (design s18), Vortex first (MO2 not installed per s14 Q11).
- R1 link ownership (linksync hardened: L1, L3, L5) exposed as a verb and a cartridge page.
- R2 deploy verification: hash manifest of what is in Data against the enabled set; report drift.
- R3 optional: own deploy for PIP-MON's own files only.
- R4 general mod manager: not recommended; revisit only if R0-R3 prove insufficient.
"Update-type issues" are better handled by the build-identity gate (launcher BuildIdentity.cpp already exists) plus vanilla-record cartridges, than by owning installation.

### 8.9 New defects found in this pass
- VL1 (suspected, UNVERIFIED, needs Windows run): vprobe/src/IPCServer.cpp passes PIPE_UNLIMITED_INSTANCES (value 255) inside dwPipeMode on the first CreateNamedPipeW, while also passing 4 as nMaxInstances. 255 is an instance count, not a mode flag; the extra bits are invalid or select message mode, which would make that call fail with ERROR_INVALID_PARAMETER. The fallback call then passes the constant correctly, so the pipe probably works by accident, and the comment blaming ERROR_ACCESS_DENIED is likely wrong. Fix: first call mode = PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT (| PIPE_REJECT_REMOTE_CLIENTS), nMaxInstances = chosen number; log GetLastError on each failure.
- U3: V-Link is duplex (control channel via send_control; probe queues commands) but the server holds a single `pipeServer_` handle; archive's multi-client hub (HUD + logger + AI terminal) is not implemented. Decide: a fan-out broker (launcher or small daemon) so the game side has one writer.
- D3b: overseer_cli/pyproject.toml declares license MIT and author "PIP-MON contributors"; repo LICENSE is PolyForm Noncommercial. Licence decision must be applied everywhere.
- P5b: two byte-identical duplicate image files (294 KB + 200 KB) in the archive; keep one copy each, rename to say what they are (not "Untitled", "testimage").
- U6: archive says Rust/Ratatui for the TUI; code is Python/Textual; docs should say which is current.

### 8.10 Usability enhancement list (ordered by leverage)
1. One config resolver (X1) so every UI and CLI finds the same game, plugins.txt, tools. [S-M]
2. `pipmon.ps1`: add `--json` everywhere (exists as envelope), `status --watch`, a single `doctor` verb (runs status+verify+link status and prints ONE ranked list of findings with remedies). This is the CLI face of 8.7. [M]
3. Finish test env: P4 wall, 3-arg FileWriteToStream, copy-element path (RESUME.md steps 1-4) so the facility esp has records. [M, on the critical path for every cartridge test]
4. Cartridge 1 (Status, Terminal holotape) plus Beacon script, one-way via user log, tailed by overseer-cli. [M]
5. Workbench v0. Two options: (a) VS Code extension: the pictured chrome (explorer, tree views, Problems, status bar, context menu, terminal) already exists in the host, and envelopes map directly to diagnostics, tree items and commands; cost is a TypeScript layer and a VS Code dependency. (b) Extend Textual: no new dependency, but the pictured GUI chrome must be hand-built. My lean: (a) for the pictured IDE look, (b) kept as the in-game secondary-monitor view. If NemoAid is meant to be the host IDE, the same envelope contract serves it. This is a recommendation, not measured.
6. Settings cart with MCM-compatible reader/writer. [L]
7. Multi-client broker (U3) and VL1 fix. [M]
8. Then Layer A, for two-way cartridges. [L, separate track]

## 9. CLI design (Session 1c): concrete proposal

Owner (Session 1c): the images are concept art of a VS-style workbench for the UI side; CLI ideas are not concrete yet. This section makes them concrete, grounded in what exists. Everything here is a PROPOSAL from reading; nothing built or run.

### 9.1 What exists today (measured by reading)
| Entry point | Lang | Style | Role |
|---|---|---|---|
| tools/pipmon.ps1 | PowerShell | positional verb + -Param, JSON envelope `pipmon.surface/1` | THE SURFACE: caps, status, verify, build, link, validate, rag, editor, ck-session, snapshot, docs (+ -Watch, -Format dense, -Limit, -Page, -MaxLines) |
| overseer_cli (`overseer-cli`) | Python 3.12, Textual | argparse --flags | telemetry: `--mode tui|headless`, `--pipe`, `--config`, `--output`, `--once`, `--low-detail`, `--verify` (env gate) |
| tools/orchestrate.py | Python | plan file | runs declarative plans (create_environment .pyr), phases P1-P4 |
| tools/taskrun.ps1, launcher (C++), tests/fake_probe.py, run_gen.ps1, ck_session.ps1 | mixed | ad hoc | task runner, game launcher, fake telemetry producer, generator, CK session |
Problem: 5+ entry points, 3 languages, 2 flag conventions, and only one (pipmon.ps1) honours the envelope. A UI that wraps this would have to learn each one.

### 9.2 Principles (all taken from the repo's own invariants)
1. One surface, one envelope, one exit table (pipmon.ps1 header). 2. A human view is a RENDER of the envelope, never a second output format. 3. SKIP is never PASS. 4. A verb reports and acts; it never decides (orchestrator rule). 5. Writers follow: plan (staging) -> diff -> apply on request -> snapshot first -> verify after (the project's own write rule). 6. Depth control and signage are first-class (T5 hallway): the CLI tells you what else exists and lets you choose how much detail. 7. Every fact carries provenance.

### 9.3 Command tree (noun-verb; existing verbs map 1:1)
```
pipmon status | doctor | caps | docs            # orientation (status, caps, docs exist; doctor NEW)
pipmon script  list | check | build | deploy | undeploy      # script management core (build exists; rest NEW, see B1)
pipmon plugin  list | inspect | validate                     # validate exists
pipmon link    status | plan | diff | apply | restore        # linksync (status/apply/restore exist; plan/diff NEW)
pipmon snap    list | take | show | restore                  # snapshot exists
pipmon session inspect | prepare | restore                   # ck-session today
pipmon cart    list | build | deploy | show                  # cartridges (all NEW, see 8.4)
pipmon probe   list | status | attach | detach | kill        # V-Link / beacons / satellites (all NEW; kill = control channel)
pipmon watch   [--filter sev>=warn] [--since last] [--once]  # NDJSON event stream (wraps overseer headless)
pipmon log     tail | find | explain <finding-id>            # Papyrus.0.log, xEdit, CK, user logs
pipmon fix     list | plan <finding> | apply <plan-id> | verify | rollback   # closed loop (8.7), NEW
pipmon test    list | run <scenario>                         # fake_probe scenarios and facility benches
pipmon config  show | resolve | doctor                       # the single config resolver (X1), NEW
pipmon rag     index | stats | query                         # exists
pipmon editor  preflight                                     # exists
pipmon shell                                                  # REPL with completion generated from caps (NEW)
```
Backward compatibility: `pipmon build` stays as an alias of `script build`; `pipmon ck-session` of `session`; envelope `command` field keeps the old name until the UI migrates.

### 9.4 Standard flags (every verb)
`--json` (default when stdout is not a TTY), `--format dense|table|md` (dense exists), `--depth 0..3` (0 = status line, 3 = full evidence), `--limit/--page/--max-lines` (exist), `--watch` (exists), `--run-id`, `--dry-run` is the DEFAULT for writers: they emit a plan; `apply <plan-id>` executes. `--yes` is accepted only for risk class `reversible`; `irreversible` always prompts a human.

### 9.5 One exit table (resolves V3)
0 GREEN/OK, 1 RED, 2 BROKEN, 3 SKIP, 4 usage, 5 BUSY (CK/xEdit running, lock held, job still running), 6 NEEDS_AUTHORITY (verb is valid but requires a higher autonomy level). Today pipmon.ps1 uses 4 for usage while validate_plugin.ps1 uses 4 for RUNNING and 5 for LOCKED; this table replaces both.

### 9.6 Envelope v2 (additive to pipmon.surface/1, so old consumers keep working)
```json
{
  "schema": "pipmon.surface/2",
  "command": "link status",
  "run_id": "2026-10-01T18:22:07Z-7f3a",
  "status": "RED",
  "ok": false,
  "reason": "PipMonTestFacility.esp is in plugins.txt but disabled",
  "depth": 1, "truncated": false,
  "data": { "...verb-specific..." },
  "findings": [{
    "id": "link.plugin-disabled",
    "severity": "error",
    "evidence": [{"file": "plugins.txt", "line": 61, "text": "PipMonTestFacility.esp"}],
    "provenance": {"script": "tools/linksync.ps1", "game_build": "1.11.240"},
    "remedies": [{
      "id": "link.enable", "verb": "link apply", "args": ["-Enable", "PipMonTestFacility.esp"],
      "risk": "reversible", "authority": "agent",
      "rollback": "snap:last", "verify": "link status"
    }]
  }],
  "next": ["fix plan link.plugin-disabled", "log explain link.plugin-disabled"],
  "provenance": { "script": "...", "generatedUtc": "...", "workspace": "..." }
}
```
`findings[]`, `remedies[]`, `next[]` are the closed loop (8.7) and the T5 signage. `run_id` fixes V1 (a report is accepted only if it carries the id the caller passed).

### 9.7 `doctor` (the first new verb to build)
Runs status + verify + link status + config doctor, de-duplicates, ranks by severity then blast radius, prints ONE list. Human render:
```
$ pipmon doctor
RED  3 findings   GREEN  9 checks   SKIP  2
 1 error  link.plugin-disabled   PipMonTestFacility.esp disabled in plugins.txt
          fix: pipmon fix plan link.plugin-disabled        (reversible, auto-snapshot)
 2 warn   build.stale-pex        PipMon.pex older than PipMon.psc by 2 d
          fix: pipmon script build
 3 info   gate.door_lint         17 unregistered tools (known)
$ pipmon fix plan link.plugin-disabled
plan 9c1e: link apply -Enable PipMonTestFacility.esp   diff: +0 -0, 1 line changed   snapshot: yes
$ pipmon fix apply 9c1e
snapshot snap-20261001-182311  applied  verify: link status GREEN
```
(Illustrative output, not produced by any run.)

### 9.8 UI and CLI cannot drift: `caps` drives the workbench
`pipmon caps --json` lists every verb with: `appliesTo` (file kinds or node types: `*.psc`, `*.esp`, `plugins.txt`, `cart:*`, `probe:*`), `risk`, `authority`, `args schema`, `streams: true|false`. The VS-style workbench builds its right-click menus, command palette and tree views FROM caps. The image's context menu then equals `caps` filtered by the clicked item: on `*.psc` -> Build, Check dependencies, Open in CK; on a plugin -> Validate, Inspect, Link enable/disable; on a cartridge -> Build, Deploy, Show. A new verb appears in the UI with zero UI code.
Envelope -> UI mapping: findings[] -> Problems panel; status -> status bar; run history -> Timeline; data tables -> tree views; `next[]` -> quick actions.

### 9.9 Streaming
`pipmon watch` emits NDJSON, one event per line, each with `run_id`/`seq`/`ts`/`type` (V-Link event types exist: HEARTBEAT, THREAD_STATE, STACK_FRAME, STACK_DUMP, VM_TICK, VM_EXCEPTION, MEMORY, MOD_LOAD, PLUGIN_DIAG, SAVE_BLOAT), plus synthetic `finding` events from the detector. Wraps `overseer-cli --mode headless` today. Multi-subscriber needs the broker (U3).

### 9.10 In-game <-> CLI parity (honest)
- Game to outside (one-way, no Layer A): a cartridge menu item runs a Papyrus fragment that writes a REQUEST line with Debug.TraceUser to a user log (API present in repo reference). A small `pipmon serve` tails it, accepts only allowlisted `reversible` verbs (same allowlist idea as orchestrate.py), and executes them. Result appears in the workbench or status bar, NOT back inside the game. UNVERIFIED: user-log flush timing and whether a running game keeps the file readable.
- Outside to game: needs Layer A. Until then the cartridge can show pre-built static pages and state kept in Globals the player sets.
- Both paths go through the same verbs, so a cartridge button and a CLI command cannot behave differently.

### 9.11 Implementation lean (decision for the owner)
Option A (my lean): one Python console script `pipmon` (3.12 already required by overseer_cli) that owns argument parsing, envelope construction, run-ids, timeouts, argv-array subprocess calls and exit-code mapping, and calls the existing .ps1/.bat tools as backends. This fixes V1, V3, O1 and X2 in one place, makes completion and tests easy, and hosts watch/doctor/fix naturally. `tools/pipmon.ps1` becomes a shim until parity. Option B: keep PowerShell as the surface and add the verbs there. Cheaper now, but envelope, run-id and argv handling stay in PowerShell, which is harder to unit test and already hosts the largest drift (two exit vocabularies). Decide before building `doctor`.

### 9.12 Test plan for the CLI
Golden-file tests per verb (envelope shape, exit code, SKIP never PASS); `caps` snapshot test so UI contract changes are reviewed; extend surfaces_gate to cover every verb; run `doctor` against fake_probe scenarios in CI (needs a Windows runner; tests/fake_probe.py uses Win32 named pipes) and a non-Windows subset for envelope logic.

### 9.13 First slice (smallest thing that proves the whole shape)
1. `pipmon caps --json` with appliesTo/risk/authority for the 11 existing verbs. 2. `pipmon doctor` over status+link status. 3. `pipmon link plan|apply` with snapshot, hash-compare, verify (fixes L1/L2/L3). 4. `pipmon fix` for that one remedy. 5. The workbench v0 reads caps and renders the Problems panel and a context menu for plugins.txt. That is a complete vertical slice from CLI to UI to repair, small enough to finish before any cartridge work.

## 10. Product shape (Session 1d): identity, launch modes, probe profiles, workbench

Owner brief (Session 1d), recorded as stated, then my assessment. Nothing built or run. Supersedes: 8.10 item 5 (VS Code extension lean WITHDRAWN, see 10.7), because the owner wants a lightweight CUSTOM IDE.

### 10.1 Owner requirements (stated)
Workbench: Windows-style menu bar with dropdowns and popout submenus; left panels that hide/collapse; terminal pane with a CLI prompt at the bottom; lightweight custom IDE; numbered, highlightable lines; ergonomics for AI and tools to diff and amend quickly.
Look and feel: startup like an old PC (fake machine terminal boot), then an ASCII Pip-Boy loadup like FO4's, then a thumbs-up, then the UI. UI: high-definition "Overseer" black with gold/bronze trim (an Overseer-style Pip-Boy skin mod is a colour starting point only); lightweight modernised Pip-Boy that looks like old tech made futuristic/apocalyptic. Stretch: its own saved second desktop.
Launch: three ways (10.4). Two probe profiles for now (light, heavy), more modular later. In all three, PIP-MON and the Overseer come up; in plain gameplay they sit minimised in monitor mode; in debug/verbose the heavy profile runs with the UI, tools and suites under machine or AI protocol rules and guardrails.

### 10.2 Architecture that makes the three modes cheap: a daemon/UI split
The "minimised, lightweight" state is a PROCESS, not a window state. Proposal: three layers.
1. Probe (in game): vprobe.dll, profile-driven, writes to V-Link.
2. Daemon `pipmon serve` (always-on, no UI, tray icon): sole owner of the V-Link pipe (fixes U3 single-handle), fan-out to subscribers, bounded black-box recorder, verb executor with guardrails, project/env launcher. Idle target near 0% CPU and no rendering.
3. Clients: workbench UI, CLI, AI agent adapter, in-game cartridge request path (one-way, 9.10), HUD overlay. All speak the same verbs and envelope (Section 9).
Consequences: closing the UI never stops recording; crashes of the game leave daemon and recorder alive (matches the archive's "decoupled crash protection"); the UI can start on demand when the recorder flags something.

### 10.3 Probe profiles (contract, two for now)
| Profile | Purpose | Capture | Cost ceiling | Who consumes |
|---|---|---|---|---|
| LIGHT ("watch") | normal gameplay, back-end collection "enough to feed the heavy later" | minimal event schema: heartbeat, VM tick counts, VM exceptions, MOD_LOAD, SAVE_BLOAT, errors, log pointers; ring-buffered segments on disk with pre-roll around any anomaly | near-zero game-thread cost, no string work in probe (existing rule) | daemon/recorder, optional tray HUD at 1 Hz |
| HEAVY ("trace") | debugging/validating during play, semi-realtime | everything LIGHT plus thread state, stack frames/dumps, memory, plugin diag, higher sample rates, verbose trace | higher; accepted only when a human or an authorised agent escalated | workbench, detector, AI agent |
Rules: profiles are named capability sets with declared cost ceilings (extends 8.5); a profile is a version-stamped record both sides acknowledge (seq number in the control reply); future profiles are additions, not renumbering (same append-only rule as EventType).
Key design choice: install the full hook set at startup (dormant, gated by a flag/branch) so LIGHT to HEAVY is a hot switch over the control channel; ONLY when HEAVY needs a hook LIGHT never installed is a restart required. That is the honest rule for "restart like Bethesda does": restart only when the profile cannot be reached hot. Today's reality: Layer A hooks do not exist yet (A2), so profile switching is a contract to build toward; it can be exercised now only against tests/fake_probe.py.
"Feed the heavy later" = a bounded rolling recorder (size and age caps) plus `pipmon review <capture>` replaying a capture through the same detector the live HEAVY path uses.

### 10.4 The three launch modes
| Mode | Name | Start | Probe | Daemon | UI | Authority default |
|---|---|---|---|---|---|---|
| 1 | Watch | game started normally (Steam, Bethesda launcher, Vortex) | LIGHT | running, tray | minimised/absent; pops on anomaly | observe |
| 2 | Debug-live | game already running or starting | LIGHT escalated to HEAVY hot | running | up, tools and suites active | propose / apply-reversible per guardrail profile |
| 3 | Tandem | `pipmon open <project>` or platform-provider launch with PIP-MON as the gate | LIGHT at boot, escalation negotiated at main menu | running | up | per project guardrails |
Mode 3 sequence (proposal):
1. Resolve config (X1), run `doctor --depth 0`, snapshot plugins.txt and CK state (existing snapshot/ck-session machinery).
2. Open the project file: load-order profile, editor host, target environment, scripts, cartridges, probe profile, guardrails.
3. Start CK first with the curated profile (`ck-session prepare` exists), build and deploy project scripts (`script build`).
4. Start the game through the launcher using the platform-provider path; probe boots LIGHT and the daemon sets up normal monitoring/logging.
5. At main menu the UI shows HOLD and offers "Escalate to HEAVY". Daemon sends the profile, waits for the probe's ack and a sync check (capture started, pipe healthy, build identity matches). If hot escalation is impossible it relaunches via the launcher on the same provider path (10.5).
6. UI shows READY. Player starts or loads the game, or the project drops them into the target environment.
Why the environment is special: it is a COMPONENT AREA, not a compiled save (owner). Entry must therefore be repeatable and save-independent: the project file names a cell/area (the PipMonTestFacility cell is the existing candidate) and the entry method. How to enter a cell from main menu without a save (console `coc`, or a dedicated clean test save) is UNVERIFIED here; testfacility/ENV-SETUP.md and HANDOVER cover the facility, check them first.

### 10.5 "It waits until synced before you can start": feasibility, honestly
- A hard block of New/Continue/Load at the main menu requires a hook on the menu's start path = Layer A or an input-level interception. Neither exists. Until then the gate is ADVISORY: UI and tray say HOLD, the launcher can be the thing that starts the game only after pre-flight passes (that gate is real, because the launcher controls process start), and escalation at the main menu is reliable only if the probe and daemon are already in sync.
- Pre-game alternative that needs no hook: choose the profile BEFORE the game starts (launcher flag), so there is nothing to wait for. The owner's main-menu escalation can layer on top once hot switching exists.
- "Restart the Bethesda-native way": the game already prompts and relaunches after load-order changes in its Mods menu. Mimicking exactly how it does that (which process relaunches, via which provider) is UNVERIFIED; the safe build is: launcher closes the game, restores the load order snapshot if needed, relaunches via the same provider path it used the first time.

### 10.6 Guardrails and protocols (machine or AI rules)
Define one table of protocol profiles, enforced by the daemon, not by the client:
| Protocol | Who | May | May not |
|---|---|---|---|
| OBSERVE | tray HUD, any watcher | read status, logs, captures | any write |
| HUMAN | person at the workbench | all verbs, with confirm on irreversible | nothing blocked beyond existing refuse rules |
| ASSIST | AI agent beside a person | propose (edits, plans), apply reversible after approval or within a pre-approved allowlist | irreversible, writes outside workspace/Data allowlist |
| MACHINE | scripted/CI/headless | allowlisted reversible verbs, no prompts, exit codes only | anything needing human authority (exit 6) |
Cross-cutting: path-scoped writes; snapshot before every write; verify after every write with auto-rollback on failed verify; rate limits; every action carries actor, run_id and a Timeline entry (audit); one kill switch (daemon and probe control channel); refuse, do not guess, on unknown build identity (existing rule). The same table drives menu enable/disable in the UI, `caps.authority` in the CLI, and the cartridge request allowlist (9.10).

### 10.7 Workbench spec (lightweight custom IDE)
Chrome:
- Menu bar (Windows-style): File, Edit, Selection, View, Go, Run, Tools, Cartridges, Probes, Window, Help. Dropdowns with keyboard accelerators and popout submenus (e.g. Run > Verb > link > status/plan/apply; Probes > Profile > Light/Heavy). Menus are generated from `pipmon caps --json` plus a small static layout file, so a new verb appears without UI code.
- Side panels collapse to an icon rail (toggle shortcut, auto-hide with edge peek); panels can pop out into their own windows for a second monitor (archive: detachable/pinned HUD).
- Bottom panel tabs: Terminal, Output, Problems, Timeline. Terminal ends with a live `pipmon>` prompt: history, completion from caps, and `@` references to editor selections (e.g. `fix plan @PipMon.psc#L42-48`).
- Status bar: gates, game build, probe + profile, link state, daemon state, protocol (OBSERVE/HUMAN/ASSIST/MACHINE).
Editor (the part owner asked to be fast for AI and tools):
- Line numbers; click/drag in gutter selects a range; multiple highlight ranges, coloured by actor (person, AI, tool); gutter markers for findings anchored to lines.
- Line reference syntax: `path#L12-L18@<8-hex content hash of that range>`. Copyable from any selection; accepted by every CLI `edit` verb and by the AI adapter. The hash is a precondition: if the range changed, the edit is refused with a diff, never guessed (project principle).
- Edit verbs (NEW): `edit diff <a> <b>`; `edit propose <ref> --with <file|->` writes a proposal (.proposed + patch, mirroring ck_session's staging pattern); `edit list`; `edit apply <proposal-id> [--hunks 1,3]`; `edit reject`. Apply = snapshot, check base hash, atomic replace, run `script check`, auto-rollback if it fails. Proposals show as an inline diff with per-hunk accept/reject, each hunk labelled with actor and run_id.
- Efficiency: virtualised rendering; incremental diff; huge logs streamed with a line-offset index instead of loading whole files (Papyrus logs can be large); bounded live-event ring buffer in the UI; no rendering at all while minimised.
Toolkit decision (owner, unmade): requirements are custom menus, hi-def themed rendering, line gutter, diff view, small footprint, Windows-first. Options: (a) Tauri (Rust shell, system WebView2) + CodeMirror 6 (light editor core with line numbers, selections and a merge/diff extension; I believe this exists, not verified here); matches the existing Rust crate and gives full CSS control for the theme. (b) Native Rust (egui/iced): smallest runtime, weakest text-editor and diff widgets. (c) Qt/PySide6: mature widgets, large install, licence review needed. (d) Python Textual: already used by overseer_cli, but cannot do the hi-def trim and pixel-level theme, so it stays the secondary-monitor/headless view. My lean: (a) for the workbench, (d) kept as a fallback TUI. Decide before any UI code.

### 10.8 Look and feel
- Boot (proposal): REAL work happens during the animation so it is never dead time. Stage 1 fake-machine text (original ROBCO-flavoured but not copied) while the client runs `doctor --depth 0`, daemon handshake and config resolve. Stage 2 ASCII Pip-Boy loadup. Stage 3 thumbs-up ONLY when boot checks pass; otherwise a different frame that names the failing check. Skippable (any key; `--no-boot`), capped length (a few seconds), and silent/static for reduced-motion.
- Palette (tokens, my proposal, sampled from no one): background near-black warm `#0B0A08`; panel `#14120E`; raised `#1B1812`; bronze trim `#8C6B2F`; gold `#C9A24A`; highlight `#E6C46A`; text `#D8CBA8`; dim text `#8A7F66`; OK green `#7FB069`; warn orange `#D98A2B`; error red `#C8503C`; info steel `#6FA3B8`. Gold carries focus and selection; status colours stay separate from gold so a warning never looks like a selection. Check contrast on the real screen.
- Shape: chamfered corners, thin bronze trim lines, segmented meters, monospace for data and a condensed sans for headings, subtle optional scanlines/glow (off by default; honour reduced motion). "Old tech, futuristic UI" comes from the contrast of cut corners and thin trim, not from heavy effects.
- Licensing caution (important): owner believes the FO4 boot content exists in several repos and is free to use in mods. Two separate questions: (1) the repos' licences, which differ and must be read per repo; (2) Bethesda's rules for reusing game assets, which for FO4 are the Creation Kit terms covering MODS for the game. PIP-MON's workbench is a standalone program, not a mod, so those mod permissions may not cover it. Pip-Boy, Vault Boy, ROBCO and the thumbs-up are Bethesda trademarks/art. Safe path: ship original art and text in the style; optionally load the user's own copy of game assets at runtime from their install without redistributing; get a read of the CK EULA and each repo licence before shipping anything copied. Not legal advice.

### 10.9 Second desktop ("its own saved desktop")
Checked: Microsoft's documented IVirtualDesktopManager has three methods (is window on current desktop, get a window's desktop id, move a window to a desktop). Creating or switching desktops goes through undocumented interfaces whose class IDs change between Windows builds; community wrappers exist and need per-build care. Microsoft's guidance also says only the user should change the active desktop. Recommendation: first build a window-layout profile (saved positions per monitor, restore on launch, pin the HUD to the secondary monitor); treat true virtual-desktop creation as an optional best-effort module behind a capability check that falls back silently; never required for any workflow.

### 10.10 Project file (new concept)
`pipmon.project.json` (proposal): name; load-order profile ref (snapshot id or plugin list); editor host (CK); scripts roots; target environment (cell/area + entry method); cartridges to build/deploy; probe profile; protocol/guardrail level; boot options; window layout. `pipmon open <project>` implements 10.4 mode 3. The existing create_environment plan and ck_session are the building blocks; the project file is what makes them one user-facing thing.

### 10.11 New findings from this brief
- PS1: Three launch modes are described but not modelled anywhere in code or spec; no profile concept in V-Link (add profile id + ack to the protocol, append-only).
- PS2: Hard main-menu gate impossible until Layer A (10.5); advisory gate and pre-game profile choice are what can be built now.
- PS3: Daemon/UI split not designed in repo; today overseer_cli is both. Needed for minimised monitoring and for U3.
- PS4: Recorder and `review` replay path do not exist.
- PS5: Boot-art provenance and trademark question unresolved (10.8).
- PS6: UI toolkit undecided (10.7); VS Code extension lean withdrawn.
- PS7: Virtual-desktop feature depends on undocumented Windows interfaces (10.9).
- PS8: Edit/ref/hunk contract for fast AI and tool amendments does not exist (10.7).
- PS9: Project file concept absent (10.10).
- PS10: Theme tokens not defined anywhere (10.8).

### 10.12 Correction (Session 1e): the launcher already IS the "pause"; it replaces F4SE's loader
Owner: "we're replacing F4SE but similar idea, it's scripted entry." Confirmed by reading launcher/src/ProcessLaunch.cpp (473 lines, written to the same pattern as F4SE's loader):
1. `CreateProcessW(..., CREATE_SUSPENDED, ...)`: game main thread is held at zero.
2. Verify build identity against the suspended image (image base read from the PEB via NtQueryInformationProcess: measured relocated base 0x7ff6c38c0000, not 0x140000000; Toolhelp module walk fails with error 299 on a suspended process).
3. Inject one known DLL by path: VirtualAllocEx + WriteProcessMemory + `CreateRemoteThread(LoadLibraryW)`; wait for the loader thread (30 s cap).
4. The runtime's DllMain runs now, before the game executes an instruction; parent-created named events ("loaded", "ready") exist BEFORE spawn so DllMain can open them.
5. `ResumeThread`, THEN handshake: "loaded" fatal on timeout; "ready" may legitimately never arrive pre-game (probes cannot resolve without a game module) and is reported as Degraded, not failure. CLI flags today: `--timeout-ms N`, `--no-wait`, `-- game args`, `--self-test`. Teardown of a suspended process is TerminateProcess.
Consequences for sections 10.4/10.5 (these supersede the "advisory only" wording):
- A HARD pre-game gate is feasible NOW with no Layer A: insert a HOLD between step 4 and step 5. The process is suspended and injected; the launcher does not call ResumeThread until a third event, `synced`, is set by the daemon. While held, the daemon can: pick the probe profile (from the project file or a UI prompt), set capture directories, take the plugins.txt/CK snapshot, start the recorder, and verify build identity. This is the real "wait until synced before it lets you start the game", at process start instead of at the main menu.
- Scripted entry: every launch mode goes through the launcher via the daemon: `pipmon open <project>` (mode 3), `pipmon launch --profile light|heavy` (modes 1 and 2). Proposed launcher flags: `--profile <id>`, `--hold` (wait for the `synced` event before Resume, with a timeout and a "give up and run vanilla" fallback), `--sync-event <name>`, `--capture-dir <path>`. Profile id is passed to the DLL through an environment variable or named shared section set before spawn (DllMain can read it while suspended).
- Main-menu escalation stays a different problem: after Resume, a hard block needs a hook; but a main-menu escalation can now be implemented as hot switch (profile seq + ack over the control channel) or, when a missing hook is needed, as relaunch through the same launcher path (TerminateProcess + relaunch with `--profile heavy`). That relaunch is what the owner means by restarting like Bethesda does, and it needs no knowledge of the game's own restart mechanism.
- Dormant-hook idea (10.3) needs one check: whether detours can be installed in the suspended window (image base is known via PEB, but the module list and imports are not walkable pre-entry). Most likely hooks still install after the game module resolves post-resume, so "install all hooks at startup, gate by flag" still holds, just a little after Resume. UNVERIFIED.
- If the game is started from Steam/Bethesda launcher WITHOUT our launcher, no injection happens and there is no probe. Platform-provider starts therefore need a stub path: the project/launcher registers itself as the start target (shortcut or Steam launch option), or a proxy DLL entry (the repo mentions dinput only in BuildIdentity.cpp and the design doc; I did not find a built proxy path). Decide how "started from Steam" modes 1 and 2 get the probe.
Open risk that touches ALL modes: COVERAGE.md says the injection crash "has been reproduced five times on a heavily modded install and never once diagnosed"; clean/stripped install testing is listed as the cheapest way to isolate it. Until that is resolved, Watch mode on the owner's modded install is unproven and could crash the game. Highest-value measurement before any of the UI work.
Note: ENV-SETUP.md still says "launch through f4se_loader.exe" for the facility; the replacement direction is our launcher, so ENV-SETUP and the facility instructions need updating when the new entry is ready.
New findings: PS11 (H) injection crash on modded install, undiagnosed, blocks all modes; PS12 (M) launcher resumes immediately after inject, no HOLD/synced event, no --profile; PS13 (M) no plan for how Steam/Bethesda-launcher starts get the probe; PS14 (L) ENV-SETUP still routes through f4se_loader.
