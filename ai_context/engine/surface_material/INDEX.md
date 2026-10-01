---
directory: ai_context/engine/surface_material
purpose: >
  Single door into Fallout 4 surface/material reference documentation. Holds verbatim
  upstream page text only, plus this index. Fallout 4 scope ONLY.
compiled_utc: 2026-09-30T23:24:54Z
game_scope: Fallout 4
scope_warning: >
  Skyrim-only material is deliberately EXCLUDED. Fallout 4 dropped Havok for PhysX.
  No HKX, hkpPolyhedron, bhkCollisionObject, bhkMaterial, hbmaterial, HKMAT enums
  (HAV_MAT_STONE / HAV_MAT_WOOD / HAV_MAT_DIRT), CommonLibSSE, or BGSFootstepSet /
  BGSBodyPartData / BGSListForm record signatures appear in this directory. See
  "Rejected sources" below.
authored_file_note: "INDEX.md is the only authored file here. All other files are verbatim upstream bodies."
---

# Fallout 4 — Surface & Material Reference

## prose

This directory holds **verbatim upstream documentation** relevant to Fallout 4 surface and
material handling. It exists because a downstream AI must not hallucinate record layouts,
so real page text is stored unmodified behind YAML frontmatter that records the exact URL
fetched, the retrieval timestamp, and an honest trust statement.

**Read the trust field before you rely on anything here.** None of this material has been
verified against an installed Fallout 4 record. Two of the four files are from
`fopdoc` (maintained by the TES5Edit team); one is an unofficial fan site; one is
unrelated to Fallout 4 entirely and is retained only for the planned Rust/Python bridge.

The headline finding of this collection is a **negative** one, and it is the most important
thing in this directory:

> **The `MATT` (Material Type) record is NOT documented in any source reachable from this
> session.** No file was written for MATT, IPCT, IPDS, or FSTP, because inventing a field
> list for them would be worse than having nothing. See "Still unverified" below.

A secondary finding: **no Fallout 4 PhysX material or collision documentation was found at
all.** This is a real gap, not a search failure. The only FO4-adjacent physics documentation
that surfaced was on a site that documents *Havok* for Fallout 4, which is wrong for this
game and was therefore rejected and not written.

## Files

| File | Source URL | What it covers | Bytes |
| --- | --- | --- | --- |
| `fopdoc-fo4-impact-material-types.md` | https://tes5edit.github.io/fopdoc/Fallout4/Records/Values/Impact%20Material%20Types.html | **The most on-target file in this directory.** The Fallout 4 impact-material-type enum, values 0–11: Stone, Dirt, Grass, Glass, Metal, Wood, Organic, Cloth, Water, Hollow Metal, Organic Bug, Organic Glow. These are integer values consumed by impact/effect records. | 1,294 |
| `fopdoc-fo4-records-index.md` | https://tes5edit.github.io/fopdoc/Fallout4/Records.html | fopdoc's Fallout 4 record index plus the generic 24-byte record header and subrecord framing (`type char[4]`, `dataSize uint32`, `flags uint32`, `id formid`, …) and zlib compression scheme. Retained chiefly as **evidence of absence**: the index covers 14 FO4 record types and MATT is not among them. | 3,468 |
| `fo4docs-esm-esp-format.md` | https://www.fo4docs.org/File%20Formats/ESM | Unofficial fan reference for FO4 ESM/ESP binary structure: record header offsets, GRUP hierarchy and group types, `XXXX` length-override fields, zlib compression, and per-record subrecord tables for 20 record types. Includes two records that *point at* our targets: `LTEX.MNAM` is described as "Material type" (a formid), and `WEAP.INAM` as "Impact dataset" (a formid). **Contains a direct contradiction of fopdoc** — see Conflicts below. | 17,101 |
| `maturin-user-guide-introduction.md` | https://www.maturin.rs/ | Official maturin user guide, chapter 1. Not Fallout 4 material. Held for the planned Rust/Python bridge: builds PyO3/cffi/uniffi-extension wheels. Authoritative for maturin. | 17,455 |

## What these files do and do not give you

**They give you:**
- A confirmed FO4 impact-material-type integer enum (12 values) from the format maintainers.
- Confirmed FO4 binary framing: 24-byte record header, subrecord packing, zlib compression.
- Cross-references showing that `LTEX` holds a *reference* to a material type record and
  `WEAP` holds a *reference* to an impact dataset record — which implies MATT and the IPDS
  family exist in FO4, but says nothing about their internal layout.

**They do NOT give you:** the subrecord list, field names, field types, field sizes, or
offsets for `MATT`, `IPCT`, `IPDS`, or `FSTP`. Nothing in this directory should be used to
infer them.

