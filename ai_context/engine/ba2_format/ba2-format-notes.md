---
source_url: https://github.com/1001Bits/Faster-File-Copy , https://github.com/miette43/ba2tools , https://github.com/matiaszanolli/ByroRedux , https://github.com/Counterpart21/Amethyst-Mod-Manager
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: index-authored
trust: "Authored by me. Every offset below is attributed to at least one captured source, and I state the corroboration level explicitly. Four independent third-party implementations were captured and cross-checked against each other; three of the four agree on every field. The primary spec that the main source cites (a Nexus wiki page) is dead and was NOT read. I did not have a real game BA2 on hand to test against, so nothing here is confirmed against Bethesda's own output except via the two tiny third-party fixtures in ./fixtures/."
provenance: "No dedicated BA2 specification was reachable. en.uesp.net and ck.uesp.net have no BA2 page (all four URLs probed returned 404/403). The Bethesda Archive2 tool is proprietary, ships only inside Creation Kit, and has no public source, so its 'command-line approach' and 'format notes' could NOT be retrieved. What was retrieved instead is four independent open-source BA2 reader implementations plus their own inline documentation, which between them pin down the container layout."
---

# BA2 archive format: field-by-field notes

## RELATIONSHIP TO OUR PROJECT — READ FIRST

**We need the BA2 FORMAT. We do not need a BA2 tool.**

The Archive2 *tool* has been removed from our project and is not coming back.
Separately, BA2-capable tooling is already on this machine (`BSArch.exe`,
`BSArch64.exe`, `BSArchPro.exe`, `BSArchPro64.exe` ship with xEdit), so acquiring
another packer would be redundant. What we actually lack is a written definition
of the container, because the test facility will need meshes and textures and
asset handling is ours.

So: everything below is **format knowledge to encode**, not a dependency to
adopt. No BA2 library, reader, or writer is being vendored by this capture. The
four upstream projects in `./verbatim/` are evidence, not dependencies. Note
their licences differ and mostly forbid reuse — see the trust notes in the
per-file frontmatter.

## Terminology corrections to the request

Two terms in the brief do not correspond to anything real, and I am flagging
them rather than inventing definitions for them:

- **"GNF"** — there is no `GNF` BA2 type. The two real type tags are `GNRL`
  and `DX10`. I read "GNF" as a slip for `GNRL` and wrote it that way.
- **"BS versions"** — there are no "BS" BA2 versions. `BS` appears to be a
  confusion with **BSA**, which is a *different, older* container (Oblivion
  through Skyrim SE). A BA2 archive is never a "BS version". I have not
  documented BSA, and the one captured source that covers both
  (`ByroRedux-archives.md`) is the only place in this capture where BSA layout
  appears.

## prose (human-readable)

A BA2 is a **flat, header-first container with no file hierarchy**. You open it,
read a 24-byte header, then read exactly `fileCount` fixed-size records back to
back. After the records comes the file payloads, then a name table at an offset
the header points you to. There is no directory tree, no per-file header
preamble, and no compression dictionary shared across files.

The single most consequential design choice is that **BA2 does not store paths.**
Each record carries a 4-byte `nameHash` and a 4-byte `dirHash` — that is the
entire addressing mechanism inside the record. The human-readable path only
exists in the *optional* name table at the end. So an archive is fundamentally
hash-addressed, and the name table is an index over that, not the source of
truth. Any tool that assumes "read the name, then find the data" has the
dependency backwards.

That also means **writing a BA2 correctly requires knowing the hash algorithm**,
and here is the important admission: **not one of my four sources documents it.**
All four read the hashes; all four decline to say what function produces them.
`ba2tools` calls them "Probably file hash" and "Probably directory hash" — the
author of the most mature reader I captured did not know either. This is the
hardest blocker for a writer and it is an open gap, not something to guess.

The second big thing is the **DX10 texture variant**, which behaves nothing like
GNRL. A DX10 archive does not store a DDS file. It stores a 24-byte metadata
record describing the texture (width, height, mip count, DXGI format, chunk
count) followed by N 24-byte per-mip chunk records, and the *pixel data only*.
The DDS header — 128 or 148 bytes of it — is **not in the file** and must be
synthesised on extraction from those metadata fields. This is a real trap: a
DX10 archive is not a container of DDS files, it is a container of DDS pixel
bodies plus enough metadata to rebuild the headers.

