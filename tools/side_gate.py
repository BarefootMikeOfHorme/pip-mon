"""Per-side status: is each side of the aisle actually available today?

The build gate is global. That is its weakness, and this tool is the correction:
a global green says the thing builds, not that any given side of the work
functions. The engine side can be completely unavailable while every stage is
green, and it currently is.

Sides are engine / in-house / creation-kit. Each has preconditions, and an
invariant is not a capability: it is true or it is not, and while it is false
the whole side is unavailable. Partial delivery of a capability is still useful;
an unmet invariant means nothing on that side works.

A status is one of MET / NOT_MET / UNVERIFIED / PARTIALLY_MET / NOT_APPLICABLE.
UNVERIFIED is kept distinct from MET on purpose, because a design rule nobody
measures is a hope and reporting it as met is how it stops being looked at.

    python tools/side_gate.py
    python tools/side_gate.py --json
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "ai_context" / "spec" / "side_invariants.json"

# NOT_MET and PARTIALLY_MET make a side unavailable. UNVERIFIED does not, but it
# is reported loudly, because an unmeasured rule is indistinguishable from a
# working one until somebody measures it.
HARD_FAIL = {"NOT_MET"}
SOFT = {"PARTIALLY_MET", "UNVERIFIED"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--side")
    args = ap.parse_args()

    if not SPEC.exists():
        print("side_gate: no spec at %s" % SPEC, file=sys.stderr)
        return 2
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    entries = spec.get("entries", [])
    if args.side:
        entries = [e for e in entries if e.get("side") == args.side]

    sides = {}
    for e in entries:
        s = sides.setdefault(e["side"], {"met": 0, "not_met": 0, "partial": 0,
                                         "unverified": 0, "blockers": [], "soft": []})
        st = e.get("status")
        if st == "MET":
            s["met"] += 1
        elif st == "NOT_MET":
            s["not_met"] += 1
            s["blockers"].append(e["name"])
        elif st == "PARTIALLY_MET":
            s["partial"] += 1
            s["soft"].append("%s (partial)" % e["name"])
        elif st == "UNVERIFIED":
            s["unverified"] += 1
            s["soft"].append("%s (unverified)" % e["name"])
    for s in sides.values():
        s["available"] = s["not_met"] == 0
        s["total"] = s["met"] + s["not_met"] + s["partial"] + s["unverified"]

    if args.json:
        print(json.dumps({"schema": "pipmon.side.gate/1", "sides": sides}, indent=2))
        return 0

    declared = {d["side"]: d for d in spec.get("sides", [])}
    print("side status -- a green global gate does NOT mean a side works\n")
    for name in sorted(sides):
        s = sides[name]
        d = declared.get(name, {})
        mark = "AVAILABLE" if s["available"] else "UNAVAILABLE"
        print("  %-14s %-12s %d/%d invariants met" % (name, mark, s["met"], s["total"]))
        if d.get("summary"):
            print("      %s" % d["summary"])
        for b in s["blockers"]:
            print("      BLOCKED BY: %s" % b)
            for e in entries:
                if e.get("name") == b and e.get("blocks"):
                    print("          blocks: %s" % ", ".join(e["blocks"]))
        for x in s["soft"]:
            print("      soft     : %s" % x)
    un = [n for n, s in sides.items() if not s["available"]]
    print("\n  %d of %d sides available" % (len(sides) - len(un), len(sides)))
    if un:
        print("  unavailable: %s" % ", ".join(sorted(un)))
        print("  A side is unavailable while any of its invariants is NOT_MET, no matter")
        print("  how much else is finished. Capability can be partial and still useful;")
        print("  an unmet invariant means nothing on that side works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
