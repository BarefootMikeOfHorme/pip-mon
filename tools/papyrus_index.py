"""Papyrus index: generate the FO4 function index from the shipped base scripts.

THE GAP THIS EXISTS FOR
    ai_context/papyrus_syntax_rules.md holds the only machine-readable-adjacent
    statement of what FO4 Papyrus can and cannot do, and its most valuable half
    is a hand-written NEGATIVE table: the Skyrim habits that do not exist here.
    It is good, it is partial, and it is prose, so nothing can branch on it.

    The table was also found to be WRONG on its first two rows when checked
    against the shipped scripts rather than against recollection. Measured on
    this machine, 2026-10-03, root Source/Base:

        papyrus_syntax_rules.md:39  "CustomEvent, SendEvent -- SKSE-only. Not in
                                    FO4 ... Zero occurrences across the 41 CK
                                    base scripts."
        MEASURED                   52 `customEvent` declarations in the FO4 base
                                    scripts, e.g. ArtilleryReferenceScript.psc:37
                                    `CustomEvent FinishedFiring`,
                                    BirdSpawnerScript.psc:14 `customEvent flee`.

        papyrus_syntax_rules.md:40  "There is no `Debug` script in FO4 at all."
        MEASURED                   Source/Base/Debug.psc EXISTS and declares 40
                                    functions.

    ai_context/spec/papyrus_constructs.json already recorded BOTH corrections on
    2026-09-30, with the same file:line evidence, and the markdown was never
    brought into line. So the knowledge existed and the two documents disagreed.
    That is the actual failure mode: a hand-maintained table drifts from the
    thing it describes, and nothing notices because nothing can read it.

    So this GENERATES the table instead of writing it. Everything below is read
    out of the shipped .psc sources; nothing is recalled.

WHAT IT READS, AND WHAT IT DELIBERATELY DOES NOT
    Source root (default, and asserted -- see the FO4-ONLY section):
        <FO4>/Data/Scripts/Source/Base, recursively.

    NOT read, and the reasons are load-bearing rather than incidental:

      Source/User/            66 .psc. The directory carries a Vortex marker
                              file, so its contents are MOD content on this
                              machine, not shipped Bethesda source. Indexing it
                              would make the index a statement about the modlist.
      Source/DLC0*.zip        the DLC scripts ship as archives. Reading them
                              means extracting, and extraction writes outside the
                              project, which policy section 8 forbids. So every
                              usage count here is a LOWER BOUND.
      Creation Kit install    not present on this machine (verified), so the
                              "41 CK base scripts" the markdown cites cannot be
                              re-measured here.

    Count discrepancy worth recording: the task brief describes 7,932 .psc under
    Source/Base. Measured, Source/Base holds 7,854 and Source/ in total holds
    7,932 -- the difference is exactly the 66 User scripts plus the zip archives.
    The brief's number is the Source total; this tool indexes the Base subtree.

FO4-ONLY, ASSERTED IN BOTH DIRECTIONS, LOUDLY
    Skyrim contamination is a named live hazard: ai_context/spec/nomenclature.json
    records CK and GECK being conflated repeatedly, and ck_command_reference.md
    warns about it. An index that quietly absorbed Skyrim would be worse than no
    index, because it would be believed.

    So the source root is checked against the FO4 path and refused if it looks
    like Skyrim's, every parsed file is scanned for SKYRIM_ONLY_MARKERS, and --
    the half that matters -- the run also requires FO4_ONLY_STRUCTURE to be
    PRESENT. A negative-only assertion passes vacuously on an empty directory,
    which is the usual way "we checked and found nothing" turns into "we checked
    nothing". Both halves must hold or the tool exits non-zero and writes
    nothing.

    SKYRIM_ONLY_MARKERS is measured, not guessed. Every entry was confirmed to
    occur ZERO times across all 7,854 files before being put in the table, so
    adding it cannot turn this gate permanently red on committed, correct data.
    `SendEvent` is deliberately NOT in the table, and the reason is the most
    interesting result in the run: it occurs 3 times, as a LOCALLY DEFINED
    script function at CA_TopicInfoScript.psc:36, not as an engine builtin. That
    is exactly why the index keys on ScriptName.FunctionName -- a bare-name
    existence test would have reported the FO4 engine as having SendEvent.

    `Start`, `Stop`, `Update`, `Cancel`, `Menu`, `GetSize` are also excluded as
    markers: all occur in FO4 source (2380/1885/908/31/123/39 times), so they
    discriminate nothing. GetSize is receiver-dependent rather than absent --
    FormList declares it, a plain array cannot -- which
    ai_context/spec/papyrus_constructs.json already records.

WHAT A TEXT-BASED PARSER CANNOT SEE. Stated here because the blind spots are the
part most likely to be discovered later by someone else:

  * It reads SOURCE, never a compiled .pex. So it can say a function is DECLARED
    and it cannot say the function is COMPILED, REGISTERED, REACHABLE or
    DISPATCHABLE. The authority of everything written here is `measured`, at
    best, and never `compile-verified`: no compiler was launched, because policy
    section 8 forbids it and because none is needed to read a declaration.
  * Overloads are invisible. Papyrus resolves on the receiver's static type, so
    two scripts may declare the same name with different arities and a text scan
    reports both without being able to say which applies at a given call site.
    Same name + different arity is reported as `overloaded_names`, not resolved.
  * INHERITANCE IS NOT RESOLVED. A call to a function declared only on a parent
    script reads as a call to something this build does not declare. That is the
    `called_but_not_declared` finding, and it is a floor, not a proof of absence.
  * A usage count of zero does NOT mean dead. Event handlers are invoked by the
    engine and by other scripts, never called; `global` functions are reachable
    from the console and from native code. Only `functions` are counted against
    call sites, and zero is reported as "zero observed calls in this corpus",
    never as "unused".
  * Dynamic dispatch through a Var[] payload cannot be resolved, so calls made
    through a cast or a Var cannot be attributed to a name at all.
  * Comment syntax is assumed to be `;`, `;/ ... /;`, and a brace block that
    opens at the start of a line. That third rule is inherited from
    gen_papyrus_ref.py so the two extractors agree; if FO4 has a third comment
    form neither tool sees it. Measured: 3,402 lines open a brace block and 107
    lines carry /;.
  * Papyrus has STATES, and ignoring them does not degrade the index, it
    DELETES from it. `State Done ... EndState` wraps a second independent set of
    declarations and the same event name is legal once per state: 308 of the
    7,854 scripts declare 661 states. An earlier draft of this parser flattened
    states and then reported 225 event handlers as duplicates of others. State
    awareness is why `attributes` keys are `Script.State.Event` inside a state
    and `Script.Event` outside one. This is recorded because it is the failure
    mode that looked like a rounding error and was not.
  * Papyrus also has `Group ... EndGroup` (639 uses) and the `conditional`
    script and property flags. Groups are recorded on each declaration as `group`
    because a CK-facing reader needs them; they do not affect identity.
  * SCRIPT-TYPED SCRIPT VARIABLES are not modelled. A line such as
    `protectronScript protectronRefScript` declares a variable whose type is
    another script; it is a declaration this tool does not capture, and it is the
    one declaration form found in the corpus that the index is blind to. It is
    blind in a harmless direction -- it holds no function signature.
  * A function whose declared return type is non-void but whose body never
    returns a value is accepted silently. Real example:
    abProtectronRaceScript.psc declares `bool function shutDownAllScenes()` with
    no return statement. Whether the compiler accepts that is NOT verified here,
    because verifying it needs a compiler and policy section 8 forbids one.
  * Multi-line signatures are joined on a trailing backslash (11 declarations).
    A signature continued some other way would be missed, not misparsed, because
    every declaration pattern is anchored to the start of a line.

    A line-numbered provenance that points one line off is worse than none,
    because it looks checkable. So the stripper is LENGTH-PRESERVING: every
    removed character becomes a space and newlines stay newlines, and the 65
    lines whose string literals contain a semicolon are handled by blanking
    string contents rather than by cutting at the first `;`.

    python tools/papyrus_index.py                  # generate
    python tools/papyrus_index.py --limit 200      # sample, for a fast look
    python tools/papyrus_index.py --json           # machine-readable summary
    python tools/papyrus_index.py --root PATH      # a different source root
"""
import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "ai_context" / "spec" / "papyrus_functions.json"