`packedSize == 0` is the universal "stored uncompressed" sentinel, appearing
identically in GNRL records and DX10 chunk records. Both readers I captured
branch on exactly that.

A third trap is the **`0xBAADF00D` end marker** occupying the last 4 bytes of
every GNRL record and every DX10 chunk record. It is pure padding, it is
consistently present, and it is the best structural self-check available when
writing a file.

Finally, **version numbering is non-monotonic and game-ordinal, not
chronological**, and this has broken real tools. `v1` is original Fallout 4,
`v2`/`v3` are Starfield, and `v7`/`v8` are the Fallout 4 Next-Gen update — so
FO4 Next-Gen archives have a *higher* version number than Starfield's, and a
"is it at least 2?" test silently mis-parses FO4 v8. One captured source
documents being bitten by precisely this. **Test on `version == 2 || version == 3`
explicitly, never on an inequality.**

## Container header — field by field (24 bytes)

Corroboration: **all four sources agree**, and the layout is additionally
confirmed byte-for-byte by the two fixtures in `./fixtures/`.

| Offset | Size | Type | Field | Meaning | Documented? |
|---|---|---|---|---|---|
| 0x00 | 4 | char[4] | `magic` | Always `BTDX`. | **yes — 4 sources + fixtures** |
| 0x04 | 4 | uint32 LE | `version` | Archive version. Non-monotonic; see version table below. | **yes — 4 sources + fixtures** |
| 0x08 | 4 | char[4] | `type` | `GNRL` or `DX10`. Nothing else is accepted by any captured reader. | **yes — 4 sources + fixtures** |
| 0x0C | 4 | uint32 LE | `fileCount` | Number of file records that immediately follow the header. | **yes — 4 sources + fixtures** |
| 0x10 | 8 | uint64 LE | `nameTableOffset` | Absolute byte offset of the name table. | **yes — 4 sources + fixtures** |
| 0x18 | — | — | — | End of header. Header is exactly 24 bytes. | **yes** |

**Meaning of `nameTableOffset == 0`**: observed as `0` in the
`GeneralHeaderOnly.ba2` fixture (a 0-file archive). Whether `0` universally
means "no name table" is **undocumented** — no source states it. Do not assume.

## Version field — what the sources actually claim

| Value | Claimed meaning | Source count | Header size |
|---|---|---|---|
| 1 | Original Fallout 4; also Fallout 76 | 2 (ByroRedux, FasterFileCopy) | 24 bytes |
| 2 | Starfield general (GNRL) | 1 (ByroRedux) | 32 bytes = 24 + 8 |
| 3 | Starfield texture (DX10) | 1 (ByroRedux) | 36 bytes = 24 + 12 |
| 7 | Fallout 4 Next-Gen texture (DX10) | 1 (ByroRedux) | 24 bytes |
| 8 | Fallout 4 Next-Gen update (GNRL and DX10) | 1 (ByroRedux) | 24 bytes |

**The v2/v3/v7/v8 assignments rest on a single source.** Two independent
readers do not corroborate them. For a Fallout 4 project the practically
important claim is **v1 = original FO4, 24-byte header, zlib**, which *is*
corroborated. Treat Starfield version numbers as single-source and unverified.

Header extensions (single-source, ByroRedux only):
- v2: `+8 bytes (2x uint32 unknown, "likely compressed name-table metadata")`.
  Meaning **undocumented**.
- v3: `+12 bytes` = the v2 eight bytes `+ uint32 compression_method`, where
  `0 = zlib` and `3 = LZ4 block`. Meaning of the two uint32s still
  **undocumented**.

## GNRL file record — field by field (36 bytes)

