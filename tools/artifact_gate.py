"""Artifact gate: validates what is passing through, against what the engine supports.

build_all.bat's earlier stages ask "does it compile". This one asks "is the thing
being compiled something Fallout 4 can actually run". Those are different
questions, and only the second one is the one that has repeatedly cost this
project a build.

Every rule here comes from ai_context/spec/*.json, never from a hardcoded list in
this file. The specs carry a `detect` list of literal stems, so adding a known
FO4 Papyrus prohibition or a non-existent xEdit API to the spec makes the gate
aware of it with no code change. That is the point: the gate is aware of what
wants to pass through it, and it knows what the engine can do, and both of those
live in one place.

What it checks:
  1. Papyrus sources for constructs marked exists_in_fo4: false.
  2. xEdit Pascal sources for calls marked exists: false.
  3. xEdit Pascal sources for calls that exist but have an easy-to-misintend
     side effect (AddNewFileName and friends) -- a WARNING, because failing on
     legitimate use teaches people to bypass a gate.
  4. Two structural Papyrus rules that no single token can express: a Native
     script that declares data, and a property with an initial value that is
     neither Auto nor AutoReadOnly.
  5. Hardcoded structural constants that contradict the record-format spec.

    python tools/artifact_gate.py
    python tools/artifact_gate.py --json

Exit 0 clean, 1 if any error, 0 with warnings only.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "ai_context" / "spec"
BASELINE = Path(__file__).resolve().parent / "artifact_gate.baseline.json"
# ai_context/ is deliberately excluded. It holds upstream verbatim reference
# material, and the point of keeping it is precisely that it contains code FO4
# cannot run: SKSE-era Papyrus using Debug.Notification, mxpf and xEditScripts
# calling AddNewFile. Flagging the reference corpus for containing the very
# things it documents would make the gate meaningless. This gate inspects OUR
# artifacts.
SKIP_DIRS = {".git", "node_modules", "__pycache__", "third_party", "target",
             "build", "dist", ".venv", "venv", "obj", "bin", "ai_context",
             "inspiration archive", "runs"}

# Pascal block comments and string literals. A prohibition named inside a
# comment, or the word "Start" inside a MenuButton label, is documentation of the
# rule rather than a violation of it. Both false positives appeared on the first
# run and both would have taught people to ignore the gate.
_PAS_STR = re.compile(r"'[^']*'")
_PAPYRUS_STR = re.compile(r'"[^"]*"')
_PAS_BLOCK = re.compile(r"\{[^}]*\}", re.S)
_PAS_PAREN = re.compile(r"\(\*.*?\*\)", re.S)


def strip_noise(text, ext):
    """Remove comments and string literals so only real code is matched."""
    if ext == ".pas":
        text = _PAS_PAREN.sub(" ", text)
        text = _PAS_BLOCK.sub(lambda m: "\n" * m.group(0).count("\n"), text)
        text = _PAS_STR.sub("''", text)
    elif ext == ".psc":
        # A MenuButton label reading "Start leaking" is a string, not a call to
        # the non-existent Start(). Papyrus has no block comments, so only the
        # literals need removing.
        text = _PAPYRUS_STR.sub('""', text)
    return text


def load(name):
    p = SPEC / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def walk(exts):
    for p in REPO.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def word_hit(line, stem):
    """Whole-word containment.

    Substring matching is how 'BSScript' came to contain 'script' in the
    retrieval expander, so a query about vtables silently became a query about
    Papyrus. The same trap applies here: 'Start' must not match 'StartTimer'.
    """
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(stem) + r"(?![A-Za-z0-9_])", line) is not None


def scan_tokens(path, entries, key_exists, label):
    """Yield (line_no, line, entry) for every banned token found in real code."""
    text = strip_noise(path.read_text(encoding="utf-8", errors="replace"), path.suffix.lower())
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if low.lstrip().startswith(";") or low.lstrip().startswith("//"):
            continue
        for e in entries:
            if e.get(key_exists) is not False:
                continue
            for stem in e.get("detect", []):
                if stem.startswith("__"):
                    continue
                if word_hit(line, stem):
                    yield i, line.strip(), e


def check_native_has_data(path):
    """A script flagged Native may not declare properties or script variables."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"^\s*Scriptname\s+\w+\s+.*\bNative\b", text, re.M | re.I):
        return []
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith(";"):
            continue
        if re.search(r"\bproperty\b", s, re.I) or re.match(
                r"^(Int|String|Bool|Float|ObjectReference|Actor|Form|Location|Marker|Quest|Item)\s+\w+\s*=",
                s, re.I):
            hits.append((i, s, "a script flagged Native may not contain data; the compiler "
                               "rejects Native functions in a non-Native script and a Native "
                               "script cannot hold properties or variables"))
    return hits


