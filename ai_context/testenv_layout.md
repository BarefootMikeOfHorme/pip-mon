# Test environment: region, layers, and the fast-travel chain

Research note, 2026-10-01. Written to settle the layout question before any code,
because the doables and the not-doables are decided by the engine and the CK, not
by preference.

Sources: fallout.wiki CK pages (Cell, WorldSpace, Door, Cell ID),
`ai_context/fo4_records_guide.md` s7, and a Nexus CK discussion on interior fast
travel. Claims below are sourced or marked unverified.

---

## 1. The container model, and why "layer" is not the word

The instinct to think of the bunker as *inside* the field is natural and wrong.
FO4's containers do not nest the way the example suggests.

**Exteriors are a flat grid, not a tree.**
> Exterior cells belong to a World Space, and seamlessly join to one another in a
> huge continuous landscape. Each exterior cell is 4096×4096 units, ~58.5m square.
> All exterior cells are automatically given a grid number representing their [X,Y]
> position from the centre of the world.

**Interiors are separate universes, entered by a door.**
> Interior cells are entered through a load Door linked to another cell… When
> inside an interior, the exterior world is no longer visible. Each interior cell
> is essentially its own universe.

**The only nesting that exists is worldspace → worldspace.**
> Parent Worldspace: if NONE, the worldspace has its own editable landscape;
> otherwise it uses the landscape of its parent.

**Interiors are the part that genuinely composes.**
> Interiors can be composed of multiple cells broken up by load doors, or exist
> as one large cell.

So the structure for this environment is:

```
WORLDSPACE                the map region we pick
  ├─ exterior CELL  grid (x,y)   the field, the woods -- seamless, adjacent
  │     └─ DOOR (load) ────────────────┐
  │                                     │ both ends linked to each other
  └─ interior CELL  (its own universe) ┘
        └─ interior CELL  (next room)  -- a real tree, via doors
```

The bunker is not a child of the meadow. It is a **sibling** reached through a
door. What makes it feel nested is shared `LOCATION` and `ENCOUNTER ZONE`, not
the record tree.

**This is the practical consequence:** the field and the woods are *one* module
with N cells. The bunker is *another* module with its own cells and doors. They
compose by reference, not by containment.

---

## 1b. Where an off-map location actually sits on the physical map

Two different mechanisms, and which one you want is a design decision, not a
technical constraint.

**Option A — its own map, Far Harbor style.** A `WRLD` with its own map data has
its own map screen:

> Use Map Data: the world map texture file for this WorldSpace.
> Map Image: select the DDS file to use.

Far Harbor and Nuka-World both work this way. Each has its own map image, so the
location appears on **its own map and nowhere on the Commonwealth map**. The
player reaches it the way they reach Far Harbor — not by walking the main map.

**Option B — parented, and pinned to a point on the Commonwealth map.** Set a
`Parent Worldspace` and give it world map offset data:

> World Map Offset Data: the offset of the location for the **Parent's** world
> map. This is used to line up the map marker with where the WorldSpace would be
> on the world map.
> Cell X Offset / Cell Y Offset / Cell Z Offset / World Map Scale / Hide Map Markers

So an off-map worldspace is not invisible on the map. It can be *placed* on the
parent map at a chosen offset, and its markers line up there. `Hide Map Markers`
suppresses them if you want the reverse.

**So the answer to "where would it be placed" is: you choose, and there are two
shapes for it.** Either it gets its own map (Far Harbor model), or it is pinned
at an offset on the Commonwealth map (parented model). The second is closer to
what most people picture when they say "somewhere on the map."

**Two related fields that matter either way:**
- `WRLD` → **Hide Map Markers** — suppress markers for this worldspace
- `WRLD` → **Encounter Zone** and **Location** — world-wide, and the
  worldspace-level encounter zone is what NPCs are scoped by
- `WRLD` → **No Landscape / No Sky** — for interiors dressed as a worldspace
- `WRLD` → **Small WorldSpace** — a real performance flag: *"Mark this as a
  small WorldSpace. This speeds up certain processing for smaller WorldSpaces."*
  Directly relevant to a test environment, which is exactly the wrong size to be
  optimising for.

**On the "another instance" instinct — it is correct, and Far Harbor is the
proof.** Far Harbor is a separate worldspace, not a region of the Commonwealth.
The engine treats it as its own instance with its own map, weather, and loading.
That is the shape a bunker-of-our-own wants if it is to be somewhere distinct
rather than tucked into an existing cell.

