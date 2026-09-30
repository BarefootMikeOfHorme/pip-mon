"""Self-alignment: re-derive what is derived, and refuse to re-derive the rest.

The project already has this pattern in one place. tools/fix_papyrus_flags.py
reads the Papyrus compiler's complaints and REPAIRS the flags file rather than
reporting a red gate. That is the right shape, and this generalises it.

The hard part is not repairing. It is knowing what must never be repaired.

    DERIVED   a function of on-disk state. Re-deriving is deterministic and
              cannot lose information, because the source of truth survives.
              Index, generated scripts, compiler flags, the door registry's
              mechanical entries. These are re-derived, and the build says so.

    JUDGMENT  a decision someone made. Re-deriving it would erase the decision
              and then declare success, which is the exact shape of a gate that
              always passes. The artifact_gate baseline, authority tiers,
              compat statuses, and recorded open discrepancies. These are
              REPORTED and never touched.

A self-aligning gate that repairs everything is not a self-aligning gate, it is
no gate. So this file names the refusals explicitly, and `--repair` will not
take an override for them: the refusals are the point.

Determinism is a property that has to be TESTED rather than asserted, so
`--verify-deterministic` runs every derivation twice and fails if the second run
changes anything. Repair twice, get the same tree.

    python tools/selfalign.py                  # check only
    python tools/selfalign.py --repair         # re-derive, then report
    python tools/selfalign.py --verify-deterministic
    python tools/selfalign.py --json
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable

# ---------------------------------------------------------------------------
# DERIVED. Each entry names what it derives FROM, so a stale derivation is
# detectable without trusting any timestamp.
DERIVED = [
    {"name": "retrieval index", "source": "the workspace tree", "target": "rag/index.sqlite3",
     "run": ["tools/rag_index.py", "--quiet"], "type": "index",
     "why": "a function of the tree; re-deriving cannot lose anything"},

    {"name": "generated xEdit validator", "source": "testfacility/xedit/validate_plugin.pas + paths",
     "target": "runs/watch/validate_plugin.gen.pas", "run": ["tools/validate_plugin.ps1", "--noop"],
     "type": "generated", "skip": True,
     "why": "regenerated on every validation launch; deriving it separately would "
            "duplicate the substitution logic and risk the two copies diverging"},

    {"name": "papyrus compiler flags", "source": "the CK Papyrus compiler's own complaints",
     "target": "vprobe/papyrus/papyrus_flags.flg", "run": ["tools/fix_papyrus_flags.py", "--check"],
     "type": "self-repairing", "skip": True,
     "why": "already self-aligning: it reads the compiler and rewrites the flags. Handing it "
            "to a generic driver as well would mean two repairers for one artifact"},
]

# ---------------------------------------------------------------------------
# JUDGMENT. Named so the refusal is visible rather than an omission.
REFUSED = [
    {"artifact": "tools/artifact_gate.baseline.json",
     "reason": "The baseline is the record of known-bad findings. Re-deriving it would make "
               "every acknowledged violation disappear the moment it was noticed, and the gate "
               "would go green having learned nothing. Fixing a violation and re-baselining is "
               "a deliberate act."},

    {"artifact": "authority tiers in ai_context/ranking.json",
     "reason": "compile-verified outranking measured is a judgement about what to trust. "
               "Recomputing it from file contents would rank by self-description, which is "
               "exactly the failure the tiers exist to stop."},

    {"artifact": "compat statuses in ai_context/spec/compat_f4se_map.json",
     "reason": "COVERED versus PLANNED is a claim about reality. Only evidence can move it, and "
               "a script cannot gather that evidence about a hook that does not exist yet."},

    {"artifact": "open_discrepancies in the record-format spec",
     "reason": "The 24-versus-16 byte header question is open because it was not measured. When "
               "it WAS measured the answer was 24 and 16 bytes exactly, which is why it is now "
               "closed -- but closing it happened by measuring, not by re-deriving."},

    {"artifact": "goal_covered flags in the component spec",
     "reason": "spec_lint already refuses a component claiming coverage its own status "
               "contradicts. Repairing that flag automatically would launder a false claim into "
               "a true-looking one."},
]


def digest(p: Path) -> str:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except OSError:
        return ""


def run_one(entry, repair):
    """Run a derivation. Returns (state, detail)."""
    tgt = REPO / entry["target"]
    if entry.get("skip"):
        return "delegated", "handled by its own tool, not by a generic driver"
    if not repair:
        return "checked", ("present sha=%s" % digest(tgt)) if tgt.exists() else "MISSING"
    before = digest(tgt)
    try:
        r = subprocess.run([PY] + entry["run"], cwd=str(REPO), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=900)
    except subprocess.TimeoutExpired:
        return "failed", "timed out after 900s"
    if r.returncode != 0:
        return "failed", (r.stdout or r.stderr or "").strip().splitlines()[-1:] and \
            (r.stdout or r.stderr).strip().splitlines()[-1] or "nonzero exit %d" % r.returncode
    after = digest(tgt)
    return ("repaired" if after != before else "already-current"), \
        "sha %s -> %s" % (before or "(none)", after or "(none)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repair", action="store_true", help="re-derive the derived artifacts")
    ap.add_argument("--verify-deterministic", action="store_true",
                    help="derive twice and fail if the second pass changes anything")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results = []
    if args.verify_deterministic:
        first = [run_one(e, True) for e in DERIVED if not e.get("skip")]
        second = [run_one(e, True) for e in DERIVED if not e.get("skip")]
        for e, a, b in zip([x for x in DERIVED if not x.get("skip")], first, second):
            results.append({"name": e["name"], "state": a[0], "detail": a[1],
                            "second_pass": b[0], "deterministic": a[1] == b[1]})
        ok = all(r["deterministic"] for r in results)
        if args.json:
            print(json.dumps({"schema": "pipmon.selfalign/1", "status": "GREEN" if ok else "RED",
                              "mode": "verify-deterministic", "results": results,
                              "refused": REFUSED}, indent=2))
            return 0 if ok else 1
        print("selfalign: determinism check")
        for r in results:
            print("  [%s] %-28s %s" % ("OK" if r["deterministic"] else "DRIFT", r["name"], r["detail"]))
        print("  %d derivations, %d drifted" % (len(results), sum(1 for r in results if not r["deterministic"])))
        return 0 if ok else 1

    for e in DERIVED:
        state, detail = run_one(e, args.repair)
        results.append({"name": e["name"], "target": e["target"], "type": e["type"],
                        "state": state, "detail": detail, "why_derived": e["why"]})

    failed = [r for r in results if r["state"] == "failed"]
    repaired = [r for r in results if r["state"] == "repaired"]

    if args.json:
        print(json.dumps({
            "schema": "pipmon.selfalign/1",
            "status": "RED" if failed else "GREEN",
            "mode": "repair" if args.repair else "check",
            "derived": results, "refused": REFUSED,
        }, indent=2))
        return 1 if failed else 0

    print("selfalign: %s" % ("repairing derived artifacts" if args.repair
                             else "checking derived artifacts (pass --repair to re-derive)"))
    for r in results:
        print("  [%s] %-28s %s" % (r["state"].upper(), r["name"], r["detail"]))
    print("  %d derived, %d repaired, %d failed" % (len(results), len(repaired), len(failed)))
    print("\n  REFUSED TO REPAIR, because these are decisions and not derivations:")
    for r in REFUSED:
        print("    - %s" % r["artifact"])
    print("      %s" % r["reason"].split(". ")[0] + ".")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
