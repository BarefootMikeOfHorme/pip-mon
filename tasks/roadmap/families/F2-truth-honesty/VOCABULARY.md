# F2.0 — Status and exit vocabulary research

Written 2026-10-03, before changing anything. The owner's instruction: more than
one state will be needed as the program matures, so **research what the program
could or would need and validate each idea for use and helpfulness before doing
anything.** This is that research.

Nothing here is applied. Every claim is from reading, with `file:line`.

## The finding that reorders F2

> **`$EXIT[$status]` on an unrecognised key returns `$null`, and `exit $null` is 0.
> An unrecognised status is currently a PASS.**

`tools/pipmon.ps1:107` — `$script:surfaceExit = $EXIT[$status]`, and `$EXIT`
(`:83`) is a plain hashtable with no default.

Values already reaching it that have no key:

| value | emitted at | consequence |
|---|---|---|
| `ATTENTION` | `:207`, `:208`, `:213` | `$null` → **exit 0** |
| `PASS` | `:275`, from `validate_plugin.ps1` | `$null` → **exit 0** |
| `FAIL` | `:275`, from `validate_plugin.ps1` | `$null` → **exit 0** |
| `NOT RUN` | `:205`, `:206` | `$null` → **exit 0** |
| `UNKNOWN` | via `agent_watchdog.ps1:122`, `:199` | `$null` → **exit 0** |
| any exit ≥ 4 | `:237` (map covers 0–3 only) | `$null` → **exit 0** |

**`pipmon validate` exits 0 when validation FAILS.** `validate_plugin.ps1` only
ever writes `PASS`, `FAIL` or `SKIP` — that set is exhaustive across its 18
report sites. `$EXIT` contains none of the three. So a failed validation
produces `"status":"FAIL","ok":false` and **exit 0**. Line 212 proves the author
knew `PASS` existed: `-notin 'PASS','GREEN'`.

This reframes F2.1. The fix is **not** "add `ATTENTION = 1`" — that presupposes
what `ATTENTION` means, which is genuinely the owner's call. The fix is that
**the table must be total**: an unknown status may never resolve to 0. Those are
separable, and only the second is a bug rather than a contract decision.

## The project already has 18 status vocabularies

The 5-state table is not the only one, and it is not the largest.

| axis | vocabulary | where | linted? |
|---|---|---|---|
| run verdict | `GREEN/OK/RED/BROKEN/SKIP` | `pipmon.ps1:29,37-41` | **no** |
| per-check | `PASS/FAIL/SKIP/UNKNOWN` | `envgate.py:74-80` | no |
| aggregate gate | `PASS/PARTIAL/FAIL` → `0/1/3` | `envgate.py:989-1005` | no |
| task step | `DONE/PROXY/PENDING` | `taskrun.ps1:333-342` | no |
| evidence authority | 7 tiers, weights 2.6→0.35 | `schema.json:13-21`, `ranking.json:7-13` | no |
| compat coverage | 6 values | `schema.json:175-188` | **yes** — `spec_lint.py:172-195` |
| side invariant | `MET/NOT_MET/UNVERIFIED/NOT_APPLICABLE` | `side_invariants.json:8-13` | **yes** — `side_gate.py` |
| surface maturity | `MET/PARTIALLY_MET/DECLARED/NOT_MET/UNVERIFIED` | `surfaces.json:8-14` | **yes** — `surfaces_gate.py:69` |
| doc freshness | `CURRENT/PARTLY_FIXED/STALE/SUPERSEDED/BUILT` | `door_registry.json:8-14` | **yes** — `door_lint.py` |
| plan progress | 9 `level=` values | `orchestrate.py:533-735` | no |
| protocol profile | `OBSERVE/HUMAN/ASSIST/MACHINE` | `PIPMON_EVAL_NOTES6.md:534-538` | no |
| autonomy ladder | `observe/propose/apply-reversible/confirm` | `NOTES6.md:347` | no |
| risk class | `read/reversible/irreversible` | `NOTES6.md:346` | no |
| proposed exits | adds `5 BUSY`, `6 NEEDS_AUTHORITY` | `NOTES6.md:418` | no |
| concurrency | `0 PASS/1 FAIL/2 BROKEN/3 SKIP/4 RUNNING/5 LOCKED` | `validate_plugin.ps1:42-48`, `run_gen.ps1:40-45` | no |
| human consent | `0 APPROVED/2 BROKEN/3 DECLINED` | `approve.ps1:18-21` | no |
| runtime liveness | 7-value `LaunchResult` incl. `Degraded` | `ProcessLaunch.hpp:55-63` | no |
| finding severity | `CRITICAL/WARN` + numeric `confidence` | `ANOMALY_RULES.md:73,77` | no |
| wire event | 11 types + 3 flags, **append-only** | `IPC_PROTOCOL.md:97-121` | no |

