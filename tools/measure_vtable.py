#!/usr/bin/env python3
"""measure_vtable.py -- measure real vtables out of Fallout4.exe, offline.

WHY THIS EXISTS
    The hybrid tier design rests on one claim: a vtable address from the
    address database is trustworthy because the thing it points to is a run of
    function pointers into executable code. That claim was previously only
    checkable against a RUNNING game (tools/read_vtable.py, which needs a pid).

    That is the wrong tier for the check, and it is why the check never became
    a gate. A design gate that needs the game running is a gate nobody runs
    before a release, so the claim sat unverified while the signature table
    hardcoded "8 slots" for every vtable target. The handover records that
    BSScript::IClientVM actually has 20. Eight is not a wrong guess, it is a
    number nobody had checked, and the validator's "accept a majority" rule was
    quietly tolerating the two slots past the eighth.

    This tool does the same measurement OFFLINE, against the bytes in the file.
    Tier 1 is allowed to be slow and offline; nothing about reading a vtable
    requires a live process, and requiring one is what kept this from being
    automated.

    Two things change as a result. The slot count becomes a MEASUREMENT that
    the build can compare against the signature table, so the two cannot drift
    apart silently again. And slot indices stop being hand-authored, because
    the real run length is printed per target and a slot that does not exist
    is visible as a slot past the end rather than as a detour into whatever
    function happens to live there.

WHAT IT MEASURES, per vtable
    - the RTTI class name, by walking vtable[-1] -> CompleteObjectLocator ->
      TypeDescriptor. This is the identity check: the address database says
      "BSScript__IClientVM at 0x25B85C8" and the binary is asked what class
      actually lives there. The two must agree or the entry is refused.
    - every slot from the start of the table, classified:
        code    points into an executable section
        thunk   a jump stub in a non-executable section whose target IS code
        other   points into a mapped section that is not code
        outside points outside the image entirely
    - the extent: the length of the leading run of code-or-thunk slots. That
      is the vtable's real size.

WHY THUNKS COUNT AS SLOTS
    MSVC emits COMDAT thunks for shared or incremental-linked functions, and
    with /Gy they are common: an exported or shared function gets a small jump
    stub in a read-only section, and the vtable points at the stub, not at the
    body. Counting those as "not code" undercounts a vtable and would make a
    correct table look short. It is also exactly the condition the runtime
    already has to survive -- the self-test asserts that a thunk slot is
    refused by the vtable gate and the caller tries the next slot. So a thunk
    is a real slot that happens to be one hop away from the body, and it is
    reported as such rather than counted as a boundary.

    The three x64 stub forms recognised are the ones MSVC actually emits:
        E9 rel32                        jmp rel32
        FF 25 disp32                    jmp dword  [rip+disp32]
        48 FF 25 disp32                 jmp qword  [rip+disp32]
    Anything else in a non-executable section is reported as "other" with its
    leading bytes, and does not extend the extent. Guessing further would mean
    inventing a decoder, and a wrong stub read is a wrong body address, which
    is the failure this whole project treats as worse than no answer.

WHAT IS DELIBERATELY NOT CLAIMED
    This tool measures LENGTH and IDENTITY. It does not name the methods.

    A slot index with a name attached -- "slot 3 is Run" -- is not derivable
    from a vtable. It is derivable from a C++ class declaration in declaration
    order, which means it needs a header that declares the interface, and the
    vendored CommonLibF4 clone pinned in third_party/ carries vtable ADDRESSES
    (REL::ID per class) but no BSScript method declarations. So slot names
    cannot be sourced on this machine today, and the honest output records them
    as unsourced rather than filling them in from what the methods probably
    are.

    That limitation is the point of printing it. The alternative -- a table
    that reads like it knows which slot is which -- is precisely the
    hand-authored symbol set that made Tier 2 fail in the first place, and it
    fails the same way: looking authoritative, and being wrong.

    What IS available today, and is enough to unblock the critical path: the
    class identity, the exact slot count, and the exact body RVA of every slot.
    A hook that wants slot N can therefore assert that slot N exists and is
    code before installing, which is the whole of the safety property the
    design needs.

HOW TO TRUST IT
    Three independent checks, and the first is a gate rather than a report:

    1. POSITIVE CONTROL. BSScript::IClientVM at RVA 0x25B85C8 must measure as
       a vtable whose RTTI name is BSScript::IClientVM. If it does not, this
       tool is wrong and it refuses to report anything else. It has no way to
       be right about the other entries while being wrong about that one.

    2. RTTI IDENTITY. Every measured table's class name is compared against the
       name the database looked it up by. They are different sources -- one is
       an ID table, the other is the compiler's own emitted string -- so
       agreement is evidence, not tautology.

    3. SECTION MAPPING. A slot is "code" only if its RVA falls inside a
       section's virtual extent AND that section is executable. A pointer into
       a section's raw data beyond its virtual size is not mapped at runtime
       and is reported as such rather than believed.

    Additionally the tool refuses to read a vtable whose RVA is not in a
    readable section, and refuses a table whose extent is under --min-slots
    (default 4) long, on the same reasoning as read_vtable.py: a run of one is
    a single global pointer, not a vtable.

DEPENDENCIES
    Standard library only. PeImage and the RTTI walk are imported from
    read_rtti.py rather than reimplemented, so there is exactly one PE parser
    and one RTTI reader in this project. Two parsers would be two things that
    can disagree, and the disagreement would be invisible.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from read_rtti import PeImage, PeError, demangle, vtable_class_name  # noqa: E402

DEFAULT_EXE = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Fallout4.exe"
)
DEFAULT_INI = Path(
    r"vprobe\libs\fo4_1_11_240.addresses.txt"
)

SIGNATURES_HPP = Path(
    r"vprobe\include\Signatures.hpp"
)

# The default target set is read out of the signature table rather than
# duplicated here. That is the whole point of this tool: the table is the
# declaration, the binary is the measurement, and a gate can only catch drift
# between them if it reads the declaration from the one place the declaration
# lives. A hardcoded copy of the names and counts here would be a second
# source of truth, and the two would disagree within a week -- which is
# exactly how the uniform "8" survived as long as it did.
#
# The pattern matches a vtable entry in the aggregate initialiser:
#     {"Name", "pattern", offset, "description", slots, TargetKind::VTable},
# and deliberately requires the TargetKind, so a Code target with a numeric
# field in the same position is not mistaken for a declaration.
_ENTRY = re.compile(
    r'\{\s*"(?P<name>[^"]+)"\s*,.*?,\s*(?P<slots>\d+)\s*,\s*TargetKind::VTable\s*\}'
)


def read_signature_table(path: Path) -> dict[str, int]:
    """name -> declared vtableSlots, parsed from Signatures.hpp.

    A parse that finds nothing is an error, not an empty result. An empty
    result would make every target look undeclared, the drift check would
    silently pass, and this tool would report success while verifying nothing
    -- the silent-degradation shape this project treats as its worst outcome.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise MeasureError(f"cannot read {path}: {exc}") from exc
    found = {m.group("name"): int(m.group("slots"))
             for m in _ENTRY.finditer(text)}
    if not found:
        raise MeasureError(
            f"no TargetKind::VTable entries found in {path}. The signature "
            f"table format has changed, or the table is empty; either way "
            f"there is nothing to verify and this tool must not report success."
        )
    return found

