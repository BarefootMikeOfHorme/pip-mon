"""Verb-parity gate: three lists of the same verbs must be the same list.

THE DEFECT THIS EXISTS FOR
    ai_context/spec/surfaces.json claimed a verb `compat` that existed in no
    code path, and it stayed that way for eight months. The gate whose declared
    job is "every claimed path exists" -- tools/surfaces_gate.py -- did not
    catch it, and could not have: surfaces_gate checks that a surface's `path`,
    `artifact` and `index` resolve on disk. A VERB is not a path. A claim of
    "this file exists" says nothing about "this file answers to this word".

    It was closed in 0063a22 by SERVING the verb rather than deleting the claim,
    which is the better fix, and left no check behind it. This is that check.

THE THREE SETS
    claimed      surfaces.json, the record whose `path` is tools/pipmon.ps1,
                 its `verbs` list. This is the inventory's promise.
    advertised   pipmon.ps1 `caps`, the `commands` array. This is what a caller
                 discovers by reading nothing else.
    implemented  the case labels of `switch ($Command)`. This is what the
                 program actually does.

    All three must be equal. Each disagreement is reported in the direction it
    fails, because the three are not the same defect:
      claimed - implemented    a promise with no code path      (F2.8)
      advertised - implemented a discovery document that lies    (F2.6 shape)
      implemented - advertised a verb nobody can find by asking
      claimed - advertised     an inventory and a discovery doc disagree
      any duplicate            two entries, one verb: which one runs is a guess

READING THE REAL SHAPE, WHICH IS NOT THE OBVIOUS ONE
    surfaces.json is `kind: registry` with `collection_field: surfaces`, and the
    record is `id: operator.surface` -- NOT `entries`. A naive query for
    `entries` returns nothing and a gate built on it reports "0 verbs, all
    agree", which is the same green-on-nothing failure this project keeps
    refusing to build. If the expected shape is not found the gate REFUSES and
    says so rather than comparing two empty sets.

ALSO CHECKED: every `-Parameter` caps advertises must be declared in the entry
    point's param block. Same defect family -- a claim the entry point rejects --
    and F2.6 was exactly that, with caps advertising -Enable/-Disable that
    pipmon.ps1 did not declare. Sub-verbs (`link status`, `rag index`) are NOT
    checked: they arrive through the `$Arg` positional and are compared inside
    each case, so declaring them here would mean reimplementing the parser to
    chase a false positive.

    python tools/verb_parity_gate.py
    python tools/verb_parity_gate.py --json
    python tools/verb_parity_gate.py --self-test
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "ai_context" / "spec" / "surfaces.json"
PIPMON = REPO / "tools" / "pipmon.ps1"
SURFACE_PATH = "tools/pipmon.ps1"

# `n = 'verb'`, anchored so that `python   = '3.12+'` -- whose last character is
# also an n -- is not read as a command named 3.12+. That was the first regex's
# bug and it produced a thirteenth verb out of the generated block.
RE_CAPS_VERB = re.compile(r"(?<![\w])n\s*=\s*'([^']+)'")
RE_CAPS_ARGS = re.compile(r"args\s*=\s*@\(([^)]*)\)")
# A case label of `switch ($Command)`, at exactly the switch's own indent.
# Nested switches exist in this file (`switch ($overall)`, `switch ($r.exit)`)
# and their labels are indented deeper, so the indent is the discriminator.
RE_CASE = re.compile(r"^    '([a-z][a-z-]*)' \{\s*$", re.M)
# [string]$Foo / [switch]$Foo / [string[]]$Foo, but not [Parameter(Position=0)].
RE_PARAM = re.compile(r"\[\w+(?:\[\])?\]\$([A-Za-z_]\w*)")
RE_PARAM_TOKEN = re.compile(r"(?<![\w])-([A-Za-z][A-Za-z0-9]*)")


def read_pipmon(path=None):
    """Read the entry point and hand its text to parse_pipmon(). Split so that a
    historical revision can be parsed out of git without being written to disk
    first, which is how this gate's own RED state was verified."""
    path = Path(path or PIPMON)
    if not path.exists():
        return {"text": None, "implemented": [], "advertised": [], "caps_args": {},
                "params": set(),
                "problems": [("unreadable", str(path), "file does not exist")]}
    return parse_pipmon(path.read_text(encoding="utf-8"))