FO4_DATA = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Fallout 4\Data")
DEFAULT_ROOT = FO4_DATA / "Scripts" / "Source" / "Base"

RUN_ID = "papyrus_index.py/1"
SCAN_DATE = "2026-10-03"

# ---------------------------------------------------------------------------
# Declaration grammar. Every pattern is anchored to the start of a logical line
# and runs against CODE ONLY (comments blanked, string contents blanked), so a
# declaration cannot be manufactured by a comment or by a debug.trace payload
# that happens to contain the word Function.
# ---------------------------------------------------------------------------
RE_SCRIPTNAME = re.compile(
    r"^Scriptname\s+(?P<name>[\w:]+)(?:\s+extends\s+(?P<ext>[\w:]+))?\s*(?P<flags>.*)$",
    re.I)
RE_FUNCTION = re.compile(
    r"^(?:(?P<ret>[A-Za-z_][\w:]*(?:\[\])?)\s+)?Function\s+(?P<name>\w+)\s*"
    r"\((?P<params>[^)]*)\)\s*(?P<flags>.*)$", re.I)
RE_EVENT = re.compile(
    r"^Event\s+(?P<name>[\w.]+)\s*\((?P<params>[^)]*)\)\s*(?P<flags>.*)$", re.I)
RE_PROPERTY = re.compile(
    r"^(?P<type>[A-Za-z_][\w:]*(?:\[\])?)\s+Property\s+(?P<name>\w+)"
    r"(?:\s*=\s*(?P<default>\S*))?\s*(?P<flags>.*)$", re.I)
RE_CUSTOMEVENT = re.compile(r"^[Cc]ustomEvent\s+(?P<name>\w+)", re.I)
RE_STRUCT = re.compile(r"^Struct\s+(?P<name>\w+)", re.I)
# Papyrus has STATES: `State Done ... EndState` wraps a second, independent set of
# declarations, and the SAME event name is legitimately declared once per state.
# 308 of the 7,854 scripts use them, 661 times. A parser that ignores State
# flattens the states together and reports one event where there are several --
# which is not a rounding error, it silently deletes handlers: an early draft of
# this tool discarded 262 of them as apparent duplicates before State was handled.
RE_STATE = re.compile(
    r"^(?:(?P<auto>auto)\s+)?state\s+(?P<name>\w+)\s*(?P<flags>.*)$", re.I)
RE_GROUP = re.compile(r"^group\s+(?P<name>\w+)\s*(?P<flags>.*)$", re.I)
RE_PARAM = re.compile(
    r"^(?:(?P<type>[A-Za-z_][\w:]*(?:\[\])?)\s+)?(?P<name>\w+)"
    r"(?:\s*=\s*(?P<default>.*))?$", re.I)

# Flag words. `hidden` is here because the index is asked to report it, and the
# honest answer turns out to be that FO4 never uses it on a declaration.
FUNC_FLAGS = {"native", "global", "hidden", "const", "debugonly", "betaonly", "conditional"}
SCRIPT_FLAGS = {"native", "hidden", "debugonly", "betaonly", "const", "conditional"}
PROP_FLAGS = {"auto", "readonly", "conditional", "const"}

# A call is `Name(` or `Receiver.Name(`. The lookbehind is what keeps the bare
# form from also counting the qualified one, which would double-count every
# cross-script call -- and cross-script calls are exactly the ones this project
# gets wrong most often (see papyrus_syntax_rules.md section 5).
#
# Two constraints that are load-bearing rather than stylistic:
#   * the name must START with a letter or underscore, because a numeric literal
#     before a paren (`= 1 (a + b)`) otherwise registers as a call named "1";
#   * the gap before the paren is [ \t]*, not \s*. \s spans newlines, and since
#     a blanked comment line becomes a run of spaces, \s* welds an identifier at
#     the end of one declaration onto a paren several lines below. That is how
#     "EndFunction" and "EndGroup" arrived in the called-but-not-declared list.
RE_CALL_BARE = re.compile(r"(?<![.\w])(?P<name>[A-Za-z_]\w*)[ \t]*\(")
RE_CALL_QUAL = re.compile(r"(?<![.\w])(?P<recv>[A-Za-z_]\w*)\.(?P<name>[A-Za-z_]\w*)[ \t]*\(")

# Papyrus keywords. `if (x)` and `elseif (y)` are syntactically identical to a
# one-argument call, so without this the index reports the language's own
# control flow as functions the game calls hundreds of times.
KEYWORDS = {
    "scriptname", "extends", "function", "endfunction", "event", "endevent",
    "property", "endproperty", "struct", "endstruct", "customevent", "if",
    "elseif", "else", "endif", "while", "endwhile", "loop", "endloop",
    "return", "switch", "case", "default", "endswitch", "of", "to", "step",
    "in", "as", "new", "delete", "assert", "goto", "label", "global",
    "native", "const", "auto", "readonly", "hidden", "debugonly", "betaonly",
    "type", "self", "parent", "none", "true", "false", "not", "and", "or",
    "explicit", "implicit", "int", "float", "string", "bool", "form", "var",
}

# ---------------------------------------------------------------------------
# SKYRIM_ONLY_MARKERS. Each row was MEASURED at zero occurrences across all
# 7,854 files of Source/Base before being listed. A marker nobody measured is a
# guess, and a guessed marker is how a gate ends up permanently red on correct
# data, which is decoration.
# ---------------------------------------------------------------------------
SKYRIM_ONLY_MARKERS = {
    "SkyUI": "Skyrim's UI framework; FO4 has no SkyUI namespace",
    "SKSE": "Skyrim Script Extender",
    "GetOwningObjectOfThread":
        "SKSE; recorded absent in FO4 at ai_context/papyrus_syntax_rules.md:48",
    "SpawnThreadFromCustomEvent":
        "SKSE; papyrus_syntax_rules.md:50 records that NO FO4 script can start a "
        "second thread",
    "IsValidRef": "SKSE; papyrus_syntax_rules.md:51",
    "SetGlobalFlag": "SKSE; papyrus_syntax_rules.md:52",
    "GetLocalFlag": "SKSE; papyrus_syntax_rules.md:52",
    "GetFormIDFromEvent": "papyrus_syntax_rules.md:53",
    "CreateObjectAtForm": "papyrus_syntax_rules.md:45",
    "RegisterForEvent":
        "ai_context/spec/papyrus_constructs.json records exists_in_fo4 false",
    "Skyrim.esm": "the Skyrim master, named in a script",
}

# ---------------------------------------------------------------------------
# FO4_ONLY_STRUCTURE. The positive half of the assertion. Each of these is
# something a Skyrim install does not have, so their presence PROVES the root is
# FO4 rather than merely failing to look like Skyrim.
# ---------------------------------------------------------------------------
FO4_ONLY_STRUCTURE = {
    "dir_creation_club": "CreationClub/ -- the Creation Club script set is an FO4 feature",
    "dir_hardcore": "Hardcore/ -- Survival Mode scripts, an FO4 mode",
    "dir_fragments_terminals": "Fragments/Terminals/ -- the FO4 dialogue terminal system",
    "dir_fragments_topicinfos": "Fragments/TopicInfos/ -- FO4 dialogue fragments",
    "script_debug_psc": "Debug.psc -- the FO4 Debug script, 40 functions",
    "script_cc_prefix": "a CC_*.psc script -- Creation Club naming",
}

