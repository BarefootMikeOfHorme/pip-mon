# PIP-MON Evaluation Notes (single running document)

Repo: https://github.com/BarefootMikeOfHorme/pip-mon (main @ e05dd7a RESUME.md, 23 commits, 371 files, cloned shallow 2026-10-01; earlier notes were against da52ad4)
Owner framing: "A script management system first; the rest is bells and whistles."
Revise THIS file each session. Do not create new versions.

## 0. STATE CARD (read this first; everything below is detail)

**Subject:** github.com/BarefootMikeOfHorme/pip-mon, evaluated at main e05dd7a (371 files). Owner: "script management system first; the rest is bells and whistles."
**Owner facts:** repo is public only for this eval; licence undecided (GitHub would not take PolyForm); some gate blockers fixed locally but NOT pushed, so every "gate red" below is "as of GitHub main".
**Progress:** Pass 1 done (skim). Pass 2 partial (design doc s1, s6, s14, s18). Pass 3 partial (linksync, build_papyrus.bat, validate_plugin, pipmon validate, orchestrate.py, create_environment plan). Passes 4-6 not started. Nothing was executed; all findings are from reading.
**Thesis (what I believe so far):** most of the real, gated investment IS script management (tools/ ~13k lines vs native runtime ~7k). `pipmon.ps1` is already a good product surface. The native runtime (Layer A hook) is unproven and is a separate, larger track. The best unbuilt, best-justified feature is the provider registry (design s18).
**Top 6 findings by impact:**
1. B1: the Papyrus build is a hard-coded list of 6 own scripts, not a general script manager (the core gap).
2. X1: no single config; FO4/plugins.txt/xEdit/stage paths hard-coded and divergent across .bat/.ps1/.py.
3. L1/L3/L5: linksync round-trips through ASCII, has a read-modify-write race with Vortex/CK, and never checks masters.
4. V1/V2/V3: `pipmon validate` can report a stale verdict, cannot run async, and exit codes mean different things in two tools.
5. O1/O3: orchestrator splits commands on spaces (paths contain spaces); P4 has the wall gate AND a 60 s poll budget vs a measured 102 s run (second part unconfirmed).
6. D-series: documentation drift (README stub, stale handover/dashboard/comments, licence unrecorded in the design doc).
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
| X1 | H | No single config resolver | OPEN (roadmap 2) |
| X2 | M | Three languages share loose JSON/exit codes; no enforced envelope | OPEN (roadmap 3) |
| X3 | L | Lessons live in code comments that go stale | OPEN |

Severity is my judgement from reading, not from running anything.

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

## 6. Resume block (paste into a new window with this file)

"Continue the pip-mon evaluation using PIPMON_EVAL_NOTES.md. Read section 0 first. Clone with git (github.com is reachable from the sandbox; pull for new commits). Next: finish Pass 3 per section 7, then Pass 2 remainder. Revise the notes file in place; do not create new versions. Warn me when context is getting heavy."

## 7. Session log

- Session 1 (2026-10-01): Pass 1 (skim), Pass 2 partial (s1, s6, s14, s18, outline), Pass 3 partial (see 2e). Cloned da52ad4, pulled e05dd7a. Owner clarified: repo public only for eval; licence undecided; some gate blockers fixed locally but unpushed. Compaction/realign done at end of session 1 (see section 0). Corrected P3 after re-verification.
- Next window: finish Pass 3 (taskrun.ps1, artifact_gate.py, gen_papyrus_ref.py, ck_session.ps1, run_gen.ps1, rest of orchestrate.py), then Pass 2 remainder, then 4-6.
