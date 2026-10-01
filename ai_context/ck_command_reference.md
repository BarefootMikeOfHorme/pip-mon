---
title: Fallout 4 Creation Kit Command & Shortcut Reference
doc_type: cheat-sheet
application: Fallout 4 Creation Kit (CreationKit.exe)
version: 1.11.240.0
purpose: Fast retrieval lookup for Creation Kit keybindings, menu commands, viewport navigation, and workflow procedures.
authority: unproven
trust: Combined wiki/Steam guide sources with local machine verification. Conf ratings indicate reliability per item.
derived_from:
  - Fallout 4 Creation Kit Wiki (Official)
  - Steam Community Creation Kit Guide
  - testfacility/ck/README.md (Local repo entries)
  - tools/ck_session.ps1 (Local repo entries)
verified_against: CreationKit.exe 1.11.240.0 (Local executable)
reviewed: 2026-10-01
rag_optimization: Standardized ID schema (CK-AREA-NN), fully self-contained section context, uniform table attributes, bi-directional lookup indexes, and chunk-resilient sizing (<1250 chars/section).
keywords: [Creation Kit, CK, CreationKit.exe, Fallout 4, hotkeys, keyboard shortcuts, key bindings, Render Window, Object Palette, Batch Dialog, Warnings window, Data Window, Active File, FormID, navmesh, Papyrus Manager, light master, FBX, Depth Biasing, camera orbit, axis constraint, grid snap, marker toggle, light radius, deselect]
---

# Fallout 4 Creation Kit: Command & Shortcut Reference

How to read this sheet: Every entry uses a unique, permanent identifier (`CK-AREA-nn`), a explicit task statement, key/menu input, context notes, and a Confidence Code (**Conf**). 

**Confidence Code Legend:**
* **`H` (High):** Verified consensus between Creation Kit Wiki and Steam Guide.
* **`L` (Low):** Discrepancy between sources or unconfirmed behavior.
* **`V` (Verified Local):** Explicitly tested and verified on local development environment.
* **`P` (Procedure Local):** Prescribed workflow documented in repo, awaiting automated execution test.
* **`U` (Unrated):** Sourced outside primary comparison sets; unverified rating.

---

## 1. Data Operations & Startup (Area: START)
Context: Application initialization, loading master files/plugins, setting active workspace, plugin saving, and diagnostic error logging.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-START-01 | Load game data | **File → Data...** | Select `Fallout4.esm` and dependent DLC/master plugins | H |
| CK-START-02 | Set Active File for editing | Set as **(Active File)** in Data Window | Required to persist changes to target plugin | H |
| CK-START-03 | Save active plugin | `CTRL+S` | Performs in-place write to active file | H |
| CK-START-04 | View load & compile warnings | **Warnings window** | Displays automatically on load/save; logs errors | H |
| CK-START-05 | Show internal hotkey menu | **View → Render Window Hotkeys** | Displays CK native keybinding list | H |

---

## 2. Object Placement & Form Handling (Area: PLACE-1)
Context: Object palette selection, reference duplication, movement, deletion, drop-to-ground physics, and clipboard operations.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-PLACE-01 | Open Object Palette | `SHIFT+O` | Opens palette dialog to select base objects | H |
| CK-PLACE-02 | Duplicate selected object | `CTRL+D` | Instantiates copy with a new FormID | H |
| CK-PLACE-03 | Move object reference | `CTRL+M` | Preserves existing FormID during move | H |
| CK-PLACE-04 | Delete selected object | `DELETE` | Removes object reference from cell | H |
| CK-PLACE-05 | Drop object to floor | `F` | Snaps selection down to nearest collision mesh | H |
| CK-PLACE-06 | Standard Paste | `CTRL+V` | Pastes clipboard object with standard offset | H |
| CK-PLACE-07 | Paste in Place | `CTRL+SHIFT+V` | Pastes object maintaining source position/orientation | H |

---

## 3. Object Manipulation & Batch Editing (Area: PLACE-2)
Context: Multibounds generation, incremental vertical offsets, direct scaling, render visibility cycling, and batch property dialogs.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-PLACE-08 | Create multibound box | `CTRL+B` | Generates a multibound volume around selection | H |
| CK-PLACE-09 | Nudge upward 3 units | `ALT+G` | Increments Z-axis position by +3 units | H |
| CK-PLACE-10 | Scale object interactively | Hold `S` + Move Mouse | Mouse-driven scaling (separate from gizmo key `2`) | H |
| CK-PLACE-11 | Cycle object visibility | `1` | Toggles state: Normal → Transparent → Hidden | H |
| CK-PLACE-12 | Open Batch Edit dialog | `-` | Opens Batch Dialog for multi-selected objects | H |

