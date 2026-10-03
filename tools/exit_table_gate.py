"""Exit-table gate: every status the surface can emit has a key in $EXIT.

THE DEFECT THIS EXISTS FOR
    tools/pipmon.ps1 line 101 declares
        $EXIT = @{ GREEN = 0; OK = 0; RED = 1; BROKEN = 2; SKIP = 3 }
    and line 153 consumes it as $script:surfaceExit = $EXIT[$status].

    On a missing key PowerShell does not return $null, as the F2 plan assumed.
    It raises a NON-TERMINATING NullArrayIndex, so the assignment is SKIPPED and
    $surfaceExit keeps whatever it already held -- which is 0, set at line 119.
    A failed deploy verification exited 0, with "ok": false in a clean envelope
    on stdout and the error on stderr, so nothing looked wrong. e103b6e added a
    guard inside Emit that turns this into BROKEN. The guard is a net, not a fix,
    and a net catches only what someone thought to wrap in it.

THE RULE
    A status string is safe only if it is a key in $EXIT. So this finds every
    status any code path can reach Emit with, and reports the ones with no key.
    The vocabulary is closed and this refuses to widen it: inventing a status is
    the owner's decision (F2.1b), not a gate's.

HOW IT FINDS THEM, AND WHY IT IS NOT SIMPLY A GREP FOR Emit '...'
    The interesting statuses are not literals. `$overall` is assigned from four
    different branches; `$status` is assigned thirteen times in the same file.
    So for each Emit call the candidate set is resolved from the variable's
    assignments INSIDE ITS OWN switch case, because $status in `build` and
    $status in `validate` are different facts that happen to share a name.

    Two rules keep it from crying wolf, and both were needed here:

    1. An if/elseif/else chain with a terminal else REMAPS. In `build`,
         $status = if ($rep) { $rep.status } else { 'BROKEN' }
         if     ($status -eq 'GREEN') { $status = 'GREEN' }
         elseif ($status -eq 'RED')   { $status = 'RED' }
         else                         { $status = 'BROKEN' }
       is exhaustive, so whatever papyrus-latest.json said -- including
       UNKNOWN, which watch_papyrus.ps1:190 does write and which is NOT in
       $EXIT -- is BROKEN by the time it reaches Emit. Reading the first
       assignment alone would report a defect that does not exist.
    2. A report file's status vocabulary is read from the tool that WRITES the
       report, not guessed. validate_plugin.ps1 is the writer of
       xedit-latest.json and its Write-Report call sites yield exactly
       {PASS, FAIL, SKIP}. That is how the `validate` defect below is proved
       rather than assumed.

KNOWN DEFECTS, REPORTED AND NOT FAILED
    Four findings are real, already documented with an ID in the repository, and
    live in tools/pipmon.ps1, which this agent does not own. They are printed on
    every run and are listed in ACKNOWLEDGED below with their provenance.
    Failing the build on them would mean a permanently red gate, and a gate
    that is always red is decoration with better manners. `--strict` fails on
    them; that is how the table is emptied rather than argued with.

      ATTENTION   F2.1b  emitted at :260, meaning UNDECIDED and owed to the owner
      PASS        F2.12  validate_plugin.ps1's report vocabulary, unmapped
      FAIL        F2.12  same, and it should be RED/1 rather than BROKEN/2
      caps        F2.10  a hand-built envelope that bypasses New-Envelope
      default     --     a hand-built envelope claiming BROKEN while exiting 4,
                          which the contract says are different facts. NO ID: this
                          is a finding, not a tracked defect.

WHAT IT DOES NOT DO
    It does not run any verb. It cannot tell you that `compat` works, only that
    every status it could emit is declared. R9 smoke-tested 9 verbs at baseline.

    python tools/exit_table_gate.py
    python tools/exit_table_gate.py --json
    python tools/exit_table_gate.py --strict
    python tools/exit_table_gate.py --self-test
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PIPMON = REPO / "tools" / "pipmon.ps1"
TOOLS = REPO / "tools"

RE_EXIT_TABLE = re.compile(r"^\$EXIT\s*=\s*@\{([^}]*)\}", re.M)
RE_EXIT_ENTRY = re.compile(r"(\w+)\s*=\s*(-?\d+)")
RE_CAPS_EXITCODES = re.compile(r"exitCodes\s*=\s*\[ordered\]@\{(.*?)\}\s*\n", re.S)
RE_CASE_HEAD = re.compile(r"^    (?:'([a-z][a-z-]*)'|default)\s*\{", re.M)
RE_LITERAL = re.compile(r"'([A-Za-z_][A-Za-z0-9_]*)'")
# The contract's status list is written as a JSON-ish pipeline of double-quoted
# words -- `"GREEN" | "RED" | "SKIP" | "BROKEN" | "OK"` -- so it needs its own
# pattern. PowerShell source literals are single-quoted and are matched by
# RE_LITERAL, which must NOT grow double quotes: it also scans assignment
# right-hand sides, where a double-quoted path would arrive as a status.
RE_DQ_LITERAL = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"')

# Which file WRITES each report pipmon.ps1 reads. Discovered by reading
# Read-Report's call sites and matching the report file name against the
# assignments in tools/*.ps1, then confirmed by eye against validate_plugin.ps1
# (line 63) and watch_papyrus.ps1 (line 52).
REPORT_PRODUCERS = {
    "xedit-latest.json": "tools/validate_plugin.ps1",
    "papyrus-latest.json": "tools/watch_papyrus.ps1",
}

RE_REPORT_WRITE = re.compile(r"Write-Report\s+'([A-Z][A-Z_]*)'")
RE_SAVE_REPORT = re.compile(r"Save-Report\s+'([A-Z][A-Z_]*)'")
RE_SWITCH_ARM = re.compile(r"^\s+\d+ \{ '([A-Z_]+)' \}", re.M)

# ---------------------------------------------------------------------------
# KNOWN DEFECTS, REPORTED AND NOT FAILED.
#
# Keyed by the status word or the envelope tag, NOT by a line number. A line
# number would be a lie within a week: tools/pipmon.ps1 went from 667 to 800
# lines under this gate while it was being written, by another agent's commit,
# and every hard-coded line in an earlier draft of this file became wrong. The
# gate computes WHERE from the code it is reading; only the judgement and the
# provenance are recorded here.
#
# Each is real, already documented with an ID, and lives in a file this agent
# does not own. Failing the build on them would mean a permanently red gate, and
# a gate that is always red is decoration with better manners. `--strict` fails
# on them: that is how the table is emptied rather than argued with.
# ---------------------------------------------------------------------------
ACKNOWLEDGED_STATUS = {
    "ATTENTION": ("F2.1b",
                  "assigned to $overall and passed to Emit. Its MEANING is undecided "
                  "and owed to the owner, which is precisely why no gate may quietly "
                  "declare it: policy section 6 forbids inventing a status"),
    "PASS": ("F2.12",
             "validate_plugin.ps1 writes PASS into xedit-latest.json and `validate` "
             "passes $rep.status to Emit with no key for it. Must be MAPPED onto the "
             "surface vocabulary, not caught by the guard inside Emit"),
    "FAIL": ("F2.12",
             "as PASS, and worse: it should land on RED/1, because the validation ran "
             "and the plugin was wrong. BROKEN/2 claims a missing precondition"),
}

ACKNOWLEDGED_ENVELOPE = {
    "caps": ("F2.10",
             "`caps` writes its own JSON with ConvertTo-Json and never calls "
             "New-Envelope, so it carries no status, no ok and no provenance, and "
             "nothing it emits reaches $EXIT"),
    "default": ("(none)",
                "a hand-built envelope claiming status BROKEN while $surfaceExit is 4. "
                "The contract at the top of the file says BROKEN is 2 and that 4 is "
                "usage, so the envelope and the exit code are asserting different "
                "facts about the same event. NO tracking ID exists for this: it is "
                "reported here for the first time"),
}


def declared_statuses(text):
    """The contract's own status list, read from the header comment rather than
    hardcoded here. If the contract changes, this gate follows it."""
    m = re.search(r'^\s*#\s*"status":(.*)$', text, re.M)
    if not m:
        return []
    return RE_DQ_LITERAL.findall(m.group(1))


RE_CONT = re.compile(r"\\\s*$")
RE_ELSE_CONT = re.compile(r"^\s*(?:else|elseif)\b")
RE_ARM_CONT = re.compile(r"^\s*(?:\d+|default)\s*\{")


def after_open_brace(line):
    """The part of a continuation line after its opening brace, so a condition
    mentioning a status is not mistaken for one being assigned."""
    i = line.find("{")
    return line if i < 0 else line[i + 1:]


def logical_lines(lines):
    """(first line number, text, char offset) with backtick continuations joined.

    Char offset is carried because the same text has to be located in the joined
    document to know which switch case it belongs to, and searching for the text
    would find the wrong occurrence the moment two cases looked alike."""
    out, buf, start, offset, pos = [], "", 1, 0, 0
    for i, ln in enumerate(lines, 1):
        if not buf:
            start, offset = i, pos
        continued = bool(RE_CONT.search(ln))
        body = RE_CONT.sub("", ln).strip()
        buf = (buf + " " + body).strip() if buf else body
        pos += len(ln) + 1
        if not continued:
            out.append((start, buf, offset))
            buf = ""
    if buf:
        out.append((start, buf, offset))
    return out


def first_arg(s):
    """The first argument of an Emit call, or None if this line is not one.

    Only the `(@{...}[$x])` form needs a bracket scan: it is the one argument
    containing spaces. A `$(...)` argument does NOT, because scanning on `{`
    would stop at the closing brace of an `if` inside it."""
    s = s.strip()
    if not s.startswith("Emit "):
        return None
    rest = s[4:].strip()
    if rest.startswith("(@{"):
        depth = 0
        for i, ch in enumerate(rest):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    # The hashtable plus its `[index]` and closing paren, which
                    # are the rest of this one argument.
                    return rest[:i + 1] + re.match(r"\S*", rest[i + 1:]).group(0)
        return rest
    parts = rest.split()
    return parts[0] if parts else None


def exit_table(text):
    m = RE_EXIT_TABLE.search(text)
    if not m:
        return None
    return {k: int(v) for k, v in RE_EXIT_ENTRY.findall(m.group(1))}


def caps_exit_codes(text):
    m = RE_CAPS_EXITCODES.search(text)
    if not m:
        return None
    return {k: int(v) for k, v in RE_EXIT_ENTRY.findall(m.group(1))}


def report_vocabulary(report_name):
    """The status literals the producing tool writes. Read from the producer, so
    the claim carries a file:line and is not an inference about what a tool
    'probably' emits."""
    rel = REPORT_PRODUCERS.get(report_name)
    if not rel:
        return None, []
    path = REPO / rel
    if not path.exists():
        return None, ["producer %s does not exist" % rel]
    t = path.read_text(encoding="utf-8", errors="replace")
    vocab = set(RE_REPORT_WRITE.findall(t)) | set(RE_SAVE_REPORT.findall(t))
    # A tool that switches on an exit code writes its status through a variable,
    # so its switch arms are part of the vocabulary too.
    vocab |= set(RE_LITERAL.findall("\n".join(
        re.findall(r"^\s+\d+ \{ '([A-Z_]+)' \}", t, re.M))))
    return sorted(vocab), []


def case_ranges(lines):
    """(name, start, end) per top-level case of `switch ($Command)`. `$status`
    means one thing in `build` and another in `validate`, so resolution is
    scoped to a case rather than to the file."""
    heads = [(m.group(1) or "default", m.start()) for m in RE_CASE_HEAD.finditer("\n".join(lines))]
    out = []
    for i, (name, pos) in enumerate(heads):
        end = heads[i + 1][1] if i + 1 < len(heads) else len("\n".join(lines))
        out.append((name, pos, end))
    return out


def resolve_variable(var, block):
    """Candidate statuses a variable can hold when it reaches Emit.

    `block` is the case's text UP TO the Emit call, so only assignments that can
    have run are considered -- $status is assigned thirteen times in this file
    and the one in `build` says nothing about the one in `validate`.

    Returns (literals, report_flows, remapped). Three shapes occur in the
    committed file and each needs different handling:

      $status = if (...) { 'GREEN' }
                elseif (...) { 'BROKEN' }
                else { $rep.status }
    is ONE statement over three lines. Reading the first line alone reports
    {'GREEN'} and misses the report status, which is how a gate that exists to
    prevent false confidence manufactures it. PowerShell continues an `if`
    expression onto `elseif`/`else` lines with no backtick, so the statement is
    followed while those continue. A `switch` assigned to a variable continues
    onto its numbered arms, which is the same problem in a different costume.

      $status = switch ($r.exit) { 0 { 'GREEN' } ... }
      if ($r.missing) { $status = 'BROKEN' }
    the second line is CONDITIONAL. It does not overwrite, so the switch's value
    survives when it does not fire and its statuses are still reachable.

      $status = if ($rep) { $rep.status } else { 'BROKEN' }
      if ($status -eq 'GREEN') { $status = 'GREEN' }
      elseif ($status -eq 'RED') { $status = 'RED' }
      else { $status = 'BROKEN' }
    here the conditional chain IS exhaustive -- it ends in `else` -- so whatever
    the report said, including UNKNOWN which watch_papyrus.ps1:190 does write and
    which is NOT in $EXIT, is BROKEN before it reaches Emit. Reading the first
    assignment alone would report a defect that does not exist, and a gate that
    cries wolf is worse than none. Hence `remapped`.

    Conditions are stripped before literals are read: `elseif ($x -notin 'PASS',
    'GREEN')` mentions a status in a comparison, not in an assignment, and
    treating it as one put PASS in $overall's candidate set on the first run."""
    sites = []
    for li, ln in enumerate(block.split("\n")):
        for m in re.finditer(r"\$%s\s*=\s*" % re.escape(var), ln):
            prefix = ln[:m.start()]
            kind = "unconditional" if not prefix.strip() else "conditional"
            rhs = ln[m.end():]
            k = li + 1
            nxt_lines = block.split("\n")
            while k < len(nxt_lines):
                nxt = nxt_lines[k]
                if RE_ELSE_CONT.match(nxt) or RE_ARM_CONT.match(nxt):
                    rhs += " " + after_open_brace(nxt)
                    k += 1
                else:
                    break
            sites.append((kind, prefix, rhs))
    if not sites:
        return set(), [], False
    last_u = max((i for i, s in enumerate(sites) if s[0] == "unconditional"), default=None)
    if last_u is None:
        last_u = len(sites) - 1
    _kind, _prefix, base_rhs = sites[last_u]
    after = sites[last_u + 1:]
    lits = set(RE_LITERAL.findall(base_rhs))
    flows = [m.group(1) for m in re.finditer(r"\$(\w+)\.status\b", base_rhs)]
    exhaustive = (after and all(s[0] == "conditional" for s in after)
                  and re.match(r"\s*else\s*\{", after[-1][1]) is not None)
    for _k, _p, rhs in after:
        lits |= set(RE_LITERAL.findall(rhs))
        if not exhaustive:
            flows += [m.group(1) for m in re.finditer(r"\$(\w+)\.status\b", rhs)]
    if exhaustive:
        # Every value the base could hold is replaced, so a status that only ever
        # arrived through it cannot reach Emit.
        return lits, [], True
    return lits, flows, False