## Still unverified — records with NO documentation found

| Record | Name | Status | What was tried |
| --- | --- | --- | --- |
| `MATT` | Material Type | **not documented** | fopdoc FO4 record index (absent); full fopdoc repo tree via GitHub API (no `MATT.md`); en.uesp.net search + allpages + title lookup (endpoint returns an empty database); 6 distinct websearch phrasings. No page in any reachable source describes MATT's subrecords. |
| `IPCT` | Impact Data | **not documented** | Same sources as above. Note: fopdoc *does* have a `Fallout3/Records/IPCT.md`, but that is Fallout 3, not Fallout 4, and its `DATA` subrecord references a Havok-era impact material enum. Deliberately not used. |
| `IPDS` | Impact Data Set | **not documented** | Same sources. A `Fallout3/Records/IPDS.md` exists but is out of scope for this directory. |
| `FSTP` | Footstep Set | **not documented** | Same sources. Note `BGSFootstepSet` is a *class* name, not a record signature; per project constraint it is not treated as one. |
| `BGSSoundImpactDataset` | (class, not a record) | **not documented** | No documentation found. Per project constraint this is a class name and is not recorded as a record signature. |
| FO4 PhysX material handling | — | **no documentation exists** | See "Gap" below. |
| FO4 collision / material enum | — | **partially covered** | The fopdoc impact-material-type enum is a gameplay/impact enum. It is *not* documented as a PhysX material mapping, and no source states which PhysX material each MATT maps to. |

### The PhysX gap, stated plainly

**No Fallout 4 PhysX material or FO4 collision documentation was found. This is a real gap.**

Every FO4 physics result surfaced was either (a) generic NVIDIA PhysX SDK documentation,
which is not about Fallout 4, or (b) the `fo4docs.org` site, which documents **Havok**
for Fallout 4 — the wrong physics engine, and one that would poison this corpus with exactly
the structures excluded by scope. Searches were run for "Fallout 4 PhysX collision mesh
material modding documentation" and "Fallout 4 PhysX material handling"; neither returned an
FO4-specific PhysX source.

Practical consequence: the mapping from FO4 `MATT` records to PhysX material instances is
**entirely undocumented** in this corpus. If a downstream component needs it, it must come
from disassembly of `Fallout4.exe` or from CommonLibF4, not from here.

## Conflicts between held sources — read before using record flags

`fo4docs-esm-esp-format.md` makes an explicit, on-page claim that contradicts the fopdoc
material held elsewhere in this knowledge base:

> "Older documentation sources (fopdoc, xEdit) list additional flags inherited from Skyrim's
> format, but several of those have been found to be incorrect for FO4."

Specifically, fopdoc's FO4 page lists `0x00000001` = master file and `0x00000200` = light
master, and documents a 5-field tail (`revision uint32`, `version uint16`, `unknown uint16`).
`fo4docs.org` instead documents a 6×uint16 tail and a different flag set
(`0x00000020` deleted, `0x00000800` initially disabled, `0x00040000` compressed,
`0x00800000` marker).

Both cannot be right. **This was not adjudicated** — no Fallout 4 install was available to
check against. Treat record-flag and record-tail questions as open. fopdoc is the
maintainer of the actual tool and carries more weight, but the fo4docs claim of code analysis
is not obviously wrong either.

## Rejected sources — excluded as Skyrim, or otherwise out of scope

These were fetched or encountered and deliberately **not** written to disk. Recording them so
a later session does not re-tread them.

| Source | Why rejected |
| --- | --- |
| `https://www.fo4docs.org/File Formats/Assets/NIF/` | **Havok-contaminated.** Despite being an FO4 site, its Collision section documents `bhkCollisionObject`, `bhkRigidBody`, `bhkRigidBodyT`, `bhkShape`, `bhkBoxShape`, `bhkSphereShape`, `bhkCapsuleShape`, `bhkConvexVerticesShape`, `bhkMoppBvTreeShape`, `bhkNiTriStripsShape`, `bhkCompressedMeshShape`, and states collision "uses its own Havok-specific serialization". All excluded structures. The site also has a dedicated `Havok Collision` page in its nav. |
| `https://www.fo4docs.org/Gameplay/Movement/` | **Havok-contaminated.** Documents a "Havok character controller", `hknpCharacterStateType` (`OnGround -> Jumping -> InAir`), `bhkCharacterController`, an INI section `[Havok]`, and `fInAirFallingCharGravityMult`. All excluded structures. |
| `https://ck.uesp.com`, `https://ck.uesp.net` | Known transport errors / HTTP 403 from a previous session. Not retried. |
| Fallout 3 / New Vegas sections of fopdoc | `Fallout3/Records/IPCT.md` and `Fallout3/Records/IPDS.md` exist and would have answered IPCT/IPDS — but they are Fallout 3, pre-PhysX, and their impact material enum differs from FO4's. Using them would be a scope violation. |
| NVIDIA PhysX SDK docs (`nvidia-omniverse.github.io`, `NVIDIAGameWorks/PhysX`, O3DE, GMPhysX) | Genuine PhysX documentation, but engine-generic. Not Fallout 4. Adds no FO4-specific fact; would risk implying FO4 uses stock PhysX API semantics. |
| `CommonLibSSE` | Skyrim. Excluded by constraint. CommonLibF4 is already held elsewhere. |
| Fallout Wiki / Fandom / IGN / Game8 / Nexus "material" pages | These are *crafting-component* articles (Steel, Wood, Glass as junk items) or item-ID lists. They have nothing to do with the `MATT` record and are a search-result trap. |

