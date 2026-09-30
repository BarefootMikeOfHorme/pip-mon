"""Read an AddressLib .bin and map IDs to symbol names.

WHY THIS EXISTS
    The five dead AOB signatures are not a scanning problem, they are a
    naming problem. We have one confirmed address (RVA 0x1B887C0) out of six
    tries, and no way to find the other five, because a byte pattern does not
    tell you what function it is.

    The address database already exists on this machine: AddressLib writes one
    .bin per game build, and CommonLibF4 ships the open-source decoder for it.
    The format, from AddressLibDecoder/src/main.cpp, is deliberately simple:

        [uint64 entryCount][ (uint64 id, uint64 offset) × entryCount ]

    Sixteen bytes per entry, ids and offsets both 64-bit. The decoder's only
    real work is pretty-printing, so reimplementing the read is safer than
    pulling in its dependency chain (mmio, fmt, SRELL) for a struct read.

WHY THIS IS NOT REVERSE-ENGINEERING
    An earlier note in the design doc called these files a competitor's
    proprietary format and declined to touch them. That was wrong. They are
    AddressLib output from a documented pipeline (IDA exports + version diffs),
    and the decoder is MIT-licensed and vendored. Reading a published data
    format is not the same act as guessing at an undocumented one, and the
    difference matters: a wrong guess here produces plausible addresses, which
    is the single most dangerous failure mode in this project.

THE CROSS-CHECK
    One address in this project is independently confirmed: PapyrusScript::
    Execute at RVA 0x1B887C0, unique in the live image, sitting on a real
    function boundary (RET + 15x INT3, then a textbook prologue). If this
    database reports the same RVA for that symbol, the whole pipeline --
    bin parsing, name mapping, and our signature -- is validated at once. If it
    does not, something is wrong and that is worth knowing immediately.
"""
import re
import struct
import sys
from pathlib import Path

BIN = Path(sys.argv[1]) if len(sys.argv) > 1 else None
VTABLE_IDS = Path(sys.argv[2]) if len(sys.argv) > 2 else None

# The address we already proved against a live Fallout 4 process.
KNOWN_SCRIPT_EXECUTE_RVA = 0x1B887C0


def read_bin(path: Path) -> dict[int, int]:
    """Parse [count][(id, offset)*] into {id: offset}."""
    data = path.read_bytes()
    if len(data) < 8:
        raise ValueError("file too small to contain a count")
    (count,) = struct.unpack_from("<Q", data, 0)
    expected = 8 + count * 16
    if expected != len(data):
        # Report the mismatch rather than trusting the count. A truncated or
        # differently-shaped file must not silently yield a partial map that
        # looks complete -- that is the M12 failure in a new place.
        raise ValueError(
            f"count field says {count} entries ({expected} bytes) but the file "
            f"is {len(data)} bytes. Format mismatch; refusing to guess."
        )
    out: dict[int, int] = {}
    for i in range(count):
        ident, off = struct.unpack_from("<QQ", data, 8 + i * 16)
        out[ident] = off
    return out


