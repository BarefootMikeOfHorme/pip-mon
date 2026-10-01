---
title: Fallout 4 xEdit (FO4Edit) Command & Shortcut Reference
doc_type: cheat-sheet
application: xEdit / FO4Edit (FO4Edit.exe / xEdit.exe)
version: 4.1.x +
purpose: Fast retrieval lookup for xEdit keybindings, record navigation, conflict filtering, override generation, script automation, and batch operations.
authority: unproven
trust: Combined official xEdit documentation, ElminsterAU/xEdit GitHub wiki, and community modding standards. Conf ratings indicate reliability per item.
derived_from:
  - xEdit Official Documentation & GitHub Wiki
  - FO4Edit / SSEEdit Community Cleaning & Conflict Resolution Guides
  - Modding Community Best Practices for Record Editing
reviewed: 2026-10-01
rag_optimization: Standardized ID schema (XEDIT-AREA-NN), fully self-contained section context, uniform table attributes, bi-directional lookup indexes, and chunk-resilient sizing (<1250 chars/section).
keywords: [xEdit, FO4Edit, SSEEdit, FNVEdit, TES5Edit, FormID, Conflict Winner, Conflict Loser, Deep Copy as Override, Apply Filter for Cleaning, Quick Auto Clean, Automation Scripts, Pascal, Record Tree, View Tab, Subrecords, Header, Master Files]
---

# Fallout 4 xEdit (FO4Edit): Command & Shortcut Reference

How to read this sheet: Every entry uses a unique, permanent identifier (`XEDIT-AREA-nn`), an explicit task statement, key/menu input, context notes, and a Confidence Code (**Conf**).

**Confidence Code Legend:**
* **`H` (High):** Verified consensus across official xEdit documentation and GitHub wiki.
* **`L` (Low):** Discrepancy between sources or context-dependent behavior.
* **`V` (Verified Local):** Verified in active xEdit / FO4Edit execution environment.
* **`P` (Procedure Local):** Prescribed workflow documented for mod maintenance.
* **`U` (Unrated):** Sourced outside primary comparison sets; unverified rating.

---

## 1. Startup, Data Loading & Mode Flags (Area: START)
Context: Executable parameters, plugin selection dialogs, automated cleaning modes, startup performance flags, and plugin saving.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| XEDIT-START-01 | Load selected plugins | **Module Selection Dialog → OK** | Double-click or check plugins to load into record tree | H |
| XEDIT-START-02 | Quick Auto Clean mode | Command Parameter: `-quickautoclean` | Launches automated, single-plugin cleaning pipeline | H |
| XEDIT-START-03 | Skip distant LOD loading | Command Parameter: `-b:1` or `-i:1` | Accelerates startup by bypassing distant LOD / image space cache | H |
| XEDIT-START-04 | Save modified plugins | `CTRL+S` (or close application prompt) | Opens save dialog for all modified plugins | H |
| XEDIT-START-05 | Enable Expert Mode | **Options → Options → General → Enable Expert Mode** | Unlocks advanced editing menus, warning bypasses, and raw edits | H |

---

## 2. Record Tree Navigation & Link Following (Area: NAV)
Context: FormID tree navigation, jumping through record references, history tracking, and selection expansion.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| XEDIT-NAV-01 | Expand / collapse branch | `Right Arrow` / `Left Arrow` (or `+` / `-`) | Expands or collapses active node in Left Navigation Tree | H |
| XEDIT-NAV-02 | Jump to FormID | `CTRL+F` (or FormID input box top-left) | Focuses navigation directly onto typed 8-digit FormID | H |
| XEDIT-NAV-03 | Follow reference link | `CTRL` + Click on FormID link | Jumps directly to target record in View Tab | H |
| XEDIT-NAV-04 | Navigate backward in history | `ALT+Left Arrow` (or Back button top-left) | Returns to previously viewed record in link history | H |
| XEDIT-NAV-05 | Navigate forward in history | `ALT+Right Arrow` (or Forward button top-left) | Advances forward in record link history | H |
| XEDIT-NAV-06 | Locate record in Tree View | `CTRL+SHIFT` + Click link (or Right-click → Select in tree) | Highlights linked record in Left Navigation Tree | H |
| XEDIT-NAV-07 | Select next / previous record | `Down Arrow` / `Up Arrow` | Moves selection down/up in Left Navigation Tree | H |

---

