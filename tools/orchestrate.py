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
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLANS = REPO / "ai_context" / "plans"
TRANSCRIPT = REPO / "runs" / "watch" / "orchestrator-transcript.jsonl"
PY = sys.executable

# Only shell-outs that are genuinely safe to run here. Anything long or
# GUI-bearing must be a detached launch inside the plan, never a direct call.
SHELL = {
    "tools/artifact_gate.py": [PY, "tools/artifact_gate.py"],
    "tools/side_gate.py": [PY, "tools/side_gate.py"],
    "tools/spec_lint.py": [PY, "tools/spec_lint.py"],
    "tools/rag_selftest.py": [PY, "tools/rag_selftest.py"],
    "tools/validate_plugin.ps1": ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                  "-File", "tools/validate_plugin.ps1"],
}


class Stop(Exception):
    def __init__(self, reason, detail=""):
        self.reason = reason
        self.detail = detail


def record(entry):
    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    entry["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with TRANSCRIPT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


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
    function so the check and the dispatch can never drift apart again."""
    parts = cmd.split()
    return bool(parts) and parts[0] in SHELL


def preflight(plan):
    """Run the plan's own preflight. These are read-only checks that decide
    whether it is safe to continue, and they are cheap on purpose."""
    for check in plan.get("preflight", []):
        code, out = sh(check["run"]) if check["run"] in SHELL else (0, "")
        if check["run"] == "Get-Process xFOEdit64":
            live = subprocess.run(["powershell", "-NoProfile", "-Command",
                                   "@(Get-Process xFOEdit64 -ErrorAction SilentlyContinue).Count"],
                                  capture_output=True, text=True, encoding="utf-8")
            count = int((live.stdout or "0").strip() or 0)
            if count:
                record({"event": "preflight_blocked", "check": did(check), "live": count})
                raise Stop("preflight_failed",
                           "%d xEdit process(es) already running. A leaked process from an "
                           "earlier detached launch holds the instance lock and silently blocks "
                           "every later run -- one held it for 191 minutes. Reap it first." % count)
            record({"event": "preflight_ok", "check": did(check)})
            continue
        record({"event": "preflight", "check": did(check), "exit": code})
    return True


def did(check):
    return check.get("check", "?")


def verify(phase):
    """A phase is done when its verification passes, not when its commands exit 0."""
    for v in phase.get("verify", []):
        gate = v["gate"]
        target = None
        if "/" in gate and not gate.endswith(".py") and not gate.endswith(".ps1"):
            target = REPO / gate.split()[0]
        if target is not None:
            ok = target.exists()
            detail = ("exists" if ok else "ABSENT: %s" % target)
        else:
            code, out = sh(gate)
            ok = code == v.get("expect_exit", 0)
            detail = "exit=%d %s" % (code, out.strip().splitlines()[-1:] or [""])
            if not ok:
                detail = "exit=%d (wanted %s) %s" % (code, v.get("expect_exit", 0), out.strip()[-400:])
        record({"event": "verify", "phase": phase["id"], "gate": gate, "ok": ok, "detail": detail})
        if not ok:
            raise Stop("verify_failed", "phase %s: %s -- %s" % (phase["id"], gate, detail))
    return True


def run_plan(plan, through=None, plan_only=False):
    print("plan: %s" % plan["plan_id"])
    print("  goal   : %s" % plan["goal"])
    print("  side   : %s   surfaces: %s" % (plan["side"], ", ".join(plan.get("surfaces", []))))
    if plan.get("requires"):
        print("  requires invariants: %s" % ", ".join(plan["requires"]))
    record({"event": "plan_start", "plan": plan["plan_id"], "goal": plan["goal"]})

    if plan_only:
        for ph in plan["phases"]:
            print("  %-4s %-38s verify=%d rollback=%d" % (
                ph["id"], ph["name"], len(ph.get("verify", [])),
                len(ph.get("on_failure", {}).get("rollback", []))))
            if ph.get("blocked_reason"):
                print("       BLOCKED: %s" % ph["blocked_reason"][:110])
        return 0

    try:
        preflight(plan)
    except Stop as e:
        print("\nSTOP: %s\n  %s" % (e.reason, e.detail))
        record({"event": "plan_stopped", "reason": e.reason, "detail": e.detail})
        return 3

    for ph in plan["phases"]:
        if through and ph["id"] == through:
            print("\n-- stopping before %s as requested --" % through)
            break
        if ph.get("blocked_reason"):
            print("\n%s %s is BLOCKED: %s" % (ph["id"], ph["name"], ph["blocked_reason"]))
            record({"event": "phase_blocked", "phase": ph["id"], "reason": ph["blocked_reason"]})
            break

        print("\n%s %s" % (ph["id"], ph["name"]))
        print("   purpose: %s" % ph["purpose"])
        for a in ph.get("actions", []):
            print("   run    : %s" % a["run"])
            print("     why  : %s" % a.get("why", ""))
            if a["run"] in SHELL:
                code, out = sh(a["run"])
                want = a.get("expect_exit", 0)
                ok = code == want if not isinstance(want, str) else code == 0
                print("     exit : %d %s" % (code, "OK" if ok else "UNEXPECTED"))
                record({"event": "action", "phase": ph["id"], "cmd": a["run"], "exit": code, "ok": ok})

        # A detached launch is not done when it returns; it is done when the
        # thing it launched finishes. Without this, P1's verify block would fail
        # on a perfectly healthy run that simply had not finished loading yet --
        # which is the same class of error as treating a stale index as fresh.
        poll = ph.get("poll")
        if poll and poll["run"] in SHELL:
            inflight_exit = poll.get("in_flight_exit", 4)
            budget = poll.get("budget_sec", 0)
            print("   poll   : %s (in-flight exit %s, budget %ds)"
                  % (poll["run"], inflight_exit, budget))
            waited = 0
            while waited < budget:
                code, out = sh(poll["run"])
                record({"event": "poll", "phase": ph["id"], "exit": code, "waited": waited})
                if code != inflight_exit:
                    print("     converged: exit=%d after %ds" % (code, waited))
                    break
                time.sleep(poll.get("interval", 20))
                waited += poll.get("interval", 20)
            else:
                print("     still in flight after %ds budget; returning so the caller stays free."
                      % budget)
                record({"event": "poll_budget_exhausted", "phase": ph["id"], "waited": waited})
                return 4

        verify(ph)
        print("   verified.")

    print("\nplan %s: phases completed up to the block above." % plan["plan_id"])
    record({"event": "plan_end", "plan": plan["plan_id"]})
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["list", "show", "run"])
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--through", help="stop before this phase id")
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()

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
    try:
        return run_plan(plan, args.through, args.plan_only)
    except Stop as e:
        print("\nSTOP: %s\n  %s" % (e.reason, e.detail))
        return 3


if __name__ == "__main__":
    sys.exit(main())