| Offset | Size | Type | Field | Meaning | Documented? |
|---|---|---|---|---|---|
| 0x00 | 4 | uint32 LE | `nameHash` | Hash of the file name. **The hash function is not documented by any source.** | size+offset **yes**; algorithm **NO** |
| 0x04 | 4 | char[4] | `extension` | Null-padded extension, e.g. `txt\0`, `nif\0`, `dds\0`. Confirmed in fixtures. | **yes — 3 sources + fixtures** |
| 0x08 | 4 | uint32 LE | `dirHash` | Hash of the containing directory. **Algorithm not documented.** | size+offset **yes**; algorithm **NO** |
| 0x0C | 4 | uint32 LE | `flags` | **No source documents what any bit means.** `ba2tools` says only "Probably file flags". `FasterFileCopy` says "file flags". | size+offset **yes**; **semantics NO** |
| 0x10 | 8 | uint64 LE | `offset` | **Absolute** offset of the payload within the same file (not relative to the record). | **yes — 3 sources + fixtures** |
| 0x18 | 4 | uint32 LE | `packedSize` | Compressed size. **`0` means stored uncompressed** — not "size zero". | **yes — 3 sources + fixtures** |
| 0x1C | 4 | uint32 LE | `unpackedSize` | Decompressed size. | **yes — 3 sources + fixtures** |
| 0x20 | 4 | uint32 LE | `endMarker` | Always `0xBAADF00D`. Pure padding / structural sentinel. | **yes — 3 sources + fixtures** |

## DX10 base record — field by field (24 bytes)

| Offset | Size | Type | Field | Meaning | Documented? |
|---|---|---|---|---|---|
| 0x00 | 4 | uint32 LE | `nameHash` | As GNRL. Algorithm **not documented**. | size+offset **yes**; algorithm **NO** |
| 0x04 | 4 | char[4] | `extension` | `dds\0` in practice. | **yes — 3 sources** |
| 0x08 | 4 | uint32 LE | `dirHash` | As GNRL. Algorithm **not documented**. | size+offset **yes**; algorithm **NO** |
| 0x0C | 1 | uint8 | `unknown1` | Always `0` per ByroRedux. **Undocumented meaning.** | **NO** |
| 0x0D | 1 | uint8 | `numChunks` | Number of per-mip chunk records that follow this base record. | **yes — 3 sources** |
| 0x0E | 2 | uint16 LE | `chunkHeaderSize` | Size of each chunk record; always `24`. | **yes — 3 sources** |
| 0x10 | 2 | uint16 LE | `height` | Texture height in pixels. | **yes — 3 sources** |
| 0x12 | 2 | uint16 LE | `width` | Texture width in pixels. | **yes — 3 sources** |
| 0x14 | 1 | uint8 | `numMips` | Mipmap count. | **yes — 3 sources** |
| 0x15 | 1 | uint8 | `format` | DXGI format enum value. | **yes — 3 sources** |
| 0x16 | 2 | uint16 LE | `flags` | `FasterFileCopy` names this `isCubeMap` and says `0x0800` if cubemap; ByroRedux says "bit 0 = cubemap". **These two statements contradict each other** — see gaps. | **CONFLICTED** |

Note the `isCubeMap`/flags naming conflict is between two captured sources and is
**not resolved**. Do not encode either reading without verifying against a real
DX10 archive.

## DX10 chunk record — field by field (24 bytes)

| Offset | Size | Type | Field | Meaning | Documented? |
|---|---|---|---|---|---|
| 0x00 | 8 | uint64 LE | `offset` | Absolute offset of the chunk payload. | **yes — 3 sources** |
| 0x08 | 4 | uint32 LE | `packedSize` | `0` = stored uncompressed. | **yes — 3 sources** |
| 0x0C | 4 | uint32 LE | `unpackedSize` | Decompressed size. | **yes — 3 sources** |
| 0x10 | 2 | uint16 LE | `startMip` | First mip level in this chunk. | **yes — 3 sources** |
| 0x12 | 2 | uint16 LE | `endMip` | Last mip level in this chunk. | **yes — 3 sources** |
| 0x14 | 4 | uint32 LE | `endMarker` | Always `0xBAADF00D`. | **yes — 3 sources** |

## Name table

