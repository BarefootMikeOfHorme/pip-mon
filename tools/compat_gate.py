"""Compat gate: the replacement map may not drift from a decision to an aspiration.

THE DEFECT THIS EXISTS FOR
    ai_context/spec/legacy_replacement.json is the canonical answer to "which
    legacy product do we replace, how, and what do we add beyond it". It is
    31 rows, it is spec_lint-clean, and every row carries provenance. Its
    `status` field uses a CLOSED six-value vocabulary declared in
    ai_context/spec/schema.json: COVERED, DECLARED, PLANNED, NOT_PLANNED,
    REJECTED, DIFFERENT_MECHANISM.

    So `status` can be edited from REJECTED to PLANNED -- turning a measured
    refusal into an aspiration -- and the row still parses, still has notes,
    still has provenance, and nothing notices. That is the specific failure this
    gate exists to catch, and it is invisible to every other check in the tree.

    Nothing catches it because both the old and the new value are LEGAL. A
    REJECTED row that keeps its notes and becomes PLANNED satisfies every static
    rule there is. Only a comparison against history sees it. So this gate is
    two halves, and the honest half is the one that does most of the work:

      static  four rules over the committed file, cheap, always run
      drift   the same rows read at every commit that touched the file, and any
              status that changed is reported with its sha

    ONE CORRECTION TO THAT, MEASURED RATHER THAN ASSUMED. The first draft of this
    file claimed the static half cannot see the flip at all. It can, sometimes,
    for the wrong reason: a flipped row becomes PLANNED, and
    `planned_without_depends_on` fires on it -- a rule about a different field,
    which has nothing to do with drift. Supply that field and the identical flip
    goes green again. Both states are in --self-test. So the accurate claim is
    that the static half catches some instances of this defect by accident, and
    one edit removes the accident, and the drift half is the only thing aimed at
    it.

THE FOUR STATIC RULES
    1. `status` must be in the closed vocabulary. Read from schema.json's
       `compat_status_vocabulary`, never hardcoded here, so the gate follows the
       contract instead of a copy of it that can rot.
    2. NOT_PLANNED and REJECTED must carry a non-empty note. schema.json says it
       outright: "An unexplained refusal is indistinguishable from an oversight."
    3. COVERED must cite a `spec`. Parity with nothing named is not a claim.
    4. EXTENSION, and flagged as one: a cited `spec` must EXIST on disk.
       Rule 3 is satisfied by citing a path that is not there, which is a
       dangling promise. tools/spec_lint.py applies exactly this check to
       nomenclature entries and calls it "a dangling promise"; it does not apply
       it to a compat_mapping row, and rule 3 without it is theatre.

OVERLAP WITH tools/spec_lint.py, STATED BECAUSE IT IS REAL
    Rules 1, 2 and 3 are also enforced by spec_lint.py, inline in main(), over
    every `kind: compat_mapping` spec. That is a genuine second implementation
    of one rule and it is not hidden. Why it is tolerable here rather than
    netted out: spec_lint is the shape-and-type linter that runs on every build,
    while this gate is the change-control gate for one file, and it is where
    `--strict`, the findings table and the drift half live. What BOTH read is
    single-source -- `compat_status_vocabulary` in schema.json -- so the two
    cannot disagree about what is legal. Reported to the coordinator as a
    consolidation candidate; not consolidated unilaterally, because
    tools/spec_lint.py is not this agent's file.

KNOWN FINDINGS, REPORTED AND NOT FAILED
    Three real findings in the committed map, keyed by (rule, row name) and not
    by rule alone. Keying by rule would mean a NEW row with no `depends_on` was
    silently accepted as known, which is the same false comfort this gate exists
    to remove; tools/entry_field_gate.py keys by (kind, field) for the same
    reason. A pair absent from the table FAILS. `--strict` fails on the
    catalogued ones too, which is how the table gets drained rather than argued
    with.

      planned_without_depends_on   3 rows. schema.json's optional_notes for
                                   `depends_on` says a PLANNED row with none is
                                   "asserting it could start today".
      parity_without_measured_failure  2 rows. The same optional_notes for
                                   `measured_failure`: "A row claiming parity
                                   with no recorded failure of the thing being
                                   replaced is asserting an unexamined
                                   comparison."
      superseded_spec_cited        1 row. Cites
                                   ai_context/spec/program_components.json, which
                                   door_registry.json's `program-components` door
                                   declares superseded by the .2 variant.
      drift_history_thin           the recorded history holds 2 commits for this
                                   file, so the drift half has exactly ONE
                                   comparison. Reported as a standing
                                   limitation on every run, because a drift
                                   detector with one data point is not evidence
                                   that it works.

WHAT THE DRIFT HALF DOES NOT CLAIM, PRECISELY
    It is honest, and this list is the reason it can be:
      * A RENAME defeats the join. Rows are keyed by `name`, so a row whose name
        was edited reads as one row removed and one added. Both events are
        reported, and neither is called "unchanged".
      * A commit where the path is absent at that sha -- a rename, or a delete --
        is SKIPPED and named. It is never treated as "no drift".
      * MERGE COMMITS are compared against the previous commit in `git log
        --follow` order, which is NOT necessarily a parent. Every merge is
        therefore ALSO compared against each of its parents individually, and any
        divergence is reported as `parent_divergence`. What that still cannot
        see: a merge that resolved a conflict to a value matching its first
        parent while the second parent disagreed. `git log --follow` does not
        give the gate the tree of every path, so that case is undetectable here
        and is stated rather than papered over.
      * The history is read through `git log --follow`, so it stops at the first
        commit in which the file does not exist. Pre-rename history is out of
        reach.
      * Nothing is committed by this gate and no commit is created to test it.
        The self-test covers the static rules in memory and says plainly that it
        does not cover drift.

    It does not judge whether a status is the RIGHT status. Turning MCM's
    REJECTED into PLANNED may be correct; the gate's only claim is that it
    happened, and that it is visible with its sha.

    python tools/compat_gate.py
    python tools/compat_gate.py --json
    python tools/compat_gate.py --strict
    python tools/compat_gate.py --self-test
    python tools/compat_gate.py --file ai_context/spec/compat_f4se_map.json
    python tools/compat_gate.py --no-history

--self-test runs seven states in memory and writes nothing. Five are
RED-by-perturbation. The last two are about the limits of the static half and
they were written AFTER measuring it: flipping a REJECTED row to PLANNED does go
red, but on `planned_without_depends_on` -- a different field, for an unrelated
reason -- and supplying that field turns the same flip green again. The self-test
proves both halves of that, because a reader who believes four static rules stop
the named defect has been told something false.
"""
import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC_DIR = REPO / "ai_context" / "spec"
SCHEMA = SPEC_DIR / "schema.json"
DEFAULT_MAP = "ai_context/spec/legacy_replacement.json"

