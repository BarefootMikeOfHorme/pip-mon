---
source_url: (authored record of this retrieval session)
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: index-authored
trust: "Authored by me. Factual log of attempted URLs with verbatim error strings. No URL was guessed: every path was either returned by the GitHub API tree listing, or a search result URL."
provenance: "PowerShell Invoke-WebRequest, GitHub REST API, and websearch used to locate candidates."
---

# Fetch log — ba2_format

## No dedicated BA2 specification was reachable

The brief suggested the Skyrim Mod File Format pages on en.uesp.net and
"BA2Format documentation" as candidates. **en.uesp.net has no BA2 page at
all** — it documents BSA, not BA2. Four URLs were probed and all failed. The
Nexus wiki page cited as the primary spec by the richest source I did find is
dead.

## Archive2: not obtained

The brief asked for "the Archive2 project if reachable, for its command-line
approach and any format notes it carries."

**Archive2 is proprietary.** It ships only inside the Fallout 4 Creation Kit
(Bethesda's own tool, `Archive2.exe`). websearch for it returned no public
source repository — only third-party guides and unrelated Bethesda-adjacent
tools. Its CLI surface and any format notes it carries are therefore
**unavailable**, and I have recorded that as a gap rather than reconstructing a
command-line interface from memory. This is consistent with the project's
position that Archive2 is not coming back; only its *format* was needed, and the
format was obtained independently.

This is also consistent with the brief's own note that BA2-capable tooling is
already on this machine (`BSArch.exe`, `BSArch64.exe`, `BSArchPro.exe`,
`BSArchPro64.exe` from xEdit), so no tooling gap remains.

## URLs attempted — failures (exact errors)

| URL | Exact error |
|---|---|
| `https://github.com/libxse/addresslib` | `StatusCode: non 2xx status code (404 GET https://github.com/libxse/addresslib)` |
| `https://raw.githubusercontent.com/matortheeternal/bae/master/README.md` | `Response status code does not indicate success: 404 (Not Found)` |
| `https://en.uesp.net/wiki/Fallout_4_Mod:Mod_File_Format` | `Response status code does not indicate success: 404 (Not Found)` |
| `https://en.uesp.net/wiki/Skyrim_Mod:BA2_File_Format` | `Response status code does not indicate success: 404 (Not Found)` |
| `https://en.uesp.net/wiki/Category:BA2` | `Response status code does not indicate success: 404 (Not Found)` |
| `https://ck.uesp.net/wiki/Category:BA2` | `Response status code does not indicate success: 403 (Forbidden)` |
| `https://wiki.nexusmods.com/index.php/BA2_File_Format` | `Response status code does not indicate success: 403 (Forbidden)` — **this is the spec cited by `FasterFileCopy-BA2MemoryMap.h` itself** |

## URLs attempted — successes

| URL | Bytes | Local file |
|---|---|---|
| `https://raw.githubusercontent.com/1001Bits/Faster-File-Copy/main/Fallout4/src/BA2MemoryMap.h` | 6151 | `verbatim/FasterFileCopy-BA2MemoryMap.h` |
| `https://raw.githubusercontent.com/matiaszanolli/ByroRedux/main/docs/engine/archives.md` | 24948 | `verbatim/ByroRedux-archives.md` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/README.md` | 1667 | `verbatim/ba2tools-README.md` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2Tools/BA2Header.cs` | 638 | `verbatim/ba2tools-BA2Header.cs` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2Tools/BA2Type.cs` | 325 | `verbatim/ba2tools-BA2Type.cs` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2Tools/Internal/BA2GeneralFileEntry.cs` | 1717 | `verbatim/ba2tools-BA2GeneralFileEntry.cs` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2Tools/Internal/BA2TextureFileEntry.cs` | 1962 | `verbatim/ba2tools-BA2TextureFileEntry.cs` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2Tools/Internal/TextureChunk.cs` | 825 | `verbatim/ba2tools-TextureChunk.cs` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2ToolsTests/Data/README.md` | 430 | `verbatim/ba2tools-TestsData-README.md` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2ToolsTests/Data/GeneralHeaderOnly.ba2` | 24 | `fixtures/GeneralHeaderOnly.ba2` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2ToolsTests/Data/GeneralHeaderOnlyInvalidVersion.ba2` | 24 | `fixtures/GeneralHeaderOnlyInvalidVersion.ba2` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2ToolsTests/Data/GeneralOneFile.ba2` | 79 | `fixtures/GeneralOneFile.ba2` |
| `https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2ToolsTests/Data/GeneralTwoFiles.ba2` | 143 | `fixtures/GeneralTwoFiles.ba2` |
| `https://raw.githubusercontent.com/matortheeternal/bae/master/src/archive.h` | 1398 | `verbatim/bae-archive.h` |
| `https://raw.githubusercontent.com/Counterpart21/Amethyst-Mod-Manager/main/src/Utils/ba2_extract.py` | 12725 | `verbatim/Amethyst-ba2_extract.py` |

## Corroboration achieved

Four independent implementations captured: `Faster-File-Copy` (C++),
`ba2tools` (C#), `ByroRedux` (Rust), `Amethyst-Mod-Manager` (Python).
**Three of the four agree on every field of the 24-byte header, the 36-byte GNRL
record, the 24-byte DX10 base record, and the 24-byte DX10 chunk record.**

Independently confirmed by parsing two real BA2 fixtures against that layout —
`GeneralOneFile.ba2` decodes to exactly EOF with zero trailing bytes.

## Licensing note

These are third-party sources captured as **evidence**, not as dependencies.
`ba2tools` is WTFPL, `bae` is unspecific, `ByroRedux` and
`Amethyst-Mod-Manager` have their own terms. Per-file trust statements in the
frontmatter of each verbatim file record what each one is good for. No BA2
library is being adopted by this capture.
