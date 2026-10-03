# PIP-MON Evaluation Notes (single running document)

Repo: https://github.com/BarefootMikeOfHorme/pip-mon (main @ e05dd7a RESUME.md, 23 commits, 371 files, cloned shallow 2026-10-01; earlier notes were against da52ad4)
Owner framing: "A script management system first; the rest is bells and whistles."
Revise THIS file each session. Do not create new versions.

## Status

| Pass | Scope | State |
|---|---|---|
| 1 | Repo shape, inspiration archive (core files), README, both HANDOVERs, ai_state_dashboard, FRONT-LIST, FIX-BACKLOG, POSITIONING (head), pipmon.ps1 outline | DONE (skim depth) |
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
P3. Validator blind spot (FIX-BACKLOG A): validate_plugin.ps1 reads three logs but not xFOEdit64Exception.log, where the real cause lives. Silent-failure class, third occurrence.
P4. Orchestrator has no checkpoint/resume, discards gate output (FIX-BACKLOG E1, E2).
P5. Backup/stray files committed: `tools/rag_query.py.bak-unicodefix`; commit 3746bcf "Stop excluding session backups".
P6. Stage-2 cost: xEdit loads the entire active load order (~2m15s for 61 plugins) even for one plugin. Undecided (scratch Data folder vs plugins.txt swap vs accept).
P7. Windows-only, hardcoded-path tooling (.bat/.ps1). Acceptable for the target, but nothing is portable or CI-able; no GitHub Actions evident.

### Risk
R1. Vendored third-party code in a PolyForm-licensed public repo: ai_context/systems/F4SE-Plugins (20 files), ckpe/verbatim (15), pyo3 (15), ba2_format/verbatim, mxpf, xEditScripts. HANDOVER says "nothing proprietary" but that was verified at 115 files. Re-audit each upstream licence (pass 5).
R2. Process-injection plus detour engine into a shipping game: failure mode is a crash with no symptom. The project's refuse-do-not-guess rules are the right mitigation; keep them.
R3. Documentation volume (213 KB design doc, 96 md) versus a blank README: onboarding cost is high and drift is already measured.


## 2b. Pass 2 findings (design doc, partial)

S1. "Script management" is the END STATE, not the current build. Design doc roadmap Tier 2 / POSITIONING phase D: "A user installs PIP-MON and needs nothing else for papyrus instrumentation, a script console, and script management." Phases: A dual load, B own plugin loading + own Papyrus host, C own command/script API, D extender no longer required. So the owner's "script management first" matches the destination, but today's working code is Phase-A-adjacent tooling.
S2. Doc numbering is broken: sections run 1-14, 18-25, then 24.8, then 15-17 appended later ("added from 1moreideas.txt"). Section 24.8 sits after 25. Fix when the DOCS DOOR is built.
S3. The design doc has two real script-management designs not yet built: s6.2 two-pane CLI (`compile <file>`, `sort`, `exec`, `kill`) with Caprica build pipeline, and s18 provider registry (probe / enabledSet / disagreements across Bethesda, F4SE, Vortex, MO2, FOMOD; read-only providers; a published survey manifest). s18 is marked "nothing built yet" and is the best-justified feature in the repo: it came from a measured failure (Vortex state deleted, 65 enabled vs 0 deployed). Strong candidate for the real spine.
S4. s6.4 log object model (raw text, path, line/col, FormID) and s6.7 dedup (hash, collapse above 50/s) are sound and cheap; check whether overseer_cli implements them (pass 4).
S5. Inspiration archive is a prompt-to-design lineage: "pip-mon prompt.txt" (original 3-part monitor spec, CommonLibF4 + CBOR assumptions) was superseded by the measured design (no CommonLib linked, own wire format, KERNEL32-only imports). Good evidence the project self-corrects; "updated ideas.txt" lists libraries (Mutagen, esplugin, Champollion, minidump, zerocopy, Capstone) of which only capstone/pefile are adopted per HANDOVER s7.

## 2c. Tier notes, S1 continued

OWNER UPDATE (S1): some of the gate blockers listed in 2/P1-P3 were fixed after the last push. GitHub copy may lag local. Treat P1-P3, D4, D5 as "as of GitHub main (da52ad4)"; re-verify against a fresh push before reporting them as current.

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

## 2d. Owner clarifications (S1)

- Repo is public ONLY so it can be evaluated. Public push is not a design decision; G10 is not violated in spirit. D1 (public/remote mismatch) downgraded to "handover text is stale".
- Licence is unsettled: GitHub would not take PolyForm, so another licence must be chosen. D3 and design-doc s14 Q5 (MIT) both stay open until chosen. Practical note: a LICENSE file with any text can be committed by hand; GitHub only fails to auto-classify it (shows as unrecognised). Also: before choosing, re-audit vendored third-party code under ai_context (R1), since it constrains what licence the repo can carry.
- Gate blockers partly fixed locally since last push (see 2c).

## 2e. Pass 3 findings: the script-management code (S1)

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

## 5. Proposed roadmap (draft, to be revised after passes 2-5)

1. Land an honest README + one DOCS DOOR index (what is true, what is not, which doc answers what). Fix D1-D4 in one commit.
2. Fix validator visibility (read xFOEdit64Exception.log; separate compile error from missing report) and replace the P4 wall gate.
3. Make `pipmon.ps1` the declared product surface for script management; give orchestrate.py checkpoint/resume and keep gate output.
4. Remove committed generated and backup files; add CI that runs the gates that do not need the game.
5. Only then pursue Layer A / S0 with a real BSScript declaration source (libxse/commonlibf4), as a separate track.

## 6. Resume block (paste into a new window with this file)

"Continue the pip-mon evaluation using PIPMON_EVAL_NOTES.md. Clone with git (github.com is reachable from the sandbox). Start Pass 2: read PIP-MON_CONSOLIDATED.txt in sections, update the notes file in place."

## 7. Session log

- 2026-10-01 S1 (cont): Pass 3 partial (see 2e). Pulled e05dd7a. Next window: finish pass 3 (taskrun.ps1, artifact_gate.py, gen_papyrus_ref.py, ck_session.ps1, run_gen.ps1, rest of orchestrate.py), then pass 2 remainder, then 4-6.\n- 2026-10-01 S1: Pass 1 complete at skim depth; Pass 2 started (outline, s6, s18, roadmap). Pass 2 continued (s1, s14), LOC sizing, pipmon.ps1 header. Not yet read: most of consolidated design doc, any C++/Python/PS source, most inspiration files (only prompt + updated ideas read), docs/*, tasks/*.json, ai_context/spec.
