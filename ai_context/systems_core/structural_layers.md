---
title: The three structural layers, and the cost ceiling each one carries
scope: meta
authority: measured
purpose: >
  Where code runs, what it is allowed to cost, and how the escalation ladder is
  bounded. This is the PLACEMENT axis. It is not the T0-T5 axis. Conflating the
  two is why four Papyrus scripts ended up doing backend work in the one place
  they could least afford to do it.
related:
  - ai_context/systems_core/t5_highway_bus.md   # the DATA-FLOW axis
  - docs/IPC_PROTOCOL.md                       # the wire itself
---

# Placement, and what each place may cost

## Two axes, and why the cross of them is the real design

**The level axis — whose surface is this?** Three levels, and they are the ones
the project actually speaks in:

| level | what a surface here *is* | example |
| --- | --- | --- |
| **engine** | something the game itself provides | the Papyrus VM, record layout, address space, the terminal |
| **our mod** | something PIP-MON provides, for its own purposes | the `PipMon:` script surface, the wire, the dashboard, the CLI |
| **creation env** | something that exists at authoring time | CK, its addons, xEdit, the validation tooling |

**The placement axis — where does it run?** L-IN, L-HOST, L-BE, defined below.

The design is the **cross of the two**, because a level on its own says nothing
about affordability and a placement on its own says nothing about ownership:

| | **L-IN** in-engine | **L-HOST** in-process | **L-BE** out-of-process |
| --- | --- | --- | --- |
| **engine** | Papyrus VM, records, game address space. Zero-alloc, never block a frame. | probing and disassembling engine internals (`vprobe`, Zydis, address resolution). Same budget as its host. | offline analysis of captured engine data, corpus indexing. Free. |
| **our mod** | the `PipMon:` script surface. Declared, thin, must be cheap. | `vprobe.dll`, the runtime, Layer A and B. | `overseer_cli`, the wire, the dashboard, the CLI, the retrieval layer. **Free and verbose.** |
| **creation env** | **does not exist** — you cannot have an authoring-time surface inside the running game | CK-side inspection tools; shares the CK's crash domain. | headless xEdit, `validate_plugin`, `spec_lint`, `artifact_gate`. Free. |

Three things fall straight out of the cross:

- **The empty cell is real, not an oversight.** creation-env × L-IN cannot be
  filled, because authoring-time and running-game are different worlds. Any
  design that reaches for it is reaching for a CK session it will not get.
- **The verbose corner is unambiguous.** our-mod × L-BE is the one place where
  heavy work is free, so heavy work goes there. That is the whole argument for
  the backend existing at all.
- **Misplacement is a readable error.** Something sitting in the wrong cell can
  now be *named* rather than merely called wrong. The four testlab scripts are
  **our-mod-level work sitting in an engine-level placement** — Papyrus, in the
  game, doing measurement. That is the diagnosis, and it is a diagnosis rather
  than a verdict, because the cross tells you where it should go.

## The three layers in detail

### L-IN — in-engine

Runs inside `Fallout4.exe` or `CreationKit.exe`: the Papyrus VM, Layer A and B,
anything holding a game address.

**Shares:** the frame budget, the CPU with the renderer, the GPU, the game's
own allocators. **Cost ceiling: zero-alloc in the hot path, and never block a
frame.** This is not a style preference; it is the difference between a mod that
is playable and one that is not.

A verbosity increase here is paid for in milliseconds of the player's frame. A
log line is a real cost.

### L-HOST — in-process, in the host

A separate module inside one of the two host processes: `vprobe.dll`, the
CK-side inspection tools, anything that links the runtime.

**Shares:** the same process budget as its host, and inherits the host's crash
domain. **Cost ceiling: the same as L-IN, plus a rule that a crash here takes
the editor or the game with it.** This is why the CK's three recorded crash
dumps matter beyond lost work: a crash in L-HOST is indistinguishable from a
crash in Bethesda's code to whoever is sitting in front of it.

### L-BE — backend, out of process

`overseer_cli`, the Rust `vlink-protocol` crate, `ai_watcher.py`, the retrieval
tools, the dashboards and the CLIs.

