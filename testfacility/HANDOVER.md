# HANDOVER — PIP-MON test facility

Written at the end of a session that ran out of context. Everything here is on
disk; nothing needs rediscovering. Read this first, then `testfacility/COVERAGE.md`
and `testfacility/FACILITY-SPEC.md`.

---

## 1. Mission

PIP-MON is an injection-based runtime for Fallout 4. It is being validated
against a purpose-built test environment that exercises the game's components
and produces state changes PIP-MON can be measured against.

The environment is a bunker-style player home (underground, per-room lighting and
ambient sound, blast doors, workshop, lab, power armour). The design language
comes from Nexus mod `27466` — Cotozic's Bunker Ravine Player Home. **Its assets
and records are a reference only. Nothing is copied from it.** No `.esp`, no
`.ba2`, no meshes, textures, scripts, cells or records. Only the environmental
*variables* are borrowed.

Optional visual vocabulary, not a dependency: Prydwen Build Kit, Nexus `70726`.

---

## 2. Do not repeat these mistakes

This session's failures, so the next one doesn't repeat them:

- **Do not launch the game to "test the environment."** The environment is built
  in the Creation Kit / xEdit. Launching `Fallout4.exe` was wrong and was undone.
- **Do not drive the GUI.** The CK is a native app with no scriptable interface
  here. Anything that sends keystrokes fights the user for the keyboard. Say so
  once and move to a headless tool.
- **The CK showing no Worldspaces is expected** until data is loaded. It is not
  a broken install and not a reason to reinstall anything.
- **Do not connect a pipe client to an injected runtime on the modded install.**
  That combination crashed the game five times. Injection + file read only.
- **Do not re-derive the Papyrus language constraints in section 4.** They were
  established by compiling probes against the real compiler. Trust them.
- **Do not use gated compound commands** — the user may be in-game and cannot
  approve prompts. One purpose per command, and read files with Read.

---

## 3. Environment facts

| | |
|---|---|
| Game | `C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Fallout4.exe` |
| Game build | `1.11.240.0` |
| CK | `...\Fallout 4\CreationKit.exe`, `1.11.240.0` — exact build match |
| CKPE | **absent** (Nexus `51165`). Without it the CK render-crashes on larger cells. |
| F4SE | `0.7.9` |
| Mod manager | Vortex, 200+ mods active in the main install |
| Repo | `C:\Users\Administrator\Desktop\Pip-mon Script Management system` |
| Git | branch `master`, **no remote**. Local commits only; the user has asked for local commits, not pushes. |

GECK is Fallout 3 / New Vegas only. Fallout 4 has no GECK. Use the CK, or xEdit.

---

## 4. Papyrus language constraints — compile-probed, do not re-derive

Established by compiling probes with the real FO4 compiler. These are facts, not
guesses.

**Cross-script calls** use dot syntax: `PipMon.GetVersion()`. Not
`PipMon_GetVersion()`.

**Rejected — do not write these:**

| Attempted | Result |
|---|---|
| `Menu`, `Option` types | rejected |
| `OnActivate`, `OnMenuClose`, `OnAddToMenu`, `OnMenuClick` | rejected |
| `OnStart`, `OnQuestInit`, `OnEnd`, `OnStageChanged` | rejected |
| `GetLength`, `GetSize`, `Count`, `Size` | rejected — no array-length intrinsic |
| `CreateObjectAtForm` | rejected |

**Accepted:**

- `Event OnInit()` on a normal script
- `Event OnTimer(float afTimeInSeconds, ObjectReference akObjRef, Actor akActor, String asEventType)` on a quest script
- `auto readonly` properties (requires `papyrus_flags.flg`)
- plain script variables

**Consequence for the quest design:** stage changes are detected by polling
`GetStage()` from `OnTimer` with a stored `lastStage` guard, so each stage is
handled exactly once. There is no event to subscribe to. A probe file that
declared `OnTimer` twice ended with `script event ontimer already defined in the
same state` — that error was an artifact of the probe, not a language limit.

---

## 5. Committed work

All on `master`, all building green.

| Commit | Contents |
|---|---|
| `4d8f678` | RTTI ground-truth tooling; 18 sourced vtable targets; `tools/measure_vtable.py` with 15 self-tests; corrected slot counts including `IClientVM = 3`; vtable drift gate in `build_all.bat` |
| `c9adb5a` | `PipMonTestFacility.psc` — first project script against the native surface |
| `2c78347` | default test-character setup; corrected environment build guide |
| `ba230f5` | 15-slot roster — 10 NPCs, 2 robots, 2 synths, 1 merchant; native AI activation via `EvaluatePackage(true)` + `EnableAI(true)`; teardown removes **only** what was placed, via stored placed-actor properties |
| `171b3ea` | file-based trace and session telemetry; periodic producers gated on a connected client |
| `7d113d6` | lifecycle phase reports `UNKNOWN` rather than falsely claiming `MENU` when no frame source exists |

