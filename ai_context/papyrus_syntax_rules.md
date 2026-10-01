---
title: Papyrus syntax rules for Fallout 4
purpose: Authoritative FO4-specific Papyrus reference for this project. Read before writing or editing any .psc file.
derived_from:
  - vprobe/papyrus/PipMon.psc
  - vprobe/papyrus/PipMonTestFacility.psc
  - pip_mon_testlab/Scripts/Source/PipMon_TerminalTest.psc
  - pip_mon_testlab/Scripts/Source/PipMon_LoopTest.psc
  - pip_mon_testlab/Scripts/Source/PipMon_LeakTest.psc
  - overseer_event_bridge/Scripts/Source/OverseerBridge.psc
  - vprobe/papyrus/papyrus_flags.flg
verified_against: FO4 Papyrus compiler 2.8.0.4, on this machine, 2026-09-30
authority: compile-verified
trust: every rule below was compile-verified here. The NEGATIVES are the valuable half.
---

# Papyrus in Fallout 4: what is real and what is a Skyrim habit

Read the negatives first. Every item marked "does not exist" below is a genuine
feature of Skyrim Papyrus, which is exactly why it is tempting, and every one of
them was found by compiling against the real FO4 compiler rather than by
recalling documentation.

## 1. Constructs that DO NOT EXIST in Fallout 4

> **These are not all permanent negatives.** "Unavailable in FO4 Papyrus" means
> unavailable *today*, not out of scope. SKSE is to Skyrim what PIP-MON is to
> Fallout 4, so anything gated behind SKSE is a candidate we may build rather
> than a prohibition. See `ai_context/skyrim_capability_adoption.md` for the
> triage, which admits `CustomEvent`/`SendEvent`, FormID runtime spawn, wire
> logging and array marshalling, and rejects `Start()`/`Stop()` and vanilla-type
> extension. Read that file before concluding a limitation is permanent.
>
> What matters for *writing code today* is unchanged: none of these compile,
> and the compiler names each one.

| Construct | Reality | Error text seen |
| --- | --- | --- |
| `CustomEvent`, `SendEvent` | SKSE-only. Not in FO4, and F4SE does not supply it. Zero occurrences across the 41 CK base scripts. | not declared |
| `Debug.Notification`, `Debug.MessageBox` | There is no `Debug` script in FO4 at all. | unknown script |
| `Menu`, `Option` property types | Not Papyrus types in FO4. | "unknown type" |
| `Player` bare identifier | Skyrim-ism. Use `Game.GetPlayer()`, which returns an Actor. | "variable Player is undefined" |
| `arr.GetLength()` | No array length intrinsic. | "not a function or does not exist" |
| `arr.GetSize()`, `arr.Count()`, `arr.Size()` | Do not even parse. | parse error |
| `CreateObjectAtForm` | No runtime spawn from a form ID. A reference must exist before it can be placed. | "not a function or does not exist" |
| `Start()` / `Stop()` | Skyrim timer API. FO4 uses `StartTimer`/`CancelTimer`. | "Start is not a function or does not exist" |
| `Event OnTimer(float)` | Wrong signature. FO4's takes the timer **ID**. | parameter types do not match ScriptObject |
| `GetOwningObjectOfThread` | Skyrim/SKSE. FO4 has no way for a script to ask a thread for its owning object. | "GetOwningObjectOfThread is not a function or does not exist" |
| `self.Cancel()` / `ObjectReference.Cancel` | No `Cancel` method on ScriptObject. It looks like the Skyrim idiom for stopping a self-run script; nothing in this build declares it. | "Cancel is not a function or does not exist" |

### 1a. Two traps that produce *misleading* error text

Both of the following were found on 2026-10-01 by compiling, not by reading. Each
one made the compiler blame the wrong line, so the reported position was not the
fault.

**A `;` after a function or event signature.** `Function Ping() ;` is not valid.
The parser derails from that point, and the errors it then reports are
attributed to *later*, innocent lines — in our case to a `while` block two
hundred lines further down, as `required (...)+ loop did not match anything at
input '('` and `,`. Twenty such signatures across four files produced a cascade
of five unrelated-looking errors. A stray `;` on a declaration is worth reading
the whole error list for.

**A doubled `endif`.** `endif    endif` on one line is not one terminator too
many in an if/elseif/else chain — it is two, and the second closes the *enclosing*
`if`. So `if abOpening` wrapping an action chain legitimately needs two, on
separate lines, at different indents. Compiled as one line they read as a single
malformed terminator and the error lands on the chain's last branch instead.

