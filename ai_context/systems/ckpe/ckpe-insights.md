---
source_url: https://github.com/Perchik71/Creation-Kit-Platform-Extended
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: index-authored
trust: "Authored by me from verbatim upstream C++ in ./verbatim/. These are TECHNIQUES observed in source, not claims from CKPE's marketing; where CKPE's own README states something I did not verify in code, I say so. I did not build, run, or benchmark any of this. Portability judgements are my opinion about what would transfer to an in-house C++ replacement, not measurements."
provenance: "CKPE README, LICENSE, and 13 Fallout-4-targeted source files (render window, cell view window, memory manager, crash dump, plus reverse-engineered EditorAPI headers). Repo master branch, LGPLv3."
---

# CKPE: techniques for render-window and CK stability — IDEAS ONLY

## RELATIONSHIP TO OUR PROJECT — READ FIRST, THIS IS THE MOST IMPORTANT PART

**We are not including CKPE. We are not depending on it. We are not vendoring it,
linking it, shipping it, or asking users to install it.** Nothing in this
directory is an adopted dependency. It is a captured set of *ideas* from a
third-party project that solved some of the same problems we have.

Our actual situation, for context: **our Creation Kit crashes on larger cells,
and we have no CKPE.** We intend an in-house replacement. So the only question
that matters is: *did CKPE solve this, and is their solution reusable by us?*

Two consequences for a later session:

1. **Never cite CKPE as a dependency, a vendored library, or an available
   runtime.** If a future design says "use CKPE", that is a design error — the
   whole point is an in-house replacement.
2. **The licence matters if we ever copy.** CKPE is LGPLv3 from v0.6, GPLv3
   before. Techniques are generally not copyrightable, but *code* is. The table
   below deliberately describes techniques in my own words so the ideas are
   cleanly separable from the implementation. If we ever need to copy actual
   code, that is a licence decision, not a technical one.

The one cross-reference worth noting: CKPE's own main window declares
`SupportsAddressLibrary() const { return true; }` — **CKPE itself consumes an
address library**, which is a nice independent confirmation that the address
mapping scheme in `../engine/address_mapping/` is a real, load-bearing pattern
rather than an obscure one.

## prose (human-readable)

Reading the Fallout 4 patches, CKPE's approach falls into four families. What is
notable is how much of the value is in the *small, boring* fixes rather than
anything architectural.

**Family 1 — Render window.** CKPE chains the render window's window procedure,
installs its own `WNDPROC` via a jump patch, saves the original, and forwards
everything it does not care about through `CallWindowProc`. Everything
overlay-related is drawn by intercepting the DirectX 11 swap chain's `Present`
method and drawing immediately before it. Two details stand out as genuinely
valuable rather than cosmetic. First, CKPE caches the render window's draw
dimensions on `WM_ACTIVATE` when the window deactivates and restores them on
reactivation, with the comment *"Fix bug loss of window size"* — that is a real
Bethesda bug where the render window loses its dimensions across focus changes,
and the fix is a save/restore of a global size struct around activation. Second,
it returns `S_FALSE` from `WM_ERASEBKGND`, which is the standard Windows way to
suppress background erase and stop flicker, and it clamps the minimum track size
to 96x96 in `WM_GETMINMAXINFO` with the comment *"96 min tex size"* — a
documented constraint that the render window cannot usefully go below the
minimum texture dimension.

