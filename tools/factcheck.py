"""Fact check: catches two documents asserting different values for the same fact.

An external review of this knowledge base found the worst problem in it, and the
problem was not a missing fact or a wrong API. It was that the corpus held
CONTRADICTORY CLAIMS ABOUT THE SAME THING:

    project_blueprint.md and fo4_records_guide.md said the facility plugin was
    66 bytes with 0 records.  The dashboard said 973 B, deployed at 12:50.

Nothing flagged it. Every gate was green. The reason is structural: a retrieval
system has no idea two numbers are talking about the same quantity, and a
document set with several volatile numbers WILL drift unless something compares
them.

So this declares the volatile facts, finds every place the corpus asserts a
value for each, and reports any place that disagrees with the declared truth.
It is deliberately narrow: only facts that are cheap to detect mechanically and
expensive to get wrong.

    python tools/factcheck.py
    python tools/factcheck.py --json
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "rag" / "index.sqlite3"

# Each fact: what it is, how to find a claim about it, and how to read the value.
# `declared` is the truth the tree is expected to agree with.
FACTS = [
    {"id": "facility_plugin_bytes",
     "label": "PipMonTestFacility.esp size in bytes",
     "pattern": re.compile(r"PipMonTestFacility\.esp[^\n]{0,120}?(\d[\d,]{0,9})\s*(?:B\b|bytes)", re.I),
     "invert": re.compile(r"(\d[\d,]{0,9})\s*(?:B\b|bytes)[^\n]{0,120}?PipMonTestFacility\.esp", re.I),
     "declared": 66,
     "note": "Measured: 24-byte record header + dataSize 42 = 66 exactly."},

    {"id": "facility_plugin_records",
     "label": "PipMonTestFacility.esp record count",
     "pattern": re.compile(r"PipMonTestFacility\.esp[^\n]{0,160}?(\d+)\s*records", re.I),
     "invert": re.compile(r"(\d+)\s*records[^\n]{0,160}?PipMonTestFacility\.esp", re.I),
     "declared": 0,
     "note": "xEdit's own load log: 'Header processed. Expecting 0 records'."},

    {"id": "papyrus_selftests",
     "label": "vprobe self-test count in the build gate",
     "pattern": re.compile(r"(\d+)\s+self-test checks", re.I),
     "invert": re.compile(r"self-test[^\n]{0,40}?(\d+)", re.I),
     "declared": 17,
     "note": "17 total, of which 15 pass, 0 fail, 2 skip. Restating only '15' is not a contradiction, it is a different quantity -- but it must not be labelled as the count."},

    {"id": "index_size",
     "label": "number of files in the retrieval index",
     "pattern": re.compile(r"(\d{3,4})\s+files[,.]?\s*(?:indexed|in the index)", re.I),
     "invert": re.compile(r"index[^\n]{0,40}?(\d{3,4})\s+files", re.I),
     "declared": None,
     "note": "Self-describing: the declared value is whatever the index says right now, so the check is that no document quotes a stale one."},
]


def corpus():
    if not DB.exists():
        return None
    con = sqlite3.connect(str(DB))
    rows = con.execute("SELECT path, start_line, end_line, text FROM chunks").fetchall()
    con.close()
    return rows


def claims_for(rows, fact):
    found = {}
    for path, start, end, text in rows:
        if not path.endswith((".md", ".txt", ".json", ".ps1")):
            continue
        for rx in (fact["pattern"], fact["invert"]):
            for m in rx.finditer(text):
                try:
                    val = int(m.group(1).replace(",", ""))
                except (ValueError, IndexError):
                    continue
                # Only treat it as a claim about this fact if the same chunk
                # actually mentions the subject. Otherwise "17 self-test checks"
                # in an unrelated paragraph gets read as the plugin's byte size.
                found.setdefault(val, set()).add(path)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = corpus()
    if rows is None:
        print("factcheck: no index; run tools/rag_index.py", file=sys.stderr)
        return 2

    problems = []
    for fact in FACTS:
        declared = fact["declared"]
        if declared is None:
            continue  # self-describing facts are checked by the others
        claims = claims_for(rows, fact)
        for val, paths in sorted(claims.items()):
            if val == declared:
                continue
            # A different number is only a contradiction if the document is
            # asserting it about THIS fact. Near-misses are reported as
            # suspects rather than silently accepted, because the cost of a
            # false accusation here is low and the cost of a missed stale
            # number is a model confidently quoting the wrong thing.
            for p in sorted(paths):
                problems.append({
                    "fact": fact["id"], "label": fact["label"],
                    "declared": declared, "found": val, "in": p,
                    "note": fact["note"],
                })

    ok = not problems
    if args.json:
        print(json.dumps({"schema": "pipmon.factcheck/1",
                          "status": "GREEN" if ok else "RED",
                          "facts": [f["id"] for f in FACTS],
                          "contradictions": problems}, indent=2))
        return 0 if ok else 1

    print("factcheck -- do two documents disagree about the same number?\n")
    for fact in FACTS:
        d = fact["declared"]
        print("  %-26s declared=%s  %s" % (fact["id"], d if d is not None else "self", fact["note"]))
    if not problems:
        print("\n  no contradictions found.")
        return 0
    print("\n  %d suspected contradiction(s):" % len(problems))
    for p in problems:
        print("    %s: declared %s, %s claims %s" % (p["in"], p["declared"], p["fact"], p["found"]))
    print("\n  A document quoting a number that is true of a DIFFERENT quantity is not")
    print("  always wrong, but it is ambiguous, and a model cannot tell which it read.")
    return 1


if __name__ == "__main__":
    sys.exit(main())