---
title: The Paradise Project — measured subject notes
purpose: >
  The Paradise Project as an installed, measured subject: what it is, what it
  contains, and the open question of its playable size. Read before sizing any
  test environment, because the unit-scale error in circulation makes every
  dimension wrong by 9.4% if taken unchecked.
authority: measured
status: SKELETON — INERT
---

# The Paradise Project — measured subject notes

> **STATUS: SKELETON. INERT.**
>
> The identification, size and header facts below were measured on this machine.
> **Nothing has been built, imported, launched or tested.** No Paradise cell has
> been placed, no weather authored, no boundary constructed. The size question in
> §4 is **open**, and the numbers in §3 are corrected but not yet applied to any
> geometry.
>
> The file exists so the subject is registered and so the next session does not
> re-derive the identity or re-propose the wrong unit scale.

Plugin: **`theparadiseproject.esp`**, **1,271,923 B**, Author "uituit",
subtitle "V4". Loose file in the game `Data` folder. **Not a Vortex install** —
Vortex has 71 mods and none of them is this one.

---

## 1. Where the name came from, and why it was ambiguous

"Paradise" is not the mod's filename and not a load-order entry. The filename is
`theparadiseproject.esp`; the in-plugin author is `uituit`; the subtitle is
`V4`. It is the 32nd of 35 entries in `dplugins.txt`, immediately after
`Cotozic's Bunker Ravine.esp`.

It is a **loose file, not a Vortex-managed mod.** Measured:

- `LinkType` empty, no reparse point
- exactly **1** hard link — itself
- Vortex's `fallout4\mods` contains 71 mods, none matching `*paradise*`
- Vortex's `state.v2` LevelDB contains no occurrence of "paradise"

**Consequence:** no Vortex deploy or undeploy will touch this file, and Vortex
cannot report it as enabled or disabled. It is also outside Vortex's conflict
detection entirely, so a future Vortex deploy can silently change what this mod
overrides without Vortex knowing there is a conflict.

---

## 2. Header — measured, and the reason our reader fails

`TES4` header, `dataSize` 386, flags `0x00000000` (uncompressed), HEDR:

- record version `1.0`
- record count **4,214**
- `nextFormId` **988,252**

**HEDR occupies 10 effective payload bytes while declaring 12.** A literal scan
finds `CNAM` at `0x2A`, but a 4-byte-sig + 4-byte-size subrecord header
predicts `0x2C`. The same 2-byte discrepancy is present in `Fallout4.esm` and
in our own generated plugin, so it is a format fact and not a quirk of this
file.

This is the root cause of `tools/esp_cells.py` refusing all four plugins. The
FO4 subrecord header is **6 bytes** (4-byte signature + 2-byte size), not 8.
The GRUP layout is still unresolved — see `ai_context/cotosbunker.md` §8.

---

## 3. Unit scale — CORRECTED, and this is the load-bearing correction

**CONFIRMED: `1 unit = 1/64 yard = 0.5625 in = 1.42875 cm` → `69.99125` units/m.**

Derived from the Bethesda CK wiki `Unit` page, archived 2021-10-06 (page last
modified 2018-04-10), which gives the exact Imperial formula
`FT = Unit * 0.046875`. Derivation, units cancelled:

```
1 unit = 0.5625 in
1 unit = 0.5625 in x 0.0254 m/in            = 0.0142875 m
1 m    = 1 / 0.0142875                      = 69.99125 units
```

**The circulating error is `64 units = 1 metre`, and the reason it is wrong is
now known.** 64 units is exactly **one yard** (`64 x 0.5625 in = 36 in`). The
author converted 64 units to a yard and labelled the result "metre." The
resulting 9.4% is a units slip, not an engine variant:

```
claimed (64 u/m):  4096 / 64      = 64.000 m per cell side
actual:            4096 x 0.0142875 = 58.5216 m per cell side
error:             64.000 / 58.5216 = 1.0936   ->  +9.36%
```

Practical working values:

- `69.99125` units/m — for arithmetic and documentation
- `70` units/m — for mental arithmetic. Error 0.0125%, far below the CK's own
  128-unit vertex spacing (1.83 m). **This is why 70 was used before it was
  derived, and it is now correct rather than lucky.**
- `64` units/m — **rejected.** Do not build on it.

Exterior cell, exact: `4096 units = 64 yd = 192 ft = 58.5216 m` per side. The
CK wiki's "58.5 m" is that number rounded to 4 significant figures; "192 ft" is
exact and should be preferred.

Confidence: high. The constant is established from Skyrim-era CK documentation
plus reverse-engineering consensus, and FO4 shares the 4096-unit cell with
Skyrim — a per-game change would make 4096 a non-round quantity, and the
community tables would have flagged it. **No Bethesda document states the FO4
constant explicitly**, so this is a high-confidence inference from shared
geometry, not a primary FO4 source. One CK measurement closes it: place a sphere
trigger, read its radius, and 64.000 units confirms the yard anchor for this
build. That measurement has **not** been run.

---

## 4. Playable size — OPEN QUESTION, do not build on any number yet

The owner's recollection is **100 m diameter**. That has not been checked against
the mod, and no measurement of the mod's actual extent has been taken.

```
100 m diameter -> 7,000 units -> radius 3,500 units
```

The earlier working proposal in `cre_spatial.md` used a 4096-unit **radius**,
which is 117 m diameter — larger than the owner's figure, and chosen for no
better reason than being a clean power of two. **The owner's 100 m is the better
starting estimate and should replace it.**

The constraint that makes the question non-trivial: a Vertibird is 12–15 m
span, so a landing pad wants ~30 m plus a ~60 m approach corridor — a **90 m
flight envelope inside a 100 m diameter**. That fits, with almost nothing to
spare, and it means the pad and its approach corridor must stay inside one
3×3 previs cluster.

TODO, in order:
1. Measure the mod's actual playable extent, if it is measurable from the plugin.
2. Confirm or replace 100 m as the target diameter.
3. Only then choose a cell footprint.

---

## 5. What is NOT known

- **Not measured:** the mod's cells, worldspace, coordinates, or playable area.
  Our reader cannot parse the file, so nothing has been read past the header.
- **Not measured:** the Vertibird's actual NIF scale, which would independently
  confirm the unit conversion in §3.
- **Not attempted:** opening the CK against this mod.
- **Unresolved:** whether this mod is even the intended "paradise" subject, or
  whether a second candidate exists. The owner's description — 100 m diameter,
  fog rolling in, a wall of no-going — has not been matched to this mod's
  contents. **Confirm the subject is right before building anything.**

---

## 6. Companion files

- `ai_context/cre_spatial.md` — grid, units, transforms, weather, boundary
- `ai_context/cre_weather.md` — weather and season mechanics (SKELETON)
- `ai_context/cre_boundary.md` — boundary mechanisms (SKELETON)
- `ai_context/testenv_layout.md` — how the pieces compose
- `docs/diagrams/paradise_bubbles.svg` — current two-bubble diagram. XML
  validates; **browser rendering has not been verified**, and it uses literal
  arithmetic expressions in SVG numeric attributes, which most renderers reject.
  Treat the diagram as unproven.
