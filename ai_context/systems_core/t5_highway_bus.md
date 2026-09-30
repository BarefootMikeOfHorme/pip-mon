---
title: T5 Hallway / Highway bus — architecture overview and proper use
scope: meta
authority: measured
purpose: >
  What the T5 access layer is, how data crosses it, and what code may and may
  not do with it. This is the RAG's SHORT orientation, deliberately. The heavy
  design record stays in PIP-MON_CONSOLIDATED.txt section 26 and HANDOVER.md,
  which are the doors; this is the sign at the entrance.
heavy_docs:
  - PIP-MON_CONSOLIDATED.txt   # design record, section 26.5 is authoritative
  - HANDOVER.md                # lines 55-80 carry the tier table and these rules
  - docs/IPC_PROTOCOL.md       # partly fiction, see HANDOVER section 11
---

# T5: the hallway, the highway, the bus

## What it is, in one paragraph

T5 is a **stateless access layer**. It is *not* a sixth tier and must never
become one. It owns no data and holds no state. Its whole job is to let a
consumer — a human at the dashboard, a CLI, a Papyrus script, or another
provider's model — find its way to an answer without the layers below having to
be made comfortable for the reader. It provides four things: **signage**
(what capabilities exist), **depth control** (how much detail), **provenance**,
and **polite refusal** (a clean "no" instead of a wrong answer).

## The highway-with-amenities reading

The better mental model is a **highway or hallway with amenities**, not a
conduit. A traveller walking it does not follow one fixed route. They **pick**
which way to go at each junction, and they **align to a task** as they walk —
narrowing, backing up, or descending when what they need changes mid-journey.

That is what the amenities are for:

| amenity | what it lets a traveller do |
|---|---|
| signage | see what exists before committing to a direction |
| depth control | choose how much detail they can afford to read |
| provenance | trust a sign, or refuse it and check the source |
| polite refusal | learn a route is closed, and why, without hitting a wall |

So the hallway's value is not that it carries anything. It is that it makes
choosing cheap, and that a consumer can re-aim without starting over. A layer
that forced a single path, or that could only be traversed at one fixed depth,
would be a corridor with a turnstile — and would push people to bypass it.

## The tiers it sits over

| Tier | What it is | Written for | Cost allowed |
|---|---|---|---|
| T0 | `Fallout4.exe` as bytes | accuracy | raw, no comfort |
| T1 | Oracle: extracts facts from T0 | provenance | slow, offline |
| T2 | Library: the facts, queryable | speed | zero-alloc in-game |
| T3 | Surface: `PIPMON_*`, V-Link, `PipMon:` | explicitness | versioned, refuses cleanly |
| T4 | Consumer: dashboard, CLI, Papyrus | clarity | the user's language |
| **T5** | **Hallway: navigation, depth, provenance, refusal** | — | **may only render or descend** |

## The two rules that constrain everything

1. **A layer may never be made more comfortable than its cost allows.**
2. **The hallway may only RENDER or DESCEND. It may never raise a tier's cost
   ceiling.**

So "go deeper" always means dropping to a *lower* tier. It never means making T0
or T2 perform user-level work. If a request would require T2 to allocate, or T0
to be interpreted, the answer is to descend, not to optimise the lower tier into
something it is not allowed to be.

## Depth: the one axis that matters

| depth | Returns |
|---|---|
| 0 | one-line verdict |
| 1 | per-tier summary |
| 2 | per-fact, each with provenance |
| 3 | raw bytes |

Depth is the whole interface. A consumer should be able to ask for 0 and get
something readable, then ask for 3 and get the ground truth, without the layers
in between changing behaviour.

## Proper use, and proper non-use

**Use T5 to:** find that a capability exists; get a verdict at a chosen depth;
carry provenance alongside any fact; and be told cleanly when something is not
available.

**Do not use T5 to:** store anything; cache anything; hold a session; translate
between formats on the way through; or make an upper layer's answer available
because a lower layer could technically produce it.

On serialization: control signals on the T5 path stay **lightweight and
inspectable** — JSON, with YAML a reasonable alternative. A reader who asked a
question must be able to read the answer in a text editor.

