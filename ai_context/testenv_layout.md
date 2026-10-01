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
