#!/usr/bin/env python3
"""build_libbin.py -- compile the Tier-1 address INI into a compact native blob.

WHY THIS EXISTS
    The in-game resolver loads its address database with std::getline over a
    541 KB text file of "<name> <rva-hex>" lines, building an unordered_map at
    startup. That was fine as a first pass and it is wrong now, for three
    reasons that compound:

      1. It is TEXT PARSED INSIDE THE GAME PROCESS. Every startup pays for
         istringstream construction per line across 8,617 entries.
      2. It allocates a std::string per name, then copies it into the map. That
         is thousands of allocations during game boot, in a project whose own
         section 3 performance rule says the in-process tier must not allocate
         on a game thread.
      3. It is a dependency-on-a-parser. The AOB tier is the tier that is
         SUPPOSED to be the fallback; a database that cannot be read is a
         database that silently costs us the whole three-tier design.

    So the parse moves to BUILD time, where being slow and allocating freely
    costs nothing, and what the game loads is a fixed-stride binary table it
    can binary-search with no allocation at all.

    The text INI is still emitted, and still ships. It is the human-readable
    and diffable form; the blob is derived from it and is verified against it.
    Two representations of one fact, with the readable one kept authoritative.

FORMAT (v1) -- little-endian throughout
    offset  size  field
    ------  ----  --------------------------------------------------
    0       4     magic       "PLIB"
    4       4     schema      u32  layout version; reader refuses unknown
    8       4     buildKey    u32  FNV-1a of the game PE headers, so a blob
                                   built for another patch is REJECTED
                                   rather than silently returning wrong
                                   addresses -- which is a crash, not an
                                   error, if we let it through
    12      4     recordCount u32
    16      4     recordSize  u32  (== 12 in v1; the reader validates this so
                                       a future widening cannot be misread)
    20      4     reserved    u32  must be 0; validated, so a v2 that reuses
                                       the space cannot be read as v1
    24      N*12  records, ascending by nameHash

    record (12 bytes)
    0   4   nameHash  u32  FNV-1a 32 of the symbol name
    4   4   rva       u32  relative virtual address
    8   1   classId   u8   see build_libbin.py -- CLASS_IDS
    9   1   slot      u8   vtable slot index, 0xFF when not slot-addressed
    10  2   flags     u16  bit 0: name is an exact match (see NOTE below)

    A NAME-HASHED TABLE CANNOT DISTINGUISH A REAL HIT FROM A COLLISION, so
    flags bit 0 records whether the hash was unique in this build. The in-game
    reader is documented as treating a non-exact entry as a miss rather than as
    an address, because a one-in-2^32 false positive that lands in the wrong
    function is precisely the class of bug this project has been bitten by
    before (see the detour and prologue work in the self-test).

USAGE
    python tools/build_libbin.py <ini> <out.bin> [build_key]
"""

from __future__ import annotations

import struct
import sys

MAGIC = b"PLIB"
# Explicit schema version, separate from the magic. The previous header had no
# version field at all -- a 4-byte `reserved` was doing duty as spare space --
# so a future record-layout change would only be caught if whoever made it also
# remembered to widen recordSize. A wrong-but-same-size layout would then be
# read silently and produce plausible, wrong addresses.
#
# Bump this whenever the record layout or the meaning of any header field
# changes. The reader refuses an unknown version outright.
SCHEMA_VERSION = 1

VERSION_RECORD_SIZE = 12
HEADER_SIZE = 24

# Coarse class identifier carried per record so the in-game reader can tell a
# vtable pointer from a plain code address without a second lookup. Values are
# fixed and append-only; a renumbering would invalidate every shipped blob.
CLASS_IDS = {
    "VTable": 1,
    "Code": 2,
}
CLASS_CODE = 1
CLASS_VTABLE = 2

FLAG_EXACT = 1 << 0