**For the systems core boundary the representation is STRUCTS, not CBOR and not
a bespoke message format.** Typed, language-native structures on both sides of a
Rust/Python boundary: a Rust struct mirrored by a Python dataclass or a
`#[pyclass]`, with the schema declared in one place. The reasons are the ones
that matter here — a struct is checkable by a linter, diffable in review,
readable in a debugger, and impossible to misparse silently. CBOR-LD and other
self-describing binary schemes were considered and **rejected for this path**:
they trade inspectability for compactness, and compactness buys nothing at our
volumes while removing the ability to read a payload without running the
reader. If a bulk path ever does need a binary stream, that is a separate route
with its own spec entry and its own decision record, not something the hallway
launders into existence.

**PyO3 is NOT currently installed.** Verified absent from the repository. The
`systems_core/pyo3/` reference material is held for a *planned* Rust/Python
bridge, not for code that exists. `ai_context/tech_stack.md` records the
distinction and must keep doing so.

## The doors, and the registry that keeps them real

A hallway with no door inventory is a corridor. The full inventory lives in
`ai_context/systems_core/door_registry.json`, and `tools/door_lint.py` checks it.

The design record already carried a ten-row door table by hand — `design`,
`resume`, `readme`, `licence`, `protocol`, `rules`, `anomalies`, `arch`,
`logging`, `papyrus-flags` — and two more the hallway *wanted*: the **SCHEMA
DOOR** and the **DOCS DOOR**. Both are now built. Seven more were added for the
retrieval, spec and gate work, which is how a hand-maintained table stops being
complete: somebody adds a document and nobody records that it is now a way in.

So `door_lint.py` also reports **unregistered candidates** — any top-level or
`docs/` markdown file that is not in the registry. That is the only way the
inventory stays honest as the program grows.

Each door records: the **question** it answers, its **path**, its **state**, and
its **keeper** — the check that keeps it from rotting. A door that names a
keeper which does not exist, or which exits non-zero, fails the lint. A door
guarded by something broken is worse than an unguarded one, because it is
trusted.

### The doors

| id | answers | state |
|---|---|---|
| `design` | what is the design and why | CURRENT |
| `resume` | where did we get to | CURRENT |
| `readme` | what this claims to be, and what it does not | CURRENT |
| `licence` | what are the terms | CURRENT |
| `protocol` | what travels on the wire | PARTLY_FIXED — documents three things that do not exist |
| `rules` | which rules are inviolable | STALE — PITFALL 1 uniquely valuable, preserve it |
| `anomalies` | what counts as an anomaly | CURRENT |
| `arch` | thread model, prefix constraint | SUPERSEDED — do not delete |
| `logging` | what a log line looks like | CURRENT |
| `papyrus-flags` | which compiler flags, and why | CURRENT |
| `schema` | the address-blob format | BUILT |
| `docs-index` | which document answers which question | BUILT |
| `tier` | what T0–T5 are, and what the hallway may do | BUILT |
| `vendor` | what third-party code we took, and what we use it for | BUILT |
| `papyrus-language` | what FO4 Papyrus can actually do | BUILT |
| `xedit-api` | what FO4Edit 4.1.5f can actually call | BUILT |
| `record-format` | what a plugin file looks like on disk | BUILT |
| `nomenclature` | what each word denotes | BUILT |
| `ba2` | the BA2 container layout | BUILT |
| `address-mapping` | how an address database is built and read | BUILT |
| `xedit-automation` | how people actually write xEdit Pascal | BUILT |
| `ckpe` | how someone else solved our editor problems | BUILT — ideas only |
| `retrieval` | how to ask this knowledge base something | BUILT |
| `goal-alignment` | do the gates serve the goals | BUILT |
| `stack` | what is installed versus proposed | BUILT |
| `live` | what the game is doing right now | BUILT |

**Not doors**, deliberately: `third_party/**` is vendored source, registered
separately in `vendored_libraries.json`; `ai_context/reference/**` is upstream
documentation captured verbatim; `runs/**` is evidence, not a way in.

## Cross-environment routing, in brief

Producer side: the game and our native layer emit onto the wire (T3 / V-Link).
T2 holds the queryable facts. T5 sits above and renders them for T4 consumers —
the dashboard, the CLI, a Papyrus caller — and for `tools/ai_watcher.py`, which
republishes live state to a file so that no agent has to sit in a blocking
terminal loop waiting for the game.

The telemetry file is a **T4 artifact**, not a T5 one. The hallway does not
watch anything; `ai_watcher.py` does, and it is a separate process on purpose.

## The rule that outranks all of the above

**A fact with no provenance may not exist.** Hand-authored symbol names are
*queries*, never facts. This is why every retrieval hit in this workspace
carries a path, a line range and a hash, and why `rag_query.py --explain`
exists: a reader must be able to check the claim against the file it came from.
