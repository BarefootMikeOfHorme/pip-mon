# F2 — Truth and honesty

**Goal:** the surface stops reporting success when it did not succeed.

**Why first.** `ai_context/goal_alignment.md` is blunt about the build gate:
*"That is build integrity. It is not goal coverage."* A fully green gate is
consistent with S0 unproven, the facility plugin at 0 records, and no xEdit run
ever producing a report. The owner is braced for that explosion. This family is
the other half of it — **nine places `tools/pipmon.ps1` currently reports success
or the wrong status**, all verified firsthand against the source on 2026-10-03.

Nine is the number. Not "a vague risk" — nine, each with a line number, each
independently fixable and independently revertable.

## State

| id | defect | state |
|---|---|---|
| **F2.1a** | `$EXIT` lookup is not total — an unknown status keeps the previous value | **FIXED** `e103b6e` |
| **F2.1b** | what `ATTENTION` *means* in the vocabulary | **owed to the owner** |
| **F2.6** | `caps` advertises `-Enable`/`-Disable` that the entry point did not accept | **FIXED** `e103b6e` |
| F2.2 | `snapshot` returns GREEN having copied nothing | **FIXED** `c27a0b4` |
| F2.5 | `link` reports a missing precondition as RED | open — needs a decision, see below |
| F2.7 | `docs` advertises a file that does not exist | **FIXED** `c27a0b4` |
| F2.3 | `status` decides its verdict from unrefreshed report files | open |
| F2.4 | `verify` cannot return SKIP or BROKEN | open |
| F2.5 | `link` reports a missing precondition as RED | open — needs a decision, see below |
| F2.8 | `surfaces.json` lists a `compat` verb that exists in no code path | **FIXED** `0063a22` — closed by **serving** the verb, not deleting the claim |
| F2.9 | `plans.schema.json` documents enforcement that does not exist | open |
| F2.10 | `caps` has no `provenance` block, violating its own invariant | open |
| **F2.11** | the "no writes outside" invariant omits `ck-session prepare` | **FIXED** `0063a22` |
| **F2.12** | `validate` exits 0 when validation FAILS | open — F2.1a made it loud, not right |
| **F2.13** | `ck_session.ps1` writes the proposal as ASCII and reads `plugins.txt` with the ANSI codepage | **FIXED** `bae7d00` — the bug `2ad0485` fixed in `linksync.ps1`, still live here |

**7 of 14 closed.** Two are deliberately not defects-yet: **F2.1b** is a contract
decision owed to the owner, and **F2.5** needs a change inside `linksync.ps1`
before the surface can tell a thrown precondition from a wrong result.

**F2.1a was a net, not a fix, and the distinction matters.** After it, `validate`
on a FAIL exits **2 — loud instead of silent** — but it should be **RED/1**,
because the validation ran and the plugin was wrong. Making it right is F2.12.
Conflating the two is how a safety net gets mistaken for a fix.

**F2.5 is not a one-liner and is deliberately deferred.** `linksync.ps1` signals
both "precondition missing" and "wrong result" by exit 1, so the surface cannot
currently tell them apart. Mapping exit 2 to BROKEN is done; distinguishing a
thrown precondition needs `linksync.ps1` to report which case it was. That is a
change in another file and belongs in its own cycle.

## The defects

Every line number verified by reading `tools/pipmon.ps1` on 2026-10-03. Not
inherited from a handover.

### F2.12 — `validate` exits 0 when validation FAILS · **found during F2.0 research**

```
 83: $EXIT = @{ GREEN = 0; OK = 0; RED = 1; BROKEN = 2; SKIP = 3 }
275:  Emit $rep.status ...        # $rep.status passed straight through
```

`validate_plugin.ps1` writes **only** `PASS`, `FAIL` or `SKIP` — an exhaustive
set across its 18 report sites. `$EXIT` contains **none** of the three. So
`$EXIT['FAIL']` is `$null`, `exit $null` is **0**, and a failed validation
returns `"status":"FAIL","ok":false` with **exit 0**.

Line 212 proves the author knew `PASS` existed: `-notin 'PASS','GREEN'`.

**This is the same bug class as F2.1 but worse**, because the value comes from a
child tool's documented vocabulary rather than from a typo. `ATTENTION` was
emitted by mistake; `PASS`/`FAIL` are what the validator has always written.

**This is why F2.1 must be split.** The real defect is not "add `ATTENTION = 1`"
— that presupposes what `ATTENTION` means, which is the owner's call. The real
defect is that **`$EXIT[$status]` has no default**, so *every* unrecognised
status resolves to 0. Making the table **total** is a bug fix, separable from the
contract decision. See [`VOCABULARY.md`](VOCABULARY.md).

## F2.1, restated after the research

> **`$EXIT[$status]` on an unrecognised key returns `$null`, and `exit $null` is 0.
> An unrecognised status is currently a PASS.**

Values already reaching it with no key: `ATTENTION` (207/208/213), `PASS` and
`FAIL` (275), `NOT RUN` (205/206), `UNKNOWN` (via `agent_watchdog`), and any exit
≥ 4 from `:237` (map covers 0–3 only).

