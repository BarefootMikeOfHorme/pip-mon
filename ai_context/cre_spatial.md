---
title: Creation Engine spatial, weather and boundary architecture
purpose: Grid, units, transforms, trigger volumes, weather, and the mechanisms that can and cannot make a worldspace edge. Read before writing any .psc for the test environment, before placing anything in a cell, and before trusting a coordinate from any source.
authority: measured
trust: >
  The unit scale, the container model and the precombine wall are measured or
  compile-verified and are the load-bearing facts. The two corrections below are
  recorded because the source material this came from contained them and they
  would each have cost a rebuild.
---

# Creation Engine spatial, weather and boundary architecture

The source was an owner-supplied "Creation Engine Spatial & Coordinate
Architecture Matrix" plus a RAG seed-prompt matrix, 2026-10-01. It is
substantially correct and its framing of the boundary problem is better than
anything in the shipped game. Two of its numbers are wrong, and both are
recorded here rather than silently corrected, because the wrong versions are the
ones that will get re-proposed.

Engine: **Creation Engine**, `Fallout4.exe` FileVersion **1.11.240.0**, the
post-Next-Gen build. Same engine lineage as Skyrim; FO4 reuses the language and
the `.pex` format but not the function surface.

---

## 1. Corrections, first

### 1.1 The unit scale is 70 units/m, not 64

The source matrix states `64 units = 1.0 metre`, making an exterior cell
64 m × 64 m. The CK wiki states an exterior cell is 4096 × 4096 units =
**58.5 m × 58.5 m**, which is 70 units/m.

Spread: **9.4%**. Every dimension in the source blueprint is expressed in units,
so this compounds. **We use the wiki figure** (70 units/m) throughout this repo.

**Unresolved.** 64 and 70 are both in circulation and we have no first-party
source. The cheap decisive measurement: a Vertibird is a known real-world
length, so its NIF scale in the CK yields the actual conversion. Until that is
run, treat 70 as the working assumption and say so when quoting a real-world
size.

### 1.2 The in-worldspace Z-shift does not work

The source Module 2 proposes fading the screen, applying a vertical
Z-displacement of −2000 units, and arriving "directly beneath an exterior
waterfall **without crossing cell boundaries**", with the bunker as a
"subterranean interior" at its own water level `Z = −1200`.

This cannot work, and the source blueprint's own numbers are what expose it. A
Z-shift keeps the player in the **same cell**, and a cell is a single streaming
unit with one lighting set, one navmesh, one weather state and one audio
environment. A separate interior with its own water table, its own skybox
emittance and its own ambient descriptors is therefore unreachable by any
in-cell displacement.

The fix is not a smaller number. The fix is the mechanism the source already
lists first:

> **Choice A: Cross-Cell Teleport (XTEL / Interior Cell)**

A separate interior cell is a **load door** — a load screen, a new cell, its own
lighting/navmesh/weather. That is why the bunker mod needed an elevator, blast
doors and a power switch: those are the cost of a real instance change.

**The 60-unit sphere survives, with a different job.** It is a good *proximity
trigger for a load door* — the affordance that fires the transition. It is not
the transition. See §5.

---

## 2. The container model

Exteriors are a flat grid, not a tree.

> Exterior cells belong to a World Space, and seamlessly join to one another in a
> huge continuous landscape. Each exterior cell is 4096×4096 units, or
> approximately 192×192 ft, or 58.5×58.5 m.
> All exterior cells are automatically given a grid number representing their
> [X,Y] position from the centre of the world.

Interiors are separate universes reached by a door.

> Interior cells are entered through a load Door linked to another cell… When
> inside an interior, the exterior world is no longer visible. Each interior cell
> is essentially its own universe.
> Interiors can be composed of multiple cells broken up by load doors, or exist
> as one large cell.

The only nesting is worldspace → worldspace, via **Parent Worldspace**.

**Consequence for a house-in-a-field mental model:** the bunker is not a child of
the meadow. It is a **sibling** reached through a linked door. What makes it
*feel* nested is a shared `LOCATION` and `ENCOUNTER ZONE`, not the record tree.
The field and the woods are one module with N adjacent cells; the bunker is a
separate module.

---

## 3. Transforms, and the rotation locks

| Role | Subrecord | Constraint |
|---|---|---|
| Translation | `DATA` | Float32, metres = units ÷ 70 |
| Yaw / heading | `RotZ` | 0.00–359.99, the only free rotation on a landing marker |
| Pitch | `RotX` | **must be 0.00** on landing markers |
| Roll | `RotY` | **must be 0.00** on landing markers |

Handedness, as given: `+Z` elevation/sky, `−Z` underground, `±X` and `±Y`
horizontal. A **right-handed** Cartesian grid.

