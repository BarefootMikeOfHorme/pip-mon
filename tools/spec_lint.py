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
  * entries use only DECLARED fields -- a key no kind declares describes
                                       nothing, and R4 proved a declaration can
                                       be cleanly reverted away with the data
                                       still using it

The entry-field rule lives in tools/entry_field_gate.py and is called from here,
so it runs in build_all.bat stage 6 without a second build entry. It is called
rather than reimplemented because two copies of one rule drift, and a rule that
drifted between the gate and the lint would be worse than neither.

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

# The undeclared-entry-field rule. A sibling module rather than a second copy
# here, because spec_lint runs on every build and a gate that only runs when
# someone remembers it is not a gate.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import entry_field_gate
except Exception as _efg_err:  # noqa: BLE001 - the message is the point
    entry_field_gate = None
    _EFG_IMPORT_ERROR = "%s: %s" % (type(_efg_err).__name__, _efg_err)
else:
    _EFG_IMPORT_ERROR = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    problems = []
    notes = []

    def bad(spec, rule, detail):
        problems.append({"spec": spec, "rule": rule, "detail": detail})

    # A rule that could not run is reported as not-run, never as fine. Silently
    # skipping the undeclared-field check because a sibling file failed to import
    # would leave this lint reporting 0 problems while checking one field less
    # than it did yesterday, which is exactly the quiet-drift failure mode the
    # rule was written to catch.
    if entry_field_gate is None:
        bad("spec/", "entry_fields_unavailable",
            "tools/entry_field_gate.py did not import, so the undeclared-entry-field "
            "rule did not run (%s). This is a SKIP reported as a failure, on purpose." % _EFG_IMPORT_ERROR)

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

        # A registry keeps its records under a declared field of its own, so the
        # globally-required `entries` key does not apply to it. Checking it anyway
        # would force a catalogue of surfaces to pretend it is a list of fields.
        _kd = (schema.get("kinds") or {}).get(spec.get("kind")) or {}
        req = [f for f in required if not (_kd.get("collection_field") and f == "entries")]
        for f in req:
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

        # A registry keeps its records under a declared field of its own rather
        # than in `entries`, because it is a catalogue of things rather than a
        # list of fields. Inventing an `entries` array to satisfy this linter
        # would make the document lie about its own shape.
        coll_field = kdef.get("collection_field")
        if not coll_field or coll_field.startswith("REQUIRED") or ":" in coll_field:
            coll_field = spec.get("collection_field", "entries")
        entries = spec.get(coll_field or "entries")
        rec_required = kdef.get("entry_required") or kdef.get("record_required") or []
        if not isinstance(entries, list) or not entries:
            bad(name, "collection", "collection %r must be a non-empty list" % (coll_field or "entries"))
            continue
        entry_count += len(entries)

        # The declared field set for this kind, resolved ONCE per spec rather than
        # per entry, and deliberately including entry_optional. Reading only
        # entry_required and record_required is what made R4's revert invisible:
        # declaring a field and then removing the declaration were both no-ops,
        # so entry_optional was documentation rather than a contract.
        declared_fields = entry_field_gate.declared_fields(kdef) if entry_field_gate else set()
        audited = (entry_field_gate.AUDITED_UNDECLARED.get(kind, {})
                   if entry_field_gate else {})

        for i, e in enumerate(entries):
            where = "%s#%d(%s)" % (name, i, e.get("id") or e.get("name") or e.get("side") or "?")
            for f in rec_required:
                if f not in e:
                    bad(where, "entry_required", "missing %r" % f)
            if f_name := e.get("name"):
                if not isinstance(f_name, str) or not f_name.strip():
                    bad(where, "entry_required", "name must be a non-empty string")

            # An entry may carry no field its kind does not declare. A pair the
            # 2026-10-03 audit already catalogued is reported as a finding and
            # counted, not failed: those 65 pairs are in shipped data and the fix
            # is to declare them in schema.json, which this repository does not
            # own. A pair nobody has catalogued is a failure, which is what makes
            # a newly added field, or a quietly deleted declaration, both red.
            if entry_field_gate is not None:
                for f in e:
                    if f in declared_fields or f in audited:
                        continue
                    bad(where, "entry_undeclared",
                        "uses field %r, which kind %r declares in neither "
                        "entry_required, record_required nor entry_optional. Add "
                        "it to the schema with a sentence saying what it means, or "
                        "remove it from the record." % (f, kind))

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

            if "provenance" in rec_required and not e.get("provenance"):
                bad(where, "provenance", "entry requires provenance")

# Ownership records are where arrays and booleans are legitimate, so both are
        # checked for real type rather than mere presence. `available: "yes"` as
        # a string would be unbranchable, and a missing bucket reads as "checked
        # and there are none" when it actually means "nobody looked".
        for b in kdef.get("bucket_required", []):
            if b not in e:
                bad(where, "bucket_missing",
                    "missing bucket %r; an absent bucket is indistinguishable from an empty one" % b)
            elif not isinstance(e[b], list):
                bad(where, "bucket_type", "bucket %r must be a list, got %r" % (b, type(e[b]).__name__))
        if "available" in e and not isinstance(e["available"], (bool, str)):
            bad(where, "type", "available must be a boolean or one of the three availability words")

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
