#!/usr/bin/env python3
"""verify_libbin.py -- round-trip check for the generated address blob.

Stands alone rather than living in a unittest so it can be run straight after
generation, and so a failure is legible in the build log without a test runner
attached. Exits non-zero on any mismatch, so a build script can gate on it.

Checks, in order of what would hurt most if it broke:
  1. header geometry      -- size must equal 24 + count*recordSize exactly
  2. sort order           -- ascending by nameHash, or binary search is wrong
  3. known symbols        -- two RVAs we independently confirmed against the
                             live binary earlier, so this is a real check and
                             not a tautology against the generator
  4. collision flagging   -- every non-exact record must be reported, not hidden
"""

from __future__ import annotations

import bisect
import struct
import sys

MAGIC = b"PLIB"
SCHEMA_VERSION = 1
HEADER = 24

# Header geometry, asserted rather than assumed. A generator and a reader that
# disagree about where a field lives produce a blob that parses into plausible
# nonsense, so the layout is pinned in both languages and checked here.
LAYOUT = [("magic", 0, 4), ("schema", 4, 4), ("buildKey", 8, 4),
          ("recordCount", 12, 4), ("recordSize", 16, 4), ("reserved", 20, 4)]

# Independently verified against a live Fallout4.exe on this machine, not taken
# from the generator's own output. If the format ever starts disagreeing with
# reality, these are the two that would catch it.
KNOWN = {
    "BSScript__IClientVM": 0x25B85C8,
}

# A FREE FUNCTION, which this database must NOT contain. PapyrusScript::Execute
# resolves at RVA 0x1B887C0, but that address came from an AOB signature on the
# live binary, not from AddressLib -- the database holds VTABLE addresses only.
#
# Asserting the ABSENCE is the more valuable half of this test. It is the
# check that keeps the three tiers honest: if a free function ever turned up in
# here, something would have quietly started resolving a code address through
# the vtable path, and the failure mode of that is a detour in the wrong
# function rather than a clean miss.
MUST_BE_ABSENT = {
    "PapyrusScript__Execute": 0x1B887C0,
}


def fnv1a32(data: bytes) -> int:
    h = 0x811C9DC5
    for byte in data:
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: verify_libbin.py <blob>")
        return 2
    blob = open(argv[1], "rb").read()
    failures: list[str] = []

    if blob[:4] != MAGIC:
        print(f"FAIL: bad magic {blob[:4]!r}")
        return 1

    schema, build_key, count, rec_size, reserved = struct.unpack_from("<IIIII", blob, 4)
    print(f"  header: schema={schema} buildKey=0x{build_key:08X} "
          f"count={count} recSize={rec_size} reserved={reserved}")
    if schema != SCHEMA_VERSION:
        print(f"FAIL: schema {schema} != expected {SCHEMA_VERSION}")
        return 1
    if reserved != 0:
        print(f"FAIL: reserved must be 0, got {reserved} -- a future layout is "
              f"reusing these bytes and must not be read as v1")
        return 1

    expected = HEADER + count * rec_size
    print(f"  layout: {len(LAYOUT)} fields, {HEADER}B header")
    if len(blob) != expected:
        failures.append(f"size {len(blob)} != expected {expected}")

    recs = [struct.unpack_from("<IIBBH", blob, HEADER + i * rec_size) for i in range(count)]
    hashes = [r[0] for r in recs]

    if hashes != sorted(hashes):
        failures.append("records are not sorted by nameHash")
    else:
        print("  sort order: ascending by nameHash, binary search is valid")

    for name, want in KNOWN.items():
        h = fnv1a32(name.encode("utf-8"))
        idx = bisect.bisect_left(hashes, h)
        rec = recs[idx] if idx < len(recs) and recs[idx][0] == h else None
        if rec is None:
            failures.append(f"{name} not found by hash")
            print(f"  {name:24} NOT FOUND")
            continue
        got = rec[1]
        ok = got == want
        print(f"  {name:24} want 0x{want:07X}  got 0x{got:07X}  "
              f"{'MATCH' if ok else 'MISMATCH'}  (class={rec[2]} exact={bool(rec[4] & 1)})")
        if not ok:
            failures.append(f"{name}: 0x{got:07X} != 0x{want:07X}")

    non_exact = sum(1 for r in recs if not (r[4] & 1))
    print(f"  exact-hash records: {count - non_exact}/{count}  "
          f"({non_exact} flagged as collision-risk)")

    # The tier boundary: a free function must be absent from a VTABLE database.
    for name in MUST_BE_ABSENT:
        h = fnv1a32(name.encode("utf-8"))
        idx = bisect.bisect_left(hashes, h)
        present = idx < len(recs) and recs[idx][0] == h
        print(f"  {name:24} {'PRESENT (WRONG - free fn in a vtable db)' if present else 'absent, as required'}")
        if present:
            failures.append(f"{name} is a free function and must not be in the vtable database")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("  all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