# The two rules that are more than a type check.
REFUSALS = ("NOT_PLANNED", "REJECTED")
PROOF_REQUIRED = ("COVERED",)

# ---------------------------------------------------------------------------
# KNOWN FINDINGS. Keyed by (rule, row name).
#
# The rule text beside each one is the rule being applied, quoted from
# ai_context/spec/schema.json so the judgement has a source and not just an
# opinion. `id` is a tracking id where one exists; "(none)" means this is a
# finding reported here for the first time and it has never been given a number.
# ---------------------------------------------------------------------------
ACKNOWLEDGED = {
    ("planned_without_depends_on", "Buffout 4 / Net Script Framework crash logging"): (
        "(none)",
        "schema.json optional_notes.depends_on: 'A row with status PLANNED and no "
        "depends_on is asserting it could start today.' The row does name a host "
        "(requires_host none), which is not a dependency. Whether GoE/PAP/Buffout "
        "can genuinely start today is a judgement this gate does not make."),
    ("planned_without_depends_on", "Archive2 .ba2 reading and validation"): (
        "(none)",
        "same rule. Reading .ba2 has no recorded blocker, so this one may be correct; "
        "it is catalogued because nothing says so."),
    ("planned_without_depends_on", "FO4 Papyrus and Creation Engine function index"): (
        "(none)",
        "same rule. program_components.2.json's `retrieval layer` entry says this row "
        "'does not exist yet' and is adjacent to the 7,932-file base .psc corpus, so "
        "the dependency is real and unwritten."),
    ("planned_without_depends_on", "CKPE / editor stability patches"): (
        "(none)",
        "same rule, and this one is the row the gate was RED on when it was first "
        "run -- it is catalogued because the gate found it, not because it was "
        "foreseen. The row's own notes say the dependency is unresolved in BOTH "
        "directions: the project wants CKPE gone AND treats its absence as a risk, "
        "and 'resolving that tension is what this row is for'. An empty depends_on "
        "on a row whose notes say it depends on replacing the thing it replaces is "
        "the clearest instance of the assertion schema.json warns about."),
    ("parity_without_measured_failure", "ModOrganizer 2"): (
        "(none)",
        "schema.json optional_notes.measured_failure: 'A row claiming parity with no "
        "recorded failure of the thing being replaced is asserting an unexamined "
        "comparison.' The row is DIFFERENT_MECHANISM, which the vocabulary defines as "
        "'we do the job differently; not a drop-in' -- a parity-shaped claim with "
        "measured_failure null."),
    ("parity_without_measured_failure", "FOMOD installers"): (
        "(none)",
        "same rule as ModOrganizer 2. NOT the same severity: the row's own notes say "
        "the job is deferred, so this may be an accurate thinness rather than a gap."),
    ("superseded_spec_cited", "F4SE loader and DLL injection"): (
        "(none)",
        "cites ai_context/spec/program_components.json. door_registry.json's "
        "`program-components` door declares that file SUPERSEDED by "
        "program_components.2.json and names the .2 file authoritative. The cited "
        "path exists, so this is not a dangling reference -- it points at the record "
        "of the state before the replacement map existed. Fixing it means editing a "
        "file this agent does not own, and the row itself is in the same category."),
    ("drift_history_thin", "*"): (
        "(none)",
        "git log --follow reports 2 commits touching the file, so the drift half has "
        "ONE comparison and has never seen a status change. 0 flips have occurred in "
        "the recorded history, which is consistent with a clean map and also "
        "consistent with a detector that has not been exercised. Draining this means "
        "the history has grown enough to be evidence."),
}


