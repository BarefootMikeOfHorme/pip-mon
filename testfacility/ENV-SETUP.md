# PIP-MON test environment — build guide

**Status:** our own bench, internal use for now. The surface is written to stay
general so this can be adapted into a shipped default area later.

**Last verified:** 2026-09-29 against this machine.

---

## 0. What is already installed

Checked, not assumed:

| | |
|---|---|
| Game | `Fallout4.exe` **1.11.240.0** (Anniversary Edition) |
| Creation Kit | `CreationKit.exe` **1.11.240.0** — exact build match |
| F4SE | `f4se_loader.exe` **0.7.9** |
| HUDFramework | installed (Transfer Settlements requires it) |
| **CKPE** | **NOT installed** — see section 1 |
| Transfer Settlements | **NOT installed** — see section 1 |
| `Data\Mods\` | empty; no plugin has ever been built here |
| Second Steam library | `D:\SteamLibrary` — 5.5 TB free |

### 0.1 The main install is NOT the test environment

The existing FO4 install carries **200+ mods**: SimSettlements 2, snap'n build,
WorkshopFramework, three separate power-armour overhauls, Seasons, and a wall of
texture packs. **Do not test PIP-MON in it.**

This is not tidiness. It is whether the S0 result means anything.

- If the hook **succeeds** there, there is no way to tell a robust
  implementation from one that happened to survive that particular load order.
- If it **fails**, there is no way to tell a PIP-MON defect from SimSettlements
  2 fighting it for the workshop hooks.

A minimal environment turns "it works" into a claim that can be checked, and
"it broke" into a diagnosis rather than a shrug.

**Recommended:** a separate FO4 install on `D:\SteamLibrary`, vanilla plus the
two mods below and nothing else. It costs disk, resets in seconds, and cannot
disturb the main save.

### 0.2 The intended mod set — deliberately three things

| Mod | Why it is here |
|---|---|
| **Scrap Everything** | Clearing a space to bare bones is step 2 of the build, and it is the slowest step by hand. This is the reason it earns its place. |
| **Whispers** (power armour) | The facility needs a power armour frame and a station. PAO is also present on the main install; either works, but only one. |
| *one more, TBD* | Left open deliberately rather than filled in. |

Everything else stays out. In particular the settlement frameworks —
SimSettlements 2, snap'n build, WorkshopFramework — are **excluded on purpose**,
not by oversight; see §6.

### 0.3 Considered and not used

Nexus 46399 ("Everyday People") was raised as a character-creation template. It
is a pack of 18 LooksMenu face presets from 2020 with seven hard dependencies,
three of which replace face and body rendering globally. It is recorded here as
an **idea and a resource reference, not a dependency** — nothing in this guide
requires it, and nothing should be installed for it.

The underlying thought was sound, though: in FO4 an NPC and a character preset
are both `ActorBase` records, so "one source for both" is nearly right. The
player is the exception — CharGen runs once at character creation and no mod can
re-trigger it. See section 4.

---

## 1. What to install, and what is actually load-bearing

### CKPE — Creation Kit Platform Extended (Nexus 51165)

**Install this.** It is the one addon that changes the CK from painful to
usable: render-window crash mitigation, 64-bit support, faster loads.

*Unverified:* the published supported-CK list names builds up to 1.11.137.0.
Ours is 1.11.240.0, newer. Confirm a compatible build exists before relying on
it, and keep the vanilla CK working as a fallback.

### Transfer Settlements (Nexus 22442)

**Verified compatible.** The mod page states an AE build for
**Fallout 4 1.11.240 + F4SE 0.7.9** — exactly this machine.

Install notes that are not optional:

- Needs F4SE's `Data\Scripts\F4SE.pex` **and** `Data\Scripts\ObjectReference.pex`.
  Copy the whole F4SE `Data` folder, not just the loader.
- Needs HUDFramework (already present).
- `Fallout4Custom.ini` must contain, under `[Archive]`:
  `bInvalidateOlderFiles=1` and `sResourceDataDirsFinal=`
- Launch the game through `f4se_loader.exe`, not `Fallout4.exe`.
- Blueprints land in
  `Data\F4SE\Plugins\TransferSettlements\blueprints\<slot>\*.json`

Known gotcha: export requires a workbench nearby, and the common failure is
"no workshops found". That is usually the settlement not being wired as a
workshop — which is exactly what section 3 fixes.

---

## 2. Blueprint to ESP: the tool is not what the guides say

The common walkthrough says "run a Blueprint to ESP Converter". The real
tooling is:

- **DieFeM's "Import Transfer Settlements Blueprint to ESP"** — an **xEdit
  (FO4Edit) script**, not a standalone application. It needs the vanilla ESM
  loaded in xEdit.
- **Settlement Distributor** — a Win32 tool that converts a blueprint into a
  **standalone `esp` + script pair that does not require F4SE or Transfer
  Settlements**.

Prefer Settlement Distributor if it is available. A standalone `.esp` matters
for us specifically: it keeps the test area loadable without F4SE, which is the
whole G7 claim. An F4SE-dependent test area would prove nothing about PIP-MON
running standalone.

---

## 3. Make the cell a vanilla workshop settlement

This is the step that is easy to get subtly wrong, and it is what makes
Transfer Settlements and the `V` key work at all.

1. Drag a **workbench** into the cell (a `WorkshopWorkbench`, or any
   workbench-type object).
2. Drag a **trigger volume** over the whole interior.
3. On the trigger, set **Linked Ref** to the workbench and give it the keyword
   `WorkshopLinkedPrimitive`.
4. In the cell's **Location** record, add the keywords:
   - `LocTypeSettlement`
   - `LocTypeWorkshop`
   - `LocTypeWorkshopSettlement`

Only after step 4 will Workshop mode and blueprint export see the cell as a
settlement. A missing `LocTypeWorkshop` is the usual reason a "settlement"
does not register.

---

## 4. The Papyrus step, corrected

**Do not follow the common instruction to attach a `.psc` to a terminal and
give it menu options.** That does not compile with this toolchain.

Verified against `PapyrusCompiler 2.8.0.4` on this machine:

| Construct | Result |
|---|---|
| `Event OnInit()` on a normal script | accepted |
| `Event OnActivate(...)` on a normal script | **rejected** — "not flagged as native" |
| `Event OnMenuClose(...)` on a normal script | **rejected** — same |
| A `Native`-flagged script | may contain **no** properties, no script variables, not even a bare `Int property x` |

So a script that handles terminal events cannot also hold state — the two
requirements are mutually exclusive here.

Ruled out as causes before concluding that: missing base-script types, the
flags file, `.ppj` project vs loose `.psc`, declaration order, and cascading
parse errors. It survives all of them with 62 base scripts staged.

*Caveat, stated honestly:* this contradicts published FO4 examples, so it is
**verified in this configuration**, not proven true of FO4 generally. If the
menu becomes important, re-test before designing around it.

### What to do instead

`PipMonTestFacility.psc` is already written and gated. It:

- keeps its state in `auto readonly` properties,
- exposes plain functions (`RunNativeProbe`, `PlaceActors`, `CheckFixtures`,
  `Unsubscribe`),
- declares only `OnInit`.

The **native side calls it directly.** That is a better shape anyway:

- the verdict goes out over the **PIP-MON wire**, which is this project's real
  output channel (design section 26 — T4 is the dashboard and CLI);
- it exercises **native → Papyrus**, which nothing has tested yet;
- it needs no in-game text output, which matters because **FO4 has no
  `Debug.Notification`** and no usable menu type to fall back on.

Call syntax, since it is the easiest thing to get wrong:

```papyrus
PipMon.GetVersion()        correct
PipMon_GetVersion()        WRONG — "not a function or does not exist"
```

---

## 5. SimSettlements 2 - excluded, not deferred

**SimSettlements 2 is on the main install and is deliberately NOT in the test
environment.** section 3 wires a *vanilla* workshop settlement, which is exactly the
mechanic SS2 intercepts, so including it would put the two in direct conflict
over the same hooks.

This was flagged as the largest unresolved risk on this page. Keeping the test
environment minimal (section 0.2) **resolves it** rather than deferring it, and it is
worth being clear that it is resolved by exclusion and not by compatibility
testing — nobody has run the two together to see what happens.

If a shipped version of this area later needs to work on SS2 installs, that is a
separate piece of work and needs its own test, on an SS2 install.

---

## 6. Vortex

The main install is Vortex-managed, so files written straight into its `Data\`
get flagged as externally modified and can be reverted. That is one more reason
section 0.1 recommends a separate install: a clean directory on `D:\` has no mod
manager to disagree with, so the deployment question disappears rather than
being solved.

If the main install is used anyway, develop in a Vortex staging mod
(`Vortex\mods\staging\<name>\`) and deploy from there.

This is the same class of mistake as the three divergent copies already sitting
in `stage/` — a deployment path nobody owns. One canonical layout with a hash
manifest is the fix, and it is still on the list.

---

## 7. Build order

CK involvement is deliberately tangential: most of the work happens in-engine.

**A. In-engine (no CK).**
Launch via `f4se_loader.exe`. Enter the target cell. Hold `V`, clear it, place
the workbench, trigger volume, power armour station and a terminal. Wire the
settlement per section 3. Verify Workshop mode works before going further.

**B. Export.**
Use the Transfer Settlements holotape → *Export this settlement to a
blueprint* → pick a slot. Confirm the `.json` appears in the blueprints folder.

**C. Convert.**
Settlement Distributor (preferred — standalone output), else DieFeM's xEdit
script. Produce `PipMonTestFacility.esp`.

**D. Creation Kit (the only CK step that matters).**
Launch the CK under CKPE. Load `Fallout4.esm` + the new `.esp`, set the `.esp`
active. In the cell, attach the already-compiled `PipMonTestFacility` script to
the terminal, and fill the properties:

| Property | Assign |
|---|---|
| `TerminalRef` | the terminal |
| `WorkbenchRef` | the workbench |
| `PowerArmorStationRef` | the power armour station |
| `TestNpcRef` / `TestNpcSpawn` | a dialogue NPC / a marker near it |
| `TestRobotRef` / `TestRobotSpawn` | a robot / a marker near it |

Save. That is the entire CK session.

**E. Run.**
Launch, `~`, `coc <CellEditorID>` to drop straight in. The facility probes on
demand. Read the verdict with:

```
python tools\vlink_probe.py --summary-only
```

---

## 8. What is verified and what is not

**Verified here:** the installed tool versions and build numbers; that
Transfer Settlements publishes a build for exactly 1.11.240 + F4SE 0.7.9; that
the blueprint→ESP tooling is an xEdit script rather than a standalone app; the
Papyrus constraints in section 4, by compile probe.

**Not verified:** that any of this has been run. No game has been launched, no
blueprint exported, no `.esp` produced, and `RunNativeProbe()` has never been
called. CKPE compatibility with 1.11.240 is unconfirmed. The section 5 SimSettlements conflict is resolved by exclusion rather than by compatibility testing; nobody has run the two together.

Treat this document as a build plan with a verified parts list, not a report of
something that works.