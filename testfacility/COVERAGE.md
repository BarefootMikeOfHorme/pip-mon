# Test facility — component coverage matrix

The facility is a **validation environment**, so coverage is measured against the
game's systems rather than against our feature list. A row exists only where
something in the cell produces a state change we can observe.

Two tests of a row: does the **game** behave (did the power armour actually
climb on, did the dialogue actually advance), and does **PIP-MON** see it. A row
where the game works but we report nothing is a PIP-MON bug, not a quiet pass.

---

## Core loop

| Component | Object / stage | Validates |
|---|---|---|
| Quest state | quest record, 9 stages | `GetStage`, stage-change detection |
| Script lifecycle | `OnInit` + `OnTimer` | timer path, idempotence of stage handling |
| Native dispatch | the 13 `PipMon:` natives | the whole Layer B surface, live |
| Save / load | save mid-ladder, reload | **our state survives persistence** |
| Objectives | one per stage | objective fires → stage advances |

The save/load row is the one most test environments skip and the one that
breaks real users first. If a verdict recorded in a property does not come back
after a reload, everything else is decoration.

## Actors and AI

| Component | Object | Validates |
|---|---|---|
| NPCs | 10, vanilla AI packages | `EvaluatePackage` path, package execution |
| Robots | 2 securutrons | second dispatch path |
| Synths | 2 | **third** path — the one that differs most |
| Faction | NPC vs player hostility | `SetFactionRank`, relationship |
| Dialogue | NPC with a dialogue view | dialogue start/end, custom events |
| Companions | sandbox idle markers | follower-safe placement, no aggro on spawn |
| Death | target dummies, one NPC | onhit, actor death, cleanup of placed actors |
| Merchant | stocked vendor | container linkage, trade path |

## Items, inventory, crafting

| Component | Object | Validates |
|---|---|---|
| Pickup / drop | loose item, container | inventory reads, `GetItemCount` |
| Containers | locked safe, linked multi-cell | opening, linkage, ownership |
| Weapon bench | in Utility room | bench detection, container output |
| Armour bench | in Utility room | as above, second type |
| Chemistry bench | Lab / greenhouse | **third** bench type, different container class |
| Cooking | stove, ingredients | cooking path, item transformation |
| Weight / carry | test item, heavy item | inventory limits, equip constraints |
| Scrap | bench output | reverse crafting, container round-trip |

## Power armour

| Component | Object | Validates |
|---|---|---|
| Station | Utility room | `EnterPowerArmor()` against a real station |
| Frame | T-60 in inventory | frame attach, `GetPowerArmorFrame` |
| HUD | worn PA | HUD layer, our telemetry alongside it |
| Exit / re-enter | station, twice | idempotence, no double-entry |

## Combat and damage

| Component | Object | Validates |
|---|---|---|
| Melee | knife, dummy | damage event, limb |
| Ranged | rifle, dummy | projectile path, hit registration |
| Damage | dummies at varying HP | cumulative damage, death threshold |
| Reset | resettable targets | re-usable stage, no state leakage |
| Health | player damage taken | HP read, aid items |
| VATS | any target | pause interaction, timing under a pause |

## World and cells

| Component | Object / stage | Validates |
|---|---|---|
| Cell load | stage 8, leave and re-enter | **streamedCells**, the transition Layer A must survive |
| Cell unload | same | teardown, no dangling references |
| Fast travel | to and from | travel events, multi-cell sequence |
| Doors | blast doors, keyed | linked objects, toggling, lock state |
| Interior / exterior | bunker + surface garage | multi-cell container linkage |
| Streaming | large cell, long sightline | streaming under load |

## World systems

| Component | Object | Validates |
|---|---|---|
| Lighting | per-room switches, monitors | discrete state, per-room independence |
| Sound | ambient zones per room | audio zones, and our "wired for sound" requirement |
| Weather | exterior, any time | weather state, exterior cell behaviour |
| Time | sleep in the bedroom bed | clock advance, sleep path |
| Weather menus | — | the game's own menu, as a UI smoke test |

## Pip-Boy and UI

| Component | Object | Validates |
|---|---|---|
| Pip-Boy | player inventory | the surface every real user touches first |
| Data | terminals in two rooms | per-room terminal behaviour |
| Workshop | non-settlement surface workshop | workshop **without** settlement wiring |
| Holotape | one in inventory | holotape playback, script on play |
| Map | fast travel from map | map interaction, world map markers |
| Photo mode | — | camera, and that our telemetry survives a mode change |
| Menus | pause, settings, save | UI state, no interference from us |

## The facility's own parts

| Component | Object | Validates |
|---|---|---|
| Light switches | one per room | the state machine the environment is built around |
| Blast-door buttons | 3 buttons, 3 doors | the richest discrete-interaction source here |
| Terminals | 2, in different rooms | two independent activation points |
| Roster spawn | hub marker | 15 actors placed, `PopulateRoster` |
| Roster teardown | `ClearRoster` | **only** what we placed is removed |
| Character kit | `SetupTestCharacter` | idempotence, inventory-by-query not by flag |

---

## What this cannot cover, and why

Stated rather than left to be discovered:

- **Main-quest progression and radiant quests.** Needs a played save with a quest
  log. A facility cannot manufacture main-quest state.
- **Creation Club content.** Needs CC installed; the CK sees it as master records
  if present. Not something the facility controls.
- **Mod interactions at scale.** Needs a heavy load, which is the opposite of a
  controlled environment. This is the argument for a second, stripped install —
  one facility for correctness, one dirty install for interference.
- **Controller input, VR, localisation.** Not Papyrus-observable and not ours.
- **Anything requiring a crash to observe.** Obviously.

## The two-environment argument

One facility cannot answer both "does PIP-MON work" and "does PIP-MON survive a
real load". They need different conditions:

| | **This facility** | **A stripped install** |
|---|---|---|
| mod load | none, or minimal | vanilla + F4SE only |
| question | is it correct | does it survive injection at all |
| blocks | component coverage above | the injection crash, which is still open |

The injection crash has been reproduced five times on a heavily modded install
and never once diagnosed, because the install is too dirty to isolate. A clean
install is the cheapest way to turn that from a mystery into a measurement.
