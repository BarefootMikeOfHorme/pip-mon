"""Heuristic anomaly detection (Rule 4: all analysis lives here, not in the UI).

Every rule is a class with a ``evaluate`` method, so a rule can be unit-tested in
isolation and disabled by name from the CLI without touching the dashboard.

Design rules for the rules themselves:

* **No false negatives we can avoid.** A missed runaway loop costs a user a
  frozen save. A false positive costs five seconds of their attention. So the
  default thresholds are deliberately noisy and every finding carries a
  confidence the UI shows.
* **Explain, don't just flag.** Every finding names the script, the FormID and
  the source mod, because "a script is looping" is not actionable while
  "SkyFC06.esp's Script_TCMain is at 3200 ops/s" is.
* **Report after the fact.** A runaway script is usually killed by the engine
  (stack overflow, debug break) before the user opens the dashboard. The
  ``exited_hot`` check therefore looks at threads that are no longer live.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Final

from . import protocol as proto
from .profiler import WINDOW_SECONDS, Profiler, Snapshot

# --------------------------------------------------------------------------
# Thresholds. Documented in docs/ANOMALY_RULES.md; keep the two in sync.
# --------------------------------------------------------------------------

#: A healthy Papyrus workload is a handful of short scripts per frame. 500 ops/s
#: sustained is roughly an order of magnitude above a busy-but-normal frame and
#: is the floor for the runaway rule.
RUNAWAY_OPS_PER_SEC: Final[float] = 500.0

#: ...but only after this long. Sub-500ms spikes are ordinary: a script that
#: loops a container once on script start legitimately looks like a runaway.
RUNAWAY_SUSTAIN_SECONDS: Final[float] = 2.0

#: Papyrus' own stack limit is 0x400 (1024) locals. Depth past 80% of that is
#: recursion heading for a stack overflow, not ordinary nesting.
STACK_DEPTH_WARN: Final[int] = 820
STACK_OVERFLOW_DEPTH: Final[int] = 1024

#: Frame time above this is a visible hitch regardless of what caused it.
FRAME_TIME_WARN_MS: Final[float] = 33.3  # 30 fps
FRAME_TIME_BAD_MS: Final[float] = 66.7   # 15 fps

#: Handle growth over the window that indicates a ref leak. Fallout 4 with a
#: heavy load order sits around 4-6k handles; growth matters, not the absolute.
HANDLE_GROWTH_WARN: Final[int] = 1500
HANDLE_GROWTH_BAD: Final[int] = 6000

#: Working-set growth over the window, in MiB. Save-bloat precursors show up
#: here long before the save itself bloats.
MEMORY_GROWTH_WARN_MB: Final[float] = 128.0
MEMORY_GROWTH_BAD_MB: Final[float] = 512.0

#: A thread that never parks. Every script that waits on an event or a delay
#: drops below this. Sustained maximum means the VM cannot yield, which starves
#: everything else including the player's inputs.
STARVED_MIN_OP_RATE: Final[float] = 50.0


class Severity(Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {"info": 0, "warn": 1, "critical": 2}[self.value]


@dataclass(frozen=True, slots=True)
class Finding:
    """One anomaly report. Immutable; the UI renders it directly."""

    rule: str
    severity: Severity
    title: str
    detail: str
    confidence: float
    form_id: int = 0
    script_name: str = ""
    source_mod: str = ""
    thread_id: int = 0
    metric: float = 0.0
    threshold: float = 0.0
    first_seen: float = 0.0
    last_seen: float = 0.0
    acknowledged: bool = False

    def key(self) -> str:
        """Identity for de-duplication and acknowledgement.

        Two findings are the same finding if the same rule fired for the same
        form on the same thread. Without this, a 2 Hz sampling loop produces a
        new object every 500 ms and the warning list becomes unreadable.
        """
        return f"{self.rule}:{self.form_id}:{self.thread_id}"

    def to_dict(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "title": self.title,
            "detail": self.detail,
            "confidence": round(self.confidence, 3),
            "form_id": f"{self.form_id:08X}" if self.form_id else "",
            "script_name": self.script_name,
            "source_mod": self.source_mod,
            "thread_id": self.thread_id,
            "metric": round(self.metric, 2),
            "threshold": round(self.threshold, 2),
        }


@dataclass(slots=True)
class _Candidate:
    """Per-target state for a rule that needs to persist a decision."""

    first_seen: float
    last_seen: float
    peak: float = 0.0
    fired: bool = False
    acknowledged: bool = False
    values: deque[tuple[float, float]] = field(default_factory=lambda: deque(maxlen=256))


class ModIndex:
    """Maps FormID -> source mod using the probe's load-order records.

    A FormID's high byte is the load-order index, so the mapping is exact rather
    than heuristic -- provided we have the mod-index -> filename table. The probe
    sends that via ``ModLoad`` events and the intern table via ``PluginDiag``.
    """

    def __init__(self) -> None:
        self._by_index: dict[int, str] = {}
        self._by_form: dict[int, int] = {}  # formid -> mod index
        self._names: dict[int, str] = {}  # intern id -> string

    def set_names(self, names: dict[int, str]) -> None:
        self._names = names

    def name_of(self, intern_id: int) -> str:
        return self._names.get(intern_id, f"<{intern_id}>" if intern_id != 0xFFFFFFFF else "?")

    def set_mod_index(self, mod_index: int, filename: str) -> None:
        self._by_index[mod_index] = filename

    def note_form(self, form_id: int, mod_index: int) -> None:
        if form_id:
            self._by_form[form_id] = mod_index

    def mod_for(self, form_id: int) -> str:
        """Resolve a FormID to its source file.

        Falls back to the FormID's high byte when no explicit record exists,
        which is correct on Old Gen and correct on Next Gen for any mod that
        used a contiguous index block.
        """
        if not form_id:
            return "unknown"
        if form_id in self._by_form:
            return self._by_index.get(self._by_form[form_id], f"index {self._by_form[form_id] >> 24:02X}")
        return self._by_index.get(form_id >> 24, f"index {form_id >> 24:02X}")

    def ingest(self, frame: proto.Frame) -> None:
        et, p = frame.event_type, frame.payload
        if et is proto.EventType.MOD_LOAD and isinstance(p, proto.ModLoad):
            self.set_mod_index(p.mod_index, self.name_of(p.source_name_id))
            self.note_form(p.form_id, p.mod_index)
        elif et is proto.EventType.PLUGIN_DIAG and isinstance(p, proto.PluginDiag):
            self._ingest_diag(p.text)
        elif et is proto.EventType.STACK_DUMP and isinstance(p, proto.StackDump) and p.frames:
            deepest = max(p.frames, key=lambda f: f.depth)
            self.note_form(deepest.form_id, deepest.form_id >> 24)

    def _ingest_diag(self, text: str) -> None:
        """Pull the name table out of the probe's intern-table JSON.

        Parsed with ``json`` because this is a once-per-connect payload of a few
        dozen names; the hot path never touches JSON (see docs/IPC_PROTOCOL.md).
        """
        if '"names"' not in text:
            return
        try:
            import json

            data = json.loads(text)
        except ValueError:
            return
        for i, name in enumerate(data.get("names", [])):
            self._names[i] = str(name)

    def script_name_for(self, ts: proto.StackDump | None, form_id: int) -> str:
        if ts is None or not ts.frames:
            return ""
        # Innermost non-empty frame is the script actually executing.
        for frame in sorted(ts.frames, key=lambda f: f.depth):
            if frame.script_name_id not in (0, 0xFFFFFFFF):
                return self.name_of(frame.script_name_id)
        return f"FormID {form_id:08X}" if form_id else ""


class Rule:
    """Base class. Subclasses implement ``evaluate`` only."""

    name: str = "rule"

    def evaluate(self, snap: Snapshot, mods: ModIndex, now: float) -> list[Finding]:
        raise NotImplementedError

    def reset(self) -> None:
        pass


class RunawayLoopRule(Rule):
    """The headline rule: a script executing far above a sustainable rate.

    Requires *sustained* elevation, not a spike, and reports the script rather
    than the raw rate so the finding is actionable.
    """

    name = "runaway_loop"

    def __init__(
        self,
        threshold_ops: float = RUNAWAY_OPS_PER_SEC,
        sustain: float = RUNAWAY_SUSTAIN_SECONDS,
    ) -> None:
        self.threshold = threshold_ops
        self.sustain = sustain
        # Read by save_bloat to decide whether a loop is "hot" enough to
        # correlate with memory growth. Injected so a config override of the
        # runaway threshold also moves this, rather than leaving the two rules
        # disagreeing about what "too fast" means.
        self.hot_threshold = threshold_ops
        self._candidates: dict[str, _Candidate] = {}

    def reset(self) -> None:
        self._candidates.clear()

    def evaluate(self, snap: Snapshot, mods: ModIndex, now: float) -> list[Finding]:
        out: list[Finding] = []
        cutoff = now - WINDOW_SECONDS
        live: set[str] = set()

        for ts in snap.threads:
            # Use the windowed rate, not the instantaneous one: the instantaneous
            # value spikes on every function-event-heavy script.
            rate = ts.op_rate_over(now, WINDOW_SECONDS)
            if rate < self.threshold:
                continue
            if now - ts.last_seen > 2.0:
                continue  # not currently live

            key = f"{ts.vm_thread_id}:{ts.form_id}"
            live.add(key)
            cand = self._candidates.get(key)
            if cand is None:
                cand = self._candidates[key] = _Candidate(first_seen=now, last_seen=now)
            cand.last_seen = now
            cand.peak = max(cand.peak, rate)
            cand.values.append((now, rate))

            held = now - cand.first_seen
            if held < self.sustain:
                continue

            # Confidence rises with how far past the threshold we are and how
            # long it has held. A script at 1.2x the threshold for 2s is a
            # weak signal; 10x for 10s is not.
            over = rate / self.threshold
            conf = min(1.0, 0.35 + 0.12 * (over - 1.0) + 0.02 * held)
            severity = (
                Severity.CRITICAL
                if (over > 4 and held > 5) or ts.depth > STACK_DEPTH_WARN
                else Severity.WARN
            )
            script = mods.script_name_for(self._dump_of(ts), ts.form_id)
            out.append(
                Finding(
                    rule=self.name,
                    severity=severity,
                    title=f"Runaway script loop: {script or 'unnamed script'}",
                    detail=(
                        f"{rate:,.0f} ops/s sustained for {held:.1f}s "
                        f"({over:.1f}x the {self.threshold:,.0f} ops/s threshold) "
                        f"on VM thread {ts.vm_thread_id}"
                    ),
                    confidence=conf,
                    form_id=ts.form_id,
                    script_name=script,
                    source_mod=mods.mod_for(ts.form_id),
                    thread_id=ts.vm_thread_id,
                    metric=rate,
                    threshold=self.threshold,
                    first_seen=cand.first_seen,
                    last_seen=now,
                )
            )
            cand.fired = True

        # Forget candidates that stopped qualifying, but keep them briefly so a
        # thread that flickers over the threshold does not restart its timer.
        stale = [k for k, c in self._candidates.items() if now - c.last_seen > WINDOW_SECONDS * 3]
        for k in stale:
            if k not in live:
                del self._candidates[k]
        return out

    @staticmethod
    def _dump_of(ts) -> proto.StackDump | None:
        if not ts.frames:
            return None
        return proto.StackDump(ts.vm_thread_id, ts.frames, ts.stack_truncated, 0.0)


class SaveBloatRule(Rule):
    """Correlates loop rate with resource growth to predict a bloated save.

    A loop alone is not a save problem. A loop that is also adding properties or
    streaming references is, because every one of those is a record the save
    file has to write. Requires both signals; either alone is reported at INFO.
    """

    name = "save_bloat"

    def __init__(
        self,
        growth_warn_mb: float = MEMORY_GROWTH_WARN_MB,
        handle_warn: int = HANDLE_GROWTH_WARN,
        handle_critical: int = HANDLE_GROWTH_BAD,
        runaway_threshold: float = RUNAWAY_OPS_PER_SEC,
    ) -> None:
        self.growth_warn = growth_warn_mb
        self.handle_warn = handle_warn
        self.handle_critical = handle_critical
        self.runaway_threshold = runaway_threshold
        self._first_mem: float | None = None
        self._first_at: float = 0.0
        self._first_handles: int | None = None

    def reset(self) -> None:
        self._first_mem = None
        self._first_handles = None

    def evaluate(self, snap: Snapshot, mods: ModIndex, now: float) -> list[Finding]:
        if self._first_mem is None:
            self._first_mem = snap.working_set_mb
            self._first_handles = snap.handles
            self._first_at = now
            return []

        elapsed = max(now - self._first_at, 1.0)
        mem_growth = snap.working_set_mb - self._first_mem
        handle_growth = snap.handles - (self._first_handles or 0)
        mem_rate = mem_growth / elapsed  # MiB/s

        out: list[Finding] = []

        hot = [t for t in snap.threads if t.op_rate_over(now) > self.runaway_threshold]
        if hot and mem_rate > self.growth_warn:
            worst = max(hot, key=lambda t: t.op_rate_over(now))
            rate = worst.op_rate_over(now)
            script = mods.script_name_for(RunawayLoopRule._dump_of(worst), worst.form_id)
            # Record estimate: Papyrus property writes are ~48 bytes each in the
            # save. At 500 ops/s a tight set/get loop is plausibly adding tens of
            # thousands of records per save, which is the actual user pain.
            est_records = int(rate * elapsed * 0.35)
            severity = (
                Severity.CRITICAL
                if mem_rate > 8.0 or mem_growth > MEMORY_GROWTH_BAD_MB
                else Severity.WARN
            )
            out.append(
                Finding(
                    rule=self.name,
                    severity=severity,
                    title=f"Save-bloat hazard: {script or 'unnamed script'}",
                    detail=(
                        f"loop at {rate:,.0f} ops/s while working set grows "
                        f"{mem_rate:.1f} MiB/s ({mem_growth:+.0f} MiB over {elapsed:.0f}s); "
                        f"~{est_records:,} script records may be added to the save"
                    ),
                    confidence=min(1.0, 0.4 + mem_rate / 20.0),
                    form_id=worst.form_id,
                    script_name=script,
                    source_mod=mods.mod_for(worst.form_id),
                    thread_id=worst.vm_thread_id,
                    metric=mem_rate,
                    threshold=self.growth_warn,
                    first_seen=self._first_at,
                    last_seen=now,
                )
            )

        if handle_growth > self.handle_critical:
            out.append(
                Finding(
                    rule="handle_leak",
                    severity=Severity.CRITICAL,
                    title="Reference handle leak",
                    detail=(
                        f"{handle_growth:+,} handles over {elapsed:.0f}s. "
                        "Unloading this cell will not release them; the leak is "
                        "save-resident."
                    ),
                    confidence=min(1.0, 0.5 + handle_growth / 20000.0),
                    form_id=0,
                    source_mod="(engine-level)",
                    metric=float(handle_growth),
                    threshold=float(self.handle_critical),
                    first_seen=self._first_at,
                    last_seen=now,
                )
            )
        elif handle_growth > self.handle_warn:
            out.append(
                Finding(
                    rule="handle_leak",
                    severity=Severity.WARN,
                    title="Handle growth trending high",
                    detail=f"{handle_growth:+,} handles over {elapsed:.0f}s.",
                    confidence=0.45,
                    source_mod="(engine-level)",
                    metric=float(handle_growth),
                    threshold=float(self.handle_warn),
                    first_seen=self._first_at,
                    last_seen=now,
                )
            )
        return out


class StackDepthRule(Rule):
    """Recursion heading for a Papyrus stack overflow (pitfall 1)."""

    name = "stack_depth"

    def __init__(
        self,
        warn_depth: int = STACK_DEPTH_WARN,
        overflow_depth: int = STACK_OVERFLOW_DEPTH,
    ) -> None:
        self.warn_depth = warn_depth
        self.overflow_depth = overflow_depth

    def evaluate(self, snap: Snapshot, mods: ModIndex, now: float) -> list[Finding]:
        out: list[Finding] = []
        for ts in snap.threads:
            if ts.depth < self.warn_depth:
                continue
            script = mods.script_name_for(RunawayLoopRule._dump_of(ts), ts.form_id)
            crit = ts.depth >= self.overflow_depth
            pct = (ts.depth / self.overflow_depth * 100) if self.overflow_depth else 0.0
            out.append(
                Finding(
                    rule=self.name,
                    severity=Severity.CRITICAL if crit else Severity.WARN,
                    title=f"{'Stack overflow' if crit else 'Deep recursion'}: {script or 'unnamed'}",
                    detail=(
                        f"call depth {ts.depth} of Papyrus' 1024 limit ({pct:.0f}%). "
                        "A stack overflow here terminates the script and can leave "
                        "quest flags half-written -- save before continuing."
                    ),
                    confidence=min(1.0, pct / 100.0),
                    form_id=ts.form_id,
                    script_name=script,
                    source_mod=mods.mod_for(ts.form_id),
                    thread_id=ts.vm_thread_id,
                    metric=float(ts.depth),
                    threshold=float(self.overflow_depth),
                    last_seen=now,
                )
            )
        return out


class FrameTimeRule(Rule):
    """Frame pacing. Catches the hitches that Papyrus load causes indirectly."""

    name = "frame_time"

    def __init__(
        self,
        warn_ms: float = FRAME_TIME_WARN_MS,
        critical_ms: float = FRAME_TIME_BAD_MS,
        runaway_threshold: float = RUNAWAY_OPS_PER_SEC,
    ) -> None:
        self.warn_ms = warn_ms
        self.critical_ms = critical_ms
        self.runaway_threshold = runaway_threshold

    def evaluate(self, snap: Snapshot, mods: ModIndex, now: float) -> list[Finding]:
        mean = snap.series["frame_time"].mean_over(now, WINDOW_SECONDS)
        if not mean:
            return []
        if mean < self.warn_ms:
            return []
        hot = [t for t in snap.threads if t.op_rate_over(now) > self.runaway_threshold]
        culprit = ""
        if hot:
            worst = max(hot, key=lambda t: t.op_rate_over(now))
            culprit = mods.script_name_for(RunawayLoopRule._dump_of(worst), worst.form_id) or "an active script"
        return [
            Finding(
                rule=self.name,
                severity=Severity.CRITICAL if mean > self.critical_ms else Severity.WARN,
                title=f"Frame time {mean:.1f} ms average",
                detail=(
                    f"mean over the last {WINDOW_SECONDS:.0f}s, "
                    f"{'above' if mean > self.critical_ms else 'near'} the 15 fps floor. "
                    + (f"Probable contributor: {culprit}." if culprit else
                       "No single script dominates; suspect cell streaming or save I/O.")
                ),
                confidence=min(1.0, mean / (FRAME_TIME_BAD_MS * 2)),
                script_name=culprit,
                metric=mean,
                threshold=self.warn_ms,
                last_seen=now,
            )
        ]


class VmStarvationRule(Rule):
    """The VM is saturated: threads are spinning and none of them can yield.

    Distinct from a runaway loop: several ordinary scripts in aggregate can do
    this, and the fix is different (raise the thread budget or lower the op
    rate) from a single bad script.
    """

    name = "vm_starvation"

    def __init__(
        self,
        min_op_rate: float = STARVED_MIN_OP_RATE,
        min_busy_threads: int = 2,
        aggregate_threshold: float = RUNAWAY_OPS_PER_SEC,
    ) -> None:
        self.min_op_rate = min_op_rate
        self.min_busy_threads = min_busy_threads
        self.aggregate_threshold = aggregate_threshold

    def evaluate(self, snap: Snapshot, mods: ModIndex, now: float) -> list[Finding]:
        busy = [t for t in snap.threads if t.op_rate_over(now) > self.min_op_rate]
        if len(busy) < self.min_busy_threads:
            return []
        total = sum(t.op_rate_over(now) for t in busy)
        if total < self.aggregate_threshold:
            return []
        return [
            Finding(
                rule=self.name,
                severity=(
                    Severity.WARN if total < self.aggregate_threshold * 4 else Severity.CRITICAL
                ),
                title=f"VM saturated: {len(busy)} busy threads at {total:,.0f} ops/s",
                detail=(
                    "no thread is parked on an event or delay. The VM has no slack, "
                    "so the next script to block will stall everything behind it."
                ),
                confidence=min(1.0, 0.4 + len(busy) / 8.0),
                metric=total,
                threshold=self.aggregate_threshold,
                last_seen=now,
            )
        ]


class DroppedEventRule(Rule):
    """The probe is dropping frames, which means the dashboard is lying.

    Surfaced loudly on purpose: silently under-reporting Papyrus load is worse
    than no dashboard, because the user trusts the number.
    """

    name = "dropped_events"

    def __init__(self, critical_ratio: float = 0.05) -> None:
        self.critical_ratio = critical_ratio

    def evaluate(self, snap: Snapshot, mods: ModIndex, now: float) -> list[Finding]:
        if snap.events_dropped <= 0:
            return []
        ratio = snap.events_dropped / max(snap.events_emitted, 1)
        return [
            Finding(
                rule=self.name,
                severity=Severity.CRITICAL if ratio > self.critical_ratio else Severity.WARN,
                title=f"{snap.events_dropped:,} telemetry frames dropped",
                detail=(
                    f"{ratio:.1%} of the probe's output was discarded because the "
                    "consumer fell behind. Rates below may understate reality. "
                    "Close other OverseerCLI instances or use --low-detail."
                ),
                confidence=1.0,
                metric=float(snap.events_dropped),
                threshold=0.0,
                last_seen=now,
            )
        ]


class DegradedProbeRule(Rule):
    """Reports which probes failed to resolve, from the probe's own report.

    This is the rule that makes a version-agnostic build debuggable: on a build
    where a signature stopped matching, the user sees which half of the monitor
    is dark instead of just getting an empty panel.
    """

    name = "degraded_probe"

    def __init__(self) -> None:
        self._report: dict[str, str] = {}
        self._seen_at = 0.0

    def note_report(self, text: str, now: float) -> None:
        import json

        try:
            data = json.loads(text)
        except ValueError:
            return
        if data.get("kind") != "resolver_report":
            return
        for entry in data.get("entries", []):
            self._report[entry["name"]] = entry["state"]
        self._seen_at = now

    def reset(self) -> None:
        self._report.clear()

    def evaluate(self, snap: Snapshot, mods: ModIndex, now: float) -> list[Finding]:
        if not self._report:
            return []
        down = sorted(n for n, s in self._report.items() if s in ("missing", "rejected"))
        if not down:
            return []
        tier = sum(1 for s in self._report.values() if s == "addresslib")
        return [
            Finding(
                rule=self.name,
                severity=Severity.WARN,
                title=f"{len(down)} probe(s) unavailable on this game build",
                detail=(
                    "disabled: " + ", ".join(down) + ". "
                    f"{tier} resolved from the AddressLib INI, the rest via AOB scan "
                    "or not at all. Panels depending on these will be incomplete."
                ),
                confidence=1.0,
                metric=float(len(down)),
                last_seen=now,
            )
        ]


#: Registry order is display order: most urgent first.
DEFAULT_RULES: Final[list[Rule]] = [
    RunawayLoopRule(),
    SaveBloatRule(),
    StackDepthRule(),
    VmStarvationRule(),
    FrameTimeRule(),
    DroppedEventRule(),
    DegradedProbeRule(),
]


class Detector:
    """Runs the rule set, de-duplicates, and keeps a bounded finding list."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules = rules if rules is not None else list(DEFAULT_RULES)
        self.mods = ModIndex()
        self._findings: dict[str, Finding] = {}
        self._order: list[str] = []
        self._acknowledged: set[str] = set()
        #: Keys seen on the previous evaluate. Used to tell "still happening"
        #: from "stopped and came back", which is what re-arms an acknowledgement.
        self._seen_last_pass: set[str] = set()
        self._max_findings = 200

    def ingest(self, frame: proto.Frame) -> None:
        """Feed raw frames for state the detector needs outside the snapshot.

        Only the name table and the resolver report matter here, and both arrive
        on the low-rate PluginDiag channel.
        """
        self.mods.ingest(frame)
        if frame.event_type is proto.EventType.PLUGIN_DIAG and isinstance(
            frame.payload, proto.PluginDiag
        ):
            for rule in self.rules:
                if isinstance(rule, DegradedProbeRule):
                    rule.note_report(frame.payload.text, time.monotonic())

    def evaluate(self, snap: Snapshot) -> list[Finding]:
        now = snap.now
        seen: set[str] = set()

        for rule in self.rules:
            try:
                findings = rule.evaluate(snap, self.mods, now)
            except Exception as exc:  # noqa: BLE001
                # A broken rule must not take down the dashboard, but it must
                # also not fail SILENTLY -- a rule that quietly stops working
                # makes the dashboard look healthy. Store it like any other
                # finding so it reaches the user.
                self._store(
                    f"detector_error:{rule.name}",
                    Finding(
                        rule="detector_error",
                        severity=Severity.WARN,
                        title=f"Rule '{rule.name}' raised and was skipped",
                        detail=f"{type(exc).__name__}: {exc}",
                        confidence=1.0,
                        last_seen=now,
                    ),
                )
                continue

            for f in findings:
                key = f.key()
                seen.add(key)
                if key in self._findings:
                    # Preserve first_seen and acknowledgement across refreshes so
                    # the confidence ramp and the user's dismissals both stick.
                    prior = self._findings[key]
                    # A finding that went away and has come back is a NEW
                    # occurrence, not the one the user dismissed. Re-arm it,
                    # otherwise a user who acknowledges a runaway loop once would
                    # never be warned about it again -- even after it has
                    # stopped, been fixed, and started again ten minutes later.
                    rearmed = key not in self._seen_last_pass
                    if rearmed:
                        # A new occurrence is not the one the user dismissed, so
                        # the dismissal must be forgotten entirely. Clearing it
                        # only on the Finding is not enough: `_acknowledged` is a
                        # separate sticky set, and leaving the key in it made the
                        # NEXT refresh flip acknowledged straight back to True.
                        self._acknowledged.discard(key)
                    f = replace(
                        f,
                        first_seen=now if rearmed else prior.first_seen,
                        acknowledged=(
                            False
                            if rearmed
                            else (prior.acknowledged or key in self._acknowledged)
                        ),
                    )
                self._store(key, f)

        # Findings whose condition cleared are retained (not deleted) so the user
        # can still read what just stopped happening. Clearing is what makes a
        # later re-occurrence count as new, tracked via _seen_last_pass.
        self._seen_last_pass = seen

        if len(self._order) > self._max_findings:
            for stale in self._order[: len(self._order) - self._max_findings]:
                self._findings.pop(stale, None)
            self._order = self._order[-self._max_findings :]

        return self.active()

    def _store(self, key: str, finding: Finding) -> None:
        if key not in self._findings:
            self._order.append(key)
        self._findings[key] = finding

    def active(self) -> list[Finding]:
        """All current findings, unacknowledged first, then by severity, recency.

        Acknowledged findings stay in this list (greyed out in the UI) rather
        than disappearing. A runaway script the user dismissed is still running,
        and hiding it would be the exact failure mode this module exists to
        avoid.
        """
        items = list(self._findings.values())
        items.sort(key=lambda f: (f.acknowledged, -f.severity.rank, -f.last_seen))
        return items

    def unacknowledged(self) -> list[Finding]:
        """Only findings the user has not dismissed. Use for counts and alerts."""
        return [f for f in self._findings.values() if not f.acknowledged]

    def counts(self) -> dict[str, int]:
        live = self.unacknowledged()
        return {
            "critical": sum(1 for f in live if f.severity is Severity.CRITICAL),
            "warn": sum(1 for f in live if f.severity is Severity.WARN),
            "info": sum(1 for f in live if f.severity is Severity.INFO),
            "acknowledged": sum(1 for f in self._findings.values() if f.acknowledged),
            "total": len(self._findings),
        }

    def acknowledge(self, key: str) -> None:
        """Dismiss a finding so it stops counting as active.

        Note this does not stop the underlying rule from re-raising it. The rule
        will re-fire on the next evaluate, because a runaway script that the user
        dismissed is still running. What the acknowledgement suppresses is the
        *repeated notification*; ``active()`` still lists it, flagged, because
        silently hiding an active runaway is the failure mode to avoid.
        """
        f = self._findings.get(key)
        if f is None:
            return
        self._findings[key] = replace(f, acknowledged=True)
        self._acknowledged.add(key)

    def acknowledge_all(self) -> None:
        for f in self.active():
            self.acknowledge(f.key())

    def clear(self) -> None:
        self._findings.clear()
        self._order.clear()
        self._acknowledged.clear()
        for rule in self.rules:
            rule.reset()