---

## 4. Render Window Navigation & Viewport Controls (Area: CAM)
Context: 3D Render Window camera navigation, orbit anchoring, viewport panning/zooming, plane constraints, grid snapping, and marker visibility.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-CAM-01 | Orbit camera around target | `SHIFT` + Drag Mouse | Rotates camera view pivoted on current selection | H |
| CK-CAM-02 | Pan viewport camera | `Spacebar` + Drag (or `MMB` Drag) | Translates camera parallel to current view plane | H |
| CK-CAM-03 | Zoom viewport camera | Mouse Scroll Wheel (or `V` + Drag) | Adjusts focal distance / FOV zoom in render window | H |
| CK-CAM-04 | Axis-constrained movement | Hold `Z`, `X`, or `C` + Drag | Restricts translation/rotation strictly to Z, X, or Y axis | H |
| CK-CAM-05 | Deselect current object | `D` | Clears active selection in 3D viewport | H |
| CK-CAM-06 | Toggle Grid Snap | `Q` | Enables/disables snap-to-grid for object transforms | H |
| CK-CAM-07 | Toggle editor markers | `M` | Toggles display of light bulbs, sound markers, and points | H |
| CK-CAM-08 | Toggle light radius outlines | `L` | Toggles visual wireframe sphere for light ranges | H |

---

## 5. Cell Management & Viewport Camera Anchoring (Area: CELL)
Context: Exterior/interior cell forcing, cell reloads, cell boundary overlays, auto-loading adjacent cells, and camera alignment.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-CELL-01 | Force-load selection cell | `CTRL+L` | Centers viewport and forces cell loading | H |
| CK-CELL-02 | Reload active cell | `F5` | Refreshes geometry and unhides hidden objects | H |
| CK-CELL-03 | Toggle cell borders | `B` | Displays cell boundary grid lines | H |
| CK-CELL-04 | Auto-load adjacent cells | `ALT+A` | Dynamically streams exterior cells as camera moves | H |
| CK-CELL-05 | View Scene Graph | `F10` | Opens Scene Graph hierarchy window | H |
| CK-CELL-06 | Center camera on selection | `SHIFT+F` | Anchors viewport focus directly onto selection | H |
| CK-CELL-07 | Cycle camera Ortho/Top view | `T` / Cycle with `V` | Cycles orthographic view (`V` per Steam, `Y` per wiki) | L |

---

## 6. Navmesh Editing & Pathfinding (Area: NAV)
Context: Navmesh toolbar modes, single-cell rendering, room/portal debugging, occlusion links, and path generation.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-NAV-01 | Toggle Navmesh Mode | `CTRL+E` | Enters or exits navmesh editing interface | H |
| CK-NAV-02 | Isolate active cell navmesh | `N` | Restricts navmesh view strictly to current cell | H |
| CK-NAV-03 | Show Room Markers & Portals | `4` | Displays debug geometry for portal rendering | H |
| CK-NAV-04 | Link/Break Occlusion Planes | `ALT+L` | Connects or separates room markers/planes | H |
| CK-NAV-05 | Finalize Navmesh | Navmesh Menu | Finalizes cell navmesh for NPC pathfinding | H |

---

## 7. Render Viewport Toggles (Area: VIEW-1)
Context: Visual debugging modes including physics collisions, wireframe rendering, dynamic shadows, skybox, grass, and depth biasing.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-VIEW-01 | Toggle collision geometry | `F4` | Overlay physics collision meshes in render window | H |
| CK-VIEW-02 | Toggle debug geometry | `4` | Overlays portal and room marker debug visuals | H |
| CK-VIEW-03 | Toggle wireframe mode | `7` | Switches viewport rendering to wireframe display | H |
| CK-VIEW-04 | Toggle dynamic shadows | `5` | Toggles real-time shadow rendering | H |
| CK-VIEW-05 | Toggle skybox rendering | `6` | Enables or disables background skybox rendering | H |
| CK-VIEW-06 | Toggle grass rendering | `8` | Toggles landscape grass rendering | H |
| CK-VIEW-07 | Toggle landscape borders | `B` | Displays terrain land boundary indicators | H |
| CK-VIEW-08 | Enable Depth Biasing | **View → Depth Biasing** | Adjusts z-buffer bias to highlight z-fighting mesh errors | H |