**Last full green build:** vprobe `15 pass / 0 fail / 2 skip`; both PEX images
valid; launcher `45`; Python `67`; Rust `5`.

**Deployed to the game and verified:**
- `Data\Scripts\PipMon.pex` — 990 B, valid PEX magic
- `Data\Scripts\PipMonTestFacility.pex` — 11,790 B, valid PEX magic
- `Data\PIP-MON\libs\vprobe.addresses.txt` — 541,674 B
- `Data\PIP-MON\libs\vprobe.addresses.bin` — 103,428 B

The address database was **absent in every prior live run**, so the resolver had
been silently falling back to its embedded dump. The first real live test is
therefore the first run on the intended path. This matters for interpreting any
result.

---

## 6. Live findings, and the one open failure

- `Runtime ready: 18/18 probes resolved` — the native surface resolves.
- **V-Link pipe crashes and injection crashes are unresolved.** Reproduced five
  times on the modded install, never diagnosed, because the install is too dirty
  to isolate a variable.

That is the core reason for wanting a clean install. It is a measurement
problem, not a code problem, and more logging on a dirty install cannot fix it.

The crash mitigation already landed in `171b3ea`: with **no client attached** the
periodic producers (heartbeat, memory, thread enumeration) do not run. The worker
loop reduces to a `GetQueuedCompletionStatus` with a 50 ms timeout. Injection
plus reading the session log file is therefore near-inert and is the intended
way to test.

---

## 7. Test facility — what is written

| File | Purpose |
|---|---|
| `testfacility/ENV-SETUP.md` | toolchain, what is installed, what is missing |
| `testfacility/FACILITY-SPEC.md` | bunker environmental variables, room-by-room lighting and sound, NPC placement, blast-door buttons, non-settlement surface workshop, two terminals, roster spawn point, 15-slot roster table, property table |
| `testfacility/QUEST-SPEC.md` | 9-stage quest ladder, driven by game actions not by script, each stage mapped to an interactive object, `OnTimer` polling design |
| `testfacility/COVERAGE.md` | component coverage matrix — what is testable and what is not, and why |
| `testfacility/ck/README.md` | short CK session checklist and property-assignment order |
| `testfacility/ck/verify_deploy.ps1` | deployment verifier |

`verify_deploy.ps1` currently reports **2 failures**, both expected:
`PipMonTestFacility` plugin not yet generated, and CKPE absent. Everything else
is green.

### Staged CK workspace

`testfacility/ck/PipMonTestFacility/` exists with the full plugin folder layout
(`Scripts`, `Exporters`, `Textures`, `Sound`, `Meshes`, `Video`, `Materials`)
and both `.pex` files in `Scripts\`. It is ready to become the active plugin.

---

## 8. Coverage — the shape of it

Each row tests two things: does the game behave, and does PIP-MON see it. A row
where the game works but we report nothing is a **PIP-MON bug, not a quiet pass**.

Groups: core loop (quest, lifecycle, natives, save/load, objectives); actors
(NPCs, robots, synths, factions, dialogue, companions, death, merchant); items
(pickup, containers, three bench types, cooking, weight, scrap); power armour
(station, frame, HUD, exit/re-enter); combat (melee, ranged, damage, reset,
health, VATS); world (cell load/unload, fast travel, doors, multi-cell,
streaming); world systems (lighting, sound, weather, time, sleep); Pip-Boy and
UI (inventory, terminals, workshop, holotape, map, photo mode, menus).

Two rows carry unusual weight:

- **Save / load.** Every test environment skips it and it is what breaks real
  users first. A verdict stored in a property that does not survive a reload
  makes everything else decoration.
- **Cell transition (stage 8).** Leave and re-enter. The only stage that proves
  the runtime survives a cell load, which is exactly where a real hook breaks.

### Not coverable here, stated so it is not discovered later

Main-quest and radiant progression (needs a played save with a quest log);
Creation Club content; mod interactions at scale; controller input, VR,
localisation.

### The two-environment argument

One facility cannot answer both "is PIP-MON correct" and "does PIP-MON survive a
real load". This facility answers correctness. A stripped install — vanilla plus
F4SE only — answers whether injection works at all. The crash in section 6 has
never been isolated precisely because the install is too dirty to isolate it.
That is the cheapest path to turning it into a measurement.

---

## 9. xEdit — the headless route, already obtained

This is the way to build the plugin without a GUI.

- `xEdit 4.1.5f` downloaded and extracted to
  `C:\Users\ADMINI~1\AppData\Local\Temp\opencode\xedit\x`
- **`xFOEdit64.exe`** (34.8 MB) is the Fallout 4 editor. Also present:
  `xDump64.exe`, `BSArch*.exe`, `LODGenx64.exe`, `Texconvx64.exe`.
- 7-Zip is at `C:\Program Files\7-Zip\7z.exe`.
- Note the executable is `xFOEdit64.exe`, not `FO4Edit.exe`. A search for
  `FO4Edit.exe` returns nothing and that is not a missing install.

The download URL that works:
`https://github.com/TES5Edit/TES5Edit/releases/download/xedit-4.1.5f/xEdit.4.1.5f.7z`

