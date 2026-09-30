# Anomaly Rules

Every heuristic in OverseerCLI, with its threshold, the reasoning behind that
threshold, and how to override it. Source: `overseer_cli/detector.py`.

**All of this is consumer-side** (Rule 4). V-Probe reports op counts and thread
transitions. It has no opinion about what a good op rate is.

---

## Tuning philosophy

The asymmetry that governs every threshold here:

> **A missed runaway loop costs a user a frozen save. A false positive costs five
> seconds of their attention.**

So the defaults are deliberately noisy, and every finding carries a **confidence**
value the UI displays. A weak signal is shown weakly rather than hidden. The
detector's job is to make a user look at something once, not to be silent until it
is certain.

Three consequences worth internalising:

1. **Spikes are not signals.** A script that loops a container once on start
   legitimately looks like a runaway. Every sustained-rate rule requires a dwell
   time.
2. **Rates are computed from retained samples, never smoothed.** An exponential
   moving average stays high after a script stops, which is precisely the failure
   mode that makes a runaway detector useless when you are post-mortemming.
3. **Report after the fact.** Runaway scripts are usually killed by the engine before
   the user opens the dashboard. Findings therefore survive the condition clearing.

---

## Calibration reference

Measured on Fallout 4 1.10.980 with a heavy Next Gen load order:

| Condition | ops/s | Notes |
|---|---:|---|
| Idle in a streamed cell | 0–20 | |
| Normal dialogue / quest tick | 30–120 | |
| Workshop rebuild batch | 150–400 | brief, legitimate |
| Mod scripts doing real work | 400–600 | occasional |
| **Runaway `while` loop** | **1 500–20 000** | orders of magnitude apart |
| Per-frame script budget | ~8 000 | at 60 fps |

The gap between "busy mod" (600) and "runaway" (1500+) is why `500 ops/s` is a
sensible floor and why the detector is mostly about *sustained* elevation. A
threshold at 1000 would be more precise and would miss short-but-fatal loops that
trip a stack overflow before they reach 1000.

---

## 1. `runaway_loop` — the headline rule

**What:** a script executing far above a sustainable rate, sustained.

| Parameter | Default | Config key |
|---|---:|---|
| threshold | 500.0 ops/s | `runawayLoop.thresholdOpsPerSec` |
| sustain | 2.0 s | `runawayLoop.sustainSeconds` |
| window | 5 s | (shared) |

**Detection.**
1. For each live thread, compute `op_rate_over(5 s)` from retained `(t, opTotal)`
   samples — not the instantaneous rate, which spikes on every function-event-heavy
   script.
2. If ≥ threshold, open or update a candidate keyed `(thread, formId)`.
3. Fire when the candidate has been above threshold for ≥ `sustain` seconds.

**Confidence** = `min(1.0, 0.35 + 0.12·(over−1) + 0.02·held)` where `over` is the
multiple of threshold. A script at 1.2× for 2 s scores 0.41 (weak); one at 10× for
10 s saturates at 1.0.

**Severity:** `CRITICAL` at >4× held >5 s, or depth > 820. Otherwise `WARN`.

**Reports:** script name (from the intern table, innermost non-empty frame),
FormID, source mod resolved via the load-order index. "A script is looping" is not
actionable; "SkyFC06.esp's `Script_TCMain` at 3 200 ops/s" is.

**Tuning:** lowering the threshold flags ordinary mod scripts. If you have a heavy
load order, raise it to 800–1000 before concluding the detector is broken.

---

## 2. `stack_depth` — recursion heading for overflow

**What:** call depth approaching Papyrus' own hard limit.

| Parameter | Default |
|---|---:|
| `warnDepth` | 820 (80% of 1024) |
| `overflowDepth` | 1024 |

`0x400` = 1024 is the VM's stack limit. Depth is read from the VM thread structure;
it is **not** a native stack walk, because doing that on a game thread is exactly
pitfall 1.

**Severity:** `CRITICAL` at ≥ 1024. Confidence = `depth/1024`.

**The finding text says something the user needs:** a stack overflow terminates the
script and can leave quest flags half-written — *save before continuing*. That is
the actionable part, and it is why this rule exists separately from `runaway_loop`
rather than as a sub-case of it.

---

## 3. `save_bloat` — predicting a bloated save

**What:** a script loop that is *also* growing the process, which means it is
adding records the save file must eventually write.

A loop alone is not a save problem. A loop adding properties or streaming references
is, because every one is a record in the save.