def git(args):
    """One git call in the repo. Returns (code, stdout, stderr)."""
    r = subprocess.run(["git", "-C", str(REPO)] + list(args), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=60)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


# --- static half -----------------------------------------------------------

def vocabulary():
    """The closed vocabulary, read from schema.json. (set, reason) on failure."""
    if not SCHEMA.exists():
        return None, "no schema at %s" % SCHEMA
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except ValueError as e:
        return None, "%s does not parse: %s" % (SCHEMA.name, e)
    cv = schema.get("compat_status_vocabulary") or {}
    allowed = {k for k in cv if not k.startswith("_")}
    if not allowed:
        return None, ("%s declares no compat_status_vocabulary, so every status "
                      "would be illegal and the check would be vacuous"
                      % SCHEMA.name)
    return allowed, None


def rule_texts():
    """The three declared rules, quoted. Printed so a reader can see the gate is
    implementing the contract rather than a paraphrase of it."""
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [r for r in (schema.get("compat_status_rules") or []) if isinstance(r, str)]


def superseded_paths():
    """Paths a pointer declares superseded, read from door_registry.json.

    Read, not hardcoded: the authoritative component spec is named in a door
    record, and hardcoding ".2" here would be a second place to forget to update
    when a .3 arrives."""
    p = REPO / "ai_context" / "systems_core" / "door_registry.json"
    if not p.exists():
        return set(), "no door registry at %s" % p
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        return set(), "%s does not parse: %s" % (p.name, e)
    out = set()
    for door in doc.get("doors") or []:
        if not isinstance(door, dict):
            continue
        sup = door.get("supersedes")
        targets = sup if isinstance(sup, list) else ([sup] if sup else [])
        for t in targets:
            if isinstance(t, str):
                out.add(t)
        nxt = door.get("superseded_by")
        if isinstance(nxt, str):
            out.add(str(door.get("path") or ""))
    return {t for t in out if t}, None