---

## 8. Viewport Lighting Control (Area: VIEW-2)
Context: Default viewport lighting toggles, interactive light radius/intensity adjustment, and shadow depth bias configuration.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-VIEW-09 | Toggle default bright light | `A` | Switches preview lighting to full ambient brightness | H |
| CK-VIEW-10 | Drag light radius & intensity | `CTRL+ALT+S` | Click and drag to interactively adjust light parameters | H |
| CK-VIEW-11 | Adjust shadow depth bias | `ALT+B` | Drag to fine-tune shadow bias on light sources | H |

---

## 9. Transform Gizmos & History Controls (Area: MANIP)
Context: Translation/rotation/scale gizmo selection, rotation resets, grid resnapping, undo/redo history, and pick selection preferences.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-MANIP-01 | Translation Gizmo | `E` | Activates movement transform gizmo handles | H |
| CK-MANIP-02 | Rotation Gizmo | `W` | Activates rotational transform rings | H |
| CK-MANIP-03 | Scale Gizmo | `2` | Activates uniform scale transform gizmo | H |
| CK-MANIP-04 | Hide Transform Gizmos | `R` | Suppresses active transform gizmo display | H |
| CK-MANIP-05 | Reset Rotation | `CTRL+K` | Resets selected object rotation coordinates to (0,0,0) | H |
| CK-MANIP-06 | Snap Selection to Grid | `SHIFT+K` | Snaps current object position to nearest grid coordinate | H |
| CK-MANIP-07 | Undo Action | `CTRL+Z` | Reverts last viewport/form modification | H |
| CK-MANIP-08 | Redo Action | `CTRL+Y` | Reapplies last undone modification | H |
| CK-MANIP-09 | Selection Filter Dialog | `/` | Opens Pick Preferences to filter selectable object types | H |

---

## 10. File Import/Export & Landscape Tools (Area: IO)
Context: FBX geometry export, render buffers, string table export, global string searching, data validation, and landscape heightmap editor.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-IO-01 | Export geometry to FBX | `F2` | Exports 3D selection to external `.fbx` mesh file | H |
| CK-IO-02 | Copy Render | **File → Copy Render** | Copies render transformation buffer | H |
| CK-IO-03 | Paste Render | **File → Paste Render** | Applies copied position/orientation to selection | H |
| CK-IO-04 | Export text data | **File → Import/Export** | Exports tab-delimited text records | H |
| CK-IO-05 | Global Text Search | `CTRL+F` or **File → Find Text** | Searches text string references across plugin forms | H |
| CK-IO-06 | Validate Loaded Data | **File → Validate Loaded Data** | Scans plugin forms for missing links and structural errors | H |
| CK-IO-07 | Open Landscape Editor | `H` | Opens heightmap terrain editing dialog | H |

---

## 11. Papyrus Scripting Tools (Area: PAP)
Context: Script compilation tracking, Papyrus Manager, script property assignment, and runtime log tracing setup.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-PAP-01 | Open Papyrus Manager | **Window → Papyrus Manager** | Lists active Papyrus scripts attached to project forms | U |
| CK-PAP-02 | View Script Compile State | **Window → Papyrus Compile** | Displays compiler log output and status | U |
| CK-PAP-03 | Enable Papyrus Log Tracing | `Fallout4Custom.ini` edit | Under `[Papyrus]`, set `bEnableTrace=1` (Game INI setting) | U |

---

## 12. File Menu Utility Commands (Area: FILE)
Context: File menu actions including plugin publishing, FormID compaction, light master (ESL) conversion, version control, and preferences.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-FILE-01 | Save & Push Plugin | **File → Save and Push Plugin to PC** | Writes plugin directly to configured path | H |
| CK-FILE-02 | Compact Form IDs | **File → Compact Active File Form IDs** | Renumbers FormIDs for ESL conversion (invalidates saves) | H |
| CK-FILE-03 | Convert to Light Master | **File → Convert Active File to Light Master** | Sets ESL flag on plugin (requires compact FormIDs) | H |
| CK-FILE-04 | Version Control Dialog | **File → Version Control** | Accesses built-in version control integration | H |
| CK-FILE-05 | Open Preferences | **File → Preferences** | Configures Creation Kit default editor settings | H |