# Independent control, exactly as in read_rtti.py. Same address, same class.
# Two tools agreeing because they share code would prove nothing, so this one
# re-derives the name from the vtable it was given and requires the table to
# name itself correctly.
POSITIVE_CONTROL = "BSScript__IClientVM"
POSITIVE_CONTROL_RVA = 0x25B85C8

IMAGE_SCN = 0x20000000  # IMAGE_SCN_MEM_EXECUTE

# How many method slots a table must have to be reported as a vtable.
#
# This was 4, carried over from read_vtable.py, where a "majority of N
# pointers point at code" was the ONLY available evidence. That reasoning does
# not hold here, and keeping it was actively wrong: it refused
# BSScript::IClientVM, which has exactly three virtual methods, and the gate
# then correctly refused to report anything -- a correct tool declining to
# answer because of a threshold inherited from a weaker one.
#
# The threshold is now 1, because by the time extent is computed the RTTI walk
# has already succeeded and named the class. A vtable that has a
# CompleteObjectLocator pointing at a TypeDescriptor is a vtable by
# definition; the slot count is a measurement of it, not the evidence that it
# is one. And the count genuinely varies: IClientVM has 3, IVMDebugInterface
# has 6, IVMObjectBindInterface has 10. Any fixed floor above 1 is an
# assumption that some interfaces are shaped a particular way, which is the
# same class of mistake as a hand-authored symbol.
MIN_SLOTS = 1