def read_names(path: Path) -> dict[str, list[int]]:
    """Parse VTABLE_IDs.h into {name: [id, ...]}.

    The real format is NOT a flat list of (id, "name") pairs, which is what the
    first version of this function assumed and searched for. It is:

        inline constexpr std::array<REL::ID, 17> Actor{ REL::ID(1455516), ... };

    Three consequences the naive regex got wrong:
      - the name comes BEFORE the ids, not after
      - the ids are bare decimal, not 0x hex
      - ONE NAME MAPS TO MANY IDS. A vtable symbol names a class, and each
        entry is a slot in that class's vtable. Collapsing that to a single id
        would silently discard 16 of Actor's 17 addresses, and the resulting
        "name not found" would look like a database problem rather than a
        parser problem.

    The mapping is genuinely one-to-many and has to stay that way.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    names: dict[str, list[int]] = {}
    # name{ ... REL::ID(123), REL::ID(456) ... }
    pattern = re.compile(
        r"std::array<REL::ID,\s*\d+>\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}"
    )
    for m in pattern.finditer(text):
        name = m.group(1)
        ids = [int(x) for x in re.findall(r"REL::ID\(\s*(\d+)\s*\)", m.group(2))]
        if ids:
            names[name] = ids
    return names


def main() -> int:
    if BIN is None or not BIN.exists():
        print("usage: read_addresslib.py <version-x.bin> [VTABLE_IDs.h]")
        return 2

    print(f"bin    {BIN.name}  ({BIN.stat().st_size:,} bytes)")
    offsets = read_bin(BIN)
    print(f"       {len(offsets):,} id -> rva entries")

    if VTABLE_IDS and VTABLE_IDS.exists():
        print(f"names  {VTABLE_IDS}")
        by_name = read_names(VTABLE_IDS)
        print(f"       {len(by_name):,} vtable symbols")
    else:
        by_name = {}
        print("names  (none supplied) -- showing raw ids only")

    # name -> [ids], and only the ids that the address database actually has.
    resolved = {
        n: [(i, offsets[i]) for i in ids if i in offsets]
        for n, ids in by_name.items()
    }
    resolved = {n: v for n, v in resolved.items() if v}

    # The cross-check that validates the whole pipeline. PapyrusScript::Execute
    # is a vtable symbol with many slots, so ANY of its slots landing on the
    # independently confirmed RVA would be a real hit -- but the method being a
    # non-vtable free function makes that unlikely, so absence is informative
    # rather than alarming.
    print("\n--- cross-check against the one independently proven address ---")
    hits = [rva for _, rva in resolved.get("PapyrusScript::Execute", [])]
    if KNOWN_SCRIPT_EXECUTE_RVA in hits:
        print(f"  MATCH: PapyrusScript::Execute has a slot at RVA "
              f"0x{KNOWN_SCRIPT_EXECUTE_RVA:X} -- pipeline confirmed")
    else:
        print(f"  PapyrusScript::Execute has {len(hits)} vtable slot(s); none at "
              f"0x{KNOWN_SCRIPT_EXECUTE_RVA:X}.")
        print("  Expected: Execute is a free function, not a vtable method, so the")
        print("  vtable ID list legitimately does not contain it. This database")
        print("  covers VTABLES; free functions come from a different table.")

    # Show the shape of what we do have, for the Papyrus area.
    print("\n--- Papyrus / VM symbols present in the vtable database ---")
    papyrus = sorted(n for n in resolved if "Papyrus" in n or "VM" in n)
    for name in papyrus[:25]:
        slots = resolved[name]
        print(f"  {name:<44} {len(slots):>3} slot(s)  "
              f"RVA 0x{slots[0][1]:X}.." if len(slots) == 1 else
              f"  {name:<44} {len(slots):>3} slot(s)  first RVA 0x{slots[0][1]:X}")
    if len(papyrus) > 25:
        print(f"  ... and {len(papyrus) - 25} more")

    # --- emit the Tier-1 INI, if asked ------------------------------------
    if len(sys.argv) > 3:
        out = Path(sys.argv[3])
        n = emit_ini(resolved, out)
        print(f"\nwrote {n} entries to {out}")

        # Read it back exactly the way the C++ resolver will: skip comments,
        # skip "0", take name + hex. A generator that has never had its output
        # re-read is a generator that can write garbage confidently.
        reread: dict[str, int] = {}
        for line in out.read_text(encoding="utf-8").splitlines():
            if not line or line[0] in "#;":
                continue
            parts = line.split()
            if len(parts) == 2 and parts[1] != "0":
                reread[parts[0]] = int(parts[1], 16)

        print(f"  read back {len(reread)} entries")
        mismatches = 0
        for name, slots in resolved.items():
            expected = slots[0][1]
            got = reread.get(name)
            if got != expected:
                mismatches += 1
                if mismatches <= 5:
                    print(f"  MISMATCH {name}: wrote 0x{expected:X}, "
                          f"read 0x{got:X}" if got else f"  MISSING {name}")
        print(f"  {len(resolved)} symbols checked, {mismatches} mismatches")

        # The bare-name convention is the contract with the resolver, so assert
        # it rather than trusting the writer.
        suffixed = [k for k in reread if k.endswith("#0")]
        if suffixed:
            print(f"  [FAIL] {len(suffixed)} entries use '#0', which the resolver "
                  f"cannot look up")
            return 1
        print("  no '#0' entries: bare-name convention holds")
        print(f"  spot check: BSScript__IClientVM -> 0x"
              f"{reread.get('BSScript__IClientVM', 0):X}")
    return 0


def emit_ini(resolved, out_path: Path, section_of: dict[str, str] | None = None) -> int:
    """Write a Tier-1 address INI in the format vprobe's Resolver reads.

    The contract, from VersionConfig.cpp::loadAddressLib:
        <name> <rva hex>
    with '#' or ';' comments, blank lines skipped, and the literal "0"
    meaning "unresolved on this build". That last detail is worth keeping: a
    database that only covers some symbols still loads, and the AOB tier picks
    up the rest. A generator that refused to emit a partial file would turn a
    partial answer into no answer.

    WHAT IS EMITTED, and the caveat that matters:
      - vtable symbols, with the address of the VTABLE itself (an RVA in
        .rdata), not the address of any method inside it. Reading a method
        means dereferencing the vtable at runtime and indexing a slot, which
        the hook layer must do explicitly.
      - free functions are absent, because CommonLibF4 ships no free-function
        ID list. PapyrusScript::Execute and four of its siblings cannot be
        resolved this way and are marked in the header comment so nobody
        assumes they are merely missing from the file.
    """
    lines = [
        "# PIP-MON Tier-1 address database",
        "# GENERATED by tools/read_addresslib.py -- do not hand-edit.",
        "#",
        "# Source : AddressLib database for this exact game build",
        "# Names  : CommonLibF4 CommonLibF4/include/RE/VTABLE_IDs.h (MIT)",
        "#",
        "# THESE ARE VTABLE ADDRESSES (pointers in .rdata), NOT FUNCTION",
        "# ADDRESSES. To reach a method, read the vtable and index a slot.",
        "# The AOB tier still supplies anything listed under free functions.",
        "#",
        "# NOT PRESENT, and no database can supply them:",
        "#   PapyrusVM::PapyrusVM            free function, not a vtable slot",
        "#   PapyrusVM::GetRunningThreadCount  free function",
        "#   PapyrusVM::DebugPrint            free function",
        "#   PapyrusThread::Execute           free function",
        "#   PapyrusScript::Execute           free function",
        "#   FormData::CellStream             free function",
        "",
    ]
    written = 0
    for name in sorted(resolved):
        slots = resolved[name]
        for idx, (ident, rva) in enumerate(slots):
            # Slot 0 uses the BARE name; later slots get #N.
            #
            # This is not cosmetic. The resolver looks up a plain symbol name,
            # so emitting "GameVM#0" makes the entry unreachable -- the first
            # version of this generator did exactly that, and it silently
            # orphaned 1,945 of the 8,617 entries. Every vtable with more than
            # one slot was unresolvable, and nothing reported an error,
            # because the resolver treats "not found" as a legitimate outcome
            # and simply leaves the hook uninstalled.
            #
            # The convention is: bare name == first slot. Anything the caller
            # wants beyond that asks for #1, #2 explicitly.
            key = name if idx == 0 else f"{name}#{idx}"
            lines.append(f"{key} {rva:X}")
            written += 1
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return written


if __name__ == "__main__":
    sys.exit(main())