**Caveat on scale, from CK modders building custom worldspaces:**
> The max map size allowed by the Creation Kit editor is 64x64 Cells, with
> negative and positive (-32, +31)… Bigger world can be made with external
> tools. There is a bug that makes maps bigger than ±64 cells on the X axis not
> work properly.

So a custom worldspace is bounded, and the bound is known-broken past 64 cells
on X. For a test environment that is generous.

**Unverified:** whether the world map offset survives being authored headlessly,
or whether it is a CK-only field like precombine. `xEditAPI.pas` exposes
`SetEditValue` and this is a field-set operation, so it is *probably* reachable
from a script, but that has not been tested. It should be probed before any plan
depends on it.

---


This is the part that constrains the design most, and it is not "make the door
fast travel".

**A door is not a fast travel point.** Doors have no destination of their own:
> Doors themselves aren't set up to take you to a specific location… you do so by
> placing both ends in the editor, and then modifying both of those References to
> link them together.

**Fast travel into an interior needs a three-part chain:**

| Part | Where it lives | What it is |
|---|---|---|
| the map marker | **exterior** cell | the point the player selects on the map |
| the XMarkerHeading | **interior** cell | where the player actually arrives |
| the link | between them | marker → marker heading |

> To allow fast travel into an interior settlement the map marker must be in an
> exterior cell, then linked to an XMarkerHeading in the interior cell. That can
> either be a specific fast travel marker, or the center marker. A dedicated
> marker is recommended.

**Fast travel back OUT is a cell flag:**
> right click the cell name in the Cell window, choose Edit, then make sure that
> "Can't travel from here" is **NOT** checked.

`CELL` also carries a "Can't Travel From Here" field, and `WRLD` has
"Can't Fast Travel From Here". Both must be clear or travel out is blocked.

**Settlers do not use the map marker.** This is the trap:
> Settlers are not looking for the MapMarker, they are looking for the XMarker…
> As long as the exterior cell and the interior cell **share the same Location and
> Encounter Zone** settlers have no problem walking through the load door.

So player fast travel and settler pathing are satisfied by **different** things.
Matching `LOCATION` + `ENCOUNTER ZONE` across the exterior and interior is what
makes NPC assignment work, and it is independent of the marker chain.

**Navmesh must be finalised** for NPCs to path to the marker at all.

---

## 1c. Build order, and the cohort

Owner direction, 2026-10-01. This supersedes the ordering in section 4 where the
two disagree.

**Paradise first, alone, until it is boring.** Built, recorded, validated, marked
stable, with a backup that reverts it. Only then does anything get attached to it.
A half-built environment plus an attached door is two variables changing at once,
and then a regression belongs to neither.

**Then the bunker door**, as a separate, independently revertible step.