`RotX`/`RotY` locked to zero is not cosmetic — a tilted landing marker puts the
actor's feet off the navmesh and the engine either clips through the floor or
drops them. The source's guidance here is correct and worth keeping verbatim in
intent: *"confirm landing marker properties in the Creation Kit."*

---

## 4. The precombine wall — why exteriors need the CK

This is the single most consequential fact for scheduling the work.

- `xEditAPI.pas` exposes **no precombine and no save function**. Verified
  2026-10-01: the only precombine surface is the read-only `HasPrecombinedMesh`
  and `PrecombinedMesh` queries. xEdit can write exterior *records* but cannot
  make them render.
- The CK **GUI can only produce "Filtered" precombine**. Clean requires the CK
  **command line**. Precombine and Previs are two separate operations either way.
- Previs clusters are **3×3 exterior cells** sharing one `.uvd`, and a cell
  cannot belong to two clusters. So exterior module boundaries have to follow the
  grid or precombine work multiplies.

**Therefore: interiors are the xEdit track, exteriors are a CK track.** Starting
with an interior is not a shortcut, it is the only half that can be done
headlessly. Interiors also need no precombine at all.

---

## 5. Trigger volumes and state, the parts that carry over

The source's bounding-volume arithmetic is sound and is the correct way to build
a proximity affordance:

```
ellipsoid test, radii rx, ry, rz:
  ((x-x0)/rx)² + ((y-y0)/ry)² + ((z-z0)/rz)²  <=  1
inert outside, active inside
```

With `r = 60` units that is a **0.86 m** radius at 70 units/m. Adequate for a
door prompt, small for an environment — see §7.

**The state-machine point is the best engineering advice in the source and it is
correct.** An ESF `Auto State` / `State Active` transition is evaluated on
relevant events, whereas an `OnUpdate()` distance check runs **every frame per
object**. For a test environment that spawns NPC cohorts and watches them, the
difference is not marginal. Use state transitions; reserve `OnUpdate()` for
genuinely continuous things.

Papyrus used by the affordance: `OnObjectEnteredTrigger`, `MoveTo()`,
`Game.FadeOutGame`. All three exist in FO4.

---

## 6. Weather and seasons

Weather is **per-worldspace**, and the vocabulary is small and fixed.

**`WTHR` types** — the complete set:
`Clear, Cloudy, Fog, Rain, Snow, Thunder, Storm, Overcast, Mist`

Vanilla Commonwealth/DLC records, from the Biome mod's published table, with
their transition values:

```
CommonwealthClear         1,0000  Pleasant
CommonwealthMisty         2,0000  Cloudy
CommonwealthFoggy         2,0000  Cloudy
CommonwealthRain          4,0000  Rain
CommonwealthDarkSkies3    4,0000  Rain Thunder
DLC03_RadStorm            8,0000  Snow Thunder
DLC03_RadMistWeather      2,0000  Cloudy
DLC04NukaWorldRain        4,0000  Rain Thunder
```

**`CLMT` climate** holds the distribution and three independent dials:

```
bad_weather_factor   probability of adverse weather
wetting_factor       how fast surfaces wet
drying_factor        how fast they dry
```

Wet and dry being independent is most of what a season system needs. A
`Weather` **script** also exists in FO4 and is editable in the CK's Form Script
Editor, so seasons can be **driven by script** rather than authored as a fixed
rotation.

Worldspace fields that bind this together: `Use Climate Data`, `Climate`,
`Use Weather Data`, `Use Sky Data`, `SkyboxEmittance`, `Small World`.

---

## 7. The boundary — geometry, not a trigger

The design intent: an oblate spheroid of geometry centred on the local origin.
Inside is interactive. Outside is renderable and observable but not reachable —
you can see a storm arriving, feel the weather change on a delay, hear it, watch
birds, but you cannot reach out and touch it. And crucially **no invisible wall,
no "[You cannot go that way]"**.

That is a better design than the shipped game, which uses flat invisible walls at
a rectangle.

**The source blueprint's own radii do not scale.** `r = ±60` units is 1.7 m
across at 70 units/m — smaller than a person, and **34× smaller than one single
cell**. `r = 60` is a *trigger* radius, not an environment. Scaling it:

| r (units) | diameter | metres @70 | verdict |
|---|---|---|---|
| 60 | 120 | 1.7 m | closet — this is a door prompt |
| 700 | 1,400 | 20 m | yard; no Vertibird |
| 2,048 | 4,096 | 58.5 m | exactly one cell; a room, tight |
| **4,096** | **8,192** | **117 m** | **small valley. Vertibird fits, storm reads, backdrop works** |

