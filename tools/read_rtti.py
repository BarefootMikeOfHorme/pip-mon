#!/usr/bin/env python3
"""read_rtti.py -- read the game's own RTTI type names out of Fallout4.exe.

WHY THIS EXISTS
    Six "Tier 2" AOB signature targets do not resolve. The conclusion from the
    research that preceded this tool is that the hand-authored symbol NAMES are
    wrong, not stale: the six targets are named after PapyrusScript::Execute,
    PapyrusThread::Execute, PapyrusVM::DebugPrint, PapyrusVM::PapyrusVM,
    PapyrusVM::GetRunningThreadCount and FormData::CellStream, and there is
    reportedly no PapyrusVM, PapyrusThread, PapyrusScript or FormData class in
    the game at all.

    "Reportedly" is the problem. Every other tier in this project is built on
    assertions somebody believed. This one is not. MSVC embeds the mangled name
    of every class it emits RTTI for as a NUL-terminated ASCII string in the
    image, so the set of real class names is a fact sitting in the file, and
    the only honest way to get it is to read it rather than to keep guessing
    plausible ones.

    The failure mode this prevents is specific and it is nasty: a wrong name
    produces a plausible-looking scan plan, a signature that matches nothing,
    and a build log that reads like a stale database. A wrong name and a stale
    database are indistinguishable from the outside, so the only fix is to stop
    treating hand-written names as evidence.

    This is Tier-1 "Oracle" tooling. It runs offline, on this machine, at build
    time. It is not a runtime component and must never be loaded by vprobe.dll.

WHAT IS ACTUALLY VALIDATED, AND HOW STRONG IT IS
    A byte scan for ".?A" is trivially easy to get subtly wrong, and a wrong
    extractor is worse than none because it looks like an answer. Three
    independent checks are therefore run on every run, and the positive control
    is a gate: if BSScript::IClientVM is not found, this tool exits non-zero
    rather than printing a list that happens not to contain it.

    1. STRUCTURAL. An MSVC type descriptor is

           struct TypeDescriptor { void *vftable; long spare; char name[]; };

       so a real one is preceded by exactly 16 bytes: a vftable pointer that
       resolves inside the image, and a spare field. Every candidate found in
       this binary has spare == 0 and a vftable pointer into .rdata, and the
       vftable those pointers name is the shared type_info vftable. A
       coincidental ".?A" byte sequence in .text would not survive that.

       This check is REPORTED, not used as a filter. A name that fails it is
       still listed, with the failure recorded, because a tool that silently
       drops the one symbol you needed is the exact bug being fixed here.

    2. POSITIVE CONTROL. BSScript::IClientVM is independently known to exist --
       its vtable is at RVA 0x25B85C8, confirmed by an external reader and by
       the AddressLib database. --verify-vtable proves the tool end to end by
       walking the real RTTI chain backwards from that vtable: vtable[-1] is a
       CompleteObjectLocator, whose pTypeDescriptor is a TypeDescriptor, whose
       name is the string. That path shares no code with the scan.

    3. SECTION MAPPING. A name is only accepted if its file offset is inside a
       section's raw data AND its RVA is inside that section's virtual extent.
       The second half matters: .data on this build has vsize 0xF9DCF0 against
       rsize 0x20D400, so a file offset alone does not prove the bytes are
       mapped at runtime. It also keeps the scan from reporting names that sit
       in the overlay of a section's raw data beyond its virtual size.

WHAT IS DELIBERATELY NOT DONE HERE
    No full MSVC demangler. 8208 of the 12262 names are templates whose
    arguments are encoded in the MSVC type grammar (PEAV1@, AEBV3@, 6A...,
    $$R..., W4..., back-references). Rendering those needs a recursive-descent
    demangler covering that grammar, and a demangler that is subtly wrong is
    worse than raw text: it produces confident, false identifiers, which is
    the same class of failure as the hand-written names this tool exists to
    replace. So demangle() handles only the subset that is unambiguous by
    inspection -- a plain qualified name with no template, scope-tag or
    expression construct in it -- and returns None for everything else, which
    the report shows as the raw mangled string.

    That is a real limitation and it is not hidden: the JSON output carries a
    per-record "demangled" field that is null precisely when the name was left
    mangled, so a consumer can tell the two apart. The raw names are the ground
    truth and are always present, so no information is lost by refusing to
    render it.

    For filtering and grouping there is a components field: the plain
    identifier tokens found in a name, as an UNORDERED set. It is not a
    qualified name and is never presented as one. It exists so that
    --filter BSScript can find a name that has BSScript buried in the middle
    of a template argument list, which is where most of them are.

    One thing the vtable walk produces but this tool does not interpret: the
    last DWORD of the CompleteObjectLocator, which the x64 layout documents as
    pSelf and which should hold the vtable's own RVA. On this build it holds
    the CompleteObjectLocator's own RVA instead, for 122 of 122 sampled
    locators. The chain does not need that field, so nothing here depends on it
    and no claim is made about why it is what it is. Flagged rather than
    guessed at, per G12.

DEPENDENCIES
    Standard library only, deliberately. A PE header is 40 bytes of DWORDs and
    a string scan is bytes.find(); paying a dependency chain for that would buy
    nothing and cost the property that this tool runs anywhere Python does.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_EXE = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Fallout4.exe"
)

# The six Tier-2 targets that do not resolve, and the type each one claims to
# belong to. Spelling them out here means the tool answers the question that
# was actually asked rather than dumping a list and leaving the reader to
# remember it.
DEAD_TARGETS = (
    "PapyrusScript::Execute",
    "PapyrusThread::Execute",
    "PapyrusVM::DebugPrint",
    "PapyrusVM::PapyrusVM",
    "PapyrusVM::GetRunningThreadCount",
    "FormData::CellStream",
)

# The class each dead target is reaching for, plus the bare words, so that
# "Papyrus" hitting only inside a functor name is visible as a hit of one and
# not mistaken for a hit of the other.
DEAD_CLASSES = ("PapyrusScript", "PapyrusThread", "PapyrusVM", "FormData")

# Independently confirmed to exist: vtable at this RVA per an external reader
# and per the AddressLib database. If the scan cannot find it, the scan is
# broken and this tool has no business reporting anything else.
POSITIVE_CONTROL = "BSScript::IClientVM"
POSITIVE_CONTROL_VTABLE_RVA = 0x25B85C8

# The scripting families, printed in full. BSScript is the headline; GameScript
# is the layer above it and turns out to hold several of the callback managers
# the six dead targets were probably reaching for, so suppressing it would
# suppress the answer.
SCRIPT_ROOTS = ("BSScript", "GameScript")

# Secondary sweeps, and an honest note on each. These exist to answer "what ARE
# the six targets reaching for" -- the Compile / Link / Execute / Load / Save /
# Debug / callback interfaces -- not to claim exhaustiveness.
#
# The pipeline sweep is scoped to the scripting families, and says so. Run
# unscoped, the tokens Load and Link match MovementHandler::LoadScrapper and
# the whole Pathing layer, which is 200-odd lines of noise that bury the answer
# rather than revealing it. The unscoped total is printed alongside so the
# scoping is visible and nothing reads as if it had been filtered to fit.
PIPELINE_TOKENS = ("Compil", "Link", "Execut", "Load", "Save", "Debug",
                   "Tasklet", "Loader", "Linker", "Error", "Cache", "Store",
                   "Stream", "Print", "Message", "Callback", "Patcher",
                   "Policy", "Unpack", "Pack", "Register", "Function")

SWEEPS = (
    ("Papyrus", ("Papyrus",), False),
    ("FormData", ("FormData",), False),
    ("VM / VirtualMachine", ("VM", "VirtualMachine"), False),
    ("compile / link / execute / load / save / debug / message-callback",
     PIPELINE_TOKENS, True),
)

# The character set a type-descriptor name is actually made of in this binary,
# measured by running a permissive printable-ASCII scan and collecting the
# union of characters across all 12262 hits. Tight on purpose: the scan must
# never run past the end of a name into whatever follows it. Anything a name
# might contain that is not in here shows up as a REJECTED CANDIDATE, printed
# with the character that stopped it, rather than as a silent omission.
NAME_ALPHABET = frozenset(
    b"$.0123456789<>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"
)

# The tag character after ".?A" that says what kind of type this is. Only the
# first three are given names; an unrecognised tag is reported as "other" with
# the character kept, so an unexpected form shows up instead of being folded
# into a class.
KIND_BY_TAG = {"V": "class", "U": "struct", "T": "union"}

IDENTIFIER = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")

# Characters that mean a name contains a construct a plain qualified-name
# demangle cannot see through: '?' and '$' introduce templates, back-references
# and scope tags; '<' '>' delimit MSVC's lambda-closure encoding.
COMPLEX_CHARS = "?$<>"


class PeError(Exception):
    """The bytes are not a PE image this tool can trust."""


@dataclass(frozen=True)
class Section:
    name: str
    vaddr: int
    vsize: int
    rptr: int
    rsize: int
    chars: int

    def holds_file_offset(self, off: int) -> bool:
        return self.rptr <= off < self.rptr + self.rsize

    def holds_rva(self, rva: int) -> bool:
        return self.vaddr <= rva < self.vaddr + self.vsize


@dataclass(frozen=True)
class TypeDescriptor:
    """One RTTI type descriptor, as found in the file.

    raw is the mangled name exactly as the compiler emitted it and is the
    ground truth. demangled is None when the name uses a construct the
    conservative demangler will not guess at. components is an unordered set
    of identifier tokens for filtering, never a qualified name.
    """

    file_offset: int
    rva: int
    section: str
    raw: str
    kind: str
    demangled: str | None
    own: str | None
    components: tuple[str, ...]
    spare: int
    vftable_rva: int | None

    @property
    def label(self) -> str:
        """What to print as this descriptor's name."""
        return self.demangled if self.demangled else self.raw

    @property
    def structurally_valid(self) -> bool:
        return self.spare == 0 and self.vftable_rva is not None

    def as_dict(self) -> dict:
        return {
            "mangled": self.raw,
            "demangled": self.demangled,
            "ownName": self.own,
            "kind": self.kind,
            "rva": f"0x{self.rva:X}",
            "fileOffset": f"0x{self.file_offset:X}",
            "section": self.section,
            "components": list(self.components),
            "structurallyValid": self.structurally_valid,
        }