Practical consequence: when this compiler reports a **loop** error, check the
loop before believing it. In both cases above the loop was correct and the
`endwhile` was fine. Verify the line the compiler named, then keep reading
backwards for the first genuine fault.


The array-length gap is a structural constraint, not a missing convenience:
without a length there is no way to iterate an editor-filled array from script,
so `ObjectReference[] property Roster` would be writable in the CK and
unreadable at runtime. Use individual named properties instead. The benefit is
real: fifteen named slots are visible at a glance in the CK property list, so
"which one is the synth" is answered by looking rather than by counting indices.

## 2. The timer API, verbatim from the CK base script

Read from the base script the CK installs, which is the authority:

```papyrus
Function StartTimer(float afInterval, int aiTimerID = 0) native
Function CancelTimer(int aiTimerID = 0) native
Event OnTimer(int aiTimerID)
```

The first argument is an interval, and `aiTimerID` is an identifier, **not** an
elapsed time. An event whose signature does not match `ScriptObject`'s
declaration is rejected outright:

```
the parameter types of function ontimer ... do not match the original
script scriptobject
```

Working one-shot pattern, as used in `PipMonTestFacility.psc`:

```papyrus
Event OnInit()
    StartTimer(2.0)
EndEvent

Event OnTimer(int aiTimerID)
    If probeFired
        Return
    EndIf
    probeFired = true
    CancelTimer()
    RunNativeProbe()
EndEvent
```

## 3. Properties: the three rules that cost compile cycles

**A property with an initial value must be `Auto` or `AutoReadOnly`.**

```papyrus
int property s0Version = -1 auto readonly     ; legal
int property s0Version = -1                    ; rejected
```

> Only Auto and AutoReadOnly properties can have initial values

**A bare `ObjectReference property x` is not valid at all**, and an `Auto`
property with no initial value must be written `= none Auto`.

```papyrus
ObjectReference property TerminalRef Auto              ; legal, no initial value
ObjectReference property placedN01 = none Auto          ; legal, initial value none
ObjectReference property placedN01                     ; rejected
```

**`AutoReadOnly` is read-only to the script.** Choose it deliberately: verdict
fields the native side writes should be `AutoReadOnly`, while fields the script
itself records (so teardown can find them) must be `Auto`. Using `AutoReadOnly`
for something the script needs to write is backwards, and the failure is silent
because the field just never changes.

## 4. Native functions and the `Native` script flag

A Papyrus function may only be declared `Native` if the containing script is
also flagged `Native`, or the compiler rejects every one of them at once:

```
cannot be defined as native because the script is not flagged as native
```

```papyrus
ScriptName PipMon Native

Int Function GetVersion() Global Native
String Function GetStringTest() Global Native
```

`Native` = we supply the implementation. `Global` = callable as
`PipMon:GetVersion()` from anywhere with no script instance. The `ScriptName`
value is a registration key matched by the VM, not a label: a typo does not
warn, it produces a script that calls into nothing.

**The mutual exclusion that shapes this project:** a script flagged `Native` may
not contain data. No properties, no script variables, not even a plain
`int property x`. Events like `OnAddToMenu` / `OnMenuClick` / `OnMenuClose`
require `Native`, so a script handling terminal events cannot also hold state.
The two requirements are mutually exclusive in this toolchain. That is why the
facility has no in-game menu and `OnInit` is the only event it declares.

## 5. Cross-script calls use a DOT

```papyrus
iVersion = PipMon.GetVersion()      ; correct
iVersion = PipMon_GetVersion()      ; WRONG: not a function or does not exist
```

`PipMon_GetVersion` is the mangled name the VM uses internally. The underscore
form is what the function is called everywhere else in this repository, which
makes the dot form the single most likely mistake when extending the surface.

**Compile order matters.** The compiler resolves `PipMon.X()` against
`PipMon.pex`, so `PipMon.psc` must be compiled first or every call fails with
"not a function or does not exist" -- which reads like a missing surface rather
than a missing artefact. See `vprobe/papyrus/build_papyrus.bat`.

## 6. Verified natives used by this project

**No semicolon after a signature.** `Function Name(args)` and
`Event OnSomething(type arg)` take no trailing `;`. The same is true of the
`end...` keywords: one terminator per line, never two. A stray `;` on a
declaration does not error where it is — the parser loses its place and reports
the damage somewhere else entirely, usually as a loop or a type error hundreds
of lines downstream. This is the single most expensive typo in this codebase and it
has now been made twenty times across four files. If the compiler blames a line
that looks obviously correct, look for a `;` or a doubled terminator *earlier* in
the same file.

**A return type goes BEFORE the whole declaration, and it is required.**
Verified on 2026-10-01 by compiling five spellings of the same two-line function
against compiler 2.8.0.4. Exactly one compiles:

