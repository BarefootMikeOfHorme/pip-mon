"""Gate watch: the conversational counterpart to the one-way gates.

Every other gate here is one-way. It runs, it exits with a code, and it is gone.
That means nothing ever tells you what CHANGED or WHY, and a session inherits a
pass/fail with no memory of how it got there.

This is the other half. It runs the gate set on an interval and speaks ONLY when
something relevant changed, because a gate that talks constantly is a gate nobody
reads. Silence is the normal case and is not a failure to report.

It writes two things:

  runs/watch/gate-history.jsonl   append-only, one record per observed change,
                                  timestamped, so "when did artifact_gate go
                                  red, and what was new?" is answerable later
  runs/watch/gate-converse.md     the current conversation surface, rewritten
                                  only on change, for an agent to read at leisure

The back-and-forth part is --since and --why: given a gate that changed, it
reports what moved and which input moved it, from provenance the gates already
carry. It never invents an explanation; if a gate gives no reason, it says the
gate gave no reason.

    python tools/gate_watch.py --once            # single sweep, for the build
    python tools/gate_watch.py --watch           # long-running, delta-only
    python tools/gate_watch.py --since 30m       # what changed in the last 30 min
    python tools/gate_watch.py --why artifact_gate   # what moved, and when
    python tools/gate_watch.py --json
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
WATCH = REPO / "runs" / "watch"
HISTORY = WATCH / "gate-history.jsonl"
CONVERSE = WATCH / "gate-converse.md"

# Ordered cheapest-first so a sweep that is going to fail loudly gets there
# before the slow ones. Each is (name, relative script, timeout seconds).
GATES = [
    ("spec_lint", "tools/spec_lint.py", 120),
    ("ownership_gate", "tools/ownership_gate.py", 120),
    ("surfaces_gate", "tools/surfaces_gate.py", 120),
    ("side_gate", "tools/side_gate.py", 120),
    ("artifact_gate", "tools/artifact_gate.py", 300),
    ("door_lint", "tools/door_lint.py", 600),
    ("rag_selftest", "tools/rag_selftest.py", 600),
]

# How the gate's own reason is extracted. These read the tools' stdout, because
# the reason is already there and re-deriving it here would be a second,
# possibly-wrong opinion about the same gate.
REASON_PATTERNS = {
    "rag_selftest": "rag_selftest: ",
    "spec_lint": "spec_lint: ",
    "artifact_gate": "NEW errors",
    "door_lint": "door_lint: ",
    "side_gate": "sides available",
    "surfaces_gate": "problems",
    "ownership_gate": "problems",
}


def run_gate(name, script, timeout):
    try:
        r = subprocess.run([PY, str(REPO / script)], cwd=str(REPO), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {"exit": r.returncode, "stdout": r.stdout or "", "stderr": r.stderr or ""}
    except subprocess.TimeoutExpired:
        return {"exit": 124, "stdout": "", "stderr": "timed out after %ds" % timeout}
    except OSError as e:
        return {"exit": 127, "stdout": "", "stderr": str(e)}


def summarise(name, res):
    """The gate's own verdict, plus its own reason if it gave one."""
    text = (res["stdout"] or "") + (res["stderr"] or "")
    verdict = "GREEN" if res["exit"] == 0 else "RED"
    reason = ""
    pat = REASON_PATTERNS.get(name)
    if pat:
        for line in text.splitlines():
            if pat in line:
                reason = line.strip()
                break
    if not reason and res["exit"] != 0:
        # Deliberately says it has no reason rather than inventing one.
        reason = "gate gave no reason; exit=%d" % res["exit"]
    return verdict, reason


def sweep():
    out = {}
    for name, script, timeout in GATES:
        res = run_gate(name, script, timeout)
        verdict, reason = summarise(name, res)
        out[name] = {"verdict": verdict, "reason": reason, "exit": res["exit"]}
    return out


def fingerprint(state):
    return {k: (v["verdict"], v["reason"]) for k, v in state.items()}


def load_last():
    if not HISTORY.exists():
        return None, []
    records = []
    for line in HISTORY.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return (records[-1]["state"] if records else None), records


def diff_states(old, new):
    if old is None:
        return ["initial sweep: %d gates, %d green"
                % (len(new), sum(1 for v in new.values() if v["verdict"] == "GREEN"))]
    deltas = []
    for name in sorted(set(old) | set(new)):
        o, n = old.get(name), new.get(name)
        if o is None:
            deltas.append("%s: NEW -> %s (%s)" % (name, n["verdict"], n["reason"]))
        elif n is None:
            deltas.append("%s: REMOVED (was %s)" % (name, o["verdict"]))
        elif o["verdict"] != n["verdict"]:
            deltas.append("%s: %s -> %s (%s)" % (name, o["verdict"], n["verdict"], n["reason"]))
        elif o["reason"] != n["reason"]:
            deltas.append("%s: still %s, reason changed: %s" % (name, n["verdict"], n["reason"]))
    return deltas