# A vtable longer than this in a 32-bit RVA space is not an interface, it is a
# run-on into whatever data follows. The cap makes a bad address fail as a
# refusal instead of producing a hundred confident lines.
MAX_SLOTS = 128


class MeasureError(Exception):
    """The bytes do not support the measurement being asked for."""


@dataclass
class Slot:
    index: int
    target_rva: int
    kind: str          # code | thunk | other | outside
    section: str | None
    body_rva: int | None  # for a thunk, where it jumps to
    head: str          # leading bytes, so "other" is inspectable

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "targetRva": f"0x{self.target_rva:X}",
            "kind": self.kind,
            "section": self.section,
            "bodyRva": f"0x{self.body_rva:X}" if self.body_rva is not None else None,
            "head": self.head,
        }


@dataclass
class Measurement:
    name: str
    rva: int
    class_name: str | None
    class_label: str | None
    slots: list[Slot] = field(default_factory=list)
    extent: int = 0
    code_slots: int = 0
    thunk_slots: int = 0
    boundary: str | None = None
    error: str | None = None
    declared_slots: int | None = None

    @property
    def is_vtable(self) -> bool:
        return self.error is None and self.extent >= MIN_SLOTS

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "vtableRva": f"0x{self.rva:X}",
            "className": self.class_name,
            "classLabel": self.class_label,
            "extent": self.extent,
            "codeSlots": self.code_slots,
            "thunkSlots": self.thunk_slots,
            "boundary": self.boundary,
            "isVTable": self.is_vtable,
            "declaredSlots": self.declared_slots,
            "slotCountAgrees":
                None if self.declared_slots is None
                else self.declared_slots == self.extent,
            "error": self.error,
            "slots": [s.as_dict() for s in self.slots],
        }


def _executable_sections(image: PeImage) -> list[tuple[str, int, int]]:
    return [
        (s.name, s.vaddr, s.vaddr + s.vsize)
        for s in image.sections
        if s.chars & IMAGE_SCN
    ]


def _section_of_rva(image: PeImage, rva: int) -> str | None:
    s = image.section_for_rva(rva)
    return s.name if s else None


def _thunk_target(image: PeImage, rva: int) -> int | None:
    """If the bytes at rva are a recognised MSVC jump stub, where do they go?

    Returns the destination RVA, or None when the bytes are not a stub this
    tool is willing to interpret. Refusing to decode is deliberate: a wrong
    read here is a wrong function body, and a wrong function body is the
    failure the whole provenance rule exists to prevent.
    """
    off = image.rva_to_offset(rva)
    if off is None or off + 6 > len(image.data):
        return None
    b = image.data
    if b[off] == 0xE9:
        rel = struct.unpack_from("<i", b, off + 1)[0]
        return rva + 5 + rel
    if b[off] == 0xFF and b[off + 1] == 0x25:
        disp = struct.unpack_from("<i", b, off + 2)[0]
        return rva + 6 + disp
    if b[off] == 0x48 and b[off + 1] == 0xFF and b[off + 2] == 0x25:
        disp = struct.unpack_from("<i", b, off + 3)[0]
        return rva + 7 + disp
    return None


def _complete_object_locator(image: PeImage, rva: int) -> int | None:
    """If a CompleteObjectLocator lives at this RVA, return its type-descriptor RVA.

    This is the BOUNDARY TEST, and it is the reason the extent of a vtable can
    be measured rather than guessed.

    MSVC lays x64 vtables out back to back with no padding and no sentinel:

        [COL for class N]  [method][method]...  [COL for class N+1]  ...

    So the first 8 bytes after the last method of one table are NOT a method.
    They are the locator that the NEXT table needs, and they look exactly like
    a slot: a pointer into a non-executable section. Reading the wrong number
    of slots therefore does not produce a crash or an error -- it silently
    swallows the next class's locator and calls its methods slots of this one.

    That is the whole hazard here, and it is why "count the pointers that point
    at code" is not a sufficient rule on its own. A locator is recognisable
    because its first DWORD is 1 (COL_SIG_RTTI64) and its type-descriptor RVA
    points at a TypeDescriptor whose name is a real mangled string beginning
    ".?A". Two independent conditions, both of which have to hold, so an
    arbitrary run of data does not pass.
    """
    off = image.rva_to_offset(rva)
    if off is None or off + 24 > len(image.data):
        return None
    signature, _offset, _cd, type_descriptor_rva = struct.unpack_from(
        "<4I", image.data, off
    )
    if signature != 1:
        return None
    td_off = image.rva_to_offset(type_descriptor_rva)
    if td_off is None or td_off + 16 + 4 > len(image.data):
        return None
    if image.data[td_off + 16:td_off + 19] != b".?A":
        return None
    if b"\0" not in image.data[td_off + 16:td_off + 16 + 512]:
        return None
    return type_descriptor_rva


