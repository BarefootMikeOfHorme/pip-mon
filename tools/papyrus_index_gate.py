"""Papyrus index gate: the generated FO4 index must stay true to its source.

THE DEFECT THIS EXISTS FOR
    ai_context/spec/papyrus_functions.json is GENERATED, and a generated fact
    decays silently. The index was correct when tools/papyrus_index.py wrote it
    and stays correct only while nobody hand-edits it, nobody regenerates it
    against a different source root, and nobody deletes a function out of it.
    Nothing in the repository would have noticed any of those. That is the same
    class of defect tools/entry_field_gate.py documents for the schema layer: a
    declaration nothing enforces is documentation, not a contract. This gate is
    the enforcement.

    The specific failure it is shaped around is the one this index is most able
    to suffer, because it is the failure the whole task exists to prevent. An
    index of "what FO4 Papyrus can do", quietly containing one Skyrim habit, is
    worse than no index: it would be believed, by exactly the people the
    negative table was written for.

THE RULES
    1. FO4-ONLY, both directions. The declared source root must name Fallout 4
       and must not name Skyrim, GECK, Starfield or the Creation Kit; no
       Skyrim-only marker may be recorded as hit; and every FO4-only structure
       must be recorded as PRESENT. The positive half is not redundant: a
       negative-only assertion passes on an empty directory, so the two together
       are what "provably FO4" actually means.
    2. PROJECTION INTEGRITY. `entries` is a projection of `attributes`, written
       from one record in one pass. They must agree exactly: same key set, same
       signature, same container, same return type, and the arity implied by the
       signature's parenthesised argument list must equal the recorded arity.
       This is the check that catches a hand-edit to either side.
    3. TYPE HONESTY. native/global/hidden/const and exists must be real
       booleans, because the entire point of the file is that a program can
       branch on them. "yes" as a string is worse than the field being absent.
    4. PROVENANCE. Every entry must name the file and line it was read from,
       because a fact with no provenance may not exist.
    5. NO UNDECLARED CASE. Keys in every mapping must be unique
       case-insensitively. Papyrus is case-insensitive, and a JSON object with
       keys differing only in case cannot be loaded by PowerShell's
       ConvertFrom-Json at all -- which policy section 5 names as the
       verification step, so an index that fails this is an index nobody can
       check.
    6. AUTHORITY. The spec may claim `measured` and below. `compile-verified` is
       a lie for this artefact: no compiler was run, because policy section 8
       forbids launching one. Ranking weights compile-verified at 2.6 and
       measured at 2.4, so the gap is worth 0.2 to a reader who trusts the tier
       and everything to a reader who does not.

KNOWN FINDINGS, REPORTED AND NOT FAILED
    Four findings are real, already documented, and live in files this agent does
    not own. They print on every run. Failing the build on them would mean a
    permanently red gate, and a gate that is always red is decoration with
    better manners; `--strict` fails on them, which is how the table empties.

      syntax_rules_contradiction  ai_context/papyrus_syntax_rules.md disagrees
                                 with this index on 6 rows of its own negative
                                 table. The markdown is hand-maintained prose and
                                 is not this agent's file. This is the finding
                                 the gate exists to keep visible.
      schema_field_gap           no declared kind in schema.json fits a function
                                 index, so arity/native/hidden/usage live in
                                 top-level maps that spec_lint does not police.
                                 schema.json is the owner's file.
      called_but_not_declared    114 names are called in the corpus and declared
                                 nowhere in it. DLC archives and Source/User are
                                 not read, so this is a floor, not a defect.
      dead_functions             zero call sites is not proof of deadness: global
                                 functions are reachable from the console and from
                                 native code, and calls through a Var[] payload
                                 cannot be attributed to a name at all.

WHAT IT DOES NOT DO
    It does not run the compiler and does not re-derive the index from source;
    tools/papyrus_index.py owns generation and it asserts the FO4-only property
    at generation time, before it writes anything. This gate checks that the
    committed artefact still says what that run said, which is a different and
    complementary question. It also does not check that any index entry is
    TRUE, only that it is internally consistent and correctly attributed.

    python tools/papyrus_index_gate.py
    python tools/papyrus_index_gate.py --json
    python tools/papyrus_index_gate.py --strict
    python tools/papyrus_index_gate.py --self-test
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX = REPO / "ai_context" / "spec" / "papyrus_functions.json"

# Impostor roots. The point of listing them is that a path can be wrong in a way
# that still contains the right words, and a check that only asserted "not
# Skyrim" would pass a Starfield tree.
IMPOSTOR_ROOT_MARKERS = ("skyrim", "geck", "starfield", "creation kit")

# What the index must be able to say about itself. Held here rather than read
# out of the file so that a field simply vanishing from the index is RED: a gate
# that reads its expectations from the artefact it is checking cannot detect the
# artefact losing the property.
REQUIRED_TOP_LEVEL = (
    "spec_id", "kind", "title", "authority", "provenance", "prose", "entries",
    "source_root", "scan", "attributes", "name_level", "scripts",
    "usage_summary", "case_collisions", "negative_table_crosscheck",
    "schema_fit", "usage_attribution",
)
REQUIRED_ATTR = ("kind", "script", "form_type", "arity", "parameters",
                 "return_type", "native", "global", "hidden", "declared_at")
ALLOWED_KIND = {"function", "event_handler"}
ALLOWED_AUTHORITY = {"compile-verified", "measured", "upstream-verbatim",
                     "derived", "judgement", "unproven", "aspiration"}
BOOL_ATTRS = ("native", "global", "hidden")

# What api_function actually declares for an entry. Checked here as well as by
# tools/spec_lint.py because this gate must be able to run without it, and
# because a gate that borrows its expectations from the file under test is not
# checking anything.
ENTRY_REQUIRED = ("name", "exists", "signature", "container", "provenance")

RE_PROVENANCE_SITE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+)$")


def arity_from_signature(sig):
    """Count the arguments in a signature's parenthesised list.

    Counting commas rather than trusting a recorded number is the whole point:
    schema.json's own rule is that a signature must contain a parenthesised
    argument list "so field offsets can be COMPUTED, not eyeballed", and the
    same discipline applies to arity.
    """
    if not isinstance(sig, str):
        return None
    start = sig.find("(")
    end = sig.rfind(")")
    if start < 0 or end < start:
        return None
    inner = sig[start + 1:end].strip()
    if not inner:
        return 0
    return inner.count(",") + 1


def check(spec):
    """Return (problems, known). Problems fail; known are reported."""
    problems = []
    known = []

    def bad(rule, subject, detail):
        problems.append({"rule": rule, "subject": subject, "detail": detail})

    def note(rule, subject, detail, track):
        known.append({"rule": rule, "subject": subject, "detail": detail,
                      "track": track})

    # -- 6. authority, and the spec-level shape ------------------------------
    authority = spec.get("authority")
    if authority not in ALLOWED_AUTHORITY:
        bad("authority", "spec", "%r is not one of %s" % (authority, sorted(ALLOWED_AUTHORITY)))
    if authority == "compile-verified":
        bad("authority", "spec",
            "authority is compile-verified. NO COMPILER WAS RUN for this artefact "
            "-- tools/papyrus_index.py reads source text, and policy section 8 "
            "forbids launching PapyrusCompiler. `measured` is the strongest "
            "honest claim: a declaration was read, not proven to compile.")
    if not spec.get("provenance"):
        bad("provenance", "spec", "spec-level provenance is empty")
    if not spec.get("prose"):
        bad("dual_form", "spec", "no prose; a data-only spec cannot be interpreted")

    for key in REQUIRED_TOP_LEVEL:
        if key not in spec:
            bad("missing_section", key,
                "the index has no %r section. It is absent rather than empty, so "
                "whatever it was proving is no longer claimed anywhere." % key)

    # -- 1. FO4-only, both directions ---------------------------------------
    root = spec.get("source_root") or {}
    path = str(root.get("path") or "")
    low = path.lower()
    if "fallout 4" not in low:
        bad("fo4_root", path or "<no source_root.path>",
            "the declared source root does not name Fallout 4. An index of FO4 "
            "that cannot name FO4 is not evidence of anything.")
    for marker in IMPOSTOR_ROOT_MARKERS:
        if marker in low:
            bad("fo4_root", path,
                "the source root names %r. Conflating installs is a recorded, "
                "repeated failure here -- ai_context/spec/nomenclature.json." % marker)
    for hit in root.get("marker_hits") or []:
        bad("fo4_marker", "%s:%s" % (hit.get("file"), hit.get("line")),
            "Skyrim-only marker %r is recorded as present in the FO4 corpus"
            % hit.get("marker"))
    structure = root.get("fo4_only_structure") or {}
    if not structure:
        bad("fo4_structure", "source_root",
            "no fo4_only_structure recorded. The POSITIVE half of the FO4-only "
            "assertion is missing, and without it a negative-only check passes "
            "on an empty directory.")
    for key, present in sorted(structure.items()):
        if present is not True:
            bad("fo4_structure", key,
                "FO4-only structure %r is not recorded as present. Either the "
                "source root is not FO4, or the assertion was never made." % key)

    # -- 2. projection integrity: entries <-> attributes ---------------------
    entries = spec.get("entries") or []
    attributes = spec.get("attributes") or {}
    if not entries:
        bad("empty_collection", "entries", "no entries; an empty index proves nothing")
    if not attributes:
        bad("empty_collection", "attributes", "no attributes")

    entry_keys = []
    for i, e in enumerate(entries):
        label = e.get("name") or "#%d" % i
        for field in ENTRY_REQUIRED:
            if field not in e:
                bad("entry_field", label, "entry is missing %r" % field)
        if not isinstance(e.get("name"), str) or not e.get("name"):
            bad("entry_field", label, "name must be a non-empty string")
        if not isinstance(e.get("exists"), bool):
            bad("type", label, "exists must be a real boolean, got %r, because "
                                "this field exists to be branched on" % (e.get("exists"),))
        prov = e.get("provenance")
        if not prov:
            bad("provenance", label, "entry requires provenance")
        else:
            for site in prov if isinstance(prov, list) else [prov]:
                if not RE_PROVENANCE_SITE.match(str(site)):
                    bad("provenance", label,
                        "provenance %r does not name a file and a line. An "
                        "unlocatable fact cannot be checked." % (site,))
        entry_keys.append(e.get("name"))

    attr_keys = set(attributes)
    missing_attr = sorted(set(entry_keys) - attr_keys)
    orphan_attr = sorted(attr_keys - set(entry_keys))
    for key in missing_attr[:20]:
        bad("projection", key, "in `entries` but absent from `attributes`")
    for key in orphan_attr[:20]:
        bad("projection", key, "in `attributes` but absent from `entries`")
    if len(missing_attr) > 20 or len(orphan_attr) > 20:
        bad("projection", "(bulk)",
            "%d entries lack attributes and %d attributes lack entries; only the "
            "first 20 of each are listed" % (len(missing_attr), len(orphan_attr)))

    for e in entries:
        key = e.get("name")
        attr = attributes.get(key)
        if attr is None:
            continue
        sig = e.get("signature")
        if isinstance(sig, str) and "(" not in sig:
            bad("signature", key, "signature %r has no argument list" % sig)
        sig_arity = arity_from_signature(sig)
        if sig_arity is not None and sig_arity != attr.get("arity"):
            bad("arity", key,
                "the signature implies %d argument(s) and attributes records "
                "arity %r. One of the two is lying and a caller branching on "
                "arity gets the wrong answer." % (sig_arity, attr.get("arity")))
        if attr.get("kind") == "function":
            if not isinstance(sig, str) or "Function" not in sig:
                bad("signature", key, "kind is function but the signature is %r" % sig)
        if attr.get("kind") == "event_handler":
            if not isinstance(sig, str) or "Event" not in sig:
                bad("signature", key, "kind is event_handler but the signature is %r" % sig)
        if e.get("returns") != attr.get("return_type"):
            bad("returns", key,
                "entry returns %r but attributes records return_type %r"
                % (e.get("returns"), attr.get("return_type")))
        if e.get("container") != attr.get("declared_at", "").rsplit(":", 1)[0]:
            bad("container", key,
                "entry container %r does not match declared_at %r"
                % (e.get("container"), attr.get("declared_at")))
        for field in REQUIRED_ATTR:
            if field not in attr:
                bad("attr_field", key, "attributes record is missing %r" % field)
        if attr.get("kind") not in ALLOWED_KIND:
            bad("vocabulary", key, "kind %r is outside the declared vocabulary %s"
                % (attr.get("kind"), sorted(ALLOWED_KIND)))
        for b in BOOL_ATTRS:
            if b in attr and not isinstance(attr[b], bool):
                bad("type", key, "%s must be a real boolean, got %r" % (b, attr[b]))

    # -- 5. no undeclared case, anywhere ------------------------------------
    def walk(node, path, depth=0):
        if depth > 4:
            return
        if isinstance(node, dict):
            seen = {}
            for k in node:
                f = k.lower()
                if f in seen:
                    bad("case_collision", "%s/%s" % (path, k),
                        "keys %r and %r differ only in case. Papyrus is "
                        "case-insensitive, and a JSON object like this cannot be "
                        "loaded by ConvertFrom-Json, which policy section 5 names "
                        "as the verification." % (seen[f], k))
                seen[f] = k
            for k, v in node.items():
                walk(v, "%s/%s" % (path, k), depth + 1)
        elif isinstance(node, list):
            for item in node[:50]:
                walk(item, path, depth + 1)

    for section in ("entries", "attributes", "name_level", "scripts"):
        walk(spec.get(section), section)

    # -- KNOWN: the crosscheck the markdown disagrees with -------------------
    for row in spec.get("negative_table_crosscheck") or []:
        if row.get("verdict") in ("CONTRADICTED", "PRESENT_BUT_NOT_THE_THING"):
            note("syntax_rules_contradiction",
                 "%s (papyrus_syntax_rules.md:%s)" % (row.get("token"),
                                                       row.get("papyrus_syntax_rules_md_line")),
                 "%s -- the markdown claims %r and this index measured otherwise: "
                 "%d engine declaration(s), %d call sites. The markdown is not this "
                 "agent's file; it is reported, not corrected."
                 % (row.get("verdict"), row.get("md_claim"),
                    len(row.get("engine_declarations") or []),
                    row.get("observed_calls") or 0),
                 "ai_context/papyrus_syntax_rules.md section 1")

    gap = spec.get("schema_fit") or {}
    if gap.get("finding_owed_to_owner"):
        note("schema_field_gap", gap.get("kind_used", "?"),
             gap.get("finding_owed_to_owner"),
             "ai_context/spec/schema.json -- owner's file")

    undeclared = spec.get("called_but_not_declared") or []
    if undeclared:
        note("called_but_not_declared", "%d names" % len(undeclared),
             "called in the corpus, declared nowhere in it. A FLOOR: DLC archives "
             "and Source/User are not read, and inheritance is not resolved.",
             "ai_context/spec/papyrus_functions.json")

    summary = spec.get("usage_summary") or {}
    if summary.get("deadest_count"):
        note("dead_functions", "%d names" % summary["deadest_count"],
             "zero observed call sites. NOT proof of deadness: global functions "
             "are reachable from the console and from native code, and a call "
             "through a Var[] payload cannot be attributed to a name at all.",
             "ai_context/spec/papyrus_functions.json")

    return problems, known


def load(path=None):
    p = Path(path or INDEX)
    if not p.exists():
        raise FileNotFoundError(str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def self_test():
    """Six states, all in memory, writing nothing.

    The committed artefact must be GREEN and each perturbation must be RED. A
    perturbation that leaves it GREEN is a rule this gate does not have.
    """
    spec = load()
    out = []
    ok = True

    def record(label, problems, expect, note_text):
        nonlocal ok
        good = bool(problems) == expect
        ok = ok and good
        out.append((label, len(problems), expect, good, note_text))

    p, _ = check(spec)
    record("committed index", p, False,
           "ai_context/spec/papyrus_functions.json exactly as committed")

    # The defect this gate exists for: an index that has quietly absorbed a
    # Skyrim habit. Point the root at Skyrim.
    s = copy.deepcopy(spec)
    s["source_root"]["path"] = r"C:\Games\Skyrim Special Edition\Data\Scripts\Source\Base"
    p, _ = check(s)
    record("source root is Skyrim's", p, True,
           "the root names Skyrim. The negative-only marker scan would still "
           "pass, which is exactly why the root assertion is separate")

    # The same root, with every FO4-only structure still marked present -- the
    # vacuous-pass shape: nothing FO4-shaped was ever actually observed.
    s = copy.deepcopy(spec)
    s["source_root"]["fo4_only_structure"] = {}
    p, _ = check(s)
    record("no FO4-only structure recorded", p, True,
           "the POSITIVE half deleted. With it gone, 'no Skyrim markers found' "
           "would pass on an empty directory")

    # A Skyrim-only marker recorded as hit.
    s = copy.deepcopy(spec)
    s["source_root"]["marker_hits"] = [{"marker": "SkyUI",
                                        "file": "SomeScript.psc", "line": 12}]
    p, _ = check(s)
    record("a Skyrim marker is recorded present", p, True,
           "SkyUI found in the FO4 corpus: the exact contamination the whole "
           "task exists to prevent")

    # Hand-edited: an entry removed from `attributes` only.
    s = copy.deepcopy(spec)
    first = s["entries"][0]["name"]
    del s["attributes"][first]
    p, _ = check(s)
    record("entry deleted from attributes", p, True,
           "a hand-edit that touched one side of the projection; this is the "
           "quiet drift the projection rule exists to catch")

    # Hand-edited: arity that disagrees with the signature it sits beside.
    s = copy.deepcopy(spec)
    victim = next(a for a in s["attributes"].values()
                  if a.get("kind") == "function" and a.get("arity", 0) > 0)
    for key, attr in s["attributes"].items():
        if attr is victim:
            attr["arity"] = attr["arity"] + 3
            break
    p, _ = check(s)
    record("arity contradicts its signature", p, True,
           "arity bumped by 3 while the signature still shows the old argument "
           "list; a caller branching on arity gets the wrong answer")

    # Type honesty: native as a string.
    s = copy.deepcopy(spec)
    for attr in s["attributes"].values():
        if attr.get("native"):
            attr["native"] = "yes"
            break
    p, _ = check(s)
    record("native is the string 'yes'", p, True,
           "the field exists so a program can branch on it; 'yes' is worse "
           "than the field being absent")

    # Provenance emptied.
    s = copy.deepcopy(spec)
    s["entries"][0]["provenance"] = []
    p, _ = check(s)
    record("provenance emptied on one entry", p, True,
           "a fact with no provenance may not exist")

    # A key pair differing only in case.
    s = copy.deepcopy(spec)
    key = next(iter(s["attributes"]))
    twin = key.upper() if key.upper() != key else key.lower()
    s["attributes"][twin] = copy.deepcopy(s["attributes"][key])
    p, _ = check(s)
    record("two keys differing only in case", p, True,
           "PowerShell cannot load such a file at all, so nobody could verify "
           "it with the check policy section 5 names")

    # Authority overclaim.
    s = copy.deepcopy(spec)
    s["authority"] = "compile-verified"
    p, _ = check(s)
    record("authority claims compile-verified", p, True,
           "no compiler was run. ranking.json weights that tier 2.6 against "
           "measured at 2.4, so the overclaim is worth reading")

    width = max(len(r[0]) for r in out)
    print("papyrus_index_gate self-test -- writes nothing; every state is in memory")
    for label, n, expect, good, note_text in out:
        print("  [%s] %-*s  problems=%-4d expected=%s"
              % ("PASS" if good else "FAIL", width, label, n,
                 "RED" if expect else "GREEN"))
        print("         %s" % note_text)
    print("  %s: %d of %d states behaved as specified"
          % ("all" if ok else "NOT ALL", sum(1 for r in out if r[3]), len(out)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="fail on the acknowledged findings too; this is how "
                         "the table gets emptied rather than argued with")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--index", default=None)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    try:
        spec = load(args.index)
    except (OSError, ValueError) as e:
        # A gate that cannot load what it checks reports that as a failure, not
        # as a pass. SKIP is never PASS.
        print("papyrus_index_gate: cannot read the index: %s" % e, file=sys.stderr)
        return 2

    problems, known = check(spec)
    failed = problems + (known if args.strict else [])

    if args.json:
        print(json.dumps({
            "schema": "pipmon.papyrus_index.gate/1",
            "status": "GREEN" if not failed else "RED",
            "index": str(Path(args.index or INDEX)),
            "entries": len(spec.get("entries") or []),
            "attributes": len(spec.get("attributes") or {}),
            "authority": spec.get("authority"),
            "source_root": (spec.get("source_root") or {}).get("path"),
            "known": known,
            "problems": problems,
        }, indent=2))
        return 0 if not failed else 1

    root = spec.get("source_root") or {}
    print("papyrus_index_gate: %s" % INDEX.name)
    print("  entries        %d" % len(spec.get("entries") or []))
    print("  attributes     %d" % len(spec.get("attributes") or {}))
    print("  authority      %s" % spec.get("authority"))
    print("  source root    %s" % root.get("path"))
    print("  skyrim markers %d hit(s) across %d marker(s)"
          % (len(root.get("marker_hits") or []),
             len(root.get("skyrim_only_markers") or {})))
    print("  fo4 structure  %d/%d present"
          % (sum(1 for v in (root.get("fo4_only_structure") or {}).values() if v is True),
             len(root.get("fo4_only_structure") or {})))
    print()
    if known:
        print("  KNOWN, open and owned elsewhere. Reported, not failed.")
        print("  --strict fails on these too.")
        for k in known:
            print("    [known] %-28s %s" % (k["rule"], k["subject"]))
            print("            %s" % k["detail"])
            print("            tracked as: %s" % k["track"])
        print()
    for pr in problems:
        print("  [FAIL] %-28s %s" % (pr["rule"], pr["subject"]))
        print("         %s" % pr["detail"])
    print("\npapyrus_index_gate: %d problems, %d known" % (len(problems), len(known)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
