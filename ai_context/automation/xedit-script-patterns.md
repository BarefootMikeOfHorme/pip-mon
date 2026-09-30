---
source_url: https://github.com/TES5Edit/xEditScripts ; https://github.com/TES5Edit/mxpf
retrieved_utc: 2026-09-30T21:28:15Z
content_kind: index-authored
trust: This index is authored. Every .pas file listed below is upstream working code, saved verbatim and verified byte-identical to its upstream git blob SHA (sha1 of raw blob == sha1 of file on disk, no line-ending or encoding conversion applied).
---

# xEdit Pascal Script Patterns — Index

Two upstream repositories, both retrieved in full as real source. Nothing here is
paraphrased, refactored or summarised inside the `.pas` files themselves.

| Repo | URL | Commit retrieved | Default branch |
|---|---|---|---|
| xEditScripts | `https://github.com/TES5Edit/xEditScripts` | `c93d6266059496e94eb20e7dcc0f14c122885943` | `master` |
| mxpf | `https://github.com/TES5Edit/mxpf` | `f63f9328c096ecd38c8cd37b24494405894a56d8` | `master` |

Note: `TES5Edit/mxpf` is a mirror of `matortheeternal/mxpf` (same author, `Edit Scripts/lib/mxpf.pas`).
Both URLs resolve; `TES5Edit/mxpf` was used.

---

## 1. `xEditScripts\` — TES5Edit/xEditScripts