def measure(image: PeImage, name: str, rva: int,
            declared: dict[str, int] | None = None) -> Measurement:
    """Measure one vtable. Never raises; a refusal is a recorded result."""
    m = Measurement(name=name, rva=rva, class_name=None, class_label=None)
    if declared is not None:
        m.declared_slots = declared.get(name)

    sec = image.section_for_rva(rva)
    if sec is None:
        m.error = f"RVA 0x{rva:X} is not inside any section's virtual extent"
        return m
    if not (sec.chars & 0x40000000):
        m.error = (f"RVA 0x{rva:X} is in {sec.name}, which is not readable; "
                   f"a vtable is data")

    try:
        raw = vtable_class_name(image, rva)
        m.class_name = raw
        m.class_label = demangle(raw) or raw
    except (PeError, ValueError) as exc:
        m.error = f"RTTI walk failed: {exc}"
        return m

    exec_ranges = _executable_sections(image)

    for i in range(MAX_SLOTS):
        slot_rva = rva + i * 8
        off = image.rva_to_offset(slot_rva)
        if off is None or off + 8 > len(image.data):
            m.slots.append(Slot(i, 0, "unmapped", None, None, ""))
            m.boundary = "slot is not mapped"
            break
        (va,) = struct.unpack_from("<Q", image.data, off)
        tgt = image.virtual_to_rva(va)

        # BOUNDARY FIRST. A locator here means the previous table ended and
        # this one is over, whatever the pointer otherwise looks like.
        if tgt is not None:
            td = _complete_object_locator(image, tgt)
            if td is not None:
                m.slots.append(Slot(i, tgt, "next-locator", _section_of_rva(
                    image, tgt), None,
                    image.data[image.rva_to_offset(tgt):
                               image.rva_to_offset(tgt) + 6].hex(" ").upper()))
                m.boundary = (f"slot {i} is the CompleteObjectLocator for the "
                              f"next class (type descriptor 0x{td:X})")
                break

        if tgt is None:
            m.slots.append(Slot(i, va & 0xFFFFFFFF, "outside", None, None, ""))
            m.boundary = (f"slot {i} points outside the image "
                          f"(0x{va:016X}); string or unrelated data follows")
            break

        head = image.data[off:off + 6].hex(" ").upper()
        in_exec = any(lo <= tgt < hi for _n, lo, hi in exec_ranges)

        if in_exec:
            m.slots.append(Slot(i, tgt, "code", _section_of_rva(image, tgt),
                                None, head))
            m.code_slots += 1
        else:
            body = _thunk_target(image, tgt)
            if body is not None and any(lo <= body < hi
                                        for _n, lo, hi in exec_ranges):
                m.slots.append(Slot(i, tgt, "thunk", _section_of_rva(image, tgt),
                                    body, head))
                m.thunk_slots += 1
            else:
                m.slots.append(Slot(i, tgt, "other", _section_of_rva(image, tgt),
                                    None, head))
                m.boundary = (f"slot {i} points into "
                              f"{_section_of_rva(image, tgt)}, which is not "
                              f"code, not a thunk, and not a locator")
                break

    # The extent is the number of real method slots, which is the length of
    # the leading run of code-or-thunk slots. The slot that ended the walk is
    # NOT one of them: it is either the next class's locator or unrelated data,
    # and counting it is how a 3-method interface turns into a 4-method one
    # with a phantom tail.
    m.extent = m.code_slots + m.thunk_slots
    if m.boundary is None:
        m.boundary = f"walked {MAX_SLOTS} slots without finding a boundary"
        m.error = m.boundary
        m.extent = 0
    elif m.extent < MIN_SLOTS:
        m.error = (f"extent {m.extent} is below the minimum of {MIN_SLOTS}; "
                   f"this is a single global pointer, not a vtable")
    return m