**Three vocabularies are linted. The one with the most readers is not.** And
`tasks/roadmap/README.md` already states the policy: *status vocabularies are
closed and reused, not reinvented.* Eighteen exist partly because nobody picked
one.

## Hypothesis: the single `status` field is carrying several orthogonal dimensions

**Confirmed.** Ten dimensions are in use somewhere; the 5-state table expresses
two of them.

| dimension | expressible today? |
|---|---|
| did it run / did it fail | ✅ `GREEN`/`RED` |
| why it could not run (something missing) | ✅ `BROKEN` |
| could not run (unverified) | ✅ `SKIP` |
| **coverage fraction** — some ran, some did not | ❌ exists as `PARTIAL`/`PROXY`/`PARTIALLY_MET` |
| **freshness** — is this report about the current tree | ❌ exists as `STALE` |
| **concurrency** — in flight, lock held | ❌ `4` collides with `usage` |
| **authority** — declined by policy or by a human | ❌ `3` already double-booked |
| **degradation** — ran, named part dark | ❌ collapsed to `RED` |
| **evidence authority** | ❌ not a surface concern, but `provenance` lives there |
| **risk class of the verb** | ❌ not in `caps` at all |

Two refutations I looked for and did not find. `SKIP` does **not** already mean
"partially covered" — `:40` defines it singularly, and the aggregate at
`:210-213` is a hand-written cascade, not a count. And `ok` is **not** a
workaround — it is derived at `:90` and **nothing in the tree reads it.**

## Who actually consumes a status

This is the part that decides everything else.

> **The exit code is the real contract. Nothing reads `ok`. Nothing reads the
> `status` string. The envelope is written by one process and parsed by no
> automated consumer in the tree.**

| consumer | reads | notes |
|---|---|---|
| `orchestrate.py:753-757` | **exit code only** | `code == 3` → `SkipItem` and keeps going; `!= 0` → `RuntimeError`. Never parses stdout |
| `orchestrate.py:335-336` | exit code → own label | `{0:GREEN,1:RED,3:STOPPED,4:IN FLIGHT}` — **`2` is absent**, so a `BROKEN` exit prints `??` |
| `gate_watch.py:83` | **exit code only** | `"GREEN" if exit == 0 else "RED"` — collapses SKIP, BROKEN, timeout 124, missing-binary 127 into RED |
| `taskrun.ps1:648` | exit code | |
| `taskrun.ps1:321` | a **status string**, from a different file | `-eq 'PASS'` — reads the xEdit report, not the envelope |
| `agent_watchdog.ps1:115` | **status string** | the only string comparison on a report status |
| `unblock_and_generate.ps1:69` | **nothing** | pipes the envelope to `Out-Null` |
| `envgate.py` | **its own enum** | does not read the pipmon envelope at all |
| `side_gate.py:96` | — | **`return 0` unconditionally**, while printing "1 of 3 sides available" |
| `launcher/src/main.cpp:149` | — | `Ok ? 0 : 1` — `Degraded` exits the same as failure |
| the gates | exit code only | none emits a 3 |
| an AI agent | both | `SKILL.md:34-38` — a *reader*, not a program |

