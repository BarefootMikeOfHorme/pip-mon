---
source_url: https://www.fo4docs.org/File%20Formats/ESM
title: "ESM / ESP Format - The unofficial Fallout 4 Documentation"
retrieved_utc: 2026-09-30T23:24:54Z
content_kind: upstream-documentation-verbatim
trust: "unofficial fan-made technical reference, quoted verbatim. NOT verified against an installed Fallout 4 record. Author claims (stated on-page) that several fopdoc/xEdit record flags are INCORRECT for FO4; this is an unverified claim and conflicts with the fopdoc record already held. This page is ESM/ESP record structure only. It does NOT document MATT, IPCT, IPDS or FSTP. Its site nav links to a 'Havok Collision' page; that page was NOT fetched and is out of scope for Fallout 4 (PhysX)."
game_scope: Fallout 4
---

ESM / ESP Format - The unofficial Fallout 4 Documentation        

[Skip to content](#esm-esp-format)

[](../.. "The unofficial Fallout 4 Documentation")

The unofficial Fallout 4 Documentation

ESM / ESP Format

 

Initializing search

-   [Home](../..)
-   [Creation Engine](../../Creation%20Engine/Overview/)
-   [Papyrus](../../Papyrus/Overview/)
-   [File Formats](../)
-   [Gameplay](../../Gameplay/)

# ESM / ESP Format[¶](#esm-esp-format "Permanent link")

`.esm` (Elder Scrolls Master) and `.esp` (Elder Scrolls Plugin) files are Bethesda's binary record database format used across all modern Creation Engine games. In Fallout 4 they store every piece of game data: world geometry references, NPCs, items, quests, audio, weather, and more.

## File Structure[¶](#file-structure "Permanent link")

An ESM is a flat binary stream of **groups** and **records**, each preceded by a 24-byte header.

### Record Header (24 bytes)[¶](#record-header-24-bytes "Permanent link")

Offset

Type

Meaning

Notes

0x00

char\[4\]

Type

Record type code, e.g. "CELL", "NPC\_", "TES4"

0x04

uint32

Data size

Size of the field payload (excludes this header)

0x08

uint32

Flags

See flags table below

0x0C

uint32

Form ID

Unique identifier within the plugin

0x10

uint16

Unknown

Purpose is unknown

0x12

uint16

Unknown

Purpose is unknown, but likely used for version control

0x14

uint16

Unknown

Purpose is unknown

0x16

uint16

Unknown

Purpose is unknown

**Record flags:**

Bit

Meaning

Notes

`0x00000020`

Deleted

Record is logically removed; never spawns in-game. Vanilla Fallout4.esm contains none, but DLC and mod plugins can.

`0x00000800`

Initially Disabled

Placed reference starts disabled. Visibility may be overridden by an XESP enable-parent chain.

`0x00040000`

Compressed

Payload is zlib-compressed (see Compression below).

`0x00800000`

Marker

Record is a CK-only marker object (XMarker, trigger box, etc.) that should not be rendered.

Note: some flags are context-dependent and have different meanings on different record types. The flags above are the ones confirmed through code analysis of Fallout 4. Older documentation sources (fopdoc, xEdit) list additional flags inherited from Skyrim's format, but several of those have been found to be incorrect for FO4.

### GRUP Header (24 bytes)[¶](#grup-header-24-bytes "Permanent link")

Groups wrap records of the same type or records belonging to a parent record.

`[](#__codelineno-0-1)"GRUP"       char[4]   - magic [](#__codelineno-0-2)group_size   uint32    — total size including this header [](#__codelineno-0-3)label        char[4]   — record-type code for type=0; cell/world coords for others [](#__codelineno-0-4)group_type   int32     — see group type table [](#__codelineno-0-5)timestamp    uint16 [](#__codelineno-0-6)vcs_info     uint16 [](#__codelineno-0-7)unknown      uint32`

**Group types:**

Value

Meaning

Label interpretation

0

Top-level

Record type (e.g. `CELL`)

1

World children

Worldspace form ID

2

Interior cell block

Block number (int32)

3

Interior cell sub-block

Sub-block number (int32)

4

Exterior cell block

Grid Y (int16) + Grid X (int16)

5

Exterior cell sub-block

Grid Y (int16) + Grid X (int16)

6

Cell children

Cell form ID

7

Topic children

Topic form ID

8

Cell persistent children

Cell form ID

9

Cell temporary children

Cell form ID

### Field (Subrecord)[¶](#field-subrecord "Permanent link")

Within each record's decompressed payload, fields are packed end-to-end:

`[](#__codelineno-1-1)code    char[4]   — field type, e.g. "EDID", "DATA", "DNAM" [](#__codelineno-1-2)length  uint16    — byte length of data [](#__codelineno-1-3)data    byte[length]`

**XXXX override field:** When a field named `XXXX` appears, its 4-byte payload contains a `uint32` giving the *true* length of the immediately following field. That following field's own `length` uint16 is meaningless. This handles fields exceeding 65535 bytes.

### Compression[¶](#compression "Permanent link")

When the record flag `0x00040000` is set, the record payload (after the 24-byte header) is:

`[](#__codelineno-2-1)uncompressed_size  uint32   — size after decompression [](#__codelineno-2-2)zlib_data          byte[]   — standard zlib stream (RFC 1950)`

Decompress to `uncompressed_size` bytes, then parse fields normally.

### TES4 — File Header Record[¶](#tes4-file-header-record "Permanent link")

Always the first record. Key fields:

Field

Type

Content

`HEDR`

struct

Version (float32), num records (uint32), next object ID (uint32)

`CNAM`

zstring

Author name

`SNAM`

zstring

Description

`MAST`

zstring

Master filename (repeated per dependency)

`DATA`

uint64

Master file size (paired with each MAST)

---

## FormID / FormKey[¶](#formid-formkey "Permanent link")

Every record is identified by a 32-bit FormID. The upper 8 bits encode the **load order index** of the plugin that owns the record; the lower 24 bits are the record's local ID within that plugin.

When serialized as a string (FormKey): `"0x{LocalID:X6}:{PluginFilename}"`, e.g. `"0x03C0F0:Fallout4.esm"`.

---

## World Hierarchy[¶](#world-hierarchy "Permanent link")

Exterior world records are nested in a specific GRUP hierarchy:

`[](#__codelineno-3-1)GRUP(type=0, label="WRLD")         top-level worldspace group [](#__codelineno-3-2)  WRLD record                      worldspace metadata [](#__codelineno-3-3)  GRUP(type=1, label=wrld_formid)  world children [](#__codelineno-3-4)    CELL record                    persistent worldspace cell [](#__codelineno-3-5)    GRUP(type=4, label=blockXY)    exterior cell block [](#__codelineno-3-6)      GRUP(type=5, label=subXY)     exterior cell sub-block [](#__codelineno-3-7)        CELL record                individual exterior cell [](#__codelineno-3-8)        GRUP(type=6, label=cell)   cell children [](#__codelineno-3-9)          LAND record              landscape data [](#__codelineno-3-10)          REFR/ACHR/...            placed objects`

Interior cells live under a different top-level group:

`[](#__codelineno-4-1)GRUP(type=0, label="CELL") [](#__codelineno-4-2)  GRUP(type=2, label=blockNum)     interior cell block [](#__codelineno-4-3)    GRUP(type=3, label=subNum)     interior cell sub-block [](#__codelineno-4-4)      CELL record [](#__codelineno-4-5)      GRUP(type=6, label=cell) [](#__codelineno-4-6)        REFR/ACHR/...`

---

## Record Types[¶](#record-types "Permanent link")

### ARMO — Armor[¶](#armo-armor "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`FULL`

lstring

Name

`MODL`

zstring

World model (male)

`MOD2`

zstring

World model (female)

`DNAM`

struct

Armor rating (float32)

`DATA`

struct

Value (int32) + weight (float32)

`BODT` / `BOD2`

struct

Body slot flags

`RNAM`

formid

Race

`EITM`

formid

Enchantment

`INDX`

uint32

Addon index

### CELL — Cell[¶](#cell-cell "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`FULL`

lstring

Display name

`DATA`

uint16

Flags (interior=1, has water=2, etc.)

`XCLC`

struct

Grid X (int32), Grid Y (int32), Force hide land (uint32)

`XCLL`

struct

Lighting (ambient, directional, fog colors + distances)

`LTMP`

formid

Lighting template

`XEZN`

formid

Encounter zone

`XCLW`

float32

Water height

`XCWT`

formid

Water type

`XOWN`

formid

Owner

### CONT — Container[¶](#cont-container "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`FULL`

lstring

Name

`MODL`

zstring

Model path

`DATA`

struct

Flags (uint8) + weight (float32)

`SNAM`

formid

Open sound

`QNAM`

formid

Close sound

`CNTO`

struct

Item entry: formid + int32 count (repeated)

### DIAL / INFO — Dialogue[¶](#dial-info-dialogue "Permanent link")

`DIAL` (topic) groups `INFO` (response) records.

DIAL field

Content

`EDID`

Editor ID

`FULL`

Topic name

`PNAM`

Priority (float32)

`BNAM`

Branch (formid)

`QNAM`

Quest (formid)

`DATA`

Flags

INFO field

Content

`EDID`

Editor ID

`TRDT`

Response data: emotion type (uint32), emotion value (uint32), unused, response number, unused, sound (formid), flags, unused

`NAM1`

Response text (lstring)

`NAM2`

Actor notes (lstring)

`SNAM`

Speaker (formid)

`PNAM`

Previous INFO (formid)

`CNAM`

Conditions

### FLST — Form List[¶](#flst-form-list "Permanent link")

Field

Content

`EDID`

Editor ID

`LNAM`

FormID entry (repeated)

### GMST — Game Setting[¶](#gmst-game-setting "Permanent link")

Field

Content

`EDID`

Editor ID; first character encodes type: `i`\=int, `f`\=float, `s`\=string, `b`\=bool

`DATA`

Value, interpreted per type prefix

### KYWD — Keyword[¶](#kywd-keyword "Permanent link")

Field

Content

`EDID`

Editor ID

`CNAM`

Color (RGBA uint32)

### LAND — Landscape[¶](#land-landscape "Permanent link")

Field

Type

Content

`DATA`

uint32

Flags

`VNML`

byte\[3×33×33\]

Vertex normals (X, Y, Z bytes, one per vertex in 33×33 grid)

`VHGT`

struct

Height map: float32 offset + int8\[33×33\] deltas + 2 pad bytes

`VCLR`

byte\[3×33×33\]

Vertex colors (R, G, B, one per vertex)

`BTXT`

struct

Base layer: formid texture + uint8 quadrant + uint8 unknown + int16 layer

`ATXT`

struct

Alpha layer header: formid texture + uint8 quadrant + int16 layer

`VTXT`

struct\[\]

Alpha data for preceding ATXT layer (see below)

**LAND vertex grid:** 33×33 vertices per cell, covering a 4096-unit cell with one shared vertex per edge (adjacent cells share the border row/column).

**Height reconstruction:**

`[](#__codelineno-5-1)actual_height[row][col] = (offset + sum of deltas from [0][0] to [row][col]) * 8.0`

Deltas accumulate along rows then columns.

**VTXT format (Fallout 4 specific):**

Each entry is **8 bytes**:

`[](#__codelineno-6-1)position   uint16   — encodes row * 17 + col within a 17×17 quadrant sub-grid [](#__codelineno-6-2)unknown    uint16   — padding / unknown purpose [](#__codelineno-6-3)opacity    float32  — alpha value 0.0–1.0`

Older games (Skyrim, Oblivion) used a 6-byte layout without the float opacity. FO4 switched to float precision and added the unknown uint16 padding.

Quadrants divide the cell into NW / NE / SW / SE. Each has its own 17×17 alpha grid.

### LIGH — Light[¶](#ligh-light "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`MODL`

zstring

Model path

`DATA`

struct

Time (int32), radius (uint32), color (RGBA bytes), type flags (uint32), falloff exponent (float32), FOV (float32), near clip (float32), period (float32), intensity amplitude (float32), movement amplitude (float32)

`FNAM`

float32

Fade value

`SNAM`

formid

Sound

### LTEX — Landscape Texture[¶](#ltex-landscape-texture "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`TNAM`

formid

Texture set (→ TXST)

`MNAM`

formid

Material type

`HNAM`

struct

uint8 friction + uint8 restitution

`SNAM`

byte

Specular exponent

### NPC\_ — Non-Player Character[¶](#npc_-non-player-character "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`FULL`

lstring

Name

`RNAM`

formid

Race

`CNAM`

formid

Class

`VTCK`

formid

Voice type

`DNAM`

struct

Skill values, health/stamina/AP offsets, level, calc min/max

`ACBS`

struct

Flags, magicka/stamina/health offsets, speed/disposition/aggression

`SNAM`

struct

Faction (formid) + rank (int8), repeated per faction

`AIDT`

struct

AI data: aggression, confidence, energy, responsibility, mood, assistance

`PKID`

formid

Package (repeated per package)

`SPLO`

formid

Spell (repeated per spell)

`ITMO`

struct

Inventory item: formid + int32 count

`WNAM`

formid

Default outfit

`NAM5`

uint16

Required AV for crime

### QUST — Quest[¶](#qust-quest "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`FULL`

lstring

Name

`DNAM`

struct

Flags (uint16) + priority (uint8) + unknown (uint8) + quest type (uint32)

`INDX`

uint32

Stage index marker

`QSDT`

uint8

Stage flags

`CNAM`

lstring

Stage log text

`QOBJ`

uint16

Objective index

`NNAM`

lstring

Objective description

`ALID`

formid

Alias ID

### REFR — Placed Object Reference[¶](#refr-placed-object-reference "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID (optional)

`NAME`

formid

Base object being placed

`DATA`

struct

Position (3× float32) + Rotation (3× float32, radians)

`XSCL`

float32

Scale (default 1.0 if absent)

`XOWN`

formid

Owner

`XLCK`

int32

Lock level

`XTEL`

struct

Teleport destination (door links)

`XESP`

struct

Enable state parent

### SNDR — Sound Descriptor[¶](#sndr-sound-descriptor "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`CNAM`

formid

Sound category

`SNAM`

formid

Output model

`FNAM`

struct

Flags

`LNAM`

uint32

Loop info

`BNAM`

uint32

Echo time

`GNAM`

uint32

Loop and frequency offset

`HNAM`

struct

Unknown

`CS3P`

struct

Sound file + params (repeated per alternate)

### STAT — Static Object[¶](#stat-static-object "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`MODL`

zstring

Model path

`DNAM`

struct

Max angle (float32) + Material (formid)

`MNAM`

int32

Unknown

### TES4 — File Header[¶](#tes4-file-header "Permanent link")

*(see above)*

### TXST — Texture Set[¶](#txst-texture-set "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`TX00`

zstring

Diffuse

`TX01`

zstring

Normal / gloss

`TX02`

zstring

Environment mask / subsurface tint

`TX03`

zstring

Glow / detail map

`TX04`

zstring

Height / parallax

`TX05`

zstring

Environment

`TX06`

zstring

Multilayer / Inner layer

`TX07`

zstring

Specular / backlight

`DODT`

struct

Decal data

`DNAM`

uint16

Flags

### WEAP — Weapon[¶](#weap-weapon "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`FULL`

lstring

Name

`MODL`

zstring

Model path

`DNAM`

struct

Animation type, speed, reach, sight FOV, base damage, attack shots/sec, reload time

`DATA`

struct

Value (int32), weight (float32)

`EITM`

formid

Enchantment

`EAMT`

uint16

Enchantment amount

`INAM`

formid

Impact dataset

`WNAM`

formid

First person model

### WRLD — Worldspace[¶](#wrld-worldspace "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`FULL`

lstring

Display name

`WNAM`

formid

Parent worldspace

`PNAM`

struct

Flags + unknown

`MNAM`

struct

Map data (width, height, NW cell coords, SE cell coords)

`DATA`

uint8

Flags

`NAM0`

formid

Low-level LOD

`NAMA`

float32

Distant LOD mult

### WTHR — Weather[¶](#wthr-weather "Permanent link")

Field

Type

Content

`EDID`

zstring

Editor ID

`DNAM`

struct

Fog distances near/far (day + night)

`CNAM`

struct

Sky upper/lower colors at dawn/day/dusk/night

`NAM0`

struct

Ambient colors

`NAM1`

struct

Directional colors

`MNAM`

struct

Fog colors

`NNAM`

struct

Fog colors near/far

`PNAM`

struct

Precipitation chance

`ONAM`

formid

Precipitation

`GNAM`

formid

Visual effect

`DATA`

struct

Wind speed, cloud speed, transDelta, sunGlare, sunDamage

`SNAM`

struct

Sound entry: formid + type (uint32) (repeated)

---

## String Encoding[¶](#string-encoding "Permanent link")

All text fields use one of two encodings:

-   **zstring** — null-terminated UTF-8, embedded directly in the field
-   **lstring** — either a null-terminated UTF-8 string (in non-localized plugins), or a `uint32` string table index (when the plugin has the localization flag set in TES4). String tables live in `.STRINGS`, `.DLSTRINGS`, and `.ILSTRINGS` sidecar files.

---

## FormID Remapping[¶](#formid-remapping "Permanent link")

When a record from plugin B references a record from plugin A, the upper 8 bits of the stored FormID encode B's *load-order index* for A — not A's actual load order. Resolving references requires looking up the correct master in the TES4 `MAST` list.

Back to top

This is an unofficial fan-made technical reference.

Fallout, Fallout 4, the Creation Engine, and all related trademarks are property of Bethesda Softworks LLC and ZeniMax Media Inc.  
This site is not affiliated with, endorsed by, or sponsored by Bethesda Softworks or ZeniMax Media.  
Content licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) unless otherwise noted.  
© 2026 Julian Thomas.
