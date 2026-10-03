---
title: Creation Engine boundary mechanisms — skeleton
purpose: >
  Every way the engine can stop a player leaving an area, ranked by how well it
  survives scrutiny. Read before building any wall, fog ring, or edge. INERT —
  nothing here has been built, and the two obvious candidates are both weaker
  than previously believed.
authority: measured
status: SKELETON — INERT
---

# Creation Engine boundary mechanisms

> **STATUS: SKELETON. INERT.**
>
> This file **corrects two things that were previously planned on and should
> not have been.** No boundary has been built, placed, or tested in game. The
> ranking below is a research result, not a validated design.
>
> The two corrections matter enough to lead with:
>
> 1. **"No navmesh" does not stop the player.** It only stops AI pathing.
> 2. **DBLOCK could not be confirmed to exist** as a Creation Engine feature.

---

## 1. The correction that changes the design

An earlier draft of this project proposed: build the playable area, omit navmesh
beyond it, and rely on the player being unable to path there. **That is wrong,
and the error was in assuming navmesh governs player movement.**

Navmesh absence produces these outcomes:

| Mechanism | Navmesh blocks it? | Basis |
|---|---|---|
| AI pathfinding | yes | by definition |
| **Player walking** | **no** | "the player can walk anywhere and doesn't really need any navmesh" |
| `MoveTo` / scripted teleport | no | Papyrus movement ignores navmesh |
| Vehicles | no | physics, not navmesh |
| Jumping, falling | no | physics, not navmesh |
| Fast travel | no | marker-based, not navmesh |
| Followers | partly | path via AI, but also physically follow the player |
| Recast generation | may regenerate over it | re-lays navmesh where it finds walkable surface |

**So an 88 m margin with no navmesh is not an unreachable margin — it is a
margin the player walks into freely.** Any design that relies on missing navmesh
as the wall is broken, and it fails most visibly against the player's own
movement, which is exactly the thing it was supposed to prevent.

There is a second-order consequence: `ai_context/cre_spatial.md` and
`docs/diagrams/paradise_bubbles.svg` both present the unloaded outer ring as
"not reachable." That claim is **retracted** pending re-authoring. The ring is
unloaded; it is not unreachable.

---

## 2. DBLOCK — unverified, and previously relied on

Earlier drafts proposed a **distant block (DBLOCK)** as the large fog-coloured
boundary ring. A targeted search for the term across general web, the Fallout
Wiki, Nexus, and UESP returned **no Creation Engine documentation of any kind** —
no primary source, no reverse-engineering reference, no community documentation.

**Status: unverifiable from public sources.** Not asserted to exist, not
asserted not to exist. It is a lead with nothing behind it.

The cheapest test is 15 minutes: search the CK object palette for "distant" and
"block", and search `Fallout4.esm` EditorIDs. **Not run.**

What *is* documented, and is the better candidate:

