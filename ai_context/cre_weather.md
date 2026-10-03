---
title: Creation Engine weather — skeleton
purpose: >
  Weather, lighting, sky, visibility and seasons in Creation Engine, and the
  limits on scripted control of them. Read before authoring any WTHR, CLMT, or
  weather-driven design. INERT — no mechanism here has been built or tested.
authority: unproven
status: SKELETON — INERT
---

# Creation Engine weather

> **STATUS: SKELETON. INERT. Not a build plan and not a design.**
>
> Every mechanism below is named so it can be looked up. **None has been
> authored, loaded, or observed in game.** No `.wthr`, `.clmt`, or `.esl` for
> weather exists in this repo. Anything built from this file is untested.

Everything here is **LIKELY or UNRESOLVED** except the engine version and the
`.esl` container fact. The intended use — a storm front observable before it
arrives — has a hard requirement that is not yet satisfiable from public
sources; see §5.

---

## 1. The file surface

| File | Holds | Confidence |
|---|---|---|
| `.wthr` | weather class: precipitation, wind, particles, transitions, cloud cover | LIKELY |
| `.clmt` | classification: cloud layers, colours, fog densities per layer | LIKELY |
| `.esl` | loads both, and carries the active-weather list | LIKELY |

WTHR/CLMT are the standard Creation Engine weather pair and are the same across
FO4 and Skyrim. **Exact subrecord layout is NOT read** — see `ai_context/spec/`
and the surface-material notes.

**Unproven:** whether a test environment can override weather per cell, or only
per worldspace. This decides whether the bunker and the meadow can hold
different weather, which the layout in `ai_context/testenv_layout.md` assumes.

---

## 2. Interiors and weather

**CONFIRMED (container model):** an interior cell is its own instance, with its
own lighting, navmesh and weather. From `ai_context/testenv_layout.md` §1:

> Interior cells are entered through a load Door linked to another cell… Each
> interior cell is essentially its own universe.

So a separate interior cell is the **reliable** way to guarantee a different
weather state, because it is a different instance rather than a different value
in the same one. This is the same reason the in-cell Z-shift was rejected for
the bunker: one cell cannot hold two lighting sets.

TODO: confirm empirically that an interior ignores exterior weather rather than
inheriting it.

---

## 3. Seasons

**LIKELY:** seasons are implemented as a mod that swaps the active weather and
lighting setlist on a timer, not as an engine concept. The base core contains
`vivid weathers - fo4.esp`, `trees for the future.esp`, `Seasons.esm` and
`Seasonal Snow.esl` — so a seasons system is already installed.

**Unproven:** whether the engine has any native season concept at all. Nothing
found so far suggests it does. If seasons are purely a mod, then a test
environment's "seasons" is a question about that mod's setlist format, not
about the engine.

TODO: read `Seasons.esm` to see what it actually changes, and whether a
test environment can participate or only observe.

---

## 4. Scripted control — the hard limit

**LIKELY, and this is the most important line in this file:** Papyrus can
*select* weather, and cannot author it. There is no documented Papyrus call to
create a weather class, set cloud density, or define a precipitation type. Those
live in the data files, loaded by the `.esl`.

The practical shape:

```
.wthr / .clmt / .esl   authored offline or in the CK  ->  we can make these
Papyrus                selects which one is active   ->  we can do this
Papyrus                authors a new weather on the fly ->  we cannot
```

So the owner's goal of a storm that *rolls in* has two separable halves:

- **choose the storm weather** — supported, by selecting a `.wthr`
- **animate the front approaching** — **unsupported.** Nothing found describes a
  scriptable front position, and weather is a per-cell state, not a positioned
  volume.

The closest achievable equivalent is a **crossfade** between two weather
classes over a scripted interval, which reads as the sky changing rather than as
a front travelling across the map. Whether that reads as "fog rolling in"
without a visible boundary artifact is **UNRESOLVED and must be observed
in game.** It is a judgement call, not a known-good technique.

TODO: find whether any engine mechanism positions a weather front. If one
exists it is the difference between the intended effect and a crossfade.

---

## 5. Visibility and distance — blocks the intended effect

The intended design is: the player sees weather approaching, then it arrives.
That needs the weather to be visible **outside** the playable area.

**UNRESOLVED:** how far outside the loaded grid the engine spawns
precipitation. The 2D streaming grid is `(uGridsToLoad/2) x 4096` units per
side — with the machine's `uGridsToLoad=5` that is a resident span of 10,240
units = **146.3 m** per side. No source found states whether particles render
beyond that span.

If particles are clipped at the resident boundary, a storm 50 m beyond a 100 m
playable area may never be seen coming. That would make the goal unachievable by
fog and force a different mechanism.

**The measurement that settles it:** place weather over an empty cell, walk away
from it until it disappears, and note the distance. Compare against the resident
span. Cheap, and it decides the design.

---

## 6. Lightning

Not researched. `Enhanced Lights and FX` is installed in the base core, which
may own storm lighting. No FO4-specific lightning research has been done.

---

## 7. What is NOT known

- **Not measured:** how far weather renders beyond the resident cell grid.
- **Not observed:** whether a scripted weather crossfade reads acceptably.
- **Not read:** any WTHR or CLMT subrecord layout.
- **Not tested:** whether interior and exterior weather can differ as assumed.
- **Not determined:** whether a positioned weather front exists at all.

Do not cite this file as evidence that any weather behaviour is achievable.
Cite it as a list of what to go measure.
