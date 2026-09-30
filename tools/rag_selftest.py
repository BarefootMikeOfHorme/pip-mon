"""Retrieval self-test: the hook that stops this depending on anyone remembering.

Every rule this project relies on about its own knowledge base was, at some
point, true only because someone happened to remember it. Files that describe
the tooling outranked the domain files they quoted. Configuration files came
back as search hits. Objectives went missing and a whole component became
invisible. Each of those shipped as a green gate, because the gate did not
look.

So the invariants are asserted here, mechanically, and this is wired into
build_all.bat. It fails the build rather than reminding a human.

    python tools/rag_selftest.py            # human-readable
    python tools/rag_selftest.py --json     # machine-readable

Exit 0 = every invariant holds. Exit 1 = at least one FAILED, each named.
"""
import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "rag" / "index.sqlite3"
RANKING = REPO / "ai_context" / "ranking.json"

# Known-answer battery. Each is a real question the project gets asked, with the
# file that must answer it. A regression here means retrieval got worse while
# every other gate stayed green, which is precisely the failure this exists for.
KNOWN_ANSWER = [
    ("does CustomEvent exist in FO4 papyrus", "papyrus_syntax_rules.md"),
    ("how do I add a cell with xEdit safely", "fo4_records_guide.md"),
    ("bunker Ravine exterior door entrance", "DOOR-SPEC.md"),
    ("FO4 Scaleform ActionScript 3 widget", "scaleform"),
    ("StartTimer CancelTimer timer id OnTimer", None),
    ("AddNewFileName creates a new empty plugin", "fo4_records_guide.md"),
    ("pipeline stages S0 S1 S2 S3 canary", None),
    ("load order curated profile plugins.txt", None),
    # Regression guards. Each of these was WRONG at some point while every other
    # stage stayed green:
    #  - "BSScript vtable slot declaration" returned the Papyrus syntax rules,
    #    because substring expansion matched "script" inside "BSScript" and
    #    pulled in the whole Papyrus group.
    #  - "FO4 Scaleform ActionScript 3 widget" returned the same Papyrus chunk.
    #  - A cap of 3.0 on the stacked multiplier broke the CustomEvent query that
    #    had been correct, by flattening the authority ordering.
    ("BSScript vtable slot declaration", None),
    ("make the papyrus event fire", "papyrus_syntax_rules.md"),
]

# Files that must exist on disk. A missing upstream reference is a silent
# capability loss: the model simply stops knowing something.
REQUIRED_FILES = [
    "ai_context/papyrus_syntax_rules.md",
    "ai_context/fo4_records_guide.md",
    "ai_context/project_blueprint.md",
    "ai_context/skyrim_capability_adoption.md",
    "ai_context/ranking_model.md",
    "ai_context/goal_alignment.md",
    "ai_context/rag_output_contract.md",
    "ai_context/vocabulary.json",
    "ai_context/ranking.json",
    "ai_context/reference/xedit/13-scripting-functions.md",
    "ai_context/automation/xedit-script-patterns.md",
    "ai_context/systems/f4se-plugin-structure.md",
    "tools/rag_index.py",
    "tools/rag_query.py",
    "tools/ai_watcher.py",
]

# Vendored native reference code. If this disappears, the engine-layout half of
# the knowledge base goes with it and nothing would report the loss.
REQUIRED_NATIVE = [
    "third_party/CommonLibF4/CommonLibF4/include/RE/Bethesda/BSScript.h",
    "third_party/CommonLibF4/CommonLibF4/include/RE/VTABLE_IDs.h",
]


class Results:
    def __init__(self):
        self.rows = []

    def add(self, name, ok, detail=""):
        self.rows.append({"check": name, "ok": bool(ok), "detail": detail})
        return ok

    @property
    def failed(self):
        return [r for r in self.rows if not r["ok"]]