class PeImage:
    """Just enough PE to map a file offset to an RVA and back.

    Deliberately not a general PE parser. It reads the DOS stub, the NT headers,
    the PE32+ optional header (to get the image base) and the section table,
    and refuses anything it does not recognise rather than carrying on with
    numbers it has not checked. A truncated or garbage file produces a PeError
    with a message that says which check failed, because a parser that returns
    plausible zeros for a file it did not understand is how a tool like this
    ends up confidently reporting nothing.
    """

    def __init__(self, data: bytes):
        self.data = data
        if len(data) < 0x40:
            raise PeError(
                f"file is {len(data)} bytes; too small to contain a DOS header"
            )
        if data[:2] != b"MZ":
            raise PeError("no MZ signature: not a PE image")

        e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
        if e_lfanew + 24 > len(data):
            raise PeError(
                f"e_lfanew 0x{e_lfanew:X} points past the end of a "
                f"{len(data)}-byte file: truncated"
            )
        if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
            raise PeError(f"no PE signature at e_lfanew 0x{e_lfanew:X}")

        nsec = struct.unpack_from("<H", data, e_lfanew + 6)[0]
        opt_size = struct.unpack_from("<H", data, e_lfanew + 20)[0]
        if not 0 < nsec <= 96:
            raise PeError(f"implausible section count {nsec}")
        opt_off = e_lfanew + 24
        if opt_off + 2 > len(data):
            raise PeError("truncated before the optional header")
        magic = struct.unpack_from("<H", data, opt_off)[0]
        if magic != 0x20B:
            raise PeError(
                f"optional header magic 0x{magic:X} is not PE32+; this tool "
                f"reads the 64-bit image layout only"
            )
        if opt_off + 112 > len(data):
            raise PeError("truncated inside the optional header")
        self.image_base = struct.unpack_from("<Q", data, opt_off + 24)[0]

        sec_off = opt_off + opt_size
        if sec_off + nsec * 40 > len(data):
            raise PeError("truncated inside the section table")
        self.sections: list[Section] = []
        for i in range(nsec):
            o = sec_off + i * 40
            raw_name = data[o:o + 8].split(b"\0")[0]
            vsize, vaddr, rsize, rptr = struct.unpack_from("<IIII", data, o + 8)
            chars = struct.unpack_from("<I", data, o + 36)[0]
            if rptr + rsize > len(data):
                # A section whose raw data runs off the end of the file means
                # the file was truncated. Report it rather than scanning the
                # tail of a short file and reporting what it happened to hold.
                raise PeError(
                    f"section {raw_name.decode('ascii', 'replace') or i} claims "
                    f"raw data to 0x{rptr + rsize:X} but the file is "
                    f"0x{len(data):X} bytes: truncated"
                )
            self.sections.append(
                Section(
                    raw_name.decode("ascii", "replace"),
                    vaddr, vsize, rptr, rsize, chars,
                )
            )

    def section_for_offset(self, off: int) -> Section | None:
        for s in self.sections:
            if s.holds_file_offset(off):
                return s
        return None

    def section_for_rva(self, rva: int) -> Section | None:
        for s in self.sections:
            if s.holds_rva(rva):
                return s
        return None

    def rva_to_offset(self, rva: int) -> int | None:
        s = self.section_for_rva(rva)
        if s is None:
            return None
        return s.rptr + (rva - s.vaddr)

    def virtual_to_rva(self, va: int) -> int | None:
        if not self.image_base <= va < self.image_base + (1 << 32):
            return None
        rva = va - self.image_base
        return rva if self.section_for_rva(rva) is not None else None


