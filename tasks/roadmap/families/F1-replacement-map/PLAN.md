# F1 — Replacement map

**Goal:** one document that answers *which legacy product do we replace, what
job did it actually do, how did it break, and what do we add beyond it* — keyed
per product, so a program can branch on it.

**Status:** the map exists. 30 rows. See [`ai_context/spec/legacy_replacement.json`](../../../ai_context/spec/legacy_replacement.json).

## The headline, stated honestly

**1 of 30 rows is COVERED.** One — the V-Link wire.

That is not a criticism of the map; it is the map's most useful property. Before
this file existed the replacement claim lived in seven places, the largest being
one sentence of prose in `program_components.json` naming seven tools. There was
no way to count what was covered. Now there is, and the answer is 1.

| status | rows | what it means here |
|---|---|---|
| `COVERED` | **1** | implemented **and proven**. V-Link only |
| `DECLARED` | 2 | built and shipped, not yet proven by a gate that could fail |
| `PLANNED` | 13 | a named mechanism exists, not built |
| `DIFFERENT_MECHANISM` | 5 | we do the job differently and say so; not a drop-in |
| `NOT_PLANNED` | 8 | declined, with a mandatory reason |
| `REJECTED` | 1 | considered and refused on measured grounds |

**By host — the column that answers the owner's requirement:**

| `requires_host` | rows | which |
|---|---|---|
| **`none`** | **18** | AddressLib resolution · po3/GoE/PAP work · Buffout analysis · xEdit read · xEdit-diff reporting · Archive2 read · Papyrus *negative table* · Vortex · MO2 · FOMOD · Nexus/CurseForge (declined) · V-Link · control plane · Papyrus index · capability registry · MCM ingestion (declined) · Engine Fixes (declined) · Wrye (declined) |
| `game` | 8 | F4SE loader · F4SE hooks · GoE · PAP · MCM UI (refused) · Canary · in-game surface · V-Link |
| `ck` | 4 | CK · CKPE · Papyrus compiler · curated CK staging |

**18 of 30 need neither Fallout 4 nor the Creation Kit.** That is the standalone
surface, stated as a fact rather than an aspiration. It is also much larger than
what `pipmon.ps1` advertises today — see F5.

## Three tiers, because "integrate some as ideas" is the correct instinct

The owner asked to *count some as ideas and some as back-door compatibility*.
That is right, and the map's `PLANNED` is too coarse to express it. Splitting it:

### Tier 1 — COMMITMENT. Built, or built enough to be a promise.

| row | state |
|---|---|
| V-Link wire | **COVERED.** Three parallel compile-time assertions (C++, Python, Rust) pin the frame; verified live 2026-09-29, 25 frames, `totalEventsDropped = 0` |
| F4SE loader / injection | built. `launcher`, 45 self-tests green, and host-agnostic already — zero product names in `ProcessLaunch.cpp` |
| AddressLib replacement | built. 8,617 records, 103,428 bytes, build fails on a stale blob |
| control plane `pipmon.ps1` | **DECLARED**, not covered. Nine places it currently lies → F2 |
| capability registry | **DECLARED**. No `status`, no `provenance` → F4.2 |

### Tier 2 — NAMED MECHANISM. The plan says how; nothing is built.

These have a *specific artifact or file* named as the thing that would make them
real, which is what separates them from an idea:

| row | the named artifact |
|---|---|
| F4SE hook install | `third_party/CommonLibF4/CommonLibF4/include/RE/Bethesda/BSScript.h` — blocked on B5 |
| Canary Redux | `SaveGame()` hook + measured thresholds (>50 events, 1500 ms) |
| xEdit read/parse | KaDag, plus a measured API reference that already records which functions *don't* exist |
| Papyrus compiler | Caprica (forward compiler; the format is settled and Champollion proves the reverse) |
| Archive2 read | four verbatim prior-art sources already captured in `ba2_format/` |
| in-game surface | a pre-authored Terminal `.esp` + ordinary Papyrus shim |
| curated CK staging | `ck_session.ps1` (present, `prepare` is inert) + `session-profiles.json` (present) |
| CKPE replacement | 12 of 20 techniques assessed portable, with the reasons |
| Vortex / MO2 / FOMOD | the three-question provider contract, specified in §18.2 |

### Tier 3 — IDEA. A direction with no artifact behind it yet.

**Treat these as inspiration, not schedule.** Recorded so they are not lost, and
so nobody reads a Tier 2 row and assumes they all have the same footing.