def parse_pipmon(text):
    """Pull the three facts out of the entry point. Returns partial information
    plus `problems`, because a source it cannot read is a refusal, not a pass."""
    out = {"text": text, "implemented": [], "advertised": [], "caps_args": {},
           "params": set(), "problems": []}
    if not text:
        out["problems"].append(("unreadable", "tools/pipmon.ps1", "no text"))
        return out

    marker = "switch ($Command) {"
    if marker not in text:
        out["problems"].append(("no_switch", "tools/pipmon.ps1",
                                "no %r found, so the implemented set cannot be read "
                                "and comparing it would compare nothing" % marker))
    else:
        out["implemented"] = RE_CASE.findall(text[text.index(marker):])

    verbs = RE_CAPS_VERB.findall(text)
    if not verbs:
        out["problems"].append(("no_caps", "tools/pipmon.ps1",
                                "no caps command list found; `n = 'verb'` entries "
                                "inside the caps block are what this reads"))
    out["advertised"] = verbs

    args_all = RE_CAPS_ARGS.findall(text)
    if len(args_all) != len(verbs):
        out["problems"].append(("args_unpaired", "tools/pipmon.ps1",
                                "%d caps commands but %d args arrays; refusing to "
                                "pair them by position"
                                % (len(verbs), len(args_all))))
    else:
        for verb, raw in zip(verbs, args_all):
            out["caps_args"][verb] = sorted(set(RE_PARAM_TOKEN.findall(raw)))

    head = text[:text.index("$ErrorActionPreference")] if "$ErrorActionPreference" in text else text
    out["params"] = set(RE_PARAM.findall(head))
    return out


def claimed_verbs(spec):
    """The `verbs` list of the record that claims tools/pipmon.ps1. Returns
    (verbs, problems) and refuses rather than guessing when the shape is not the
    one this was written against."""
    problems = []
    if spec.get("kind") != "registry":
        problems.append(("shape", "surfaces.json",
                         "kind is %r, expected 'registry'; this gate was written "
                         "against the real shape and will not guess at another"
                         % spec.get("kind")))
        return [], problems
    coll = spec.get("collection_field")
    if not coll:
        problems.append(("shape", "surfaces.json",
                         "no collection_field declared; a registry declares where it "
                         "keeps its records and this gate will not assume `entries`, "
                         "which is the mistake R7 documented"))
        return [], problems
    records = spec.get(coll)
    if not isinstance(records, list) or not records:
        problems.append(("shape", "surfaces.json",
                         "collection_field %r holds %s, not a non-empty list"
                         % (coll, type(records).__name__)))
        return [], problems
    rec = [r for r in records
           if isinstance(r, dict) and r.get("path") == SURFACE_PATH]
    if not rec:
        problems.append(("no_surface", "surfaces.json",
                         "no record in %r has path %r, so there is nothing claiming "
                         "these verbs" % (coll, SURFACE_PATH)))
        return [], problems
    if len(rec) > 1:
        problems.append(("ambiguous", "surfaces.json",
                         "%d records claim %r; which one is authoritative is a "
                         "judgement this gate refuses to make" % (len(rec), SURFACE_PATH)))
        return [], problems
    verbs = rec[0].get("verbs")
    if not isinstance(verbs, list) or not verbs:
        problems.append(("no_verbs", "surfaces.json",
                         "the record for %r carries no `verbs` list" % SURFACE_PATH))
        return [], problems
    return [str(v) for v in verbs], problems


def compare(claimed, advertised, implemented, caps_args, params):
    problems = []

    def dupes(seq, where):
        seen, dup = set(), []
        for v in seq:
            if v in seen and v not in dup:
                dup.append(v)
            seen.add(v)
        for v in dup:
            problems.append(("duplicate", where,
                             "%r appears more than once; which entry runs is a guess" % v))

    dupes(claimed, "surfaces.json claimed")
    dupes(advertised, "caps advertised")
    dupes(implemented, "switch implemented")

    c, a, i = set(claimed), set(advertised), set(implemented)
    for verb in sorted(c - i):
        problems.append(("promise_without_code", verb,
                         "ai_context/spec/surfaces.json claims it but switch "
                         "($Command) has no case for it, so it exists in no code "
                         "path. This is the F2.8 shape."))
    for verb in sorted(i - c):
        problems.append(("undocumented", verb,
                         "switch ($Command) implements it but no surface record claims "
                         "it, so the inventory does not know it exists."))
    for verb in sorted(a - i):
        problems.append(("advertised_not_implemented", verb,
                         "caps advertises it and switch ($Command) has no case for it."))
    for verb in sorted(i - a):
        problems.append(("undiscoverable", verb,
                         "switch ($Command) implements it but caps does not list it, "
                         "so a caller who reads nothing else cannot find it."))
    for verb in sorted(c ^ a):
        problems.append(("claim_disagreement", verb,
                         "surfaces.json and caps disagree about this verb, and one of "
                         "them is describing a program that does not exist."))

    for verb in sorted(caps_args):
        for tok in caps_args[verb]:
            if tok not in params:
                problems.append(("argument_not_declared", "%s -%s" % (verb, tok),
                                 "caps advertises -%s and the entry point's param block "
                                 "does not declare it, so the argument is rejected "
                                 "before the verb runs. F2.6 was exactly this." % tok))
    return problems


