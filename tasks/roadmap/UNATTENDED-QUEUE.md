# UNATTENDED QUEUE — what may be done without a human present

Created 2026-10-03. This file is the answer to *"what can you be left to do?"*
and it is deliberately narrow.

## The safety line

**Safe unattended** means all three of these are true:

1. Every file written is inside `C:\Users\Administrator\Desktop\Pip-mon Script Management system`.
2. No third-party process is launched — no xEdit, no Creation Kit, no game, no compiler, no `build_all.bat`.
3. The task is verifiable **without** a host, by running something that exits with a known code.

**Not safe unattended** — any one of these and I stop and ask:

- writes to the game folder or `%LOCALAPPDATA%`
- launches `xFOEdit64`, `CreationKit.exe`, `Fallout4.exe`, `PapyrusCompiler.exe`
- anything longer than ~60 seconds of runtime
- `git push`, `git commit --amend`, `git reset --hard`
- deleting or emptying anything
- inventing a status, a schema field, or a vocabulary value (that is the owner's)

## Commit cadence

Commit after **each verified task**, never batched. Target one commit per 5–10
minutes of work, whichever comes first. Every message states VERIFIED and NOT
VERIFIED. `tools/changelog_gate.py` enforces that the index keeps up.

Standing rules, from `tasks/roadmap/VERSIONING.md`: no deletions · small repairs
edit in place with a diff and a changelog line · anything longer than a couple of
lines becomes a numbered variant (`x.2.ext`) with the original kept.

---

## PRIORITY 1 — finish the honesty work (F2)

The instrument everything else is measured by. **7 of 14 closed.**

| # | id | task | verify | est |
|---|---|---|---|---|
| 1 | **F2.3** | `Read-Report` gains a freshness check; `status` cannot present a stale report as current. Staleness goes in `data`, **not** a new status | `pipmon.ps1 status` before/after a touched input | 15m |
| 2 | **F2.4** | `agent_watchdog.ps1` gets a real `exit`; `verify`'s map covers every exit | `pipmon.ps1 verify` returns a non-GREEN when it should | 15m |
| 3 | **F2.12** | `validate` maps `PASS`/`FAIL`/`SKIP` onto the surface vocabulary — FAIL must be RED/1, not BROKEN/2 | inject a report into `runs/watch` in scratch, assert the mapping | 10m |
| 4 | **F2.10** | route `caps` through `New-Envelope` so it stops breaking its own published provenance invariant | `caps` output gains `status`/`ok`/`provenance` | 15m |
| 5 | **F2.9** | `plans/schema.json` either enforces `requires` or stops claiming it | `orchestrate.py` refuses, or the claim is withdrawn in writing | 10m |

**F2.5 is deliberately excluded.** The change is inside the project, but proving
it means exercising `linksync` against the **live** `plugins.txt`. Needs a human.

## PRIORITY 2 — lints, so my own failures become build failures

Three of my failures this session were a *missing check*, not a missing fix.

| # | id | task | verify | est |
|---|---|---|---|---|
| 6 | **S31** | `spec_lint.py` fails when a `compat_mapping` entry uses a field its kind's `entry_optional` does not declare. Closes the gap the R4 revert test found | mask a declaration, assert RED | 20m |
| 7 | **S31b** | a lint that `caps`' advertised verbs and `surfaces.json`'s claimed verbs are the same set | break one, assert RED | 15m |
| 8 | **S31c** | lint the `$EXIT` table: every status any code path can emit must have a key | emit a foreign status, assert the table is incomplete | 20m |

## PRIORITY 3 — wire F1, the replacement map, into the places that should read it

| # | id | task | verify | est |
|---|---|---|---|---|
| 9 | **F1.3** | `replaces` on the 13 `program_components.json` entries lacking it — as `program_components.2.json` per VERSIONING.md, original kept | `spec_lint` GREEN on the variant | 25m |
| 10 | **F1.5** | fix `docs/POSITIONING.md` §4, which still asserts F4SE is a hard runtime dependency — contradicted by four sources | text no longer contradicts `program_components.json` | 10m |
| 11 | **F1.4** | `door_registry.json` gains doors for `program_components`, `surfaces`, `side_invariants`, `capabilities`, `facility-v0`, `session-profiles` | `door_lint` GREEN | 15m |
| 12 | **F1.6** | a gate so a `status` in the map cannot be edited `REJECTED`→`PLANNED` unnoticed | flip one, assert RED | 20m |
| 13 | **S13** | write `PIPMON_INTERFACE.md` — the doc the `docs` door now declares owed | the door resolves with no gap | 30m |

## PRIORITY 4 — spec drift found on 2026-10-03, none of it fixed yet

| # | id | task |
|---|---|---|
| 14 | **D1** | three different path spellings for `BSScript.h` across three specs; only one exists on disk |
| 15 | **D2** | `blockers_to_environment.json` `critical_path_to_a_cell_on_disk` omits B4 despite `blocks_the_critical_path: true` |
| 16 | **D3** | blocker `status` is free prose, so no program can branch on it — the vocabulary is closed everywhere except here |
| 17 | **D4** | python test count drifts across four docs: 106 / 107 / 108 |
| 18 | **D5** | six registries have no door, so "which doc answers this" cannot answer for them |

## PRIORITY 5 — F3, the Papyrus/CE index (the big one)

Needs no host and blocks nothing. Reads `Data\Scripts\Source\Base` (**7,932
files, read-only, outside the project but read**) and writes inside it.

| # | id | task | est |
|---|---|---|---|
| 19 | **S15** | machine-readable signature per function — arity, param types, return type, `Native`/`Hidden`/`Event` | 60m |
| 20 | **S16** | observed usage counts, so "dead function" and "legacy habit" become measurements | 30m |
| 21 | **S18** | hard FO4-only assertion, before anything is indexed | 15m |
| 22 | **S17** | negative table by compile probe — **needs the CK compiler, so it stops here unattended** | — |

**S17 is the one that most needs a human**, because a compile probe launches
`PapyrusCompiler.exe`. Everything up to and including S18 can proceed.

---

## NOT ON THIS QUEUE, AND WHY

| task | why not |
|---|---|
| F2.5 | proving it writes the live `plugins.txt` |
| S20–S24 (P4 wall, xEdit) | xEdit runs are 2–3 minutes and modify the facility plugin |
| S32–S35 (CK experiments) | S32/S33 are read-only and *are* safe — but they need the game folder and are ~10 min each; S35 **crashes the game** |
| anything in `build_all.bat` | compiles and deploys to the game folder |
| `git push` | G10, and the owner has said local only |
| status-vocabulary changes | **F2.1b is the owner's decision.** Not mine to make |