**Consequence:** adding a status string without a number is worse than adding
nothing, because both channels are documented as authoritative (`:35-36`: *"so a
caller can branch without parsing text"*) and only one is enforced.

## Candidate states, validated against the project's own test

The test is already written down — `schema.json:187`: **"a status nobody can
branch on is decoration."** So: does it change a caller's behaviour?

| candidate | branchable | observable | producible | changes behaviour | verdict |
|---|---|---|---|---|---|
| **`PARTIAL`** — some checks settled, some could not | ✅ | ✅ "≥1 did not run, none failed" | ✅ already at `envgate.py:1004` | ✅ caller must **not** stop; `orchestrate.py:753` already wants this | **PASSES all four** |
| **`IN_FLIGHT`** — launched detached, not finished, not failed | ✅ | ✅ pure: pid alive + job file | ✅ job files on disk now | ✅ **poll later, do not relaunch** | **PASSES** — zero judgement |
| **`BUSY`/`LOCKED`** — something holds the resource | ✅ | ✅ `Get-Process` returned something | ✅ `xedit-latest.json` right now reads `SKIP` / *"xEdit is already running (pid 127544)"* | ✅ **wait, do not stack** | **PASSES** — and the sharpest evidence `SKIP` is overloaded: a lock is not "unverified", it is "try later" |
| **`PROXY`** — all checks passed but all circumstantial | ✅ | ✅ `proxy: true` already exists | ✅ | ✅ re-attempt, do not skip | **PASSES, already implemented** in `taskrun.ps1` — needs propagation only |
| **`STALE`** — report predates the tree | ✅ | ⚠️ judgement: needs a threshold, and a threshold is policy | ❌ never today | ✅ re-run, trust nothing | **PASSES with a caveat** |
| **`NEEDS_AUTHORITY`** — valid verb, insufficient authority | ✅ | ✅ declared risk vs declared profile | ❌ not producible: `caps` emits no `risk`/`authority` | ✅ the only candidate that **prevents** a write | needed *before* the fields that produce it |
| **`REFUSED`** — precondition present, we declined | ✅ | ⚠️ judgement on the boundary | ❌ nothing emits it | ✅ do not retry, escalate a design question | **FAILS (c)** |
| **`DEGRADED`** — ran, named part dark | ✅ | ✅ probe list shorter than declared | ✅ in C++ | ⚠️ **FAILS (d)** — `main.cpp:149` throws it away | strong once a probe reports up |
| **`UNVERIFIED`** — looked, could not conclude | ✅ | ✅ distinct from "did not look" | ✅ 3 sites | ❌ **FAILS (d)** — `envgate.py:1000` folds it into the same exit 3 | a **refinement of SKIP**, not a peer state |
| **`ATTENTION`** | ❌ | ❌ **no definition exists anywhere** | ✅ accidentally | ❌ inverted | **not a candidate — a decision already owed** |

**The strongest single result: five of these already exist in the project.**
`PARTIAL`, `UNKNOWN`, `PROXY`, `STALE` and `DEGRADED` are all shipped somewhere.
None needs inventing. Each needs *reaching*.

## The project's own criterion for when two states deserve separate codes

`tools/LOG_FORMAT.md:74-79`:

> `no_listener` and `stale_client` are deliberately different codes: **collapsing
> them sends someone to restart a game that was never running. Both cost minutes
> to diagnose wrongly.**

So: **the caller's correct action differs.** Apply it and four candidates earn
their place — `PARTIAL` (keep going, re-poll the skips), `IN_FLIGHT` (poll, do
not relaunch), `BUSY` (wait, do not stack), `STALE` (re-run, trust nothing).

The eval notes already have the correct table at `NOTES6.md:418`, and it is
**additive** — `5 BUSY`, `6 NEEDS_AUTHORITY`, with 0–4 unchanged. That matches
`IPC_PROTOCOL.md:97`'s append-only rule: *"Never renumber or reorder."*

## What should a consumer do with a status it does not recognise

**There is no explicit rule.** I searched for it and it does not exist. Four
adjacent rules point the same way:

1. `gate_watch.py:92-93` — the fail-safe is to *say you do not know*: `reason =
   "gate gave no reason; exit=%d"`. `orchestrate.py:335-336` prints `??` rather
   than guessing.
2. `spec_lint.py:185-187` + `surfaces_gate.py:69-70` — for an **unclosed
   vocabulary** the safe response is a hard lint failure, not a pass. That is
   the one real precedent, and it is a build-time failure.
3. `validate_plugin.ps1:141-143` — the sharpest statement of intent in the tree.
   Same observable facts (no report produced), two different truthful claims:
   *"COMPILE failure: the script was rejected before Initialize ran. No record
   was ever read, so plugin contents are UNVERIFIED, not bad"* vs *"RUNTIME
   failure: the script compiled and started."* That is the project's own argument
   that one status cannot carry both.
4. Non-negotiable #1: **SKIP is never PASS.**

**So the safe default is non-zero and non-PASS.** Today the code does the
opposite: an unrecognised status is a pass.

## Ordering constraint — the fix sequence this implies

| step | what | class |
|---|---|---|
| **0** | **make the table total.** An unknown status may never resolve to 0. | A, 1 line |
| **1** | decide the vocabulary is a **set of axes**, not a list — and route the existing ones in | B |
| **2** | extend `caps`, never renumber 0–4 | additive |
| **3** | **give every new state a consumer in the same commit** | per state |
| **4** | extend the lint to the exit table — it currently protects three vocabularies and not the one with the most readers | B |
| 5 | only then decide which new states to admit | decision |

**Step 0 must precede step 5.** Until the `$null` path is closed, **adding a
state adds a new silent-PASS path** rather than an honest answer. That is the
whole argument for doing step 0 first, and it is independent of what `ATTENTION`
means — which is why it is not blocked on your decision.

Step 3 is the one most likely to be skipped, and `schema.json:187` is the
project's own reason not to skip it.

## Two claims worth one command each, not yet run

Both are the most consequential findings here and both are read-only-checkable:

1. `pipmon validate` exits 0 on `FAIL`. Follows from two exhaustive literal sets
   (`validate_plugin.ps1` writes only `PASS`/`FAIL`/`SKIP`; `$EXIT` has none of
   them) — but it has not been executed.
2. `powershell -File tools\agent_watchdog.ps1` exits 0 regardless, because it
   contains no `exit` statement. Asserted by reading; not run.

Running them is one call each and changes nothing on disk. Say the word.

## What this does not decide

- What `ATTENTION` means. Still yours, still owed.
- Whether the exit code should remain the primary channel. The corpus says it
  already is, by accident rather than by design — five consumers read it and
  none read the envelope. Making that deliberate is probably worth more than any
  individual state.