# ---------------------------------------------------------------------------
# The negative table being cross-checked, transcribed from
# ai_context/papyrus_syntax_rules.md section 1 with its line numbers. The claim
# text is the markdown's, not this file's: if the index disagrees with the
# markdown, the DISAGREEMENT is the output and the markdown is not edited here
# because it belongs to another owner.
#
# `probe` says what the markdown's claim is actually about, because "the name
# does not exist" and "the name exists but not in the role you mean" are
# different findings and conflating them would be its own kind of lie:
#
#   function             a bare-name function declaration
#   script               a ScriptName declaration
#   custom_event_keyword any use of the `customEvent` DECLARATION keyword, whose
#                        declared name is something else entirely (FinishedFiring,
#                        flee, CGShockWaveAnimEvent), so it can only be probed at
#                        keyword level
#   property_type        use as a property type
#
# The engine/script split is decided by the `native` FLAG ON THE DECLARING
# SCRIPT, not by a hand-written list of engine types. That is measurable, and it
# rests on a rule the project has already compile-verified: a Papyrus function may
# be declared Native only if its script is also flagged Native
# (papyrus_syntax_rules.md section 4). Engine-provided base-type scripts are
# flagged Native; an ordinary quest script is not.
# ---------------------------------------------------------------------------
NEGATIVE_TABLE = [
    {"token": "CustomEvent", "probe": "custom_event_keyword", "md_line": 39,
     "md_claim": "SKSE-only. Not in FO4. Zero occurrences across the 41 CK base scripts."},
    {"token": "SendEvent", "probe": "function", "md_line": 39,
     "md_claim": "SKSE-only. Not in FO4."},
    {"token": "Debug", "probe": "script", "md_line": 40,
     "md_claim": "There is no Debug script in FO4 at all."},
    {"token": "Menu", "probe": "property_type", "md_line": 41,
     "md_claim": "Menu/Option property types are not Papyrus types in FO4."},
    {"token": "Option", "probe": "property_type", "md_line": 41,
     "md_claim": "Menu/Option property types are not Papyrus types in FO4."},
    {"token": "GetLength", "probe": "function", "md_line": 43,
     "md_claim": "no array length intrinsic: arr.GetLength() does not exist"},
    {"token": "GetSize", "probe": "function", "md_line": 44,
     "md_claim": "arr.GetSize() does not even parse"},
    {"token": "Count", "probe": "function", "md_line": 44,
     "md_claim": "does not even parse"},
    {"token": "Size", "probe": "function", "md_line": 44,
     "md_claim": "does not even parse"},
    {"token": "CreateObjectAtForm", "probe": "function", "md_line": 45,
     "md_claim": "no runtime spawn from a form ID"},
    {"token": "Start", "probe": "function", "md_line": 46,
     "md_claim": "Skyrim timer API; not a function or does not exist"},
    {"token": "Stop", "probe": "function", "md_line": 46,
     "md_claim": "Skyrim timer API; not a function or does not exist"},
    {"token": "GetOwningObjectOfThread", "probe": "function", "md_line": 48,
     "md_claim": "Skyrim/SKSE"},
    {"token": "Cancel", "probe": "function", "md_line": 49,
     "md_claim": "no Cancel method on ScriptObject"},
    {"token": "SpawnThreadFromCustomEvent", "probe": "function", "md_line": 50,
     "md_claim": "Skyrim/SKSE"},
    {"token": "IsValidRef", "probe": "function", "md_line": 51,
     "md_claim": "Skyrim/SKSE"},
    {"token": "SetGlobalFlag", "probe": "function", "md_line": 52,
     "md_claim": "SKSE global/local flag access"},
    {"token": "GetLocalFlag", "probe": "function", "md_line": 52,
     "md_claim": "SKSE global/local flag access"},
    {"token": "GetFormIDFromEvent", "probe": "function", "md_line": 53,
     "md_claim": "not in this build"},
]