def self_test():
    """Four states, all in memory, writing nothing. The committed tree must be
    GREEN and each perturbation must be RED, or the gate is decoration."""
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    pip = read_pipmon()
    out, ok = [], True

    def record(label, problems, expect, note):
        nonlocal ok
        good = bool(problems) == expect
        ok = ok and good
        out.append((label, len(problems), expect, good, note))

    base = compare(*_sets(spec, pip))
    record("committed tree", base, False, "surfaces.json, caps and the switch, as they are")

    s2 = json.loads(SPEC.read_text(encoding="utf-8"))
    _rec(s2)["verbs"] = [v for v in _rec(s2)["verbs"] if v != "compat"]
    record("compat de-claimed", compare(*_sets(s2, pip)), True,
           "the claim removed from surfaces.json, as deleting it instead of "
           "serving it would have looked")

    p3 = dict(pip)
    p3["implemented"] = [v for v in pip["implemented"] if v != "docs"]
    record("docs case removed", compare(*_sets(spec, p3)), True,
           "the switch case deleted; the code path disappears and both docs keep "
           "claiming it")

    p4 = dict(pip)
    p4["caps_args"] = dict(pip["caps_args"])
    p4["caps_args"]["build"] = sorted(set(pip["caps_args"]["build"]) | {"Deploy"})
    record("caps advertises -Deploy", compare(*_sets(spec, p4)), True,
           "an argument the param block does not declare, as F2.6 was")

    width = max(len(r[0]) for r in out)
    print("verb_parity_gate self-test -- writes nothing; every state is in memory")
    for label, n, expect, good, note in out:
        print("  [%s] %-*s  problems=%-3d expected=%s"
              % ("PASS" if good else "FAIL", width, label, n, "RED" if expect else "GREEN"))
        print("         %s" % note)
    print("  %s: %d of %d states behaved as specified"
          % ("all" if ok else "NOT ALL", sum(1 for r in out if r[3]), len(out)))
    return 0 if ok else 1


def _rec(spec):
    return [r for r in spec[spec["collection_field"]] if r.get("path") == SURFACE_PATH][0]


def _sets(spec, pip):
    """The five inputs compare() takes. Shape problems are the caller's to
    report: a scenario that cannot produce a set is not a scenario that agrees."""
    verbs, _shape = claimed_verbs(spec)
    return (verbs, pip["advertised"], pip["implemented"],
            pip["caps_args"], pip["params"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not SPEC.exists():
        print("verb_parity_gate: no spec at %s" % SPEC, file=sys.stderr)
        return 2
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    pip = read_pipmon()

    verbs, shape_problems = claimed_verbs(spec)
    problems = list(pip["problems"]) + list(shape_problems)
    if not problems:
        problems = compare(verbs, pip["advertised"], pip["implemented"],
                           pip["caps_args"], pip["params"])

    # An empty implemented set is the failure mode this file was written to
    # avoid: three empty lists compare equal and report agreement about nothing.
    if not pip["implemented"]:
        problems.append(("empty", "tools/pipmon.ps1",
                         "0 verbs read from switch ($Command); agreement between "
                         "empty sets is not agreement"))

    ok = not problems
    if args.json:
        print(json.dumps({
            "schema": "pipmon.verb_parity.gate/1",
            "status": "GREEN" if ok else "RED",
            "claimed": verbs,
            "advertised": pip["advertised"],
            "implemented": pip["implemented"],
            "problems": [{"rule": r, "subject": s, "detail": d} for r, s, d in problems],
        }, indent=2))
        return 0 if ok else 1

    print("verb_parity_gate: %d claimed / %d advertised / %d implemented"
          % (len(verbs), len(pip["advertised"]), len(pip["implemented"])))
    print()
    c, a, i = set(verbs), set(pip["advertised"]), set(pip["implemented"])
    for v in sorted(c | a | i):
        marks = "".join([v in c and "C" or "-", v in a and "A" or "-", v in i and "I" or "-"])
        flag = "" if marks == "CAI" else "   <-- NOT IN ALL THREE"
        print("  [%s] %s%s" % (marks, v, flag))
    print("\n  C=claimed in surfaces.json  A=advertised in caps  I=implemented in switch")
    for r, s, d in problems:
        print("  [FAIL] %-26s %-14s %s" % (r, s, d))
    print("\nverb_parity_gate: %d problems" % len(problems))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())