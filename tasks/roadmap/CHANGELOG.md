# Roadmap changelog

Append-only. One entry per task, newest last. Every entry names the commit, so
`git show <sha>` is the authority and this file is the index.

Rule source: [`VERSIONING.md`](VERSIONING.md).

---

## R0 — baseline and rules

### `1344d4d` — BASELINE: 14 untracked files preserved

**Change class:** neither. A baseline is not a change.

14 files existed untracked and were one accidental clean away from being lost
when the session crashed. Committed verbatim, not modified.

- The four `PIPMON_EVAL_NOTES*.md` and `PIPMON_startup_and_workbench_concept.html`
- `ai_context/COMENDIUM_STATE.md`, `f4se_prohibition.md`, `cre_boundary.md`,
  `cre_weather.md`, `cotosbunker.md`, `tparadise.md`
- `tools/fo4_watch.py`
- `testfacility/xedit/out/PipMonTestFacility.probe.esp`

**VERIFIED:** that these files existed and what bytes they contain.

**NOT VERIFIED:** any claim inside them. The eval notes say so themselves —
*"Nothing was executed; all findings are from reading."* Four of the six
environment subjects are `SKELETON` status.

**Known duplicates, kept not deleted:** `PIPMON_EVAL_NOTES1.md` is byte-identical
to `PIPMON_EVAL_NOTES.md`, both 21,707 B. Retained under the no-deletions rule.

**Superseded path, kept not erased:** `PipMonTestFacility.probe.esp`. Commit
`1a61a21` moved the CELL write into the testfacility plugin because the
`.probe.esp` copy was a dead end. Retained as evidence of that decision.

**Cost:** 14 files, ~0.4 MB, no code touched.

---

## Corrections to the inherited picture

Recorded before any new plan, because two load-bearing avenues turned out to be
closed and one to be unowned. Each was checked against source, not prose.

### C1 — the Terminal-holotape replacement for MCM is largely DEAD

