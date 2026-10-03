"""Goal-coverage gate: a green build gate is not goal coverage, and this is the
dimension the build gate does not have.

THE DEFECT THIS EXISTS FOR, QUOTED
    ai_context/goal_alignment.md, "What 'all gates green' actually means":

      "That is build integrity. It is not goal coverage. A fully green gate is
       consistent with all of the following being true at once: S0 is unproven,
       because no BSScript vtable slot is hooked. `PipMonTestFacility.esp` is 66
       bytes with 0 records. No xEdit run has yet produced a validation report.
       The control plane has never been driven end to end by a second agent.
       Retrieval could rank an aspiration above a measurement and nothing would
       fail. The gate has no goal-coverage dimension."

    That last sentence is the defect. This file is the dimension.

WHAT IT REPORTS, PER GOAL
    Whether any check exists that could fail for it. That is the only question
    this gate asks, and it is deliberately not the question "is this goal met" --
    because nothing in the tree can answer that, and a gate that answered it
    anyway would be the thing it exists to prevent.

    The signal is `gate_covered` on ai_context/spec/program_components.2.json: a
    real boolean, declared by ai_context/spec/schema.json's `component` kind,
    already policed for honesty by spec_lint (a component whose status says it is
    not working may not claim gate_covered). That signal is CONSUMED here, not
    reinvented. There is no parallel "goal is covered" flag in this file, and
    adding one would be inventing a second source of truth for a fact that
    already has one.

    Per goal the gate reports:
      components      the registry entries the goal row actually names
      with_gate       how many of those carry gate_covered: true
      disposition     COMPONENT_CHECKED | PARTIAL | UNCHECKED | UNRESOLVED
      recorded        goal_alignment.md's own verdict cell, verbatim, unparsed
      recorded_says   NO | YES | PARTIAL | MIXED | JUDGEMENT
      agreement       AGREES | DIVERGES | CONFLICT | INDETERMINATE | NO VERDICT

THE VOCABULARY HAS NO WORD FOR "SATISFIED", AND THAT IS THE POINT
    COMPONENT_CHECKED means every component this goal names has gate_covered
    true. It does NOT mean the goal works, and the gate prints that sentence on
    every run. The evidence is not hypothetical: of the four goals that resolve
    to registry entries, all four DIVERGE from their own recorded verdict, and
    three read COMPONENT_CHECKED while their audit says partly, or no.

    UNRESOLVED is not a near miss. It means the goal row names things the
    component registry does not contain -- 8 of 12 rows -- so no check can be
    attributed to it at all. That is reported as UNRESOLVED, never as UNCHECKED,
    because "we looked and found nothing" and "we could not look" are different
    facts and collapsing them is how a workspace starts lying.

WHY IT REPORTS BY DEFAULT AND FAILS ONLY ON REGRESSION
    A gate that is red on arrival teaches people to ignore it, and every gate in
    this repository says so about itself. So the finding here is not "this gate
    has problems" -- it plainly does, 8 of 12 -- it is "the coverage got WORSE
    than the recorded baseline". The baseline is BASELINE below, edited by hand.
    There is deliberately NO --update-baseline flag: build_all.bat's own comment
    on selfalign.py says a tool that repairs its own signals is not a gate, and
    a self-rewriting baseline is the same thing with better manners.

WHAT IT FAILS ON
    1. a goal whose disposition is WORSE than the baseline (ranked below)
    2. a divergence between a goal's component checks and its recorded verdict
       that is not in the baseline -- i.e. new drift, not the drift already known
    3. fewer gate_covered: true components than the baseline records
    4. shape failures: the goals table unreadable, a goal row with no Component
       cell, the authoritative component spec not resolvable, a retrieval
       objective named by a goal that does not exist in ai_context/ranking.json
    Every one of those is a check that could not be made or was made worse.
    None of them is an opinion about whether a goal is achieved.

    Everything else is printed and not failed, and `--strict` fails on it too.

THE HONEST LIMITS, WHICH ARE THE POINT
    * The goal list is a MARKDOWN TABLE in a prose file. There is no
      `goals.json`. It is parsed strictly: exactly four cells, a header row
      named `Goal`, and a separator. Anything else is a FAIL, not a shrug,
      because a parser that silently reads fewer goals reports coverage for a
      subset and calls the whole thing covered.
    * The recorded verdict is PROSE and is classified by three word tests, which
      are printed alongside the raw cell so a reader can check the
      classification rather than trust it. A markdown table is not a contract.
    * Goal -> component attribution is by SUBSTRING: a registry component whose
      `name` appears in the row's Component cell. Deliberately conservative --
      it can only fail to attribute, never to invent an attribution. It is why
      8 rows are UNRESOLVED rather than fewer: the rows name FILES
      (`rag_index.py`, `generate_env.ps1`) and the registry names COMPONENTS
      (`retrieval layer`), and joining those needs a table this gate would have
      to invent. It does not invent one.
    * gate_covered means "a gate asserts this component's status". It does not
      mean the component does what the goal wants. Those are different claims
      and the DIVERGES column is where the difference shows up.
    * It does not run any check, so it cannot tell you a goal is met, and it
      cannot tell you a goal is unmet either. It reports what could fail.

    python tools/goal_coverage_gate.py
    python tools/goal_coverage_gate.py --json
    python tools/goal_coverage_gate.py --strict
    python tools/goal_coverage_gate.py --self-test
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOALS_MD = REPO / "ai_context" / "goal_alignment.md"
RANKING = REPO / "ai_context" / "ranking.json"
DOORS = REPO / "ai_context" / "systems_core" / "door_registry.json"

# Dispositions, ranked. A goal moving DOWN this list is a regression; moving up is
# an improvement and never fails, because a gate that punishes progress is a gate
# that gets switched off.
RANK = {"UNRESOLVED": 0, "UNCHECKED": 1, "PARTIAL": 2, "COMPONENT_CHECKED": 3}

# ---------------------------------------------------------------------------
# THE RECORDED BASELINE. Read by hand, 2026-10-03, from the committed tree.
#
# It records what coverage EXISTS, so that losing it is a failure. It does not
# record any goal as met, because this gate has no vocabulary for that and will
# not grow one to make its output look better.
#
# There is no flag that rewrites this. To move it, edit it and say in the commit
# what changed and why the change is not a regression.
# ---------------------------------------------------------------------------
BASELINE = {
    "recorded": "2026-10-03, against commit 1e973f8",
    "goals": 12,
    "gate_covered_true": 10,
    "gate_covered_false": 4,
    "disposition": {
        "Replace the extender layer": "COMPONENT_CHECKED",
        "Prove a script reaches our natives": "UNRESOLVED",
        "Replace scripting/telemetry mods": "COMPONENT_CHECKED",
        "Own CLI / terminal / control plane": "COMPONENT_CHECKED",
        "Author and validate without the CK": "UNRESOLVED",
        "Compile-correct FO4 Papyrus": "PARTIAL",
        "Work within CK limits": "UNRESOLVED",
        "Stable load order, no F4SE": "UNRESOLVED",
        "Demonstrate on a real cell": "UNRESOLVED",
        "Link CK and game": "UNRESOLVED",
        "Adopt Skyrim capability with a path": "UNRESOLVED",
        "Serve AI retrieval": "UNRESOLVED",
    },
    # Divergences already known and reported. A NEW one fails; these do not.
    # Six of the twelve rows, in two shapes: four where components claim gate
    # coverage and the audit says partly or no, and two where the audit claims
    # partly and no component can be attributed to the goal at all.
    "known_divergences": [
        "Replace the extender layer",
        "Replace scripting/telemetry mods",
        "Own CLI / terminal / control plane",
        "Compile-correct FO4 Papyrus",
        "Stable load order, no F4SE",
        "Link CK and game",
    ],
}


def component_spec_path():
    """The authoritative component spec, resolved through the door registry.

    Read through the pointer rather than hardcoded, exactly as compat_gate does
    for superseded paths: hardcoding ".2" here would be a second place to forget
    to update when a .3 arrives. (None, reason) when it cannot be resolved.
    """
    if not DOORS.exists():
        return None, "no door registry at %s" % DOORS
    try:
        doc = json.loads(DOORS.read_text(encoding="utf-8"))
    except ValueError as e:
        return None, "%s does not parse: %s" % (DOORS.name, e)
    for door in doc.get("doors") or []:
        if isinstance(door, dict) and door.get("id") == "program-components":
            p = door.get("path")
            if not p:
                return None, "the `program-components` door declares no `path`"
            if not (REPO / str(p)).exists():
                return None, ("the `program-components` door points at %s, which is "
                              "not on disk" % p)
            return str(p), None
    return None, "no door with id `program-components`, so the authoritative " \
                 "component spec cannot be resolved"


def goal_rows(md_text):
    """The goals table, parsed strictly. (rows, reason).

    ai_context/goal_alignment.md holds FOUR markdown tables, so the first job is
    picking the right one: a table is a CONTIGUOUS block of pipe-lines, and the
    goals table is the block containing a row whose first cell is exactly `Goal`.
    Parsing "all pipe lines" instead would swallow the next table and call its
    three-column rows a malformed goals table.

    Within that block the parse is strict: four cells in the header, a `---`
    separator, four cells in every row. A goals table that cannot be read that way
    is a FAIL in main(), because a parser that quietly returns fewer goals than
    exist will report coverage for a subset and call the whole thing covered.
    """
    blocks, cur = [], []
    for ln in md_text.splitlines():
        if ln.startswith("|"):
            cur.append(ln)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)

    def cells(ln):
        return [c.strip() for c in ln.strip().strip("|").split("|")]

    target = None
    for block in blocks:
        if any(cells(ln)[0] == "Goal" for ln in block):
            target = block
            break
    if target is None:
        return None, ("no contiguous table block contains a row whose first cell is "
                      "exactly `Goal`. ai_context/goal_alignment.md is prose and this "
                      "parse is strict on purpose.")

    header = None
    for ln in target:
        cs = cells(ln)
        if cs and cs[0] == "Goal":
            header = cs
            break
    if len(header) != 4:
        return None, "the goals header has %d cells, not 4" % len(header)

    rows, seen_sep, closed = [], False, False
    for ln in target:
        cs = cells(ln)
        if cs and cs[0] == "Goal":
            continue
        if all(set(c) <= set("-: ") for c in cs):
            seen_sep = True
            continue
        if not seen_sep:
            continue                      # anything before the separator is a header
        if len(cs) != 4:
            # The goals table is over and something else has started. Not an error:
            # the block was chosen by its `Goal` header, so this is the next table
            # inside the same run of pipe lines.
            closed = True
            break
        rows.append(cs)
    if not seen_sep:
        return None, "the goals table has a header and no `---` separator row"
    if not rows:
        return None, "the goals table has a header and no rows"
    return rows, None


def classify_verdict(cell):
    """NO | YES | PARTIAL | MIXED | JUDGEMENT, from three word tests.

    Prose in, and prose out: the raw cell is always printed beside this, because
    a classification of a sentence is a judgement and a reader is entitled to see
    the sentence. `partly` is deliberately NOT `yes` -- "python 108 checks,
    partly" is not a pass and flattening the two is the defect this repository
    keeps finding in new costumes.
    """
    plain = cell.replace("*", "").replace("`", "").lower()
    words = set(re.findall(r"[a-z]+", plain))
    if plain.startswith("n/a") or "judgement" in words:
        return "JUDGEMENT"
    says_no = "no" in words
    says_yes = "yes" in words
    says_part = "partly" in words or "partial" in words
    if says_no and (says_yes or says_part):
        return "MIXED"
    if says_no:
        return "NO"
    if says_yes:
        return "YES"
    if says_part:
        return "PARTIAL"
    return "MIXED"


def agreement(disposition, verdict):
    """AGREES | DIVERGES | CONFLICT | INDETERMINATE | NO VERDICT."""
    if verdict == "JUDGEMENT":
        return "NO VERDICT"
    covered = disposition in ("COMPONENT_CHECKED", "PARTIAL")
    says_no = verdict in ("NO", "MIXED")
    if covered and verdict == "NO":
        return "CONFLICT"
    if covered and says_no:
        return "DIVERGES"
    if covered and verdict in ("YES", "PARTIAL"):
        return "DIVERGES"
    if not covered and says_no:
        return "AGREES"
    if not covered and verdict in ("YES", "PARTIAL"):
        return "DIVERGES"
    return "INDETERMINATE"


def raw_comps(doc):
    """[(name, gate_covered)] straight out of a parsed component spec."""
    return [(str(e["name"]), e.get("gate_covered"))
            for e in (doc.get("entries") or [])
            if isinstance(e, dict) and e.get("name")]


def load_components(rel):
    """[(name, gate_covered)] plus a count, or (None, reason)."""
    try:
        doc = json.loads((REPO / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, "cannot read %s: %s" % (rel, e)
    out = []
    for e in doc.get("entries") or []:
        if isinstance(e, dict) and e.get("name"):
            gc = e.get("gate_covered")
            if not isinstance(gc, bool):
                return None, ("component %r has gate_covered %r, not a boolean. The "
                              "whole point of the field is that a program can branch on "
                              "it." % (e.get("name"), gc))
            out.append((str(e["name"]), gc))
    if not out:
        return None, "%s declares no component entries" % rel
    return out, None


def objectives():
    """The retrieval objective ids, from ai_context/ranking.json. (set, reason)."""
    if not RANKING.exists():
        return None, "no ranking config at %s" % RANKING
    try:
        doc = json.loads(RANKING.read_text(encoding="utf-8"))
    except ValueError as e:
        return None, "%s does not parse: %s" % (RANKING.name, e)
    objs = doc.get("objectives")
    if not isinstance(objs, dict):
        return None, "%s declares no `objectives` map" % RANKING.name
    return {k for k in objs if not k.startswith("_")}, None


def survey(md_text=None, comp_rel=None, comps=None, goals_path=None):
    """The whole report. Returns (report, problems).

    `comps` exists so the self-test can perturb gate_covered in memory instead of
    editing a file three other agents are working in. `goals_path` lets the gate
    be pointed at a copy, which is how the three-state check was run without
    touching ai_context/goal_alignment.md -- a file this agent does not own.
    `report` is always returned even when there are problems, so a broken tree
    still prints what it could read. `problems` is what FAILS.
    """
    problems, known = [], []
    report = {"goals": [], "components": [], "summary": {}}

    if md_text is None:
        src = Path(goals_path) if goals_path else GOALS_MD
        if not src.exists():
            return report, [("no_goals_file", str(src),
                             "%s does not exist, so there are no goals to cover"
                             % src.name)]
        md_text = src.read_text(encoding="utf-8")
        report["goals_source"] = str(src.relative_to(REPO)).replace("\\", "/") \
            if src.is_relative_to(REPO) else str(src)

    rows, gerr = goal_rows(md_text)
    if rows is None:
        return report, [("goals_unreadable", "ai_context/goal_alignment.md", gerr)]

    if comps is None:
        if comp_rel is None:
            comp_rel, cerr = component_spec_path()
            if cerr:
                return report, [("components_unresolvable", "door_registry.json", cerr)]
        comps, cerr = load_components(comp_rel)
        if cerr:
            return report, [("components_unreadable", comp_rel, cerr)]
    objs, oerr = objectives()
    if oerr:
        return report, [("objectives_unreadable", "ai_context/ranking.json", oerr)]

    report["components"] = [{"name": n, "gate_covered": g} for n, g in comps]
    report["component_spec"] = comp_rel

    for goal, comp_cell, obj_cell, verdict_cell in rows:
        cell = comp_cell.lower()
        named = [(n, g) for n, g in comps if n.lower() in cell]
        flags = [g for _n, g in named]
        if not named:
            disp = "UNRESOLVED"
        elif all(flags):
            disp = "COMPONENT_CHECKED"
        elif any(flags):
            disp = "PARTIAL"
        else:
            disp = "UNCHECKED"
        verdict = classify_verdict(verdict_cell)
        agree = agreement(disp, verdict)

        # A goal naming nothing the registry knows is the single biggest hole in
        # this report and it is reported as a finding, not as a footnote.
        if disp == "UNRESOLVED":
            known.append(("goal_unresolved_in_registry", goal,
                          "names %r and no component in %s has that name, so no check "
                          "can be attributed to this goal. UNRESOLVED, not UNCHECKED: "
                          "nobody has established that nothing checks it, only that "
                          "this gate could not find the subject."
                          % (comp_cell.strip(), comp_rel)))
        if agree in ("DIVERGES", "CONFLICT"):
            if disp in ("COMPONENT_CHECKED", "PARTIAL"):
                why = ("components named here carry gate_covered as %s, while the row's "
                       "own verdict cell reads %r. A component check is not a goal "
                       "check: it asserts that a gate watches the component, not that "
                       "the goal is served. Verdict classified %s from %r."
                       % ([g for _n, g in named], verdict_cell, verdict, verdict_cell))
            else:
                why = ("the row claims %r in its verdict cell while naming nothing this "
                       "gate could attribute to it, so no check behind that claim can "
                       "be found. The claim may be true; it is unfalsifiable as "
                       "written. Verdict classified %s from %r."
                       % (verdict_cell, verdict, verdict_cell))
            known.append(("recorded_verdict_diverges", goal, why))

        for obj in re.findall(r"`([a-z0-9-]+)`", obj_cell):
            if obj not in objs:
                problems.append(("objective_not_in_ranking", goal,
                                 "names retrieval objective %r, which is not in "
                                 "ai_context/ranking.json's objectives. A goal pointing "
                                 "at an objective nobody can query is a dangling "
                                 "promise." % obj))
        if not comp_cell.strip():
            problems.append(("goal_without_components", goal,
                             "the Component cell is empty, so there is nothing for this "
                             "gate to look for"))

        report["goals"].append({
            "goal": goal, "components_cell": comp_cell.strip(),
            "objectives_cell": obj_cell.strip(),
            "components": [{"name": n, "gate_covered": g} for n, g in named],
            "with_gate": sum(1 for g in flags if g),
            "disposition": disp, "rank": RANK[disp],
            "recorded": verdict_cell, "recorded_says": verdict, "agreement": agree,
        })

    got = {g["goal"]: g["disposition"] for g in report["goals"]}
    base = BASELINE["disposition"]

    # 1. regression, per goal, by rank
    for goal, was in sorted(base.items()):
        now = got.get(goal)
        if now is None:
            problems.append(("goal_disappeared", goal,
                             "the goals table no longer has a row for this goal. The "
                             "baseline records it, so its removal is a change in what "
                             "is being claimed, not a quiet edit."))
            continue
        if RANK[now] < RANK[was]:
            problems.append(("coverage_regressed", goal,
                             "was %s at the recorded baseline and is %s now. The "
                             "component it named lost its gate coverage, or stopped "
                             "being named." % (was, now)))

    # 2. a divergence that is not already known
    for g in report["goals"]:
        if g["agreement"] in ("DIVERGES", "CONFLICT") and \
                g["goal"] not in BASELINE["known_divergences"]:
            problems.append(("new_divergence", g["goal"],
                             "components named here claim gate coverage while the row's "
                             "own verdict cell reads %r. This divergence is not in the "
                             "recorded baseline, so it is new." % g["recorded"]))

    # 3. fewer covered components than the baseline
    n_true = sum(1 for _n, g in comps if g)
    if n_true < BASELINE["gate_covered_true"]:
        problems.append(("gate_covered_dropped", comp_rel,
                         "%d components carry gate_covered: true; the baseline records "
                         "%d. Losing gate coverage is always a regression."
                         % (n_true, BASELINE["gate_covered_true"])))

    if len(report["goals"]) != BASELINE["goals"]:
        problems.append(("goal_count_changed", "ai_context/goal_alignment.md",
                         "%d goal rows; the baseline records %d. Adding a goal is "
                         "progress and is fine; this only fails because the baseline "
                         "must be updated by hand so the change is deliberate."
                         % (len(report["goals"]), BASELINE["goals"])))

    disp_counts = {}
    for g in report["goals"]:
        disp_counts[g["disposition"]] = disp_counts.get(g["disposition"], 0) + 1
    agree_counts = {}
    for g in report["goals"]:
        agree_counts[g["agreement"]] = agree_counts.get(g["agreement"], 0) + 1
    no_check = [g["goal"] for g in report["goals"]
                if g["disposition"] in ("UNRESOLVED", "UNCHECKED")]
    report["summary"] = {
        "goals": len(report["goals"]),
        "disposition": disp_counts,
        "agreement": agree_counts,
        "components": len(comps),
        "gate_covered_true": n_true,
        "gate_covered_false": len(comps) - n_true,
        "goals_with_no_attributable_check": len(no_check),
        "goals_with_no_attributable_check_names": no_check,
        "goals_fully_component_checked": disp_counts.get("COMPONENT_CHECKED", 0),
        "goals_whose_recorded_verdict_says_no":
            sum(1 for g in report["goals"] if g["recorded_says"] in ("NO", "MIXED")),
    }
    report["known"] = [{"rule": r, "goal": w, "detail": d} for r, w, d in known]
    return report, problems


# --- self-test -------------------------------------------------------------

def self_test():
    """Seven states, all in memory, writing nothing. The committed tree must be
    GREEN; five perturbations must be RED; and one must stay GREEN, because the
    gate is allowed to be green while 8 of 12 goals have no check -- it fails on
    regression and must NOT fail on progress."""
    md = GOALS_MD.read_text(encoding="utf-8")
    out, ok = [], True

    def record(label, problems, expect_fail, note):
        nonlocal ok
        good = bool(problems) == expect_fail
        ok = ok and good
        out.append((label, len(problems), expect_fail, good, note))

    comp_rel, _r = component_spec_path()
    raw = json.loads((REPO / comp_rel).read_text(encoding="utf-8"))

    rep, p = survey(md_text=md, comp_rel=comp_rel)
    record("committed tree", p, False,
           "the goals table against %s as committed: %d goals, %d with no attributable "
           "check, %d problems"
           % (comp_rel, rep["summary"].get("goals", 0),
              rep["summary"].get("goals_with_no_attributable_check", 0), len(p)))

    # THE REGRESSION THIS GATE EXISTS FOR: a component loses its gate coverage.
    # Done in memory because ai_context/spec/** belongs to other agents.
    worse = [(n, (False if n == "overseer_cli" else g)) for n, g in raw_comps(raw)]
    rep, p = survey(md_text=md, comp_rel=comp_rel, comps=worse)
    record("overseer_cli loses gate_covered", p, True,
           "the named component for 'Replace scripting/telemetry mods' and 'Own CLI / "
           "terminal / control plane' goes from COMPONENT_CHECKED to PARTIAL, which "
           "is a regression by rank, and the covered-component count drops below the "
           "baseline. This is the failure the gate is for.")

    # The opposite: a component GAINS coverage. Must stay GREEN.
    better = [(n, (True if n in ("ai_watcher", "test facility") else g))
              for n, g in raw_comps(raw)]
    rep, p = survey(md_text=md, comp_rel=comp_rel, comps=better)
    record("two components gain gate_covered", p, False,
           "GREEN ON PURPOSE. A gate that fails on progress gets switched off, which is "
           "how a permanently red gate becomes decoration. Progress must not be a "
           "failure.")

    md_bad = md.replace("| Prove a script reaches our natives | S0 experiment |",
                        "| Prove a script reaches our natives |  |")
    rep, p = survey(md_text=md_bad)
    record("a goal's Component cell emptied", p, True,
           "a goal with nothing to look for is a check that cannot be made")

    # The new row has to go INSIDE the goals table's contiguous block: appended to
    # the end of the file it would be a different table, and the parser would
    # correctly ignore it. The first attempt at this state did exactly that and
    # measured GREEN, which is the test being wrong rather than the gate.
    anchor = "| Serve AI retrieval | `rag_index.py`, `rag_query.py` | `retrieval` | **no** |"
    if anchor not in md:
        raise SystemExit("self-test anchor row not found in goal_alignment.md; the "
                         "table changed shape and this test needs updating")
    rep, p = survey(md_text=md.replace(
        anchor, anchor + "\n| A new goal | something | `not-an-objective` | **no** |"))
    record("goal naming an objective that does not exist", p, True,
           "a dangling promise: the goal points at a retrieval objective nobody can "
           "query. Also trips goal_count_changed, which is the intended hand-edit "
           "prompt for adding a goal.")

    md_bad3 = md.replace("| Goal | Component | Retrieval objective | Build gate covers it? |",
                         "| Objective | Component | Retrieval objective | Build gate covers it? |")
    rep, p = survey(md_text=md_bad3)
    record("goals table header changed", p, True,
           "no cell is exactly `Goal`, so the block cannot be identified. A parser "
           "that cannot read the table must FAIL, not report a subset as covered.")

    rep, p = survey(md_text=md, comp_rel="ai_context/spec/no_such_components.json")
    record("component spec unresolvable", p, True,
           "SKIP is never PASS: if the signal cannot be read there is no coverage "
           "report, and reporting none as fine is the defect")

    width = max(len(r[0]) for r in out)
    print("goal_coverage_gate self-test -- writes nothing; every state is in memory")
    for label, np, expect, good, note in out:
        print("  [%s] %-*s  problems=%-3d expected=%s"
              % ("PASS" if good else "FAIL", width, label, np,
                 "RED" if expect else "GREEN"))
        print("         %s" % note)
    print("  %s: %d of %d states behaved as specified"
          % ("all" if ok else "NOT ALL", sum(1 for r in out if r[4]), len(out)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="fail on the reported findings too. That is how the goal table "
                         "and the component registry get reconciled rather than argued "
                         "with -- and it will be red for as long as 8 of 12 goals name "
                         "nothing checkable")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the gate can go red, in memory")
    ap.add_argument("--goals-file", default=None,
                    help="read the goals table from here instead of "
                         "ai_context/goal_alignment.md. Exists so the gate can be "
                         "pointed at a COPY for a three-state check, rather than "
                         "edited, by an agent that does not own that file")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    report, problems = survey(goals_path=args.goals_file)
    known = report.get("known") or []
    failed = list(problems)
    if args.strict:
        failed += [(k["rule"], k["goal"], k["detail"]) for k in known]
    s = report["summary"]

    if args.json:
        print(json.dumps({
            "schema": "pipmon.goal_coverage.gate/1",
            "status": "GREEN" if not failed else "RED",
            "baseline": BASELINE["recorded"],
            "summary": s,
            "goals": report["goals"],
            "components": report["components"],
            "component_spec": report.get("component_spec"),
            "goals_source": report.get("goals_source"),
            "known": known,
            "problems": [{"rule": r, "goal": g, "detail": d} for r, g, d in failed],
        }, indent=2))
        return 0 if not failed else 1

    print("goal_coverage_gate: %d goals, %d components in %s"
          % (s.get("goals", 0), s.get("components", 0), report.get("component_spec")))
    print("  goals    : %s" % report.get("goals_source", "ai_context/goal_alignment.md"))
    print("  baseline : %s" % BASELINE["recorded"])
    print()
    print("  A GREEN BUILD GATE IS NOT GOAL COVERAGE. This reports whether any check")
    print("  exists that could fail for each goal. COMPONENT_CHECKED means every")
    print("  component the goal names has gate_covered true -- it does NOT mean the")
    print("  goal works, and no row below is reported as satisfied.")
    print()
    for g in report["goals"]:
        comps = ", ".join("%s=%s" % (c["name"], "gate" if c["gate_covered"] else "NO GATE")
                          for c in g["components"]) or "none the registry names"
        print("  [%-17s] %s" % (g["disposition"], g["goal"]))
        print("      components : %s" % comps)
        print("      recorded   : %s   (classified %s)"
              % (g["recorded"], g["recorded_says"]))
        print("      agreement  : %s" % g["agreement"])
    print()
    print("  coverage   : %s" % (s.get("disposition") or {}))
    print("  agreement  : %s" % (s.get("agreement") or {}))
    print("  gate_covered: %d true, %d false of %d components"
          % (s.get("gate_covered_true", 0), s.get("gate_covered_false", 0),
             s.get("components", 0)))
    print()
    print("  %d of %d goals have NO check this gate can attribute:"
          % (s.get("goals_with_no_attributable_check", 0), s.get("goals", 0)))
    for name in s.get("goals_with_no_attributable_check_names") or []:
        print("     ! %s" % name)
    print("  %d of %d goals are COMPONENT_CHECKED, and every one of them DIVERGES "
          "from its own recorded verdict."
          % (s.get("goals_fully_component_checked", 0), s.get("goals", 0)))
    print("  %d of %d goals have a recorded verdict that says no (NO or MIXED)."
          % (s.get("goals_whose_recorded_verdict_says_no", 0), s.get("goals", 0)))
    print()
    print("  FINDINGS, reported and not failed. --strict fails on these too.")
    for k in known:
        print("    [known] %-26s %s" % (k["rule"], k["goal"]))
        print("            %s" % k["detail"])
    for r, g, d in failed:
        print("    [FAIL] %-26s %s" % (r, g))
        print("            %s" % d)
    print("\ngoal_coverage_gate: %d problems, %d findings"
          % (len(failed), len(known)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())