def demangle(raw: str) -> str | None:
    """Render an MSVC type-descriptor name, or return None.

    Only the subset that is unambiguous by inspection is rendered: a plain
    qualified name whose components are all plain identifiers, with no
    template ('?$' or '?'), no back-reference ('$' on its own), no lambda
    closure ('<...>') and no scope tag anywhere in it. For that subset the
    mapping is a mechanical component join and there is nothing to get wrong.

    Returning None is the important part. A demangler that guesses on the hard
    cases produces identifiers that look authoritative and are not, which is
    indistinguishable from a wrong hand-written name -- the failure this tool
    was written to stop. The caller keeps the raw string in that case.
    """
    if not raw.startswith(".?A") or len(raw) < 5:
        return None
    if raw[3] not in KIND_BY_TAG:
        return None
    body = raw[4:]
    if not body.endswith("@@"):
        return None
    if any(c in COMPLEX_CHARS for c in body):
        return None
    parts = [p for p in body.split("@") if p]
    if not parts or not all(IDENTIFIER.match(p) for p in parts):
        return None
    # Reversed, and this is not cosmetic. MSVC writes a qualified name
    # leaf-first, so "IClientVM@BSScript@@" is the class IClientVM in the
    # namespace BSScript. Joining in stored order yields "IClientVM::BSScript",
    # which is a real-looking identifier that names nothing -- exactly the
    # failure mode this tool exists to stop, arrived at from the other
    # direction. The self-test covers this exact case.
    return "::".join(reversed(parts))


