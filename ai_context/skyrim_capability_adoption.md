---
title: Skyrim capability adoption triage
purpose: >
  Decides what PIP-MON should implement from the Skyrim/SE feature set that
  Fallout 4's Papyrus does not have. Read alongside
  ai_context/papyrus_syntax_rules.md, which lists these as FO4 negatives. This
  file is where a negative becomes a target, and where it stays rejected.
project_rule: >
  A Skyrim idea may be adopted for FO4 if there is a valid use or idea path. It
  is not adopted on the strength of being a good idea. An entry earns ADOPT only
  by naming the mechanism and the proof. Anything that cannot name both is
  INVESTIGATE or REJECT, and no amount of enthusiasm promotes it.
authority: unproven
trust: verdicts are engineering judgement as of 2026-09-30, not measured fact. Every ADOPT is unproven.
---

# Skyrim capabilities: what we take, and what we refuse

## The rule

SKSE is to Skyrim what PIP-MON is to Fallout 4. A capability gated behind SKSE
is therefore not off-limits because it is Skyrim-specific; it is off-limits
because **we have not built it yet**. Those are different statements and this
project has been conflating them.

The filter is deliberately hostile to enthusiasm. An idea is admitted only if
all three of these are answerable in one sentence each:

1. **The use.** What is broken or impossible in FO4 today, in terms a player or
   mod author would recognise?
2. **The mechanism.** Which native, hooking what, at which layer? Not "we would
   add a function" but where the call goes.
3. **The proof.** What single observable result shows it worked, and what result
   shows it did not?

An idea that answers 1 but not 2 and 3 is a dream. It goes in INVESTIGATE with a
named experiment, or it does not go in at all.

## Standing evidence this project already has

These are real and are load-bearing for several verdicts below.

- The `PipMon.psc` surface already declares `RegisterForEvents(Int aiMask)` and
  `UnregisterFromEvents(Int aiToken)`, staged as **S2 poll, then S3 push**. The
  event system's front half is designed, not imagined.
- **S1 canaries** `GetStringTest()` and `GetStringArrayTest()` exist to answer
  one question before anything else is built on it: can a non-int value cross
  into Papyrus at all? If S1 passes, several REJECTs below become ADOPTs.
- 18 of 18 probes resolve through Tier 1, so address resolution works. What
  does not exist is **Layer A**, the BSScript vtable slot, so no call has ever
  been intercepted in either direction.
- `RegisterForEvents` returning a token, and `Unsubscribe()` in the facility
  script, show the intended shape: scripts register, native keeps state, the
  wire carries the payload.

## Triage

| Skyrim capability | FO4 status | Verdict | One-line reason |
| --- | --- | --- | --- |
| `CustomEvent` / `SendEvent` | absent | **ADOPT** | We already own the push half by declaration; this is its missing half. |
| Runtime spawn from a FormID | absent | **ADOPT** | We already resolve FormIDs through load order; the game's spawn call is the only unknown. |
| `Debug.Notification` / `MessageBox` | no `Debug` script exists | **ADOPT, differently** | The wire and dashboard are a better channel than a toast, and we own the wire. |
| Array length / iteration | no intrinsic | **ADOPT via S1** | Gated on proving arrays cross the native boundary. Not gated on anything we control. |
| Missing event types (`OnAddToMenu`, `OnCombatEnd`, ...) | signature-gated | **ADOPT via split** | A Native event shell plus a state script, communicating over the wire. |
| `Menu` / `Option` property types | not types in FO4 | **INVESTIGATE** | The FO4 Pip-Boy menu system exists; whether it is reachable from native is untested. |
| `Start()` / `Stop()` | absent | **REJECT** | Cosmetic. `StartTimer`/`CancelTimer` already do the job. |
| More properties on vanilla types | requires extending `Form`/`Actor` | **REJECT** | Our whole coexistence argument is registering only into our own class. This would forfeit it. |

## ADOPT, in detail

### 1. Custom event injection

**Use.** An addon needs to tell an unrelated script something happened, with no
compile-time link between them. Today the only channel is polling, because FO4
Papyrus has no event injection. Every add-on therefore either polls or
monkey-patches someone else's script.

**Mechanism.** The push half of the system already declared as
`RegisterForEvents`. Native keeps a subscription table keyed by the token
`RegisterForEvents` returns; the caller enqueues a payload; a dispatch pass
delivers it. The delivery mechanism depends on Layer A, and that is the honest
hard part: it is either a vtable call into a script's event, or a native-side
queue drained by a script-driven tick. The second needs no Layer A at all and
should be built first precisely because it is reachable now.

**Proof.** Register from two scripts, enqueue from native, and observe the
arrival count on the wire with no polling in either script. Failure looks like
a zero count with a non-zero registration, which distinguishes "not delivered"
from "not registered" and is worth having as a diagnostic from day one.

### 2. Runtime spawn from a FormID

