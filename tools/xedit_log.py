"""xEdit run oracle: what actually happened, measured from xEdit's own logs.

Why this exists
---------------
The plan's P1 gate used to be the string "FO4Script_log.txt advanced past
'Loading active plugin list'", which is not a gate -- the orchestrator's verify()
can only run an allowlisted command, so that phrase was unreachable and the
phase failed for a reason that had nothing to do with xEdit.

The information it was reaching for is real and it is measurable, so this
measures it. It answers four separate questions, because they fail separately
and each has a different fix:

    did the background loader finish?   a load problem, or no problem
    did the script start applying?      a wiring problem (placeholders, path)
    did it reach Finalize?              a runtime problem inside the script
    did the report land?                the only actual proof

and separately, what did xEdit's exception log say, since a COMPILE failure
never appears in FO4Script_log.txt at all.

Read-only. Touches nothing but two log files. Offline.

Exit codes, chosen so a plan gate can use them directly:
    0  every --require was satisfied
    1  the run happened and something required was not reached
    3  there is no evidence yet -- UNVERIFIED, never collapsed into pass

    python tools/xedit_log.py
    python tools/xedit_log.py --require loader --require script
    python tools/xedit_log.py --require report --json
"""
import argparse
import json
import os
import re
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WATCH = REPO / "runs" / "watch"
XEDIT_DIR = Path(os.environ.get("PIPMON_XEDIT_DIR",
                                Path(os.environ.get("LOCALAPPDATA", "")) / "Temp" / "opencode" / "xedit" / "x"))
SCRIPT_LOG = XEDIT_DIR / "FO4Script_log.txt"
EXC_LOG = XEDIT_DIR / "xFOEdit64Exception.log"
REPORT = WATCH / "xedit-validation-report.json"
# The generator writes a different report. Without this, a gate asking for "the
# report" after a generator run would find the VALIDATOR's stale report and pass
# on evidence from a different job -- which is the quiet substitution this tool exists
# to prevent.
GEN_REPORT = WATCH / "gen-facility-report.json"
REPORTS = {"validator": REPORT, "generator": GEN_REPORT}

RE_DONE = re.compile(r"Done (?:loading|building) reference info", re.I)
RE_START = re.compile(r'Start:\s*Applying script\s*"([^"]+)"', re.I)
RE_ABORT = re.compile(r"Exception in unit .*?line (\d+):\s*\[(\w+)\]\s*(.*)", re.I)
RE_INTERP = re.compile(r"Undeclared Identifier '([^']+)'", re.I)


def read(p):
    """Decode by BOM, not by hope.

    xFOEdit64Exception.log is UTF-16LE with a BOM. Read as UTF-8 it becomes
    mojibake -- every character followed by a NUL -- and then EVERY regex in
    this file silently matches nothing, which presents as "xEdit reported no
    exception" rather than as a decoding bug. PowerShell hides this by
    auto-detecting the BOM, so a change that works there fails here for a
    reason nothing in the output would tell you.
    """
    try:
        raw = p.read_bytes()
    except OSError:
        return None
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def safe(s, limit=200):
    """Console-safe text.

    These logs carry bytes that a cp1252 console cannot encode, and printing one
    raises UnicodeEncodeError -- which in a sweep is recorded as a failed item
    and looks like the tool being broken rather than the tool reporting on a
    file that is not text. Lossy on purpose: a replacement character is a
    cosmetic problem, a crash is a false negative."""
    if s is None:
        return ""
    return str(s).encode("ascii", "replace").decode("ascii")[:limit]


# The separator is a line of '=' characters. In the UTF-16 file every character
# is NUL-interleaved until it is decoded, so this only matches after read().
RE_SEPARATOR = re.compile(r"(?m)^[=\s]*=[=\s]*$")