**Shares: nothing.** Its own process, its own memory, its own CPU and GPU
budget, and it can be stopped and restarted without touching the game.
**Cost ceiling: effectively none — which is exactly why the expensive work
belongs here.**

## The governing rule, applied to placement

The existing tier rule — *a layer may never be made more comfortable than its
cost allows* — is a placement rule as much as a tier rule. Stated for these
three:

> Verbosity, sampling and analysis are **cheap in L-BE and expensive in L-IN**.
> Work migrates outward until only the unavoidable minimum remains in-engine.

That is the whole design, and it is why the escalation ladder below is bounded
by layer rather than by a global switch.

## The escalation ladder

How much the system tells you, and where each level is affordable.

| level | what it does | affordable in | cost to the player |
| --- | --- | --- | --- |
| 0 | one-line verdict, counters only | anywhere | none |
| 1 | per-tier summary | anywhere | none |
| 2 | per-fact with provenance | L-BE freely, L-IN sampled | low if sampled |
| 3 | raw bytes / full trace | **L-BE only** | unacceptable in-engine |

A single global verbosity switch is the wrong shape, because the same setting
means "free" in one process and "30 fps drop" in another. Verbosity is
therefore **per-layer**, and the in-engine level is capped independently of
anything the backend asks for.

The in-engine budget is a **ring buffer, not a stream.** The engine writes
compact fixed-size records into a preallocated ring; the backend drains it over
the wire at whatever rate it likes, and when the backend is slow or stopped the
oldest records are simply overwritten. That is what makes the backend's freedom
to be verbose *safe*: it cannot make the engine do more work by asking for more
detail, because the writing was already paid for and already bounded.

## Why the four testlab scripts are misplaced

`PipMon_LeakTest.psc`, `PipMon_LoopTest.psc`, `PipMon_TerminalTest.psc` and
`overseer_event_bridge/Scripts/Source/OverseerBridge.psc` are Papyrus, so they
are L-IN by definition. What they contain is L-BE work:

- a **leak test** measures allocations from inside the VM it is measuring
- a **loop / starvation test** counts iterations inside the thread it is
  starving
- an **event bridge** is a routing concern, which is wire-shaped by nature

Doing backend work in L-IN costs twice: the measurement perturbs what it
measures, and the instrumentation spends the frame budget that the thing under
test needs in order to be measured honestly.

They are also written against **SKSE's vocabulary** — `CustomEvent`,
`SendEvent`, `MenuButton`, `OnMenuClick` — none of which exist in FO4 Papyrus,
so they cannot compile here at all. That is a second, independent symptom of
the same misplacement: the scripts were written as if the in-engine layer were
the natural home for an event system. It is not. Our event system is the wire,
and the wire is L-BE.

## The realignment

Each script becomes what it should have been: a **thin L-IN shim** whose only
job is to forward to L-BE and cache the last value. All measurement, counting
and analysis moves to the backend, where it is free.

| file | today | becomes |
| --- | --- | --- |
| `OverseerBridge.psc` | 5 `CustomEvent`s, SKSE-shaped | a shim that registers with the wire and exposes a cached snapshot to Papyrus |
| `PipMon_LeakTest.psc` | leak counting + `MenuButton` | measurement in L-BE; the shim only reports the last sampled figure |
| `PipMon_LoopTest.psc` | loop counters + `SendEvent` | counters in L-BE, sampled over the wire |
| `PipMon_TerminalTest.psc` | menu test bench | **retire.** Terminal UI needs a `Native` script, and a `Native` script cannot hold data, so it is a dead end for a test bench that must report results |

Naming follows ours, not SKSE's: the surface is `PipMon:` and the wire is
V-Link, so a shim is a *V-Link client*, not an *event bridge*. SKSE's
`CustomEvent` is not a capability we lack; it is a capability whose work belongs
in a different layer than the one SKSE put it in.

## What this does not change

Layer A is still the blocker. A shim that forwards over the wire still needs the
wire, and the wire still needs a VM hook to originate from. Realigning the
scripts makes their current state honest and makes the eventual work smaller; it
does not make the scripts runnable, and it is not a substitute for the hook.