**Use.** Every actor in the facility is a CK-assigned property, because
`CreateObjectAtForm` does not exist. That is a real authoring tax: 15 roster
slots, each one a manual CK assignment, and any add-on shipping actors has the
same problem. Worse, a form ID hardcoded in a script breaks silently when a mod
shifts it.

**Mechanism.** We already do FormID resolution through load order, and we
already read FormIDs out of records via `FixedFormID`. The missing step is
invoking the game's own spawn path from native. A proposed signature, to be
confirmed against the address database rather than assumed:

```papyrus
; PROPOSED, not implemented, not proven
ObjectReference Function SpawnFromFormID(Int aiFormID) Global Native
```

**Proof.** Spawn a vanilla ActorBase by ID into a known cell, and confirm it
appears with its package intact and its FormID matching what was asked for.
Negative case matters more: spawn a FormID from a mod that is not loaded, and
confirm it returns `none` rather than crashing or spawning a wrong object. A
silent wrong-object spawn is the failure that would poison everything built on
top of it.

### 3. Diagnostics through the wire, not a toast

**Use.** `Debug.Notification` does not exist in FO4, so a mod author debugging
at runtime has no sanctioned channel. Mods resort to `DisplayRaceMenu` hacks or
on-screen text hacks.

**Mechanism.** Proposed, consistent with the existing surface:

```papyrus
; PROPOSED, not implemented, not proven
Function Log(String asMessage) Global Native
Function LogError(String asMessage) Global Native
```

Native appends to the wire; T4, the dashboard and CLI, renders it. This is
strictly better than a toast for our purposes: it is queryable after the fact,
it survives a crash, and it does not require the game to be in a state where a
toast is visible.

**Proof.** Call `Log` from a script, read the entry back off the wire with no
game UI involved. If it cannot be read without the game running, it is a
toast with extra steps and should be rejected.

### 4. Array marshalling, gated on S1

**Use.** FO4 has no array length intrinsic, so no script can iterate an
editor-filled array. Rosters become named properties, which is workable at 15
entries and unworkable at 150.

**Mechanism.** Nothing new. S1 canaries `GetStringTest` and
`GetStringArrayTest` already exist to answer whether non-int values cross the
boundary. If arrays cross, a proposed `Int Function GetArrayLength(...)` is
available almost for free. **This is explicitly gated on S1, and the gate is
honoured: nothing here is built before S1 reports.**

**Proof.** Return a 3-element array from native and have script count it. If S1
fails, this whole section is REJECT and the roster stays as named properties.

### 5. Event types, via a split script

**Use.** `OnAddToMenu`, `OnMenuClick` and similar require the script to be
flagged `Native`, and a `Native` script may not contain data. So one script
cannot both receive a terminal event and hold state. This is a hard toolchain
constraint, not a preference, and it is why the facility has no in-game menu.

**Mechanism.** Split by concern: a `Native` event shell with no properties that
forwards each event onto the wire, and an ordinary script holding state that
reads it. Once Layer A supports native-to-Papyrus calls, the shell can invoke a
named function on the state script directly instead.

**Proof.** An event shell receives a terminal event while a separate script
retains a counter across the same interaction. If the counter resets, the split
is not working and the mechanism is wrong, not merely incomplete.

## INVESTIGATE

### The `Menu` / `Option` question

**Use.** The Fallout 4 Pip-Boy menu system exists and is more capable than
anything Papyrus can reach. A native-driven menu, with the script supplying
choices as data rather than as authored UI, would be a genuine capability.

**Why it is not ADOPT.** The mechanism is unstated in anything trustworthy. FO4
menu internals are not a documented API, and this project's own rule is that
unverified structure is a hypothesis. Claiming a menu path without having read
the structure would be exactly the dreaming the rule forbids.

**The named experiment.** Read the structure first: find the Pip-Boy menu
records, determine whether menu state is reachable from a native at the
addresses already in the database, and only then decide. Until that reading
exists, this is a question, not a design.

## REJECT, with reasons

- **`Start()` / `Stop()`.** `StartTimer(float, int)` and `CancelTimer(int)`
  already exist in FO4 and are verified working. This is a naming preference,
  not a capability, and adding it would be surface area with no user.
- **Extending vanilla types** (`Form`, `Actor`, `System:`). PIP-MON registers
  only into its own class, and that is the entire reason it coexists with every
  other extender instead of competing. Extending a vanilla type would forfeit
  the architectural position to gain a convenience. If it is ever worth it, it
  is worth it for a reason that has to be written down first.

## What stays forbidden regardless of enthusiasm

- A capability with no named hook point. "We would add a function" is not a
  mechanism.
- A capability whose only proof is "it should feel faster".
- Anything that requires extending a vanilla type without a written reason for
  surrendering coexistence.
- Treating a Skyrim feature's presence as evidence that it is implementable
  here. It is evidence that Bethesda's engine could do it, which is a different
  and weaker claim.