| Property | Value | Documented? |
|---|---|---|
| Location | `nameTableOffset` from the header (absolute) | **yes** |
| Order | One entry per file, **in record order** | **yes — 1 source (ByroRedux)**, consistent with fixtures |
| Entry format | `uint16 length`, then `length` bytes of name | **yes — 1 source (ByroRedux)** |
| Encoding | UTF-8 per ByroRedux; the fixtures hold plain ASCII, which is consistent with but does not prove UTF-8 | **single-source** |
| Separator convention | FO4 uses backslashes, FO76 forward slashes; ByroRedux normalises to backslash + lowercase | **single-source** |
| Empirically confirmed | Yes — `GeneralOneFile.ba2` parses cleanly to exactly EOF with this format | **yes, verified** |

## Compression

| Claim | Documented? |
|---|---|
| Fallout 4 BA2 (v1/v7/v8) uses **zlib** per-entry, indicated by non-zero `packedSize` | **yes — 2 sources (ByroRedux, ba2tools "ZLib packed length")** |
| Starfield v3 may use **LZ4 block**, archive-level, selected by the header `compression_method` field (`0`=zlib, `3`=LZ4 block) | **single-source (ByroRedux)** |
| Compression is per-entry, not archive-wide, for FO4 | **yes — 1 source, and consistent with the per-record `packedSize` field existing at all** |
| Whether the zlib stream carries an Adler-32 trailer, and whether any size prefix precedes it | **undocumented** — note BSA *does* prefix the uncompressed size, per ByroRedux's BSA section, but that is a BSA fact and must not be assumed for BA2 |

## Empirical verification performed

I did not merely transcribe these offsets. Two real, tiny, third-party-built BA2
files in `./fixtures/` were parsed against the layout above:

- `GeneralHeaderOnly.ba2` (24 bytes) — header only, `fileCount=0`,
  `nameTableOffset=0`. Parses exactly. Confirms the 24-byte header and that
  `version=1`/`GNRL` is valid.
- `GeneralOneFile.ba2` (79 bytes) — `fileCount=1`. Record at 0x18 decodes
  cleanly; `offset=60` is exactly where the record table ends; `unpackedSize=9`
  matches the 9-byte payload; `endMarker` reads `0xBAADF00D`; and the name table
  at 69 decodes to `len=8 "test.txt"` and ends **exactly at EOF (79)**, with
  zero trailing bytes. This is a complete, self-consistent, minimal valid GNRL
  v1 archive and is a good first fixture for a reader.
- `GeneralTwoFiles.ba2` (143 bytes) — **MALFORMED, do not use as a conformance
  case.** Its two records decode cleanly, but its name table is inconsistent
  with its own file length: entry 0 (`len=8`, `test.txt`) parses, then entry 1
  declares `len=16` at offset 131, but only 12 bytes remain before EOF (143).
  The fixture is short by 6 bytes relative to its own declared name table. This
  is a defect in the upstream test data, not a finding about the format.

## Gaps — do NOT fill these in from memory

| Question | Status |
|---|---|
| The `nameHash` / `dirHash` algorithm | **undocumented in all 4 sources.** Blocks any correct BA2 *writer*. Highest-priority unknown. |
| Bit meaning of the GNRL `flags` field | **undocumented** |
| Bit meaning of the DX10 `flags` field | **CONFLICTED** between two captured sources (bit 0 vs `0x0800`) |
| Meaning of the DX10 base `unknown1` byte at 0x0C | **undocumented** |
| The primary BA2 spec (Nexus wiki `BA2_File_Format`, cited by `FasterFileCopy`) | **UNREACHABLE — HTTP 403.** Not read. |
| Any BA2 page on en.uesp.net or ck.uesp.net | **DOES NOT EXIST** — 4 URLs probed, 404/403 |
| Archive2 tool's CLI and its format notes | **UNAVAILABLE** — proprietary, ships only in Creation Kit, no public source located |
| Whether `nameTableOffset == 0` universally means "absent" | **undocumented** (only seen in a 0-file fixture) |
| Endianness as an explicit spec statement | **implied by every reader's use of LE struct unpacking, but never stated in prose by any source** |
| Max `fileCount` / any hard archive size limit for BA2 | **undocumented** (BSA has a hardcoded 2 GB limit per BSArch's docs; **that is BSA and must not be assumed for BA2**) |