def check(doc, allowed, sup, root=REPO):
    """Findings over the committed map. Returns (problems, known, meta)."""
    problems, known = [], []
    rows = doc.get("entries")
    if not isinstance(rows, list) or not rows:
        return ([("no_rows", "entries", "no `entries` array, so there is nothing to "
                                 "check and agreement would be vacuous")],
                [], {"rows": 0})
    seen = {}
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or "?")

        def disposition(rule, subject, detail):
            hit = ACKNOWLEDGED.get((rule, name)) or ACKNOWLEDGED.get((rule, "*"))
            if hit:
                known.append((rule, subject,
                              "%s  [%s] %s" % (detail, hit[0], hit[1])))
            else:
                problems.append((rule, subject, detail))

        st = r.get("status")
        if st not in allowed:
            disposition("status_outside_vocabulary", "%s#%d" % (name, i),
                        "status %r is not one of %s. The vocabulary is closed; a "
                        "status nobody can branch on is decoration."
                        % (st, sorted(allowed)))
        if st in REFUSALS and not str(r.get("notes") or "").strip():
            disposition("refusal_without_reason", "%s#%d" % (name, i),
                        "status is %s and `notes` is empty. An unexplained refusal is "
                        "indistinguishable from an oversight." % st)
        if st in PROOF_REQUIRED and not r.get("spec"):
            disposition("covered_without_spec", "%s#%d" % (name, i),
                        "status is COVERED but no `spec` is cited, so nothing proves it")
        cited = r.get("spec")
        if cited and not (root / str(cited)).exists():
            disposition("dangling_spec", "%s#%d" % (name, i),
                        "cites %s, which is not on disk. Rule 3 is satisfied by a path "
                        "that names nothing." % cited)
        elif cited and str(cited) in sup:
            disposition("superseded_spec_cited", "%s#%d" % (name, i),
                        "cites %s, which a pointer declares superseded. The path exists, "
                        "so this is not dangling; it cites the record of the earlier "
                        "state rather than the authoritative one." % cited)
        if st == "PLANNED" and not r.get("depends_on"):
            disposition("planned_without_depends_on", "%s#%d" % (name, i),
                        "status is PLANNED and `depends_on` is empty, which asserts it "
                        "could start today")
        if st == "DIFFERENT_MECHANISM" and not r.get("measured_failure"):
            disposition("parity_without_measured_failure", "%s#%d" % (name, i),
                        "DIFFERENT_MECHANISM is a parity-shaped claim and "
                        "`measured_failure` is empty, so the comparison was never "
                        "examined")
        if name in seen:
            disposition("duplicate_row_name", "%s#%d" % (name, i),
                        "`name` already used by row #%d. Rows are keyed by name for "
                        "the drift join, so a duplicate makes a status flip "
                        "unattributable." % seen[name])
        else:
            seen[name] = i
    return problems, known, {"rows": len(rows)}


# --- drift half ------------------------------------------------------------

SEP = "\x1f"


def history(rel, depth=64):
    """Commits that touched `rel`, oldest first, following renames."""
    fmt = SEP.join(["%H", "%ad", "%P", "%s"])
    code, out, err = git(["log", "--follow", "--date=short", "--format=" + fmt,
                          "-n", str(depth), "--", rel])
    if code != 0:
        return None, ("git log --follow %s failed (%d): %s"
                      % (rel, code, (err.strip() or "no stderr")[:200]))
    commits = []
    for ln in out.splitlines():
        parts = ln.split(SEP)
        if len(parts) != 4 or not parts[0].strip():
            continue
        parents = [p for p in parts[2].split() if p]
        commits.append({"sha": parts[0], "date": parts[1], "subject": parts[3],
                        "parents": parents, "merge": len(parents) > 1})
    commits.reverse()
    return commits, None