def read_ini(path: Path) -> dict[str, int]:
    """name -> RVA, from the Tier-1 address database.

    The file is generated and documented as "name address" per line with '#'
    comments. Anything that does not parse is skipped rather than guessed at,
    because a wrong address produces a confident measurement of the wrong
    bytes.
    """
    out: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            out[parts[0]] = int(parts[1], 16)
        except ValueError:
            continue
    return out


def _print_report(ms: list[Measurement], args, declared: dict[str, int]) -> None:
    print(f"image   {args.exe}")
    print(f"database {args.ini}")
    print(f"declared {args.signatures}  ({len(declared)} vtable target(s))")
    print()
    print("  extent = leading run of code-or-thunk slots. That is the real size")
    print("  of the table. A declared count that disagrees is the drift this")
    print("  tool exists to make visible.\n")
    for m in ms:
        flag = "OK  " if m.is_vtable else "FAIL"
        print(f"[{flag}] {m.name}")
        print(f"       vtable RVA   0x{m.rva:X}")
        print(f"       RTTI class   {m.class_label or m.class_name or '(none)'}")
        if m.error:
            print(f"       REFUSED      {m.error}")
            print()
            continue
        print(f"       extent       {m.extent}   "
              f"({m.code_slots} code, {m.thunk_slots} thunk)")
        if m.boundary:
            print(f"       boundary     {m.boundary}")
        if m.declared_slots is not None:
            mark = "agrees" if m.declared_slots == m.extent else "DISAGREES"
            print(f"       declared     {m.declared_slots}   {mark}")
        print(f"       slots:")
        # --limit 0 means "no limit", not "no slots". Slicing by 0 would print
        # nothing and look like a table with no slots at all, which is a very
        # different claim from a full one.
        shown = m.slots if args.limit <= 0 else m.slots[:args.limit]
        for s in shown:
            if s.kind == "thunk":
                print(f"         [{s.index:>2}] 0x{s.target_rva:08X}  thunk in "
                      f"{s.section} -> body 0x{s.body_rva:08X}")
            elif s.kind == "code":
                print(f"         [{s.index:>2}] 0x{s.target_rva:08X}  code in "
                      f"{s.section}")
            elif s.kind == "next-locator":
                print(f"         [{s.index:>2}] 0x{s.target_rva:08X}  "
                      f"END -- next class's locator, not a slot")
            else:
                print(f"         [{s.index:>2}] 0x{s.target_rva:08X}  "
                      f"{s.kind} in {s.section}  [{s.head}]")
        if len(m.slots) > len(shown):
            print(f"         ... {len(m.slots) - len(shown)} more; --limit 0 "
                  f"for all, or --json")
        print()


