"""Artifact-gate self-test: does the FO4 construct ban actually discriminate?

    python tools/gate_selftest.py             # human-readable
    python tools/gate_selftest.py --json      # machine-readable

Exit 0 = every case behaved as specified. Exit 1 = at least one FAILED, named.

WHY THIS EXISTS
---------------
`ai_context/spec/papyrus_constructs.json` bans constructs that do not compile in
FO4 Papyrus, and `tools/artifact_gate.py` enforces that by matching tokens. Two
properties of that design are easy to break and invisible when broken:

1. **A stem that matches nothing looks exactly like a green gate.** The
   "array length intrinsic" entry shipped a `Count` stem of `array.Count`,
   which `word_hit()` matches literally, so it fired only on a variable actually
   NAMED `array`. Every real call -- `Roster.Count`, `myList.Count` -- passed
   the gate silently. The spec said the thing was banned; it was not enforced.

2. **An over-broad exemption hides real errors.** The same entry also needed an
   exception, because `GetSize` IS legal on a `FormList` (FormList.psc declares
   `int Function GetSize() native`). Putting that exception on the whole entry
   also exempted `Count` -- which is illegal on a FormList too, proven by
   compiling. An exception scoped one step too wide is a gate that stopped
   looking, and no test failed, because the test was this file and it did not
   exist.

Both shipped as green. The gate reported success, the spec read correctly, and
neither matched reality. So the cases are asserted here mechanically, and this
is wired into build_all.bat: it fails the build rather than reminding a human.

HOW THE CASES ARE BUILT
-----------------------
A temporary .psc is written per case group into a scratch directory, never into
the repo -- an earlier version of this check wrote a probe into
`pip_mon_testlab/Scripts/Source/` and it had to be deleted by hand, which is
exactly the kind of thing a self-test should never do. The gate is asked to scan
it and the real .psc files alongside each other, and the expectation is per LINE.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Each case: (line_text, should_be_flagged, why). Lines are assembled into one
# file so the gate's per-file property resolution is exercised too -- that is
# what makes the FormList exemption testable at all.
DECLARATIONS = [
    "int[] property Plain auto readonly",
    "int[] property Roster auto readonly",
    "FormList property Listed auto readonly",
    "FormList property MyList auto readonly",
]

CASES = [
    # (source line, expect flagged, rationale)
    ("int a = Plain.GetSize()", True,
     "GetSize on a plain array is fatal; the exception must not cover it"),
    ("int b = Roster.Count", True,
     "bare .Count, arbitrary receiver name -- the case the old 'array.Count' "
     "stem let through"),
    ("int c = Listed.Count()", True,
     ".Count is illegal on FormList too, so the exception must not cover it"),
    ("int d = Listed.GetLength()", True,
     "GetLength is banned unconditionally, FormList included"),
    ("int e = Listed.GetSize()", False,
     "the one legal case: FormList declares GetSize"),
    ("int f = MyList.GetSize()", False,
     "second FormList property, so the exemption is not hardcoded to one name"),
    ("int g = Roster.Size", True,
     "bare .Size, the property spelling with no parens"),
    ("int h = Roster.Size()", True,
     ".Size() the call spelling; both forms must be caught"),
    ("int i = Listed.Size()", True,
     ".Size is illegal on FormList as well"),
]


def build_probe(tmp: Path) -> Path:
    p = tmp / "gate_selftest_probe.psc"
    body = ["Scriptname GateSelfTestProbe", ""]
    body += DECLARATIONS
    body += ["", "Function F()"]
    for line, _, _ in CASES:
        body.append("    " + line)
    body.append("EndFunction")
    p.write_text("\n".join(body) + "\n", encoding="utf-8")
    return p


def run_gate(probe: Path):
    """Ask the gate's own scanner about one file; return flagged (line, construct).

    Calls `scan_tokens` directly rather than `main()`. `main()` walks the whole
    repository and prints a report, which makes it useless for asserting on a
    single synthetic file -- and walking the repo to test the scanner would also
    couple this test to whatever else happens to be in the tree. `scan_tokens` is
    the unit under test: it is what decides whether a line is a violation.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "artifact_gate", REPO / "tools" / "artifact_gate.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    papyrus = mod.load("papyrus_constructs.json")
    hits = list(mod.scan_tokens(probe, papyrus.get("entries", []), "exists_in_fo4", "papyrus"))
    return [(ln, e.get("name", "")) for ln, _, e in hits]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks = []

    with tempfile.TemporaryDirectory(prefix="pipmon_gate_selftest_") as td:
        probe = build_probe(Path(td))
        hits = run_gate(probe)
        flagged = {ln for ln, _ in hits}

        # The probe is built in a known order, so each case's line is computable:
        # Scriptname, blank, the declarations, blank, "Function F()", then cases.
        first_case = 1 + 1 + len(DECLARATIONS) + 1 + 1 + 1
        for i, (line, expect, why) in enumerate(CASES):
            ln = first_case + i
            got = ln in flagged
            checks.append({
                "case": line.strip(),
                "line": ln,
                "expected": "flagged" if expect else "clean",
                "actual": "flagged" if got else "clean",
                "ok": got == expect,
                "why": why,
            })

    failed = [c for c in checks if not c["ok"]]
    if args.json:
        print(json.dumps({
            "status": "RED" if failed else "GREEN",
            "checks": len(checks),
            "failed": len(failed),
            "cases": checks,
        }, indent=2))
    else:
        print("Artifact-gate discrimination self-test")
        print("Does the FO4 construct ban flag what it must and exempt what it must?\n")
        for c in checks:
            mark = "PASS" if c["ok"] else "FAILED"
            print(f"    [{mark:6}] {c['expected']:7} {c['actual']:7}  {c['case']}")
            if not c["ok"]:
                print(f"             expected {c['expected']}, got {c['actual']} -- {c['why']}")
        print()
        if failed:
            print(f"  {len(failed)} FAILED of {len(checks)}")
        else:
            print(f"  all {len(checks)} cases behaved as specified")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