The overlay drawing is more involved and is the part I would *not* copy. To draw
an ImGui overlay it reaches into two hardcoded global addresses
(`gGlobAddrDeviceContext + 0x88` and `+ 0xA8`, the latter commented *"Used by
gizmo enabled"`) holding render target view pointers, calls `OMGetRenderTargets`,
compares the bound target against both, temporarily rebinds a target, draws, then
restores. That is a two-render-target dance specific to how CK sets up gizmo
rendering, and it depends on undocumented globals at version-specific offsets.

**Family 2 — Cell view window.** This is the one most relevant to our crash, and
it is a filter, not a fix. CKPE interposes on the functions that insert rows into
the Cell View list control, and before each insert fires a notification carrying
a mutable `allowInsert` flag. A handler that sets it false causes CKPE to return
early without ever calling the original insert. The upstream comment is
*"Allow objects to be filtered in CellViewProc"*. So the technique is: **make the
list view refuse to materialise rows**, thereby bounding the size of the thing
that is failing.

That is a *virtualisation-by-omission* pattern, and it is worth being precise
about what it does and does not do. It makes the **Cell View window** cheap. It
does **not** make the **3D render window** cheaper, and it does not reduce CK's
own memory use — it only reduces what the list control is asked to hold. If our
crash is in the cell view list, this is a direct hit. If our crash is in
rendering or in the cell data itself, it is not. I could not determine which of
these our failure is, so this is a candidate, not a diagnosis.

Note also that CKPE needed *two* variants of this hook (`sub2` and `sub2_ver2`)
selected per editor version, because the calling convention and argument list
changed between CK 1.10.162 and later builds. Any in-house replacement inherits
that per-version maintenance burden.

**Family 3 — Memory and stability.** This is the strongest family and the most
directly portable. CKPE replaces Bethesda's allocators wholesale: it jumps
`BSMemoryManager::Allocate/Deallocate/Size`, `BSScrapHeap::Allocate/Deallocate`,
`NiBSScrapAdapter_AllocateFromBSScrap`, and the `bhkThreadMemorySource`
constructor, routing all of them into one custom allocator singleton. It also
**IAT-detours the CRT allocators** in `API-MS-WIN-CRT-HEAP-L1-1-0.DLL` and
`MSVCR110.DLL` — `malloc`, `calloc`, `realloc`, `_recalloc`, `free`, `_msize`,
`_strdup`, `memcpy_s`, `memmove_s`, `memcmp`, `memcpy`, `memmove`, `memset` — so
that even CRT-internal allocations land in that same allocator. The point is
consistency: if half of CK's allocations come from the CRT heap and half from
Bethesda's scrap heap, no allocator-level defence can work.

Two individual items here are the highest-value-per-line in the whole capture:

- **`DisableProcessWindowsGhosting()`** — called with the comment *"The program
  really likes to think, and Windows doesn't like it, let's tell Windows not to
  pay attention."* This tells Windows to stop detecting the app as hung and
  offering to kill it. For a long-running heavy editor operation, this is a
  one-line, version-independent, zero-risk mitigation. It should be the first
  thing an in-house replacement does.
- **An explicit low-memory precondition.** CKPE queries physical and shared
  memory, logs both, and then hard-asserts if free memory is not above a 2 GB
  threshold — producing a clear *"Not enough memory to run the program"* message
  instead of letting CK die obscurely. Converting an unreadable crash into a
  legible refusal is worth doing even before we know the root cause.

**Family 4 — Making crashes survivable and diagnosable.** CKPE installs its own
crash handler, then **IAT-detours every CRT termination routine** — `exit`,
`_exit`, `_Exit`, `_c_exit`, `_cexit`, `abort`, `terminate` — redirecting them
into its handler, and separately detours `_purecall` into a handler that raises
a custom `'PURE'` exception. This means that when the CRT decides to tear down
(because CK hit an internal `abort`/`terminate`), execution passes through CKPE
first, giving it a chance to report properly instead of the process vanishing.
It also turns pure-virtual-call crashes, which are otherwise near-impossible to
diagnose, into a recognisable event. The technique is portable in spirit; the
specific exception-code-as-magic-number convention is theirs.

## Techniques table

`portable` = would this transfer to an in-house C++ replacement that does *not*
use CKPE's hooking framework? `yes` / `no` / `maybe`.

| # | Technique | Evidence (file in `./verbatim/`) | portable | Reason |
|---|---|---|---|---|
| 1 | `DisableProcessWindowsGhosting()` so Windows never offers to kill a long CK operation | `FO4-Patch-MemoryManager.cpp` | **yes** | A single Win32 call, no hooking, no version dependency, no engine knowledge. Pure win. |
| 2 | Query physical + shared memory and refuse early with a legible message below a threshold | `FO4-Patch-MemoryManager.cpp` (`MEM_THRESHOLD = 2`) | **yes** | Turns an opaque crash into a clear diagnostic using public `GlobalMemoryStatusEx`-style APIs. We should adopt this regardless of root cause. |
| 3 | Route *all* Bethesda + CRT allocation through one custom allocator (jump hooks + IAT detours) | `FO4-Patch-MemoryManager.cpp` | **maybe** | The idea is sound and version-robust in spirit, but landing it needs the relocation IDs for `BSMemoryManager`/`BSScrapHeap`/`bhkThreadMemorySource` per CK build. We inherit CKPE's per-version maintenance cost. |
| 4 | IAT-detour CRT allocators specifically (`API-MS-WIN-CRT-HEAP-L1-1-0.DLL`, `MSVCR110.DLL`) | `FO4-Patch-MemoryManager.cpp` | **yes** | Technique is standard and module-name-driven. Must confirm which CRT CK actually imports on our machine. |
| 5 | Save/restore the render window's draw dimensions across `WM_ACTIVATE` (upstream comment: *"Fix bug loss of window size"*) | `FO4-Patch-RenderWindow.cpp` (`HKWndProc`, `WM_ACTIVATE`, `rcSafeDrawArea`) | **yes** | Pure Win32 message handling on a cached struct. No engine internals, no offsets. Directly fixes a real Bethesda bug. |
| 6 | Return `S_FALSE` from `WM_ERASEBKGND` to stop background-erase flicker | `FO4-Patch-RenderWindow.cpp` | **yes** | Textbook Win32, engine-agnostic. |
| 7 | Clamp minimum track size via `WM_GETMINMAXINFO` (96 = minimum texture size) | `FO4-Patch-RenderWindow.cpp` | **yes** | Textbook Win32. The 96 figure is a CK-specific constraint worth re-verifying, not a magic constant to copy blindly. |
| 8 | `SetWindowPos(..., SWP_FRAMECHANGED)` on `WM_INITDIALOG` to force a frame recalculation | `FO4-Patch-RenderWindow.cpp` | **yes** | Standard Win32 idiom. |
| 9 | Expand/shrink a code region by NOP-filling it, then write a `CALL` to a trampoline (inline hook with size adjustment) | `FO4-Patch-RenderWindow.cpp` (`WriteFill(NOP, 0x4B/0x44)` then `WriteCall`) | **maybe** | The technique is a normal detouring primitive. The *lengths* (0x4B vs 0x44) are per-CK-version and must be re-derived; the branch is on editor version. |
| 10 | Intercept the swap chain's `Present` to draw an overlay immediately before presentation | `FO4-Patch-RenderWindow.cpp` (`DrawFrameEx`) | **maybe** | Conceptually universal for a DX11 host, but binding to CK's swap chain requires its vtable layout or a hook on its creation call. |
| 11 | Capture render stats by interposing on the engine's `"%u main draw calls, %u polys, %s textures, %u FPS"` printf-style format function | `FO4-Patch-RenderWindow.cpp` (`UpdateDrawInfo`) | **maybe** | Clever and portable in idea — the stats are already formatted, so hooking the formatter is cheaper than recomputing. Needs the format string located per version. |
| 12 | Two-render-target save/restore dance to draw overlays around the gizmo target | `FO4-Patch-RenderWindow.cpp` (`+ 0x88` / `+ 0xA8`) | **no** | Depends on undocumented globals at hardcoded offsets and CK's gizmo-specific target layout. Version-fragile and deeply coupled. |
| 13 | **Filter the Cell View list by vetoing row inserts** (upstream: *"Allow objects to be filtered in CellViewProc"*) | `FO4-Patch-CellViewWindow.cpp` (`sub1`/`sub2`/`sub2_ver2`, `allowInsert`) | **maybe** | The technique is the most promising lead for our large-cell crash, but it only bounds the *list control*, not the render window or CK's memory. Also needed two hook variants for two CK versions. |
| 14 | Interpose on list-control row insertion generally, to virtualise expensive lists | `FO4-Patch-CellViewWindow.cpp` | **yes** | The pattern — veto at the insertion point, never materialise the row — is standard UI virtualisation and is not CKPE-specific. |
| 15 | IAT-detour every CRT termination routine (`exit`/`_exit`/`_Exit`/`_c_exit`/`_cexit`/`abort`/`terminate`) into one handler | `FO4-Patch-CrashDump.cpp` | **yes** | Standard technique, entirely under our control, no engine knowledge. Makes internal aborts observable instead of silent. |
| 16 | Detour `_purecall` and raise a recognisable custom exception code (`'PURE'`) | `FO4-Patch-CrashDump.cpp` | **yes** | Pure-virtual crashes are otherwise undiagnosable; catching them is a genuine improvement. The magic-code convention is CKPE's, but the idea is free. |
| 17 | Install a crash handler before any patching takes effect | `FO4-Patch-CrashDump.cpp` (`CrashHandler::Install()`) | **yes** | Ordering discipline, trivially portable and obviously correct. |
| 18 | Use a relocation database keyed by per-version numeric IDs rather than raw offsets | `FO4-Patch-*.cpp` (`Relocation(ID{...})`) | **no** | This *is* CKPE's own infrastructure. It is also the same concept as our address library (`../engine/address_mapping/`) — we should build our own, not adopt theirs. |
| 19 | ImGui overlay for stats/inspection, drawn in the Present hook | `FO4-Patch-RenderWindow.cpp` | **no** | Requires their ImGui + DX11 backend integration and their docking manager. A UI decision, not a technique. |
| 20 | Registry/INI-driven patch toggles so each fix is individually disableable | `FO4-Patch-RenderWindow.cpp` (`_READ_OPTION_BOOL`, `_READ_OPTION_FLOAT`) | **yes** | Good operational practice for an in-house tool: it makes bisecting a crash possible. |

## What I could not determine

| Question | Status |
|---|---|
| Which specific CK crash our large cells hit (cell view list vs render window vs allocator) | **unknown — needs our own reproduction.** Technique 13 only helps in one of three cases. |
| Whether any CKPE technique *fixes* large-cell crashes specifically, as opposed to improving general robustness | **not found in sources.** CKPE's per-patch names describe symptoms (`CrashInventory`, `CrashMergeForms`, `CrashTestRadius`, `CrashMHDTMoreThan70`); there is no `CrashLargeCell` patch, and **absence of such a patch is not evidence the problem is unsolvable.** |
| The `.relb` relocation database format | **not documented in the captured files.** The `Database/FO4/CKPERelbs/*/` files exist in the repo but are CKPE's internal binary format, and we are not adopting CKPE anyway. |
| Whether techniques 3/9/13 still work on our CK build | **unknown and version-specific.** Each is gated on an editor-version comparison inside CKPE's own code. |