| Parameter | Default | Config key |
|---|---:|---|
| memory growth rate | > 1.0 MiB/s | `saveBloat.workingSetGrowthMbPerSec` |
| critical growth | 8.0 MiB/s, or >512 MiB total | — |

**Requires both signals.** Either alone is reported separately at lower severity.

**Record estimate:** `rate × elapsed × 0.35`. Papyrus property writes are ~48 bytes
each in a save, and a tight set/get loop at 500 ops/s plausibly adds tens of
thousands of records. The estimate is deliberately conservative and is labelled as
an estimate.

**Severity:** `CRITICAL` at >8 MiB/s or >512 MiB growth.

The advice is always to **save to a new slot**. Never over the known-good one.

---

## 4. `handle_leak` — references that will not be released

| Parameter | Default | Config key |
|---|---:|---|
| warn | +1 500 over window | `saveBloat.handleGrowthWarn` |
| critical | +6 000 | `saveBloat.handleGrowthCritical` |

Measured from the first Memory sample. Fallout 4 sits around 4–6 k handles with a
heavy load order, so **growth** is the signal, not the absolute. A handle that is
created per cell load and never released is save-resident: it inflates every future
save, not just the current session.

**Confidence** = `min(1.0, 0.5 + growth/20 000)`.

---

## 5. `vm_starvation` — the VM has no slack

**What:** several ordinary scripts saturating the VM in aggregate, with none of them
parked on an event or delay.

| Parameter | Default | Config key |
|---|---:|---|
| min op rate per thread | 50.0 | `vmStarvation.minOpRate` |
| min busy threads | 2 | `vmStarvation.minBusyThreads` |
| aggregate threshold | 500 ops/s | — |

Distinct from `runaway_loop`: the fix is different. One bad script is a mod bug to
report; aggregate saturation is a load-order problem to tune (raise the thread
budget, or reduce the per-script op rate). Naming the distinction saves a user from
reporting "mod X is broken" when the answer is "six mods are all fine, together they
are too much".

**Severity:** `CRITICAL` above 4× the aggregate threshold.

---

## 6. `frame_time` — pacing

| Parameter | Default | Config key |
|---|---:|---|
| warn | 33.3 ms (30 fps) | `frameTime.warnMs` |
| critical | 66.7 ms (15 fps) | `frameTime.criticalMs` |

Mean over the 5 s window. If a script is above the runaway threshold it is named as
the probable contributor; otherwise the finding says so plainly and points at cell
streaming or save I/O, because a no-single-culprit hitch has a different fix.

---

## 7. `dropped_events` — the dashboard is lying to you

| Parameter | Default |
|---|---:|
| fires | any drops |
| critical | > 5% of emitted |

**Deliberately the loudest rule in the set.** If telemetry is being discarded, every
rate on screen understates reality, and the user is about to make a decision based
on those numbers.

The detail text names the remedy (close other instances, use `--low-detail`) rather
than just reporting a number. **A profiler that silently under-reports is worse than
no profiler**, because it is trusted.

---

## 8. `degraded_probe` — which half of the monitor is dark

**Consumes** the probe's own `resolver_report` JSON from the `PluginDiag` channel.

Not a heuristic — a **transparency** rule. On a game build where a signature stopped
matching, this is the difference between "no anomalies" and "no monitoring". It
names the disabled probes and reports how many resolved from the AddressLib INI
versus AOB scan.

This rule is the reason version-agnostic support is debuggable. Without it, a
signature that quietly stopped matching presents as an empty panel, and the user
concludes the game is healthy.

---

## Rule interaction

Findings are de-duplicated by `(rule, formId, threadId)` and sorted by severity, then
recency. A runaway script that is also growing memory produces two findings — a
`runaway_loop` and a `save_bloat` — deliberately. They have different owners and
different fixes.

Acknowledging a finding does **not** stop the rule re-raising it. A runaway script
the user dismissed is still running. What acknowledgement suppresses is the
repeated notification; the finding stays listed, flagged. Silently hiding an active
runaway is the failure mode to avoid.

---

## Adding a rule

1. Subclass `Rule`, set `name`, implement `evaluate(snap, mods, now) -> list[Finding]`.
2. It is registered in `DEFAULT_RULES`; ordering is display order, most urgent first.
3. Add threshold constants near the top of `detector.py` and document them here.
4. If it needs state outside the snapshot (e.g. a resolver report), add an `ingest`
   hook — do not reach into the profiler.
5. `evaluate` is called inside a `try`. A rule that raises produces a
   `detector_error` finding instead of taking down the dashboard. Write tests anyway.
6. **Ask what the user does with the finding.** If there is no action, it is noise —
   cut it.
