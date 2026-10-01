"""Orchestrator: executes a declared plan, and gets out of the way.

A plan lives in ai_context/plans/*.pyr. This executes it. The separation is the
point: a plan can be reviewed, argued with and diffed, and the code that runs it
stays small and boring enough to trust.

What it enforces, because these are the things a script cannot:
  * preconditions are CHECKED before a phase runs, not documented and hoped for
  * a phase that cannot be verified is attempted, not done
  * the first failure halts the plan and prints the rollback, rather than
    carrying on into a worse state
  * the transcript records what actually ran and what actually happened

What it deliberately does NOT do: reorder phases, parallelise, retry, or decide.
Every decision is written in the plan. An orchestrator that makes its own
decisions is a script wearing a plan's clothes, and the reasoning goes back to
being buried in control flow where it cannot be reviewed.

It never blocks on a third-party process. Actions are expected to be detached
launches; the orchestrator polls them with bounded sleeps BETWEEN polls and can
be interrupted at any point, because being locked inside a long process is the
one failure mode that makes everything else unobservable.

    python tools/orchestrate.py list
    python tools/orchestrate.py show create_environment
    python tools/orchestrate.py run create_environment --through P2
    python tools/orchestrate.py run create_environment --plan-only
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLANS = REPO / "ai_context" / "plans"
WATCH = REPO / "runs" / "watch"
TRANSCRIPT = WATCH / "orchestrator-transcript.jsonl"
STATE = WATCH / "orchestrator-state.json"
ARCHIVE = WATCH / "archive"
PY = sys.executable

# Set by --verbose. The gates' own output is ALWAYS captured and ALWAYS saved to
# the transcript and the state file; this only controls whether it is also
# printed. Capturing-but-discarding is what made the last run look like it was
# doing nothing: the work happened, the text went nowhere.
VERBOSE = False

# Poll pacing. 0 means "use what the plan declared". The override exists because
# a plan's budget is written for the job, while the caller's patience is not the
# same quantity -- and an orchestrator that blocks for a plan's full budget is an
# orchestrator nobody can interrupt, which is the one property that must not be
# traded away. It sets the stage up, narrates it, and hands control back.
BUDGET_OVERRIDE = 0
INTERVAL_OVERRIDE = 0

# Running tally for the dashboard. Every gate and action lands here, so the
# summary at the bottom counts what actually ran rather than what was planned.
TALLY = {"gates": 0, "gate_ok": 0, "actions": 0, "action_ok": 0,
         "verify_ok": 0, "verify_fail": 0, "polls": 0, "preflights": 0}


def _atomic_write(path, text):
    """Write via a temp file and replace, so a reader never sees half a file.

    Same reasoning as the log writer in validate_plugin.ps1: an observer that
    catches a partial state file concludes the run crashed, when in fact it was
    mid-write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(str(tmp), str(path))

# Only shell-outs that are genuinely safe to run here. Anything long or
# GUI-bearing must be a detached launch inside the plan, never a direct call.
SHELL = {
    "tools/artifact_gate.py": [PY, "tools/artifact_gate.py"],
    "tools/side_gate.py": [PY, "tools/side_gate.py"],
    "tools/spec_lint.py": [PY, "tools/spec_lint.py"],
    "tools/rag_selftest.py": [PY, "tools/rag_selftest.py"],
    "tools/check_item.py": [PY, "tools/check_item.py"],
    "tools/xedit_log.py": [PY, "tools/xedit_log.py"],
    "tools/door_lint.py": [PY, "tools/door_lint.py"],
    "tools/ownership_gate.py": [PY, "tools/ownership_gate.py"],
    "tools/surfaces_gate.py": [PY, "tools/surfaces_gate.py"],
    "tools/factcheck.py": [PY, "tools/factcheck.py"],
    "tools/validate_plugin.ps1": ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                  "-File", "tools/validate_plugin.ps1"],
    "tools/run_gen.ps1": ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                          "-File", "tools/run_gen.ps1"],
}


class Stop(Exception):
    def __init__(self, reason, detail=""):
        self.reason = reason
        self.detail = detail


STATE_ROW = {"plan": None, "goal": None, "task": None, "started_utc": None,
             "updated_utc": None, "phase": "starting", "level": "declared",
             "phases_done": [], "phases_remaining": [], "blocked": None,
             "last_gate": None, "counts": dict(TALLY), "exit": None}