**Two separable fixes:**

- **F2.1a — make the table total.** A default arm, so an unknown status cannot
  become 0. This is a bug fix, not a contract decision, and it is not blocked on
  the owner.
- **F2.1b — decide what `ATTENTION` is.** Still owed. Not started, deliberately.

**Why 1a must land before any state is added:** until the `$null` path is closed,
adding a state adds a *new silent-PASS path* rather than an honest answer. The
ordering constraint is in `VOCABULARY.md`.

## F2.1 — the exit table has no `ATTENTION` key

```
 83: $EXIT = @{ GREEN = 0; OK = 0; RED = 1; BROKEN = 2; SKIP = 3 }
107:     $script:surfaceExit = $EXIT[$status]
207:         deploy = if ($dep.exit -eq 0) { 'GREEN' } else { 'ATTENTION' }
208:         link   = if ($link.exit -eq 0) { 'GREEN' } else { 'ATTENTION' }
213:         elseif ($states.deploy -ne 'GREEN' -or $states.link -ne 'GREEN') { $overall = 'ATTENTION' }
```

`status` **produces** `ATTENTION` at 207, 208 and 213. `$EXIT['ATTENTION']` is
`$null`. `exit $null` is exit **0**.

**So a failed deploy verification exits 0, with `"ok": false` in the envelope.**
A caller that branches on exit code — which is the entire point of the exit-code
contract — reads it as success. This is reachable whenever the game folder is
absent, because `verify_deploy.ps1` exits 1 on that path.

**Why it is the worst:** every other defect is a wrong answer. This one is a
right answer in the wrong channel, which means the JSON says one thing and the
exit code says the opposite, and the two are both documented as authoritative.

### F2.2 — `snapshot` returns GREEN having copied nothing

```
310:  foreach ($f in @('Data\PipMonTestFacility.esp', ...)) {
312:      if (Test-Path -LiteralPath $src) { ... $taken += ... }
318:  }
329:  Emit 'GREEN' "snapshot '$what' taken" ([ordered]@{ ...; files = $taken })
```

The `Test-Path` guard is inside the loop. The `Emit` is outside it. With no game
folder: `$taken = @()`, and the surface returns **exit 0, `GREEN`, `"files": []`**
with the reason string *"snapshot taken"*. Nothing anywhere distinguishes
"nothing to snapshot" from "nothing was deployed".

### F2.3 — `status` decides its verdict from files it never checked

```
110: function Read-Report($name) {
111:     $p = Join-Path $WatchDir $name
112:     if (Test-Path $p) { try { return Get-Content $p -Raw | ConvertFrom-Json } ... }
116: }
```

No freshness check. `status` (178–179) and `validate` (274) both read a report
file and present it as current. On this machine right now `papyrus-latest.json`
reads `GREEN` from `2026-10-01T00:08:33Z` and `xedit-latest.json` reads `SKIP`
from `2026-10-01T08:16:15Z`. **Both stale, both presented as truth.** This is the
`gate_watch` failure shape the project's own rules name: a silent drop is the
worst failure mode available to a diagnostic tool, because the tool's output is
trusted.

### F2.4 — `verify` cannot return anything but GREEN

```
235:  $r = Run-Tool 'tools\agent_watchdog.ps1' @()
237:  Emit (@{ 0 = 'GREEN'; 1 = 'RED'; 2 = 'BROKEN'; 3 = 'SKIP' }[$r.exit]) `
```

`tools/agent_watchdog.ps1` contains **no `exit` statement**, so `powershell
-File` returns 0 on normal completion → `GREEN`. Two further consequences:

- Any exit **above 3** is not in the map, so the lookup is `$null`, and
  `$EXIT[$null]` is `$null` → **exit 0**. So `verify` can never return SKIP or
  BROKEN.
- The `reason` string at 238 is a **constant**. The envelope cannot report
  "broken", only "dashboard regenerated".
- `@()` passes no `-GameDir`, so `pipmon.ps1 verify -GameDir X` silently ignores X.

### F2.5 — `link` reports a missing precondition as RED

```
259:  $r = Run-Tool 'tools\linksync.ps1' (@($sub, '-GameDir', $GameDir))
264:  $status = if ($r.exit -eq 0) { 'GREEN' } else { 'RED' }
```

`linksync.ps1:60` — `if (-not (Test-Path $PluginTxt)) { throw ... }`. Under
`$ErrorActionPreference = 'Stop'` with no catch, that is an uncaught terminating
error → child exit 1 → `RED`.

But RED means *"the thing ran and is wrong"*, and the truth is *"a precondition
is missing"*, which the contract itself defines as **BROKEN** at line 39. This
defect inverts the meaning of the vocabulary.

### F2.6 — `caps` advertises a `link` capability that does not exist

```
148:  @{ n = 'link'; does = '...'; args = @('status', '-Disable <plugin>', '-Enable <plugin>') }
259:  $r = Run-Tool 'tools\linksync.ps1' (@($sub, '-GameDir', $GameDir))
```

`$Enable` and `$Disable` are **declared as parameters and never forwarded.** They
are silently dropped. `caps` is the discovery document — the thing a caller reads
to learn what it can do — and it advertises two arguments that do nothing.

**But the feature exists and works.** `linksync.ps1` declares `[string[]]$Enable`
and `[string[]]$Disable` at lines 45-46 and implements both at 147-155, with the
snapshot taken *before* apply at line 132. So this is not a missing capability,
it is a **dropped wire**: one argument list stands between a working toggle and
the surface.

Which makes it load-bearing for a separate reason. The owner's compiled-
environment model — toggle compiled plugins from the terminal instead of
recompiling — is *exactly this code path*. The mechanism is already written and
tested; only the forwarding is missing. See
[`F4-surface-content/PLAN.md`](../F4-surface-content/PLAN.md).

### F2.7 — `docs` advertises a file that does not exist

Line 457 advertises `'this surface, in prose' = 'PIPMON_INTERFACE.md'`.
**That file does not exist.** The other 12 door targets exist.

### F2.8 — `surfaces.json` lists a verb that exists in no code path

`ai_context/spec/surfaces.json:33-46` enumerates **twelve** verbs including
`compat`. `pipmon.ps1:474` returns `BROKEN / unknown command` for it. And
`surfaces_gate.py`'s whole job is "every claimed path exists" — so the surface
list and its own gate disagree.

### F2.9 — `plans.schema.json` documents enforcement that does not exist

`ai_context/plans/schema.json` — *"requires: invariant ids … The orchestrator
refuses to start if one is not."* `tools/orchestrate.py:530-531`:

```python
if plan.get("requires"):
    print("  requires invariants: %s" % ", ".join(plan["requires"]))
