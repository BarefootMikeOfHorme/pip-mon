---
title: Retrieval ranking model
scope: meta
authority: measured
purpose: >
  Why ai_context/ranking.json weights what it weights, and how to change it
  without touching code. Read before tuning retrieval or trusting a rank.
applies_to: tools/rag_index.py (classify_authority), tools/rag_query.py (weight_parts)
config: ai_context/ranking.json
trust: >
  The mechanism is verified by A/B measurement on this index. The specific
  weights are POLICY, not truth: they encode a judgement about what this project
  needs, and every one of them is a number someone chose. That is why they live
  in a file and why --no-weights exists.
---

# Why this ranks the way it does

## The one principle

**Content that encodes a constraint or a measured limit outranks content that
describes an aspiration.**

Acting on an aspiration produces a broken build. Acting on a constraint produces
a correct one. That single rule is what makes the ranking correlate with actual
use rather than with text volume, and it is the same rule the project already
states about its own evidence: `SKIP` is never `PASS`, and an unproven claim is
not a fact.

## Why the expensive knowledge is the negative

Look at what each high-value fact in this project cost:

| Fact | Cost to establish |
| --- | --- |
| `CustomEvent` / `SendEvent` do not exist in FO4 Papyrus | a compile cycle, repeated for each of 4 obvious Skyrim habits |
| A `Native` script may not contain data | found the hard way; it silently invalidates a whole design |
| `GetPluginName` does not exist in FO4Edit 4.1.5f | a three-minute xEdit run that produced no output |
| `AddNewFileName` creates a plugin rather than registering one | would have written to `Data\` and mutated `plugins.txt` |
| The full core load takes ~3 minutes | two false-negative timeouts before it was measured |
| xEdit loads `Fallout4.ccc` and the DLC list regardless | watching the load log contradict the curated profile |

Every one of these is a **negative**, and every one is expensive. Meanwhile the
architecture prose that *mentions* SKSE is cheap to write and cheap to act on
incorrectly. So the model deliberately inverts the usual "longer and more
detailed wins" instinct: the terse table of things that do not work outranks the
long document that discusses them in passing.

## The engine constraints the model encodes

These are not arbitrary topic preferences. They are the specific limits the
Creation Kit and the game engine impose, which is what makes the weights
defensible rather than merely convenient.

| Constraint | Encoded as |
| --- | --- |
| FO4 Papyrus lacks CustomEvent, Debug, array length, CreateObjectAtForm, bare `Player`, `Start`/`Stop` | `objective[papyrus-correctness]`, `constraint` bonus |
| A `Native` script cannot hold properties or variables | `papyrus-correctness` markers |
| The CK has no scriptable interface, crashes, and has no CKPE | `objective[ck-constraints]` |
| xEdit headless blocks on a first-run notice, then takes ~3 min, and only documents some APIs | `objective[xedit-automation]`, `staleness` penalty |
| FormIDs move under modding, so references must be properties | `objective[facility]` |
| No F4SE loader is deployed, deliberately | `objective[layer-a]`, `load-order` |
| S0 is unproven because no BSScript vtable slot is hooked | `objective[s0]` at 1.3 |
| The xEdit API surface is only partly proven | `authority[unproven]` demotion |

## Authority tiers

Assigned per file by `classify_authority`, from an explicit `authority: <tier>`
line in its first 60 lines, else by keyword match. First match wins, lowest tier
first, so aspiration is demoted before judgement is.

| Tier | Weight | Meaning |
| --- | --- | --- |
| `compile-verified` | 2.60 | Checked by the real FO4 Papyrus compiler. |
| `measured` | 2.40 | Established by running something and reading the result. |
| `upstream-verbatim` | 2.10 | Authoritative source quoted exactly. |
| `derived` | 1.60 | Sensible, sourced, but not directly verified. |
| `judgement` | 1.00 | An opinion, dated and labelled. |
| `unproven` | 0.70 | Acknowledged as unproven. |
| `aspiration` | 0.35 | A dream, an idea with no path yet. |

`aspiration` is the lowest tier on purpose. A file that admits it is speculative
should not outrank a file that was compiled.

**616 of 646 files classify as `derived`**, so the authority signal is currently
concentrated in the curated layer. That is honest rather than a defect: most of
this repository is code and logs with no claim to make about authority. If the
model is to bite harder, the lever is adding `authority:` lines to more files,
not inflating the tiers.

## Measured effect

Query: `CustomEvent SendEvent SKSE only not in FO4`

| | top hit | second |
| --- | --- | --- |
| `--no-weights` (pure BM25) | `project_blueprint.md` (judgement) | `PIP-MON_CONSOLIDATED.txt` |
| default | `papyrus_syntax_rules.md` (compile-verified) | `papyrus_syntax_rules.md` |

Full breakdown of the winning hit:

```
w=authority[compile-verified]=2.600 curated=1.350 objective[papyrus-correctness]=1.250 constraint=1.300
```

5.70x total. This is the intended behaviour: a question about whether a Papyrus
construct exists should be answered by the compiler-verified table of
constructs that do not, not by architecture prose that mentions the topic.

## Other multipliers

- `curated` 1.35 for `ai_context/` excluding `reference/`. Upstream names are
  authoritative and still misleading; that produced one wrong recipe.
- `constraint` 1.30 for chunks stating a limit, prohibition or negative result.
- `stale` 0.85 for chunks whose own text declares a dated current-state claim.
  Retrieval cannot fix a stale file, but it can stop promoting one.
- `kind_weights` 0.8-1.0, a small nudge. `archive` at 0.9 because the
  inspiration archive is explicitly inspiration, not decisions.

## Changing it

Edit `ai_context/ranking.json` and reindex. Never hardcode a weight in the
tools; that is how a model stops matching the policy it claims to implement.

Every key carries a `_comment` explaining why it has the value it has. A weight
without a stated reason is a weight nobody will dare to change and nobody will
remember.

```powershell
tools\pipmon.ps1 rag index
tools\pipmon.ps1 rag query -Query "..." --explain      # audit the breakdown
tools\pipmon.ps1 rag query -Query "..." --no-weights    # A/B against raw BM25
```

## Limits, stated plainly

- **Still lexical.** Multipliers reorder lexical matches; they do not create
  semantic understanding. Vocabulary expansion widens recall, weights reorder
  what comes back. Neither comprehends.
- **Authority is per file, not per section.** A file containing one measured
  finding and fifty opinions is weighted as one measured file. This is the
  model's largest known distortion.
- **Objective markers are substring heuristics.** They will drift as vocabulary
  changes and will occasionally fire on unrelated text.
- **The weights are policy.** `--no-weights` exists so the effect of the policy
  is always visible and always arguable. A ranker whose weights cannot be
  compared against its own baseline is how a workspace starts confidently wrong.