def check(text, report_vocab=None):
    problems = []
    acked = []

    def fail(rule, subject, detail):
        problems.append((rule, subject, detail))

    def known(rule, subject, detail):
        acked.append((rule, subject, detail))

    table = exit_table(text)
    if table is None:
        fail("no_table", "tools/pipmon.ps1",
             "no `$EXIT = @{...}` declaration found, so nothing can be checked "
             "against it and agreement would be vacuous")
        return problems, acked, {}

    published = caps_exit_codes(text)
    contract = declared_statuses(text)
    report_vocab = report_vocab or {}

    # --- parity between the table, what caps publishes, and the contract -----
    if published is None:
        fail("no_published", "tools/pipmon.ps1",
             "caps publishes no exitCodes; a discovery document with no exit "
             "vocabulary teaches a caller to parse text")
    else:
        for k, v in sorted(table.items()):
            if k not in published:
                fail("unpublished_status", k,
                     "in $EXIT with value %d but caps exitCodes does not list it" % v)
            elif published[k] != v:
                fail("value_disagreement", k,
                     "$EXIT says %d, caps exitCodes says %d; a caller branching on "
                     "one gets a different answer from a caller branching on the other"
                     % (v, published[k]))
        for k, v in sorted(published.items()):
            if k not in table and k != "usage":
                fail("published_without_table", k,
                     "caps exitCodes publishes %s = %d and $EXIT has no key for it. "
                     "`usage` is exempt because it is a usage exit, not a status: it "
                     "is set directly and never reaches Emit." % (k, v))
    if not contract:
        fail("no_contract", "tools/pipmon.ps1",
             "the header contract declares no status list, so there is nothing for "
             "the table to agree with")
    for s in sorted(contract):
        if s not in table:
            fail("contract_without_table", s,
                 "the contract at the top of the file lists it as a status but $EXIT "
                 "has no key, so a caller branching on the exit code cannot tell it "
                 "apart from an unknown status")

    # --- every status that can reach Emit ------------------------------------
    lines = text.split("\n")
    joined = "\n".join(lines)
    ranges = case_ranges(lines)

    def line_of(char_pos):
        return joined.count("\n", 0, char_pos) + 1

    seen_sites = 0
    for lineno, logical, pos in logical_lines(lines):
        arg = first_arg(logical)
        if arg is None:
            continue
        seen_sites += 1
        cands, flows = set(), []
        if arg.startswith("'") and arg.endswith("'"):
            cands.add(arg.strip("'"))
        elif arg.startswith("(@{"):
            # Emit (@{ 0 = 'GREEN'; ... }[$r.exit]) -- the values are statuses and
            # the keys are child exit codes.
            inner = arg[2:arg.index("}")]
            cands |= set(RE_LITERAL.findall(inner))
            keys = [int(x) for x in re.findall(r"(\d+)\s*=", inner)]
            if keys and max(keys) >= 4:
                known("exit_map_partial", "pipmon.ps1:%d" % lineno,
                      "the exit map covers %s and a child exit above %d yields no "
                      "status at all. F2.4: verify's map covers 0-3 only."
                      % (sorted(keys), max(keys)))
        else:
            var = arg.lstrip("$")
            scope = joined
            for _name, start, end in ranges:
                if start <= pos < end:
                    # Up to the Emit, not the whole case: $status is assigned
                    # again after several Emits in the same case, and only the
                    # assignments that can already have run say anything.
                    scope = joined[start:pos]
                    break
            cands, flows, _remapped = resolve_variable(var, scope)
            if not cands and not flows:
                known("unresolved_status", "pipmon.ps1:%d" % lineno,
                      "Emit is given $%s and no assignment to it could be read in "
                      "this case. Refused rather than guessed: an unread status is "
                      "reported, not assumed declared." % var)

        for _f in flows:
            # The report a $rep came from is named by the Read-Report call above
            # this Emit; the nearest one is the one in scope.
            names = re.findall(r"Read-Report\s+'([\w.-]+\.json)'", joined[:pos])
            if not names:
                known("unresolved_report", "pipmon.ps1:%d" % lineno,
                      "a report status reaches Emit and the report it came from could "
                      "not be named, so its vocabulary is unknown")
                continue
            rep = names[-1]
            vocab, errs = report_vocab.get(rep, (None, ["no producer is registered for %s" % rep]))
            if errs:
                fail("unreadable_producer", rep, "; ".join(errs))
                continue
            for v in (vocab or []):
                if v in table:
                    continue
                track, why = ACKNOWLEDGED_STATUS.get(v, (None, "no $EXIT key and no record of it"))
                where = "%s -> pipmon.ps1:%d" % (v, lineno)
                detail = ("%s reaches Emit from %s with no key in $EXIT: %s" % (v, rep, why))
                if track:
                    known("undeclared_status", where, detail + "  [%s]" % track)
                else:
                    fail("undeclared_status", where, detail)
        for c in sorted(cands):
            if c in table:
                continue
            track, why = ACKNOWLEDGED_STATUS.get(c, (None, "no $EXIT key and no record of it"))
            where = "%s -> pipmon.ps1:%d" % (c, lineno)
            detail = "%s reaches Emit with no key in $EXIT: %s" % (c, why)
            if track:
                known("undeclared_status", where, detail + "  [%s]" % track)
            else:
                fail("undeclared_status", where, detail)

    if not seen_sites:
        fail("no_emit", "tools/pipmon.ps1",
             "no Emit call site found; if Emit was renamed this gate is checking "
             "nothing, which is worse than reporting it")

    # --- envelopes built by hand, bypassing the table entirely --------------
    for lineno, logical, _pos in logical_lines(lines):
        m = re.match(r"Write-Output\s+([^\n]*)", logical)
        if not m:
            continue
        expr = m.group(1)
        if "New-Envelope" in expr:
            continue
        if "ConvertTo-Json" not in expr and not expr.strip().startswith(("'{", '"{')):
            continue
        tag = "caps" if "$caps" in expr else ("default" if "pipmon.surface/1" in expr else None)
        if not tag:
            continue
        track, why = ACKNOWLEDGED_ENVELOPE[tag]
        known("hand_built_envelope", "pipmon.ps1:%d (%s)" % (lineno, tag),
              "writes a JSON envelope directly instead of through New-Envelope, so no "
              "status reaches $EXIT and the provenance invariant is broken: %s  [%s]"
              % (why, track))
    return problems, acked, {"table": table, "published": published, "contract": contract}


