#!/usr/bin/env python3
"""make_empty_esp.py -- write a minimal, VALID Fallout 4 plugin.

WHY THIS EXISTS
    The headless generation route needs an existing plugin to write into, and
    xEdit will not create one: passing a non-existent .esp on the command line
    makes it hang until it is killed, and no file appears. That was measured,
    not assumed.

    So we write the smallest thing xEdit will accept, and let the script do the
    rest. "Smallest valid" is doing real work in that sentence -- a Bethesda
    plugin is a TES4 record followed by GRUP records, and the header carries
    fields the editor reads before it will show anything.

WHY IT IS A SCRIPT AND NOT A BYTE BLOB
    The layout is a documented format, not an implementation, and a hardcoded
    60-byte literal in a source file is indistinguishable from a magic number
    that rots. Everything here is derived and commented, and the output is
    verified by a re-parse rather than trusted because it was written.

THE FORMAT
    Record := signature(4) dataSize(4) data[dataSize]

    TES4 is special: its data begins with a 4-byte flags field, and the
    subrecords follow. Getting that offset wrong yields an empty parse rather
    than an error, which is exactly the silent-failure shape this project
    treats as its worst outcome -- hence the self-check at the bottom.

      HEDR  12 B  u32 recordCount, u32 nextFormId, u8 groupType, u8 pad[3]
      ONAM   n B  the master list, NUL-terminated, NUL-terminated again
      CNAM   n B  description, free text
      SNAM   n B  version, free text
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

TES4_MAGIC = b"TES4"
# 0x0001 = ESM. An .esp leaves this zero, which is the only structural
# difference between an .esm and an .esp header.
FLAG_ESM = 0x0001

# 0x83 = 131. The record version both Fallout4.esm and a Creation Kit plugin
# carry, measured rather than recalled.
RECORD_VERSION = 0x83

# The editor treats 0x800 as "this plugin has allocated nothing yet" and starts
# handing out IDs from there. 0x6D is the vanilla next free ID in some builds,
# which is precisely why it is not used here: a plugin that collides with
# vanilla's range is a plugin whose records overwrite base records.
DEFAULT_NEXT_FORM_ID = 0x800


def _subrecord(sig: bytes, payload: bytes) -> bytes:
    return sig + struct.pack("<I", len(payload)) + payload


def _tes4(masters: list[str], description: str, version: str, next_form_id: int) -> bytes:
    hedr = struct.pack("<IIB", 0, next_form_id, 0) + b"\0\0\0"
    onam = b"".join(m.encode("ascii") + b"\0" for m in masters) + b"\0"
    subrecords = (
        _subrecord(b"HEDR", hedr)
        + _subrecord(b"ONAM", onam)
        + _subrecord(b"CNAM", description.encode("ascii", "replace") + b"\0")
        + _subrecord(b"SNAM", version.encode("ascii", "replace") + b"\0")
    )
    # THE 16-BYTE PROLOGUE, and why it is not optional.
    # Measured against two real files -- Fallout4.esm and a plugin the Creation
    # Kit wrote minutes earlier -- both carry, between the record's dataSize
    # field and its first subrecord:
    #
    #     flags(4)   0x81 on an .esm, 0x00 on an .esp
    #     zero(4)
    #     zero(4)
    #     version(4) 0x83 = 131 for this game
    #
    # and both declare a dataSize that COUNTS ONLY THE SUBRECORDS, excluding
    # all sixteen prologue bytes. An earlier version of this tool wrote flags
    # and then went straight to HEDR, which is a header no Bethesda tool ever
    # produces. It read back fine through this tool's own parser, which is
    # exactly how a wrong artefact passes its own test.
    prologue = struct.pack("<IIII", 0, 0, 0, RECORD_VERSION)
    return TES4_MAGIC + struct.pack("<I", len(subrecords)) + prologue + subrecords


def parse_tes4(data: bytes) -> dict[str, object]:
    """Read back what we wrote. A writer that never verifies is a rumour."""
    if data[:4] != TES4_MAGIC:
        raise ValueError(f"not a plugin: magic {data[:4]!r}")
    size = struct.unpack_from("<I", data, 4)[0]
    # dataSize counts the subrecords only; the RECORD HEADER sits between the
    # size field and the first subrecord and is NOT counted.
    #
    # MEASURED, not assumed. Decoding the installed 66-byte plugin: TES4 at
    # 0x00, dataSize=42 at 0x04, version=131 at 0x14 -- and 24 + 42 = 66, the
    # exact file size. The 16-byte prologue this used to assume was wrong, and
    # fopdoc independently documents a 24-byte record header (type, dataSize,
    # flags, formid, revision, version, unknown). Corrected against a
    # measurement rather than against a wiki, because a wiki is a claim about
    # the engine and this is the engine's own output.
    prologue = 24
    # The body starts AT the end of the header, not 8 bytes past it. type and
    # dataSize live INSIDE the 24-byte record header, so adding 8 first was an
    # off-by-eight that only surfaced once the prologue was measured rather
    # than guessed: the installed 66-byte plugin declares 42 and is 24+42.
    end = prologue + size
    if end > len(data):
        raise ValueError(f"TES4 claims {size} B of subrecords, file holds {len(data) - prologue} B")
    body = data[prologue:end]
    out: dict[str, object] = {"masters": [], "description": None, "version": None,
                              "nextFormId": None, "recordCount": None, "subrecords": []}
    pos = 0
    while pos + 8 <= len(body):
        sig = body[pos : pos + 4]
        if not (sig.isalpha() and sig.isupper()):
            break
        sub_size = struct.unpack_from("<I", body, pos + 4)[0]
        payload = body[pos + 8 : pos + 8 + sub_size]
        out["subrecords"].append(sig.decode("ascii"))
        if sig == b"ONAM":
            out["masters"] = [p.decode("ascii") for p in payload.split(b"\0") if p]
        elif sig == b"CNAM":
            out["description"] = payload.rstrip(b"\0").decode("ascii", "replace")
        elif sig == b"SNAM":
            out["version"] = payload.rstrip(b"\0").decode("ascii", "replace")
        elif sig == b"HEDR" and sub_size >= 12:
            count, nxt, _grp = struct.unpack_from("<IIB", payload, 0)
            out["recordCount"] = count
            out["nextFormId"] = nxt
        pos += 8 + sub_size
    return out


def build(masters: list[str], description: str, version: str, next_form_id: int) -> bytes:
    return _tes4(masters, description, version, next_form_id)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="make_empty_esp.py",
        description="Write a minimal valid Fallout 4 plugin for xEdit to populate.",
    )
    p.add_argument("out", type=Path, help="path to write, e.g. PipMonTestFacility.esp")
    p.add_argument("--master", action="append", default=None,
                   help="master file, repeatable (default: Fallout4.esm)")
    p.add_argument("--description", default="PIP-MON test facility")
    p.add_argument("--version", default="1.0")
    p.add_argument("--next-form-id", type=lambda s: int(s, 0), default=DEFAULT_NEXT_FORM_ID)
    p.add_argument("--force", action="store_true",
                   help="overwrite an existing file; without it an existing file is refused")
    args = p.parse_args(argv)

    if args.out.exists() and not args.force:
        print(f"refusing to overwrite {args.out} (pass --force)", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)

    masters = args.master or ["Fallout4.esm"]
    data = build(masters, args.description, args.version, args.next_form_id)

    # Verify before writing, not after. A file that exists but is wrong is worse
    # than no file, because the next stage will read it and believe it.
    info = parse_tes4(data)
    if info["masters"] != masters:
        print(f"self-check FAILED: masters read back as {info['masters']}", file=sys.stderr)
        return 2
    if info["nextFormId"] != args.next_form_id:
        print(f"self-check FAILED: nextFormId read back as {info['nextFormId']}", file=sys.stderr)
        return 2
    if not info["subrecords"]:
        print("self-check FAILED: no subrecords parsed", file=sys.stderr)
        return 2

    args.out.write_bytes(data)
    print(f"wrote {args.out}  {len(data)} B")
    print(f"  subrecords : {' '.join(info['subrecords'])}")
    print(f"  masters    : {', '.join(str(m) for m in info['masters'])}")
    print(f"  nextFormId : 0x{info['nextFormId']:08X}")
    print(f"  description: {info['description']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
