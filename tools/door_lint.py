"""Door lint: keeps the hallway's doors real.

The design record says the hallway (section 26.5) is an access layer providing
navigation, depth and provenance. A hallway with no door inventory is a
corridor, so the inventory is this file's registry and this tool is what stops
it rotting.

The project's own audit is the reason this exists. A reader-facing document
disagreed with three separately-asserted implementations, and a stale size was
sitting in a field the code comments already said had been fixed.
Documentation drift here is not cosmetic, so a door's existence, uniqueness and
keeper are CHECKED rather than asserted.

What it enforces:
  1. Every registered door's target file EXISTS. A door to nowhere is worse
     than no door, because it is trusted.
  2. No two doors claim the same id.
  3. Every door's state is one the legend defines, so 'fine' cannot be a state.
  4. Every door that names a keeper HAS that keeper on disk, and the keeper
     actually runs. A door that claims a validator nobody executes is the
     documentation equivalent of a check that is never run.
  5. UNREGISTERED doors are reported. Any top-level or docs/ markdown file that
     looks like a door but is not in the registry is surfaced, because that is
     precisely how a table stops being complete: someone adds a document and
     nobody records that it is now a way in.

    python tools/door_lint.py
    python tools/door_lint.py --json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "ai_context" / "systems_core" / "door_registry.json"
LEGEND = {"CURRENT", "PARTLY_FIXED", "STALE", "SUPERSEDED", "BUILT"}
# Directories whose markdown is reference material or vendored source rather
# than a view onto our own program.
NOT_A_DOOR_PREFIX = ("third_party/", "ai_context/reference/", "runs/", "rag/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    problems = []

    if not REGISTRY.exists():
        print("door_lint: no registry at %s" % REGISTRY, file=sys.stderr)
        return 2
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    doors = reg.get("doors", [])
    notes = []

    seen = set()
    keepers = {}
    for d in doors:
        did = d.get("id", "?")
        if did in seen:
            problems.append(("duplicate_id", did, "id appears more than once in the registry"))
        seen.add(did)

        state = d.get("state")
        if state not in LEGEND:
            problems.append(("bad_state", did,
                             "state %r is not one of %s" % (state, sorted(LEGEND))))

        target = d.get("path")
        if not target:
            problems.append(("no_path", did, "a door with no location is not a door"))
        elif not (REPO / target).exists():
            problems.append(("missing_target", did, "no file at %s" % target))

        if not d.get("question"):
            problems.append(("no_question", did, "a door that does not say what question it "
                                                  "answers cannot be navigated to"))

        keeper = d.get("keeper")
        if keeper:
            if not (REPO / keeper).exists():
                problems.append(("missing_keeper", did, "names keeper %s which does not exist" % keeper))
            else:
                # Collected, not run, here. Running per door meant a validator
                # named by six doors was executed six times, and door_lint timed
                # out at 400s doing it. Each distinct keeper runs exactly once.
                keepers.setdefault(keeper, []).append(did)

    for keeper, doors_guarded in sorted(keepers.items()):
        # A tool cannot be its own keeper. When the registry named door_lint as
        # the keeper for the doors door_lint structurally checks, this spawned
        # itself once per door and hung past 600s. Self-reference is also a
        # tautology: the check that guards a door must be independent of the
        # tool doing the guarding.
        if Path(keeper).resolve() == Path(__file__).resolve():
            notes.append("keeper for %s is door_lint itself; ignored as a tautology. "
                         "These doors are guarded structurally only (existence, state, "
                         "question), and their CONTENT has no automated check."
                         % ", ".join(doors_guarded))
            continue
        try:
            r = subprocess.run([sys.executable, str(REPO / keeper)], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=600)
            if r.returncode != 0:
                problems.append(("keeper_failing", keeper,
                                 "exits %d, but guards %d door(s): %s -- a door guarded by "
                                 "something broken is worse than unguarded, because it is trusted"
                                 % (r.returncode, len(doors_guarded), ", ".join(doors_guarded))))
        except subprocess.TimeoutExpired:
            problems.append(("keeper_hanging", keeper,
                             "did not finish in 600s; it guards %s" % ", ".join(doors_guarded)))

    # Unregistered doors: a top-level or docs/ markdown file that is not listed.
    candidates = []
    for pat in ("*.md", "docs/*.md", "tools/*.md", "ai_context/*.md",
                "ai_context/spec/*.md", "ai_context/systems_core/*.md",
                "ai_context/engine/*/*.md", "ai_context/systems/*/*.md",
                "ai_context/automation/*.md", "vprobe/papyrus/*.md"):
        for p in sorted(REPO.glob(pat)):
            rel = p.relative_to(REPO).as_posix()
            if rel.startswith(NOT_A_DOOR_PREFIX) or rel == REGISTRY.relative_to(REPO).as_posix():
                continue
            candidates.append(rel)
    registered = {d.get("path") for d in doors if d.get("path")}
    registered |= {str(REGISTRY.relative_to(REPO)).replace("\\", "/")}
    # Respect the registry's own not_a_door list, so a file that has been
    # deliberately classified does not keep being reported. A linter that keeps
    # crying about a settled question is the same failure as a permanently red
    # gate: it teaches people to skim its output.
    declared_not = []
    for ex in reg.get("not_a_door", []):
        pat = ex.get("path", "")
        declared_not.append(pat.rstrip("/*"))
    unregistered = [c for c in candidates
                    if c not in registered
                    and not any(c.startswith(p) or ("/" + c) in p or c.endswith(p.rsplit("/", 1)[-1])
                                for p in declared_not if p)]

    ok = not problems
    if args.json:
        print(json.dumps({
            "schema": "pipmon.door.lint/1",
            "status": "GREEN" if ok else "RED",
            "doors": len(doors),
            "problems": [{"rule": p[0], "door": p[1], "detail": p[2]} for p in problems],
            "unregistered_candidates": unregistered,
        }, indent=2))
        return 0 if ok else 1

    print("door_lint: %d doors registered" % len(doors))
    for note in notes:
        print("  note: %s" % note)
    for rule, door, detail in problems:
        print("  [FAIL] %-16s %-10s %s" % (rule, door, detail))
    if unregistered:
        print("  markdown that could become a door but is not registered (%d):" % len(unregistered))
        for u in unregistered:
            print("      %s" % u)
    print("door_lint: %d problems, %d unregistered candidates" % (len(problems), len(unregistered)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