---

## 13. System Limitations & Unsupported Features (Area: NO)
Context: Documented Creation Kit missing features, non-existent interfaces, and unconfirmed functions per source documentation.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-NO-01 | Key Remapping | Not Available | Hotkeys are hardcoded; no native keybinding configuration | H |
| CK-NO-02 | Save As / Save Copy | Not Available | No "Save As" menu option exists; saving is in-place only | H |
| CK-NO-03 | Automated/Headless Execution | Not Available | No native CLI or headless automation interface present | L |
| CK-NO-04 | Warning Log Auto-Save | Unknown | Capability to dump Warnings window directly to file is untested | L |
| CK-NO-05 | Batch Dialog Round-Tripping | Unknown | Untested capability to import full dialog record packages | L |

---

## 14. Workspace Verification & Repository Context (Area: LOCAL)
Context: Tested machine environment details, script compilation verification, plugin generation, and modding tool interactions.

| ID | Task / Feature | Input / Control | Context & Details | Conf |
|---|---|---|---|---|
| CK-LOCAL-01 | Version Parity Check | `CreationKit.exe` 1.11.240.0 | Verified exact build match with `Fallout4.exe` 1.11.240.0 | V |
| CK-LOCAL-02 | Script Compiler Check | Local Compile | Successfully compiled `PipMon.psc` & facility test scripts | V |
| CK-LOCAL-03 | Create New Light Plugin | **File → Create** | Target output to designated mod path (not game Data) | P |
| CK-LOCAL-04 | Import Compiled `.pex` | **Scripts → Import...** | Direct import of binary scripts without recompilation | P |
| CK-LOCAL-05 | Assign Script Properties | **Properties → Script** | Link script properties via editor UI rather than hardcoding | P |
| CK-LOCAL-06 | Engine Crash Fix Fixup | CKPE (Nexus 51165) | Extended memory patch verified up to CK build 1.11.137.0 | P |
| CK-LOCAL-07 | Plugin Order File Lock | `plugins.txt` sync | Read at startup; external managers (Vortex) can overwrite | V |
| CK-LOCAL-08 | Automated Key Sequence Drive | None | Keystroke simulation conflicts with active foreground user | V |

---

## 15. Source Discrepancies & Hotkey Conflicts
Context: Explicit tracking of conflicting inputs between the Fallout 4 Creation Kit Wiki and Steam Community Guides.

| Topic / Feature | Source Conflict Summary | Associated Entry IDs |
|---|---|---|
| Camera View Cycle Key | `V` per Steam Guide vs `Y` per Creation Kit Wiki (`C` in older TES tools). | CK-CELL-07 |
| Key `4` Visual Overlay | Assigned to Debug Geometry toggle as well as Navmesh Room Markers/Portals toggle. | CK-VIEW-02, CK-NAV-03 |
| Key `B` Boundary Overlay | Assigned to Cell Boundary Grid toggle and Landscape/Land Border toggle. | CK-CELL-03, CK-VIEW-07 |
| Paste Key Function | Listed in source as "`CTRL+V` / `CTRL+SHIFT+V` paste in place". Resolved as Standard Paste (`CTRL+V`) vs Paste in Place (`CTRL+SHIFT+V`). | CK-PLACE-06, CK-PLACE-07 |

---

## 16. Reverse Lookup Index A: Single Key Bindings
Context: Mapping from individual keyboard keys to editor actions and entry IDs.