## 3. Record Copying & Override Creation (Area: COPY)
Context: Injecting record overrides, deep copies with dependencies, creating new record copies, and cross-plugin field dragging.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| XEDIT-COPY-01 | Copy record as override | Right-click record → **Copy as override into...** | Copies form into target plugin as a record override | H |
| XEDIT-COPY-02 | Deep copy as override | Right-click record → **Deep copy as override into...** | Copies record and all referenced sub-records recursively | H |
| XEDIT-COPY-03 | Copy record as new record | Right-click record → **Copy as new record into...** | Generates duplicate record with a fresh, unique FormID | H |
| XEDIT-COPY-04 | Copy field value across columns | Drag field value (or `CTRL+C` / `CTRL+V`) | Overwrites field in target column with value from source column | H |
| XEDIT-COPY-05 | Compare multiple records | Select multiple records in tree → View Tab | Displays selected records side-by-side for comparison | H |
| XEDIT-COPY-06 | Remove record / override | `DELETE` (or Right-click → **Remove**) | Deletes record from target plugin (reverts to master) | H |

---

## 4. Conflict Filtering & Color Legend (Area: FILTER)
Context: Conflict filter configuration, cleaning filters, and interpreting visual highlight color codes in View Tab columns.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| XEDIT-FILTER-01 | Open Apply Filter dialog | Right-click tree → **Apply Filter...** | Configures global record filtering parameters | H |
| XEDIT-FILTER-02 | Filter for Conflict Resolution | Apply Filter → Check **Conflict status overall** | Isolates conflicting records across active load order | H |
| XEDIT-FILTER-03 | Filter for ITM/UDR Cleaning | Apply Filter → Check **Identical to Master** & **UDR** | Identifies candidates for mod cleaning | H |
| XEDIT-FILTER-04 | Clear active filter | Right-click tree → **Clear Filter** (or `CTRL+F5`) | Resets tree view to show all records | H |
| XEDIT-FILTER-05 | Conflict Color: Green | Visual Indicator (Background / Text) | Single record (no conflict) or Identical Overrides | H |
| XEDIT-FILTER-06 | Conflict Color: Yellow | Visual Indicator (Background / Text) | Override without conflict (minor difference / addition) | H |
| XEDIT-FILTER-07 | Conflict Color: Red | Visual Indicator (Background / Text) | Critical conflict (Conflict Winner / Conflict Loser) | H |
| XEDIT-FILTER-08 | Conflict Color: Purple | Visual Indicator (Background / Text) | Master record / injected record conflict | H |

---