- **`xLODGen` / `FO4LODGen` / `DynDOLOD`** — reverse-engineered, real, produces
  `.bto` low-poly silhouettes in `Data\Meshes\terrain\<Worldspace>\`. Vanilla
  uses it for the Boston skyline and distant trees. But it is **per-object
  silhouette, not a continuous ring**, so it will not read as a wall.
- **Border regions** — vanilla, and the polygon is **redrawable in the CK
  region editor**. This is a controllable arbitrary boundary shape, and is the
  mechanism vanilla uses for its own "You cannot go that way" walls. **This is
  the leading candidate and it has not been tested.**

---

## 3. Ranked options

| Mechanism | Strength | Confidence | Cost |
|---|---|---|---|
| **Border region, redrawn** | arbitrary polygon, vanilla, proven to enforce | LIKELY | editor work, no runtime cost |
| **Collision lip / low wall** | simple, unmissable, covers walking and jumping | LIKELY | needs geometry, visible |
| **Worldspace edge + fog** | reads as a natural limit | LIKELY | fog alone is not a wall |
| **OnTriggerEnter pushback** | last-resort, covers the player and vehicles | LIKELY | visible hitch, script cost |
| **`MoveTo` on interior** | the bunker already uses doors | CONFIRMED | load screen |
| Absent navmesh | **stops AI only** | CONFIRMED | **not a wall** |
| DBLOCK | **unverified** | **UNRESOLVED** | unknown |
| xLODGen ring | not a ring | CONFIRMED (wrong tool) | high build cost |

**Best combination, per the research:** border region for the outer bound, a
collision lip so the boundary is visible and physically enforced, and an
`OnTriggerEnter` correction as a backstop for scripted movement and vehicles.
That covers every row in the §1 table except fast travel, which is
marker-based and must be handled by not placing a marker there.

**None of this has been built.** The combination is a proposal.

---

## 4. Precombine and the 3x3 cluster trap

**CONFIRMED mechanism, UNRESOLVED timings.** Previs clusters are 3×3 exterior
cells sharing one `.uvd` file, and "a Cell can only be a member of one Cluster."

The consequence that bites us:

> if the cell is in the corner of a cluster, the CK will build previs for 4
> clusters. You specified one cell to be rebuilt yet you have effected 35 other
> cells.

A **centre** cell touches 1 cluster, an edge cell 2, a corner cell 4. So the
cheapest module boundary is a **3×3 block of cells centred on a cluster
centre** — this is a hard constraint on how the test environment is divided into
modules, independent of how large it is.

Two further confirmed facts:

- The **CK GUI can only produce Filtered** precombine. Clean is command-line
  only. Filtered is "generally 5-10 times" bigger than Clean.
- Editing anything in a cell breaks that cell's precombine and disables previs
  for the whole 3×3 cluster. **Adding does not break; deleting or altering
  does.** Any `LAND` edit appears to disable precombination entirely.

---

## 5. Skipping precombine is a legitimate choice

**CONFIRMED, with UNRESOLVED limits.** `bUseCombinedObjects=0` and
`bPreCulledObjectsEnabled=0` under `[General]` make the engine load each
reference's own 3D individually. Visually correct. The documented cost:

> with previs disabled all surfaces of all items in that 3x3 area are being
> rendered — that's a huge increase in the processor load and will almost
> always lead to significant fps drops or crashes.

**No documented per-cell object or triangle budget exists.** Searched
specifically; settlement budgets are a different subsystem and must not be
transferred. So the threshold at which skipping precombine becomes unsafe is
**unknown and must be measured.**

For a test environment with low object counts this is a defensible choice, and
it eliminates all the cluster-boundary complexity in §4. Decide after measuring.

TODO: build one representative cell at expected worst-case density, load it with
both settings, measure. This is the same measurement listed in
`ai_context/tparadise.md` §4 and it settles both the density question and the
worldspace-size question.

---

## 6. Geometry limits

| Limit | Value | Confidence |
|---|---|---|
| Worldspace cell ceiling | 64x64, -32..+31, ~3.75 km | LIKELY, community |
| X-vs-Y cell asymmetry | — | **UNRESOLVED.** Searched; no source. Do not design around an X-only limit. |
| Vertical band | +/-30,000 units = +/-428.6 m | LIKELY, community, reported for **Skyrim SE not FO4** |
| Vertical streaming | does not exist — 2D grid only | CONFIRMED by construction |
| Worldspace small-world flag | CK `WorldSpace` page has a "Small World" field | LIKELY, unexamined |
| Float32 precision | ULP 27.9 µm at 300 m depth | CONFIRMED by arithmetic |
| Float32 hard cliff | integers exact to 2^24 units = 240 km | CONFIRMED by arithmetic |

The +/-30,000 figure comes from Rob's Bug Fixes (xEdit scripts by
robertgk2017/Kojak) and is reported for **Skyrim Special Edition**, not FO4. FO4
shares the lineage but no FO4-specific confirmation was found. The reported
symptom is micro-stutter from navmesh specifically, and **the mechanism is not
explained in any source** — the engine slows down is an observation, not a
diagnosis.

The float32 numbers are our own arithmetic, not an engine claim, and they are
comfortable at the depths in play. The live risk is that precision degrades with
the **magnitude of the horizontal coordinate**, not with depth — so a worldspace
placed at a large vanilla X/Y offset is worse than one near origin. That is a
design recommendation, not a documented rule.

---

## 7. What is NOT known

- **Not tested:** whether a redrawn border region enforces as expected.
- **Not searched:** whether DBLOCK exists, in the CK or in `Fallout4.esm`.
- **Not measured:** the per-cell object budget, so the no-precombine threshold
  is unknown.
- **Not measured:** per-cell or per-object precombine time. No published figures
  exist; only whole-patch anecdotes like "1hr+" and "6hr+", and CK crashing
  "roughly once per 3-4 hours". **Do not scale those anecdotes to this project.**
- **Not confirmed for FO4:** the +/-30,000 unit Z band.
- **Not measured:** the worldspace ceiling in the CK's own Heightmap Editor, or
  whether X and Y differ.