Local path prefix: `ai_context\automation\xEditScripts\`
Repo path prefix: `Scripts/`

| Local file | Repo path | Bytes | Blob SHA (short) | Pattern demonstrated |
|---|---|---|---|---|
| `Scripts\Resolve Errors.pas` | `Scripts/Resolve Errors.pas` | 7207 | `fabf6608` | Load-order/master error correction; rewrites broken FormIDs via `RecordByFormID` |
| `Scripts\Quick Scripts - Resolve Errors.pas` | `Scripts/Quick Scripts - Resolve Errors.pas` | 13609 | `5450a547` | Deeper recursive override resolver walking nested levels L0-L4 |
| `Scripts\Copy, Edit, and Flag References.pas` | `Scripts/Copy, Edit, and Flag References.pas` | 4888 | `2a29a884` | Copies references into new patch, renames, sets flags |
| `Scripts\Form FLST - Create COBJ (FLST).pas` | `Scripts/Form FLST - Create COBJ (FLST).pas` | 9134 | `3f5400fc` | `AddNewFile` patch creation, formlist-driven reference remap |
| `Scripts\Find and Replace References (FLST).pas` | `Scripts/Find and Replace References (FLST).pas` | 9134 | `60180b3d` | Origin/destination formlist reference replacement, patch-mode branching |
| `Scripts\Quick Scripts - Find and Replace COBJ References (FLST).pas` | `Scripts/Quick Scripts - Find and Replace COBJ References (FLST).pas` | 9378 | `775cc97a` | Bulk COBJ reference find/replace driven by two formlists |
| `Scripts\Form CELL - Update Owner to Parent XOWN.pas` | `Scripts/Form CELL - Update Owner to Parent XOWN.pas` | 8911 | `a98e4c03` | Parent-cell walk via `LinksTo`, XOWN owner element get/set |
| `Scripts\Form CELL - Copy and Update Owner to Parent XOWN.pas` | `Scripts/Form CELL - Copy and Update Owner to Parent XOWN.pas` | 9753 | `00bbdb51` | Copies an owner reference then rewrites it with `SetElementEditValues` |
| `Scripts\Recount KSIZ, COCT, LLCT, PKCU, PRKZ, SPCT, INAM, and QNAM subrecords.pas` | same | 19584 | `cf31ac24` | Recount count subrecords from `ElementCount`, `RemoveElement` cleanup |
| `Scripts\Form RACE - Renumber TIRS subrecords.pas` | `Scripts/Form RACE - Renumber TIRS subrecords.pas` | 5394 | `699564eb` | Indexed subrecord array renumber via `ElementByIndex`/`ElementByPath` |
| `Scripts\Export AMMO, ARMO, COBJ, MISC, and WEAP Records.pas` | same | 12565 | `089e5226` | Multi-signature record export; deep `ElementByName`/`ElementByPath` walk |
| `Scripts\dubhFunctions.pas` | `Scripts/dubhFunctions.pas` | 27260 | `e6b699e3` | Shared helper library: override/master and element get/set primitives |

Also saved verbatim: `README.md` (147 B), `LICENSE` (35143 B).

### Required coverage map (as requested)

| Requirement | Primary files |
|---|---|
| Iteration over records | `Recount KSIZ...`, `Export AMMO...`, `Form CELL - Update Owner...` (all use `Process(e: IInterface)` per-record entry point) |
| Master / override handling | `Resolve Errors.pas`, `Quick Scripts - Resolve Errors.pas`, `dubhFunctions.pas` (`OverrideMaster`, `LastOverride`, `AddOverrideToFile`, `AddGroupBySignature`) |
| Element get / set | `Recount KSIZ...` (`GetElementNativeValues` / `SetElementNativeValues`), `Form RACE - Renumber TIRS...` (`GetNativeValue` / `SetNativeValue`), `Form CELL - ...XOWN.pas` (`GetElementEditValues` / `SetElementEditValues`), `Export AMMO...` (`GetEditValue`, `ElementBySignature`) |
| Saving | `Find and Replace References (FLST).pas`, `Form FLST - Create COBJ (FLST).pas`, `Copy, Edit, and Flag References.pas` (all use `AddNewFile`) |

---

## 2. `mxpf\` — TES5Edit/mxpf (Mator's xEdit Patching Framework)

Local path prefix: `ai_context\mxpf\` — repo structure preserved exactly.

| Local file | Repo path | Bytes | Blob SHA (short) | Pattern demonstrated |
|---|---|---|---|---|
| `Edit Scripts\lib\mxpf.pas` | `Edit Scripts/lib/mxpf.pas` | 29501 | `00db2220` | The patch-generation framework itself (see API surface below) |
| `Edit Scripts\lib\mteFunctions.pas` | `Edit Scripts/lib/mteFunctions.pas` | 81824 | `d5276551` | Low-level element/master/string utility library; heavily documented |
| `Edit Scripts\lib\jvTest.pas` | `Edit Scripts/lib/jvTest.pas` | 6190 | `ccb9b733` | Unit-test harness for xEdit scripts |
| `Edit Scripts\MXPF - Save female NPCs.pas` | same | 1070 | `d315001f` | Smallest complete MXPF example: select files, load records, filter, export |
| `Edit Scripts\MXPF - Save Female NPCs - Quick.pas` | same | 1025 | `eb93deb1` | Same task via the `QuickLoad`/`QuickPatch` one-liners |
| `Edit Scripts\MXPF - Rebalance Armors.pas` | same | 1714 | `62e17376` | Bulk field edit then copy records into a generated patch |
| `Edit Scripts\MXPF - Reweight Keys.pas` | same | 493 | `340cefcb` | Minimal template for a targeted compatibility patch |
| `Edit Scripts\MXPF - Tests.pas` | same | 54515 | `57dbf2f9` | ~50 jvTest cases; heavy record-tree parsing examples |
| `Edit Scripts\jvTest - Example.pas` | same | 1668 | `9e2b1eb1` | How to write assertions against a loaded record tree |

Also saved verbatim: `Documentation\mxpf.html` (30226 B), `README.md` (1750 B), `license.txt` (1048 B).

### mxpf public API surface (from `lib/mxpf.pas`)

Declared procedures/functions, in file order:

```
InitializeMXPF            DefaultOptionsMXPF        FinalizeMXPF
PatchFileByAuthor         PatchFileByName           SetExclusions / SetInclusions
LoadRecords               LoadChildRecords          MaxRecordIndex / GetRecord / RemoveRecord
AddMastersToPatch         CopyRecordToPatch         CopyRecordsToPatch
MaxPatchRecordIndex       GetPatchRecord            MultiFileSelectString
SetFileSelection          MultiLoad                 QuickLoad
QuickPatch                PrintMXPFReport
DebugMessage / DebugList  SaveDebugMessages         PrintDebugMessages
FailureMessage            SaveFailureMessages       PrintFailureMessages
```

`QuickPatch(sAuthor, sFiles, sRecords, bMode)` is the four-call composition:
`InitializeMXPF` → `DefaultOptionsMXPF` → `PatchFileByAuthor` →
`SetFileSelection` → `MultiLoad` → `CopyRecordsToPatch`.

---

## Cross-repository dependency

`xEditScripts/Scripts/dubhFunctions.pas` begins with:

```pascal
unit dubhFunctions;