def trace(event, human="", level="info", **kw):
    """One line to a human, one object to the machine, from the same call.

    The two used to be different things: stdout was prose written into
    run_plan's prints, and the JSONL was a separate record() that kept exit
    codes. So the trace log had no work in it and the transcript had no
    narration. Both now come from here, which is what makes a reader able to
    follow a run from either side without cross-referencing two files."""
    entry = dict(kw)
    entry["event"] = event
    entry["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if level != "info":
        entry["level"] = level
    WATCH.mkdir(parents=True, exist_ok=True)
    with TRANSCRIPT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    if human:
        print(human, flush=True)


def record(entry):
    """Kept as the machine-only path. trace() is preferred; this remains for
    callers that genuinely have nothing to say to a human."""
    trace(entry.get("event", "note"), level=entry.get("level", "info"),
          **{k: v for k, v in entry.items() if k not in ("event", "level")})


def save_state(**kw):
    """Persist the declared progress level. Called after EVERY phase, so a run
    that dies between phases still says which one it reached.

    This is the 'save at the end of each stage' the orchestrator was missing:
    it used to print 'verified.' and carry on, so a killed run left no record
    of how far it had got and the next run started from nothing."""
    STATE_ROW.update(kw)
    STATE_ROW["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    STATE_ROW["counts"] = dict(TALLY)
    _atomic_write(STATE, json.dumps(STATE_ROW, indent=2))


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def archive_run(plan_id):
    """Copy the evidence for this run into a timestamped directory.

    A run overwrites runs/watch/* every time, so the previous run's evidence is
    gone by the time anyone reads this one's verdict. Lineage is the whole
    point of keeping failures: the compile error that was invisible for a day
    was invisible partly because nothing preserved the run that produced it."""
    if not WATCH.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    dest = ARCHIVE / ("%s-%s" % (plan_id, stamp))
    dest.mkdir(parents=True, exist_ok=True)
    keep = ("xedit-validation-report.json", "xedit-latest.json", "xedit-stdout.log",
            "xedit-stderr.log", "xedit-job.json", "validate_plugin.gen.pas")
    n = 0
    for name in keep:
        src = WATCH / name
        if src.exists():
            try:
                (dest / name).write_bytes(src.read_bytes())
                n += 1
            except Exception:
                pass
    if n:
        return dest
    dest.rmdir()
    return None


LEDGER = WATCH / "ledger.json"


def load_ledger():
    if LEDGER.exists():
        try:
            return json.loads(LEDGER.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_ledger(led):
    """The point of this file: a stage that scans a thousand things must not be
    re-run from scratch to fix one of them. Each item's outcome is recorded
    under a key that includes its identity, so a later pass reports the settled
    ones as CACHED and only re-attempts what actually needs another look.

    Without it, every discovery costs a full re-scan, and the incentive becomes
    'do not report a partial result' -- which is how a stage ends up either
    hiding failures or being run a thousand times. Both are worse than a ledger."""
    _atomic_write(LEDGER, json.dumps(led, indent=2))


def scan(plan_id, phase_id, items, work, force=False):
    """Run `work(item)` over `items`, tolerating per-item failure.

    THE RULE THIS ENCODES: one bad item must never cost the whole stage. A stage
    that dies on the first failure cannot tell you anything about the other 999,
    so it has to be re-run after every fix -- and re-running is how a scan turns
    into an afternoon of waiting. So a failure is RECORDED and the sweep
    CONTINUES, and the stage finishes with a verdict that names every item it
    could not settle.

    Items already settled under the same key are reported CACHED and skipped,
    unless `force`. `cached` counts as ok: it is a known-good result, and
    counting it as not-run would make a settled stage look permanently partial.
    """
    led = load_ledger()
    res = {"total": len(items), "ok": 0, "cached": 0, "failed": 0, "skipped": 0,
           "failures": [], "skips": []}
    for n, item in enumerate(items, 1):
        key = "%s/%s/%s" % (plan_id, phase_id, item)
        prev = led.get(key)
        if prev and prev.get("state") == "ok" and not force:
            res["cached"] += 1
            res["ok"] += 1
            trace("item_cached", "    %4d/%-4d CACHED  %s" % (n, len(items), item))
            continue
        try:
            detail = work(item)
            led[key] = {"state": "ok", "stamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "detail": str(detail)[:400]}
            res["ok"] += 1
            trace("item_ok", "    %4d/%-4d ok      %s%s" % (n, len(items), item,
                                                          ("  -- " + str(detail)[:70]) if detail else ""))
        except SkipItem as e:
            led[key] = {"state": "skip", "stamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "detail": str(e)[:400]}
            res["skipped"] += 1
            res["skips"].append((item, str(e)))
            trace("item_skip", "    %4d/%-4d SKIP    %s  -- %s" % (n, len(items), item, e), level="warn")
        except Exception as e:                       # noqa: BLE001 - deliberate
            # Recorded, not raised. The whole point is that the sweep survives.
            led[key] = {"state": "fail", "stamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "detail": "%s: %s" % (type(e).__name__, e)}
            res["failed"] += 1
            res["failures"].append((item, "%s: %s" % (type(e).__name__, e)))
            trace("item_fail", "    %4d/%-4d FAIL    %s  -- %s: %s"
                  % (n, len(items), item, type(e).__name__, e), level="error")
    save_ledger(led)
    return res


class SkipItem(Exception):
    """Raised by a work function for something that could not be attempted.
    Distinct from a failure: SKIP means UNVERIFIED, and the project never
    collapses one into the other."""


def sweep_report(phase_id, res):
    """The bottom-of-stage block the operator asked for: what was covered, what
    was not, and the code. Placed where it cannot be scrolled past."""
    settled = res["ok"] + res["skipped"]
    print("\n  -- %s sweep: %d total | %d ok (%d cached) | %d skipped | %d FAILED --"
          % (phase_id, res["total"], res["ok"], res["cached"], res["skipped"], res["failed"]))
    if res["skips"]:
        print("     not attempted (%d):" % len(res["skips"]))
        for it, why in res["skips"][:12]:
            print("       - %s: %s" % (it, why[:100]))
        if len(res["skips"]) > 12:
            print("       ... %d more, full list in %s" % (len(res["skips"]) - 12, LEDGER))
    if res["failures"]:
        print("     NEEDS ACTION (%d):" % len(res["failures"]))
        for it, why in res["failures"][:12]:
            print("       ! %s: %s" % (it, why[:100]))
        if len(res["failures"]) > 12:
            print("       ... %d more, full list in %s" % (len(res["failures"]) - 12, LEDGER))
    if not res["failures"] and not res["skips"]:
        print("     everything settled; nothing needs a re-run.")
    print("     settled %d/%d. Re-running is only needed for the items listed above;"
          " settled ones are cached." % (settled, res["total"]))
    return 0 if res["failed"] == 0 else 1


def dashboard(plan, phase_status, code, reason=""):
    """The short block. One screen, no file lists, at the bottom.

    The full transcript is on disk and --verbose prints it. What this gives is
    the answer to 'where did it get to and what do I do now' without scrolling,
    which is the only part anyone reads twice."""
    done = [p for p, s in phase_status.items() if s == "done"]
    blocked = [p for p, s in phase_status.items() if s == "blocked"]
    failed = [p for p, s in phase_status.items() if s == "failed"]
    skipped_ph = [p for p, s in phase_status.items() if s == "skipped"]
    left = [p for p in plan["phases"] if p["id"] not in done]

    g = TALLY
    bar = "=" * 68
    print("\n" + bar)
    print("PIP-MON  plan %s   [%s]" % (plan["plan_id"], STATE_ROW["level"].upper()))
    print(bar)
    print("  task      : %s" % (STATE_ROW.get("task") or plan["goal"]))
    print("  phase     : %s" % (STATE_ROW.get("phase") or "-"))
    print()
    print("  phases    : %d done / %d total" % (len(done), len(plan["phases"])))
    for p in plan["phases"]:
        s = phase_status.get(p["id"], "pending")
        mark = {"done": "[x]", "blocked": "[!]", "failed": "[X]", "running": "[>]", "skipped": "[~]"}.get(s, "[ ]")
        print("    %s %-4s %-42s %s" % (mark, p["id"], p["name"], s.upper()))
    print()
    print("  checks    : %d run, %d passed" % (g["gates"], g["gate_ok"]))
    if g.get("items_total"):
        print("  items     : %d total | %d ok (%d cached) | %d skipped | %d need action"
              % (g["items_total"], g["items_ok"], g.get("items_cached", 0),
                 g.get("items_skipped", 0), g.get("items_failed", 0)))
    print("  actions   : %d run, %d as expected" % (g["actions"], g["action_ok"]))
    print("  polls     : %d   preflights: %d" % (g["polls"], g["preflights"]))
    print()
    if failed:
        print("  stopped on: %s" % ", ".join(failed))
    if blocked:
        print("  blocked   : %s" % ", ".join(blocked))
    if left and not (failed or blocked):
        print("  remaining : %s" % ", ".join(p["id"] for p in left))
    if reason:
        print("  reason    : %s" % reason)
    print("  state     : %s" % STATE)
    print("  transcript: %s" % TRANSCRIPT)
    print("  %s = %d  %s" % ("EXIT", code, {0: "GREEN", 1: "RED", 3: "STOPPED",
                                            4: "IN FLIGHT"}.get(code, "??")))
    print(bar)


def sh(cmd):
    """Run one allowlisted command. Refuses anything not explicitly allowlisted,
    because a plan should not be able to name an arbitrary command.

    The allowlist is keyed by the EXECUTABLE token, not the whole command string.
    Keying it by the full string meant `tools/validate_plugin.ps1 -Async` matched
    nothing, so P1's actions silently did not run at all and the phase failed at
    verify for the wrong reason entirely. A gate that no-ops its own actions and
    then reports the consequence is worse than one that refuses to start."""
    parts = cmd.split()
    if not parts or parts[0] not in SHELL:
        raise Stop("refused_command",
                   "%r is not in the orchestrator allowlist. A plan names gates and "
                   "detached launches, not arbitrary commands." % (parts[0] if parts else cmd))
    argv = SHELL[parts[0]] + parts[1:]
    try:
        r = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "timed out after 300s"


def allowed(cmd):
    """Membership test that matches how sh() actually dispatches. Kept as one
    function so the check and the dispatch can never drift apart again.

    Every caller that decides 'can this run?' must use THIS, not `x in SHELL`.
    Three divergent copies of that test is not a style problem, it is how a plan
    reported P1 and P2 verified while both its actions had never executed:
    `a["run"] in SHELL` is an exact string match, so "tools/validate_plugin.ps1
    -Async" missed the key "tools/validate_plugin.ps1" and the action was
    skipped in silence. The plan then went on to its verify block and finished
    GREEN. A gate that no-ops its own actions and reports the consequence is
    worse than one that refuses to start.
    """
    parts = str(cmd).split()
    return bool(parts) and parts[0] in SHELL


def classify(gate):
    """Decide what a verify entry IS, before running anything.

    Was: a heuristic on the string shape -- "has a slash and does not end in
    .py/.ps1" means a file. That is wrong for any gate that takes arguments,
    because "tools/xedit_log.py --require report" ends in "report" and was
    therefore checked as though it named a file. The check passed on the mere
    existence of xedit_log.py while the gate itself was never run, and the
    phase verified on that.

    Now: allowlist membership decides. A gate whose first token is allowlisted
    is a COMMAND and is run. Only then may it be a PATH, and only if that path
    exists. Anything else is unrunnable and says so.

    Returns ("command", argv0) | ("path", Path) | ("unknown", None).
    """
    parts = str(gate).split()
    if not parts:
        return ("unknown", None)
    if parts[0] in SHELL:
        return ("command", parts[0])
    if "/" in parts[0] or "\\" in parts[0]:
        p = REPO / parts[0]
        return ("path", p) if p.exists() else ("unknown", p)
    return ("unknown", None)


def sh_detached(cmd):
    """Launch an allowlisted command and return at once, with its pid.

    WHY THIS EXISTS, and it is not a convenience.

    `sh()` uses subprocess.run, which waits. For a command that starts a
    DETACHED job and is supposed to return immediately, waiting is the bug: on
    2026-09-30 `tools/validate_plugin.ps1 -Async` was invoked through sh() and
    the orchestrator sat for the better part of three minutes while xEdit loaded
    the whole load order -- despite the -Async flag, and despite the plan
    declaring a poll for exactly this case. The caller could not be interrupted
    and could not see anything, which is the one combination this project keeps
    paying for.

    So a plan action may declare `"detach": true`. The orchestrator then spawns
    it, records the pid, traces the launch, and moves to the next line. Nothing
    waits on it. The job's own collector reaps it.

    stdout/stderr go to files beside the transcript rather than to a pipe,
    because a pipe nobody drains will eventually block the child -- which would
    reintroduce the same stall one layer down.
    """
    if not allowed(cmd):
        raise Stop("refused_command", "%r is not in the orchestrator allowlist." % cmd)
    argv = SHELL[cmd.split()[0]] + cmd.split()[1:]
    WATCH.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    op = subprocess.Popen(argv, cwd=str(REPO), stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    trace("action_detached", "   %s launched %s detached as pid %d; not waiting on it"
          % (cmd.split()[0].split("/")[-1], cmd, op.pid), level="info",
          cmd=cmd, pid=op.pid, launched=stamp)
    return op.pid


def preflight(plan):
    """Run the plan's own preflight. These are read-only checks that decide
    whether it is safe to continue, and they are cheap on purpose."""
    for check in plan.get("preflight", []):
        TALLY["preflights"] += 1
        code, out = sh(check["run"]) if allowed(check["run"]) else (0, "")
        if check["run"] == "Get-Process xFOEdit64":
            live = subprocess.run(["powershell", "-NoProfile", "-Command",
                                   "@(Get-Process xFOEdit64 -ErrorAction SilentlyContinue).Count"],
                                  capture_output=True, text=True, encoding="utf-8")
            count = int((live.stdout or "0").strip() or 0)
            if count:
                trace("preflight_blocked", "preflight %s: %d xEdit process(es) running"
                      % (did(check), count), level="error", check=did(check), live=count)
                raise Stop("preflight_failed",
                           "%d xEdit process(es) already running. A leaked process from an "
                           "earlier detached launch holds the instance lock and silently blocks "
                           "every later run -- one held it for 191 minutes. Reap it first." % count)
            trace("preflight_ok", "preflight %s: clear" % did(check), check=did(check))
            continue
        bad = code not in (0, 1) and check.get("expect") != "zero processes"
        trace("preflight", "preflight %s: exit=%d" % (did(check), code),
              level="error" if bad else "info", check=did(check), exit=code, output=out[-800:])
    return True


def did(check):
    return check.get("check", "?")


def verify(phase):
    """A phase is done when its verification passes, not when its commands exit 0."""
    for v in phase.get("verify", []):
        gate = v["gate"]
        TALLY["gates"] += 1
        kind, target = classify(gate)
        if kind == "command":
            code, out = sh(gate)
            ok = code == v.get("expect_exit", 0)
            last = (out.strip().splitlines() or [""])[-1]
            detail = "exit=%d %s" % (code, last)
            if not ok:
                detail = "exit=%d (wanted %s) %s" % (code, v.get("expect_exit", 0), out.strip()[-400:])
        elif kind == "path":
            out = "exists"
            ok = True
            detail = "exists: %s" % target
        else:
            # Refuse, loudly. A gate that cannot be run is UNVERIFIED, and
            # reporting it as anything else is the whole failure this project
            # keeps rediscovering in a new costume.
            out = ""
            ok = False
            detail = "UNRUNNABLE: %r is neither an allowlisted command nor an existing path" % gate
        TALLY["gate_ok"] += 1 if ok else 0
        # The gate's own output is kept either way. Previously it was folded into
        # `detail` and then dropped, which is why a stage could fail with no
        # visible reason -- the work had happened and the text had not survived.
        trace("verify", "   %s verify %-46s %s"
              % (phase["id"], gate[:46], "OK" if ok else "FAIL"),
              level="info" if ok else "error",
              phase=phase["id"], gate=gate, kind=kind, ok=ok, detail=detail,
              output=(out[-4000:] if kind == "command" else ""))
        if VERBOSE and kind == "command" and out.strip():
            for ln in out.strip().splitlines():
                print("        | " + ln)
        if not ok:
            TALLY["verify_fail"] += 1
            raise Stop("verify_failed", "phase %s: %s -- %s" % (phase["id"], gate, detail))
    TALLY["verify_ok"] += 1
    return True


def run_plan(plan, through=None, plan_only=False, force=False, args_start=None):
    global VERBOSE
    STATE_ROW.update({"plan": plan["plan_id"], "goal": plan["goal"],
                      "task": plan.get("task") or plan["goal"],
                      "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "phase": "preflight", "level": "declared",
                      "phases_done": [], "phases_remaining": [p["id"] for p in plan["phases"]],
                      "blocked": None, "last_gate": None, "exit": None})
    save_state()

    print("plan: %s" % plan["plan_id"])
    print("  goal   : %s" % plan["goal"])
    if plan.get("task"):
        print("  task   : %s" % plan["task"])
    print("  side   : %s   surfaces: %s" % (plan["side"], ", ".join(plan.get("surfaces", []))))
    if plan.get("requires"):
        print("  requires invariants: %s" % ", ".join(plan["requires"]))
    trace("plan_start", "plan %s declared" % plan["plan_id"], plan=plan["plan_id"],
          task=STATE_ROW["task"], level="declared")

    if plan_only:
        for ph in plan["phases"]:
            print("  %-4s %-38s verify=%d rollback=%d" % (
                ph["id"], ph["name"], len(ph.get("verify", [])),
                len(ph.get("on_failure", {}).get("rollback", []))))
            if ph.get("blocked_reason"):
                print("       BLOCKED: %s" % ph["blocked_reason"][:110])
        return 0

    prior = load_state()
    if prior and prior.get("plan") == plan["plan_id"] and prior.get("phases_done"):
        print("  resume : %d phase(s) already settled -> %s"
              % (len(prior["phases_done"]), ", ".join(prior["phases_done"])))
        trace("resume", "resuming: %s" % ", ".join(prior["phases_done"]), level="declared")

    arch = archive_run(plan["plan_id"])
    if arch:
        trace("archive", "previous run evidence preserved at %s" % arch, archived=str(arch))
        print("  archive: %s" % arch)

    status = {}

    try:
        preflight(plan)
    except Stop as e:
        trace("plan_stopped", "STOP %s: %s" % (e.reason, e.detail), level="error",
              reason=e.reason, detail=e.detail)
        save_state(level="stopped", blocked=e.reason, exit=3)
        dashboard(plan, status, 3, "%s: %s" % (e.reason, e.detail))
        return 3

    started = False
    for ph in plan["phases"]:
        if through and ph["id"] == through:
            print("\n-- stopping before %s as requested --" % through)
            break
        if args_start and not started:
            # --from: begin at a phase rather than replaying the ones already
            # settled. P1 costs a two-minute xEdit load and P2 costs another, so
            # re-running them to reach P4 is paying full price for a result that
            # is already in the transcript. Phases before the start point are
            # reported as SKIPPED, never as passed -- a phase that did not run
            # has not verified anything, and recording it as done is the exact
            # conflation this orchestrator exists to avoid.
            if ph["id"] == args_start:
                started = True
            else:
                status[ph["id"]] = "skipped"
                trace("phase_skipped", "%s skipped (--from %s)" % (ph["id"], args_start),
                      level="warn", phase=ph["id"])
                print("\n%s %s   SKIPPED (--from %s)" % (ph["id"], ph["name"], args_start))
                continue
        if ph.get("blocked_reason"):
            print("\n%s %s is BLOCKED: %s" % (ph["id"], ph["name"], ph["blocked_reason"]))
            trace("phase_blocked", "%s BLOCKED: %s" % (ph["id"], ph["blocked_reason"][:160]),
                  level="warn", phase=ph["id"], reason=ph["blocked_reason"])
            status[ph["id"]] = "blocked"
            save_state(phase=ph["id"], level="blocked", blocked=ph["id"],
                       phases_done=list(status), exit=3)
            break

        print("\n%s %s" % (ph["id"], ph["name"]))
        print("   purpose: %s" % ph["purpose"])
        save_state(phase=ph["id"], level="running", phases_done=list(status))
        trace("phase_start", phase=ph["id"], level="running")

        # A sweep phase fans out over many items and must survive any one of
        # them. A stage is a measurement of everything in scope, and a stage
        # that stops at the first bad file has measured almost nothing.
        if ph.get("sweep"):
            print("   sweep  : %d items (1 failure does not stop the stage)" % len(ph["sweep"]["items"]))
            res = scan(plan["plan_id"], ph["id"], ph["sweep"]["items"],
                       make_worker(ph["sweep"]), force=force)
            code = sweep_report(ph["id"], res)
            # A sweep is a check, and its score is the item tally -- not one
            # pass or fail for the whole stage. Recording it as a single gate
            # made the dashboard say "1 run, 0 passed" for a stage that had
            # actually checked ten files and settled six, which is the kind of
            # number that makes a reader distrust every other number here.
            TALLY["gates"] += 1
            TALLY["gate_ok"] += res["ok"]
            TALLY["items_total"] = TALLY.get("items_total", 0) + res["total"]
            TALLY["items_ok"] = TALLY.get("items_ok", 0) + res["ok"]
            TALLY["items_cached"] = TALLY.get("items_cached", 0) + res["cached"]
            TALLY["items_skipped"] = TALLY.get("items_skipped", 0) + res["skipped"]
            TALLY["items_failed"] = TALLY.get("items_failed", 0) + res["failed"]
            TALLY["verify_ok"] += res["ok"]
            TALLY["verify_fail"] += res["failed"]
            if res["failed"]:
                # Recorded and carried on. The stage is COMPLETE; it just has
                # things that need a human. Hiding that behind a non-zero exit
                # would say "rerun it", which is the opposite of the advice.
                trace("sweep_partial", "%s: %d of %d items failed; stage complete"
                      % (ph["id"], res["failed"], res["total"]),
                      level="warn", phase=ph["id"], failed=res["failures"][:40])
            save_state(phase=ph["id"], level="swept", last_gate="sweep:%s" % ph["id"],
                       phases_done=list(status))
            status[ph["id"]] = "done"
            continue

        for a in ph.get("actions", []):
            print("   run    : %s" % a["run"])
            print("     why  : %s" % a.get("why", ""))
            TALLY["actions"] += 1
            if not allowed(a["run"]):
                # Previously this printed SKIP and carried on, so a phase whose
                # actions could not run went on to its verify block and finished
                # GREEN. A declared action that does not run makes the phase's
                # verdict meaningless, because the verify block then measures
                # whatever the last run happened to leave behind. So this halts.
                trace("action_refused", "   %s action REFUSED (not allowlisted): %s"
                      % (ph["id"], a["run"]), level="error", phase=ph["id"], cmd=a["run"])
                print("     REFUSED: not in the orchestrator allowlist -- see SHELL in orchestrate.py")
                status[ph["id"]] = "failed"
                save_state(phase=ph["id"], level="failed", phases_done=list(status),
                           blocked=ph["id"], exit=3)
                dashboard(plan, status, 3,
                           "action %r is not allowlisted, so %s never ran and its verify "
                           "block would be measuring a previous run" % (a["run"], ph["id"]))
                return 3
            if a.get("detach"):
                pid = sh_detached(a["run"])
                print("     detach: launched as pid %d, NOT waiting. Progress goes to the" % pid)
                print("             trace and to the job's own collector.")
                TALLY["action_ok"] += 1
                continue
            code, out = sh(a["run"])
            want = a.get("expect_exit", 0)
            ok = code == want if not isinstance(want, str) else code == 0
            TALLY["action_ok"] += 1 if ok else 0
            print("     exit : %d %s" % (code, "OK" if ok else "UNEXPECTED"))
            trace("action", "   %s action %-42s exit=%d %s"
                  % (ph["id"], a["run"][:42], code, "OK" if ok else "UNEXPECTED"),
                  level="info" if ok else "warn",
                  phase=ph["id"], cmd=a["run"], exit=code, ok=ok, output=out[-4000:])
            if VERBOSE and out.strip():
                for ln in out.strip().splitlines():
                    print("        | " + ln)

        poll = ph.get("poll")
        if poll and allowed(poll["run"]):
            inflight_exit = poll.get("in_flight_exit", 4)
            budget = BUDGET_OVERRIDE or poll.get("budget_sec", 0)
            interval = INTERVAL_OVERRIDE or poll.get("interval", 20)
            print("   poll   : %s (in-flight exit %s, budget %ds every %ds)"
                  % (poll["run"], inflight_exit, budget, interval))
            waited = 0
            while waited < budget:
                code, out = sh(poll["run"])
                TALLY["polls"] += 1
                trace("poll", "   %s poll %-42s exit=%d waited=%ds"
                      % (ph["id"], poll["run"][:42], code, waited),
                      phase=ph["id"], exit=code, waited=waited, output=out[-2000:])
                if VERBOSE and out.strip():
                    for ln in out.strip().splitlines()[-12:]:
                        print("        | " + ln)
                if code != inflight_exit:
                    print("     converged: exit=%d after %ds" % (code, waited))
                    break
                if waited + interval >= budget:
                    break               # do not sleep past the budget we were given
                time.sleep(interval)
                waited += interval
            else:
                pass
            if code == inflight_exit:
                # Still going. That is a normal state, not a failure, and the
                # right response is to come back -- so say so and return a code
                # that means exactly that.
                print("     still in flight after %ds; returning so you stay free."
                      % waited)
                print("     follow it live : Get-Content %s -Wait" % TRANSCRIPT)
                print("     then re-run    : python tools/orchestrate.py run %s"
                      % plan["plan_id"])
                trace("poll_budget_exhausted", "%s: still in flight after %ds" % (ph["id"], waited),
                      level="warn", phase=ph["id"], waited=waited)
                save_state(phase=ph["id"], level="in-flight", phases_done=list(status), exit=4)
                dashboard(plan, status, 4, "stage %s is running; poll the trace, do not relaunch"
                           % ph["id"])
                return 4

        try:
            verify(ph)
            print("   verified.")
            status[ph["id"]] = "done"
            # The save point. Written here, after verification, so a run that
            # dies mid-plan still says which phases actually passed.
            save_state(phase=ph["id"], level="verified", phases_done=list(status),
                       phases_remaining=[p["id"] for p in plan["phases"]
                                          if p["id"] not in status])
            trace("phase_done", "%s verified" % ph["id"], phase=ph["id"], level="verified")
        except Stop as e:
            status[ph["id"]] = "failed"
            save_state(phase=ph["id"], level="failed", phases_done=list(status),
                       blocked=ph["id"], exit=3)
            trace("phase_failed", "%s: %s" % (ph["id"], e.detail), level="error",
                  phase=ph["id"], detail=e.detail)
            dashboard(plan, status, 3, "%s -- %s" % (e.reason, e.detail))
            return 3

    save_state(phase="end", level="complete", phases_done=list(status), exit=0)
    trace("plan_end", "plan %s complete" % plan["plan_id"], plan=plan["plan_id"], level="complete")
    dashboard(plan, status, 0)
    return 0


def make_worker(sweep):
    """Turn a plan's declared sweep into a callable that tolerates failure.

    `check` is the name of a gate to run per item. The gate's exit code decides
    ok / skip / fail; its output is kept either way. Nothing here raises for a
    bad item, because the sweep is the thing that must not stop."""
    check = sweep.get("check", "tools/artifact_gate.py")

    def work(item):
        if not allowed(check):
            raise SkipItem("sweep check %r is not in the allowlist" % check)
        code, out = sh("%s %s" % (check, item))
        if code == 3:
            raise SkipItem(out.strip().splitlines()[-1] if out.strip() else "gate reported SKIP")
        if code != 0:
            tail = [l for l in out.strip().splitlines() if l.strip()]
            raise RuntimeError("exit=%d %s" % (code, (tail[-1] if tail else "no output")[:160]))
        return "ok"
    return work


def dry_run(plan, through=None):
    """Walk the whole choreography and print it, executing nothing.

    This is the cheap rehearsal. Every phase, every action, every gate and every
    poll is shown in the order the real run would take it, so the plan can be
    read and argued with before a single three-minute load is spent on it.

    It is a dry run and it says so on every line, because the one way a dry run
    becomes dangerous is by being mistaken for the real thing. Anything with a
    cost attached -- an xEdit load, a generation pass -- is named with its cost
    so the price of the real run is legible before committing to it.
    """
    print("=" * 68)
    print("DRY RUN -- nothing below is executed. No process is launched.")
    print("=" * 68)
    print("plan: %s" % plan["plan_id"])
    print("  goal   : %s" % plan["goal"])
    if plan.get("task"):
        print("  task   : %s" % plan["task"])
    print("  side   : %s   surfaces: %s" % (plan["side"], ", ".join(plan.get("surfaces", []))))
    if plan.get("requires"):
        print("  requires invariants: %s" % ", ".join(plan["requires"]))

    if plan.get("preflight"):
        print("\npreflight")
        for c in plan["preflight"]:
            print("  - %-38s via %s" % (c["check"], c["run"]))
            print("      %s" % c.get("why", "")[:100])

    total_actions = 0
    for ph in plan["phases"]:
        if through and ph["id"] == through:
            print("\n-- would stop before %s --" % through)
            break
        blocked = ph.get("blocked_reason")
        print("\n%s %s%s" % (ph["id"], ph["name"], "   [BLOCKED]" if blocked else ""))
        print("   purpose: %s" % ph["purpose"])
        for pre in ph.get("preconditions", []):
            print("   needs  : %s" % pre)
        if blocked:
            print("   BLOCKED: %s" % blocked[:150])
        if ph.get("sweep"):
            print("   sweep  : %d items, one failure does not stop the stage"
                  % len(ph["sweep"]["items"]))
            print("     check: %s" % ph["sweep"].get("check"))
            for it in ph["sweep"]["items"]:
                print("       - %s" % it)
        for a in ph.get("actions", []):
            total_actions += 1
            run = a["run"]
            allowed_here = allowed(run)
            print("   action : %s" % run)
            print("     allow: %s" % ("yes" if allowed_here else "NO -- would be refused"))
            print("     want : exit %s" % a.get("expect_exit", 0))
            print("     why  : %s" % a.get("why", "")[:100])
        if ph.get("poll"):
            p = ph["poll"]
            print("   poll   : %s" % p["run"])
            print("     in-flight exit %s, every %ss, budget %ss (override with --budget/--interval)"
                  % (p.get("in_flight_exit", 4), p.get("interval", 20), p.get("budget_sec", 0)))
            print("     while in flight the trace grows at %s" % TRANSCRIPT)
        for v in ph.get("verify", []):
            g = v["gate"]
            kind, _ = classify(g)
            if kind == "command":
                how = "command (runnable)"
            elif kind == "path":
                how = "file (present)"
            else:
                how = "UNRUNNABLE -- neither allowlisted nor an existing path"
            print("   verify : %s" % g)
            print("     %s, want exit %s" % (how, v.get("expect_exit", 0)))
            print("     why   : %s" % v.get("why", "")[:100])
        of = ph.get("on_failure", {})
        print("   on fail: stop=%s, %d rollback step(s)" % (of.get("stop", True),
                                                             len(of.get("rollback", []))))
        for r in of.get("rollback", []):
            print("       - %s" % r)
        if of.get("report"):
            print("     report: %s" % of["report"][:130])

    print("\n" + "=" * 68)
    print("DRY RUN SUMMARY   phases=%d  actions=%d  no process was launched"
          % (len(plan["phases"]), total_actions))
    unrunnable = []
    for ph in plan["phases"]:
        for a in ph.get("actions", []):
            if not allowed(a["run"]):
                unrunnable.append(a["run"])
        for v in ph.get("verify", []):
            if classify(v["gate"])[0] == "unknown":
                unrunnable.append("verify: " + v["gate"])
    if unrunnable:
        print("  WOULD BE REFUSED (%d) -- allowlist is SHELL in tools/orchestrate.py:" % len(unrunnable))
        for u in unrunnable:
            print("    ! %s" % u)
    else:
        print("  every action and gate is runnable")
    print("  real run : python tools/orchestrate.py run %s" % plan["plan_id"])
    print("  live view: Get-Content %s -Wait" % TRANSCRIPT)
    print("=" * 68)
    return 0


def main():
    global VERBOSE
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["list", "show", "run", "state"])
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--through", help="stop before this phase id")
    ap.add_argument("--from", dest="args_start", help="begin AT this phase id; earlier phases are reported SKIPPED, never passed")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="also print each gate's own output. It is always captured "
                         "to the transcript and the state file either way.")
    ap.add_argument("--force", action="store_true",
                    help="re-attempt sweep items already marked ok in the ledger")
    ap.add_argument("--budget", type=int, default=0,
                    help="total seconds to spend polling an in-flight stage. 0 uses the "
                         "plan's own value. Kept small on purpose: the orchestrator "
                         "sets the stage up and narrates it, then RETURNS, so a long "
                         "job never becomes a long silence. Poll the rest yourself.")
    ap.add_argument("--interval", type=int, default=0,
                    help="seconds between polls. 0 uses the plan's own value.")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the whole choreography and exit. Executes nothing, "
                         "launches nothing, costs nothing.")
    args = ap.parse_args()
    VERBOSE = args.verbose
    BUDGET_OVERRIDE = args.budget
    INTERVAL_OVERRIDE = args.interval

    if args.command == "state":
        st = load_state()
        if not st:
            print("no state yet: %s" % STATE)
            return 0
        print(json.dumps(st, indent=2))
        return 0

    plans = sorted(PLANS.glob("*.pyr"))
    if args.command == "list":
        for p in plans:
            d = json.loads(p.read_text(encoding="utf-8"))
            print("  %-24s %s" % (d["plan_id"], d["goal"][:80]))
        return 0

    if not args.plan:
        print("name the plan", file=sys.stderr)
        return 4
    path = PLANS / (args.plan + ".pyr")
    if not path.exists():
        print("no such plan: %s" % path, file=sys.stderr)
        return 4
    plan = json.loads(path.read_text(encoding="utf-8"))

    if args.command == "show":
        print(json.dumps(plan, indent=2))
        return 0
    if args.dry_run:
        return dry_run(plan, args.through)
    try:
        return run_plan(plan, args.through, args.plan_only, force=args.force, args_start=args.args_start)
    except Stop as e:
        trace("plan_stopped", "STOP %s: %s" % (e.reason, e.detail), level="error",
              reason=e.reason, detail=e.detail)
        print("\nSTOP: %s\n  %s" % (e.reason, e.detail))
        return 3


if __name__ == "__main__":
    sys.exit(main())


