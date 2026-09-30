---
title: Fallout 4 records and the xEdit 4.1.5f scripting API
purpose: How FO4 records are laid out, and which xEdit scripting functions actually exist. Read before writing any .pas script or planning record generation.
derived_from:
  - ai_context/reference/xedit/13-scripting-functions.md  (upstream, verbatim, fetched 2026-09-30)
  - ai_context/reference/xedit/02-overview.md
  - ai_context/reference/xedit/07-mod-cleaning-and-error-checking.md
  - runs/xedit/fo4edit-4.1.5f-pascal-api.md  (measured on this machine)
authority: measured
trust: >
  Function names below are transcribed from the official TES5Edit documentation
  page 13, cross-checked against execution on FO4Edit 4.1.5f x64 (7C57FA01).
  Where the two disagree, execution wins and the disagreement is recorded.
---

# FO4 records and the xEdit scripting API

## 1. The three-tier confidence rule

When this document and a runtime error disagree, the runtime error is the
truth. This project has already been caught by one such case, so the rule is
recorded rather than assumed:

| Claim | Source | Standing |
| --- | --- | --- |
| `GetPluginName` | nowhere | **Does not exist.** Confirmed twice: absent from the official function list, and a real run aborted with `Undeclared Identifier 'GetPluginName'`. |
| `ProgramPath` | docs 13.4 | Exists, but as a read-only **global**, not a function. `outName := ProgramPath + 'x.json'` is legal. |
| `AddMessage` | docs 13.6 / 13.20 | Exists. |
| `AddNewElement` | nowhere | **Does not exist.** The real calls are `IwbContainer.AddElement`, `IwbContainer.Add`, `IwbContainer.InsertElement`. |
| `GetActivePlugin` | nowhere | **Does not exist.** Not in any documented class. |
| `SetElementEditValues` | docs 13.8 | Exists on `IwbContainer`. |

A script that fails to compile produces **no output at all**, which a caller
cannot distinguish from "the plugin was fine and there was nothing to say".
Always read the xEdit log and captured stdout before believing any result.

## 2. Documented globals (read-only, not functions)

From docs 13.4: `DataPath`, `ProgramPath`, `ScriptsPath`, `FileCount`,
`wbAppName`, `wbVersionNumber`.

## 3. Base script structure

A unit has exactly three entry points (docs 13.17):

```pascal
function Initialize: Integer;      // before the load
function Process(e: IInterface): Integer;   // once per record
function Finalize: Integer;        // after the load
```

Verified by execution in 4.1.5f: `Signature`, `GetElementEditValues`,
`FixedFormID`, `IntToHex`, `TStringList`, `AssignFile`/`Rewrite`/`WriteLn`/
`CloseFile`, `IntToStr`, `Copy`, `Length`.

## 4. The object model, by class

### IwbFile (docs 13.9) -- the plugin itself

`AddNewFileName`, `AddMasterIfMissing`, `GetFileName`, `GetIsESM`, `SetIsESM`,
`GetNewFormID`, `GetLoadOrder`, `MasterCount`, `MasterByIndex`, `HasMaster`,
`CleanMasters`, `SortMasters`, `FileFormIDtoLoadOrderFormID`,
`FileWriteToStream`, `GetFile` family, `RecordCount`, `RecordByIndex`,
`RecordByFormID`, `RecordByEditorID`, `GroupBySignature`, `HasGroup`.

### IwbContainer (docs 13.8) -- groups and masters

`Add`, **`AddElement`**, `InsertElement`, `RemoveElement`, `RemoveByIndex`,
`ElementCount`, `AdditionalElementCount`, `ElementByIndex`, `ElementByName`,
`ElementByPath`, `ElementBySignature`, `ElementExists`, `IndexOf`, `LastElement`,
`ReverseElements`, `IsSorted`, `GetElementEditValues`, `SetElementEditValues`,
`GetElementNativeValues`, `SetElementNativeValues`, `ContainerStates`.

### IwbMainRecord (docs 13.10)

