---
title: Goal alignment audit
authority: measured
purpose: >
  Whether the retrieval ranking model actually serves the program's goals, its
  components, and the Creation Kit / engine constraints it works within. Read
  before adding an objective, changing a weight, or trusting a green build.
audited: 2026-09-30
config: ai_context/ranking.json
---

# Do the gates and the retrieval model serve the program's goals?

## Short answer

**The retrieval model was not aligned when first written, and green gates still
do not mean goal alignment.** Both were fixed in part; the remaining gaps are
listed at the end rather than smoothed over.

## What the program is

A Fallout 4 extender built **without F4SE**, replacing the scripting, monitoring
and tooling layer that F4SE, AddressLib, Buffout, po3, MCM, Canary and CKPE
would otherwise provide. It ships **its own CLI / terminal / control plane**, so
that a human or another provider's model can sit in and drive tasks. Two tandem
hosts, CK and the game, linked through one mod.

## Goal to component to objective map

| Goal | Component | Retrieval objective | Build gate covers it? |
| --- | --- | --- | --- |
| Replace the extender layer | `vprobe` Layer A, `PipMon.psc` Layer B | `replacement` `layer-a` | compiles, yes; **functionally no** |
| Prove a script reaches our natives | S0 experiment | `s0` | **no** |
| Replace scripting/telemetry mods | `Overseer`, `OverseerBridge`, `overseer_cli` | `monitoring` | python 108 checks, partly |
| Own CLI / terminal / control plane | `tools/pipmon.ps1`, `overseer_cli`, dashboard | `control-plane` | partly; no end-to-end gate |
| Author and validate without the CK | headless xEdit, `generate_env.ps1` | `xedit-automation` | **no** |
| Compile-correct FO4 Papyrus | `PipMon.psc`, `PipMonTestFacility.psc` | `papyrus-correctness` | yes, real CK compiler |
| Work within CK limits | CK, no CKPE, 3 crash dumps | `ck-constraints` | **no** |
| Stable load order, no F4SE | `linksync.ps1`, `ck_session.ps1` | `load-order` | partly |
| Demonstrate on a real cell | facility, `DOOR-SPEC.md` | `facility` | **no** |
| Link CK and game | Creation Sync, pex deploy | `creation-sync` | partly |
| Adopt Skyrim capability with a path | `skyrim_capability_adoption.md` | `syrinx-adoption` | n/a, judgement |
| Serve AI retrieval | `rag_index.py`, `rag_query.py` | `retrieval` | **no** |

## What "all gates green" actually means

The build gate is five stages run from the repo root:

1. `vprobe` runtime: Zydis, compile `/W4 /WX`, link, 17 self-test checks
2. `papyrus`: `PipMon.psc` to `PipMon.pex` with the real Creation Kit compiler
3. Python: 108 checks
4. Rust: 5 checks
5. Launcher: 45 checks

**That is build integrity. It is not goal coverage.** A fully green gate is
consistent with all of the following being true at once:

- S0 is unproven, because no BSScript vtable slot is hooked.
- `PipMonTestFacility.esp` is 66 bytes with **0 records**.
- No xEdit run has yet produced a validation report.
- The control plane has never been driven end to end by a second agent.
- Retrieval could rank an aspiration above a measurement and nothing would fail.

The gate has no goal-coverage dimension, and adding one is a real piece of work:
it would mean asserting, per objective, that some check exists and passed. Until
then, green means *it builds*, not *it works*.

## Gaps found in the first ranking model, and fixed

The objectives were my own first guess and were audited against the real
component list. Four were missing:

| Missing objective | Consequence found | Fix |
| --- | --- | --- |
| `control-plane` | The mod's own CLI/terminal, its reason for existing, was **invisible**: a query for it returned xEdit API docs. | added at 1.35 |
| `monitoring` | `overseer_cli/.../detector.py` scored **28.1** and lost to unrelated Papyrus prose at 36.2. | added at 1.30 |
| `replacement` | The replacement scope was vocabulary but never an objective. | added at 1.25 |
| `creation-sync` | The two-host link was unranked. | added at 1.15 |

Also added to the vocabulary: `control_plane`, `monitoring`, and `components`
covering vprobe, V-Link, Overseer, OverseerBridge, `overseer_cli`, envgate,
detector, ipc_client, PapyrusApi, testlab and Creation Sync. Previously these
component names were not queryable at all.

Verified after the fix: a control-plane query returns `project_blueprint.md` and
`HANDOVER.md`; an anomaly query returns `docs/ANOMALY_RULES.md`; all 13
objectives return hits when queried by name.

## Known distortions, not fixed

- **Authority is per file, not per section.** A file with one measured finding
  and many opinions scores as fully measured. This is the largest known error.
- **Short source files lose to topic documents.** BM25 rewards repeated query
  terms, so `detector.py` cannot outrank a document *about* anomaly detection.
  The fix is usage, not weights: `-Kind code` or `--path` when the question is
  *where is the implementation* rather than *what does it mean*.
- **616 of 647 files classify as `derived`**, so the authority signal is
  concentrated in the curated layer. The lever is more `authority:` lines, not
  larger tiers.
- **Still lexical.** Weights reorder matches; they do not comprehend.

## Usage rules that follow

| Question | Ask for |
| --- | --- |
| What does X mean, and what is true about it? | default query, dense |
| Where is the code that does X? | `-Kind code`, or `--path` |
| What do we already know about X? | default; trust tiers over wordiness |
| Is this claim safe to act on? | read the `authority` tier, `--explain` the weights |
| Where is everything about X? | `-Format paths` |