Checked against `…\Fallout 4\Data\Scripts\Source\Base\` (7,932 `.psc`,
confirmed present) and the repo's own generated corpus.

| sub-claim | verdict |
|---|---|
| `TERMINAL` script type exists | **VERIFIED** — `Terminal.psc:1` |
| `ShowOnPipboy()` exists | **VERIFIED** — `Terminal.psc:7`, zero params, no return |
| `OnMenuItemRun(int, ObjectReference)` declared | **VERIFIED as declared** — `Terminal.psc:4` |
| …and actually used | **0 of 339** vanilla fragments implement it |
| menu items / submenus | **NO SCRIPT SURFACE.** `Terminal.psc` has zero properties |
| "Holds Holotape" | **DOES NOT EXIST.** `Holotape.psc` is one line, zero properties |
| text bound to a live value | **REFUTED** for Papyrus. Literal only |
| numeric input | **REFUTED.** Fixed list only |

Terminal's entire native surface is two members. Everything that would make it a
configurable menu is CK/ESM record data, pre-authored and shipped in an `.esp`.
Papyrus cannot create or modify it at runtime.

**Consequence:** a menu cannot be generated from PIP-MON config. The in-cartridge
surface, if built, is a **pre-authored `.esp`** plus a thin Papyrus shim. That is
a materially different project from the one the eval notes described, and the
notes' own summary line (*"needs no F4SE, no Scaleform, no new native, no
per-build address"*) was true about the F4SE part and misleading about the rest.

**Corroboration already in the repo, contradicting the avenue:**
`ai_context/systems_core/structural_layers.md:157` — *"`PipMon_TerminalTest.psc` |
menu test bench | **retire.** Terminal UI needs a `Native` script, and a
`Native` script cannot hold data, so it is a dead end"*.
`ai_context/spec/in_game_surface_requirements.json:18` — *"the honest position is
that the in-game surface has no menu and never did"*.

### C2 — the MCM config translation trick is BACKWARDS and has no local evidence

Checked against the live install and the whole repo.

- The only two mentions of `Data\MCM\` in the entire repo are the claim itself,
  in `PIPMON_EVAL_NOTES5.md:301` and `NOTES6.md:318`. **Zero code, zero schema,
  zero captured example.**
- `docs/POSITIONING.md:105` already carries a standing policy against the whole
  approach: `Third-party configs | we read NONE | clear`.
- The live install refutes the direction. `Data\MCM\Config\XDI\settings.ini:1-3`
  says, verbatim: *"This file contains XDI setting **defaults**… To make changes,
  make a copy of this file in `Data\MCM\Settings\XDI.ini`."* So
  `Data\MCM\Settings\<Mod>.ini` is the **user-override** layer, not the page
  definition. Page structure is `config.json` plus `lib.swf`.
- The repo also flatly contradicts itself on where MCM keeps settings:
  `PIP-MON_CONSOLIDATED.txt:692` and `:1090` say **in the save file**;
  `PIPMON_EVAL_NOTES5.md:301` says **in per-mod INIs**. Both unsourced.

**What MCM actually has, measured from 5 real configs**, and Terminal cannot
reach: `slider` with min/max/step, `textinput`, `textinputFloat`, `hotkey`, and
`valueOptions.sourceType: "GlobalValue"` — a live binding into a game Global,
~40 occurrences in `WorkshopFramework\config.json` alone. **That gap is in the
game data model, not in file formats**, so no translation layer closes it.

**Consequence:** MCM-surface parity is not achievable through either avenue that
was proposed. It needs a different answer, and F1 records it as OPEN with the
measured reason rather than quietly dropping it.

### C3 — `ck-rig` does not exist

Named once, in `COMENDIUM_STATE.md:84-94` — a file that is itself untracked until
`1344d4d`. Case-insensitive search for `ck-rig` / `ck_rig` / `ckrig` across the
tree returns that one line. No filename match, no git object, no directory.

The eval notes repeat *"mid-refactor, unversioned, and not safe to execute"* as
though it were verified. It is not verifiable — there is nothing to verify.

**Consequence:** do not cite it. F0 carries a task to find out what it was, and
until then the CK-side tooling inventory is one item short.

### C4 — one probe serving game *and* CK is an EXPERIMENT, not a design direction

The owner's premise was one lightweight probe surface working with both hosts in
tandem. Checked:

- **There is no probe surface to generalize.** `vprobe/src/PapyrusHooks.cpp:291-327`
  — `HookManager::install()` installs **zero** hooks and logs *"no AOB code hooks:
  the four former PapyrusVM/Thread/Script targets name classes absent from the
  game's RTTI."* "18/18 probes resolve" means 18 vtable **addresses** were found.
- **It would go inert in the CK, silently.** `vprobe/src/main.cpp:516` gates
  self-start on `GetModuleHandleW(L"Fallout4.exe") != nullptr`. Injected into
  `CreationKit.exe` it maps, raises `loaded`, and does nothing — no error.
- **The repo asserts the CK has no live VM to probe.**
  `overseer_cli/src/overseer_cli/envgate.py:594-596` — *"The Creation Kit
  COMPILES Papyrus, it does not RUN it, so 'the VM is idle' is vacuously true at
  all times and therefore says nothing."*
- **Zero `BSScript` or `Papyrus` symbols in the whole CKPE capture** — 14 files
  including all verbatim C++. CKPE works on commctrl, allocators, the DX11 swap
  chain and the CRT. Different surface entirely.
- **The project has already ruled it out in three specs**, with a stated
  mechanism: `docs/ENV_MANIFEST.schema.jsonc:141-149` — *"The address database is
  keyed on a hash of the GAME PE headers; handed the editor's image it refuses,
  correctly."*

**What is genuinely true and reusable:**

- `CreationKit.exe` and `Fallout4.exe` are both **1.11.240.0** — same generation.
- **`launcher/src/ProcessLaunch.cpp` and `BuildIdentity.cpp` contain zero
  occurrences of either name.** The launcher is already host-agnostic: it takes
  the exe path as `argv[1]`. Real, already-written, already-tested generality.
- `loadAddressLibBin(binPath, imageBase)` **already takes the image as a
  parameter**, and `setModuleForTest()` exists deliberately so the
  wrong-image refusal path is testable offline.
- `tools/read_rtti.py` and `tools/measure_vtable.py` both take `--exe`.

**Consequence:** F0.2 is a ~10 minute measurement that either kills the idea or
justifies a spike. `envgate.py:594` is the claim to overturn, and it is currently
unmeasured.

### C5 — the green gate is nine specific lies, not a vague risk

Read `tools/pipmon.ps1` line by line. Nine places where the surface reports
success or the wrong status. Detailed in
[`families/F2-truth-honesty/PLAN.md`](families/F2-truth-honesty/PLAN.md).

The two that matter most:

- **`$EXIT` has no `ATTENTION` key.** `status` can produce `ATTENTION`
  (`pipmon.ps1:207,208,213`), `$EXIT['ATTENTION']` is `$null`, and
  `exit $null` is exit 0 — with `"ok": false` in the envelope. A deploy
  verification failure exits green.
- **`snapshot` returns `GREEN`, exit 0, `"files": []`** when nothing is deployed,
  because the `Test-Path` guard is inside the loop and the `Emit` is outside it
  (`:304-331`). The reason string claims a snapshot was taken.

This is the explosion the owner is already braced for. It is not one bug; it is
nine, and they are individually fixable.

### C6 — the replacement claim is scattered across seven files with no join

| source | what it holds | the gap |
|---|---|---|
| `program_components.json` prose | names 7 legacy tools | one sentence, zero per-component attribution, no IDs |
| `program_components.json` `entries[6].replaces` | *"part of what MCM and Canary do"* | the **only** `replaces` in the file, in prose not IDs |
| `program_components.json` `entries[9].role` | *"Replace the CK for record validation…"* | in a `role` string, so the CK is never named in a structured field |
| `HANDOVER.md` G2/G3 | F4SE, po3, PCL, GoE, Canary, MCM; GECK peer | prose goals, no component↔tool table |
| `docs/POSITIONING.md` §2 | 4 native / 5 replaceable / 5 inspiration | no IDs, no per-component rows, **and §4 is factually stale** |
| `compat_f4se_map.json` | 10 rows, **closed status vocabulary** | F4SE-scoped only. No MCM/Canary/po3/Buffout/GoE/PAP/GECK |
| `ranking.json` `objective_markers` | the same 7 names | search terms, not a mapping |

**No document answers "which legacy tool does X replace, and why", keyed per X.**
F1 is that document, and `compat_f4se_map.json` stays as the API-level detail
beneath it rather than being rewritten.

**Also stale, found in passing:** `docs/POSITIONING.md` §4 still asserts *"F4SE
is a HARD RUNTIME DEPENDENCY TODAY… With no F4SE, it does not run."* Contradicted
by `program_components.json`, `project_blueprint.md`, `HANDOVER.md` §2 and
`f4se_prohibition.md`. Four sources say otherwise.

---

## R1 — replacement map

### `9bfb5c5` — schema.json: four optional fields on `compat_mapping`

**Change class:** B, additive only. Four field names appended to
`compat_mapping.entry_optional`, plus an `optional_notes` block explaining each.
Nothing removed, renamed or retyped.

**The one in-place schema edit, and why it has to be:** `tools/spec_lint.py:37`
hardcodes `SCHEMA = SPEC_DIR / "schema.json"`. A `schema.2.json` would never be
read, so the declared shape would quietly lie. Recorded in `VERSIONING.md` as the
exception to the Class B rule.

**VERIFIED — provably inert:** the linter reads `entry_required` (line 101) and
`record_required` (line 109). It never reads `entry_optional`. Adding names to
that list cannot change what is enforced.

**VERIFIED:** `spec_lint` GREEN after the edit — 13 specs, 172 entries, 0
problems, identical to before. The four new names are declaration only.

### `e499138` — F1.1: `ai_context/spec/legacy_replacement.json`, 30 rows

**Change class:** new file. Nothing existing modified, so it reverts alone.

`kind: compat_mapping`, `authority: derived`. One row per legacy **product**,
complementing `compat_f4se_map.json`, which is one row per **API call** and
F4SE-scoped. The two granularities are not interchangeable, so the older file is
cited as detail beneath rather than rewritten — and `schema.json` now says so in
`describes`.

**Status spread:** 13 `PLANNED`, 8 `NOT_PLANNED`, 5 `DIFFERENT_MECHANISM`,
2 `DECLARED`, **1 `COVERED`**, 1 `REJECTED`.

**Host spread — the load-bearing column:** 18 `none`, 8 `game`, 4 `ck`.
**18 of 30 rows need neither Fallout 4 nor the Creation Kit.** That is the
standalone surface as a countable fact rather than a claim, and it is much
larger than what `pipmon.ps1` advertises today.

**VERIFIED:** `spec_lint` GREEN — 14 specs, 202 entries, 0 problems, with the
closed status vocabulary checked across *both* `compat_mapping` files. Row and
host counts read back out of the file, not asserted from memory.

**VERIFIED by source, not prose:** the Terminal and MCM rows, checked against
`Data/Scripts\Source\Base` (7,932 `.psc`, confirmed present) and the live
`Data\MCM` tree. Findings in corrections C1 and C2.

**NOT VERIFIED:** every `requires_host` except those quoted from code. No row
has been exercised against a live host. `PLANNED` means a named mechanism
exists, not that anything runs.

**Also recorded, owner proposal 2026-10-03:** *instead of loading the mods into
the CK the hard way, add them Creation Engine style after the first compile.*
Captured as its own row against `ck_session.ps1` (present, `prepare` inert) and
`session-profiles.json` (present, 35 entries + 5 exclusions). It is the cheapest
remaining reduction of CK risk precisely because it needs no new engine
capability — it is a load-order staging decision, and the tooling is 80% there.

**One self-inflicted defect, repaired before commit:** a stray
`"function_sedded": null` key in the Wrye row. Class A, one line, in the same
session, caught by reading the file back. The linter would not have flagged it —
extra fields are permitted — which is the reason it was worth reading back.

**Cost:** one new file, ~1,400 lines of JSON. The next commit is the family plan.

---

## R2 — the honesty diagnosis

### `c4eb641` — F2: the nine defects, verified firsthand

**Change class:** new file, one. Nothing existing modified.

`tasks/roadmap/families/F2-truth-honesty/PLAN.md`. **Every line number read out
of `tools/pipmon.ps1` in-session**, not inherited from a handover — which
mattered, because the previous audit found the same nine by reading and had one
of them slightly wrong.

**The headline finding, corrected on second reading:**

> **F2.4 — `verify` cannot return anything but GREEN.** Line 237's map covers
> 0–3. `agent_watchdog.ps1` has no `exit` statement, so it returns 0. But any
> exit **above 3** is *also* not in the map, so the lookup is `$null`, and
> `$EXIT[$null]` is `$null`, and `exit $null` is **0**. So `verify` can never
> return SKIP or BROKEN — by two separate routes.

**F2.1 is the worst of the nine** because it is the only one that puts a right
answer in the wrong channel. `status` **produces** `ATTENTION` at 207, 208 and
213; `$EXIT` has no `ATTENTION` key; `$EXIT[$status]` is `$null`; `exit $null` is
0. So a failed deploy verification exits 0 with `"ok": false` in the envelope.
Both channels are documented as authoritative and they disagree.

**NOT DONE, DELIBERATELY:** the F2.1 fix. Adding `ATTENTION = 1` is wrong on its
own — `ATTENTION` currently means *"a deploy or link check did not pass"*, which
is nearer RED than GREEN, and assigning it a number without deciding what it *is*
would make the exit table unreliable in a second way. Owner ruling, 2026-10-03:
research the vocabulary first. That research is R3.

**VERIFIED:** `spec_lint` GREEN, unchanged, 14 specs / 202 entries / 0 problems.
`ai_context/spec` untouched by this commit.

**NOT VERIFIED:** no fix applied. All eleven behaviours are read from source;
none observed at runtime, because each needs a host that is *present* on this
machine and their whole point is what happens when it is absent.

**Cost:** one new file. Zero lines of behaviour changed.

---

## R3 — vocabulary research, a twelfth defect, and the compiled-environment model

### `997e2cb` — F2.0 + F2.12 + map row 31

Three additions in one commit. **No behaviour changed anywhere.**

#### 1. F2.0 `VOCABULARY.md` — research before change, as instructed

Owner instruction: *"more then one state added before its all done with this
program, research what it could or would do and validate the idea for use and
helpfulness before doing anything."* Done, and applied to nothing.

> **THE FINDING THAT REORDERS F2: `$EXIT[$status]` on an unrecognised key returns
> `$null`, and `exit $null` is 0. An unrecognised status is currently a PASS.**

Values already reaching the table with no key: `ATTENTION` (207/208/213),
`PASS` and `FAIL` (275), `NOT RUN` (205/206), `UNKNOWN` (via `agent_watchdog`),
and any exit ≥ 4 from `:237`.

**The project already has eighteen status vocabularies.** Three are linted —
`compat_status_vocabulary` via `spec_lint.py`, `side_invariants.json` via
`side_gate.py`, `surfaces.json` via `surfaces_gate.py`. The 5-state exit table,
**the one with the most readers, is not linted at all.** And `tasks/roadmap/README.md`
already states the policy — *status vocabularies are closed and reused, not
reinvented*. Eighteen exist partly because nobody picked one.

**Hypothesis CONFIRMED:** the single `status` field carries at least ten
orthogonal dimensions and expresses two. Coverage fraction, freshness,
concurrency, authority, degradation and risk class are all in use *elsewhere* in
the project and none is reachable from `$EXIT`.

**Who actually consumes a status — the decisive part:**

> The **exit code** is the real contract. **Nothing in the tree reads the
> envelope's `ok` field. Nothing reads its `status` string.** Five consumers read
> the exit code; the envelope is written by one process and parsed by no
> automated consumer.

`orchestrate.py:753-757` branches on exit code only. `gate_watch.py:83` collapses
SKIP, BROKEN, timeout 124 and missing-binary 127 all into RED.
`orchestrate.py:335-336` does not handle `2`, so **a BROKEN exit prints `??`**.
`side_gate.py:96` **returns 0 unconditionally** while printing "1 of 3 sides
available". `launcher/src/main.cpp:149` collapses `Degraded` to the same exit as
failure.

**Five of the candidate states already exist in this project:** `PARTIAL`
(`envgate.py:1004`), `UNKNOWN` (`envgate.py:74-80`), `PROXY`
(`taskrun.ps1:335-342`), `STALE` (`door_registry.json:11`), `DEGRADED`
(`ProcessLaunch.hpp:61`). **None needs inventing. Each needs reaching.** That is
the answer to "we may need more states" — the need is mostly routing.

**Ordering constraint derived:** step 0 is **make the table total**, before any
state is added. Until the `$null` path is closed, adding a state adds a *new
silent-PASS path* rather than an honest answer. Step 4 is extending the lint to
the exit table. Step 3 — *give every new state a consumer in the same commit* —
is the one most likely to be skipped, and `schema.json:187` is the project's own
reason not to skip it.

**Consequently F2.1 is split:** **F2.1a** make the table total — a bug fix, *not*
blocked on the owner — and **F2.1b** decide what `ATTENTION` is — still owed,
still not started.

#### 2. F2.12 — a defect the first pass missed

Found *during* the research, not by a second reading of the same file.

> **`pipmon validate` exits 0 when validation FAILS.**

`validate_plugin.ps1` writes only `PASS`, `FAIL` or `SKIP` — an exhaustive set
across its 18 report sites. `$EXIT` contains **none of the three**. Line 275
passes `$rep.status` straight into `Emit`, so `$EXIT['FAIL']` is `$null` and a
failed validation returns `"status":"FAIL","ok":false` with **exit 0**.

Worse than F2.1, because `PASS`/`FAIL` are what the validator has always written
rather than a typo. `ATTENTION` was emitted by mistake; this is a real value
falling through a real gap. Line 212 proves the author knew `PASS` existed:
`-notin 'PASS','GREEN'`.

#### 3. Map row 31 — the compiled-environment model

Owner proposal, 2026-10-03: *compile once, snapshot, then toggle compiled
plugins from the terminal instead of rebuilding* — and use that as the **testing
and validation method for the cartridges**, so that whatever is compiled into the
environment, even if not rendered or running, is callable through its native.

Recorded with an honest three-level split, because the claim is true at one level
and false at another, and conflating them would make the row a lie:

| level | status |
|---|---|
| **plugin** | **works today.** `linksync.ps1` declares `[string[]]$Enable`/`$Disable` at 45-46, implements both at 147-155, snapshots before apply at 132. `pipmon.ps1:148` advertises both args; `:259` forwards neither. **The mechanism is written, tested, and one argument list from reachable** |
| **pex** | a `.pex` is compiled bytecode, so toggling a function is not a thing — but that path is already cheap (seconds). The expensive ops are xEdit-class and therefore plugin-level, so plugin level is the right toggle |
| **native** | needs Layer A. One blocker |

**And the part that is sharper than it looks.** *"Callable in its native even if
not rendered or running"* decomposes into **five rungs**, and only the last three
need Layer A:

```
A. DECLARED     the .psc declares the native      checkable TODAY
B. COMPILED     the .pex carries it               checkable TODAY
C. REGISTERED   a native handler exists            needs Layer A
D. REACHABLE    a compiled .psc gets an answer     needs Layer A
E. DISPATCHABLE a cartridge fires unrendered       needs Layer B
```

**A and B are a real gate available now**, and they are the honest half of the
goal-coverage gap `goal_alignment.md` says is missing. It also turns S0 from a
binary question into a coverage figure — *declared 13, compiled 13, registered 0,
reachable 0* — where the first two numbers are knowable before any hook exists.

**VERIFIED:** `spec_lint` GREEN, 14 specs / 203 entries / 0 problems. Map is now
**31 rows**: 1 `COVERED`, 2 `DECLARED`, 14 `PLANNED`, 5 `DIFFERENT_MECHANISM`,
8 `NOT_PLANNED`, 1 `REJECTED`. By host: **19 `none`, 8 `game`, 4 `ck`**.

**VERIFIED by reading source:** the `linksync` line numbers, the `pipmon` line
numbers, the `validate_plugin.ps1` report value set, and `$EXIT` having a `$null`
path.

**NOT VERIFIED:** every claim in `VOCABULARY.md`. Two are worth one command each
and have **not** been run — that `pipmon validate` exits 0 on `FAIL`, and that
`agent_watchdog.ps1` exits 0 regardless. Both follow from exhaustive literal
sets; neither has been executed.

**NOT VERIFIED:** the five-rung ladder and the three-level split are **this
session's judgement**, not measurement. The row says so in its `notes`.

**Cost:** two new files (`VOCABULARY.md`, one map row), one plan edited. Still
**zero lines of behaviour changed** — the whole of R0 through R3 is diagnosis and
specification.