def run_query(q, limit=1):
    p = subprocess.run(
        [sys.executable, str(REPO / "tools" / "rag_query.py"), q,
         "--limit", str(limit), "--format", "paths"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    for line in (p.stdout or "").splitlines():
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 3:
                return parts[2]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    R = Results()

    if not DB.exists():
        R.add("index exists", False, "no %s -- run: python tools/rag_index.py" % DB)
        return emit(R, args.json)
    R.add("index exists", True, str(DB.relative_to(REPO)))

    ranking = {}
    if RANKING.exists():
        try:
            ranking = json.loads(RANKING.read_text(encoding="utf-8"))
            R.add("ranking.json parses", True, "%d top-level keys" % len(ranking))
        except ValueError as e:
            R.add("ranking.json parses", False, str(e))
    else:
        R.add("ranking.json parses", False, "missing")

    con = sqlite3.connect(str(DB))

    # 1. Configuration must never be retrievable. vocabulary.json is a list of
    #    the words queries use, so indexing it makes it match everything.
    indexed = {r[0] for r in con.execute("SELECT path FROM files")}
    for cfg in ("ai_context/vocabulary.json", "ai_context/ranking.json"):
        R.add("config not indexed: %s" % cfg, cfg not in indexed,
              "excluded" if cfg not in indexed else "IT IS INDEXED")

    # 2. System documents must be auto-tagged meta, or they outrank the domain
    #    files they merely quote. This happened four times.
    pats = [p.lower() for p in (ranking.get("auto_meta") or {}).get("patterns", [])]
    bad = []
    for path, scope in con.execute("SELECT path, scope FROM files"):
        name = path.rsplit("/", 1)[-1].lower()
        if any(name.endswith(p) for p in pats) and scope != "meta":
            bad.append(path)
    R.add("system docs auto-tagged meta", not bad,
          "ok" if not bad else "not meta: " + ", ".join(bad[:4]))

    # 3. Every objective must be reachable through its own markers. A missing
    #    objective makes its whole component unretrievable, which is how
    #    overseer_cli went invisible the first time. The test is on markers, not
    #    on the objective's name: names are identifiers like papyrus-correctness
    #    and appear in no source file, so searching for them tested nothing.
    objs = [k for k in (ranking.get("objectives") or {}) if not k.startswith("_")]
    markers = ranking.get("objective_markers") or {}
    unreachable = []
    for o in objs:
        marks = [m for m in markers.get(o, []) if not m.startswith("_")]
        if not marks:
            unreachable.append("%s (no markers defined)" % o)
            continue
        found = 0
        for m in marks:
            if con.execute("SELECT 1 FROM chunks WHERE lower(text) LIKE ? LIMIT 1",
                           ("%" + m.lower() + "%",)).fetchone():
                found += 1
        if found == 0:
            unreachable.append("%s (0/%d markers present)" % (o, len(marks)))
    R.add("every objective is reachable", not unreachable,
          "%d objectives" % len(objs) if not unreachable
          else "; ".join(unreachable))

    # 4. Required files present.
    missing = [f for f in REQUIRED_FILES if not (REPO / f).exists()]
    R.add("required context files present", not missing,
          "%d files" % len(REQUIRED_FILES) if not missing else "missing: " + ", ".join(missing[:5]))

    missing_native = [f for f in REQUIRED_NATIVE if not (REPO / f).exists()]
    R.add("vendored native headers present", not missing_native,
          "ok" if not missing_native else "missing: " + ", ".join(missing_native))

    # 5. Index is not stale relative to the workspace.
    newest = con.execute("SELECT MAX(mtime) FROM files").fetchone()[0] or 0
    newest_src = 0.0
    for f in REQUIRED_FILES:
        p = REPO / f
        if p.exists():
            newest_src = max(newest_src, p.stat().st_mtime)
    R.add("index not stale", newest >= newest_src - 2,
          "newest indexed %.0f vs newest source %.0f" % (newest, newest_src))
    con.close()

    # 6. Known-answer battery, end to end through the real CLI.
    wrong = []
    for q, expect in KNOWN_ANSWER:
        top = run_query(q)
        if top is None:
            wrong.append("%s -> NO HITS" % q)
        elif expect and expect.lower() not in top.lower():
            wrong.append("%s -> %s (wanted %s)" % (q, top, expect))
    R.add("known-answer battery", not wrong,
          "%d queries" % len(KNOWN_ANSWER) if not wrong else "; ".join(wrong[:3]))

    return emit(R, args.json)


def emit(R, as_json):
    if as_json:
        print(json.dumps({
            "schema": "pipmon.rag.selftest/1",
            "status": "GREEN" if not R.failed else "RED",
            "checks": R.rows,
        }, indent=2))
        return 0 if not R.failed else 1

    for r in R.rows:
        print("  [%s] %-34s %s" % ("PASS" if r["ok"] else "FAIL", r["check"], r["detail"]))
    n = len(R.rows)
    bad = len(R.failed)
    print("rag_selftest: %d checks, %d passed, %d FAILED" % (n, n - bad, bad))
    if bad:
        print("retrieval invariants are broken. The knowledge base is not trustworthy")
        print("until these pass; fix the cause, do not relax the check.")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
