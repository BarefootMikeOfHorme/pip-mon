# Test facility — quest-driven, with an object roster

**Verified this session, by compile probe against PapyrusCompiler 2.8.0.4:**

| Construct | On a normal (non-Native) script |
|---|---|
| `Event OnInit()` | accepted |
| `Event OnTimer(float, ObjectReference, Actor, String)` | **accepted** |
| script variables, `auto readonly` properties | accepted |
| `OnStart`, `OnQuestInit`, `OnEnd`, `OnStageChanged` | **rejected** — need Native |
| `OnActivate`, `OnMenuClose`, `Menu` / `Option` types | **rejected** |

So a quest script here is **`OnInit` + `OnTimer`, polling its own stage.** No
`OnStart` means the start is detected by watching the stage, not by being told —
which is slightly less elegant and considerably more robust, because it cannot
miss a transition that happened before the script woke up.

---

## Why a quest beats a static room

A room with NPCs gives you actors that move. A quest gives you **a known
sequence**, and each stage transition is an event the game itself produced.

That matters because it turns "is the VM alive" into a question with an expected
answer. At stage 3 we know exactly which natives should have been called, in
what order, and what each should have returned. A room full of NPCs can only
tell you the VM did *something*.

It also exercises precisely the VM methods Layer A will hook — all measured
against this build:

| Quest action | VM method | Slot |
|---|---|---|
| the tick that runs the tasklet | `UpdateTasklets` | `0x04` |
| objective fires an event | `SendEvent` | `0x2B` |
| the VM checks an event is implemented | `HandleImplementsEvent` | `0x27` |
| script calls a function | `DispatchStaticCall` / `DispatchMethodCall` | `0x2C` / `0x2D` |
| our natives get bound | `BindNativeMethod` | `0x1B` |

Every one of those is a thing a quest does routinely and a decorative room never
does.

---

## The stage ladder

Each stage is driven by the **game**, not by a script deciding what to do next,
so a stage only advances when something genuinely happened.

| Stage | Driven by | Exercises |
|---|---|---|
| 0 | quest starts | all 13 natives called once, verdict recorded |
| 1 | **terminal** activated | object binding, script property reads |
| 2 | **item** collected | inventory, `GetItemCount`, reference resolution |
| 3 | **power armour** equipped at the station | `EnterPowerArmor()`, equip events |
| 4 | **target dummy** destroyed | damage, onhit, actor death |
| 5 | **NPC** talked to | dialogue, custom events |
| 6 | **door** opened and closed | linked objects, cell state |
| 7 | **monitor** switched on / room lights toggled | discrete state, per-room control |
| 8 | player leaves and re-enters the cell | cell load/unload, `streamedCells` |
| 9 | quest completes | final verdict, full report |

Stage 8 is the one people skip and shouldn't: it is the only stage that proves
the runtime survives a cell transition, which is where a real hook is most
likely to break.

---

## The object roster

Everything here is a **stage trigger as well as scenery**. That is the design
rule — nothing is placed purely to look right.

| Object | Where | Stage | Also tests |
|---|---|---|---|
| **Terminal** (carries the script) | Utility room | 1 | activation, our own surface |
| **Terminal** (second) | Kitchen | 1, 6 | a second independent activation point |
| **Item** on a surface | Kitchen | 2 | pickup, inventory count |
| **Power armour station** + frame | Utility | 3 | `EnterPowerArmor()` |
| **Target dummies** (3, resettable) | Ravine range | 4 | damage, death, reset |
| **NPC** with dialogue | Kitchen | 5 | dialogue, custom events |
| **Blast doors** (3, button-controlled) | Kitchen / Security / Ravine | 6 | linked objects, toggling |
| **Monitors** (wall-mounted, switchable) | Every room | 7 | per-room state |
| **Light switches** (per room) | Every room | 7 | discrete state changes |
| **Roster** — 10 NPCs, 2 robots, 2 synths | spread | — | native AI, three dispatch paths |

**Three species on purpose.** Humans, robots and synths resolve and dispatch
differently in Papyrus. A single-species facility would hide a whole class of
failure — the kind that only appears for other people's setups.

---

## Script structure

Non-Native, so it may hold both script variables and properties.

```
Scriptname PipMonTestQuest

int  currentStage = -1     ; last stage we acted on
int  stageChanges = 0
int  timerTicks = 0
int  property verdictVersion = -1 auto readonly
int  property verdictToken   = -1 auto readonly
...                            ; one per native we read back

Event OnInit()
    ; Do NOT probe here beyond the cheapest possible check. A cell load that
    ; immediately calls thirteen natives is indistinguishable from a bug when
    ; you are diagnosing one.
EndEvent

Event OnTimer(float afSeconds, ObjectReference akObjRef, Actor akActor, String asEventType)
    ; Poll. Only act when GetStage() differs from currentStage, so each stage
    ; is handled exactly once no matter how often the timer fires.
EndEvent
```

The `currentStage` guard is the whole trick. Timers fire on their own schedule
and stages can be skipped or repeated, so without it the same stage gets handled
many times and the report is nonsense. With it, each transition is handled once
and in order.

---

## Environmental variables

Carried over from `FACILITY-SPEC.md`, unchanged: enclosed and underground,
high-tech fused with cave, **a light switch in every room**, **ambient sound
zones in every room**, and a **non-settlement surface workshop** — which gives
us a working workbench with none of the `LocTypeSettlement` wiring and so none
of the SimSettlements 2 conflict.

No assets, meshes, scripts or records from the reference mod. Vanilla parts plus
the Prydwen Build Kit.

---

## Build order

1. **Quest record + script**, stages 0–2. Terminal, one item. Enough to prove
   the ladder advances and the natives are reachable.
2. **Stages 3–4.** Power armour station, target dummies.
3. **Stages 5–7.** NPC with dialogue, blast doors, monitors, light switches.
4. **Stage 8.** Nothing to build — it is the cell transition, and it is the one
   that matters most.
5. **Roster.** Fifteen ActorBase property assignments, no placement.

Steps 1–2 are the minimum viable facility. The rest is coverage.