def survey(which="validator"):
    global REPORT
    # Resolve the report BEFORE the result dict is built. Setting it afterwards
    # looks equivalent and is not: the dict captures REPORT at construction, so
    # --report generator measured the validator's file and reported the
    # generator's report as present when no such file existed. A gate that
    # measures the wrong artefact is worse than one that measures nothing.
    REPORT = REPORTS.get(which, REPORT)
    s = {"logPresent": SCRIPT_LOG.exists(), "logLines": 0, "pluginsLoaded": 0,
         "loaderFinished": False, "scriptStarted": None, "aborted": None,
         "abortLine": None, "abortKind": None, "abortText": None,
         "undeclared": None, "lastLine": None, "logMtime": None,
         "reportPresent": REPORT.exists(), "reportMtime": None,
         "exception": None, "exceptionKind": None, "exceptionMtime": None}


    raw = read(SCRIPT_LOG)
    if raw:
        lines = raw.splitlines()
        s["logLines"] = len(lines)
        s["logMtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(SCRIPT_LOG.stat().st_mtime))
        s["pluginsLoaded"] = sum(1 for l in lines if RE_DONE.search(l))
        s["loaderFinished"] = any("Background Loader: finished" in l for l in lines)
        for l in lines:
            m = RE_START.search(l)
            if m:
                s["scriptStarted"] = m.group(1)
        for l in reversed(lines):
            m = RE_ABORT.search(l)
            if m:
                s["aborted"] = True
                s["abortLine"] = int(m.group(1))
                s["abortKind"] = m.group(2)
                s["abortText"] = m.group(3).strip()
                break
        s["lastLine"] = lines[-1].strip() if lines else None
        s["undeclared"] = RE_INTERP.search(raw).group(1) if RE_INTERP.search(raw) else None

    if REPORT.exists():
        s["reportMtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(REPORT.stat().st_mtime))

    exc = read(EXC_LOG)
    if exc:
        blocks = [b for b in RE_SEPARATOR.split(exc) if b.strip()]
        last = blocks[-1] if blocks else exc
        mm = re.search(r"(?m)^\s*Message:\s*(.+?)\s*$", last)
        s["exception"] = safe(mm.group(1), 300) if mm else None
        s["exceptionMtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(EXC_LOG.stat().st_mtime))
        s["exceptionBlocks"] = len(blocks)
        if "CreateScript" in last or (s["exception"] and "expected but" in s["exception"]):
            s["exceptionKind"] = "compile"
        elif s["exception"] and "Undeclared Identifier" in s["exception"]:
            s["exceptionKind"] = "undeclared"
        # Which exception the newest block holds, by its own timestamp, so a
        # reader can tell a current failure from a historical one without
        # cross-referencing file mtimes.
        tm = re.search(r"(?m)^\s*Time:.*?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", last)
        s["exceptionTime"] = tm.group(1) if tm else None
    # Whether the exception belongs to the run described by the run log. A
    # compile error is written once and then sits there forever, so an
    # exception log OLDER than the run log describes an earlier attempt. Reading
    # it as current is how a bug that was already fixed keeps being reported as
    # live, and it is worse than having no exception reader at all.
    if s.get("exceptionMtime") and s.get("logMtime"):
        try:
            s["exceptionIsCurrent"] = (EXC_LOG.stat().st_mtime >= SCRIPT_LOG.stat().st_mtime)
        except OSError:
            s["exceptionIsCurrent"] = None
    else:
        s["exceptionIsCurrent"] = None
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--require", action="append", default=[],
                    choices=["log", "loader", "script", "finalize", "report"],
                    help="assert this much happened; all must hold")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", choices=sorted(REPORTS), default="validator",
                    help="which report to measure. A generator phase must say so, or it"
                         " will be graded against the validator's leftover report.")
    ap.add_argument("--gen-key", action="store_true",
                    help="also require the generator report to declare records_created > 0")
    ap.add_argument("--stale-after", type=int, default=900,
                    help="seconds after which the evidence is called out as stale")
    args = ap.parse_args()

    s = survey(args.report)
    age = None
    if s["logMtime"]:
        age = time.time() - SCRIPT_LOG.stat().st_mtime
        s["evidenceAgeSec"] = int(age)
        s["stale"] = age > args.stale_after

    if args.json:
        print(json.dumps(s, indent=2))
    else:
        if not s["logPresent"]:
            print("no evidence: %s does not exist" % SCRIPT_LOG)
            print("nothing has been run, so nothing is known. This is UNVERIFIED, not fine.")
            return 3
        print("xEdit run evidence   %s" % s["logMtime"])
        if s.get("stale"):
            print("  WARNING  %ds old (>%ds). This describes an earlier run, not now."
                  % (s["evidenceAgeSec"], args.stale_after))
        print("  log lines        %d" % s["logLines"])
        print("  plugins loaded   %d through the reference stage" % s["pluginsLoaded"])
        print("  loader finished  %s" % ("YES" if s["loaderFinished"] else "NO"))
        print("  script started   %s" % (s["scriptStarted"] or "no"))
        if s["aborted"]:
            print("  ABORTED          line %s  [%s] %s"
                  % (s["abortLine"], s["abortKind"], (s["abortText"] or "")[:90]))
        if s["undeclared"]:
            print("  undeclared       %s" % s["undeclared"])
        print("  report           %s" % ("present" if s["reportPresent"] else "ABSENT"))
        if s["exception"]:
            cur = s.get("exceptionIsCurrent")
            print("  exception log    %s" % safe(s["exception"], 78))
            print("                   kind=%s at=%s blocks=%d%s"
                  % (s["exceptionKind"] or "runtime", s.get("exceptionTime") or "?",
                     s.get("exceptionBlocks", 0),
                     "" if cur else "   <- NOT THIS RUN (older than the run log); "
                                      "this run raised no exception"))
        print("  last line        %s" % safe(s["lastLine"], 100))

    if not s["logPresent"]:
        return 3

    want = {"log": s["logPresent"],
            "loader": s["loaderFinished"],
            "script": bool(s["scriptStarted"]),
            # Finalize is only provable by its effect: the report it writes.
            "finalize": s["reportPresent"],
            "report": s["reportPresent"]}
    missing = [k for k in args.require if not want.get(k)]
    if missing:
        if not args.json:
            print("\n  NOT REACHED: %s" % ", ".join(missing))
            print("  The run happened and did not get that far. That is a real result,")
            print("  not a harness problem, and it does not need re-running to confirm.")
        return 1

    if args.gen_key:
        # A generator run that reached Finalize and created nothing is NOT a
        # pass, and it is the single most likely way this phase could report
        # green while the environment still does not exist. So the gate asks the
        # report for the number, not for its existence.
        created = None
        if GEN_REPORT.exists():
            try:
                created = int(json.loads(GEN_REPORT.read_text(encoding="utf-8")).get("records_created", 0))
            except Exception as e:
                print("  UNREADABLE generator report: %s" % e)
                return 1
        if not created:
            if not args.json:
                if created is None:
                    print("\n  NOT MET: no generator report exists, so nothing was created OR measured.")
                    print("  Run tools/run_gen.ps1 -Collect; do not read this as a pass.")
                else:
                    print("\n  NOT MET: the generator report declares records_created = %d" % created)
                    print("  The generator ran and wrote its report, and created no record.")
                print("  Either way this is a real result about a real gap -- not a pass,")
                print("  and not something to re-run hoping for a different answer.")
            return 1
        if not args.json:
            print("  OK  generator created %d record(s)" % created)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


