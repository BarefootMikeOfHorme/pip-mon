"""Surfaces gate: every claimed surface points at something that exists.

A surface inventory is a list of promises, and a promise that names a path which
is not there is worse than no inventory: it makes a reader trust that the thing
was checked. So this verifies the checkable parts.

What it verifies:
  * every surface's status is in the closed vocabulary, so a program can branch
    on it rather than read prose
  * every declared path, artifact and index actually exists on disk
  * a surface marked MET with an artifact that is ABSENT is a contradiction,
    not a missing file, and is reported as such
  * every kind is one the inventory declares

What it deliberately does NOT do: it does not re-run each surface. A surface
marked PARTIALLY_MET has, by definition, been run and observed to fall short,
and re-running a three-minute xEdit load inside a lint is how a lint becomes the
thing it was supposed to be checking for. Statuses are established by smoke test
and dated; this only confirms they are at least internally consistent.

    python tools/surfaces_gate.py
    python tools/surfaces_gate.py --json
"""
import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "ai_context" / "spec" / "surfaces.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not SPEC.exists():
        print("surfaces_gate: no spec at %s" % SPEC, file=sys.stderr)
        return 2
    spec = json.loads(SPEC.read_text(encoding="utf-8"))

    statuses = {k for k in (spec.get("status_vocabulary") or {}) if not k.startswith("_")}
    kinds = {k for k in (spec.get("kinds") or {}) if not k.startswith("_")}
    # Some surfaces live outside the repository -- a deployed .pex sits in the
    # game folder, and CreationKit.exe is beside the game. Resolving those
    # against the repo produced fourteen false "missing" reports, so external
    # roots are declared explicitly rather than guessed or skipped.
    roots = {"repo": REPO}
    for name, p in (spec.get("external_roots") or {}).items():
        roots[name] = Path(p)

    def resolve(p):
        p = str(p).split("  (")[0].strip().rstrip("/")
        for name, root in roots.items():
            pref = name + ":"
            if p.startswith(pref):
                return root / p[len(pref):].replace("/", os.sep)
        return roots["repo"] / p.replace("/", os.sep)

    problems = []
    surfaces = spec.get("surfaces", [])
    counts = {}

    for s in surfaces:
        sid = s.get("id", "?")
        st = s.get("status")
        if st not in statuses:
            problems.append(("bad_status", sid, "status %r is not in %s" % (st, sorted(statuses))))
        if s.get("kind") not in kinds:
            problems.append(("bad_kind", sid, "kind %r is not in %s" % (s.get("kind"), sorted(kinds))))
        counts[st] = counts.get(st, 0) + 1

        # Paths claimed by a surface. `path: null` is legitimate and means the
        # surface has no implementation yet, which is different from a broken one.
        for field in ("path", "artifact", "index"):
            p = s.get(field)
            if p is None or p == "":
                continue
            if not resolve(p).exists():
                rule = "contradiction" if st == "MET" else "artifact_missing"
                problems.append((rule, sid,
                                 "%s=%s is not on disk" % (field, p)))

        specs = s.get("specs") or []
        if isinstance(specs, str):
            specs = [specs]
        for dep in specs:
            if not resolve(dep).exists():
                problems.append(("spec_missing", sid, "names spec %s which does not exist" % dep))
        for dep in s.get("provenance", []) or []:
            # Provenance is often "path arg1 arg2" -- a command, not just a file.
            # Check the leading path token, because a citation that names a
            # command with arguments is still a citation.
            if not isinstance(dep, str):
                continue
            tok = dep.split()[0].rstrip(":,;") if dep.split() else ""
            if tok.startswith(("ai_context/", "tools/", "third_party/")) and not resolve(tok).exists():
                problems.append(("provenance_missing", sid, "cites %s which does not exist" % tok))

    ok = not problems
    if args.json:
        print(json.dumps({"schema": "pipmon.surfaces.gate/1",
                          "status": "GREEN" if ok else "RED",
                          "surfaces": len(surfaces), "by_status": counts,
                          "problems": [{"rule": r, "surface": s, "detail": d} for r, s, d in problems]},
                         indent=2))
        return 0 if ok else 1

    print("surfaces gate -- %d surfaces, smoke-tested %s" % (len(surfaces), spec.get("audited", "?")))
    print("  " + "  ".join("%s=%d" % (k, v) for k, v in sorted(counts.items())))
    print()
    for kind in sorted(kinds):
        rows = [s for s in surfaces if s.get("kind") == kind]
        if not rows:
            continue
        print("  %s" % kind)
        for s in rows:
            print("    [%-14s] %-22s %s" % (s["status"], s["id"], s.get("direction", "")))
    for r, s, d in problems:
        print("  [FAIL] %-20s %-22s %s" % (r, s, d))
    print("\n  %d problems" % len(problems))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())