| idea | why it is only an idea |
|---|---|
| proactive anomaly prediction | the tells are named and measurable (500 ops/sec, 1000 handles, >50 identical errors/sec) but there is no model, no lead-time budget and no false-positive budget. `docs/ANOMALY_RULES.md` is a rule set, not a predictor |
| cartridge aesthetic design | the visual rules are borrowed from the archive's IDE-grade reference and are *specific* — no hover, no right-click, no icon fonts, 8-colour degradation. But nothing has been drawn, and the archive's own visual pass is four JPGs with no written rationale |
| light-settings version of the in-game surface | the dual-mode bus exists as a design with a ~1 Hz lightweight subscriber. No rate control is implemented anywhere |
| provider `disagreements()` | named as the most valuable of the three provider questions, and nobody has written down what a disagreement *looks like* or what to do with one |
| two-way cartridge | eval wiring rung **L3**, marked NOT POSSIBLE yet. Depends entirely on Layer A |
| any general mod-manager behaviour | declined outright in the eval. Recorded so it stops being the project's unspoken second product |

### The back-door register — compatibility built opportunistically

The owner asked for back-door compatibility during the build. Concretely, four
places where it happens *for free* if the rule is respected, and one where it
must not:

1. **`plugins.txt` byte-compatibility.** We write the game's own file, so the
   game and every legacy tool keep reading it. Already in `linksync.ps1`, which
   never touches `mods.txt`. **Caveat:** it was writing ASCII until commit
   `2ad0485`, which turned non-ASCII plugin names into `?`. A load-order tool
   must round-trip bytes, and this one now does — but that was a bug found by a
   reviewer, not by a test.
2. **Envelope back-compat.** `pipmon.surface/2` is additive to `/1`, and the
   envelope keeps the old `command` field until the UI migrates. `pipmon build`
   stays an alias of `script build`; `ck-session` of `session`. Cheap, and
   already specified.
3. **`.fos` and `.pex` are read, never rewritten in place.** Repairs go to a
   copy; quarantine the original. That is what makes the format continuity
   real rather than claimed.
4. **GECK and the CK keep working untouched.** We write nothing into their
   namespaces. `Data/PipMon/`, never `Data/F4SE/`. This is the cheapest
   compatibility there is and it costs one naming rule.
5. **Where it must NOT happen:** extending a vanilla Papyrus type. That single
   change would make every F4SE plugin work unmodified — and it is the one thing
   `compat_f4se_map.json` marks `REJECTED`, because *"we are additive, so we
   install alongside anything and collide with nothing"* is the project's
   central advantage. The map says: *"This is the one row where a decision to
   reverse is available, and it should be made deliberately and written down,
   not drifted into."* Nothing in this family may drift into it.

## Remaining F1 tasks

| id | task | state |
|---|---|---|
| F1.1 | `legacy_replacement.json`, 30 rows | **done** — `e499138` |
| F1.2 | join script: map × `compat_f4se_map` × `program_components` × `compat_check.py` | open. Makes the three levels machine-relatable instead of merely adjacent |
| F1.3 | surgical `replaces` on the 13 `program_components.json` entries that lack it | open. Schema already permits the field; **1 of 14** uses it. Add as `program_components.2.json` per `VERSIONING.md` |
| F1.4 | one door in `door_registry.json` so "which tool do we replace" has a home | open. Currently only `blockers` and `compat` have doors among the registries |
| F1.5 | fix `docs/POSITIONING.md` §4 | open. Still asserts *"F4SE is a HARD RUNTIME DEPENDENCY TODAY… With no F4SE, it does not run."* Four sources contradict it |
| F1.6 | a gate so the map cannot drift | open. Same shape as `ownership_gate.py`. Without it, a `status` can be edited from `REJECTED` to `PLANNED` and nothing notices |

## Three decisions that are the owner's, not mine

1. **MCM.** Both proposed replacements are measured dead. The remaining option
   is narrower: serve MCM's *role* with a pre-authored Terminal `.esp` rather
   than its *mechanism*. That is row 30, and it needs the CK to author. Take it
   or leave it — but leaving it means the honest scope statement is "we do not
   do in-game settings", which is defensible and should then be said out loud.
2. **xEdit patch generation.** `NOT_PLANNED` on principle: a wrong report the
   user notices, a silently mis-written record corrupts a save and surfaces later
   somewhere else, attributed to something else. That is a product position and
   it will be reopened by pressure, because "we analyse conflicts but cannot fix
   them" reads as half a product.
3. **Abi drop-in.** Existing F4SE plugins and po3 natives running unmodified is
   mutually exclusive with the coexistence contract. Not a gap to close — a
   choice, already written down in `compat_f4se_map.json`.

## What this family does not settle

- Whether Layer A is achievable at all. That is F0.1, and it gates 6 of the 13
  PLANNED rows.
- Whether the CK has a Papyrus VM worth probing. F0.2, about ten minutes.
- Any per-API compatibility claim. That is `compat_f4se_map.json`, still 0 of 10.