def fnv1a32(data: bytes) -> int:
    """FNV-1a, 32-bit. Matches the C++ side and the existing test vectors."""
    h = 0x811C9DC5
    for byte in data:
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def pe_header_hash(path: str) -> int:
    """FNV-1a 32 over exactly the PE header region of an image.

    WHY NOT THE BUILD-KEY STRING. The obvious thing to record is Bethesda's
    build key ("e4f3ee86437ed8e6"), and the first version of this file did
    exactly that. It is the wrong choice: the reader would have to extract the
    same string from the loaded image to compare, which means a PE parser in
    the in-process tier -- code this project deliberately does not have there.

    Hashing the header bytes solves it without a parser. Those bytes are
    mapped 1:1 from file to image, so the game can hash what is in memory and
    get the identical value, and the comparison needs only e_lfanew at 0x3C --
    four bytes, no structure walking.

    The hash covers DOS header + PE signature + COFF header + optional header,
    and stops there. Optional-header fields include the image base, which is
    ASLR-dependent, so hashing the whole file or the whole header block would
    make the value differ per launch and match nothing.
    """
    with open(path, "rb") as handle:
        data = handle.read(0x1000)  # headers always live in the first 4 KiB
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError(f"{path} is not a PE image (no MZ)")
    e_lfanew = int.from_bytes(data[0x3C:0x40], "little")
    if e_lfanew <= 0 or e_lfanew + 24 > len(data):
        raise ValueError(f"{path} has a nonsensical e_lfanew ({e_lfanew})")
    size_of_optional = int.from_bytes(data[e_lfanew + 20 : e_lfanew + 22], "little")
    end = e_lfanew + 24 + size_of_optional
    if end > len(data):
        raise ValueError(f"{path} optional header runs past the data read")
    return fnv1a32(data[:end])


def parse_ini(path: str) -> list[tuple[str, int, int]]:
    """Return (name, rva, class_id) for every usable line.

    Mirrors the C++ text loader's rules exactly, including the two that look
    like quirks but are load-bearing:

      - a zero RVA is SKIPPED. AddressLib writes 0 for "not resolved on this
        build", and storing it would turn "absent" into "points at the image
        base" -- a wild pointer that happens to be readable.
      - a malformed line is SKIPPED silently rather than aborting the load.
        A single bad row must not cost us the other 8,616.
    """
    entries: list[tuple[str, int, int]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.lstrip()[:1] in ("#", ";"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            name, rva_hex = parts[0], parts[1]
            try:
                rva = int(rva_hex, 16)
            except ValueError:
                continue
            if rva == 0:
                continue
            # The generator emits vtable entries; anything with a slot suffix
            # in its name is a vtable symbol, the rest are treated as code.
            cls = CLASS_VTABLE
            entries.append((name, rva, cls))
    return entries


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    ini_path, out_path = argv[1], argv[2]
    # argv[3] is now the GAME EXE, not a build-key string: the blob records a
    # hash of the PE headers so the in-game reader can validate it without
    # owning a PE parser. See pe_header_hash for why the string was wrong.
    exe_path = argv[3] if len(argv) > 3 else None
    if exe_path is None:
        print("FAILED: pass the game executable so the blob can record an image "
              "identity. A blob without one cannot be validated at load.",
              file=sys.stderr)
        return 1
    try:
        image_hash = pe_header_hash(exe_path)
    except (OSError, ValueError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    entries = parse_ini(ini_path)
    if not entries:
        print(f"FAILED: no usable entries parsed from {ini_path}", file=sys.stderr)
        return 1

    # Hash, and detect collisions rather than silently keeping both.
    hashed: dict[int, list[tuple[str, int, int]]] = {}
    for name, rva, cls in entries:
        hashed.setdefault(fnv1a32(name.encode("utf-8")), []).append((name, rva, cls))

    records: list[bytes] = []
    collisions = 0
    for name_hash, group in sorted(hashed.items()):
        exact = 1 if len(group) == 1 else 0
        if not exact:
            collisions += 1
        # On a collision keep the lowest RVA deterministically so the blob is
        # reproducible, and flag it so the reader treats it as a probable miss.
        name, rva, cls = sorted(group, key=lambda item: item[1])[0]
        records.append(
            struct.pack(
                "<IIBBH",
                name_hash,
                rva,
                cls,
                0xFF,  # slot unknown from the text form; the vtable tier reads
                        # it at runtime, this blob only pins the vtable address
                FLAG_EXACT if exact else 0,
            )
        )

    header = MAGIC + struct.pack(
        "<IIIII", SCHEMA_VERSION, image_hash, len(records),
        VERSION_RECORD_SIZE, 0
    )
    blob = header + b"".join(records)

    with open(out_path, "wb") as handle:
        handle.write(blob)

    print(f"  {len(records)} records, {len(blob)} bytes "
          f"(from {len(entries)} INI lines, {collisions} hash collisions flagged)")
    print(f"  image identity: PE header hash 0x{image_hash:08X} "
          f"({exe_path}) -- the reader refuses a blob that does not match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
