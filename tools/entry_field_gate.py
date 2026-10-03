"""Entry-field gate: an entry may not use a field its kind does not declare.

THE DEFECT THIS EXISTS FOR, REPRODUCED IN R4
    Reverting commit 9bfb5c5 -- the one that added four optional field names to
    ai_context/spec/schema.json -- ALONE, while keeping
    ai_context/spec/legacy_replacement.json, gives: a clean revert, spec_lint
    reporting 0 problems, and a map using `function_served`, `measured_failure`,
    `enhancement`, `requires_host` and `depends_on` that the schema no longer
    declares. The spec layer lies and no tool notices.

    The cause is one line of reading: tools/spec_lint.py read `entry_required`
    and `record_required` and never read `entry_optional`. So declaring those
    five fields was inert, and REMOVING them was equally unchecked. A
    declaration that nothing enforces is documentation, not a contract.

THE RULE
    For each kind, the declared field set is
        entry_required | record_required | entry_optional
    and a record may carry no key outside it. Anything else is an UNDECLARED
    field: a key the schema does not describe, so nothing says what it means,
    what shape it has, or whether it is still true.

TWO DISPOSITIONS, AND WHY
    `undeclared`  FAIL. A key the schema does not declare and this gate has
                  never seen before. This is the forward-looking half: a new
                  field lands in a spec and the schema is not updated with it.
    `known`       reported, not failed. The audit on 2026-10-03 found 65
                  (kind, field) pairs already in the tree that no kind
                  declares. They are catalogued in AUDITED_UNDECLARED below
                  with the file each was seen in, because the honest reading of
                  that audit is that the fix is to DECLARE them -- and
                  ai_context/spec/schema.json is the owner's file, read here and
                  never edited. Flagging them as failures today would turn a
                  build gate red on committed, shipped data and teach everyone
                  to ignore it.

    The catalogue is keyed by (kind, field) and not by (file, field) because the
    declaration that would fix a pair lives on the KIND, in schema.json. Making
    the key per-file would mean 66 file-scoped entries describing 8 kinds.

WHAT IS DELIBERATELY NOT CLAIMED
    This gate does not know whether a declared field is USED, and it does not
    know whether an undeclared field is TRUE. It knows only that the two are
    named in the same place. A field can be declared, honoured by nobody, and
    pass; a field can be undeclared, load-bearing, and be reported as `known`
    rather than failed. What it removes is the specific failure R4 found: a
    declaration quietly deleted with the data still using it.

    tools/spec_lint.py calls check() directly, so this rule also runs in
    build_all.bat stage 6 rather than needing a new build entry.

    python tools/entry_field_gate.py
    python tools/entry_field_gate.py --json
    python tools/entry_field_gate.py --strict
    python tools/entry_field_gate.py --self-test

--self-test runs the three states in memory and writes nothing: baseline GREEN,
a declaration masked RED, a new field RED. A gate that cannot fail is
decoration, which ai_context/spec/schema.json:187 already says about status
vocabularies and which applies to gates too.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC_DIR = REPO / "ai_context" / "spec"
SCHEMA = SPEC_DIR / "schema.json"

# ---------------------------------------------------------------------------
# The audit. Every (kind, field) pair the spec layer uses without declaring,
# found by reading all 14 specs on 2026-10-03 -- not by guessing from the
# schema. Values are the files each field was observed in.
#
# Each one is a real finding. The right fix for all of them is to add the name
# to that kind's entry_optional in ai_context/spec/schema.json, with a sentence
# saying what it means, in the style of the existing optional_notes. That file
# belongs to another owner, so this gate reports rather than edits.
#
# Draining this table to empty is how `--strict` becomes the default.
# ---------------------------------------------------------------------------
AUDITED_UNDECLARED = {
    "compat_mapping": {
        "depends_on_note": "ai_context/spec/legacy_replacement.json",
        "the_five_rung_ladder": "ai_context/spec/legacy_replacement.json",
        "the_honest_split": "ai_context/spec/legacy_replacement.json",
    },
    "language_construct": {
        "behaviour": "ai_context/spec/papyrus_constructs.json",
        "corrected_utc": "ai_context/spec/papyrus_constructs.json",
        "detect": "ai_context/spec/papyrus_constructs.json",
        "detect_exceptions": "ai_context/spec/papyrus_constructs.json",
        "detect_note": "ai_context/spec/papyrus_constructs.json",
        "exception_note": "ai_context/spec/papyrus_constructs.json",
        "fo4_equivalent": "ai_context/spec/papyrus_constructs.json",
        "note": "ai_context/spec/papyrus_constructs.json",
        "signature": "ai_context/spec/papyrus_constructs.json",
    },
    "api_function": {
        "caution": "ai_context/spec/xedit_api.json",
        "caution_note": "ai_context/spec/xedit_api.json",
        "detect": "ai_context/spec/xedit_api.json",
        "proof": "ai_context/spec/xedit_api.json",
        "proof_note": "ai_context/spec/xedit_api.json",
        "reference_implementation": "ai_context/spec/xedit_api.json",
        "resolves_blocker": "ai_context/spec/xedit_api.json",
        "severity": "ai_context/spec/xedit_api.json",
    },
    "component": {},
    "term": {},
    "invariant": {},
    "record_format": {},
    "registry": {
        # blockers_to_environment.json -- a blocker record, not a field list.
        "blocks": "ai_context/spec/blockers_to_environment.json",
        "blocks_the_critical_path": "ai_context/spec/blockers_to_environment.json",
        "detail": "ai_context/spec/blockers_to_environment.json",
        "fix": "ai_context/spec/blockers_to_environment.json",
        "what": "ai_context/spec/blockers_to_environment.json",
        # in_game_surface_requirements.json
        "absent_form": "ai_context/spec/in_game_surface_requirements.json",
        "compiles_in_fo4": "ai_context/spec/in_game_surface_requirements.json",
        "constraint": "ai_context/spec/in_game_surface_requirements.json",
        "cost": "ai_context/spec/in_game_surface_requirements.json",
        "current_substitute": "ai_context/spec/in_game_surface_requirements.json",
        "decision_owed": "ai_context/spec/in_game_surface_requirements.json",
        "fo4_mechanism": "ai_context/spec/in_game_surface_requirements.json",
        "measured": "ai_context/spec/in_game_surface_requirements.json",
        "measured_evidence": "ai_context/spec/in_game_surface_requirements.json",
        "mechanism_status": "ai_context/spec/in_game_surface_requirements.json",
        "spec_correction_owed": "ai_context/spec/in_game_surface_requirements.json",
        "trap": "ai_context/spec/in_game_surface_requirements.json",
        "want": "ai_context/spec/in_game_surface_requirements.json",
        # surfaces.json -- the surface-record shape, which registry declares as
        # only id/status/provenance and then uses 14 more names.
        "artifact": "ai_context/spec/surfaces.json",
        "command": "ai_context/spec/surfaces.json",
        "direction": "ai_context/spec/surfaces.json",
        "evidence": "ai_context/spec/surfaces.json",
        "index": "ai_context/spec/surfaces.json",
        "kind": "ai_context/spec/surfaces.json",
        "members": "ai_context/spec/surfaces.json",
        "notes": "ai_context/spec/surfaces.json",
        "path": "ai_context/spec/surfaces.json",
        "side": "ai_context/spec/surfaces.json",
        "spec": "ai_context/spec/surfaces.json",
        "specs": "ai_context/spec/surfaces.json",
        "transport": "ai_context/spec/surfaces.json",
        "verbs": "ai_context/spec/surfaces.json",
    },
    "ownership": {
        "available": "ai_context/spec/side_ownership.json",
        "captured": "ai_context/spec/side_ownership.json",
        "excluded": "ai_context/spec/side_ownership.json",
        "knowledge": "ai_context/spec/side_ownership.json",
        "not_written": "ai_context/spec/side_ownership.json",
        "out_of_side_but_relevant": "ai_context/spec/side_ownership.json",
        "source": "ai_context/spec/side_ownership.json",
        "summary": "ai_context/spec/side_ownership.json",
        "third_party_note": "ai_context/spec/side_ownership.json",
    },
    "ladder": {
        "ce_evidence": "ai_context/spec/scaling_ladder.json",
        "native": "ai_context/spec/scaling_ladder.json",
        "notes": "ai_context/spec/scaling_ladder.json",
        "python": "ai_context/spec/scaling_ladder.json",
    },
}

# A kind absent from the audit table has had nothing undeclared observed in it.
# Absence is not permission: a new kind is checked in full and anything it uses
# without declaring fails. That is the intended direction of travel.


def load(schema_path=None, spec_dir=None):
    """Read the schema and every spec beside it. Unparseable specs are skipped
    here and reported by tools/spec_lint.py, which owns the parse rule; a second
    report of the same thing would be noise, not coverage."""
    schema_path = Path(schema_path or SCHEMA)
    spec_dir = Path(spec_dir or SPEC_DIR)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    specs = []
    for p in sorted(spec_dir.glob("*.json")):
        if p.name == schema_path.name:
            continue
        try:
            specs.append((p.name, json.loads(p.read_text(encoding="utf-8"))))
        except ValueError:
            continue
    return schema, specs


def collection_field(kdef, spec):
    """Where a kind keeps its records. Mirrors tools/spec_lint.py exactly: a
    registry or ladder declares the field it uses instead of `entries`, and the
    schema holds a human instruction in that slot rather than a name."""
    cf = (kdef or {}).get("collection_field")
    if not cf or cf.startswith("REQUIRED") or ":" in cf:
        cf = spec.get("collection_field", "entries")
    return cf or "entries"


def declared_fields(kdef):
    req = kdef.get("entry_required") or kdef.get("record_required") or []
    return set(req) | set(kdef.get("entry_optional") or [])


def record_label(e):
    if not isinstance(e, dict):
        return "?"
    for k in ("id", "name", "side", "rung"):
        if e.get(k):
            return str(e[k])
    return "?"


def check(schema, specs):
    """Return findings for every record key no kind declares.

    A finding is {"spec", "kind", "index", "record", "field", "disposition",
    "declared_by"}, with disposition "known" when the pair is in the audit
    table and "undeclared" otherwise. Only "undeclared" fails the gate unless
    --strict is given."""
    kinds = schema.get("kinds") or {}
    findings = []
    for name, spec in specs:
        if not isinstance(spec, dict):
            continue
        kind = spec.get("kind")
        kdef = kinds.get(kind)
        if kdef is None:
            continue  # an unknown kind is spec_lint's rule, not this one's
        records = spec.get(collection_field(kdef, spec))
        if not isinstance(records, list):
            continue  # not a collection is spec_lint's rule too
        declared = declared_fields(kdef)
        audited = AUDITED_UNDECLARED.get(kind, {})
        for i, e in enumerate(records):
            if not isinstance(e, dict):
                continue
            for field in e:
                if field in declared:
                    continue
                findings.append({
                    "spec": name,
                    "kind": kind,
                    "index": i,
                    "record": record_label(e),
                    "field": field,
                    "disposition": "known" if field in audited else "undeclared",
                    "declared_by": audited.get(field),
                })
    return findings


def failures(findings, strict=False):
    return [f for f in findings
            if f["disposition"] == "undeclared" or strict]


def self_test():
    """Prove the gate discriminates, in memory, writing nothing.

    Three states, each a real transformation of the committed data:
      1. baseline                 -> expect no failures
      2. entry_optional dropped   -> expect failures   (the R4 revert)
      3. one name masked          -> expect failures   (the same revert, one
                                       commit's worth of damage instead of all)
      4. a new field on a record  -> expect failures   (the forward direction)
    """
    schema, specs = load()
    out = []
    ok = True

    def record(label, findings, expect_fail, note):
        nonlocal ok
        bad = failures(findings)
        good = bool(bad) == expect_fail
        ok = ok and good
        out.append((label, len(findings), len(bad), expect_fail, good, note))

    record("baseline", check(schema, specs), False,
           "the committed tree, unmodified")

    s2 = copy.deepcopy(schema)
    del s2["kinds"]["compat_mapping"]["entry_optional"]
    record("entry_optional dropped", check(s2, specs), True,
           "the whole optional list removed: 9 declared names become undeclared")

    s3 = copy.deepcopy(schema)
    s3["kinds"]["compat_mapping"]["entry_optional"] = [
        f for f in s3["kinds"]["compat_mapping"]["entry_optional"]
        if f != "requires_host"]
    record("requires_host masked", check(s3, specs), True,
           "one name removed, as reverting 9bfb5c5 alone would")

    s4specs = copy.deepcopy(specs)
    for name, spec in s4specs:
        if spec.get("kind") == "compat_mapping" and spec.get("entries"):
            spec["entries"][0]["totally_new_field"] = "x"
            break
    record("new field on a record", check(schema, s4specs), True,
           "a field nobody declared, added to shipped data")

    width = max(len(r[0]) for r in out)
    print("entry_field_gate self-test -- writes nothing; every state is in memory")
    for label, total, bad, expect, good, note in out:
        print("  [%s] %-*s  findings=%-4d failures=%-4d expected=%s"
              % ("PASS" if good else "FAIL", width, label, total, bad,
                 "RED" if expect else "GREEN"))
        print("         %s" % note)
    print("  %s: %d of %d states behaved as specified"
          % ("all" if ok else "NOT ALL", sum(1 for r in out if r[4]), len(out)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="fail on catalogued findings too; this is how the "
                         "audit table gets drained rather than argued with")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the gate can go red, in memory")
    ap.add_argument("--schema", default=None)
    ap.add_argument("--spec-dir", default=None)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    try:
        schema, specs = load(args.schema, args.spec_dir)
    except (OSError, ValueError) as e:
        print("entry_field_gate: cannot read the spec layer: %s" % e, file=sys.stderr)
        return 2

    findings = check(schema, specs)
    bad = failures(findings, args.strict)
    known = [f for f in findings if f["disposition"] == "known"]
    pairs = sorted({(f["kind"], f["field"]) for f in findings})
    by_kind = {}
    for k, _ in pairs:
        by_kind[k] = by_kind.get(k, 0) + 1

    if args.json:
        print(json.dumps({
            "schema": "pipmon.entry_field.gate/1",
            "status": "GREEN" if not bad else "RED",
            "specs": len(specs),
            "undeclared_pairs": len(pairs),
            "findings": len(findings),
            "known": len(known),
            "pairs_by_kind": by_kind,
            "problems": bad,
        }, indent=2))
        return 0 if not bad else 1

    print("entry_field_gate: %d specs, %d undeclared (kind, field) pairs"
          % (len(specs), len(pairs)))
    for k in sorted(by_kind):
        print("  %-18s %d" % (k, by_kind[k]))
    if known:
        print()
        print("  KNOWN, awaiting declaration in ai_context/spec/schema.json.")
        print("  These are findings, not passes. --strict fails on them.")
        for f in known:
            print("    [known] %-26s %-24s %s (seen in %s)"
                  % (f["kind"], f["field"], f["spec"], f["declared_by"]))
    for f in bad:
        print("  [FAIL] %-26s %-24s %s#%d(%s) uses %r, which its kind declares "
              "nowhere. Add it to entry_optional with a sentence saying what it "
              "means, or remove it from the record."
              % (f["kind"], f["field"], f["spec"], f["index"], f["record"], f["field"]))
    print("\nentry_field_gate: %d problems" % len(bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())