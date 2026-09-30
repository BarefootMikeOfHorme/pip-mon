---
source_url: https://github.com/icodei/f4se-code (subdirs AddressLibGen/, AddressLibDecoder/)
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: index-authored
trust: "Authored by me from verbatim upstream C++ source in ./verbatim/. Every structural claim below is traceable to a line in AddressLibGen-src-main.cpp or AddressLibDecoder-src-main.cpp. Where upstream does not document something, I wrote 'not found in sources' rather than guessing."
provenance: "Requested target https://github.com/libxse/addresslib returned HTTP 404 and does not exist; the libxse GitHub org (enumerated via api.github.com/users/libxse/repos) contains 12 repos, none named addresslib. Substituted the closest real, working reference implementation of the same idea: icodei/f4se-code, which ships both halves of the pipeline (AddressLibGen = build step that derives an address blob; AddressLibDecoder = consumer that parses the blob)."
---

# Address mapping reference: schema of the version-keyed address blob

## RELATIONSHIP TO OUR PROJECT — READ FIRST

This is **runtime mapping reference material**, captured so a later session can see
how a version-independent address-ID scheme is actually built and serialised.

**This is NOT a dependency of ours. We have not vendored this code and must not.**
`icodei/f4se-code` is a third-party fork of the F4SE codebase. It is not F4SE source
that our project consumes. It is a *worked example* of one specific pattern: assign
stable integer IDs to (game version, code offset) pairs so a mod can ship a
version-independent identifier and relocate it at runtime.

Our project has a three-tier address resolver whose Tier 1 is an address-library
lookup against a database, plus a build step that derives an address blob from an
INI. **The pattern is analogous; the format is not ours to encode.** Nothing below is
a statement about our blob format. If our blob differs, ours wins.

## THE HEADLINE CORRECTION

The task asked for `addresslib.json` and its schema.

**No `addresslib.json` exists in any public repository I could reach.** I searched
and confirmed this rather than assuming. The real pipeline in the reference
implementation has no JSON at all:

```
mappings/<L1.L2.L3>_<R1.R2.R3>.txt     tab-separated text, human-maintained
        |  AddressLibGen  (build step, offline)
        v
version-<L1.L2.L3>.bin                 flat binary blob, shipped to runtime
        |  AddressLibDecoder (or the consumer)
        v
id -> offset, at runtime
```

So the "database" is a **directory of text files**, and the "blob" is a **flat
binary**. The schema that follows describes both. This is the part worth having:
it is small, it is fully determined by two source files, and it is easy to get
subtly wrong from memory.

## prose (human-readable)

An address blob is a *version-keyed map from a small integer to a code offset*.
The integer is the stable thing: it means "the function that does X", and it does
not change when Bethesda ships a game update. The offset is the volatile thing: it
changes with every patch. The whole design is "name the thing once, look up where
it lives today".

**How IDs get assigned is the interesting part, and it is not "increment a
counter per symbol".** `AddressLibGen` reads pairs of files that each describe the
*same* symbol in two different game versions, and it treats the problem as a
disjoint-set (union-find) over offsets. Two records that share an offset get
merged and end up with one shared ID. Crucially the merge is transitive and it
propagates: `Mapping::assign()` recurses into every linked mapping that has not
yet been assigned, so assigning one member of a connected group assigns the whole
group. Only after all groups are collapsed does a single counter run from 0
upward, handing out IDs. The practical consequence: **if the same offset appears
in N version files, those N entries share one ID, and ID numbers are not
contiguous per version** — a version's ID set is a sparse subset of the global ID
space.

**Offsets are stored as RVAs, not absolute addresses.** The generator subtracts
`0x140000000` from every offset it reads. `0x140000000` is the classic x64
image-base for a 64-bit Windows executable, so this strips the assumed load
address and leaves a base-relative value. At runtime the consumer is expected to
add the real module base back. This is an assumption baked into the format and is
worth copying deliberately if we copy any of it.

**The blob itself is deliberately dumb.** No strings, no names, no version
metadata, no checksum, no index. Just a count and a flat array of id/offset pairs,
sorted ascending by id. A consumer that wants a symbol must already have been
compiled with the numeric ID baked in; the blob can only answer "id N is at
offset X", never "what is id N called". That is the whole point of the split
between the address library and the consumer.

**Two things I could not establish, and did not invent.** First, the exact content
of the 18 header lines that the generator skips at the top of each mapping file
is `not found in sources` — the code reads and discards 18 lines without
interpreting them. Second, the **runtime lookup code is not in the captured
material**: I have the writer and a decoder that formats the blob to text, but
not the F4SE/CommonLibF4 routine that maps an ID to an address at load time.
`AddressLibDecoder` reads the blob linearly and prints it, which implies a sorted
structure but does not document a search. Treat "binary search over the id-sorted
array" as **inferred from the writer's sort, not documented**. If we need the
real loader, it must be fetched from CommonLibF4 or F4SE separately.

## SCHEMA: source mapping text file (`mappings/*.txt`)