```papyrus
Int Function ConsumeTerminationRequests()      ; correct
    int n = Something
    return n
EndFunction
```

| Spelling | Compiler says |
| --- | --- |
| `Int Function Name()` | compiles, and a caller may consume the result |
| `Function Name() int` | no viable alternative at input `'int'` |
| `Function Int Name()` | extraneous input `'Int'` expecting ID |
| `Function Name() Integer` | Unknown user flag `integer` — `Integer` is not a type here |
| `Function Name()` (no type) | cannot return a int from Name, the function does not return a value |

The type precedes the declaration; it does not follow the name and it does not
follow the parameter list. The last row is the trap: omitting the type looks like
"Papyrus has no return types" and it does not — an untyped function simply
cannot return a value, and the error names the `return` rather than the missing
type. Note that `Int` is correct and `Integer` is not.


`Game.GetPlayer()` returns an Actor.
`ObjectReference.PlaceAtMe(akOrigin, aiCount, aiOverrideBehavior)` returns a
**new** Actor, so cast it: `akBase.PlaceAtMe(oSpawn, 0, 0) as Actor`.
`Actor.Delete()` removes the placed actor.
`Actor.EvaluatePackage(true)` -- the reset flag matters. Without it an actor
that already ran its package to completion will not pick it up again, so a
re-run leaves the previous cast standing still.
`Actor.EnableAI(true)`, `Actor.GetItemCount(oItem)`, `Actor.AddItem(oItem, n)`,
`Actor.RemoveItem(oItem)`, `Actor.UnequipAll()`,
`Actor.SwitchToPowerArmor(oStation)`.

## 7. No hardcoded form IDs

This install is heavily modded and form IDs move. A hardcoded ID breaks the
first time a mod shifts that record, and it breaks **silently** -- the spawn
simply does not appear, which reads as a product failure rather than a load
order change. Every reference is a property assigned in the Creation Kit.

Properties also keep the script valid if the facility is rebuilt on a different
cell or extracted for distribution.

## 8. Naming conventions

Namespace and functions are PascalCase. Parameters use Bethesda's Hungarian
prefixes: `ai` int, `af` float, `ab` bool, `as` string, `aa` array. This
project's own ESPs are lowercase `pip-mon.*.esp`, which is unrelated to Papyrus
source naming.

## 9. Idempotence is checked against the world, not a flag

A property saying "done" is a lie after a save is loaded, reverted, or
console-fiddled with. Ask the inventory instead:

```papyrus
If pPlayer.GetItemCount(KitWeapon) > 0
    iDid = iDid + 32        ; already equipped
ElseIf KitWeapon != none
    pPlayer.AddItem(KitWeapon, 1)
    pPlayer.EquipItem(KitWeapon)
EndIf
```

Return a **bitfield**, not a bool. "the setup ran" and "every piece of the kit
landed" are different questions, and one bool throws the second away. See
`CheckFixtures()` and `SetupTestCharacter()` in `PipMonTestFacility.psc`.

## 10. The tiered-bus surface (Layer B)

`PipMon.psc` is the script-visible half of the surface; `vprobe/src/PapyrusApi.cpp`
is the other half, and **the two must agree**. A self-test asserts it in both
directions: every function declared in the script has a matching row in the
native table, and every row in the table is declared in the script. A surface
existing only in C++ is invisible to a mod author; one existing only in Papyrus
calls into nothing.

Probes report **which tier resolved them**, so triage can explain itself:

| Tier | Mechanism |
| --- | --- |
| Tier 1 | AddressLib lookup by address database |
| Tier 2 | vtable slot derivation |
| Tier 3 | AOB / signature scanning |

```papyrus
Int  Function GetResolvedProbeCount() Global Native
String[] Function GetResolvedProbes()   Global Native
Bool Function IsHookLive(Int aiProbeId) Global Native
```

Dispatch and resolution are different systems. A live native with a dead
resolver is a real, useful, **partial** result, and folding it into one
pass/fail throws away the only information the experiment produces. Before
Layer A lands, `GetResolvedProbeCount()` is expected to be 0 and that is not a
failure.

## 11. Project conventions

- Save after every complete or partially complete task. A restore point costs
  nothing; a lost session costs the session.
- `SKIP` is never `PASS`. "We did not look" and "we looked and it is fine" are
  different facts.
- When a claim is uncertain, read the raw file or the compiler output. Do not
  substitute recollection.
- Prefer native behaviour over scripted behaviour where the question is "is the
  VM actually executing". `EvaluatePackage(true)` proves more than a
  hand-scripted patrol would.