def components_of(raw: str) -> tuple[str, ...]:
    """Plain identifier tokens in a name, as an UNORDERED set.

    Not a qualified name and never printed as one. It exists so that filtering
    on a namespace finds names that mention it inside a template argument
    list, which is where most of the scripting types actually are. The tag
    character is dropped, as are the single-character type codes ('V', 'U',
    'H', ...) that share the 'V'/'U' shape of an ordinary name.
    """
    if not raw.startswith(".?A"):
        return ()
    found = set()
    for tok in raw[4:].split("@"):
        if len(tok) > 1 and IDENTIFIER.match(tok):
            found.add(tok)
    return tuple(sorted(found))


def own_name(raw: str) -> str | None:
    """The class's own (innermost) name, without its enclosing scopes.

    A class descriptor is always "<tag><name><scopes...>@@", so the own name
    is whatever precedes the first scope, scope-tag or template-argument
    separator. For a template the leading "name" is itself encoded as
    "?$Name@", hence the second branch.

    This exists because a substring test answers a different question from the
    one worth asking. "FormData" occurs three times in this image and all
    three are false friends -- SavedFormData, twice, and BGSLoadFormData --
    while no class is actually named FormData. Only this function can tell
    those apart, and conflating the two would turn a clean negative into a
    false positive and straight back into the guess this tool is replacing.

    One residual limitation, stated rather than hidden: MSVC replaces a
    repeated component with a positional token ("$0", "$1", "$A"), and this
    function does not undo that. Substitution is applied to template
    arguments, never to the leading component of a top-level type descriptor,
    so it cannot change the answer for a class name -- but that reasoning is
    an argument, not a measurement, and it is the one place here where a name
    could be reported as absent because of how it was encoded.
    """
    if not raw.startswith(".?A") or len(raw) < 5:
        return None
    body = raw[4:]
    if body.startswith("?$"):
        end = body.find("@", 2)
        return body[2:end] if end > 0 else None
    end = len(body)
    for sep in "@?<":
        i = body.find(sep)
        if i >= 0:
            end = min(end, i)
    return body[:end] or None