def write_history(state, deltas):
    WATCH.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "state": fingerprint(state),
            "deltas": deltas,
        }) + "\n")


def write_converse(state, deltas, prev_deltas):
    """Rewritten ONLY when something changed. A file that rewrites itself with
    identical content every sweep is noise wearing the costume of a dashboard."""
    WATCH.mkdir(parents=True, exist_ok=True)
    if not deltas:
        return False
    lines = ["# Gate conversation", "",
             "* **Updated:** `%s`" % time.strftime("%Y-%m-%d %H:%M:%S"),
             "* **Changed:** %d event(s)" % len(deltas),
             "* **State:** %d of %d gates green"
             % (sum(1 for v in state.values() if v["verdict"] == "GREEN"), len(state)),
             "", "## This sweep", ""]
    lines += ["- %s" % d for d in deltas] or ["- (nothing changed; this file was not rewritten)"]
    lines += ["", "## Current", "",
              "| gate | verdict | the gate's own reason |", "|---|---|---|"]
    for name in sorted(state):
        v = state[name]
        lines.append("| `%s` | %s | %s |" % (name, v["verdict"], v["reason"] or "-"))
    lines += ["", "## Previous sweep", ""]
    lines += ["- %s" % d for d in (prev_deltas or ["(no prior record)"])]
    lines += ["", "History: `runs/watch/gate-history.jsonl` (append-only).",
              "This file is written only on change, so its mtime is meaningful."]
    CONVERSE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def parse_since(s):
    s = s.strip().lower()
    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if s and s[-1] in mult:
        return int(float(s[:-1]) * mult[s[-1]])
    return int(s) if s.isdigit() else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=int, default=180)
    ap.add_argument("--since")
    ap.add_argument("--why")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    WATCH.mkdir(parents=True, exist_ok=True)
    _, records = load_last()

    if args.since or args.why:
        window = parse_since(args.since or "")
        cutoff = time.time() - window if window else None
        out = []
        for rec in records:
            ts = rec.get("utc", "")
            if cutoff is not None:
                try:
                    if time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")) < cutoff:
                        continue
                except ValueError:
                    pass
            if args.why:
                hits = [d for d in rec.get("deltas", []) if d.startswith(args.why)]
                if hits:
                    out.append({"utc": ts, "deltas": hits})
            else:
                out.append({"utc": ts, "deltas": rec.get("deltas", [])})
        if args.json:
            print(json.dumps({"schema": "pipmon.gate.converse/1", "records": out}, indent=2))
        else:
            if not out:
                print("no recorded change in that window; silence is the normal case")
            for rec in out:
                print("  %s" % rec["utc"])
                for d in rec["deltas"]:
                    print("      %s" % d)
        return 0

    if args.watch:
        print("gate_watch: sweeping every %ds, speaking only on change. Ctrl-C to stop."
              % args.interval, flush=True)
        prev_deltas = []
        try:
            while True:
                state = sweep()
                old, records = load_last()
                deltas = diff_states(old, state)
                write_history(state, deltas)
                if deltas:
                    write_converse(state, deltas, prev_deltas)
                    prev_deltas = deltas
                    for d in deltas:
                        print("[%s] %s" % (time.strftime("%H:%M:%S"), d), flush=True)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\ngate_watch stopped")
        return 0

    # --once, and the default
    state = sweep()
    old, records = load_last()
    deltas = diff_states(old, state)
    write_history(state, deltas)
    wrote = write_converse(state, deltas, None)

    if args.json:
        print(json.dumps({"schema": "pipmon.gate.converse/1", "state": state,
                          "deltas": deltas, "converse_written": wrote}, indent=2))
        return 0 if all(v["verdict"] == "GREEN" for v in state.values()) else 1

    print("gate_watch: %d of %d gates green" % (
        sum(1 for v in state.values() if v["verdict"] == "GREEN"), len(state)))
    for name in sorted(state):
        v = state[name]
        print("  [%-5s] %-16s %s" % (v["verdict"], name, v["reason"] or "-"))
    if deltas:
        print("\n  changed since last sweep:")
        for d in deltas:
            print("    %s" % d)
        print("  converse surface: %s" % CONVERSE)
    else:
        print("\n  nothing changed; the converse surface was not rewritten")
    return 0 if all(v["verdict"] == "GREEN" for v in state.values()) else 1


if __name__ == "__main__":
    sys.exit(main())