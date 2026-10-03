# Roadmap — staged plan, families, priorities

Created 2026-10-03, after the session crash. Reconstructed from the inspiration
archive, `PIP-MON_CONSOLIDATED.txt`, both `HANDOVER.md`s, `RESUME.md`, the four
`PIPMON_EVAL_NOTES` files, and the `ai_context/spec/` registries — then checked
against the actual source, which changed several conclusions.

**Read [`CHANGELOG.md`](CHANGELOG.md) first.** Six corrections to the inherited
picture are recorded there, including two dead avenues. Do not plan from the
older documents without it.

## Navigation

| | family | what it settles | state |
|---|---|---|---|
| **F0** | [blocked & experiments](families/F0-blocked-experiments/PLAN.md) | the measurements that unblock everything else | 5 open |
| **F1** | [replacement map](families/F1-replacement-map/PLAN.md) | which legacy tool does X replace, how, and what we add | in progress |
| **F2** | [truth & honesty](families/F2-truth-honesty/PLAN.md) | the nine places the surface lies | 11 open |
| **F3** | [Papyrus & CE modernization](families/F3-papyrus-ce-modernization/PLAN.md) | the FO4-only scripting index and habit migration | 6 open |
| **F4** | [surface & content](families/F4-surface-content/PLAN.md) | `caps` requirements, capability state, first CELL | 5 open |
| **F5** | [standalone](families/F5-standalone/PLAN.md) | runs with neither FO4 nor CK present | 3 open |
| **F6** | [live bridge & hubs](families/F6-live-bridge-hubs/PLAN.md) | mirror out, inject in, heavy back-end creation | 4 open |

## Order, and why

```
F2  ──►  F1  ──►  F3  ──►  F0  ──►  F4  ──►  F5  ──►  F6
```

**F2 first.** Nine defects where the surface reports success or the wrong status.
Until they are fixed, every later task is measured by an instrument that lies,
and the changelog starts recording confident falsehoods. It is also the smallest
family — nine surgical repairs, each independently committable and revertable.

**F1 second** because it is the spine the other families reference. The map gives
every later task a `replaces` target and a reason, and it is where the dead
avenues from the corrections above get recorded as dead rather than quietly
dropped.

**F3 third** because it is the largest genuine asset here and it is independent
of both hosts — `Data\Scripts\Source\Base` is 7,932 files of ground truth that
exists whether or not anything runs. It also retires guesswork permanently.

**F0 fourth** because its five tasks are measurements, not code, and each one can
kill a downstream plan cheaply. Better to spend the week finding out that the CK
has no Papyrus VM than to build against the assumption.

**F4, F5, F6 after** — they consume the map, the honest surface, and the index.

The order is a recommendation, not a dependency graph. F3 and F0 have no
prerequisites and can run in parallel with anything.

## What wires to what

This tree adds to the existing registries rather than replacing them. Nothing
here is a second source of truth.

| this roadmap | wires into | how |
|---|---|---|
| F1 replacement map | `ai_context/spec/compat_f4se_map.json` | map is product-level; that file stays API-level. A join script relates them |
| F1 | `ai_context/spec/program_components.json` | surgical `replaces` arrays — the schema already permits the field, 13 of 14 entries lack it |
| F1 | `ai_context/systems_core/door_registry.json` | one door entry so "which tool do we replace" has a home |
| F2 | `tools/pipmon.ps1` | nine repairs, one commit each |
| F3 | `ai_context/vocabulary.json` | query words added **there**, never in code — per the skill's own rule |
| F4 | `tasks/capabilities.json` | gains `status` and `provenance`; it has neither, and no provenance breaks non-negotiable #2 |
| F4/F5 | `tools/pipmon.ps1 caps` | `caps` gains a per-verb `requires` |

## Conventions this tree follows

- **IDs** are `<namespace>.<slug>`, lowercase dotted — matching `surfaces.json`
  and `tasks/capabilities.json`. Families are `F0`–`F6`; tasks are `F<n>.<n>`.
- **Status vocabularies are closed and reused**, not reinvented. `compat_f4se_map.json`
  has a 6-value one, `side_invariants.json` a 4-value one, `surfaces.json` a
  5-value one. Family plans declare which they borrow.
- **Every file name avoids `*_alignment.md`, `*_contract.md`, `*_model.md`,
  `*_audit.md` and `SKILL.md`.** `ai_context/ranking.json` has an `auto_meta`
  rule that tags those as `scope: meta`, which forfeits every objective
  multiplier and applies a `0.6` off-domain penalty. Do not name a file here in
  a way that makes retrieval bury it.
- **Provenance on every claim**, per non-negotiable #2: *a fact with no
  provenance may not exist.*
- **SKIP is never PASS**, per non-negotiable #1. A family plan that says a task
  is done has run its verify command.

## The two tools that stay

**The Creation Kit and xEdit.** Not provisional.

- **CK** — `PIP-MON_CONSOLIDATED.txt` C14: `NOT REPLACEABLE`. §15.3: *"Do not
  replace what is a CONTENT AUTHORING SUITE: the Creation Kit. Attempting the
  second is how this project stops shipping anything at all."* `HANDOVER.md` G3
  makes GECK a peer tool. And `testenv_layout.md` records that **exteriors need
  clean precombine, which is a CK command-line operation only** — filtered
  precombine is GUI-only. So the CK stays load-bearing regardless of intent.
- **xEdit** — already the proven record engine. Load measured at ~2m15s to
  `Finalize`, 2,287,300 records / 64,926 CELL / 140 signatures, and `Add()`,
  `GetNewFormID()` and `FileWriteToStream` all confirmed working. Replacing it is
  not on the table; depending on it as *the* generator is.

The owner's condition was that these get dropped if they present an
unsurmountable wall. Neither has. CK's cost is three crash dumps and no CKPE;
F4 records the mitigation. xEdit's cost is the first-run notice needing one
human click and a ~3 minute load — recorded as an accepted cost, not a blocker.
