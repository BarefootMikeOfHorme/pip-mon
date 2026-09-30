---
source_url: (authored record of this retrieval session)
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: index-authored
trust: "Authored by me. Factual log of attempted URLs with verbatim error strings. No URL was guessed: every source path was returned by the GitHub API recursive tree listing for the repository, or was a search result URL."
provenance: "PowerShell Invoke-WebRequest, GitHub REST API recursive tree listing, and websearch."
---

# Fetch log — ckpe

## Target reached

`https://github.com/Perchik71/Creation-Kit-Platform-Extended` — **OK.** This is
the one requested target of the three that exists as given.

Repository enumerated via `https://api.github.com/repos/Perchik71/Creation-Kit-Platform-Extended/git/trees/master?recursive=1`
(4352 entries, `truncated: false`), then the Fallout 4 render/stability sources
were selected from that listing and fetched individually.

## URLs attempted — failures (exact errors)

| URL | Exact error | Note |
|---|---|---|
| `https://raw.githubusercontent.com/Perchik71/Creation-Kit-Platform-Extended/master/README-RU.md` | `Response status code does not indicate success: 404 (Not Found)` | No Russian README at that path. The language block in the English README points at an OpenAiTx translation mirror, not an in-repo file. |
| `https://raw.githubusercontent.com/Perchik71/Creation-Kit-Platform-Extended/master/CKPE.Fallout4/Include/EditorAPI/ScrapHeap.h` | `Response status code does not indicate success: 404 (Not Found)` | **My path was wrong**, not the file. The API tree shows it at `CKPE.Fallout4/Include/EditorAPI/S/ScrapHeap.h`. Re-fetched successfully at the correct path. Recorded because the failed URL is a real, instructive error: guessing a path instead of reading the tree listing is what produced it. |

## URLs attempted — successes

All = `https://raw.githubusercontent.com/Perchik71/Creation-Kit-Platform-Extended/master`

| Path | Bytes | Local file |
|---|---|---|
| `README.md` | 7371 | `verbatim/CKPE-README.md` |
| `LICENSE` | 7632 | `verbatim/CKPE-LICENSE` |
| `CKPE.Fallout4/Src/Patches/CKPE.Fallout4.Patch.RenderWindow.cpp` | 16496 | `verbatim/FO4-Patch-RenderWindow.cpp` |
| `CKPE.Fallout4/Include/EditorAPI/BGSRenderWindow.h` | 7387 | `verbatim/FO4-EditorAPI-BGSRenderWindow.h` |
| `CKPE.Fallout4/Include/EditorAPI/ScrapHeap.h` → actual `.../EditorAPI/S/ScrapHeap.h` | 3312 | `verbatim/FO4-EditorAPI-ScrapHeap.h` |
| `CKPE.Fallout4/Include/EditorAPI/I/IMemoryHeap.h` | 1784 | `verbatim/FO4-EditorAPI-IMemoryHeap.h` |
| `CKPE.Fallout4/Src/Patches/CKPE.Fallout4.Patch.CellViewWindow.cpp` | 15518 | `verbatim/FO4-Patch-CellViewWindow.cpp` |
| `CKPE.Fallout4/Include/Patches/CKPE.Fallout4.Patch.CellViewWindow.h` | 2760 | `verbatim/FO4-Patch-CellViewWindow.h` |
| `CKPE.Fallout4/Src/Patches/CKPE.Fallout4.Patch.MemoryManager.cpp` | 8601 | `verbatim/FO4-Patch-MemoryManager.cpp` |
| `CKPE.Fallout4/Include/Patches/CKPE.Fallout4.Patch.MemoryManager.h` | 1011 | `verbatim/FO4-Patch-MemoryManager.h` |
| `CKPE.Fallout4/Src/Patches/CKPE.Fallout4.Patch.RenderWindow60FPS.cpp` | 2224 | `verbatim/FO4-Patch-RenderWindow60FPS.cpp` |
| `CKPE.Fallout4/Include/Patches/CKPE.Fallout4.Patch.RenderWindow.h` | 1936 | `verbatim/FO4-Patch-RenderWindow.h` |
| `CKPE.Fallout4/Src/Patches/CKPE.Fallout4.Patch.CrashDump.cpp` | 7608 | `verbatim/FO4-Patch-CrashDump.cpp` |
| `CKPE.Fallout4/Include/Patches/CKPE.Fallout4.Patch.MainWindow.h` | 3262 | `verbatim/FO4-Patch-MainWindow.h` |
| `CKPE.Common/Include/CKPE.Common.MemoryManager.h` | 1504 | `verbatim/Common-MemoryManager.h` |

## Selected from the tree listing but NOT fetched

- `CKPE.SkyrimSE/*` and `CKPE.Starfield/*` mirrors of the same patches — same
  technique, different game. FO4-only was sufficient for our purpose and kept
  the capture focused.
- `Database/FO4/CKPERelbs/*/*.relb` — CKPE's per-version relocation database.
  **Deliberately skipped**: we are not adopting CKPE, so its internal binary
  format is not ours to consume. Its existence is noted in `ckpe-insights.md`
  as undocumented-by-us and not pursued.
- `CKPE.Common/Src/CKPE.Common.CrashHandler.cpp` (46069 bytes) and the other
  Skyrim/Starfield render-window sources — the FO4 set already covered the
  technique families.
- `Stuffs/FO4/CreationKitPlatformExtended_FO4_Resources.pak` — the README states
  this contains **proprietary, unlicensed** files. Not fetched, and flagged
  deliberately.

## Scope discipline

Nothing in this directory constitutes an adoption. CKPE is **not** a dependency,
**not** vendored, **not** linked, and **not** something we expect end users to
install. This directory exists so a later session can read *how a third party
solved CK render-window and stability problems* before we build our own
replacement. See the RELATIONSHIP section at the top of `ckpe-insights.md`.