| Key | Associated Task / Command | Entry ID |
|---|---|---|
| `1` | Cycle visibility (Normal / Transparent / Hidden) | CK-PLACE-11 |
| `2` | Scale Gizmo | CK-MANIP-03 |
| `4` | Show Room Markers and Portals / Toggle Debug Geometry | CK-NAV-03, CK-VIEW-02 |
| `5` | Toggle dynamic shadows | CK-VIEW-04 |
| `6` | Toggle skybox rendering | CK-VIEW-05 |
| `7` | Toggle wireframe display | CK-VIEW-03 |
| `8` | Toggle landscape grass rendering | CK-VIEW-06 |
| `-` | Multi-select Batch Edit dialog | CK-PLACE-12 |
| `/` | Pick preferences selection filter | CK-MANIP-09 |
| `A` | Toggle default viewport bright light | CK-VIEW-09 |
| `B` | Toggle cell borders / land borders | CK-CELL-03, CK-VIEW-07 |
| `C` | Constrain movement to Y-axis | CK-CAM-04 |
| `D` | Deselect current object selection | CK-CAM-05 |
| `DELETE` | Delete selected object reference | CK-PLACE-04 |
| `E` | Translation Gizmo handles | CK-MANIP-01 |
| `F` | Drop selected object to floor collision | CK-PLACE-05 |
| `F2` | Export selected geometry to FBX file | CK-IO-01 |
| `F4` | Toggle collision mesh visual overlay | CK-VIEW-01 |
| `F5` | Reload active cell geometry | CK-CELL-02 |
| `F10` | Show Scene Graph hierarchy window | CK-CELL-05 |
| `H` | Open Landscape Heightmap Editor | CK-IO-07 |
| `L` | Toggle light radius outlines | CK-CAM-08 |
| `M` | Toggle editor markers (lights/sounds) | CK-CAM-07 |
| `N` | Isolate single cell navmesh rendering | CK-NAV-02 |
| `Q` | Toggle Grid Snap | CK-CAM-06 |
| `R` | Hide transform gizmos | CK-MANIP-04 |
| `S` | Interactive scale adjustment (Hold `S` + Move Mouse) | CK-PLACE-10 |
| `T` | Camera top / front / orthographic view | CK-CELL-07 |
| `V` | Cycle camera view / Zoom modifier | CK-CELL-07, CK-CAM-03 |
| `W` | Rotation Gizmo rings | CK-MANIP-02 |
| `X` | Constrain movement to X-axis | CK-CAM-04 |
| `Y` | Cycle camera view (Wiki disputed) | CK-CELL-07 |
| `Z` | Constrain movement to Z-axis | CK-CAM-04 |

---

## 17. Reverse Lookup Index B: Combination Keys & Mouse Actions
Context: Reverse lookup mapping for modifier keys (`CTRL`, `SHIFT`, `ALT`) and combined mouse operations.

| Input Combination | Associated Task / Command | Entry ID |
|---|---|---|
| `ALT+A` | Toggle auto-loading exterior cells | CK-CELL-04 |
| `ALT+B` | Adjust light shadow depth bias | CK-VIEW-11 |
| `ALT+G` | Nudge selection upward by +3 units | CK-PLACE-09 |
| `ALT+L` | Link or break Occlusion Planes / Room Markers | CK-NAV-04 |
| `CTRL+ALT+S` | Click and drag light radius and intensity | CK-VIEW-10 |
| `CTRL+B` | Generate multibound box volume | CK-PLACE-08 |
| `CTRL+D` | Duplicate selected object (new FormID) | CK-PLACE-02 |
| `CTRL+E` | Enter or exit Navmesh editing mode | CK-NAV-01 |
| `CTRL+F` | Global text search across plugin forms | CK-IO-05 |
| `CTRL+K` | Reset selection rotation to (0,0,0) | CK-MANIP-05 |
| `CTRL+L` | Force-load selected object's cell | CK-CELL-01 |
| `CTRL+M` | Move object reference (preserve FormID) | CK-PLACE-03 |
| `CTRL+S` | Save active plugin file in-place | CK-START-03 |
| `CTRL+SHIFT+V` | Paste in Place (maintain source coordinates) | CK-PLACE-07 |
| `CTRL+V` | Standard Paste object reference | CK-PLACE-06 |
| `CTRL+Y` | Redo last undone action | CK-MANIP-08 |
| `CTRL+Z` | Undo last modification | CK-MANIP-07 |
| `Mouse Scroll Wheel` / `V` + Drag | Zoom viewport camera in/out | CK-CAM-03 |
| `SHIFT` + Mouse Drag | Orbit camera around selected object | CK-CAM-01 |
| `SHIFT+F` | Anchor/focus camera viewport on selection | CK-CELL-06 |
| `SHIFT+K` | Resnap selected object to grid | CK-MANIP-06 |
| `SHIFT+O` | Open Object Palette dialog | CK-PLACE-01 |
| `Spacebar` + Drag / `MMB` Drag | Pan render window camera | CK-CAM-02 |

---

## 18. Reverse Lookup Index C: Menu Paths & Config Files
Context: Reverse lookup table mapping software menu paths and external configuration file locations to entry IDs.

