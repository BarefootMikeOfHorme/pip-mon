---
source_url: https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2ToolsTests/Data/
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: index-authored
trust: "Authored by me. These are real BA2 files, byte-exact, taken from the test data of an established open-source reader (ba2tools). They are small hand-built fixtures, not Bethesda game archives, so they prove the container framing only - they contain no textures and no meshes. They are evidence, not a dependency; ba2tools is WTFPL licensed."
provenance: "https://raw.githubusercontent.com/miere43/ba2tools/dev/Source/Ba2ToolsTests/Data/"
---

# Real BA2 fixtures

These are actual `.ba2` files, not transcriptions. They are here because a
format description is worth little without something to parse, and the test
facility will need meshes and textures — so having real bytes on disk is more
valuable than prose.

| File | Bytes | Contents | Verdict |
|---|---|---|---|
| `GeneralHeaderOnly.ba2` | 24 | header only, `fileCount=0`, `nameTableOffset=0` | **valid** — cleanest possible proof of the 24-byte header |
| `GeneralHeaderOnlyInvalidVersion.ba2` | 24 | same but `version=153` | **intentionally invalid** — negative test for version validation |
| `GeneralOneFile.ba2` | 79 | header + 1 record + 9-byte payload + 1 name | **valid** — the recommended first fixture for a reader |
| `GeneralTwoFiles.ba2` | 143 | header + 2 records + 2 payloads + 2 names | **MALFORMED — do not use as a conformance case** |

## Verification I actually performed

I parsed these against the layout documented in `../ba2-format-notes.md`. The
results, in full:

**`GeneralHeaderOnly.ba2`** — `magic="BTDX"`, `version=1`, `type="GNRL"`,
`fileCount=0`, `nameTableOffset=0`. Parses exactly at 24 bytes. Note that
`nameTableOffset` is `0` rather than `24`; **whether `0` universally means "no
name table" is undocumented** in every source I captured.

**`GeneralOneFile.ba2`** — fully consistent, and worth using:
- header decodes to `version=1`, `GNRL`, `fileCount=1`, `nameTableOffset=69`
- the single 36-byte record sits at `0x18` and decodes to
  `nameHash=0xEFBEADDE`, `extension="txt"`, `dirHash=0xEFBEADDE`,
  `flags=0xEFBEADDE`, `offset=60`, `packedSize=0`, `unpackedSize=9`,
  `endMarker=0xBAADF00D`
- `offset=60` is exactly where the record table ends (24 + 36), which confirms
  payloads follow the record block and that `offset` is absolute
- the 9-byte payload is the ASCII string `test text`
- the name table at offset 69 decodes as `uint16 length=8` + `test.txt`, and
  ends at **exactly 79 = EOF, with zero trailing bytes**

That end-to-end agreement is what promotes the name-table format
(`uint16 length` + bytes, in record order) and the `0xBAADF00D` marker from
single-source claims to empirically confirmed.

**`GeneralTwoFiles.ba2`** — its two 36-byte records decode cleanly, but the name
table is inconsistent with the file's own length: entry 0 (`len=8`,
`test.txt`) parses, then entry 1 declares `len=16` at offset 131 while only 12
bytes remain before EOF at 143. The fixture is short by 6 bytes relative to its
own declared name table. **This is a defect in the upstream test data, not a
finding about the format.** Do not encode against it.

## What these fixtures cannot tell you

- **The `nameHash` / `dirHash` algorithm.** Every value in these files is the
  sentinel `0xDEADBEEF` / `0xADDEEFBE` — these fixtures deliberately do not
  contain real hashes. This remains the single biggest open gap for anyone
  writing a BA2.
- **Any texture or DX10 layout.** All four fixtures are `GNRL` and uncompressed.
  The DX10 records documented in `../ba2-format-notes.md` are **not**
  empirically confirmed by these files — they rest on three independent reader
  implementations agreeing, which is strong but is not the same as verified
  against a real Bethesda texture archive.
- **The GNRL `flags` field.** Left at the sentinel value here, so these files
  say nothing about it.