**Proposed default: `r = 4,096`** — 2×2 cells, ~117 m across, with `r_z` flattened
to roughly 1,200 for the oblate profile and a distant-block fog ring beyond.

**Three candidate mechanisms, and only one of them is right:**

| Mechanism | Effect | Verdict |
|---|---|---|
| `bBorderRegionsEnabled=0` in `Fallout.ini` | **removes** the invisible walls and the message entirely | the opposite of what we want |
| **Distant block (DBLOCK)** | flat, cheap, LOD-friendly mesh, the engine's own distant-landscape primitive | **the boundary** |
| `Water` plane / kill volume | blocks or drowns on contact | reads as a bug, not a boundary |

The `No Map Borders` mod is the clearest evidence for the first row, and its
author's warning is the reason geometry must exist at all:

> The further out you go, the more things start to lose texture & lod quality and
> some textures and terrain will appear not to load at all.

`bBorderRegionsEnabled=0` is recorded here **as the thing to avoid**. It is also
a machine-wide `Fallout.ini` edit, which would affect every other test.

**Hidden quads are not a wall.** `Force Hide Land` and the per-quad visibility
flags change what is *drawn* and leave collision in place, so a player can still
walk off a visually fogged edge. A boundary needs real geometry.

---

## 8. The RAG seed-prompt matrix, kept

The source supplied four query prompts. Their status after review:

| Module | Prompt | Status |
|---|---|---|
| 1 | `XTEL` binary structure, door→landing marker displacement, `RotX`/`RotY` locks, navmesh door triangles | **keep** — correct and needed |
| 2 | zero-load-screen in-worldspace Z-shift | **rejected** — §1.2 |
| 3 | cross-cell environmental continuity: exterior lake Z vs interior water table, `SkyboxEmittance`, `AMBWaterfall`, fake view dioramas | **keep, re-scoped** — all of it only applies through a real interior cell |
| 4 | state-driven activation vs `OnUpdate()` polling | **keep** — §5 |

---

## 9. What is still unverified

- **The 64 vs 70 units/m spread.** Measure a known-length NIF. Until then every
  real-world size here is an assumption, marked as one.
- **Whether `WRLD` world map offset is reachable headlessly.** `SetEditValue`
  should write it; untested. A plan depending on it needs a probe first.
- **Whether xEdit `Add` can create a door `REFR` with a link in one call**, or
  whether both ends must be created and then linked. Determines whether the
  bunker door is one task or two. Cheap to probe.
- **Custom worldspace size ceiling**: 64×64 cells (−32 to +31), with a reported
  bug past 64 on X. Ample for a 2×2.
- **Modder practice for a small worldspace**: make the playable area 15–20% of
  the worldspace and let the rest be unreachable backdrop. FO4 does this itself.

---

## 10. Two bubbles — the streaming one already solves half the problem

Verified on this machine, 2026-10-01:

```
Documents\My Games\Fallout4\Fallout4.ini   L3:  uGridsToLoad=5
```

The engine streams a **square of cells around the character** and nothing beyond.
One grid = one cell = 4096 units = 58.5 m, so `uGridsToLoad=5` keeps up to
**293 m** of real cells resident. That is the entire reason the Commonwealth feels
enormous: the world continues past the loaded block, it is simply not in memory,
which is why removing the map borders produces missing textures rather than a
clean edge.

**There are therefore two independent boundaries, and they are not the same
thing:**

| | radius | what it is |
|---|---|---|
| **streaming bubble** | `uGridsToLoad` — 5 cells, 293 m | what *exists in memory*. Already present, at the default. |
| **playable boundary** | the oblate spheroid, 117 m at r=4096 | where the player can *go*. This is the new one. |

**The fit is good.** A playable region of r=4096 units (117 m across) sits at
**0.4x the loaded block**, leaving roughly 88 m of loaded-but-unreachable world in
every direction. That margin is the design working, not wasted space:

- **inside r** — playable, full navmesh, interactive
- **between r and the loaded edge** — still streamed, still rendered, weather and
  birds live here; unreachable because there is no navmesh
- **beyond the loaded edge** — unloaded; the DBLOCK fog ring and backdrop hide the
  seam

**Consequence: the boundary never has to fight the engine.** No kill volume, no
invisible wall, no cvar edit, no "You cannot go that way". Place the fog ring at
the *playable* edge rather than the *loaded* edge and the player can never reach
the loading boundary, so the seam is never visible.

**`uGridsToLoad` is a lever we are deliberately not pulling.** Dropping it to 3
(176 m) would put the loaded block almost exactly at the playable edge and cut
memory — but it is a machine-wide `Fallout4.ini` setting that affects every other
test, and the default 5 already gives the margin this design needs. Change it
only if memory becomes the binding constraint, and never in the same rig as
`bBorderRegionsEnabled`.