## Retrieval failures — exact errors

| URL | Error |
| --- | --- |
| `https://en.uesp.net/wiki/Category:Mod_API` | `StatusCode: non 2xx status code (404 GET https://en.uesp.net/wiki/Category:Mod_API)` |
| `https://en.uesp.net/wiki/Mod:Material%20Type` | `StatusCode: non 2xx status code (404 GET https://en.uesp.net/wiki/Mod:Material%20Type)` |
| `https://en.uesp.net/wiki/Category:Fallout_4_Mod` | `StatusCode: non 2xx status code (404 GET https://en.uesp.net/wiki/Category:Fallout_4_Mod)` |
| `https://en.uesp.net/w/api.php?...srsearch=MATT Material Type` | `{"batchcomplete":"","query":{"searchinfo":{"totalhits":0,"suggestion":"mage material types",...},"search":[]}}` — 0 hits |
| `https://en.uesp.net/w/api.php?...srsearch=Material Type Fallout 4` | `{"batchinfo":...,"totalhits":0,...,"search":[]}` — 0 hits |
| `https://en.uesp.net/w/api.php?...srsearch=Footstep Set` | `totalhits: 0` — 0 hits |
| `https://en.uesp.net/w/api.php?...srsearch=Impact Data Set` | `totalhits: 0` — 0 hits |
| `https://en.uesp.net/w/api.php?action=query&list=allpages&apprefix=Mod%3A` | `{"error":{"code":"invalidtitle","info":"Bad title \"Mod:\".","*":"See https://en.uesp.net/w/api.php for API usage..."}}` |
| `https://en.uesp.net/w/api.php?action=query&list=allpages&apprefix=Mod%3AMaterial` | `{"error":{"code":"invalidtitle","info":"Bad title \"Mod:Material\".","*":"..."}}` |
| `https://en.uesp.net/w/api.php?action=query&list=allpages&apprefix=Material` | `{"batchcomplete":"","query":{"allpages":[]}}` — empty |
| `https://en.uesp.net/w/api.php?action=query&list=categorymembers&cmtitle=Category:Fallout%204%20Mod` | `{"batchcomplete":"","query":{"categorymembers":[]}}` — empty |
| `https://en.uesp.net/w/api.php?action=query&titles=Dragonsreach` | `{"pages":{"-1":{"ns":0,"title":"Dragonsreach","missing":""}}}` — **control test.** A page that certainly exists reports as missing, so this API endpoint is serving an empty database. |

**Conclusion on en.uesp.net:** the host responds, but its MediaWiki API and wiki paths are
effectively non-functional. The 0-hit results for MATT/FSTP/IPDS are therefore **not
evidence that those pages do not exist** — they are evidence the search backend is broken.
Do not re-run these searches and conclude the pages are absent.

## Notes for the next session

1. **Highest-value next step for MATT** is not more web searching. It is either (a) reading
   MATT's actual subrecords out of an installed `Fallout4.esm` with xEdit, or (b) reading the
   MATT structure out of CommonLibF4, which is already held. Either yields verified bytes
   instead of a second-hand claim.
2. `fo4docs.org` has pages for FO4 `Water (WATR)`, `Grass (GRAS)`, `Material Swaps (MSWP)`,
   `BA2`, and `Textures & Materials`. These were not fetched — out of the requested scope —
   but the `MSWP` page in particular is titled "Material Swaps" and may touch MATT. **Verify
   it is Havok-free before indexing it**, given this site's demonstrated habit.
3. The record-flag conflict between fopdoc and fo4docs.org is unresolved and should be settled
   empirically before any code depends on it.