`Signature`, `BaseRecord`, `EditorID`, `SetEditorID`, `FormID`, `FixedFormID`,
`GetFormVersion`, `SetFormVersion`, `GetIsDeleted`, `SetIsDeleted`,
`GetIsInitiallyDisabled`, `SetIsInitiallyDisabled`, `GetPosition`,
`SetPosition`-family, `GetRotation`, `GetGridCell`, `ChangeFormSignature`,
`IsMaster`, `IsWinningOverride`, `HighestOverrideOrSelf`, `MasterOrSelf`,
`OverrideCount`, `OverrideByIndex`, `ReferencedByCount`, `ReferencedByIndex`,
`UpdateRefs`, `ReportRequiredMasters` (on IwbElement).

### IwbElement (docs 13.7) -- per-field access

`GetEditValue`, `SetEditValue`, `GetNativeValue`, `SetNativeValue`,
`GetElementState`, `SetElementState`, `ElementType`, `ElementAssign`,
`EnumValues`, `FlagValues`, `DefType`, `BaseName`, `ShortName`, `Name`,
`DisplayName`, `FullPath`, `PathName`, `GetContainer`, `GetFile`, `Remove`,
`ClearElementState`, `SetToDefault`, `SortKey`, `BuildRef`, `LinksTo`,
`ContainingMainRecord`, `CanContainFormIDs`, `MarkModifiedRecursive`,
`IsInjected`, `IsEditable`, `BeginUpdate`/`EndUpdate`.

### IwbGroupRecord (docs 13.11)

`FindChildGroup`, `ChildrenOf`, `GroupLabel`, `GroupType`, `MainRecordByEditorID`.

## 5. The cell recipe

**This section was wrong twice and was corrected against the fetched
signatures. Read it as a corrected hypothesis, not as working code.** The first
version was written from function *names* alone and got three things wrong. The
signatures are what matter; the names are suggestive and frequently misleading.

### 5a. DANGEROUS: do not use AddNewFileName / AddNewFile to "register" a plugin

Docs 13.9, verbatim:

> **AddNewFileName** — Creates a new, empty plugin using FileName as the name in
> the game's plugin folder (Data) and adds it to the end of the plugins list.

> **AddNewFile** — Creates a new, empty plugin in the game's plugin folder (Data)
> and adds it to the end of the plugins list.

These do not register an existing plugin. They **create a new file in the game
folder and mutate the plugin list**. Using them to "activate"
`PipMonTestFacility.esp` would have produced a spurious empty plugin and an
edited `plugins.txt` -- a silent, destructive side effect from a call that reads
like a registration.

To act on a plugin that is *already loaded*, the documented route is a lookup,
not a creation:

| Need | Call | Source |
| --- | --- | --- |
| The Nth loaded file | `FileByIndex(aeIndex)` | docs 13.6 |
| The file at a load-order slot | `FileByLoadOrder(aeLoadOrder)` | docs 13.6 |
| The file owning a record | `IwbElement.GetFile` | docs 13.7 |
| Its name | `IwbFile.GetFileName` | docs 13.9 |
| Its load-order index | `IwbFile.GetLoadOrder`, `-1` if it is not an IwbFile | docs 13.9 |

### 5b. Verified create semantics: `Add` is the idempotent one

| Call | Signature | Behaviour, verbatim |
| --- | --- | --- |
| `Add` | `Add(aeContainer: IwbContainer; asNameOrSignature: string; abSilent: boolean): IwbElement` | "Creates a child element with the name-or-signature *asNameOrSignature* in *aeContainer* **if no such child already exists; otherwise, marks the existing child as modified.** Returns the created or existing element." |
| `AddElement` | `AddElement(aeContainer: IwbContainer; aeElement: IwbElement)` | "Adds *aeElement* as a child of *aeContainer*. **Throws an error if *aeElement* already has a container.**" |

So `Add` is the create-or-get call, and it is safe to re-run. `AddElement` only
attaches an already-constructed element, and **throws** if that element is
already parented -- so it is the wrong call for record creation and a crash
waiting to happen if used that way.

### 5c. World position to cell group, and what is still missing

```
wbPositionToGridCell(akPosition: TwbVector): TwbGridCell
```

> Converts *akPosition* to grid coordinates. In practice, this is done by
> dividing the physical coordinates by **4096**, the lateral length and width of
> a cell.