uses mteFunctions;
```

`mteFunctions` is **not** in the xEditScripts repo; it is provided by
`mxpf/Edit Scripts/lib/mteFunctions.pas`, which is saved here. Both units must sit
side by side in xEdit's `Edit Scripts` folder for `dubhFunctions.pas` to compile.
This is why `mteFunctions.pas` is included despite mxpf being listed separately.

---

## Important usage constraints observed in the real code

1. **These scripts are authored for Skyrim.** Every header reads
   `Game: The Elder Scrolls V: Skyrim`. The xEdit scripting *engine* and the
   `Iwb*` / `IInterface` function names are identical in FO4Edit, but record
   signatures and subrecord layouts are not. Signature-gated branches
   (`if Signature(e) = 'COBJ'`, `'REFR'`, `'CELL'`, `'RACE'`, `'FLST'`,
   `'LVLI'`) and hardcoded subrecord constants (`KSIZ`, `COCT`, `LLCT`, `PKCU`,
   `PRKZ`, `SPCT`, `INAM`, `QNAM`, `XOWN`, `TIRS`) must be re-validated against
   Fallout 4 record definitions before reuse. Do not assume Skyrim layout.
2. **Scripts do not explicitly save the plugin.** There is no `wbSave`/`Commit`
   call anywhere in these files. `AddNewFile` creates the new patch inside the
   live xEdit session; the user then saves through the xEdit UI. Every
   `SaveToFile` call in these scripts is `TStringList.SaveToFile` writing a
   report/log CSV or TXT, not a plugin write.
3. **Two entry points.** Scripts implement `function Initialize: Integer;`
   (setup, prompt user, return 1 to abort) and `function Process(e: IInterface): Integer;`
   (called once per selected record; returning nonzero stops iteration).
   `Export AMMO...` additionally shows `InitializeUI`/`RequiredVersion` handling.
4. **Load order, not filenames, identifies plugins.** Patterns of the form
   `FileByLoadOrder(StrToInt('$' + sNewIndex))` and `RecordByFormID(file, $06FF0000, false)`
   are the dominant idiom for resolving a master or patch target.
5. **FormIDs are manipulated as 8-char hex strings**, e.g.
   `IntToHex(GetNativeValue(L0), 8)`, then `Copy(s, 1, 2)` / `Delete` / `Insert`
   to rewrite the load-order prefix — the classic load-order-shift repair.

---

## Verification method

For each file:

1. `git rev-parse HEAD:<repo path>` → upstream blob SHA1.
2. `git cat-file blob <sha>` redirected at the byte level to the destination.
3. `git hash-object --no-filters <destination>` compared to the blob SHA.

All 12 xEditScripts files and all 9 mxpf `.pas` files matched on step 3, so the
bytes on disk are identical to the bytes committed upstream. Note this also
avoids the CRLF conversion a normal Windows `git clone` checkout would apply
(the repos carry `* text=auto`, so upstream blobs are LF-only).