| Menu / Configuration Path | Associated Task / Command | Entry ID |
|---|---|---|
| **File → Compact Active File Form IDs** | Compact active file FormIDs for light master conversion | CK-FILE-02 |
| **File → Convert Active File to Light Master** | Convert active plugin to Light Master (ESL) | CK-FILE-03 |
| **File → Copy Render** | Copy render transformation buffer | CK-IO-02 |
| **File → Create** | Create new plugin file | CK-LOCAL-03 |
| **File → Data...** | Open data file selection window | CK-START-01 |
| **File → Find Text** | Search text strings in plugin forms | CK-IO-05 |
| **File → Import/Export** | Export tab-delimited text records | CK-IO-04 |
| **File → Paste Render** | Paste copied render transformations | CK-IO-03 |
| **File → Preferences** | Open Creation Kit preferences dialog | CK-FILE-05 |
| **File → Save and Push Plugin to PC** | Save plugin directly to target computer path | CK-FILE-01 |
| **File → Validate Loaded Data** | Validate structural data integrity of loaded forms | CK-IO-06 |
| **File → Version Control** | Open Version Control management dialog | CK-FILE-04 |
| **Properties → Script** | Assign script properties on form reference | CK-LOCAL-05 |
| **Scripts → Import...** | Import compiled `.pex` script file | CK-LOCAL-04 |
| **View → Depth Biasing** | Enable Z-buffer bias rendering for Z-fighting debug | CK-VIEW-08 |
| **View → Render Window Hotkeys** | Display Creation Kit internal hotkey cheat sheet | CK-START-05 |
| **Window → Papyrus Compile** | Display script compilation log and status | CK-PAP-02 |
| **Window → Papyrus Manager** | Open Papyrus Script Manager window | CK-PAP-01 |
| `Documents\My Games\Fallout4\Fallout4Custom.ini` | Enable Papyrus runtime trace logging (`bEnableTrace=1`) | CK-PAP-03 |

---

## 19. Retrieval Evaluation Benchmarks (RAG Test Queries)
Context: Synthetic query validation set for testing retrieval pipeline chunk alignment and embedding recall accuracy.

| Sample Query | Expected Target IDs |
|---|---|
| How do I duplicate an object in the Creation Kit? | CK-PLACE-02 |
| Move versus duplicate: which keeps the FormID? | CK-PLACE-03, CK-PLACE-02 |
| What does F5 do in the Creation Kit? | CK-CELL-02 |
| What is the hotkey for navmesh mode? | CK-NAV-01 |
| Why will my plugin not load in the CK? | CK-START-02 |
| Can I remap Creation Kit hotkeys? | CK-NO-01 |
| Is there Save As in the Creation Kit? | CK-NO-02 |
| Which key cycles the camera views? | CK-CELL-07 |
| How do I orbit or rotate the camera around an object? | CK-CAM-01 |
| How do I restrict movement to the Z axis? | CK-CAM-04 |
| How do I turn on grid snapping? | CK-CAM-06 |
| How do I hide or show light markers? | CK-CAM-07, CK-CAM-08 |
| How do I deselect an object in the Render Window? | CK-CAM-05 |
| How to export the active selection to FBX? | CK-IO-01 |
| How do I turn on the Papyrus trace log? | CK-PAP-03 |
| Can the Creation Kit be automated or run headless? | CK-NO-03, CK-LOCAL-08 |
| Which CK version is installed and does it match the game executable? | CK-LOCAL-01 |
| How do I import a compiled .pex into the CK? | CK-LOCAL-04 |
| What key toggles wireframe rendering mode? | CK-VIEW-03 |
| What key combination performs a Redo? | CK-MANIP-08 |

---

## 20. Source Data Confidence Matrix
Context: Summary assessment of source reliability across Creation Kit functional domains.

| Domain Area | Confidence Assessment |
|---|---|
| File Menu, Dialog Windows, & Transform Hotkeys | **High:** Wiki and Steam guide sources fully agree. |
| Navmesh Mode Hotkeys & Finalization Workflow | **High:** Official wiki documented. |
| View Navigation & Axis Constraints | **High:** Verified standard Bethesda editor defaults. |
| Key Remapping Capability | **High:** Explicitly documented as unsupported. |
| Camera View Cycle Hotkey | **Low:** Sourced conflict (`V` vs `Y` vs `C`). |
| Automated / Headless Control Interface | **None:** Interface non-existent; open question. |
| Warnings Window Output File Logging | **Unknown:** Untested on target executable. |
| Round-trip Record Import/Export | **Unknown:** Untested across complex form types. |