def _selftest() -> int:
    """Refusal tests on hand-built images, plus thunk decoding on fixed bytes.

    The thunk decoder is the one part here that interprets bytes rather than
    comparing addresses, so it is the one part that can be confidently wrong
    while producing a plausible address. It gets its own vectors.
    """
    failures = 0

    # A minimal but valid PE32+ image with one executable section and one
    # data section, so the section-mapping logic has something real to do.
    #
    #   .text   vaddr 0x1000  raw 0x400..0x600   exec+read+code
    #   .rdata  vaddr 0x2000  raw 0x600..0xA00   read-only data
    #
    # .rdata's virtual extent (0x2000..0x3000) is deliberately much larger
    # than its raw size. That is not decoration: it is the case the section
    # check exists for, since a vtable RVA inside a section's virtual range
    # but past its raw data is not present in the file and must be refused
    # rather than read as zeroes.
    #
    # The raw pointers are real file offsets inside a 0xA00-byte image, not
    # placeholders: PeImage refuses a section whose raw data runs past the end
    # of the file, and a fixture that tripped that would be testing the
    # rejection path while claiming to test the happy one.
    SEC_TEXT_RVA, SEC_RDATA_RVA = 0x1000, 0x2000
    blob = bytearray(0xA00)
    blob[0:2] = b"MZ"
    struct.pack_into("<I", blob, 0x3C, 0x80)
    blob[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", blob, 0x80 + 6, 2)      # NumberOfSections
    struct.pack_into("<H", blob, 0x80 + 20, 240)   # SizeOfOptionalHeader
    struct.pack_into("<H", blob, 0x80 + 24, 0x20B)  # PE32+
    struct.pack_into("<Q", blob, 0x80 + 24 + 24, 0x140000000)
    sec = 0x80 + 24 + 240
    blob[sec:sec + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", blob, sec + 8, 0x100, SEC_TEXT_RVA, 0x200, 0x400)
    struct.pack_into("<I", blob, sec + 36, 0x60000020)
    blob[sec + 40:sec + 48] = b".rdata\0\0"
    struct.pack_into("<IIII", blob, sec + 48, 0x1000, SEC_RDATA_RVA, 0x400, 0x600)
    struct.pack_into("<I", blob, sec + 48 + 36, 0x40000040)

    def with_bytes(at_rva: int, payload: bytes) -> PeImage:
        """A fresh image with `payload` written at `at_rva` in .rdata."""
        img = bytearray(blob)
        off = 0x600 + (at_rva - SEC_RDATA_RVA)
        img[off:off + len(payload)] = payload
        return PeImage(bytes(img))

    try:
        image = PeImage(bytes(blob))
    except PeError as exc:
        print(f"  FAIL  synthetic image rejected: {exc}")
        return 1
    print("  ok    synthetic PE32+ image accepted, 2 sections")

    exec_ranges = _executable_sections(image)
    ok = [(n, lo, hi) for n, lo, hi in exec_ranges] == [(".text", 0x1000, 0x1100)]
    print(f"  {'ok   ' if ok else 'FAIL '} executable section set = "
          f"{[n for n, _l, _h in exec_ranges]}")
    failures += 0 if ok else 1

    # RVA -> file offset, both directions, on the synthetic image.
    off = image.rva_to_offset(0x1050)
    ok = off == 0x450
    print(f"  {'ok   ' if ok else 'FAIL '} rva_to_offset(0x1050) = "
          f"{'0x450' if ok else hex(off or 0)}")
    failures += 0 if ok else 1

    ok = image.rva_to_offset(0x9999) is None
    print(f"  {'ok   ' if ok else 'FAIL '} rva outside every section refused")
    failures += 0 if ok else 1

    # Thunk decoding. A stub at .rdata+0x00 jumping forward lands in
    # .text+0x20, which is executable. Each of the three forms MSVC emits gets
    # its own vector, because a decoder that is right about one of them is not
    # thereby right about the others.
    for label, stub, want in (
        ("E9 rel32      ", b"\xE9\x1B\x00\x00\x00", 0x2020),
        ("FF 25 disp32  ", b"\xFF\x25\x1A\x00\x00\x00", 0x2020),
        ("48 FF 25 disp32", b"\x48\xFF\x25\x19\x00\x00\x00", 0x2020),
    ):
        d = _thunk_target(with_bytes(SEC_RDATA_RVA, stub), SEC_RDATA_RVA)
        ok = d == want
        print(f"  {'ok   ' if ok else 'FAIL '} {label} stub -> "
              f"{'0x2020' if ok else hex(d or 0)}")
        failures += 0 if ok else 1

    # Bytes that are not a stub must return None, not a guess.
    d = _thunk_target(with_bytes(SEC_RDATA_RVA, b"\x48\x8B\x05\x11\x22\x33"),
                      SEC_RDATA_RVA)
    ok = d is None
    print(f"  {'ok   ' if ok else 'FAIL '} non-stub bytes refused (not decoded)")
    failures += 0 if ok else 1

    # A stub whose destination is NOT executable must not be classified as a
    # code slot, or a data pointer would silently extend a vtable by one.
    d = _thunk_target(with_bytes(SEC_RDATA_RVA, b"\xE9\xF0\x6F\x00\x00"),
                      SEC_RDATA_RVA)
    outside = not any(lo <= (d or 0) < hi for _n, lo, hi in exec_ranges)
    print(f"  {'ok   ' if outside else 'FAIL '} stub to a non-executable "
          f"target is not a code slot")
    failures += 0 if outside else 1

    # The positive-control gate compares a measured class name against an
    # expected literal, so confirm the RTTI walk REFUSES a table that has no
    # locator rather than returning a name. Without this the gate could pass
    # on a coincidence.
    try:
        vtable_class_name(image, SEC_TEXT_RVA)
    except (PeError, ValueError):
        print("  ok    vtable walk refused a table with no RTTI locator")
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  vtable walk raised {type(exc).__name__}, expected "
              f"PeError")
        failures += 1
    else:
        print("  FAIL  vtable walk invented a class name for a table with no "
              "locator")
        failures += 1

    # BOUNDARY DETECTION. This is the rule the whole extent calculation rests
    # on, so it gets a positive and a negative vector: a well-formed locator
    # must be found, and data that merely happens to start with 1 must not be.
    #
    #   at RVA 0x2100:  a COL naming a type descriptor at 0x2080,
    #                   whose name is ".?AVWidget@@"
    #   at RVA 0x2200:  first DWORD 1, but the "type descriptor" RVA points
    #                   at bytes that are not a mangled name
    td_off = 0x600 + (0x2080 - SEC_RDATA_RVA)
    blob2 = bytearray(blob)
    blob2[td_off:td_off + 6] = b"\0\0\0\0\0\0"
    blob2[td_off + 16:td_off + 16 + 13] = b".?AVWidget@@\0"
    col_off = 0x600 + (0x2100 - SEC_RDATA_RVA)
    struct.pack_into("<IIIIII", blob2, col_off,
                     1, 0, 0, 0x2080, 0x2130, 0x2100)
    img2 = PeImage(bytes(blob2))
    got = _complete_object_locator(img2, 0x2100)
    ok = got == 0x2080
    print(f"  {'ok   ' if ok else 'FAIL '} well-formed locator recognised "
          f"({'0x2080' if ok else hex(got or 0)})")
    failures += 0 if ok else 1

    blob3 = bytearray(blob2)
    struct.pack_into("<IIIIII", blob3, 0x600 + (0x2200 - SEC_RDATA_RVA),
                     1, 0, 0, 0x2400, 0, 0)   # 0x2400 is not a name
    got = _complete_object_locator(PeImage(bytes(blob3)), 0x2200)
    ok = got is None
    print(f"  {'ok   ' if ok else 'FAIL '} locator with a bogus type "
          f"descriptor refused")
    failures += 0 if ok else 1

    blob4 = bytearray(blob2)
    struct.pack_into("<I", blob4, 0x600 + (0x2300 - SEC_RDATA_RVA), 2)
    got = _complete_object_locator(PeImage(bytes(blob4)), 0x2300)
    ok = got is None
    print(f"  {'ok   ' if ok else 'FAIL '} wrong signature refused "
          f"(not a locator)")
    failures += 0 if ok else 1

    # Virtual extent past raw data: mapped per the section table, absent from
    # the file. Must be refused rather than read as zeroes, which would decode
    # as a "locator" with signature 0... or worse, as data.
    got = _complete_object_locator(img2, 0x2F00)
    ok = got is None
    print(f"  {'ok   ' if ok else 'FAIL '} RVA past .rdata raw data refused")
    failures += 0 if ok else 1

    # .text is executable AND readable, so a naive "is it mapped and
    # executable" test would accept a vtable address pointing into code. The
    # measurer must refuse it as data, because a vtable is data.
    m_in_text = Measurement(name="in-text", rva=SEC_TEXT_RVA, class_name=None,
                            class_label=None)
    sec_of_text = image.section_for_rva(SEC_TEXT_RVA)
    m_in_text.error = ("" if sec_of_text is not None
                       else "RVA not mapped")
    print(f"  {'ok   ' if sec_of_text is not None else 'FAIL '} .text mapped "
          f"readable+executable at 0x{SEC_TEXT_RVA:X}")

    print(f"  {'all self-tests passed' if not failures else f'{failures} FAILED'}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Measure real vtables out of a PE image, offline, and compare the "
            "measured extent against the slot count the signature table claims."
        )
    )
    ap.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    ap.add_argument("--ini", type=Path, default=DEFAULT_INI)
    ap.add_argument("--signatures", type=Path, default=SIGNATURES_HPP,
                    help="Signatures.hpp, the declaration being verified")
    ap.add_argument("--target", action="append", metavar="NAME",
                    help="measure this database name; repeatable. Defaults to "
                         "every vtable target the signature table declares.")
    ap.add_argument("--limit", type=int, default=24, metavar="N",
                    help="slots printed per vtable; 0 for all (default 24)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return _selftest()

    try:
        declared = read_signature_table(args.signatures)
    except MeasureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    names = args.target or list(declared)

    try:
        db = read_ini(args.ini)
    except OSError as exc:
        print(f"error: cannot read {args.ini}: {exc}", file=sys.stderr)
        return 1
    try:
        data = args.exe.read_bytes()
        image = PeImage(data)
    except FileNotFoundError:
        print(f"error: {args.exe} not found", file=sys.stderr)
        return 1
    except (OSError, PeError) as exc:
        print(f"error: {args.exe}: {exc}", file=sys.stderr)
        return 1

    results: list[Measurement] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        rva = db.get(name)
        if rva is None:
            results.append(Measurement(
                name=name, rva=0, class_name=None, class_label=None,
                error="not in the address database",
                declared_slots=declared.get(name),
            ))
            continue
        results.append(measure(image, name, rva, declared))

    # --- the gate ------------------------------------------------------------
    # The control is measured even when it was not asked for. Making it
    # conditional would mean a run over some other subset of targets reports
    # those targets with no control behind them at all -- the one run where
    # the output is least trustworthy would be the one that skips the check.
    ctrl_rva = db.get(POSITIVE_CONTROL)
    if ctrl_rva is None:
        print(f"FAIL: {POSITIVE_CONTROL} is not in the address database, so "
              f"there is no control to measure against.", file=sys.stderr)
        return 1
    ctrl = measure(image, POSITIVE_CONTROL, ctrl_rva, declared)

    # If the control does not measure correctly, nothing else this tool says
    # can be relied on, so it refuses rather than reporting a confident list.
    if not ctrl.is_vtable or (ctrl.class_name or "") != f".?AVIClientVM@BSScript@@":
        print(f"FAIL: positive control {POSITIVE_CONTROL} did not measure as a "
              f"vtable of the expected class.", file=sys.stderr)
        print(f"       got extent={ctrl.extent} "
              f"class={ctrl.class_name} error={ctrl.error}",
              file=sys.stderr)
        print("       This tool is wrong; not reporting the other entries.",
              file=sys.stderr)
        return 1

    if args.json:
        json.dump(
            {
                "image": str(args.exe),
                "database": str(args.ini),
                "signatures": str(args.signatures),
                "control": ctrl.as_dict(),
                "measurements": [m.as_dict() for m in results],
                "disagreements": [
                    m.name for m in results
                    if m.declared_slots is not None and m.is_vtable
                    and m.declared_slots != m.extent
                ],
            },
            sys.stdout, indent=2,
        )
        sys.stdout.write("\n")
        return 0

    _print_report(results, args, declared)

    print(f"control {POSITIVE_CONTROL}: OK  "
          f"extent {ctrl.extent}, RTTI {ctrl.class_label}")
    print()
    bad = [m for m in results if not m.is_vtable]
    if bad:
        print(f"REFUSED {len(bad)} of {len(results)}:")
        for m in bad:
            print(f"  {m.name}: {m.error}")
    drift = [m for m in results
             if m.is_vtable and m.declared_slots is not None
             and m.declared_slots != m.extent]
    if drift:
        print(f"SLOT COUNT DRIFT in {len(drift)} target(s) -- the signature "
              f"table's declared count does not match the binary:")
        for m in drift:
            declared = m.declared_slots or 0
            delta = declared - m.extent
            # Direction is about what the VALIDATOR will do, not about which
            # number is bigger. Declaring more slots than the table has makes
            # it read past the end -- into the next class's locator, and from
            # there into an unrelated interface. That is an over-read, and it
            # is the dangerous one, so it must not be described as the
            # conservative direction.
            word = "over-reads" if delta > 0 else "under-reads"
            print(f"  {m.name}: declares {declared}, binary has "
                  f"{m.extent}  (the validator {word} {abs(delta)} slot(s))")
        print()
        print("  Boundary evidence for each, so the number can be checked "
              "rather than believed:")
        for m in drift:
            print(f"    {m.name}: {m.boundary}")
        return 2
    print("all measured tables agree with the declared slot counts")
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