def check_property_initial(path):
    """A property with an initial value must be Auto or AutoReadOnly."""
    hits = []
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        s = line.strip()
        if s.startswith(";") or "property" not in s.lower():
            continue
        if "=" in s and not re.search(r"\bauto(readonly)?\b", s, re.I) and "==" not in s:
            hits.append((i, s, "Only Auto and AutoReadOnly properties can have initial values"))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write-baseline", action="store_true",
                    help="record the current findings as acknowledged and exit")
    args = ap.parse_args()

    papyrus = load("papyrus_constructs.json")
    xedit = load("xedit_api.json")
    recfmt = load("fo4_record_format.json")
    errors, warnings, stats = [], [], {}

    psc_files = list(walk({".psc"}))
    pas_files = list(walk({".pas"}))
    stats["psc_scanned"] = len(psc_files)
    stats["pas_scanned"] = len(pas_files)

    for f in psc_files:
        rel = f.relative_to(REPO).as_posix()
        for ln, line, e in scan_tokens(f, papyrus.get("entries", []), "exists_in_fo4", "papyrus"):
            errors.append({
                "file": rel, "line": ln, "text": line,
                "rule": "papyrus construct not in FO4",
                "construct": e["name"],
                "consequence": e.get("consequence") or e.get("replacement") or "",
                "spec": "ai_context/spec/papyrus_constructs.json",
            })
        for ln, line, msg in check_native_has_data(f):
            errors.append({"file": rel, "line": ln, "text": line, "rule": "Native script holds data",
                           "construct": "data in a Native script", "consequence": msg,
                           "spec": "ai_context/spec/papyrus_constructs.json"})
        for ln, line, msg in check_property_initial(f):
            errors.append({"file": rel, "line": ln, "text": line, "rule": "property initial value",
                           "construct": "property with an initial value, not Auto/AutoReadOnly",
                           "consequence": msg, "spec": "ai_context/spec/papyrus_constructs.json"})

    for f in pas_files:
        rel = f.relative_to(REPO).as_posix()
        for ln, line, e in scan_tokens(f, xedit.get("entries", []), "exists", "xedit"):
            sev = e.get("severity", "error")
            rec = {"file": rel, "line": ln, "text": line,
                   "rule": "xEdit API call does not exist in 4.1.5f",
                   "construct": e["name"], "consequence": e.get("behaviour", ""),
                   "spec": "ai_context/spec/xedit_api.json"}
            (warnings if sev == "warning" else errors).append(rec)
        for e in xedit.get("entries", []):
            if not e.get("caution"):
                continue
            for i, line in enumerate(
                    strip_noise(f.read_text(encoding="utf-8", errors="replace"), ".pas").splitlines(), 1):
                s = line.strip()
                if s.startswith("//"):
                    continue
                if word_hit(s, e["name"]):
                    warnings.append({"file": rel, "line": i, "text": s,
                                     "rule": "xEdit call with a side effect easy to misintend",
                                     "construct": e["name"],
                                     "consequence": e.get("caution_note", ""),
                                     "spec": "ai_context/spec/xedit_api.json"})

    # 5. Structural constants that contradict the record format spec. The spec
    #    documents a 24-byte record header; our own tool assumed 16. That is an
    #    open discrepancy, not a fixed bug, so it is reported every time until
    #    someone measures it rather than quietly editing the number.
    #
    #    Only NAMED CONSTANT ASSIGNMENTS are matched. The first version matched
    #    any number appearing within 20 characters of the word "header" and
    #    produced sixteen nonsense warnings across the protocol crate, because
    #    "header" and a byte count co-occur in ordinary code.
    hdr = next((e for e in recfmt.get("entries", []) if e.get("name") == "record header"), None)
    assign = re.compile(
        r"^\s*\w*(?:PROLOGUE|HEADER_SIZE|PREAMBLE|RECORD_HEADER)\w*\s*=\s*(\d+)", re.I)
    if hdr and hdr.get("bytes"):
        for f in walk({".py"}):
            rel = f.relative_to(REPO).as_posix()
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                m = assign.match(line)
                if m and int(m.group(1)) != hdr["bytes"]:
                    warnings.append({
                        "file": rel, "line": i, "text": line.strip(),
                        "rule": "structural constant contradicts the record format spec",
                        "construct": "record header size",
                        "consequence": "spec says %d bytes, code says %s. Unverified either way; "
                                       "measure before changing." % (hdr["bytes"], m.group(1)),
                        "spec": "ai_context/spec/fo4_record_format.json"})

    # Baseline. Without this the gate is permanently red from the moment it is
    # switched on, because it correctly finds violations that predate it -- and a
    # permanently red gate is ignored, which is the exact failure mode this whole
    # apparatus exists to prevent. So findings already recorded are reported as
    # ACKNOWLEDGED and stay visible, while only a NEW construct in a NEW place
    # fails the build. Fixing an acknowledged violation and re-baselining is a
    # deliberate act, not a side effect of running the gate.
    def fingerprint(rec):
        return "%s::%s::%s" % (rec["file"], rec["rule"], rec["construct"])

    if args.write_baseline:
        fps = sorted({fingerprint(r) for r in errors} | {fingerprint(r) for r in warnings})
        BASELINE.write_text(json.dumps({
            "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "Known violations, acknowledged rather than fixed. Regenerate with "
                    "--write-baseline only after a deliberate review. Each entry is "
                    "file::rule::construct.",
            "findings": fps,
        }, indent=2), encoding="utf-8")
        print("baseline written: %d acknowledged findings -> %s" % (len(fps), BASELINE.name))
        return 0

    known = set()
    if BASELINE.exists():
        try:
            known = set(json.loads(BASELINE.read_text(encoding="utf-8")).get("findings", []))
        except ValueError:
            known = set()

    new_errors = [r for r in errors if fingerprint(r) not in known]
    ack_errors = [r for r in errors if fingerprint(r) in known]
    new_warnings = [r for r in warnings if fingerprint(r) not in known]
    ack_warnings = [r for r in warnings if fingerprint(r) in known]

    ok = not new_errors
    if args.json:
        print(json.dumps({
            "schema": "pipmon.artifact.gate/1",
            "status": "GREEN" if ok else "RED",
            "stats": stats,
            "new_errors": new_errors, "acknowledged_errors": ack_errors,
            "new_warnings": new_warnings, "acknowledged_warnings": ack_warnings,
        }, indent=2))
        return 0 if ok else 1

    print("artifact_gate: %d .psc and %d .pas scanned" % (len(psc_files), len(pas_files)))
    for label, group in (("ERROR", new_errors), ("WARN ", new_warnings)):
        for e in group:
            print("  [%s] %s:%d  %s" % (label, e["file"], e["line"], e["rule"]))
            print("           %s" % e["text"][:110])
            print("           %s: %s" % (e["construct"], (e["consequence"] or "")[:100]))
    print("artifact_gate: %d NEW errors, %d acknowledged, %d NEW warnings, %d acknowledged"
          % (len(new_errors), len(ack_errors), len(new_warnings), len(ack_warnings)))
    if ack_errors or ack_warnings:
        roots = sorted({"%s :: %s" % (e["file"], e["construct"])
                        for e in ack_errors + ack_warnings})
        print("acknowledged, still unfixed, %d distinct problems:" % len(roots))
        for r in roots:
            print("    - %s" % r)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
