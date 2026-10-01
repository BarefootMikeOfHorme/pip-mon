"""Self-test for the orchestrator's own decision logic.

Why this file exists
--------------------
On 2026-09-30 the orchestrator reported a plan GREEN while BOTH of its phases'
actions had never executed, and a verify gate that had never run had "passed"
because it was silently reclassified as a file-existence check. Every line it
printed was true and the conclusion was false.

Both defects were the same mistake: the "can this run?" test was written out
three separate times, slightly differently each time, so the version that
decided whether to RUN a command disagreed with the version that decided
whether a gate was a command or a path.

That is a shape of bug no assertion on the output would have caught, because the
output was self-consistent. So these tests assert the DECISIONS, not the
reporting: given this input, is this classified as a command, and is it
allowlisted. If someone reintroduces a private membership test, these fail.

    python tools/orchestrate_selftest.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchestrate as O  # noqa: E402

FAILED = []


def check(name, got, want):
    if got == want:
        print("  ok    %-58s %r" % (name, got))
    else:
        print("  FAIL  %-58s got %r, wanted %r" % (name, got, want))
        FAILED.append(name)


print("orchestrator self-test: allowlist and gate classification")

# The exact defect: an action carrying arguments must still be allowlisted.
check("action with args is allowlisted",
      O.allowed("tools/validate_plugin.ps1 -Async"), True)
check("action with args is allowlisted (collect)",
      O.allowed("tools/validate_plugin.ps1 -Collect"), True)
check("bare command is allowlisted", O.allowed("tools/artifact_gate.py"), True)
check("unknown command is refused", O.allowed("tools/not_a_real_tool.py"), False)
check("empty command is refused", O.allowed(""), False)

# The second defect: a gate with arguments was being read as a file path
# because it did not end in .py. Arguments must not change the classification.
check("gate with args classifies as COMMAND",
      O.classify("tools/xedit_log.py --require report")[0], "command")
check("gate with --require loader is COMMAND",
      O.classify("tools/xedit_log.py --require loader")[0], "command")
check("bare tool classifies as COMMAND",
      O.classify("tools/check_item.py")[0], "command")
check("nonexistent path is unknown",
      O.classify("runs/watch/nope.json")[0], "unknown")
check("prose is unknown, not a path",
      O.classify("the generator declines rather than guesses")[0], "unknown")
check("empty gate is unknown", O.classify("")[0], "unknown")

# A real existing path still classifies as a path, so the file check survives.
check("existing file classifies as PATH",
      O.classify("tools/orchestrate.py")[0], "path")

# The dispatcher must agree with the classifier, or the two drift again.
check("sh() would accept an allowlisted action with args",
      O.allowed("tools/rag_selftest.py --json"), True)
check("classify and allowed agree on a command",
      O.classify("tools/rag_selftest.py --json")[0] == "command"
      and O.allowed("tools/rag_selftest.py --json"), True)

# Every plan in the tree must have no unrunnable action or gate. This is the
# check that would have caught the original eight prose gates before a single
# three-minute load was spent discovering them.
plans = sorted(O.PLANS.glob("*.pyr"))
if not plans:
    print("  FAIL  no plans found to check")
    FAILED.append("plans present")
for p in plans:
    import json
    d = json.loads(p.read_text(encoding="utf-8"))
    bad = []
    for ph in d.get("phases", []):
        for a in ph.get("actions", []):
            if not O.allowed(a["run"]):
                bad.append("action: " + a["run"])
        for v in ph.get("verify", []):
            if O.classify(v["gate"])[0] == "unknown":
                bad.append("verify: " + v["gate"])
    check("plan %s has no unrunnable action or gate" % d["plan_id"], bad, [])

print("")
if FAILED:
    print("orchestrator_selftest: %d FAILED -- %s" % (len(FAILED), ", ".join(FAILED)))
    sys.exit(1)
print("orchestrator_selftest: all checks passed")