def _vocab_from_disk():
    return {name: report_vocabulary(name) for name in REPORT_PRODUCERS}


def self_test():
    """Four states, all in memory, writing nothing. The committed file must be
    GREEN and each perturbation must be RED."""
    text = PIPMON.read_text(encoding="utf-8")
    vocab = _vocab_from_disk()
    out, ok = [], True

    def record(label, problems, acked, expect, note):
        nonlocal ok
        good = bool(problems) == expect
        ok = ok and good
        out.append((label, len(problems), len(acked), expect, good, note))

    p, a, _ = check(text, vocab)
    record("committed file", p, a, False, "tools/pipmon.ps1 exactly as committed")

    # A foreign status reaching Emit: the historical defect this whole file is
    # about, injected at the one call site whose variable is a plain assignment.
    t2 = text.replace("$status = if ($r.exit -eq 0) { 'GREEN' } elseif ($r.exit -eq 2) "
                      "{ 'BROKEN' } else { 'RED' }",
                      "$status = if ($r.exit -eq 0) { 'GREEN' } elseif ($r.exit -eq 2) "
                      "{ 'PARTIAL' } else { 'RED' }")
    p, a, _ = check(t2, vocab)
    record("PARTIAL emitted by link", p, a, True,
           "a status with no $EXIT key and no record of it; this is what a "
           "would-be silent exit 0 looks like before it happens")

    # A declaration deleted from the table: the sticky-exit mechanism, at source.
    t3 = text.replace("$EXIT = @{ GREEN = 0; OK = 0; RED = 1; BROKEN = 2; SKIP = 3 }",
                      "$EXIT = @{ GREEN = 0; OK = 0; RED = 1; SKIP = 3 }")
    p, a, _ = check(t3, vocab)
    record("BROKEN dropped from $EXIT", p, a, True,
           "every BROKEN Emit now reaches a table with no key, which is the exact "
           "shape of the silent exit 0")

    # caps and the table disagreeing about a value.
    t4 = text.replace("exitCodes  = [ordered]@{ GREEN = 0; OK = 0; RED = 1; BROKEN = 2; SKIP = 3; usage = 4 }",
                      "exitCodes  = [ordered]@{ GREEN = 0; OK = 0; RED = 1; BROKEN = 1; SKIP = 3; usage = 4 }")
    p, a, _ = check(t4, vocab)
    record("caps says BROKEN = 1", p, a, True,
           "$EXIT says 2 and caps says 1; a caller branching on one gets a "
           "different answer from a caller branching on the other")

    width = max(len(r[0]) for r in out)
    print("exit_table_gate self-test -- writes nothing; every state is in memory")
    for label, n, ak, expect, good, note in out:
        print("  [%s] %-*s  problems=%-3d known=%-3d expected=%s"
              % ("PASS" if good else "FAIL", width, label, n, ak, "RED" if expect else "GREEN"))
        print("         %s" % note)
    print("  %s: %d of %d states behaved as specified"
          % ("all" if ok else "NOT ALL", sum(1 for r in out if r[4]), len(out)))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="fail on the acknowledged findings too; this is how the "
                         "table gets emptied rather than argued with")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not PIPMON.exists():
        print("exit_table_gate: no surface at %s" % PIPMON, file=sys.stderr)
        return 2
    text = PIPMON.read_text(encoding="utf-8")
    problems, acked, meta = check(text, _vocab_from_disk())
    failed = problems + (acked if args.strict else [])

    if args.json:
        print(json.dumps({
            "schema": "pipmon.exit_table.gate/1",
            "status": "GREEN" if not failed else "RED",
            "exit_table": meta.get("table"),
            "published_by_caps": meta.get("published"),
            "contract_statuses": meta.get("contract"),
            "known": [{"rule": r, "where": s, "detail": d} for r, s, d in acked],
            "problems": [{"rule": r, "subject": s, "detail": d} for r, s, d in problems],
        }, indent=2))
        return 0 if not failed else 1

    print("exit_table_gate: %s" % PIPMON.name)
    print("  $EXIT          %s" % (meta.get("table") or {}))
    print("  caps exitCodes %s" % (meta.get("published") or {}))
    print("  contract says  %s" % (meta.get("contract") or []))
    print()
    if acked:
        print("  KNOWN, open and tracked elsewhere. Reported, not failed.")
        print("  --strict fails on these too.")
        for r, s, d in acked:
            print("    [known] %-24s %s" % (r, s))
            print("            %s" % d)
        print()
    for r, s, d in problems:
        print("  [FAIL] %-24s %s" % (r, s))
        print("         %s" % d)
    print("\nexit_table_gate: %d problems, %d known" % (len(problems), len(acked)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())