def snapshot(sha, rel):
    """{row name: status} at that commit, or (None, reason)."""
    code, out, err = git(["show", "%s:%s" % (sha, rel)])
    if code != 0:
        tail = (err.strip().splitlines() or ["no stderr"])[-1]
        return None, "the path is absent at this commit (%s)" % tail[:140]
    try:
        doc = json.loads(out)
    except ValueError as e:
        return None, "the file at this commit does not parse: %s" % e
    rows = {}
    for r in doc.get("entries") or []:
        if isinstance(r, dict) and r.get("name"):
            rows[str(r["name"])] = r.get("status")
    return (rows, None) if rows else (None, "the file at this commit declares no rows")


def drift(rel, depth=64):
    """Status changes across history.

    Returns (events, limits, problems). `limits` is the honest coverage
    statement and is printed on every run; `problems` is only for the drift half
    being unable to run at all, which is a FAIL because SKIP is never PASS.
    """
    events, limits, problems = [], [], []
    commits, err = history(rel, depth)
    if commits is None:
        return events, limits, [("history_unreadable", rel, err)], 0
    if not commits:
        return events, limits, [("no_history", rel,
                                 "git log --follow returned no commit touching %s, so "
                                 "no drift can be detected. Refused rather than "
                                 "reported as clean." % rel)], 0

    snaps = []
    for c in commits:
        rows, serr = snapshot(c["sha"], rel)
        snaps.append((c, rows, serr))

    prev = None
    for c, rows, serr in snaps:
        if rows is None:
            limits.append("%s: %s -- this comparison was NOT made. A rename or a "
                          "delete can hide a status flip and this gate will not "
                          "pretend otherwise." % (c["sha"][:9], serr))
            continue
        if prev is not None:
            pc, prow = prev
            for name in sorted(rows):
                if name in prow and prow[name] != rows[name]:
                    events.append({"kind": "status_changed", "row": name,
                                   "from": prow[name], "to": rows[name],
                                   "sha": c["sha"], "date": c["date"],
                                   "subject": c["subject"], "against": pc["sha"]})
            for name in sorted(rows):
                if name not in prow:
                    events.append({"kind": "row_added", "row": name, "from": None,
                                   "to": rows[name], "sha": c["sha"], "date": c["date"],
                                   "subject": c["subject"], "against": pc["sha"]})
            for name in sorted(prow):
                if name not in rows:
                    events.append({"kind": "row_removed", "row": name, "from": prow[name],
                                   "to": None, "sha": c["sha"], "date": c["date"],
                                   "subject": c["subject"], "against": pc["sha"]})
        prev = (c, rows)

    # A merge is compared against the previous commit in log order, which is not
    # necessarily a parent. Compare each parent explicitly so a divergence cannot
    # hide behind that.
    for c, rows, _serr in snaps:
        if not c["merge"] or rows is None:
            continue
        for p in c["parents"]:
            prows, _perr = snapshot(p, rel)
            if prows is None:
                limits.append("%s: parent %s does not have the file, so this parent "
                              "could not be compared." % (c["sha"][:9], p[:9]))
                continue
            for name in sorted(set(prows) & set(rows)):
                if prows[name] != rows[name]:
                    events.append({"kind": "parent_divergence", "row": name,
                                   "from": rows[name], "to": prows[name],
                                   "sha": c["sha"], "date": c["date"],
                                   "subject": c["subject"], "against": p})

    comparisons = sum(1 for _c, rows, _e in snaps if rows is not None) - 1
    limits.append("history depth %d, usable snapshots %d, comparisons %d. "
                  "git log --follow stops at the first commit in which the path does "
                  "not exist; earlier history under another name is out of reach."
                  % (len(commits), sum(1 for _c, r, _e in snaps if r is not None),
                     max(comparisons, 0)))
    limits.append("merge limitation: a merge that resolved a conflict to its first "
                  "parent's value while a second parent disagreed is invisible here. "
                  "Every merge IS compared against each parent, so divergences that "
                  "survive are reported; that one case is undetectable from a path "
                  "log and is stated rather than papered over.")
    return events, limits, problems, len(commits)


