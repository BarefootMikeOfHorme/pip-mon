#!/usr/bin/env python3
"""esp_cells.py -- read CELL records out of a Bethesda plugin.

WHY THIS EXISTS
    Two concrete needs, one parser.

    1. Launching straight into a test cell needs the cell's EDITOR ID, and
       nobody has written that down. `coc <name>` wants the editor ID, not a
       FormID, so an inventory of what is actually in the plugin is the input.

    2. Placing our OWN records into someone else's plugin needs to know the
       FormID space. The TES4 header carries nextFormId; if the plugin is
       already using the range we would collide, and a colliding FormID
       silently overwrites a base record at load time. That is the single most
       destructive thing that can happen to a plugin, and it is invisible
       until the game misbehaves.

FORMAT, as implemented here
    Record  := signature(4) dataSize(u32) data[dataSize]
    GRUP    := 'GRUP' label(4) groupType(4) dataSize(u32) members[dataSize]

    A record's FormID is NOT stored in the record. It is the record's INDEX
    within its top-level group, so counting members is what produces a FormID.
    Getting that wrong yields plausible addresses for records that are not
    there, which is why every formId is recomputed from the index here rather
    than read from anywhere.

    Subrecords are 4-char signature + u32 size + payload. Only the few we
    care about (EDID, FULL, DATA) are decoded; the rest are skipped by size,
    which is the only safe way to walk an unknown subrecord stream.

HOSTILE INPUT, because G8
    A truncated file, a length that overruns, or a signature that is not
    alphabetic must all be REFUSED with a reason rather than parsed into
    confident nonsense. M12's whole lesson is that a clean negative from a
    broken search is the worst thing a tool can report.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

# Top-level group types we care about. 0x01 is CELL in most Bethesda games;
# both are accepted because a wrong assumption here reads as "no cells", which
# is indistinguishable from a plugin with none.
CELL_GROUPS = {0x00, 0x01, 0x02}


class Malformed(Exception):
    """Raised rather than returned, so a broken file cannot look like an empty one."""


def _u32(d: bytes, off: int) -> int:
    if off + 4 > len(d):
        raise Malformed(f"u32 at {off} overruns {len(d)} B")
    return struct.unpack_from("<I", d, off)[0]


def _sig(d: bytes, off: int) -> str:
    """Read a 4-character group/record signature, or refuse.

    The character class is UPPERCASE ALPHANUMERIC, not alphabetic. The plugin
    magic is 'TES4' -- it contains a digit -- so an isalpha() guard rejects
    every valid plugin and reports it as malformed. That is the M12 shape from
    the other end: a validator that fails closed on honest input, which teaches
    its readers to ignore it.
    """
    if off + 4 > len(d):
        raise Malformed(f"signature at {off} overruns {len(d)} B")
    raw = d[off : off + 4]
    if not (raw.isalnum() and raw.isupper()):
        raise Malformed(f"bad signature {raw!r} at {off}")
    return raw.decode("ascii")


def read_tes4(data: bytes) -> dict[str, object]:
    """The plugin header. The only part with a fixed, documented layout."""
    if _sig(data, 0) != "TES4":
        raise Malformed(f"not a plugin: {_sig(data, 0)}")
    size = _u32(data, 4)
    if 8 + size > len(data):
        raise Malformed(f"TES4 claims {size} B, file holds {len(data) - 8} B")
    out: dict[str, object] = {"masters": [], "description": None,
                              "nextFormId": None, "recordCount": None}
    # The TES4 data block opens with FOUR u32 fields before any subrecord, so
    # the first subrecord signature sits at offset 24 -- not 12. Measured
    # against two independent plugins (an .esp and an .esm) which agree exactly:
    # flags, two reserved, then 0x83, then HEDR. Guessing 12 parses nothing and
    # reports it as a plugin with no cells, which is a lie with a confident tone.
    pos = 8 + 16
    end = 8 + size
    while pos + 8 <= end:
        sig = _sig(data, pos)
        sub_size = _u32(data, pos + 4)
        if pos + 8 + sub_size > end:
            raise Malformed(f"subrecord {sig} at {pos} overruns the TES4 body")
        payload = data[pos + 8 : pos + 8 + sub_size]
        if sig == "ONAM":
            out["masters"] = [p.decode("ascii", "replace") for p in payload.split(b"\0") if p]
        elif sig == "CNAM":
            out["description"] = payload.rstrip(b"\0").decode("utf-8", "replace")
        elif sig == "HEDR" and sub_size >= 12:
            count, nxt, _ = struct.unpack_from("<IIB", payload, 0)
            out["recordCount"] = count
            out["nextFormId"] = nxt
        pos += 8 + sub_size
    return out


def _subrecords(body: bytes) -> dict[str, bytes]:
    """First occurrence of each subrecord signature. Duplicates are ignored on
    purpose: the alternative is a last-wins rule that quietly depends on order."""
    out: dict[str, bytes] = {}
    pos = 0
    while pos + 8 <= len(body):
        raw = body[pos : pos + 4]
        if not (raw.isalpha() and raw.isupper()):
            break
        size = struct.unpack_from("<I", body, pos + 4)[0]
        if pos + 8 + size > len(body):
            break
        out.setdefault(raw.decode("ascii"), body[pos + 8 : pos + 8 + size])
        pos += 8 + size
    return out


def read_cells(data: bytes) -> list[dict[str, object]]:
    """Every CELL record, with its FormID recomputed from its group index."""
    cells: list[dict[str, object]] = []
    pos = 8 + _u32(data, 4)
    end = len(data)
    while pos + 24 <= end:
        if _sig(data, pos) != "GRUP":
            break
        label = _u32(data, pos + 4)
        size = _u32(data, pos + 12)
        if pos + 24 + size > end:
            raise Malformed(f"GRUP at {pos} claims {size} B, overruns the file")
        if label in CELL_GROUPS:
            inner = pos + 24
            stop = inner + size
            index = 0
            while inner + 8 <= stop:
                sig = _sig(data, inner)
                rsize = _u32(data, inner + 4)
                if inner + 8 + rsize > stop:
                    raise Malformed(f"record {sig} at {inner} overruns its GRUP")
                if sig == "CELL":
                    # formVersion(4) lastModified(8) flags(1) then subrecords
                    subs = _subrecords(data[inner + 13 : inner + 8 + rsize])
                    edid = subs.get("EDID", b"").rstrip(b"\0").decode("utf-8", "replace")
                    full = subs.get("FULL", b"").rstrip(b"\0").decode("utf-8", "replace")
                    cells.append({
                        "formId": (label << 24) | index,
                        "edid": edid,
                        "name": full,
                        "groupType": label,
                    })
                inner += 8 + rsize
                index += 1
        pos += 24 + size
    return cells


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="esp_cells.py",
        description="List CELL records and the FormID space of a Bethesda plugin.",
    )
    p.add_argument("plugin", type=Path)
    p.add_argument("--full", action="store_true", help="print every cell, not just named ones")
    args = p.parse_args(argv)

    try:
        data = args.plugin.read_bytes()
    except OSError as exc:
        print(f"cannot read {args.plugin}: {exc}", file=sys.stderr)
        return 2

    try:
        head = read_tes4(data)
        cells = read_cells(data)
    except Malformed as exc:
        # Refuse loudly. A partially-parsed plugin reported as a short list is
        # the exact shape that gets mistaken for "this mod has no cells".
        print(f"MALFORMED {args.plugin.name}: {exc}", file=sys.stderr)
        return 2

    print(f"=== {args.plugin.name}  ({len(data):,} B) ===")
    print(f"  description : {head['description']}")
    print(f"  masters     : {', '.join(str(m) for m in head['masters']) or '(none)'}")
    print(f"  recordCount : {head['recordCount']}")
    nxt = head["nextFormId"]
    print(f"  nextFormId  : 0x{nxt:08X}" if nxt is not None else "  nextFormId  : ?")
    print(f"  CELL records: {len(cells)}")
    print()

    named = [c for c in cells if c["edid"]]
    print(f"  {'FormID':<10} {'EditorID':<44} Name")
    print("  " + "-" * 96)
    for c in cells:
        if not c["edid"] and not args.full:
            continue
        print(f"  0x{c['formId']:08X}  {c['edid']:<44} {c['name']}")

    if not named:
        print("\n  no editor IDs found -- nothing is coc-able by name")
    else:
        print("\n  coc targets (editor ID is what -coc wants):")
        for c in named[:12]:
            print(f"    Fallout4.exe -coc {c['edid']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