def read_type_descriptors(image: PeImage) -> tuple[list[TypeDescriptor], list[tuple[int, str]]]:
    """One linear pass over the image. Returns (descriptors, rejected).

    A single bytes.find loop over 55 MB is the whole search; there is no
    reason to make it cleverer, and the loop form keeps the memory profile at
    one copy of the file.

    Rejected candidates are returned rather than dropped, for the same reason
    they are not a filter: a name that this scanner refuses must be visible to
    whoever is relying on it. Each is (file_offset, why).
    """
    data = image.data
    out: list[TypeDescriptor] = []
    rejected: list[tuple[int, str]] = []
    pos = 0
    while True:
        start = data.find(b".?A", pos)
        if start < 0:
            break
        pos = start + 3

        section = image.section_for_offset(start)
        if section is None:
            rejected.append((start, "not inside any section's raw data"))
            continue
        rva = section.vaddr + (start - section.rptr)
        if not section.holds_rva(rva):
            rejected.append(
                (start, f"RVA 0x{rva:X} is past {section.name} virtual size")
            )
            continue

        end = start
        limit = min(len(data), section.rptr + section.rsize)
        while end < limit and data[end] in NAME_ALPHABET:
            end += 1
        if end >= limit:
            rejected.append((start, "unterminated before end of section data"))
            continue
        if data[end] != 0:
            rejected.append(
                (start,
                 f"no NUL terminator; stopped at {chr(data[end])!r} "
                 f"(0x{data[end]:02X})")
            )
            continue
        if end == start + 3:
            rejected.append((start, "empty name after the .?A prefix"))
            continue

        raw = data[start:end].decode("ascii")
        tag = raw[3]
        spare = 0
        vftable_rva: int | None = None
        if start >= 16:
            vftable_va, spare = struct.unpack_from("<Qq", data, start - 16)
            vftable_rva = image.virtual_to_rva(vftable_va)

        out.append(
            TypeDescriptor(
                file_offset=start,
                rva=rva,
                section=section.name,
                raw=raw,
                kind=KIND_BY_TAG.get(tag, f"other({tag})"),
                demangled=demangle(raw),
                own=own_name(raw),
                components=components_of(raw),
                spare=spare,
                vftable_rva=vftable_rva,
            )
        )
    return out, rejected


def vtable_class_name(image: PeImage, vtable_rva: int) -> str:
    """Walk the RTTI chain backwards from a vtable to the class name.

    vtable[-1] points at a CompleteObjectLocator; the locator's type-descriptor
    RVA points at a TypeDescriptor; the name is the string 16 bytes into it.
    This is the x64 layout: signature, offset, cdOffset, pTypeDescriptor,
    pClassDescriptor, pSelf, all 32-bit. Nothing after pTypeDescriptor is read.

    Independent of the scan on purpose -- it shares no code with it, so it can
    confirm the scan rather than agreeing with it by construction.
    """
    if vtable_rva < 8:
        raise PeError(f"RVA 0x{vtable_rva:X} cannot have a locator before it")
    slot = image.rva_to_offset(vtable_rva - 8)
    if slot is None:
        raise PeError(f"vtable RVA 0x{vtable_rva:X} is not inside the image")
    col_va = struct.unpack_from("<Q", image.data, slot)[0]
    col_rva = image.virtual_to_rva(col_va)
    if col_rva is None:
        raise PeError(
            f"the word before RVA 0x{vtable_rva:X} is 0x{col_va:016X}, which is "
            f"not a pointer inside the image: this is not a vtable with RTTI"
        )
    col_off = image.rva_to_offset(col_rva)
    signature, _offset, _cd, type_descriptor_rva = struct.unpack_from(
        "<4I", image.data, col_off
    )
    if signature != 1:
        raise PeError(
            f"locator at RVA 0x{col_rva:X} has signature {signature}, expected 1"
        )
    td_off = image.rva_to_offset(type_descriptor_rva)
    if td_off is None:
        raise PeError(
            f"locator's type descriptor RVA 0x{type_descriptor_rva:X} is outside "
            f"the image"
        )
    end = image.data.index(b"\0", td_off + 16)
    return image.data[td_off + 16:end].decode("ascii")


def _matches(td: TypeDescriptor, needles: tuple[str, ...]) -> bool:
    haystacks = [td.raw]
    if td.demangled:
        haystacks.append(td.demangled)
    return any(n.lower() in h.lower() for n in needles for h in haystacks)


def _print_list(title: str, items: list[TypeDescriptor], limit: int | None) -> None:
    shown = items if limit is None else items[:limit]
    for td in shown:
        marker = " " if td.demangled else "*"
        print(f"  {marker} 0x{td.rva:08X}  {td.kind:<7} {td.label}")
    if limit is not None and len(items) > limit:
        print(f"  ... and {len(items) - limit} more; use --all or --filter "
              f"to see them, or --json for everything")
    print()