## 5. Automation Scripts & Pascal Execution (Area: SCRIPT)
Context: Executing Pascal automation scripts, running batch transformations, text search/replace, and exporting data reports.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| XEDIT-SCRIPT-01 | Open Apply Script dialog | `CTRL+N` (or Right-click record(s) → **Apply Script...**) | Displays script selector list (`\Edit Scripts\` directory) | H |
| XEDIT-SCRIPT-02 | Execute selected script | Select script → Click **OK** | Runs Pascal script against all highlighted/selected records | H |
| XEDIT-SCRIPT-03 | Export record properties | Apply Script → **Export properties** | Generates text/CSV export of designated record fields | H |
| XEDIT-SCRIPT-04 | Batch text find & replace | Apply Script → **Replace text in string fields** | Replaces matching strings across selected records | H |
| XEDIT-SCRIPT-05 | Add master flag script | Apply Script → **Set flag on records** | Programmatically updates record flags across selection | H |

---

## 6. Mod Cleaning & Error Checking (Area: CLEAN)
Context: Detecting structural errors, removing Identical to Master (ITM) records, fixing deleted references (UDR), and managing master headers.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| XEDIT-CLEAN-01 | Check for Errors | Right-click plugin → **Check for Errors** | Scans plugin forms for unresolved FormIDs or broken links | H |
| XEDIT-CLEAN-02 | Remove Identical to Master | Right-click plugin → **Remove Identical to Master Records** | Purges redundant record overrides (ITMs) | H |
| XEDIT-CLEAN-03 | Undelete & Disable References | Right-click plugin → **Undelete and Disable References** | Fixes UDRs by setting references to Disabled and moving under floor | H |
| XEDIT-CLEAN-04 | Automated Quick Auto Clean | Command Parameter: `FO4Edit.exe -quickautoclean` | Executes safe standard cleaning sequence automatically | H |
| XEDIT-CLEAN-05 | Clean Unused Masters | Right-click plugin → **Clean Masters** | Removes master header references not actively used | H |
| XEDIT-CLEAN-06 | Add Master dependency | Right-click plugin → **Add Masters...** | Explicitly adds master plugin dependency to header | H |

---

## 7. Record View Editing & Field Operations (Area: EDIT)
Context: Direct field editing, array manipulation, flags toggling, raw hexadecimal inspection, and subrecord management in View Tab.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| XEDIT-EDIT-01 | Edit field value | Double-click field (or `F2` / `Enter`) | Opens inline text / numeric / dropdown editor | H |
| XEDIT-EDIT-02 | Add array / subrecord element | Right-click field category → **Add** | Appends new item or subrecord entry to array | H |
| XEDIT-EDIT-03 | Remove subrecord element | Right-click subrecord → **Remove** (or `DELETE`) | Removes array item or subrecord entry | H |
| XEDIT-EDIT-04 | Edit flag bitfield | Double-click flag field | Opens checkbox matrix to toggle individual flag bits | H |
| XEDIT-EDIT-05 | Toggle Raw Data view | View Tab bottom → **Toggle Raw View** | Displays underlying binary/hex representation of subrecord | H |
| XEDIT-EDIT-06 | Hide unchanged fields | Right-click View Tab → **Hide No Conflicts** | Hides identical fields to focus purely on record differences | H |

---

## 8. Master Header, ESL Conversion & Options (Area: OPT)
Context: File Header modification, Light Master (ESL) flag setting, Master sorting, UI settings, and environment options.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| XEDIT-OPT-01 | Set Light Master (ESL) flag | File Header → Record Flags → Check **ESL** | Flags plugin as ESL without changing file extension | H |
| XEDIT-OPT-02 | Sort Masters | Right-click plugin → **Sort Masters** | Reorders master list in header to match active load order | H |
| XEDIT-OPT-03 | Edit Plugin Author / Description | File Header → **CNAM / SNAM** | Updates metadata fields stored in plugin header | H |
| XEDIT-OPT-04 | Open Options dialog | **Options → Options** | Configures UI font scaling, colors, cache paths, and safety checks | H |
| XEDIT-OPT-05 | View loaded plugins summary | Information Tab (bottom right) | Displays total record count, load order index, and file paths | H |

---

## 9. System Limitations & Non-Supported Features (Area: NO)
Context: Explicit limitations of xEdit architecture compared to full Creation Kit rendering and engine execution.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| XEDIT-NO-01 | 3D Viewport Rendering | Not Available | xEdit is record-based; no 3D mesh or scene rendering viewport | H |
| XEDIT-NO-02 | Graphical Navmesh Editing | Not Available | Visual navmesh node positioning requires Creation Kit | H |
| XEDIT-NO-03 | Landscape Heightmap Sculpting | Not Available | Terrain heightmap sculpting requires Creation Kit Landscape Editor | H |
| XEDIT-NO-04 | In-Place FormID Renumbering on Saves | Restricted | Modifying FormIDs invalidates save files referencing those FormIDs | H |

---

## 10. Source Discrepancies & Operational Edge Cases
Context: Operational nuances, cleaning safety rules, and FormID compaction prerequisites.

| Topic / Feature | Source Conflict / Operational Summary | Associated Entry IDs |
|---|---|---|
| Manual Cleaning vs QuickAutoClean | Manual ITM/UDR cleaning can accidentally purge intentional overrides; `-quickautoclean` is recommended for standard master cleaning. | XEDIT-CLEAN-02, XEDIT-CLEAN-04 |
| ESL Flagging vs FormID Range | Setting ESL flag requires FormIDs to fit within range `000` to `FFF`. Out-of-range FormIDs require compaction prior to flagging. | XEDIT-OPT-01, XEDIT-FILE-02 |
| Conflict Color Priority | Background color represents overall record status, while text color represents individual field status. Red background takes precedence in conflict views. | XEDIT-FILTER-05, XEDIT-FILTER-07 |

---

## 11. Reverse Lookup Index A: Single Key Bindings
Context: Reverse lookup mapping from individual keys to editor commands and entry IDs.

| Key | Associated Task / Command | Entry ID |
|---|---|---|
| `Up Arrow` / `Down Arrow` | Select previous / next record in Left Navigation Tree | XEDIT-NAV-07 |
| `Left Arrow` / `Right Arrow` | Collapse / expand tree branch node | XEDIT-NAV-01 |
| `DELETE` | Remove selected record, override, or subrecord element | XEDIT-COPY-06, XEDIT-EDIT-03 |
| `F2` | Open inline text editor for highlighted record field | XEDIT-EDIT-01 |
| `Enter` | Commit field edit or open field editor | XEDIT-EDIT-01 |

---

## 12. Reverse Lookup Index B: Combination Keys & Mouse Actions
Context: Reverse lookup mapping for modifier key combinations and mouse shortcuts.

| Input Combination | Associated Task / Command | Entry ID |
|---|---|---|
| `ALT+Left Arrow` | Navigate backward in record link history | XEDIT-NAV-04 |
| `ALT+Right Arrow` | Navigate forward in record link history | XEDIT-NAV-05 |
| `CTRL+C` / `CTRL+V` | Copy and paste record field values across columns | XEDIT-COPY-04 |
| `CTRL+F` | Open FormID search input box | XEDIT-NAV-02 |
| `CTRL+F5` | Clear active record tree filter | XEDIT-FILTER-04 |
| `CTRL+N` | Open Apply Script dialog window | XEDIT-SCRIPT-01 |
| `CTRL+S` | Trigger plugin save dialog for modified files | XEDIT-START-04 |
| `CTRL` + Click Link | Follow FormID reference link to target record | XEDIT-NAV-03 |
| `CTRL+SHIFT` + Click Link | Highlight linked FormID target directly in Left Navigation Tree | XEDIT-NAV-06 |
| Double-Click Field | Open editor for field, flag matrix, or dropdown value | XEDIT-EDIT-01, XEDIT-EDIT-04 |
| Drag & Drop Field | Copy field value from source record to target override record | XEDIT-COPY-04 |

---

## 13. Reverse Lookup Index C: Menu Actions & Command Parameters
Context: Reverse lookup mapping for application menu paths and CLI launch parameters.

| Menu / Parameter Input | Associated Task / Command | Entry ID |
|---|---|---|
| `-quickautoclean` | Launch automated single-plugin cleaning pipeline | XEDIT-START-02, XEDIT-CLEAN-04 |
| `-b:1` / `-i:1` | Bypass distant LOD and image space loading on startup | XEDIT-START-03 |
| Right-click → **Add Masters...** | Add master dependency to plugin file header | XEDIT-CLEAN-06 |
| Right-click → **Apply Filter...** | Open conflict / cleaning filter configuration window | XEDIT-FILTER-01 |
| Right-click → **Apply Script...** | Open Pascal automation script selector window | XEDIT-SCRIPT-01 |
| Right-click → **Check for Errors** | Scan selected plugin records for structural errors/broken links | XEDIT-CLEAN-01 |
| Right-click → **Clean Masters** | Purge unused master file references from header | XEDIT-CLEAN-05 |
| Right-click → **Copy as override into...** | Copy record override into existing or new target plugin | XEDIT-COPY-01 |
| Right-click → **Deep copy as override into...** | Recursively copy record and all child subrecords as overrides | XEDIT-COPY-02 |
| Right-click → **Remove Identical to Master Records** | Purge redundant ITM record overrides | XEDIT-CLEAN-02 |
| Right-click → **Sort Masters** | Reorder header masters to match current active load order | XEDIT-OPT-02 |
| Right-click → **Undelete and Disable References** | Fix deleted references (UDRs) by converting to disabled | XEDIT-CLEAN-03 |
| View Tab → **Toggle Raw View** | Switch bottom panel to display raw hexadecimal subrecord data | XEDIT-EDIT-05 |

---

## 14. Retrieval Evaluation Benchmarks (RAG Test Queries)
Context: Synthetic query validation set for testing retrieval pipeline chunk alignment and embedding recall accuracy.

| Sample Query | Expected Target IDs |
|---|---|
| How do I copy a record as an override in xEdit? | XEDIT-COPY-01 |
| How do I navigate backward after clicking a FormID link? | XEDIT-NAV-04 |
| What parameter runs Quick Auto Clean mode in FO4Edit? | XEDIT-START-02, XEDIT-CLEAN-04 |
| How do I filter for conflicts in xEdit? | XEDIT-FILTER-01, XEDIT-FILTER-02 |
| What does a red background color mean in xEdit? | XEDIT-FILTER-07 |
| How do I remove ITM records from my mod? | XEDIT-CLEAN-02 |
| How do I fix UDR deleted references in FO4Edit? | XEDIT-CLEAN-03 |
| How do I toggle the ESL flag on a plugin header? | XEDIT-OPT-01 |
| How do I run a Pascal script on selected records? | XEDIT-SCRIPT-01, XEDIT-SCRIPT-02 |
| How do I jump directly to a FormID in xEdit? | XEDIT-NAV-02 |
| How do I find linked records in the left tree? | XEDIT-NAV-06 |
| Can xEdit render 3D meshes or terrain? | XEDIT-NO-01, XEDIT-NO-03 |
| How do I enable Expert Mode in xEdit? | XEDIT-START-05 |
| How do I check for broken links and errors in a mod? | XEDIT-CLEAN-01 |
| How do I copy field values between records? | XEDIT-COPY-04 |

---

## 15. Source Data Confidence Matrix
Context: Assessment of source reliability across xEdit functional domains.

| Domain Area | Confidence Assessment |
|---|---|
| Startup Flags & Module Selection | **High:** Officially documented in xEdit CLI reference. |
| Record Copying & Override Creation | **High:** Core functionality verified across all xEdit versions. |
| Navigation History & Link Jump | **High:** Standardized across TES4Edit/TES5Edit/FO4Edit/SSEEdit. |
| Conflict Filter & Color Legend | **High:** Official xEdit documentation standard. |
| Automation Scripts (Pascal API) | **High:** Maintained in official `\Edit Scripts\` repository. |
| Mod Cleaning Procedures (ITM/UDR) | **High:** Official xEdit cleaning handbook standard. |
| 3D / Navmesh Limitations | **High:** Architectural boundaries explicitly documented. |