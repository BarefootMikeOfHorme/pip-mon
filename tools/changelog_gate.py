"""Changelog coverage gate: is the human index still behind git log?

This exists because it failed TWICE by hand before it was written.

  7d03986  caught the first drift - R2 and R3 were committed without
           being logged - and fixed it as a one-off action
  R9       found the SECOND drift, seven commits later, the same way

Two failures of the same kind is a signal that the discipline is not a
discipline, it is a habit. Habits are not gates. So:

    python tools/changelog_gate.py
    python tools/changelog_gate.py --json
    python tools/changelog_gate.py --since 1344d4d

WHAT IT CHECKS
  Every commit reachable from HEAD~1 back to the baseline must have its
  short sha named somewhere in tasks/roadmap/CHANGELOG.md.

WHY HEAD~1 AND NOT HEAD
  A commit cannot contain its own sha. The newest commit is therefore
  always one entry behind by construction, and checking it would make the
  gate permanently red and therefore ignorable. This is the same reason
  build_all.bat validates artefacts rather than trusting an exit code:
  the newest thing is the least verifiable thing.

WHAT IT DOES NOT CHECK
  Whether the entry is any good. A sha named in a table of contents passes.
  This gate enforces the INDEX, not the writing - that is what a human
  reader is for, and pretending otherwise would be the decoration this
  project keeps refusing to build.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHANGELOG = REPO / "tasks" / "roadmap" / "CHANGELOG.md"
DEFAULT_BASELINE = "1344d4d"


def sh(*args):
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--since", default=DEFAULT_BASELINE,
                    help="exclusive lower bound; the baseline commit itself is not checked")
    args = ap.parse_args()

    problems = []

    if not CHANGELOG.exists():
        print("changelog_gate: no changelog at %s" % CHANGELOG, file=sys.stderr)
        return 2

    text = CHANGELOG.read_text(encoding="utf-8")

    # Resolve the baseline to a sha so a short or long ref both work.
    try:
        sh("rev-parse", "--verify", "%s^{commit}" % args.since)
    except subprocess.CalledProcessError:
        print("changelog_gate: baseline %r is not a commit" % args.since, file=sys.stderr)
        return 2

    raw = sh("log", "--format=%h%x1f%s", "%s..HEAD~1" % args.since)
    commits = []
    for line in raw.splitlines():
        if "\x1f" in line:
            sha, subject = line.split("\x1f", 1)
            commits.append((sha, subject))

    if not commits:
        print("changelog_gate: no commits in %s..HEAD~1 - nothing to check" % args.since)
        return 0

    # Every shas the changelog names, in backticks, so a prose mention of a
    # sha in the corrections section does not accidentally satisfy this.
    named = set(re.findall(r"`([0-9a-f]{7,40})`", text))

    for sha, subject in commits:
        if sha not in named:
            problems.append({"sha": sha, "rule": "unlogged", "subject": subject})

    ok = not problems
    if args.json:
        print(json.dumps({
            "schema": "pipmon.changelog.gate/1",
            "status": "GREEN" if ok else "RED",
            "changelog": str(CHANGELOG.relative_to(REPO)).replace("\\", "/"),
            "baseline": args.since,
            "checked": len(commits),
            "problems": problems,
        }, indent=2))
        return 0 if ok else 1

    print("changelog_gate: %d commit(s) since %s, %d named in the changelog"
          % (len(commits), args.since, len(commits) - len(problems)))
    for p in problems:
        print("  [FAIL] %s  %s" % (p["sha"], p["subject"][:70]))
    if not ok:
        print("")
        print("  The changelog is the walkable index; a commit message is per-commit.")
        print("  Add the missing entries, then commit. It has now drifted twice, which")
        print("  is why this gate exists rather than a reminder to be careful.")
    print("changelog_gate: %d problems" % len(problems))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
