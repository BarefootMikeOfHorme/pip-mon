# Test facility — environmental specification

**Source of intent:** the *design* of Cotozic's Bunker Ravine (Nexus 27466),
read from its own description. **No assets, meshes, scripts or records from that
mod are used, copied or required.** Its author restricts modification and
redistribution, and none of it is needed here — what follows is a specification
we build against, using vanilla parts plus the Prydwen Build Kit.

---

## The vibe, in the author's own terms

> Take a little high tech and cave, smash em together.

Enclosed, underground, calm. Cracked apart by earthquakes, with water flooding
and draining above it so the whole place feels submerged. Modern and clean, but
lived-in. Every room individually lit and switchable. Reachable but not open.

Three properties make it work as a test stage rather than just as a room, and
all three are in the original:

- **Room-by-room light control.** Every room has its own switch. That is a
  state machine per room, and it is the cheapest possible source of observable
  state change.
- **Sound and light work throughout.** Ambient zones per room. This is also the
  "wired for sound" requirement — sound is a *variable* in this environment, not
  a decoration.
- **Non-settlement surface workshop.** The original explicitly notes its surface
  workshop "doesn't function as a settlement location". That matters: it gives
  us a working workshop with the vanilla `LocTypeSettlement` wiring — and the
  SimSettlements 2 conflict — left out entirely.

---

## Rooms, and what each one tests

| Room | What it is | What it exercises |
|---|---|---|
| **Security entry** | Sentry bot, keycard-locked blast door | `IFunction`, object binding, keyword checks |
| **Utility room** | Fusion reactor, **armour / weapon / power-armour workstations** | `EnterPowerArmor()`, the workstation trio |
| **Kitchen** | Blast-door controller, **3 buttons**, stove, incinerator | Discrete interaction events — the richest source in the build |
| **Master bedroom** | **Terminal** with logs, storage, safe, bed | Our terminal; script property assignment |
| **Bathroom** | Barber/face-surgery chair, tub, working water | Cosmetic; cheap to include, no test value |
| **Lab / greenhouse** | Chemistry lab, **growing mutfruit / carrot / tato / gourd** | Long-running growth, ticking state over minutes |
| **Subfloor** | Workbench, build area, 100-power source | Sustained build load; stress for the tick hook |
| **Ravine / range** | **Resettable target dummies**, weapon + chemistry benches | Damage and reset events |
| **Surface garage** | Workbench linked to interior, storage you can reach from outside | Multi-cell linking; objects reachable without entering |

The **blast-door buttons in the kitchen** are the detail worth stealing. Three
buttons, three separate blast doors, each a discrete press with a visible
consequence. That is the ideal shape for a test interaction: unambiguous,
repeatable, and observable from more than one system.

---

## The roster, placed

Fifteen actors, each placed at runtime and handed to the game's own AI via
`EvaluatePackage(true)` + `EnableAI(true)`, so they behave natively with vanilla
packages.

| Slot | Where | Why there |
|---|---|---|
| `Npc01`–`Npc03` | Security / Kitchen | Staffed rooms; near the buttons |
| `Npc04`–`Npc06` | Utility / Lab | Beside the workstations |
| `Npc07`–`Npc08` | Bedroom / Subfloor | Spread, so they aren't one clump |
| `Npc09`–`Npc10` | Ravine | Near the range |
| `Robot01`–`Robot02` | Entry / Ravine | Sentries; robots and humans take different event paths |
| `Synth01`–`Synth02` | Lab / Utility | Synths are a third path again — worth having all three |
| `MerchantRef` | Kitchen | Stocked vendor; a merchant with no stock is just an NPC |

Three species on purpose. Humans, robots and synths resolve and dispatch
differently in Papyrus, so a facility with only one species would hide a whole
class of failure.

---

## Terminals: the interaction points

The original puts a terminal in the master bedroom. For us terminals are the
primary interaction surface, so: **one in the Utility Room** (carries the
facility script) and **one in the Kitchen** (carries the blast-door controls).
Two, in different rooms, on different systems.

And the honest constraint, unchanged: FO4's Papyrus has no `Menu`/`Option`
types, and `OnMenuClose` requires a Native script that may not hold properties —
verified by compile probe. So terminals cannot carry dynamic script menus.
What they *can* do is drive the CK-authored static menus, and our facility
reports through the telemetry channel instead.

---

## What is deliberately not copied

- No `.esp`, no `.ba2`, no meshes, no textures, no scripts from 27466.
- No prebuilt cells. We author our own; the original's cells are its own work.
- Not the acquisition quest. We want the environment reachable immediately —
  a test stage that needs a fetch quest is a test stage that wastes a session.

The Prydwen Build Kit (Nexus 70726) supplies Prydwen/Brotherhood catwalks and
platforms with snap points, which covers the visual vocabulary without lifting
anything from the bunker mod.

---

## Build order

The rooms are independent, so this does not have to be one sitting:

1. **Shell** — one cell, light switches per room, ambient sound zones.
2. **Kitchen** — the three buttons and blast doors. Highest test value per
   object placed, and the first thing worth running.
3. **Utility** — the workstation trio and the power-armour station, plus the
   terminal that carries our script.
4. **Roster** — 15 ActorBase references. No placement needed; the script does it.
5. **Everything else** — as time allows.

Steps 1–3 are the facility. Step 4 is fifteen CK property assignments and
nothing else. Step 5 is optional.
