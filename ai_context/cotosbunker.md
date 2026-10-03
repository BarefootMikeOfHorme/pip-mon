---
title: Cotozic's Bunker Ravine — measured subject notes
purpose: >
  The measured contents of Cotozic's Bunker Ravine, the one dependency-free mod in
  the base core, and the reference model for how a real Creation Engine bunker is
  built. Read before designing any interior for the test environment, and before
  assuming what a settlement mod has to contain.
authority: measured
status: SKELETON — INERT
---

# Cotozic's Bunker Ravine — measured subject notes

> **STATUS: SKELETON. INERT.**
>
> The measurements below were read out of the plugin and are real. **Nothing in
> this file has been built, imported, launched or tested.** No record from this
> mod has been created, edited, copied or promoted. There is no test cell, no
> fixture roster, and no working fast-travel chain.
>
> The file exists so the subject is registered and so the next session does not
> re-derive it. Treat every "TODO" as unbuilt, and do not cite this file as
> evidence that anything runs.

Plugin: `Cotozic's Bunker Ravine.esp`, **613,039 B**, loose file in the game
`Data` folder. Not a Vortex install — Vortex has no record of it. Measured
2026-10-01.

---

## 1. Dependency position — the reason this mod matters

Masters: **`Fallout4.esm` only.** No framework, no extender, no library.

That is the single most useful fact in this file. It means:

- every mechanism below is reachable with the vanilla engine
- nothing here needs F4SE, SKSE, or any native plugin
- it is a valid model for what this project can build without violating the
  standing prohibition on F4SE (see `ai_context/f4se_prohibition.md`)

A settlement mod with a single vanilla master and a full power chain is the
proof that the bunker is buildable on engine primitives alone.

**Verified dependency check:** all 35 entries in `dplugins.txt` are present in
the game `Data` folder. But `XDI.esm` is enabled there and requires F4SE, which
is **not installed** — no `f4se_loader.exe`, no `f4se_steam_loader.dll`. See
§7. This mod has no such problem; the surrounding base core does.

---

## 2. The power chain — measured

The bunker runs on a generator that must be started before anything else works.
Read out of the plugin's scripts and globals:

```
garage breaker  ──►  global generator state  ──►  elevator  ──►  blast doors
```

- Entry is a **breaker in the garage**, not a key or a terminal
- The breaker writes a **global** power state, not a per-object state, so
  several consumers read one flag
- The **elevator** is gated on that state
- The **blast doors** are gated behind the elevator
- A **secure elevator** is also present, separate from the main car

**Design consequence:** this is a dependency chain, not a set of independent
locks. A test environment that wants the same shape needs a global plus
ordered consumers, and it needs to decide what happens when the player pulls the
breaker and then reloads. The global is a save-persistent, so that question is
real.

TODO: extract the exact EditorIDs and global name. Not yet read.

---

## 3. Location and marker records — measured

| Record type | EditorID | Role |
|---|---|---|
| `LOCATION` (INT) | — | interior volume |
| `LOCATION` (EXT) | — | exterior approach |
| `XMarkerHeading` | `COTOSXMarkerHeadingBUNKERRAVINE` | fast-travel anchor |
| `ENCOUNTER ZONE` | — | combat spawn volume |

`XMarkerHeading` is the record that makes a location a fast-travel
destination. The chain is: `FASTTRAVEL` marker → `XMarkerHeading` → player
arrival orientation. Both ends of a fast-travel link must agree or the player
arrives facing the wrong way or in a wall.

TODO: confirm whether a `FASTTRAVEL` marker exists alongside the heading, and
whether the mod ships one or expects the CK to place it.

---

## 4. Containers and settlement wiring — measured

- a **settlement** container, so the location is a buildable settlement
- a **garage terminal**, giving the settlement an interaction point
- a **workshop container** for crafting
- **linked exterior storage** — the storage room is a separate cell reached by
  door, not a room in the same cell

**Design consequence:** "linked exterior storage" is the interesting one. It is
the cheapest possible interior composition — one door, two cells, no shared
lighting problem. It is the right shape to copy for a test environment because
it proves out the door chain without needing a large interior.

TODO: identify the settlement's provider/requirement chain.

---

## 5. Sandbox cells — the extension surface

`COTOSintSandbox*` records are **extension points**, not rooms. The plugin
exposes sandbox cells so downstream mods can attach content without editing the
base. Several distinct `COTOSintSandbox` cells exist.

This is the pattern the test environment should copy: a base module that is
explicitly incomplete, plus named slots that a later module fills. It is the
same reason `dplugins.txt` is a default and `plugins.txt` is amendable.

Also present and recorded, not yet characterised:

- `COTOSplaceatme` — a placement helper
- `COTOSintBorder` — an interior border record
- **Morrisey**, an NPC, with a `HighScore` global/alias chain
- Saucewerks garage strings are **bundled inside this plugin**, so the garage
  has no external dependency

TODO: characterise each `COTOSintSandbox` cell. Which are empty, which are
filled, what each is intended to receive.

---

## 6. What is NOT known

Stated plainly so a later session does not mistake silence for absence.

- **Not measured:** the exterior cell coordinates, the cell count, the worldspace
  offset, and the worldspace's own dimensions.
- **Not measured:** the interior cell count and how the rooms chain by door.
- **Not measured:** navmesh presence, precombine state, or LOD.
- **Not parsed:** script source, per-object placement, or lighting. The plugin
  could not be read by our own tooling — see §8.
- **Not attempted:** opening the CK against this mod.

---

## 7. Known defect in the surrounding base core

Found while measuring this mod, and it is not this mod's fault.

| Entry | Status | Problem |
|---|---|---|
| `XDI.esm` | enabled in `dplugins.txt` | requires F4SE, which is not installed |
| `FCOM.esp` | enabled in `dplugins.txt` | F4SE-era, same class of dependency |
| `Cheat Terminal` | enabled in `dplugins.txt` | F4SE-era, same class of dependency |

All three files exist on disk. None has its runtime. So the base core loads
plugins whose dependency is absent, and our validator does not check for this,
so it would report green.

TODO: classify these into a documented F4SE-dependent group that stays out of
the default active set. Not yet done.

---

## 8. Blocked: our own plugin reader cannot parse this file

`tools/esp_cells.py` **refuses** this plugin, and also refuses `Fallout4.esm`,
`theparadiseproject.esp` and our own `PipMonTestFacility.esp`.

Cause, partially diagnosed: FO4 subrecords use a **6-byte** header (4-byte
signature + 2-byte size), not the 8 bytes the reader assumes. A brute-force
calibration over candidate GRUP/subrecord geometries found **no** geometry that
walks any of the four files cleanly to EOF, so the GRUP layout is still unknown
and the format is **not solved**.

This is a real blocker, not an inconvenience: `PipMonTestFacility.esp` is 66
bytes and unreadable by our own reader, so the "independently validate the
promotion" plan cannot be executed. A validator that cannot read the artifact
it is validating cannot be independent of it.

TODO: derive the GRUP layout from a known-good file, then re-verify. Until
then, treat any record count read from these plugins as unconfirmed.