The GitHub **API** returns 404 for several plausible owner/repo spellings
including `Nukem9/TES5Edit`. The correct one is `TES5Edit/TES5Edit`, and the
direct download URL works even where the API does not. Don't burn turns on the
API.

### Load policy, decided deliberately

Load **`Fallout4.esm` only**, no mods, no DLC if memory is tight. Two reasons:
the facility is built on vanilla so it is reproducible, and it keeps the plugin
independent of the 200+ mod load. If the machine cannot free memory for a
masterless load, fall back to `Fallout4.esm` + DLC.

xEdit reads the active module list from `%AppData%\Vortex\Fallout 4\mods.txt`, so
that file may need attention before a scripted run.

---

## 10. Next actions, in order

1. **Confirm xEdit can load the game headlessly.** Cheapest possible probe: load
   `Fallout4.esm` with `-auto -quickexit -nosplash` and exit cleanly. Establishes
   that xEdit runs against this install at all before any script complexity.
2. **Write an xEdit script that generates `PipMonTestFacility.esp`:**
   - a CELL, placed
   - a terminal carrying `PipMonTestFacility`, with the property values from
     `FACILITY-SPEC.md`
   - a weapon bench, an armour bench, a power armour station
   - light switches, blast-door buttons, sound zones per room
   - the 15-slot roster
3. **Run it with `-script=... -auto -quickexit`**, then verify with
   `testfacility/ck/verify_deploy.ps1`. The plugin check should flip to green.
4. **Only then open the CK.** The Worldspace will already exist, so the CK
   session is inspection and adjustment rather than construction.
5. **Commit locally** — the CK specs are not yet committed. Check `git status`
   first; the committed tree was clean at `7d113d6` plus the new `testfacility/`
   work.
6. **Live validation** follows the section 6 rule: inject, read the session log,
   never attach a pipe client.

---

## 11. Key paths

```
repo            C:\Users\Administrator\Desktop\Pip-mon Script Management system
facility spec   testfacility\FACILITY-SPEC.md
quest spec      testfacility\QUEST-SPEC.md
coverage        testfacility\COVERAGE.md
ck workspace    testfacility\ck\PipMonTestFacility\
verifier        testfacility\ck\verify_deploy.ps1
facility script vprobe\papyrus\PipMonTestFacility.psc
papyrus build   vprobe\papyrus\build_papyrus.bat   (compiles PipMon first, then facility)
papyrus flags   vprobe\papyrus\papyrus_flags.flg    (required for auto readonly)
full gate       build_all.bat
telemetry       vprobe\include\Trace.hpp
gating          vprobe\src\IPCServer.cpp
editor          C:\Users\ADMINI~1\AppData\Local\Temp\opencode\xedit\x\xFOEdit64.exe
```