# --- self-test -------------------------------------------------------------

def self_test():
    """Seven states, all in memory, writing nothing. The committed map must be
    GREEN, four perturbations must be RED, and the last two document exactly how
    far the static half reaches -- which is not as far as it first appeared."""
    rel = DEFAULT_MAP
    base = json.loads((REPO / rel).read_text(encoding="utf-8"))
    allowed, err = vocabulary()
    sup, _serr = superseded_paths()
    out, ok = [], True

    def record(label, doc, expect_fail, note):
        nonlocal ok
        problems, known, _meta = check(doc, allowed, sup)
        good = bool(problems) == expect_fail
        ok = ok and good
        out.append((label, len(problems), len(known), expect_fail, good, note))

    record("committed map", base, False,
           "ai_context/spec/legacy_replacement.json exactly as committed")

    d = copy.deepcopy(base)
    d["entries"][6]["status"] = "REJECTED_ISH"
    record("status outside the vocabulary", d, True,
           "a status nobody can branch on; the schema calls that decoration")

    d = copy.deepcopy(base)
    d["entries"][6]["notes"] = "   "
    record("REJECTED row's notes emptied", d, True,
           "MCM's measured refusal becomes an unexplained one, which schema.json "
           "says is indistinguishable from an oversight")

    d = copy.deepcopy(base)
    d["entries"][24]["spec"] = ""
    record("COVERED row's spec removed", d, True,
           "parity with nothing named is not a claim")

    d = copy.deepcopy(base)
    d["entries"][24]["spec"] = "ai_context/spec/no_such_proof.json"
    record("COVERED row cites a missing file", d, True,
           "rule 3 is satisfied by a path that names nothing; this is the extension")

    d = copy.deepcopy(base)
    d["entries"][6]["status"] = "PLANNED"          # notes kept: still legal
    record("REJECTED -> PLANNED, notes kept", d, True,
           "RED, BUT BY AN ADJACENT RULE. This state was expected to be GREEN and "
           "measured GREEN-in-theory / RED-in-fact: flipping MCM to PLANNED makes it "
           "a PLANNED row with no `depends_on`, so `planned_without_depends_on` fires. "
           "The refusal was caught -- by a rule about a different field, for a reason "
           "that has nothing to do with drift.")

    d = copy.deepcopy(base)
    d["entries"][6]["status"] = "PLANNED"
    d["entries"][6]["depends_on"] = ["probe"]      # defeat the adjacent rule
    record("...same flip, depends_on supplied", d, False,
           "GREEN, AND THIS IS THE POINT OF THE GATE. Both statuses are in the closed "
           "vocabulary, the note survives, and the one rule that caught the previous "
           "state is now satisfied by a value that says nothing about whether MCM may "
           "be built. MEASURED, not assumed: the previous state was RED with this same "
           "rule in force and the only difference is that field. So the static half "
           "does NOT stop the named defect; it stops this instance of it by accident, "
           "and one edit removes the accident. Only the drift half is aimed at it, and "
           "a reader who believes otherwise has been told something false.")

    width = max(len(r[0]) for r in out)
    print("compat_gate self-test -- writes nothing; every state is in memory")
    for label, np, nk, expect, good, note in out:
        print("  [%s] %-*s  problems=%-3d known=%-3d expected=%s"
              % ("PASS" if good else "FAIL", width, label, np, nk,
                 "RED" if expect else "GREEN"))
        print("         %s" % note)
    print("  %s: %d of %d states behaved as specified"
          % ("all" if ok else "NOT ALL", sum(1 for r in out if r[4]), len(out)))
    print("  NOT COVERED HERE: the drift half. Proving it needs a second commit that")
    print("  flips a status, and no gate may create commits to test itself.")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="fail on the catalogued findings too; this is how the table "
                         "gets drained rather than argued with")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the static half can go red, in memory, and prove "
                         "which defect it provably cannot catch")
    ap.add_argument("--file", default=DEFAULT_MAP,
                    help="the compat_mapping spec to check. Default %s, the PRODUCT "
                         "level replacement map. compat_f4se_map.json is the "
                         "CAPABILITY level file and works too." % DEFAULT_MAP)
    ap.add_argument("--no-history", action="store_true",
                    help="skip the drift half. It will be reported as SKIPPED, not as "
                         "clean, because SKIP is never PASS")
    ap.add_argument("--depth", type=int, default=64)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    rel = args.file.replace("\\", "/")
    path = REPO / rel
    if not path.exists():
        print("compat_gate: no map at %s" % path, file=sys.stderr)
        return 2
    allowed, verr = vocabulary()
    if verr:
        print("compat_gate: %s" % verr, file=sys.stderr)
        return 2
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        print("compat_gate: %s does not parse: %s" % (rel, e), file=sys.stderr)
        return 2
    sup, _ = superseded_paths()

    problems, known, meta = check(doc, allowed, sup)
    failed = list(problems)

    limits, events, commits_read = [], [], 0
    if args.no_history:
        limits.append("drift half SKIPPED by --no-history. Not run is not clean.")
    else:
        events, limits, dproblems, commits_read = drift(rel, args.depth)
        failed += dproblems

    if args.strict:
        failed += known

    drift_events = [e for e in events if e["kind"] == "status_changed"]

    if args.json:
        print(json.dumps({
            "schema": "pipmon.compat.gate/1",
            "status": "GREEN" if not failed else "RED",
            "map": rel,
            "rows": meta.get("rows"),
            "vocabulary": sorted(allowed),
            "declared_rules": rule_texts(),
            "drift": {"events": events, "status_changes": len(drift_events),
                      "commits_read": commits_read,
                      "limits": limits, "ran": not args.no_history},
            "known": [{"rule": r, "where": w, "detail": d} for r, w, d in known],
            "problems": [{"rule": r, "subject": s, "detail": d} for r, s, d in failed],
        }, indent=2))
        return 0 if not failed else 1

    print("compat_gate: %s" % rel)
    print("  %d rows, %d statuses in the closed vocabulary %s"
          % (meta.get("rows", 0), len(allowed), sorted(allowed)))
    for r in rule_texts():
        print("    declared: %s" % r)
    print()
    print("  static   : %d problems, %d known" % (len(problems), len(known)))
    if known:
        print("  KNOWN, catalogued in this file. Reported, not failed. --strict fails "
              "on these too.")
        for r, w, d in known:
            print("    [known] %-32s %s" % (r, w))
            print("            %s" % d)
    for r, s, d in problems:
        print("    [FAIL] %-32s %s" % (r, s))
        print("            %s" % d)
    print()
    if args.no_history:
        print("  drift    : SKIPPED (--no-history). SKIP is never PASS.")
    else:
        print("  drift    : %d commit(s) read, %d event(s), %d STATUS CHANGE(S)"
              % (commits_read, len(events), len(drift_events)))
        for e in events:
            if e["kind"] == "status_changed":
                print("    [CHANGED] %s" % e["row"])
                print("              %s -> %s in %s (%s)"
                      % (e["from"], e["to"], e["sha"][:9], e["date"]))
                print("              %s" % e["subject"])
            elif e["kind"] == "parent_divergence":
                print("    [DIVERGES] %s: %s vs %s in %s (%s)"
                      % (e["row"], e["from"], e["to"], e["sha"][:9], e["date"]))
            else:
                print("    [%s] %s -> %s in %s (%s)"
                      % (e["kind"].upper(), e["from"] or "-", e["to"] or "-",
                         e["sha"][:9], e["date"]))
        if not drift_events:
            print("  no status has changed between commits in the recorded history.")
            print("  That is consistent with a clean map AND with a drift detector")
            print("  that has never been exercised. The depth note below is the honest")
            print("  statement of which one it is.")
    for lim in limits:
        print("  limit    : %s" % lim)

    print("\ncompat_gate: %d problems, %d known, %d status change(s) in history"
          % (len(failed), len(known), len(drift_events)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())