def strip_noise(text):
    """Return the code of a .psc with comments blanked and string bodies blanked.

    Length-preserving, so a match's line number here is its line number in the
    file. Three comment forms are recognised: `;` to end of line, `;/ ... /;`
    across lines, and a brace block that opens at the start of a line -- the
    third inherited from gen_papyrus_ref.py so both extractors agree on the same
    corpus.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    mode = "code"
    for raw in text.split("\n"):
        n = len(raw)
        buf = []
        i = 0
        started = False
        while i < n:
            ch = raw[i]
            if mode == "code":
                if ch == '"':
                    buf.append('"')
                    i += 1
                    while i < n:
                        if raw[i] == '"':
                            buf.append('"')
                            i += 1
                            break
                        buf.append(" ")
                        i += 1
                    continue
                if ch == ";":
                    if raw.startswith(";/", i):
                        mode = "semi"
                        buf.append("  ")
                        i += 2
                        continue
                    break  # the rest of the line is a comment
                if ch == "{" and not started:
                    tail = raw[i:]
                    if "}" in tail:
                        buf.append(" " * (n - i))
                        i = n
                        continue
                    mode = "brace"
                    buf.append(" ")
                    i += 1
                    continue
                if not ch.isspace():
                    started = True
                buf.append(ch)
                i += 1
                continue
            closer = "/;" if mode == "semi" else "}"
            j = raw.find(closer, i)
            if j < 0:
                buf.append(" " * (n - i))
                i = n
            else:
                buf.append(" " * (j + len(closer) - i))
                i = j + len(closer)
                mode = "code"
        lines.append("".join(buf))
    return "\n".join(lines)


def logical_lines(stripped):
    """Yield (first_line_number, joined_code) joining backslash continuations.

    11 declarations in this corpus continue a parameter list onto the next line,
    so the join is load-bearing rather than cosmetic.
    """
    lines = stripped.split("\n")
    i = 0
    while i < len(lines):
        first = i + 1
        cur = lines[i].rstrip()
        while cur.endswith("\\") and i + 1 < len(lines):
            cur = cur[:-1].rstrip()
            i += 1
            cur = cur + " " + lines[i].strip()
        yield first, cur
        i += 1


def flags_of(text, vocabulary):
    return sorted({w.lower() for w in text.split() if w.lower() in vocabulary})


def split_params(text):
    """Split a parameter list on commas. String bodies are already blank, so no
    quote tracking is needed here -- a default like `= "a,b"` cannot split."""
    return [p.strip() for p in text.split(",") if p.strip()]


def parse_params(text):
    """Return [{name, type, default}] in declaration order.

    The type is optional in the pattern because a parameter with no type is
    parseable-but-suspicious, and reporting it as untyped is more useful than
    dropping the parameter and reporting a smaller arity than the source has.
    """
    out = []
    for chunk in split_params(text):
        m = RE_PARAM.match(chunk)
        if not m:
            out.append({"name": chunk, "type": None, "default": None, "parsed": False})
            continue
        default = m.group("default")
        out.append({
            "name": m.group("name"),
            "type": m.group("type"),
            "default": default.strip() if default is not None else None,
            "parsed": True,
        })
    return out


def read_text(path):
    return path.read_text(encoding="utf-8-sig", errors="replace")


def parse_script(path, rel):
    stripped = strip_noise(read_text(path))
    rec = {
        "file": rel,
        "script_name": None,
        "extends": None,
        "script_flags": [],
        "functions": [],
        "events": [],
        "properties": [],
        "custom_events": [],
        "structs": [],
        "states": [],
        "declaration_lines": set(),
    }
    in_struct = False
    in_property = False
    state = None
    group = None
    for lineno, code in logical_lines(stripped):
        s = code.strip()
        if not s:
            continue
        if in_struct:
            if s.lower().startswith("endstruct"):
                in_struct = False
            continue
        if in_property:
            if s.lower().startswith("endproperty"):
                in_property = False
            continue

        low = s.lower()

        if state is not None and low.startswith("endstate"):
            state = None
            rec["declaration_lines"].add(lineno)
            continue
        if group is not None and low.startswith("endgroup"):
            group = None
            rec["declaration_lines"].add(lineno)
            continue

        m = RE_SCRIPTNAME.match(s)
        if m and not rec["script_name"]:
            rec["script_name"] = m.group("name")
            rec["extends"] = m.group("ext")
            rec["script_flags"] = flags_of(m.group("flags") or "", SCRIPT_FLAGS)
            rec["scriptname_line"] = lineno
            rec["declaration_lines"].add(lineno)
            continue

        m = RE_STATE.match(s)
        if m:
            state = m.group("name")
            rec["states"].append({
                "name": state,
                "auto": bool(m.group("auto")),
                "flags": flags_of(m.group("flags") or "", SCRIPT_FLAGS),
                "line": lineno,
            })
            rec["declaration_lines"].add(lineno)
            continue

        m = RE_GROUP.match(s)
        if m:
            group = m.group("name")
            rec["declaration_lines"].add(lineno)
            continue

        m = RE_STRUCT.match(s)
        if m:
            rec["structs"].append({"name": m.group("name"), "line": lineno})
            in_struct = True
            rec["declaration_lines"].add(lineno)
            continue

        m = RE_CUSTOMEVENT.match(s)
        if m:
            rec["custom_events"].append({"name": m.group("name"), "line": lineno,
                                         "state": state, "group": group})
            rec["declaration_lines"].add(lineno)
            continue

        m = RE_PROPERTY.match(s)
        if m:
            flags = flags_of(m.group("flags") or "", PROP_FLAGS)
            rec["properties"].append({
                "name": m.group("name"),
                "type": m.group("type"),
                "default": m.group("default") or None,
                "flags": flags,
                "line": lineno,
                "state": state,
                "group": group,
            })
            rec["declaration_lines"].add(lineno)
            if "auto" not in flags:
                in_property = True
            continue

        m = RE_EVENT.match(s)
        if m:
            name = m.group("name")
            params = parse_params(m.group("params"))
            rec["events"].append({
                "name": name,
                "qualified": "." in name,
                "sender": name.split(".")[0] if "." in name else None,
                "arity": len(params),
                "parameters": params,
                "return_type": None,
                "flags": flags_of(m.group("flags") or "", FUNC_FLAGS),
                "line": lineno,
                "state": state,
                "group": group,
            })
            rec["declaration_lines"].add(lineno)
            continue

        m = RE_FUNCTION.match(s)
        if m:
            params = parse_params(m.group("params"))
            rec["functions"].append({
                "name": m.group("name"),
                "arity": len(params),
                "parameters": params,
                "return_type": m.group("ret"),
                "flags": flags_of(m.group("flags") or "", FUNC_FLAGS),
                "line": lineno,
                "state": state,
                "group": group,
            })
            rec["declaration_lines"].add(lineno)
            continue

    if not rec["script_name"]:
        rec["script_name"] = path.stem
        rec["script_name_inferred"] = True
    rec["declaration_lines"] = sorted(rec["declaration_lines"])
    return rec, stripped


def scan_calls(stripped, declaration_lines):
    """Count call sites, separating bare calls from receiver-qualified ones.

    Declaration lines are blanked first: a declaration is syntactically a call,
    and counting it would give every function a free hit of one and make a
    never-called function look called exactly once.
    """
    lines = stripped.split("\n")
    for ln in declaration_lines:
        if 1 <= ln <= len(lines):
            lines[ln - 1] = ""
    text = "\n".join(lines)
    bare = Counter()
    qual = Counter()
    receivers = defaultdict(Counter)
    for m in RE_CALL_BARE.finditer(text):
        name = m.group("name")
        if name.lower() in KEYWORDS:
            continue
        bare[name] += 1
    for m in RE_CALL_QUAL.finditer(text):
        name = m.group("name")
        if name.lower() in KEYWORDS:
            continue
        qual[name] += 1
        # Receiver keys are folded too. They are identifiers in the same
        # case-insensitive language, and an unfolded receiver map puts `Math` and
        # `math` in one JSON object, which PowerShell's ConvertFrom-Json refuses
        # to load -- so this is a loadability requirement, not a preference.
        receivers[name][m.group("recv").lower()] += 1
    return bare, qual, receivers


def scan_markers(stripped, rel):
    hits = []
    for lineno, code in logical_lines(stripped):
        low = code.lower()
        for marker in SKYRIM_ONLY_MARKERS:
            if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])"
                         % re.escape(marker.lower()), low):
                hits.append({"marker": marker, "file": rel, "line": lineno})
    return hits


def check_root(root):
    """Two-sided source-root assertion. Returns (problems, evidence)."""
    problems = []
    low = str(root).lower()
    if "fallout 4" not in low:
        problems.append(
            "source root %r does not name Fallout 4. This tool indexes FO4 and "
            "refuses to index anything it cannot positively identify." % str(root))
    for impostor in ("skyrim", "geck", "starfield", "creation kit"):
        if impostor in low:
            problems.append(
                "source root %r names %r. Conflating the two installs is a "
                "recorded, repeated failure in this project -- see "
                "ai_context/spec/nomenclature.json." % (str(root), impostor))
    if not root.is_dir():
        problems.append("source root %s does not exist" % root)
    return problems


def check_fo4_structure(root, limit=None):
    """The positive half. Without it the marker scan passes on an empty dir.

    Every check reads the FILESYSTEM rather than the parsed sample, so that
    --limit cannot turn a real FO4 root into a failed assertion. A check that
    depends on how much of the corpus happened to be read is a check that
    reports the sample size, not the install.
    """
    problems = []
    evidence = {}
    checks = {
        "dir_creation_club": (root / "CreationClub").is_dir(),
        "dir_hardcore": (root / "Hardcore").is_dir(),
        "dir_fragments_terminals": (root / "Fragments" / "Terminals").is_dir(),
        "dir_fragments_topicinfos": (root / "Fragments" / "TopicInfos").is_dir(),
        "script_debug_psc": (root / "Debug.psc").is_file(),
        "script_cc_prefix": any(
            p.is_file() and p.name.startswith("CC_")
            for p in (root / "CreationClub").glob("**/*.psc")),
    }
    for key, ok in checks.items():
        evidence[key] = bool(ok)
        if not ok:
            problems.append(
                "FO4-only structure %r is ABSENT (%s). A source root that is "
                "missing every FO4 marker is not proven to be FO4, and a "
                "negative-only assertion cannot tell an FO4 install from an "
                "empty directory." % (key, FO4_ONLY_STRUCTURE.get(key, "")))
    return problems, evidence


def scan(root, limit=None):
    files = sorted(p for p in root.rglob("*.psc") if p.is_file())
    total_available = len(files)
    if limit:
        files = files[:limit]

    scripts = []
    marker_hits = []
    bare_tot = Counter()
    qual_tot = Counter()
    recv_tot = defaultdict(Counter)
    unreadable = []
    total_bytes = 0

    t0 = time.time()
    for i, path in enumerate(files):
        rel = path.relative_to(root).as_posix()
        try:
            total_bytes += path.stat().st_size
            rec, stripped = parse_script(path, rel)
        except OSError as e:
            unreadable.append({"file": rel, "error": str(e)})
            continue
        scripts.append(rec)
        marker_hits.extend(scan_markers(stripped, rel))
        bare, qual, recv = scan_calls(stripped, rec["declaration_lines"])
        bare_tot.update(bare)
        qual_tot.update(qual)
        for name, counter in recv.items():
            recv_tot[name].update(counter)
        if (i + 1) % 1000 == 0:
            print("  ... %d/%d files, %.1fs" % (i + 1, len(files), time.time() - t0),
                  file=sys.stderr)

    return {
        "root": root,
        "files": scripts,
        "file_count": len(scripts),
        "file_count_available": total_available,
        "bytes": total_bytes,
        "marker_hits": marker_hits,
        "bare": bare_tot,
        "qualified": qual_tot,
        "receivers": recv_tot,
        "unreadable": unreadable,
        "seconds": time.time() - t0,
    }


def _claim(store, case_collisions, key, record):
    """Insert a declaration, folding the key case-insensitively.

    Papyrus identifiers are case-insensitive, so two declarations in one script
    that differ only in casing are ONE declaration to the language. Two things
    make this guard necessary rather than decorative:

      * a case-sensitive index reports two events where the compiler sees one;
      * a JSON consumer with a case-insensitive key type cannot load the file at
        all. PowerShell's ConvertFrom-Json -- the verification named in policy
        section 5 -- refuses an object whose keys differ only in case.

    MEASURED, and worth stating because it is the kind of thing that is easy to
    assume: after State is handled, this table is EMPTY. An earlier draft of this
    parser did not handle State, and its case-folding therefore reported 262
    "duplicate" declarations -- TrapTripwire.psc declaring OnActivate at line 76
    and again at 125 among them. Every one of the 262 was a false positive: the
    two OnActivate handlers are in `Auto state Active` and in `state Inactive`
    respectively, and Papyrus permits the same event name once per state. The
    folding is kept as a guard and as a loadability requirement, not because a
    collision has been observed in these 7,854 files.
    """
    folded = key.lower()
    for existing in store:
        if existing.lower() == folded:
            case_collisions.append({
                "name_ci": folded,
                "kept": existing,
                "kept_at": "%s:%d" % (store[existing]["file"], store[existing]["line"]),
                "discarded": key,
                "discarded_at": "%s:%d" % (record["file"], record["line"]),
                "kind": record["kind"],
                "arity_kept": store[existing]["arity"],
                "arity_discarded": record["arity"],
                "same_arity": store[existing]["arity"] == record["arity"],
            })
            return False
    store[key] = record
    return True


def build_records(scan_result):
    """Fold the per-file parse into namespaced records plus the usage index."""
    functions = {}
    events = {}
    scripts = {}
    collisions = defaultdict(list)
    case_collisions = []
    names_by_bare = defaultdict(list)

    for rec in scan_result["files"]:
        ns = rec["script_name"]
        auto_states = {s["name"] for s in rec["states"] if s["auto"]}
        if ns in scripts:
            collisions[ns].append({"file": rec["file"], "line": rec.get("scriptname_line")})
        scripts[ns] = {
            "file": rec["file"],
            "extends": rec["extends"],
            "flags": rec["script_flags"],
            "function_count": len(rec["functions"]),
            "event_count": len(rec["events"]),
            "property_count": len(rec["properties"]),
            "custom_event_count": len(rec["custom_events"]),
            "struct_count": len(rec["structs"]),
            "states": [s["name"] for s in rec["states"]],
            "auto_states": sorted(auto_states),
            "script_name_inferred": bool(rec.get("script_name_inferred")),
        }
        for f in rec["functions"]:
            key = "%s.%s.%s" % (ns, f["state"], f["name"]) if f["state"] \
                else "%s.%s" % (ns, f["name"])
            stored = _claim(functions, case_collisions, key, {
                "kind": "function",
                "script": ns,
                "name": f["name"],
                "file": rec["file"],
                "line": f["line"],
                "extends": rec["extends"],
                "state": f["state"],
                "state_auto": f["state"] in auto_states if f["state"] else None,
                "group": f["group"],
                "arity": f["arity"],
                "parameters": f["parameters"],
                "return_type": f["return_type"],
                "native": "native" in f["flags"],
                "global": "global" in f["flags"],
                "hidden": "hidden" in f["flags"],
                "const": "const" in f["flags"],
                "flags": f["flags"],
            })
            if stored:
                names_by_bare[f["name"]].append(key)
        for e in rec["events"]:
            key = "%s.%s.%s" % (ns, e["state"], e["name"]) if e["state"] \
                else "%s.%s" % (ns, e["name"])
            stored = _claim(events, case_collisions, key, {
                "kind": "event_handler",
                "script": ns,
                "name": e["name"],
                "file": rec["file"],
                "line": e["line"],
                "extends": rec["extends"],
                "state": e["state"],
                "state_auto": e["state"] in auto_states if e["state"] else None,
                "group": e["group"],
                "arity": e["arity"],
                "parameters": e["parameters"],
                "return_type": None,
                "native": False,
                "global": False,
                "hidden": "hidden" in e["flags"],
                "const": False,
                "flags": e["flags"],
                "sender_qualified": e["qualified"],
                "sender": e["sender"],
            })
            if stored:
                names_by_bare[e["name"].split(".")[-1]].append(key)

    names_by_bare_ci = defaultdict(list)
    for bare_name, keys in names_by_bare.items():
        names_by_bare_ci[bare_name.lower()] = sorted(keys)
    declared_ci = set(names_by_bare_ci)

    # Usage. A function's count is bare + qualified call sites of its bare name,
    # which is an UPPER bound on its own calls and a LOWER bound on the family's
    # -- both directions are stated rather than quietly resolved.
    #
    # MATCHING IS CASE-INSENSITIVE, and it has to be: Papyrus identifiers are not
    # case-sensitive, while these scripts are written inconsistently. The same
    # engine call appears as AddItem, addItem and additem in this corpus, so a
    # case-sensitive existence test reports three functions where there is one,
    # and a case-sensitive usage count splits one function's traffic across three
    # buckets. The DECLARED spelling is preserved for display and the variants
    # observed are recorded, so the folding is auditable rather than silent.
    bare = scan_result["bare"]
    qual = scan_result["qualified"]
    receivers = scan_result["receivers"]

    bare_ci = defaultdict(int)
    for spelling, count in bare.items():
        bare_ci[spelling.lower()] += count
    qual_ci = defaultdict(int)
    for spelling, count in qual.items():
        qual_ci[spelling.lower()] += count
    recv_ci = defaultdict(Counter)
    for spelling, counter in receivers.items():
        recv_ci[spelling.lower()].update(counter)
    variants_ci = defaultdict(set)
    for spelling in list(bare) + list(qual):
        variants_ci[spelling.lower()].add(spelling)


    # Name-level usage, counted ONCE per name.
    #
    # This exists because summing per-declaration counts across every script
    # that declares a name MULTIPLIES the number by the number of declarers: five
    # scripts declare Stop, so the sum reports 7,125 where 1,425 call sites
    # exist. Both figures are defensible answers to different questions, and
    # printing the inflated one as though it were a call count is the kind of
    # quiet overstatement this project does not permit. So:
    #   name_level[name].call_sites  -- how many call sites bear this name
    #   usage[key].observed_calls    -- the SAME family total, attributed to one
    #                                   declaration, and labelled as such
    name_level = {}
    for low in sorted(declared_ci | set(bare_ci) | set(qual_ci)):
        declarers = names_by_bare_ci.get(low, [])
        name_level[low] = {
            "call_sites": bare_ci.get(low, 0) + qual_ci.get(low, 0),
            "bare_calls": bare_ci.get(low, 0),
            "qualified_calls": qual_ci.get(low, 0),
            "top_receivers": dict(recv_ci[low].most_common(5)),
            "observed_spellings": sorted(variants_ci.get(low, set())),
            "declared_by": declarers,
            "declared_by_count": len(declarers),
            "declared_in_corpus": bool(declarers),
        }
    usage = {}
    for key, attr in functions.items():
        low = attr["name"].lower()
        family = name_level[low]["call_sites"]
        usage[key] = {
            "bare_calls": bare_ci.get(low, 0),
            "qualified_calls": qual_ci.get(low, 0),
            "observed_calls": family,
            "name_call_sites": family,
            "attribution": "FAMILY, NOT THIS DECLARATION: every call site of the "
                           "bare name %r. A text scan cannot tell which "
                           "declaration a call resolves to, because Papyrus picks "
                           "by the receiver's static type. Divide by "
                           "declared_in_scripts for a rough per-declaration share, "
                           "and do not report observed_calls as this function's "
                           "own traffic." % attr["name"],
            "top_receivers": dict(recv_ci[low].most_common(5)),
            "declared_in_scripts": len(names_by_bare_ci.get(low, ())),
            "observed_spellings": sorted(variants_ci.get(low, set())),
        }
    for key, attr in events.items():
        low = attr["name"].split(".")[-1].lower()
        usage[key] = {
            "bare_calls": bare_ci.get(low, 0),
            "qualified_calls": qual_ci.get(low, 0),
            "observed_calls": 0,
            "name_call_sites": name_level.get(low, {}).get("call_sites", 0),
            "top_receivers": dict(recv_ci[low].most_common(5)),
            "declared_in_scripts": len(names_by_bare_ci.get(low, ())),
            "observed_spellings": sorted(variants_ci.get(low, set())),
            "note": "event handlers are dispatched, not called; a zero here is "
                    "expected and is NOT evidence of deadness",
        }


    called_not_declared = []
    for low in sorted(set(bare_ci) | set(qual_ci)):
        if low in declared_ci or name_level[low]["call_sites"] <= 0:
            continue
        called_not_declared.append({
            "name_ci": low,
            "observed_spellings": sorted(variants_ci.get(low, set())),
            "bare_calls": bare_ci.get(low, 0),
            "qualified_calls": qual_ci.get(low, 0),
            "observed_calls": name_level[low]["call_sites"],
            "top_receivers": dict(recv_ci[low].most_common(3)),
        })

    custom_events = defaultdict(list)
    property_types = Counter()
    for rec in scan_result["files"]:
        for ce in rec["custom_events"]:
            custom_events[ce["name"].lower()].append("%s:%d" % (rec["file"], ce["line"]))
        for pr in rec["properties"]:
            property_types[pr["type"]] += 1

    return {
        "functions": functions,
        "events": events,
        "scripts": scripts,
        "usage": usage,
        "custom_events": {k: sorted(v) for k, v in custom_events.items()},
        "property_types": dict(property_types),
        "names_by_bare": {k: sorted(v) for k, v in names_by_bare.items()},
        "names_by_bare_ci": {k: v for k, v in names_by_bare_ci.items()},
        "name_level": name_level,
        "collisions": {k: v for k, v in collisions.items() if len(v) > 1},
        "case_collisions": case_collisions,
        "called_not_declared": called_not_declared,
    }


def overloaded_names(functions):
    """Names declared more than once with more than one distinct arity.

    Reported, not resolved: which overload a call site picks depends on the
    receiver's static type, which a text scan does not know. Keyed lowercase
    because the corpus spells the same name several ways, and two spellings in
    one JSON object is a file PowerShell cannot load.
    """
    by_name = defaultdict(set)
    spellings = defaultdict(set)
    for attr in functions.values():
        by_name[attr["name"].lower()].add(attr["arity"])
        spellings[attr["name"].lower()].add(attr["name"])
    return {k: {"arities": sorted(v), "spellings": sorted(spellings[k])}
            for k, v in by_name.items() if len(v) > 1}


def compact_param(p):
    """Omit absent keys rather than writing nulls.

    21,000 entries x 3 mostly-null parameter keys is several megabytes of the
    literal text `null`, which buys no information: a missing default and a null
    default mean the same thing and both are absent.
    """
    out = {"name": p["name"]}
    if p["type"]:
        out["type"] = p["type"]
    if p["default"]:
        out["default"] = p["default"]
    if not p["parsed"]:
        out["parsed"] = False
    return out


def signature_of(attr):
    params = ", ".join("%s %s" % (p["type"] or "", p["name"]) for p in attr["parameters"])
    params = params.replace(",  ", ", ")
    ret = attr["return_type"]
    if attr["kind"] == "event_handler":
        return "Event %s(%s)" % (attr["name"], params)
    return "%sFunction %s(%s)" % (ret + " " if ret else "", attr["name"], params)


def crosscheck_negative_table(records, prop_types):
    """Compare papyrus_syntax_rules.md's negative table against what was measured.

    Four verdicts, because "the name is absent" and "the name exists but not in
    the role the claim was about" are different facts and reporting both as
    CONTRADICTED would be its own kind of lie:

      CONTRADICTED             the construct exists in the role the markdown
                               denies, so the markdown is wrong.
      PRESENT_BUT_NOT_THE_THING the name is declared, but not by the engine and
                               not in the denied role -- typically a quest
                               script's own helper of the same name. The
                               markdown's engine-level claim survives.
      CALLED_BUT_NOT_DECLARED  called in the corpus, declared nowhere in it.
      CONFIRMED_ABSENT         neither. The markdown is right.

    Every CONTRADICTED row carries the exact declarations that contradict it,
    because a bare verdict would leave the reader to guess which of the two
    things the markdown got wrong.
    """
    fns = records["functions"]
    evs = records["events"]
    scripts = records["scripts"]
    usage = records["usage"]
    native_scripts = {name for name, meta in scripts.items() if "native" in meta["flags"]}
    custom = records["custom_events"]
    total_custom = sum(len(v) for v in custom.values())
    out = []

    for row in NEGATIVE_TABLE:
        token = row["token"]
        probe = row["probe"]
        low = token.lower()

        engine_decls = []
        local_decls = []
        if probe == "function":
            for key, a in sorted(fns.items()):
                if a["name"].lower() != low:
                    continue
                item = {"key": key, "script": a["script"], "file": a["file"],
                        "line": a["line"], "signature": signature_of(a),
                        "arity": a["arity"], "native": a["native"]}
                (engine_decls if a["script"] in native_scripts else local_decls).append(item)

        event_decls = sorted({a["script"] for a in evs.values()
                              if a["name"].split(".")[-1].lower() == low})
        typed = sorted(t for t in prop_types if t.lower() == low)
        prop_count = sum(prop_types[t] for t in typed)
        script_hit = token in scripts
        keyword_hits = sorted(custom.get(token, [])) if probe == "custom_event_keyword" else []

        observed = records["name_level"].get(low, {}).get("call_sites", 0)
        recv = {}
        for key, u in usage.items():
            if fns.get(key, {}).get("name", "").lower() == low and u["top_receivers"]:
                for r, c in u["top_receivers"].items():
                    recv[r] = recv.get(r, 0) + c

        if probe == "custom_event_keyword":
            contradicted = total_custom > 0
        else:
            contradicted = bool(engine_decls or script_hit or typed or keyword_hits)

        if contradicted:
            verdict = "CONTRADICTED"
        elif local_decls or event_decls:
            verdict = "PRESENT_BUT_NOT_THE_THING"
        elif observed:
            verdict = "CALLED_BUT_NOT_DECLARED"
        else:
            verdict = "CONFIRMED_ABSENT"

        out.append({
            "token": token,
            "probe": probe,
            "papyrus_syntax_rules_md_line": row["md_line"],
            "md_claim": row["md_claim"],
            "verdict": verdict,
            "engine_declarations": engine_decls,
            "script_local_declarations": local_decls,
            "declared_as_event_in": event_decls,
            "script_of_that_name": script_hit,
            "custom_event_declarations_total": total_custom if probe == "custom_event_keyword" else 0,
            "used_as_a_property_type": bool(typed),
            "property_type_count": prop_count,
            "observed_calls": observed,
            "top_receivers": dict(sorted(recv.items(), key=lambda kv: -kv[1])[:5]),
        })
    return out


def rank_usage(records):
    """Two rankings, because they answer different questions.

    `top_used_names` counts each NAME once, so a name declared by five scripts
    appears once. `top_used_declarations` is per declaration, which is what you
    want when asking about one specific function -- with the standing caveat that
    its count is the family total and is labelled as such in `attributes`.

    `deadest` is per NAME and covers only `functions`, never event handlers:
    a handler is dispatched by the engine and by other scripts, so a zero call
    count on one is the expected case and calling it dead would be wrong.
    """
    fns = records["functions"]
    declared_keys = {a["name"].lower() for a in fns.values()}
    rows = []
    for low, nl in records["name_level"].items():
        if low not in declared_keys:
            continue
        rows.append((nl["call_sites"], low, nl))
    rows.sort(key=lambda r: (-r[0], r[1]))
    dead = [r for r in rows if r[0] == 0]

    decl_rows = sorted(
        ((u["observed_calls"], k) for k, u in records["usage"].items() if k in fns),
        key=lambda r: (-r[0], r[1]))

    return {
        "top_used_names": [
            {"name_ci": low, "call_sites": nl["call_sites"],
             "declared_by_count": nl["declared_by_count"],
             "top_receivers": nl["top_receivers"]}
            for _, low, nl in rows[:40] if _ > 0],
        "top_used_declarations": [
            {"function": k, "observed_calls": c,
             "caveat": "family total, not this declaration's own traffic"}
            for c, k in decl_rows[:40]],
        "deadest": [
            {"name_ci": low, "call_sites": 0,
             "declared_by_count": nl["declared_by_count"],
             "declared_by": nl["declared_by"][:4]}
            for _, low, nl in dead[:40]],
        "deadest_count": len(dead),
        "declared_name_count": len(rows),
        "caveat": "zero call sites is NOT proof of deadness: DLC archives and "
                  "Source/User are not read, global functions are reachable from "
                  "the console and from native code, and a call through a Var[] "
                  "payload cannot be attributed to a name at all",
    }


def build_output(scan_result, records, root, fo4_evidence=None):
    fns = records["functions"]
    evs = records["events"]
    usage = records["usage"]
    ranking = rank_usage(records)
    form_types = sorted({m["extends"] for m in records["scripts"].values() if m["extends"]})

    entries = []
    attributes = {}
    for key in sorted(fns):
        a = fns[key]
        sig = signature_of(a)
        entries.append({
            "name": key,
            "exists": True,
            "signature": sig,
            "container": a["file"],
            "returns": a["return_type"],
            "provenance": ["%s:%d" % (a["file"], a["line"])],
        })
        attributes[key] = {
            "kind": "function",
            "script": a["script"],
            "form_type": a["extends"],
            "arity": a["arity"],
            "parameters": [compact_param(p) for p in a["parameters"]],
            "return_type": a["return_type"],
            "native": a["native"],
            "global": a["global"],
            "hidden": a["hidden"],
            "const": a["const"],
            "declared_at": "%s:%d" % (a["file"], a["line"]),
            "name_ci": a["name"].lower(),
        }
    for key in sorted(evs):
        a = evs[key]
        sig = signature_of(a)
        entries.append({
            "name": key,
            "exists": True,
            "signature": sig,
            "container": a["file"],
            "returns": None,
            "provenance": ["%s:%d" % (a["file"], a["line"])],
        })
        attributes[key] = {
            "kind": "event_handler",
            "script": a["script"],
            "form_type": a["extends"],
            "arity": a["arity"],
            "parameters": [compact_param(p) for p in a["parameters"]],
            "return_type": None,
            "native": False,
            "global": False,
            "hidden": a["hidden"],
            "sender_qualified": a["sender_qualified"],
            "sender": a["sender"],
            "declared_at": "%s:%d" % (a["file"], a["line"]),
            "name_ci": a["name"].split(".")[-1].lower(),
        }

    hidden_on_declaration = sum(1 for a in attributes.values() if a.get("hidden"))
    cross = crosscheck_negative_table(records, records["property_types"])
    scripts_hidden = sum(1 for m in records["scripts"].values() if "hidden" in m["flags"])
    scripts_native = sum(1 for m in records["scripts"].values() if "native" in m["flags"])
    custom_events = sum(m["custom_event_count"] for m in records["scripts"].values())
    total_props = sum(m["property_count"] for m in records["scripts"].values())

    return {
        "spec_id": "fo4.papyrus_functions",
        "kind": "api_function",
        "title": "FO4 Papyrus function index: every function, script function and "
                 "event handler declared by the shipped Fallout 4 base scripts",
        "authority": "measured",
        "provenance": [
            {
                "source": str(root),
                "note": "the shipped Fallout 4 base .psc sources, read read-only. "
                        "%d files, %.1f MB." % (scan_result["file_count"],
                                                scan_result["bytes"] / 1048576.0),
            },
            {
                "source": "tools/papyrus_index.py",
                "note": "run %s on %s. Extraction is textual: comments and string "
                        "bodies blanked, then declarations matched. NO COMPILER WAS "
                        "RUN, so nothing here is compile-verified. The strongest "
                        "claim available from source alone is that a declaration "
                        "exists." % (RUN_ID, SCAN_DATE),
            },
            {
                "source": "not read, and therefore absent from every count",
                "note": "Source/User/ (66 .psc, Vortex-managed mod content), the "
                        "DLC0*.zip script archives (extracting writes outside the "
                        "project, which policy section 8 forbids), and the Creation "
                        "Kit install, which is not present on this machine. Every "
                        "usage count is therefore a LOWER BOUND.",
            },
        ],
        "prose": (
            "Generated, not written. Every entry is a declaration read out of the "
            "shipped Fallout 4 base scripts; none of it is recalled from "
            "documentation, which is how the hand-written negative table in "
            "ai_context/papyrus_syntax_rules.md came to be wrong on its first two "
            "rows. Entries are keyed by ScriptName.FunctionName because Papyrus "
            "namespaces on the declaring script and because a bare-name existence "
            "test is unsafe: SendEvent does not exist as an FO4 engine function, "
            "and it occurs three times in the FO4 base scripts as a locally defined "
            "script function at CA_TopicInfoScript.psc:36. The per-function detail "
            "a caller needs to branch on -- arity, parameter names and types, the "
            "native and hidden keywords, observed call counts -- lives in the "
            "top-level attributes and usage maps rather than on the entry, because "
            "schema.json declares no field for any of them and that file belongs to "
            "another owner. entries is a projection of attributes written from the "
            "same record in one pass, so the two cannot disagree, and "
            "tools/papyrus_index_gate.py verifies that they do not."
        ),
        "entries": entries,
        "source_root": {
            "path": str(root),
            "assertion": "FO4_ONLY",
            "assertion_detail": (
                "Two-sided. Negative: the root must name Fallout 4 and must not "
                "name Skyrim, GECK, Starfield or the Creation Kit, and zero "
                "SKYRIM_ONLY_MARKERS may occur in any parsed file. Positive: the "
                "FO4-only structures below must be PRESENT, because a "
                "negative-only assertion passes vacuously on an empty directory. "
                "All %d markers were measured at zero occurrences across %d files "
                "before being listed, so the assertion cannot be reddened by "
                "correct data."
                % (len(SKYRIM_ONLY_MARKERS), scan_result["file_count"])),
            "skyrim_only_markers": SKYRIM_ONLY_MARKERS,
            # The MEASURED evidence, as booleans. An earlier draft recorded
            # FO4_ONLY_STRUCTURE here, which is a table of explanatory strings,
            # and tools/papyrus_index_gate.py went RED on the committed index for
            # it: the section claimed to be the evidence was a description of
            # what evidence would look like. Descriptions live beside it now.
            "fo4_only_structure": fo4_evidence or {},
            "fo4_only_structure_meaning": FO4_ONLY_STRUCTURE,
            "marker_hits": scan_result["marker_hits"],
        },
        "scan": {
            "source_root": str(root),
            "files_read": scan_result["file_count"],
            "files_available": scan_result["file_count_available"],
            "bytes_read": scan_result["bytes"],
            "seconds": scan_result["seconds"],
            "files_unreadable": scan_result["unreadable"],
            "excluded": {
                "Source/User": "66 .psc carrying a Vortex marker; mod content on "
                               "this machine, not shipped Bethesda source",
                "Source/DLC0*.zip": "DLC script archives; extracting writes outside "
                                    "the project",
            },
            "scripts": len(records["scripts"]),
            "functions": len(fns),
            "event_handlers": len(evs),
            "properties": total_props,
            "custom_events": custom_events,
            "distinct_form_types": len(form_types),
            "form_types": form_types,
            "scripts_flagged_native": scripts_native,
            "scripts_flagged_hidden": scripts_hidden,
            "hidden_on_a_declaration": hidden_on_declaration,
            "hidden_measurement_note": (
                "MEASURED NEGATIVE, and it is a Skyrim-contamination trap: the word "
                "`hidden` occurs 1,194 times across these scripts and NOT ONCE on a "
                "function or event declaration. In Skyrim and SKSE, "
                "`Function Foo() native hidden` is idiomatic; in the FO4 base "
                "scripts `hidden` is a SCRIPT flag only, alongside native, "
                "debugonly and betaonly. A modder or a language model importing the "
                "Skyrim idiom gets a compile error here that reads like a missing "
                "function."),
        },
        "case_collisions": records["case_collisions"],        "case_collisions_note": (
            "Declarations that differ only in casing, which a case-insensitive "
            "language reads as one. Keys in `entries` and `attributes` are folded so "
            "the file loads in consumers with case-insensitive keys -- PowerShell's "
            "ConvertFrom-Json refuses a JSON object whose keys differ only in case, "
            "and policy section 5 names ConvertFrom-Json as the verification. "
            "MEASURED: this list is EMPTY for all 7,854 files. That is a result, "
            "not an untested path. An earlier draft that ignored State blocks "
            "reported 262 collisions here; every one was a false positive, because "
            "TrapTripwire.psc declaring OnActivate at line 76 and again at 125 is "
            "one handler per state (Auto state Active, then state Inactive), and "
            "Papyrus allows the same event name once in each state."),
        "attributes": attributes,
        "usage_attribution": (
            "Per-declaration usage is NOT reported per declaration, and cannot be. "
            "Papyrus resolves a call against the receiver's STATIC TYPE, so a text "
            "scan that sees `x.Stop()` cannot say whether it bound to "
            "Quest.Stop, Scene.Stop, EffectShader.Stop, VisualEffect.Stop or "
            "TestMovement.Stop. Every usage figure here is therefore keyed by NAME "
            "in `name_level`, counted once, and carries `declared_by` so a reader "
            "can see how many declarations share it. An earlier draft of this tool "
            "summed the family total across all declarers and so reported Stop as "
            "7,125 calls where 1,425 call sites exist; the five-fold inflation was "
            "an artefact of the aggregation, not a measurement."),
        "name_level": records["name_level"],
        "scripts": records["scripts"],
        "usage_summary": ranking,
        "called_but_not_declared": records["called_not_declared"],
        "called_but_not_declared_note": (
            "Names called somewhere in the corpus but declared by no script in it. "
            "A FLOOR, not a proof of absence: the declaring script may be in a DLC "
            "archive this run does not read, or in Source/User, or inherited from a "
            "parent outside the scan. It is also the exact shape a genuine dangling "
            "call takes, which is why it is worth printing."),
        "overloaded_names": overloaded_names(fns),
        "negative_table_crosscheck": cross,
        "crosscheck_note": (
            "papyrus_syntax_rules.md section 1 against this run. Four verdicts, "
            "because 'the name is absent' and 'the name exists but not in the role "
            "the claim was about' are different facts. CONTRADICTED means the "
            "markdown is wrong and the exact contradicting declaration is carried "
            "in engine_declarations. PRESENT_BUT_NOT_THE_THING means the name is "
            "declared by an ordinary script rather than by the engine. "
            "The engine/script split is decided by the native flag on the DECLARING "
            "SCRIPT, not by a hand-written list of engine types: a Papyrus function "
            "may be declared Native only if its script is also flagged Native "
            "(papyrus_syntax_rules.md section 4), so engine-provided base-type "
            "scripts are Native and quest scripts are not. SendEvent is the "
            "instructive case -- it is absent as an engine function and occurs "
            "three times as a quest script's own helper at "
            "CA_TopicInfoScript.psc:36, so a bare-name existence test would have "
            "reported FO4 as having it. Start, Stop, GetLength and GetSize are "
            "receiver-scoped: they exist, but as members of specific engine types "
            "(Quest, Scene, EffectShader, VisualEffect, ObjectReference, FormList) "
            "and not of ScriptObject, so the practical advice in the markdown "
            "survives while its blanket wording does not."),
        "crosscheck_headline": {
            "contradicted": [r["token"] for r in cross
                             if r["verdict"] == "CONTRADICTED"],
            "present_but_not_the_thing": [r["token"] for r in cross
                                          if r["verdict"] == "PRESENT_BUT_NOT_THE_THING"],
            "called_but_not_declared": [r["token"] for r in cross
                                        if r["verdict"] == "CALLED_BUT_NOT_DECLARED"],
            "confirmed_absent": [r["token"] for r in cross
                                 if r["verdict"] == "CONFIRMED_ABSENT"],
        },
        "schema_fit": {
            "kind_used": "api_function",
            "why": "Closest declared kind in ai_context/spec/schema.json: 'A "
                   "callable in a host scripting API, whether or not it exists.' "
                   "Its entry_required set (name, exists, signature, container, "
                   "provenance) maps onto this data without inventing anything.",
            "declared_but_unusable_fields": [
                "arity", "parameters", "native", "hidden", "usage counts",
                "event_handler vs function",
            ],
            "finding_owed_to_owner": (
                "NO declared kind fits a function index. api_function declares no "
                "field for arity, parameter types, the native or hidden keywords, or "
                "a usage count, and this repository does not own schema.json, so no "
                "kind was invented. Those fields are carried in the top-level "
                "`attributes` and `usage_summary` maps, which spec_lint does not "
                "police because it checks entry fields only. The correct fix is a "
                "declared kind in schema.json; until then the split between `entries` "
                "and `attributes` is a workaround, and it should be read as one."),
        },
    }


def dumps_top_level(obj):
    """Serialise with one line per TOP-LEVEL key and compact values.

    json.dumps(indent=1) on this data produces roughly a million lines, almost
    all of them whitespace, and a 29 MB file where the information content is
    about a third of that. This writes one line per top-level key instead: the
    file stays greppable and diffable at the granularity anyone actually reads
    it, and the numbers stay honest about how big the index is rather than how
    big its indentation is.
    """
    parts = []
    for key, value in obj.items():
        parts.append("%s: %s" % (json.dumps(key), json.dumps(value, ensure_ascii=False)))
    return "{\n" + ",\n".join(parts) + "\n}\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--limit", type=int, default=None,
                    help="read only the first N files, for a fast look")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true",
                    help="run every assertion and print the summary, write nothing")
    args = ap.parse_args()

    root = Path(args.root)
    problems = check_root(root)
    if problems:
        for p in problems:
            print("papyrus_index: FO4-ONLY ASSERTION FAILED: %s" % p, file=sys.stderr)
        print("papyrus_index: refusing to index. Nothing was written.", file=sys.stderr)
        return 2

    if not args.json:
        print("papyrus_index: reading %s" % root)
    result = scan(root, args.limit)
    records = build_records(result)

    struct_problems, struct_evidence = check_fo4_structure(root, args.limit)
    problems.extend(struct_problems)
    if result["marker_hits"]:
        for h in result["marker_hits"][:20]:
            problems.append("SKYRIM_ONLY marker %r found at %s:%d -- this root is "
                            "not provably FO4"
                            % (h["marker"], h["file"], h["line"]))
    if problems:
        for p in problems:
            print("papyrus_index: FO4-ONLY ASSERTION FAILED: %s" % p, file=sys.stderr)
        print("papyrus_index: refusing to write an index that is not provably "
              "FO4. Nothing was written.", file=sys.stderr)
        return 2

    output = build_output(result, records, root, struct_evidence)

    if args.json:
        print(json.dumps({
            "schema": "pipmon.papyrus.index/1",
            "status": "GREEN",
            "source_root": str(root),
            "files_read": result["file_count"],
            "scripts": len(records["scripts"]),
            "functions": len(records["functions"]),
            "event_handlers": len(records["events"]),
            "form_types": len(output["scan"]["form_types"]),
            "skyrim_marker_hits": len(result["marker_hits"]),
            "fo4_only_structure": struct_evidence,
            "called_but_not_declared": len(records["called_not_declared"]),
            "contradicted_negative_table_rows": [
                r["token"] for r in output["negative_table_crosscheck"]
                if r["verdict"] == "CONTRADICTED"],
            "seconds": round(result["seconds"], 2),
        }, indent=2))
        return 0

    if not args.no_write:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(dumps_top_level(output), encoding="utf-8")
        print("papyrus_index: wrote %s (%.2f MB)"
              % (out_path, out_path.stat().st_size / 1048576.0))

    s = output["scan"]
    print("papyrus_index: FO4-ONLY assertion HOLDS (two-sided)")
    print("  root            %s" % root)
    print("  files read      %d (%d available)" % (s["files_read"], s["files_available"]))
    print("  scripts         %d" % s["scripts"])
    print("  functions       %d" % s["functions"])
    print("  event handlers  %d" % s["event_handlers"])
    print("  properties      %d" % s["properties"])
    print("  custom events   %d" % s["custom_events"])
    print("  form types      %d" % s["distinct_form_types"])
    print("  skyrim markers  %d hits across %d markers"
          % (len(result["marker_hits"]), len(SKYRIM_ONLY_MARKERS)))
    print("  hidden on decl  %d  (scripts flagged hidden: %d)"
          % (s["hidden_on_a_declaration"], s["scripts_flagged_hidden"]))
    print("\n  top 15 most-called names (counted once per name):")
    for row in output["usage_summary"]["top_used_names"][:15]:
        print("    %6d  %-34s declared_by=%d"
              % (row["call_sites"], row["name_ci"], row["declared_by_count"]))
    print("\n  deadest names (zero call sites): %d of %d declared"
          % (output["usage_summary"]["deadest_count"],
             output["usage_summary"]["declared_name_count"]))
    for row in output["usage_summary"]["deadest"][:10]:
        print("    %6d  %-34s declared_by=%d"
              % (row["call_sites"], row["name_ci"], row["declared_by_count"]))
    print("\n  negative-table crosscheck (papyrus_syntax_rules.md section 1):")
    by_verdict = Counter(r["verdict"] for r in output["negative_table_crosscheck"])
    for r in output["negative_table_crosscheck"]:
        if r["verdict"] == "CONFIRMED_ABSENT":
            continue
        if r["engine_declarations"]:
            where = ", ".join("%s(%d args)" % (d["script"], d["arity"])
                              for d in r["engine_declarations"][:4])
            where = "engine-declared by " + where
        elif r["script_local_declarations"]:
            where = "script-local in " + ", ".join(
                d["script"] for d in r["script_local_declarations"][:4])
        elif r["script_of_that_name"]:
            where = "a script of that name exists"
        elif r["custom_event_declarations_total"]:
            where = "%d customEvent declarations corpus-wide" % r["custom_event_declarations_total"]
        elif r["used_as_a_property_type"]:
            where = "used as a property type x%d" % r["property_type_count"]
        else:
            where = "declared as an event handler"
        print("    [%-25s] %-24s md:%-3d calls=%-5d %s"
              % (r["verdict"], r["token"], r["papyrus_syntax_rules_md_line"],
                 r["observed_calls"], where))
    print("    %s" % "  ".join("%s=%d" % (k, v) for k, v in sorted(by_verdict.items())))
    print("\n  called but not declared: %d names"
          % len(records["called_not_declared"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
