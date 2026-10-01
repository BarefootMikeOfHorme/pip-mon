"""Ownership gate: keeps the side-of-the-aisle table honest.

The index covers 777 files, so "is it in the RAG" is not a question with a
useful answer. What matters is what a reader should QUERY, what they should go
READ, and what is deliberately unreachable. That is three of five buckets, and
all three are checkable:

  knowledge   must EXIST, or the table is lying about what we know
  excluded    must be ABSENT from the index, or a retrieval will find it
  not_written must NOT EXIST, or the table is stale

The last one is the useful direction. When someone fills a documented gap, this
reports the table as out of date. Filling a known gap then tells you to update
the record, rather than leaving a claim that something does not exist sitting
there after it started existing -- which is how a reader ends up trusting a
stale "not written".

It deliberately does NOT check source, captured or out_of_side. Those are
judgements about intent, not facts about the filesystem, and this gate has the
same rule selfalign.py follows: repair or verify what is DERIVED, and never
manufacture a fact about a decision.

    python tools/ownership_gate.py
    python tools/ownership_gate.py --json
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "ai_context" / "spec" / "side_ownership.json"
DB = REPO / "rag" / "index.sqlite3"


def indexed_paths():
    if not DB.exists():
        return None
    con = sqlite3.connect(str(DB))
    out = {r[0] for r in con.execute("SELECT path FROM files")}
    con.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not SPEC.exists():
        print("ownership_gate: no spec at %s" % SPEC, file=sys.stderr)
        return 2
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    idx = indexed_paths()
    problems = []

    def base_of(entry):
        """Strip trailing annotations like 'third_party/x  (note)' and / suffixes."""
        p = entry.split("  (")[0].strip().rstrip("/")
        return p

    for side in spec.get("sides", []):
        name = side.get("side", "?")

        for k in side.get("knowledge", []):
            p = base_of(k)
            if not (REPO / p).exists():
                problems.append(("knowledge_missing", name,
                                 "claims %s is knowledge we have, but it does not exist" % p))

        for k in side.get("excluded", []):
            p = base_of(k)
            if not (REPO / p).exists():
                problems.append(("excluded_absent_from_disk", name,
                                 "claims %s is excluded, but there is nothing there" % p))
            elif idx and not any(i == p or i.startswith(p + "/") for i in idx):
                continue  # correctly absent from the index
            elif idx:
                problems.append(("excluded_but_indexed", name,
                                 "claims %s is excluded from retrieval, but the index has it" % p))

        for g in side.get("not_written", []):
            gap = g.get("gap", "?")
            words = gap.lower().split()
            # A gap is prose, so this checks the obvious case only: a gap whose
            # first word names a real path that now exists.
            cand = REPO / words[0]
            if len(words[0]) > 3 and cand.exists() and not cand.is_dir():
                problems.append(("gap_now_exists", name,
                                 "gap %r names %s, which now exists -- update the table" % (gap, words[0])))

    ok = not problems
    if args.json:
        print(json.dumps({"schema": "pipmon.ownership.gate/1",
                          "status": "GREEN" if ok else "RED",
                          "sides": [s.get("side") for s in spec.get("sides", [])],
                          "problems": [{"rule": r, "side": s, "detail": d} for r, s, d in problems]},
                         indent=2))
        return 0 if ok else 1

    print("ownership gate -- per side: what to QUERY, what to READ, what is unreachable\n")
    for side in spec.get("sides", []):
        counts = {k: len(side.get(k, [])) for k in
                  ("knowledge", "source", "captured", "excluded", "not_written")}
        mark = "AVAILABLE" if side.get("available") else "UNAVAILABLE"
        print("  %-14s %-12s knowledge=%d source=%d captured=%d excluded=%d gaps=%d"
              % (side.get("side"), mark, counts["knowledge"], counts["source"],
                 counts["captured"], counts["excluded"], counts["not_written"]))
    for r, s, d in problems:
        print("  [FAIL] %-26s %-14s %s" % (r, s, d))
    print("\n  %d problems. Checked: knowledge exists, excluded is really excluded," % len(problems))
    print("  and documented gaps have not quietly stopped being gaps.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