`PipMonTestFacility.pex` in `vprobe\papyrus\build\` is current and already
deployed. **Do not rebuild it for the CK** — the deployed build is the one the
plugin should reference.

---

## 12. Session stop — validator rework, UNVERIFIED (read before running anything)

This session was stopped by the user for changing too much without evidence.
The tree was committed in this state. **Nothing below has been run.**

### 12.1 Stop and read this first

- **Do not launch xEdit yet.** The validator has never produced a report.
- Two edits to `tools/validate_plugin.ps1` are **unverified and one is incomplete**
  (see 12.4). Treat both as suspect.
- The last live xEdit run **failed**. There is no passing run to build on.

### 12.2 What the last run actually proved

Good news, from `%LOCALAPPDATA%\Temp\opencode\xedit\x\FO4Script_log.txt`:

- Background loader **finished at `00:11`** — the loader path works.
- The script **started and reached `Finalize`**.
- It then failed at `02:17`:

```
[EJvInterpreterError] Error in unit 'UserScript' on line 97 : Undeclared Identifier 'AssignFile'
[02:17] Aborted: Applying script "validate_plugin.gen"
```

So: loader works, script engine works, `SaveToFile`-style reporting is the only
unknown left. That is a much better position than "xEdit does not work".

### 12.3 xEdit API facts — measured, do not re-derive

| Call | Status |
|---|---|
| `GetPluginName` | **does not exist** in 4.1.5f — aborted a run |
| `AssignFile` / `Rewrite` / `WriteLn` / `CloseFile` | **undeclared** — aborted a run |
| `TStringList.SaveToFile` | documented; use this for all report output |
| `AddMessage` | documented; appears in the xEdit log, not stdout |
| `GetFile`, `GetFileName`, `FileCount`, `FileByIndex` | documented, common |
| `MasterCount`, `MasterByIndex` | documented |
| `Signature` | proven by execution |

- **Hidden windows stall** at `Loading active plugin list`. Only visible mode is
  proven. `validate_plugin.ps1` now launches visibly.
- `AddNewFileName`/`AddNewFile` **create a new plugin**; do not call them to reach
  an existing one.
- `AddElement` throws if already parented; `Add` is the idempotent create-or-get.

### 12.4 Unverified / incomplete edits — the danger zone

`tools/validate_plugin.ps1`:

1. **Added** regex substitution that rewrites the two `// GENERATOR`-marked lines
   in the `.pas` template (`targetName`, `reportPath`). Needed because the new
   template carries readable literal defaults instead of `%%OUTPATH%%` /
   `%%PLUGIN%%`. **Never executed — unverified.**
2. **Added a `-GenOnly` switch to the param block with no handler.** It is a
   declared-but-unimplemented no-op. There is currently **no** way to generate the
   `.gen.pas` without launching xEdit. Finishing this was the next task.

Because of (2), the only way to produce a `.gen.pas` is a real xEdit launch. Fix
that before spending a 2–3 minute load.

### 12.5 The validator now on disk

`testfacility/xedit/validate_plugin.pas` (5,222 bytes) — authored as a correction
of an earlier, wrongly-scoped version that inventoried all ~135K records in the
load order. It now does **one job**: validate the target plugin.

- Filters records to the target via `GetFile`/`GetFileName`.
- Emits real JSON (`schema pipmon.plugin.validation/4`).
- Ends with an explicit `verdict`:
  - `SKIP` — target not in the load order (never collapsed into PASS)
  - `FAIL` — target loaded but header-only, or has records and no `CELL`
  - `PASS` — target loaded, records parse, at least one `CELL`; semantics unchecked
- Also reports per-signature counts, `masters`, `master_names`, and a
  `not_checked` list.

Expected first result, given the plugin is currently 66 B / 0 records:
**`FAIL` — "target plugin is header-only: 0 records"**. That is the correct,
honest blocker, not a harness bug.

Risk to watch on first run: `StrToInt` and `sigs.IndexOf` are used in the
signature histogram. If either is undeclared, the fix is to drop the histogram,
not to re-add file I/O.

### 12.6 Measured plugin facts

- `Data\PipMonTestFacility.esp` — **66 bytes**, CRC32 `E1DD5E4D`, **0 records**.
- FO4 TES4/record header is **24 bytes**; `dataSize=42`; `24 + 42 = 66`.
- `tools/make_empty_esp.py` was corrected 16 → 24 bytes and its off-by-eight body
  offset fixed. Subrecord parsing beyond `HEDR` is still untrusted.
- The 973-byte version is **only a backup**:
  `runs\tasks\facility-v0\snapshots\PRIOR-WORK-973B.esp`.
- `ai_state_dashboard.md` still claims 973 B and is **stale**. Regeneration was
  aborted. `tools/factcheck.py` correctly flags this.

### 12.7 Safe order of work from here

1. Implement the `-GenOnly` handler; generate `validate_plugin.gen.pas`; **diff it
   by eye** before any xEdit launch. Confirm `reportPath` points at
   `runs\watch\xedit-validation-report.json` and no absolute path leaked in.
2. Only then run `tools\validate_plugin.ps1 -Async`, **detached**, visible, and
   return immediately. Collect in a **separate** call. Never `Start-Sleep`.
3. Expect `FAIL / header-only`. Record it, do not treat it as a harness failure.
4. Then, and only then, move to cell creation — still blocked on a documented
   top-level group-by-label call and `TwbVector` construction.

### 12.8 Standing process rules

- **Never** run a long third-party process inside a blocking tool call.
- **Never** use `Start-Sleep` to monitor; poll in separate short calls.
- **Never** claim a process is running from a cached job file — check the live
  process. A stale job file caused a false "still running" report this session
  after the user had already killed it.
- **Never** claim a file/record count from memory. Re-measure or say unknown.
- Do not touch `tools/*.py`, specs, or the RAG while an xEdit run is in flight.