**Bunker identity, resolved from the load order:** it is
`Cotozic's Bunker Ravine.esp` — already entry 61 in `dplugins.txt` and installed
in `Data\`. It is a mod, not vanilla. So:

- **Does it already have a door in its own cell?** Answerable by dumping that
  plugin's records with xEdit. Cheap, and it settles the question instead of
  guessing. If it has one, use it. If not, source a door asset and place it.
- **Is it in a ravine?** Unverified, and it decides the dependency direction. A
  ravine bunker has no world-facing entrance, so paradise must be shaped around
  it rather than the bunker being placed in paradise. Do not decide this by
  assumption.
- Native doors, windows and openings on the existing model would be the cheapest
  path, since geometry and collision already exist and only the link is new.

**Fast travel to the bunker**, mat-style, using the chain in section 2. Not a
first step — it needs a destination that already exists.

### NPC cohort

Purpose: something for the tooling to observe. Pathing, behaviour, interaction
with the environment, and dialogue as an avenue.

| Property | Value | Why |
|---|---|---|
| Pool size | 10 | enough for variation |
| Loaded at a time | 3–5 | keeps a run readable and attributable |
| Selection | **ordered, not random** | a reproducible comparison needs a fixed cohort; random selection makes two runs non-comparable |
| Load timing | at environment load, the bunker | the cohort is part of the instance, not spawned on demand |
| Vendor | a bartender-style NPC | gives a working trade avenue to test |
| Workshop | required, must function | a workshop that does not work is not a test environment |
| Terminal | required, must function | the in-game surface PIP-MON exposes |

**Named starting cast**, each chosen because it exercises a different axis:

- **Metro** — long, specific, repetitive traversal. His paths and patterns are
  the cleanest available signal for the loop and pathing detectors.
- **Codsworth** — the observation and interaction baseline, and the natural
  "does the scripted-actor surface work" case.
- **The bartender** — the vendor avenue, and a dialogue-dense case.

Cohort membership per run is a declared input, not a discovery, so a result
attributes to the cast that produced it. The full roster of ten is a succession
of these, expanded as the environment supports it.

**Bunker adaptation is unresolved and gated on inspection.** Whether it sits in a
ravine, whether it has windows, and whether it has native door mechanisms all
change what paradise has to be. Inspect the plugin before designing paradise
around it.

### Method

The CK command list and the build recipes are refined *against* environment
output — what a run actually produced — not in the abstract. Slow and steady: one
module, recorded, validated, backed up, then the next.

---

### Paradise size — unresolved, and the unit matters

Stated as "600, about the same diameter width as the paradise env". The unit is
load-bearing, because the CK scale is:

> Each exterior cell is 4096×4096 Creation Kit Units, or approximately 192×192
> ft, or 58.5×58.5 m

So 1 unit ≈ 1.43 cm, and the two readings are wildly different:

| Reading | Actual | Verdict |
|---|---|---|
| 600 **units** | 8.6 m across | a closet. No Vertibird, no landing pad, no walking room. |
| 600 **metres** | ~10 cells across, ~60,000 units | a small valley. Vertibird fits, backdrop works. |

Given a Vertibird landing pad is wanted, it has to be the metres reading. A
10-cell worldspace and a 1-cell worldspace are entirely different precombine and
LOD jobs, so this must be settled before `M0` is built.

Modder practice for a small custom worldspace: make the **playable area ~15–20%**
of the worldspace and let the remainder be unreachable backdrop. FO4 itself does
this — 15–20% playable, the rest mountains and ocean.

### The fog border is not a walk-blocker

Hiding terrain and blocking movement are different operations:

> Quad (1–4): Which Quad of the Exterior Cell you want hidden. **Note that even
> though the landscape is invisible the collision still remains.**

So `Force Hide Land` and hidden quads give visual fog while the player can still
walk off the edge. "Cannot walk past the border" needs real collision —
invisible walls, or worldspace bounds plus a navmesh and land-data edge. That is
a build step with its own module, not a field checkbox.

### Planned but not now

A Vertibird landing pad inside paradise — placed somewhere realistic, explicitly
**not on the door** — plus a Vertibird cutscene entrance, for exercising
Vertibird variables. Deferred; recorded so it is not rediscovered later.

---

## 2. Fast travel into an interior — the actual rules

This is the part that constrains the design most, and it is not "make the door
fast travel".

**A door is not a fast travel point.** Doors have no destination of their own:
> Doors themselves aren't set up to take you to a specific location… you do so by
> placing both ends in the editor, and then modifying both of those References to
> link them together.

**Fast travel into an interior needs a three-part chain:**

| Part | Where it lives | What it is |
|---|---|---|
| the map marker | **exterior** cell | the point the player selects on the map |
| the XMarkerHeading | **interior** cell | where the player actually arrives |
| the link | between them | marker → marker heading |

> To allow fast travel into an interior settlement the map marker must be in an
> exterior cell, then linked to an XMarkerHeading in the interior cell. That can
> either be a specific fast travel marker, or the center marker. A dedicated
> marker is recommended.

**Fast travel back OUT is a cell flag:**
> right click the cell name in the Cell window, choose Edit, then make sure that
> "Can't travel from here" is **NOT** checked.

`CELL` and `WRLD` both carry a "Can't Fast Travel From Here" field, and both must
be clear or travel out is blocked.

**Settlers do not use the map marker.** This is the trap:
> Settlers are not looking for the MapMarker, they are looking for the XMarker…
> As long as the exterior cell and the interior cell **share the same Location and
> Encounter Zone** settlers have no problem walking through the load door.

So player fast travel and settler pathing are satisfied by **different** records.
Matching `LOCATION` + `ENCOUNTER ZONE` is what makes NPC assignment work, and it
is independent of the marker chain. **Navmesh must be finalised** for NPCs to
path to the marker at all.

**Vanilla allows exactly five interior fast-travel locations**: the Railroad HQ,
Home Plate, the Institute, the Mechanist's Lair, and Vault 88. Anything beyond
that is mod territory, which is why this is a deliberate build and not a checkbox.

---

## 3. Doables and not-doables

| Thing | Verdict | Why |
|---|---|---|
| interior cell with doors between rooms | **doable** | xEdit-generatable; no precombine needed |
| load door linking exterior ↔ interior | **doable** | both REFRs linked to each other |
| player fast travel into the interior | **doable, non-vanilla** | exterior map marker + interior XMarkerHeading + link |
| fast travel back out | **doable** | clear the cell's "Can't travel from here" |
| settler/workshop assignment inside | **doable** | shared LOCATION + ENCOUNTER ZONE across the two cells |
| exterior cells that render | **CK only** | see below |
| fast travel in survival, from interiors, always | **not doable vanilla** | F4SE mod territory ("Unlimited Fast Travel") |
| an off-map worldspace with its own map | **doable** | `WRLD` Use Map Data + Map Image (Far Harbor model) |
| an off-map worldspace pinned onto the Commonwealth map | **doable, unverified headlessly** | `Parent Worldspace` + World Map Offset Data; `SetEditValue` should reach it, untested |
| nested regions (field inside hill inside region) | **not a thing** | exteriors are a flat grid; only worldspaces nest |
| clean (unfiltered) precombine | **CK command line only** | GUI makes filtered only |

**The precombine wall, and why it splits the work in two:**
> Generating Precombines or Previs are 2 separate operations either way. The
> Creation Kit GUI can only create "Filtered" Precombines, whereas the
> Command-line can generate them "Clean" or "Filtered".

And from this repo, verified 2026-10-01: `xEditAPI.pas` exposes **no precombine
and no save function** — only the read-only `HasPrecombinedMesh` and
`PrecombinedMesh` queries. So xEdit can write exterior *records* but cannot make
them render.

**Therefore:**
- **Interiors → xEdit.** The whole headless generator track applies. Start here.
- **Exteriors → CK.** Records via xEdit, precombine via CK or its command line.

Note also: previs clusters are 3×3 exterior cells sharing one `.uvd`, and a cell
cannot belong to two clusters. So exterior module boundaries have to align with
the grid or precombine work multiplies.

---

## 4. Module boundaries for the test environment

Proposed, in dependency order. Each is independently loadable — that is the point
of layering them, and it is what lets a run test one thing at a time.

| Module | Records | Tool | Depends on |
|---|---|---|---|
| `M0.region` | pick the worldspace + the exterior cell grid coords we occupy | CK (precombine) | — |
| `M1.paradise` | the exterior area: REFRs, workshop, LOCATION | CK for precombine, xEdit for records | M0 |
| `M2.bunker_shell` | interior cell(s) + doors between rooms | **xEdit** | — |
| `M3.bunker_door` | the load door, both ends linked, exterior↔interior | xEdit | M1, M2 |
| `M4.fast_travel` | exterior map marker + interior XMarkerHeading + link | xEdit | M1, M2, M3 |
| `M5.npc_link` | shared LOCATION + ENCOUNTER ZONE, navmesh finalise | CK | M1, M2 |
| `M6.facility_plugin` | the records PIP-MON actually observes | xEdit | M2 |

`M2` is the one that unblocks everything else and is the one xEdit can do alone.
It is also the only module with no dependency, which makes it the honest first
target.

**Each module loads as an option** — the environment can be run with
`M0+M1+M2` only, then progressively more, and the differences are what the test
proves. That is the "load them all as options at first" idea, and it is sound:
each addition is one more layer, and a regression is attributable to the layer
that was added.

---

## 5. What this asks of the orchestrator

The orchestrator's job grows with module count, so the plan needs a shape that
scales without rewriting:

```
group      an environment, e.g. "paradise + bunker"
  task     a module, e.g. "bunker_shell"
    subtask  one step, e.g. "create interior cell", "link both door ends"
```

Three requirements that fall out of this, and which the current plan format does
not have:

1. **Relative ordering.** M4 cannot run before M3, but neither depends on M0. That
   is a DAG, not a list. The current `P1..P5` phases are a linear list and cannot
   express it.
2. **Optionality.** A module is either `required` or `optional`. A run selects the
   set, and the plan records which set ran, so a result is attributable.
3. **Per-module artifacts.** Each task produces its own report. Today every
   generator run writes one shared `gen-facility-report.json`, so two modules in a
   run overwrite each other's evidence — which is how a stale report became a
   green gate earlier.

Unverified, and worth checking before relying on it: whether xEdit's `Add` can
create a `DOOR` REFR with a link to a named form in one call, or whether the two
ends must be created and then linked separately. That determines whether M3 is
one task or two, and it is a cheap probe.

---

## 6. Unresolved, needs a decision from the owner

- Which worldspace region. Anything with a distinct silhouette is preferable so
  the built area is visibly ours, but that is a taste call, not a technical one.
- Whether `paradise` is a settlement (workshop + settlers) or just a location.
  Settlers pull in M5 and navmesh work; a bare location does not.
- Whether the base core should eventually include the frame for this or stay
  minimal, per the current plan to shrink toward 20-30 entries.