```

**It prints it.** Nothing checks it. This is the second instance of the same
pattern in the tree — a `requires` field declared and not enforced — and the
first is `tasks/capabilities.json`'s, which *is* enforced by `taskrun.ps1:508`.
Worth noting the contrast, because it shows the pattern is known and applied
inconsistently rather than being a gap in understanding.

### F2.10 — `caps` has no `provenance` block, violating its own published invariant

`caps` does not go through `Emit`. It writes its own literal at 172 and sets
`$script:surfaceExit = 0`. So it has **no `status`, no `ok`, no `reason`, no
`provenance`** — while publishing, at line 161, the invariant *"Every fact in a
response names the script or file it came from."* The discovery document breaks
the rule it publishes.

### F2.11 — the "no writes outside" invariant has a hole

`caps` line 162: *"No command writes to the game folder except build (deploy) and
link apply."* `ck-session prepare` writes **`%LOCALAPPDATA%\Fallout4\
plugins.txt.proposed.txt`** — outside the project, outside the game folder, and
not named. The invariant is true as written and misleading as read.

## Fix order, and why

| id | fix | class | why here |
|---|---|---|---|
| **F2.1** | add `ATTENTION` to `$EXIT` | A, 1 line | worst; every caller is wrong until it lands |
| **F2.2** | `snapshot` reports what it took | A, 3 lines | silent success is the named worst failure shape |
| **F2.3** | `Read-Report` gains a freshness check | B, new `.2` variant | touches the one function two verbs trust |
| **F2.4** | `verify` gets a real verdict | B | needs `agent_watchdog.ps1` to have an exit first |
| **F2.5** | `link` maps missing-precondition to BROKEN | A | inverts the vocabulary |
| **F2.6** | forward `-Enable`/`-Disable`, or stop advertising them | A | a lie in the discovery document |
| **F2.7** | point `docs` at a file that exists | A, 1 line | trivial |
| **F2.8** | remove `compat` from `surfaces.json` | A, 1 line | the gate and the spec should agree |
| **F2.9** | either enforce `requires` or stop claiming it | B | pick one; claiming is worse |
| **F2.10** | route `caps` through `New-Envelope` | B | removes the self-violation |
| **F2.11** | name the third writer in the invariant | A, 1 line | honesty in the contract text |

**A note on F2.1 specifically.** The obvious one-line fix — add
`ATTENTION = 1` — is *wrong on its own*, because `ATTENTION` currently means
"a deploy or link check did not pass", which is closer to RED's meaning than
GREEN's. The honest fix is to decide what `ATTENTION` *is*, in the vocabulary,
before assigning it a number. Candidate: `ATTENTION = 1` alongside RED, with the
distinction carried in the `reason` — or fold it into RED and stop emitting it.
**That is a contract decision and it belongs to the owner.** It is recorded here
rather than guessed, because guessing it is how the exit-code table becomes
unreliable in a second way.

## The rule this family exists to enforce

Non-negotiable #1: **SKIP is never PASS.** Non-negotiable #4 from the
consolidated spec: **G4 — fail loudly and specifically, or not at all**, because
*"silent degradation is the worst failure mode available to a diagnostic tool,
as the tool's output is trusted."*

Nine defects is the concrete measure of how far the surface currently is from
both. Each fix is one commit, individually revertable, with a diff you can read.
