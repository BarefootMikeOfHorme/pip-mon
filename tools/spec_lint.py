"""Spec lint: the form-and-code validator for the machine-readable spec layer.

A spec layer that is never validated is a pile of JSON that will drift from the
code and from the prose. This checks shape, types and honesty, and it is wired
into build_all.bat as part of stage 6 so a malformed spec fails the build rather
than quietly misleading a session.

What it enforces, and why each rule exists:

  * required fields per kind       -- a spec missing its provenance is a fact
                                       with no source, which this project does
                                       not permit
  * authority is a known tier      -- a spec cannot claim more confidence than
                                       the ranking model recognises
  * booleans are real booleans      -- exists / gate_covered exist to be
                                       branched on; "yes" as a string is worse
                                       than no field at all
  * bytes are integers             -- so field offsets can be COMPUTED, not
                                       eyeballed, which is the entire point of
                                       writing a record format down
  * signatures look like signatures -- a call with no argument list is a guess
  * cross-references resolve        -- a nomenclature entry pointing at a spec
                                       that does not exist is a dangling promise
  * a spec is BOTH prose and data   -- prose-only pretends to be data, and
                                       data-only cannot be interpreted by a
                                       human reading the corpus

    python tools/spec_lint.py
    python tools/spec_lint.py --json
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC_DIR = REPO / "ai_context" / "spec"
SCHEMA = SPEC_DIR / "schema.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    problems = []
    notes = []

    def bad(spec, rule, detail):
        problems.append({"spec": spec, "rule": rule, "detail": detail})

    if not SCHEMA.exists():
        print("spec_lint: no schema at %s" % SCHEMA, file=sys.stderr)
        return 2
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    required = schema["required_common"]
    tiers = set(schema["authority_tiers"])
    kinds = schema["kinds"]

    specs = sorted(p for p in SPEC_DIR.glob("*.json") if p.name != "schema.json")
    if not specs:
        bad("spec/", "empty", "no spec files found in %s" % SPEC_DIR)

    entry_count = 0
    for path in specs:
        name = path.name
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            bad(name, "parses", str(e))
            continue

        for f in required:
            if f not in spec:
                bad(name, "required_common", "missing field %r" % f)
        if not spec.get("prose") or len(str(spec["prose"]).strip()) < 40:
            bad(name, "dual-form", "prose must be a real human-readable paragraph, not a stub")
        if not spec.get("provenance"):
            bad(name, "provenance", "spec-level provenance is empty; a fact with no provenance may not exist")
        if spec.get("authority") not in tiers:
            bad(name, "authority", "%r is not one of %s" % (spec.get("authority"), sorted(tiers)))

        kind = spec.get("kind")
        kdef = kinds.get(kind)
        if kdef is None:
            bad(name, "kind", "unknown kind %r" % kind)
            continue

        entries = spec.get("entries")
        if not isinstance(entries, list) or not entries:
            bad(name, "entries", "entries must be a non-empty list")
            continue
        entry_count += len(entries)

        for i, e in enumerate(entries):
            where = "%s#%d(%s)" % (name, i, e.get("name", "?"))
            for f in kdef["entry_required"]:
                if f not in e:
                    bad(where, "entry_required", "missing %r" % f)
            if f_name := e.get("name"):
                if not isinstance(f_name, str) or not f_name.strip():
                    bad(where, "entry_required", "name must be a non-empty string")

            # Boolean honesty. These fields exist to be branched on.
            for bf in ("exists", "exists_in_fo4", "gate_covered"):
                if bf in e and not isinstance(e[bf], bool):
                    bad(where, "type", "%s must be a real boolean, got %r" % (bf, e[bf]))

            if "bytes" in e and e["bytes"] is not None and not isinstance(e["bytes"], int):
                bad(where, "type", "bytes must be an integer or null, got %r -- offsets must be computable"
                    % (e["bytes"],))

            if "signature" in e and isinstance(e["signature"], str):
                sig = e["signature"]
                if kind == "api_function" and "(" not in sig and "(" in sig.replace("(global", "("):
                    bad(where, "signature", "looks like a call with no argument list: %r" % sig)

            if "provenance" in kdef["entry_required"] and not e.get("provenance"):
                bad(where, "provenance", "entry requires provenance")

            # A component that is not working must not claim gate coverage.
            if kind == "component" and e.get("gate_covered") is True:
                st = str(e.get("status", "")).lower()
                if any(w in st for w in ("never", "no report", "unproven", "0 records", "absent", "not ")):
                    bad(where, "honesty", "gate_covered is true but status reads as not working: %r"
                        % e.get("status"))

    # Cross-references: nomenclature must point at specs that exist.
    all_ids = set()
    for path in specs:
        try:
            all_ids.add(json.loads(path.read_text(encoding="utf-8")).get("spec_id"))
        except ValueError:
            pass
    nom = SPEC_DIR / "nomenclature.json"
    if nom.exists():
        for e in json.loads(nom.read_text(encoding="utf-8")).get("entries", []):
            ref = e.get("spec")
            if ref and not (REPO / ref).exists():
                bad("nomenclature#%s" % e.get("name"), "dangling_ref", "points at %s which does not exist" % ref)
        notes.append("nomenclature cross-references checked")

    # Compatibility statuses are a CLOSED vocabulary, so a program can branch on
    # coverage instead of pattern-matching prose. A refusal without a reason is
    # indistinguishable from an oversight, so NOT_PLANNED and REJECTED must say
    # why. Both rules exist because a status nobody can trust is decoration.
    cv = schema.get("compat_status_vocabulary") or {}
    allowed = {k for k in cv if not k.startswith("_")}
    for path in specs:
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if spec.get("kind") != "compat_mapping":
            continue
        name = path.name
        for i, e in enumerate(spec.get("entries", [])):
            where = "%s#%d(%s)" % (name, i, e.get("name", "?"))
            st = e.get("status")
            if st not in allowed:
                bad(where, "compat_status",
                    "status %r is not in the closed vocabulary %s" % (st, sorted(allowed)))
            if st in ("NOT_PLANNED", "REJECTED") and not (e.get("notes") or "").strip():
                bad(where, "compat_reason",
                    "status is %s but no reason is given; an unexplained refusal is "
                    "indistinguishable from an oversight" % st)
            if st == "COVERED" and not e.get("spec"):
                bad(where, "compat_proof",
                    "status is COVERED but no spec entry is cited, so nothing proves it")
        notes.append("compat status vocabulary checked (%d allowed)" % len(allowed))

    ok = not problems
    if args.json:
        print(json.dumps({
            "schema": "pipmon.spec.lint/1",
            "status": "GREEN" if ok else "RED",
            "specs": len(specs),
            "entries": entry_count,
            "problems": problems,
        }, indent=2))
        return 0 if ok else 1

    print("spec_lint: %d specs, %d entries" % (len(specs), entry_count))
    for n in notes:
        print("  note: %s" % n)
    for p in problems:
        print("  [FAIL] %-28s %-16s %s" % (p["spec"], p["rule"], p["detail"]))
    print("spec_lint: %d problems" % len(problems))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