Useful companions in the same section: `wbGridCellToGroupLabel`,
`wbSubBlockFromGridCell`, `wbBlockFromSubBlock`, `wbIsInGridCell`.

A cell's top-level group is keyed by a *label* derived from the grid cell, not
by a signature. That leaves two genuine gaps, and both are unproven:

1. **Getting a `TwbVector`.** `wbPositionToGridCell` takes one, and no
   documented constructor for `TwbVector` appears in the function list. Until
   one is found, this call may be unreachable from script.
2. **Finding a top-level group by label.** `IwbFile.GroupBySignature` is
   signature-only, and no `GroupByLabel` is documented. Whether `IwbFile` exposes
   its top-level groups for iteration -- and whether it inherits
   `IwbContainerBase` -- is unverified.

Both gaps are *read* questions, not design questions, and both are answerable
from the structure. Neither is a reason to give up on the approach.

### 5d. What the corrected sequence looks like

```
lookup:      FileByLoadOrder / FileByIndex / e.GetFile   ; NOT AddNewFileName
group label: wbPositionToGridCell(vector) -> wbGridCellToGroupLabel(cell)
group:       find top-level group by LABEL               ; UNPROVEN, no documented call
formid:      IwbFile.GetNewFormID                        ; "the same way that Add(...,...,True) does"
record:      IwbContainer.Add(group, 'CELL', false)      ; idempotent create-or-get
fields:      IwbElement.SetEditValue                     ; XCLR / XCLL / XCLW / XCEL / UNAM
save:        IwbFile.FileWriteToStream                   ; cf. "SaveAs.pas" in the shipped scripts
```

`FileWriteToStream` is documented as being used by the shipped `SaveAs.pas`,
which creates a `TFileStream` and writes the loaded file under a new name. That
is the closest thing upstream documentation offers to a save operation, and it
is worth reading that script directly before writing our own.

The shipped `Edit Scripts` folder is a real corpus of working xEdit automation
and is the best available answer to "how do I actually do this". Point
`pipmon.ps1 rag query --path "ai_context"` at it once indexed.

## 6. Record layout, in brief

An `.esp`/`.esm` is a TES4 header followed by GRUP groups, each holding records.
Record identity is a FormID: a byte for load order, a byte for the local index
inside the plugin, and two bytes of group. Load order matters because FormIDs
resolve through it.

Reading order for a clean audit is docs page 7, *Mod Cleaning and Error
Checking*. The overview is page 2.

## 7. What xEdit actually loads, and why it surprised us

xEdit loads **three** sources, not one:

1. `%LOCALAPPDATA%\Fallout4\Plugins.txt` -- the active plugin list, which this
   project curates to 35 core entries.
2. `Fallout4.ccc` -- the Creation Club content list.
3. The DLC list.

So the curated profile does **not** bound the load. `DLCUltraHighResolution.esm`
and the whole CC set appear regardless, and `standaloneworkbenches.esl` arrives
as a *master* of `whispercraftpowerarmor.esp` even though it is not in the
profile at all. Plugin graph and resource graph are different reports and must
be reported separately.

## 8. Load timing on this machine

A full core load reaches `Finalize` at about **2m15s**, roughly 3 minutes wall
clock. It is not hung. A timeout under about 4 minutes produces a false
negative; a 90s and a 110s timeout each produced one here before this was
measured.

The first run blocks indefinitely on xEdit's first-run notice until a human
dismisses it. Until that happens, headless must report `SKIP`.

## 9. Current facility plugin state

`Data\PipMonTestFacility.esp` is **66 bytes, CRC32 `E1DD5E4D`, 0 records**.
xEdit's own load log states `Header processed. Expecting 0 records`. There is no
cell, no fixtures, no geometry, and no properties yet.

## 10. Safety

- Never launch a second xEdit while one is running. Two engines writing the
  same Data folder is the failure to prevent.
- Never run xEdit or the CK headlessly while either is open interactively.
- Long runs are launched detached and polled. A blocking three-minute wait makes
  the caller unresponsive and invites killing a process that was working.
- `tools\validate_plugin.ps1` refuses rather than guessing, and reports `SKIP`
  when it could not run.