| Key / field | Type | Size | Meaning | Documented? |
|---|---|---|---|---|
| filename `L1.L2.L3_R1.R2.R3.txt` | string | variable | The only key. Encodes two game versions: left = `L1.L2.L3`, right = `R1.R2.R3`. Regex is `(\d+)\.(\d+)\.(\d+)_(\d+)\.(\d+)\.(\d+)\.txt`; all six groups are parsed to `uint16`. | yes — `get_files()` |
| header lines 1..18 | text | variable | Discarded unread. `for (i = 0; i < 18; ++i) std::getline(...)`. Content and purpose unknown. | **undocumented** |
| column 1 | hex string | variable | Code offset of the symbol in the **left** version, base-relative after subtraction. Parsed by `std::stoull(s, 0, 16)`, so `0x` prefix optional. | yes |
| column 2 | hex string | variable | Code offset of the symbol in the **right** version, same treatment. | yes |
| separator | `\t` | 1 | Columns split on tab via `std::getline(ss, buf, '\t')`. | yes |
| `Version` internal | `uint16[4]` | 8 | A 4-element array of `uint16`. **Only elements 0,1,2 are ever populated from the filename; index 3 is never assigned and stays 0.** `string()` emits all four joined by `-`, so the emitted name has a trailing `-0` group. | yes (code), **note the unused slot** |
| key type | — | — | `offset_map` is `robin_hood::unordered_node_map<uint64, Mapping>`; `version_map` is `std::map<Version, offset_map>` so iteration is in ascending version order. | yes |

## SCHEMA: derived blob (`version-<A-B-C>.bin`)

Written by `write_binaries()`. Read by `AddressLibDecoder` via `mmio::mapped_file_source`.

| Offset | Field | Type | Size | Meaning | Documented? |
|---|---|---|---|---|---|
| 0x00 | `count` | uint64 LE | 8 | Number of `(id, offset)` records that follow. Read as `*reinterpret_cast<const uint64_t*>(input.data())`. | yes |
| 0x08 + 16*i | `id` | uint64 LE | 8 | The version-independent identifier. Assigned sequentially from 0 across the whole global ID space. | yes |
| 0x10 + 16*i | `offset` | uint64 LE | 8 | Base-relative code offset (image base already subtracted). | yes |
| — | record stride | — | 16 | `struct Pair { uint64_t id; uint64_t offset; }` — the decoder declares exactly this. | yes |
| — | record order | — | — | Records are `std::sort`ed **ascending by id** before writing. | yes |
| — | endianness | — | — | Not stated in a comment, but `file.write(reinterpret_cast<const char*>(&data), sizeof(data))` writes native memory verbatim, i.e. **little-endian on x64 Windows**. | yes (inferred from the write, marked) |
| — | count sanity bound | — | — | The decoder takes a `std::span` of `count` records starting at `data() + 8`. **There is no validation that `count` is sane** before the span is constructed. A truncated or hostile blob is read out of bounds. Worth copying the *check* if we copy the layout. | yes |
| — | name table | — | — | **Does not exist.** No strings, no symbol names, no version metadata, no checksum, no footer. | yes (absent) |
| — | trailer / magic | — | — | **Does not exist.** Unlike BA2 there is no sentinel to validate against. | yes (absent) |

## ID assignment algorithm (verbatim logic, not invented)

1. For every `L1.L2.L3_R1.R2.R3.txt`, create a `Mapping` for the left offset under
   version L, and one for the right offset under version R. Call `link()` on both.
2. `assign_ids()` walks `version_map` in ascending version order, and within each
   version in `robin_hood` **unordered** iteration order. **Consequence: within a
   single version, which offset gets which ID is not reproducible from this code
   alone** — it depends on hash-map bucket order. Only the *set* of
   (id, offset) pairs per version, and the id-sharing across versions, are stable.
   Do not assume a deterministic per-version ordering.
3. `Mapping::assign(id)` sets its own id, then recurses into any linked mapping
   that is still unassigned, assigning them the same id. This is what makes IDs
   version-invariant.
4. IDs come from one monotonic counter starting at 0, incremented per *group*,
   not per record.

## The shape most likely to be got wrong

- Offsets are **RVA, not absolute**. `address -= 0x140000000` happens in the
  generator. If a consumer skips that subtraction it will be off by the image base.
- The blob is **id-sorted, not offset-sorted**.
- IDs are **sparse per version** — do not assume `id < count` for a given version.
- There is **no version field inside the blob**. The version is in the *filename*
  only. A consumer that opens the wrong `version-*.bin` gets wrong offsets with
  no error indication.
- `packedSize`/compression: **none**. The blob is uncompressed raw records.

## Known gaps (do not fill these in from memory)

| Question | Status |
|---|---|
| Content of the 18 header lines per mapping file | **undocumented** — code skips them unread |
| Runtime ID→address lookup routine | **not found in sources** — see prose |
| Whether a name table or checksum exists in any real-world build | **not found in sources** — the two captured tools do not write one |
| Origin and schema of a hypothetical `addresslib.json` | **no such file found** — treat any JSON schema for this system as fabricated until a real source is produced |
| What `Version[3]` was intended for | **undocumented** — never assigned |
