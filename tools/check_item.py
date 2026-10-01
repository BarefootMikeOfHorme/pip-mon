"""Per-item gate: run the artifact rules against ONE file and classify the result.

Why this exists
---------------
A sweep needs a command that takes one item and answers three ways -- ok, skip,
fail. `artifact_gate.py` answers "is the whole tree clean", which is the wrong
shape for a sweep: it stops the world on the first bad file, so a stage over a
hundred sources learns nothing about the ninety-nine that were fine, and the
only way to find out about them is to fix the one and run it all again.

This is the same rules, applied per file, so the orchestrator can keep going and
report what it could not settle. Nothing is duplicated: the rule data comes from
ai_context/spec/*.json and the matching logic is imported from artifact_gate, the
same way measure_vtable.py imports its PE and RTTI walk from read_rtti.py rather
than carrying a second copy.

Exit codes are the project's standard vocabulary, chosen so a sweep can tell the
three cases apart without parsing text:
    0  ok      the item passed every rule
    3  skip    the item could not be assessed -- UNVERIFIED, never collapsed into ok
    1  fail    the item broke a rule
    4  usage   bad invocation, or an extension nothing knows how to check

    python tools/check_item.py vprobe/papyrus/PipMon.psc
    python tools/check_item.py --quiet testfacility/xedit/validate_plugin.pas
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifact_gate import (  # noqa: E402  - path set above, deliberately
    check_native_has_data,
    strip_noise,
    word_hit,
    check_property_initial,
    load,
    scan_tokens,
)

# Warning-level, not an error. AddNewFileName is legal and occasionally correct;
# failing on it teaches people to switch the gate off, which costs more than the
# hazard. It is surfaced loudly and does not change the exit code.
WARN_ONLY = {"AddNewFileName", "AddNewElement", "GetActivePlugin"}

# Documented upstream but OBSERVED TO ABORT in our use. A different kind of
# warning from WARN_ONLY: those are "legal, check your intent", these are
# "documented, and documentation did not predict this". GetFile is the case
# that earns the distinction -- its signature is unambiguous and it still
# aborted a run over 2.28M records.
FALSIFIED = {"GetFile"}


def _entry_map(entries):
    return {(e.get("name") or e.get("function") or ""): e for e in entries}


def check_scriptname_line(path):
    """The Scriptname line admits almost nothing.

    Papyrus accepts `Scriptname <Name>`, optionally `extends <Base>`, and
    optionally `Native`. Nothing else. Four of our scripts carried
    `Scriptname Foo : 0x0010 someplugin.esp`, which looks like a formID
    binding and is not Papyrus at all -- the compiler reads the 0x as a stray
    integer and then reports the whole script under a DIFFERENT name, so the
    error names a phantom "overseerbridge:overseereventbridge" and the real
    problem is nowhere in the message.

    This is a lint rule rather than a compile rule on purpose. It is the same
    class of mistake every time: a plausible-looking annotation that the
    language does not have, discovered by a compiler run that costs a staging
    pass. Catching it here means the compile is only ever spent on things a
    reader could not have spotted by eye.
    """
    errors = []
    for i, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        s = raw.strip()
        if not re.match(r"(?i)^script\s*name\b", s):
            continue
        rest = s.split(None, 1)[1] if len(s.split(None, 1)) > 1 else ""
        if not rest:
            errors.append((i, s, "Scriptname with no name"))
            continue
        # Allow: Name | Name extends Base | Name Native | Name extends Base Native
        allowed = re.match(
            r"(?i)^[A-Za-z_]\w*(\s+(extends\s+[A-Za-z_]\w*))?(\s+native)?$", rest)
        if not allowed:
            errors.append((i, s,
                           "Papyrus allows only `Scriptname <Name>`, optionally `extends <Base>` "
                           "and optionally `Native`. A formID or plugin name after a colon is "
                           "not Papyrus and the compiler reports it under a different script "
                           "name, which hides the real line."))
    return errors


def check_one(path):
    """Return (errors, warnings) for a single file."""
    ext = path.suffix.lower()
    errors, warnings = [], []

    if ext == ".psc":
        spec = load("papyrus_constructs.json")
        entries = spec.get("constructs") or spec.get("entries") or []
        for ln, text, e in scan_tokens(path, entries, "exists_in_fo4", "papyrus"):
            errors.append((ln, text, e.get("note") or e.get("name") or "not available in FO4 Papyrus"))
        for ln, text, why in check_native_has_data(path):
            errors.append((ln, text, why))
        for ln, text, why in check_property_initial(path):
            errors.append((ln, text, why))
        for ln, text, why in check_scriptname_line(path):
            errors.append((ln, text, why))


    elif ext == ".pas":
        spec = load("xedit_api.json")
        entries = spec.get("functions") or spec.get("entries") or []
        byname = _entry_map(entries)
        for ln, text, e in scan_tokens(path, entries, "exists", "xedit"):
            name = e.get("name") or e.get("function") or "?"
            msg = e.get("note") or e.get("why") or "not available in this xEdit version"
            if name in WARN_ONLY:
                warnings.append((ln, text, "%s: %s" % (name, msg)))
            else:
                errors.append((ln, text, msg))

        # Proof status, checked against the SPEC's own verdict rather than a
        # list kept here. The spec says what is known; this only enforces it, so
        # curating the spec changes the gate with no code edit -- which is the
        # whole point of keeping the rules in data.
        for ln, text in _code_lines(path):
            for name, e in byname.items():
                if not name or not word_hit(text, name):
                    continue
                proof = e.get("proof")
                if proof == "falsified_here":
                    warnings.append((ln, text,
                                     "%s: DOCUMENTED BUT FALSIFIED HERE -- %s"
                                     % (name, (e.get("proof_note") or "")[:150])))
                elif proof == "unproven":
                    warnings.append((ln, text,
                                     "%s: unproven in our scripts; documented upstream, never executed"
                                     % name))

    else:
        return None, None   # nothing knows how to check this extension

    return errors, warnings


def _code_lines(path):
    """Yield (line_no, line) with comments and string literals removed, so a
    proof warning fires on real code and not on the file narrating its own
    history. The header of validate_plugin.pas mentions GetFile several times on
    purpose, and warning about that would train people to ignore the warning."""
    text = strip_noise(path.read_text(encoding="utf-8", errors="replace"), path.suffix.lower())
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if low.lstrip().startswith(";") or low.lstrip().startswith("//"):
            continue
        yield i, line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="path to one .psc or .pas file")
    ap.add_argument("--quiet", "-q", action="store_true", help="counts only, no per-line detail")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    path = Path(args.target)
    if not path.is_absolute():
        path = REPO / path
    if not path.exists():
        print("skip: %s does not exist" % args.target, file=sys.stderr)
        return 3

    errors, warnings = check_one(path)
    if errors is None:
        print("skip: no rules for %s -- nothing was checked, so this is UNVERIFIED"
              % path.suffix, file=sys.stderr)
        return 3

    out = {"target": str(path.relative_to(REPO)) if str(path).startswith(str(REPO)) else str(path),
           "errors": [{"line": l, "text": t, "why": w} for l, t, w in errors],
           "warnings": [{"line": l, "text": t, "why": w} for l, t, w in warnings],
           "verdict": "FAIL" if errors else ("WARN" if warnings else "OK")}

    if args.json:
        print(json.dumps(out, indent=2))
    elif not args.quiet:
        for l, t, w in warnings:
            print("  WARN  %4d  %s" % (l, w))
            print("        | %s" % t[:110])
        for l, t, w in errors:
            print("  FAIL  %4d  %s" % (l, w))
            print("        | %s" % t[:110])
        if not errors and not warnings:
            print("  ok    %s -- no rule broken" % out["target"])

    # A warning is not a failure. It is printed, and the sweep records it as ok,
    # because a file that trips a documented hazard is still a file that loaded.
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())


