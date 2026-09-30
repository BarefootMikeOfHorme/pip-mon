# PIP-MON Test Facility — Creation Kit session

**Target: fifteen minutes in the CK.** Everything else is scripted, and that is
the whole point of the design.

**Verified on this machine:** `CreationKit.exe` **1.11.240.0**, exact match to
`Fallout4.exe` 1.11.240.0. Already proven working — it compiled
`PipMon.psc` and `PipMonTestFacility.psc` to valid `.pex` images.

---

## Before you open the CK

**CKPE — install this first.** Creation Kit Platform Extended, Nexus **51165**.
It prevents the render-window crashes that make the CK unusable on large cells
and enables 64-bit. *Unverified:* its published supported-CK list names builds
up to 1.11.137.0 and ours is 1.11.240.0, so confirm a compatible build exists.
It installs into `<FO4>\Data\` — which Vortex manages, so add it through Vortex
rather than dropping files in, or Vortex will flag them as externally modified.

Without CKPE the session still works, just worse.

---

## The session

### 1. New plugin

**File → Create.** Name it `PipMonTestFacility`. Choose **ESL** if you want it
light — a test area that will eventually ship should not need an ESM. Set
`Data` to a folder you control, **not** the game's `Data` directory.

### 2. Load

**File → Data**, tick:

- `Fallout4.esm`
- any DLC you intend to use
- your base-environment plugin (the one you're about to give me)
- `PipMonTestFacility.esp`

Then set **`PipMonTestFacility.esp` as Active File.**

### 3. Import the script

**Scripts → Import…** and add
`vprobe\papyrus\build\PipMonTestFacility.pex`.

It is already compiled and gated — do not recompile it in the CK. It declares
`Scriptname PipMonTestFacility` and every property it needs.

### 4. The cell

Either use a cell from your base-environment plugin, or duplicate a vanilla one
to start. Confirm the name in the CK's cell list before building on it: the
community wiki lists the Prydwen interiors as `PrydwenHull01` / `02` / `03`
(refs `0005C92E` / `0014FC54` / `0021630B`), and the name **`BoSPrydwen02`**
that came up earlier is not corroborated by any source I could find. Ten
seconds in the CK settles it.

### 5. Three fixtures, one script

Place exactly three things:

| Fixture | Why |
|---|---|
| a **workbench** | the facility checks it exists |
| a **power armour station** | `EnterPowerArmor()` needs a real station object |
| a **terminal** | carries the script |

Then attach the script to the terminal. That is the entire manual workload.

### 6. Fill in the properties

Select the terminal → **Properties** → **Script**. Every field starts empty;
that is deliberate, because this install is heavily modded and form IDs move. A
hardcoded ID breaks silently the first time a mod shifts the record.

| Property | Assign |
|---|---|
| `TerminalRef` | the terminal itself |
| `WorkbenchRef` | the workbench |
| `PowerArmorStationRef` | the power armour station |
| `SpawnHub` | a marker roughly where the cast should appear |
| `Npc01` … `Npc10` | ten ActorBase faces (any vendor NPCs; vanilla works) |
| `Robot01`, `Robot02` | securutrons / Mister Gutsy |
| `Synth01`, `Synth02` | any synth ActorBase |
| `MerchantRef` | an NPC that will carry a vendor script |
| `KitWeapon` | anything — a rifle is fine |
| `KitPowerArmorFrame` | a T-60 / T-51 / T-45 frame |
| `KitArmor` | any armour piece |
| `KitTestItem` | one odd item, for pickup probes |
| `KitBenchParts` | springs or screws |

**NPC behaviour is the game's, not ours.** Each actor is placed and then handed
straight to the engine with `EvaluatePackage(true)` and `EnableAI(true)`, so
they walk and idle because the game's systems do it. Give them vanilla AI
packages and they behave normally with no further work.

The merchant needs stock — a vendor script and a container, authored CK-side.
A merchant with an empty inventory is just an NPC, and the script deliberately
does not fake that.

### 7. Save, and wire the settlement (if you want Workshop mode)

The trigger volume over the interior, linked to the workbench, keyword
`WorkshopLinkedPrimitive`; then the cell's **Location** record gets
`LocTypeSettlement`, `LocTypeWorkshop`, `LocTypeWorkshopSettlement`.

Skip this if you only need the facility to run — it is for Workshop mode and
blueprint export, not for the script.

### 8. Deploy

Copy to the game:

```
<FO4>\Data\Scripts\PipMonTestFacility.pex
```

Enable the plugin in your mod manager. **Vortex manages this install** — if you
copy files in directly it will flag them as externally modified and may revert
them. Stage it properly.

---

## Verify it landed

```
testfacility\ck\verify_deploy.ps1
```

Checks the `.pex` is in `Data\Scripts`, that the plugin is present in `Data`,
and reports the `Data\PIP-MON\libs` state, because the runtime looks there
first and it was **absent** in every live run so far — the resolver has been
falling back to its embedded dump and still resolving 18/18, which is worth
knowing but is not the intended path.

---

## What is NOT in this session, and why

- **No in-game menu on the terminal.** FO4's Papyrus has no `Menu`/`Option`
  types, and `OnMenuClose` requires a Native script, which may not hold
  properties. Verified by compile probe. The verdict reaches you over the
  telemetry channel instead.
- **No hardcoded form IDs.** See above.
- **No Papyrus recompile.** The `.pex` is built and gated by `build_all.bat`.