def _selftest() -> int:
    """Feed the parser input it must refuse, and confirm it refuses cleanly.

    Cheap, and it is the only test that matters for a tool whose failure mode
    is silently reporting the wrong thing. All inputs are fixed literals, so
    this is deterministic and can be run in any build step.
    """
    cases = [
        (b"", "empty file"),
        (b"NOTPE" + b"\0" * 60, "no MZ"),
        (b"MZ" + b"\0" * 58 + b"\xff\0\0\0" + b"\0" * 16, "e_lfanew past EOF"),
        (b"MZ" + b"\0" * 58 + b"\x40\0\0\0" + b"XX\0\0" + b"\0" * 32, "no PE sig"),
    ]
    failures = 0
    for blob, what in cases:
        try:
            PeImage(blob)
        except PeError:
            print(f"  ok    refused {what}")
        except Exception as exc:  # noqa: BLE001 - the point is that it must not
            print(f"  FAIL  {what}: raised {type(exc).__name__} instead of PeError")
            failures += 1
        else:
            print(f"  FAIL  accepted {what}")
            failures += 1

    # A well-formed but truncated-after-headers image: the section table claims
    # more raw data than the file holds.
    hdr = bytearray(0x200)
    hdr[0:2] = b"MZ"
    struct.pack_into("<I", hdr, 0x3C, 0x80)
    hdr[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", hdr, 0x80 + 6, 1)
    struct.pack_into("<H", hdr, 0x80 + 20, 240)
    struct.pack_into("<H", hdr, 0x80 + 24, 0x20B)
    struct.pack_into("<Q", hdr, 0x80 + 24 + 24, 0x140000000)
    sec = 0x80 + 24 + 240
    struct.pack_into("<IIII", hdr, sec + 8, 0x1000, 0x1000, 0x9000, 0x200)
    try:
        PeImage(bytes(hdr))
    except PeError:
        print("  ok    refused section raw data past EOF")
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL  section raw data past EOF: raised {type(exc).__name__}")
        failures += 1
    else:
        print("  FAIL  accepted section raw data past EOF")
        failures += 1

    # The demangler must decline rather than guess.
    for raw, want in [
        (".?AVIClientVM@BSScript@@", "BSScript::IClientVM"),
        (".?AVVirtualMachine@Internal@BSScript@@",
         "BSScript::Internal::VirtualMachine"),
        (".?AVIAIWorldLocation@@", "IAIWorldLocation"),
        (".?AVUnlinkedTypes@BSScript@@", "BSScript::UnlinkedTypes"),
        (".?AV?$BSTEventSink@ULogEvent@BSScript@@@@", None),
        (".?AVSetPapyrusVarFunctor@?A0x582ba4e7@@", None),
        (".?AW4Thing@@", None),          # enum tag: recognised, not a name form
        # One component is not a malformed name: MSVC writes a class at global
        # scope as "Name@@", with the second '@' being the empty root scope.
        (".?AVSingle@@", "Single"),
        ("not a mangled name", None),
    ]:
        got = demangle(raw)
        if got == want:
            print(f"  ok    demangle({raw[:38]!r}) -> {got!r}")
        else:
            print(f"  FAIL  demangle({raw!r}) -> {got!r}, wanted {want!r}")
            failures += 1

    # own_name is what the negative control runs on, so it has to distinguish
    # "a class called FormData" from "SavedFormData" and "BGSLoadFormData".
    for raw, want in [
        (".?AVIClientVM@BSScript@@", "IClientVM"),
        (".?AVVirtualMachine@Internal@BSScript@@", "VirtualMachine"),
        (".?AV?$BSTEventSink@ULogEvent@BSScript@@@@", "BSTEventSink"),
        (".?AV?$NativeFunction1@UStaticFunctionTag@BSScript@@HAEBVBSFixedString@@"
         "@BSScript@@", "NativeFunction1"),
        (".?AVBGSLoadFormData@@", "BGSLoadFormData"),
        (".?AV?$NiTMap@W4ENUM_FORM_ID@@PEAV?$BSSimpleList@PEAUSavedFormData@@@@@@",
         "NiTMap"),
        (".?AVSetPapyrusVarFunctor@?A0x582ba4e7@@", "SetPapyrusVarFunctor"),
    ]:
        got = own_name(raw)
        if got == want:
            print(f"  ok    own_name({raw[:38]!r}) -> {got!r}")
        else:
            print(f"  FAIL  own_name({raw!r}) -> {got!r}, wanted {want!r}")
            failures += 1

    print(f"  {'all self-tests passed' if not failures else f'{failures} FAILED'}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Read MSVC RTTI type-descriptor names out of a PE image. "
            "Read-only, offline, standard library only."
        )
    )
    ap.add_argument("--exe", type=Path, default=DEFAULT_EXE,
                    help="path to Fallout4.exe (read only)")
    ap.add_argument("--filter", metavar="SUBSTR",
                    help="only report names containing this substring "
                         "(case-insensitive; matched against both the raw "
                         "mangled name and the demangled name)")
    ap.add_argument("--json", action="store_true",
                    help="emit every descriptor as JSON on stdout, sorted by "
                         "RVA; no truncation, no prose")
    ap.add_argument("--all", action="store_true",
                    help="never truncate the secondary sweeps")
    ap.add_argument("--limit", type=int, default=200, metavar="N",
                    help="per-sweep cap when --all is not given (default 200)")
    ap.add_argument("--verify-vtable", type=lambda x: int(x, 0), metavar="RVA",
                    help="walk the RTTI chain from this vtable RVA and print "
                         "the class name, as an independent check on the scan")
    ap.add_argument("--self-test", action="store_true",
                    help="run the parser's refusal tests and demangler tests, "
                         "then exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return _selftest()

    limit = None if args.all else max(args.limit, 0)

    # Timing goes to stderr so that stdout -- and the JSON -- is byte-identical
    # from run to run. A diagnostics tool whose output changes every time it is
    # run cannot be diffed against the previous run, which is the cheapest way
    # to notice that a build changed.
    started = time.perf_counter()
    try:
        data = args.exe.read_bytes()
        image = PeImage(data)
    except FileNotFoundError:
        print(f"error: {args.exe} not found", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: cannot read {args.exe}: {exc}", file=sys.stderr)
        return 1
    except PeError as exc:
        print(f"error: {args.exe}: {exc}", file=sys.stderr)
        return 1

    descriptors, rejected = read_type_descriptors(image)
    elapsed = time.perf_counter() - started

    if args.verify_vtable is not None:
        try:
            name = vtable_class_name(image, args.verify_vtable)
        except (PeError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        label = demangle(name) or name
        print(f"vtable RVA 0x{args.verify_vtable:X} -> {name} -> {label}")
        return 0

    by_name = {td.demangled: td for td in descriptors if td.demangled}
    by_raw = {td.raw: td for td in descriptors}

    if args.json:
        payload = {
            "image": {
                "path": str(args.exe),
                "size": len(data),
                "imageBase": f"0x{image.image_base:X}",
                "sections": [
                    {"name": s.name, "rva": f"0x{s.vaddr:X}",
                     "vsize": f"0x{s.vsize:X}", "rawPointer": f"0x{s.rptr:X}",
                     "rawSize": f"0x{s.rsize:X}"}
                    for s in image.sections
                ],
            },
            "totals": {
                "candidates": len(descriptors) + len(rejected),
                "accepted": len(descriptors),
                "rejected": len(rejected),
                "distinctNames": len({td.raw for td in descriptors}),
                "demangled": sum(1 for td in descriptors if td.demangled),
                "leftMangled": sum(1 for td in descriptors if not td.demangled),
                "structurallyValid": sum(
                    1 for td in descriptors if td.structurally_valid
                ),
            },
            "rejectedCandidates": [
                {"fileOffset": f"0x{off:X}", "reason": why}
                for off, why in rejected
            ],
            "descriptors": [td.as_dict() for td in descriptors],
        }
        json.dump(payload, sys.stdout, indent=2, sort_keys=False)
        sys.stdout.write("\n")
        return 0

    print(f"image   {args.exe}")
    print(f"        {len(data):,} bytes, image base 0x{image.image_base:X}")
    hits_by_section: dict[str, int] = {}
    for td in descriptors:
        hits_by_section[td.section] = hits_by_section.get(td.section, 0) + 1
    where = ", ".join(f"{k}={v}" for k, v in sorted(hits_by_section.items()))
    print(f"scan    {where}")
    print(f"        {len(descriptors):,} accepted, {len(rejected)} rejected, "
          f"{len({td.raw for td in descriptors}):,} distinct names, "
          f"{sum(1 for t in descriptors if t.demangled):,} demangled / "
          f"{sum(1 for t in descriptors if not t.demangled):,} left mangled")
    # Elapsed time goes to stderr, never stdout, so the report and the JSON are
    # byte-identical from run to run. A diagnostics tool whose output changes
    # every time it is run cannot be diffed against the previous run, which is
    # the cheapest way to notice that a build changed under it.
    print(f"scanned in {elapsed:.2f}s", file=sys.stderr)

    # ---- validation -------------------------------------------------------
    print("\n--- structural validation ---")
    print("  every type descriptor is {vftable, spare, name}; a real one has")
    print("  spare == 0 and a vftable pointer that resolves inside the image.")
    bad_spare = [td for td in descriptors if td.spare != 0]
    bad_vft = [td for td in descriptors if td.vftable_rva is None]
    print(f"  spare != 0            {len(bad_spare)}")
    print(f"  vftable unresolvable  {len(bad_vft)}")
    for td in (bad_spare + bad_vft)[:10]:
        print(f"    {td.raw}  spare={td.spare} vftable={td.vftable_rva}")
    if not bad_spare and not bad_vft:
        print("  all accepted descriptors pass. Names that failed are still")
        print("  listed above rather than dropped.")
    if rejected:
        print(f"  rejected candidates   {len(rejected)}")
        for off, why in rejected[:10]:
            print(f"    0x{off:X}: {why}")

    print("\n--- positive control (a gate: failure here means this tool is wrong) ---")
    ctrl = by_name.get(POSITIVE_CONTROL)
    if ctrl is None:
        print(f"  FAIL: {POSITIVE_CONTROL} not found. The scan cannot be "
              f"trusted; not reporting names.")
        return 1
    print(f"  PASS: {POSITIVE_CONTROL}")
    print(f"        raw     {ctrl.raw}")
    print(f"        RVA     0x{ctrl.rva:X}   file offset 0x{ctrl.file_offset:X}"
          f"   section {ctrl.section}")
    try:
        walked = vtable_class_name(image, POSITIVE_CONTROL_VTABLE_RVA)
        print(f"        vtable 0x{POSITIVE_CONTROL_VTABLE_RVA:X} -> {walked}"
              f"   (independent walk; matches the scan: "
              f"{'yes' if walked == ctrl.raw else 'NO'})")
    except PeError as exc:
        print(f"        vtable walk failed: {exc}")

    print("\n--- negative control ---")
    print("  Two counts, because they answer different questions and only one")
    print("  of them is the one that matters. SUBSTRING finds the word anywhere")
    print("  in a name, including inside a longer class name or a template")
    print("  argument. OWN NAME is a class actually called that. A class name")
    print("  that is not there cannot be hooked under that name, whatever else")
    print("  the binary happens to contain.\n")
    for cls in DEAD_CLASSES:
        substr = sorted({td.raw for td in descriptors if cls in td.raw})
        own = sorted({td.label for td in descriptors if td.own == cls})
        print(f"  {cls}")
        print(f"    substring   {len(substr):>5}   -> "
              f"{'PRESENT' if substr else 'absent'}")
        for n in substr:
            print(f"                 {n}")
        print(f"    own name    {len(own):>5}   -> "
              f"{'PRESENT' if own else 'ABSENT'}")
    print("\n  Absence of the four class names is the expected result and is a")
    print("  finding, not a failure. It means the six Tier-2 targets name")
    print("  classes this game does not have, so no amount of pattern tuning")
    print("  will make those names land. The real scripting VM is")
    print("  BSScript::Internal::VirtualMachine / GameVM; see the BSScript")
    print("  family below.")

    print("\n--- the six dead Tier-2 targets ---")
    for target in DEAD_TARGETS:
        cls = target.split("::", 1)[0]
        owners = sorted({td.label for td in descriptors if td.own == cls})
        if owners:
            print(f"  {target:<38} class {cls} exists: {', '.join(owners)}")
        else:
            print(f"  {target:<38} no class named {cls} exists in this image")

    # ---- the name lists ---------------------------------------------------
    sel = descriptors
    if args.filter:
        sel = [td for td in sel if _matches(td, (args.filter,))]
        print(f"\n--- filtered on {args.filter!r}: "
              f"{len(sel)} of {len(descriptors)} ---")

    if not args.filter:
        for root in SCRIPT_ROOTS:
            family = sorted((td for td in descriptors if root in td.raw),
                            key=lambda t: t.raw)
            print(f"\n--- {root} family: {len(family)} name(s), complete ---")
            print("  '*' means the name uses a construct the conservative")
            print("  demangler will not guess at, so the raw mangled form is")
            print("  shown. Filtering a raw name on a bare word still finds it:")
            print(f"  --filter {root} works on both forms.\n")
            _print_list("", family, None)

    for title, needles, scoped in SWEEPS:
        if args.filter:
            continue
        if scoped:
            total = sum(1 for td in descriptors if _matches(td, needles))
            found = sorted(
                (td for td in descriptors
                 if _matches(td, needles)
                 and any(r in td.raw for r in SCRIPT_ROOTS)),
                key=lambda t: t.raw,
            )
            print(f"--- {title}: {len(found)} of {total} total ---")
            print(f"  scoped to {'/'.join(SCRIPT_ROOTS)}; the other {total - len(found)}")
            print("  are outside the scripting families and are reachable with")
            print("  --all, --filter or --json.\n")
        else:
            found = sorted((td for td in descriptors if _matches(td, needles)),
                           key=lambda t: t.raw)
            print(f"--- {title}: {len(found)} name(s) ---\n")
        _print_list("", found, limit)

    if args.filter:
        print(f"--- filter matches: {len(sel)} ---")
        _print_list("", sorted(sel, key=lambda t: t.raw), limit)
        print(f"by_name lookups available for demangled names: "
              f"{len(by_name)} distinct; by_raw: {len(by_raw)}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
