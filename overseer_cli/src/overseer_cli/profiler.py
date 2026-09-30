"""Rolling-window profiler for Papyrus execution.

Owns all time-series state. The TUI reads from here; it never keeps its own
copy of a counter. Keeping the window in one place is what lets a spike be
explained after the fact instead of only being displayed.

Window semantics: a fixed 5-second ring keyed on ``time.monotonic``. Every
read is O(samples in window), which is bounded and small. No numpy, because the
sample counts here are tens of thousands at worst and a dependency would cost
more than it saves.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Final

from . import protocol as proto

#: The window every panel and every detector reads from.
WINDOW_SECONDS: Final[float] = 5.0

#: Cap on retained per-thread samples. 5s at the busiest observed rate
#: (~2 kHz) is 10k samples; the bound stops a long session from growing without
#: limit if the rate estimate is ever wrong.
_MAX_SAMPLES: Final[int] = 16384


@dataclass(slots=True)
class ThreadStats:
    """Live state for one VM thread."""

    vm_thread_id: int
    form_id: int = 0
    depth: int = 0
    waiting: bool = False
    op_total: int = 0
    op_rate: float = 0.0
    last_seen: float = field(default_factory=time.monotonic)
    frames: tuple[proto.StackFrame, ...] = ()
    stack_truncated: bool = False
    wait_seconds: float = 0.0
    samples: deque[tuple[float, int]] = field(
        default_factory=lambda: deque(maxlen=_MAX_SAMPLES)
    )

    def op_rate_over(self, now: float, window: float = WINDOW_SECONDS) -> float:
        """Ops/sec computed from retained samples, not from the smoothed counter.

        A smoothed rate is prettier and lies: it stays high after a script
        stops, which is exactly the failure mode that makes a runaway-loop
        detector useless. So the wire's ``opRatePerSec`` is treated as a hint for
        the very first sample (when there is no history to derive from) and the
        sample progression is the source of truth thereafter.
        """
        if len(self.samples) < 2:
            return self.op_rate
        cutoff = now - window
        first_t: float | None = None
        first_ops = 0
        total = 0
        for t, ops in self.samples:
            if t < cutoff:
                continue
            if first_t is None:
                first_t, first_ops = t, ops
            total = ops - first_ops
        if first_t is None:
            return 0.0
        span = now - first_t
        if span <= 0.05:
            return self.op_rate
        return total / span


@dataclass(slots=True)
class Series:
    """Named float series for sparklines."""

    name: str
    points: deque[tuple[float, float]] = field(default_factory=lambda: deque(maxlen=240))
    unit: str = ""
    peak: float = 0.0

    def push(self, now: float, value: float) -> None:
        self.points.append((now, value))
        if value > self.peak:
            self.peak = value

    def latest(self) -> float:
        return self.points[-1][1] if self.points else 0.0

    def mean_over(self, now: float, window: float) -> float:
        cutoff = now - window
        vals = [v for t, v in self.points if t >= cutoff]
        return sum(vals) / len(vals) if vals else 0.0

    def history(self, now: float, window: float) -> list[float]:
        cutoff = now - window
        return [v for t, v in self.points if t >= cutoff]


@dataclass(slots=True)
class Snapshot:
    """Immutable-ish view handed to the UI. One per refresh tick."""

    now: float
    connected: bool
    active_threads: int
    queued_threads: int
    total_threads_seen: int
    frame_time_ms: float
    game_frame_count: int
    uptime_seconds: float
    working_set_mb: float
    private_mb: float
    handles: int
    os_threads: int
    streamed_cells: int
    events_emitted: int
    events_dropped: int
    total_op_rate: float
    threads: tuple[ThreadStats, ...]
    worst_thread: ThreadStats | None
    series: dict[str, Series]
    mod_loads: int
    exceptions: int
    save_bloats: int
    diags: tuple[tuple[proto.DiagLevel, str], ...]


class Profiler:
    """Aggregates V-Link frames into the state the dashboard renders."""

    def __init__(self) -> None:
        self._threads: dict[int, ThreadStats] = {}
        self._recent_diags: deque[tuple[proto.DiagLevel, str]] = deque(maxlen=200)
        self._mod_loads = 0
        self._exceptions = 0
        self._save_bloats = 0

        self._series: dict[str, Series] = {
            "op_rate": Series("Papyrus ops/sec", unit="/s"),
            "frame_time": Series("Frame time", unit="ms"),
            "threads": Series("Active threads", unit=""),
            "memory": Series("Working set", unit="MB"),
            "handles": Series("Handles", unit=""),
            "event_rate": Series("Event rate", unit="/s"),
        }

        # Latest values from the low-frequency events.
        self._connected = False
        self._frame_time_ms = 0.0
        self._game_frames = 0
        self._uptime = 0.0
        self._working_set = 0
        self._private = 0
        self._handles = 0
        self._os_threads = 0
        self._streamed = 0
        self._emitted = 0
        self._dropped = 0
        self._heartbeat_active = 0
        self._heartbeat_queued = 0

        # Event-rate accounting over the window.
        self._event_times: deque[float] = deque(maxlen=_MAX_SAMPLES)
        self._last_series_push = 0.0

    # -- ingest ------------------------------------------------------------

    def ingest(self, frame: proto.Frame) -> None:
        now = time.monotonic()
        self._event_times.append(now)
        et = frame.event_type
        p = frame.payload

        if et is proto.EventType.HEARTBEAT and isinstance(p, proto.Heartbeat):
            self._connected = True
            self._frame_time_ms = p.frame_time_ms
            self._game_frames = p.game_frame_count
            self._uptime = p.uptime_seconds
            self._heartbeat_active = p.active_papyrus_threads
            self._heartbeat_queued = p.queued_papyrus_threads
            self._emitted = p.total_events_emitted
            self._dropped = p.total_events_dropped

        elif et is proto.EventType.VM_TICK and isinstance(p, proto.VmTick):
            ts = self._threads.get(p.vm_thread_id)
            if ts is None:
                ts = self._threads[p.vm_thread_id] = ThreadStats(p.vm_thread_id)
            ts.op_total = p.op_total
            ts.op_rate = p.op_rate_per_sec
            ts.form_id = p.form_id
            ts.depth = p.depth
            ts.waiting = p.waiting
            ts.last_seen = now
            ts.samples.append((now, p.op_total))

        elif et is proto.EventType.THREAD_STATE and isinstance(p, proto.ThreadState):
            ts = self._threads.get(p.vm_thread_id)
            if p.phase is proto.ThreadPhase.CREATED:
                self._threads[p.vm_thread_id] = ThreadStats(p.vm_thread_id)
            elif ts is not None:
                if p.phase in (proto.ThreadPhase.EXITED, proto.ThreadPhase.ERRORED):
                    # Keep the record: a thread that exited hot is exactly what
                    # a runaway detector needs to report after the fact.
                    ts.last_seen = now
                ts.wait_seconds = p.wait_seconds
                ts.depth = p.depth
                if p.form_id:
                    ts.form_id = p.form_id

        elif et is proto.EventType.STACK_DUMP and isinstance(p, proto.StackDump):
            if p.frames:
                ts = self._threads.get(p.vm_thread_id)
                if ts is None:
                    ts = self._threads[p.vm_thread_id] = ThreadStats(p.vm_thread_id)
                ts.frames = p.frames
                ts.stack_truncated = p.truncated
                ts.last_seen = now
                deepest = max(p.frames, key=lambda f: f.depth, default=None)
                if deepest is not None:
                    ts.form_id = deepest.form_id
                    ts.depth = deepest.depth + 1

        elif et is proto.EventType.MEMORY and isinstance(p, proto.MemorySample):
            self._working_set = p.working_set_bytes
            self._private = p.private_bytes
            self._handles = p.handle_count
            self._os_threads = p.thread_count
            self._streamed = p.streamed_cell_count

        elif et is proto.EventType.MOD_LOAD:
            self._mod_loads += 1

        elif et is proto.EventType.VM_EXCEPTION:
            self._exceptions += 1

        elif et is proto.EventType.SAVE_BLOAT:
            self._save_bloats += 1

        elif et is proto.EventType.PLUGIN_DIAG and isinstance(p, proto.PluginDiag):
            self._recent_diags.append((p.level, p.text))

        # Push to the series at a fixed cadence, not per frame: a Textual
        # refresh cannot use more than a few samples per second anyway, and
        # pushing per event would make the sparkline unreadable.
        if now - self._last_series_push >= 0.25:
            self._last_series_push = now
            self._push_series(now)

    def _push_series(self, now: float) -> None:
        total_rate = 0.0
        active = 0
        for ts in self._threads.values():
            rate = ts.op_rate_over(now)
            if rate > 0:
                total_rate += rate
            # A thread is "active" if it is running ops and not parked.
            if rate > 0 and not ts.waiting and now - ts.last_seen < 1.5:
                active += 1

        cutoff = now - WINDOW_SECONDS
        recent_events = sum(1 for t in self._event_times if t >= cutoff)

        self._series["op_rate"].push(now, total_rate)
        self._series["frame_time"].push(now, self._frame_time_ms)
        self._series["threads"].push(now, float(self._heartbeat_active or active))
        self._series["memory"].push(now, self._working_set / (1024 * 1024))
        self._series["handles"].push(now, float(self._handles))
        self._series["event_rate"].push(now, recent_events / WINDOW_SECONDS)

    def set_connected(self, connected: bool) -> None:
        self._connected = connected

    def note_diag(self, level: proto.DiagLevel, text: str) -> None:
        self._recent_diags.append((level, text))

    # -- read --------------------------------------------------------------

    def snapshot(self) -> Snapshot:
        now = time.monotonic()
        if not self._series["op_rate"].points or now - self._last_series_push >= 0.25:
            self._last_series_push = now
            self._push_series(now)

        total_rate = 0.0
        for ts in self._threads.values():
            total_rate += ts.op_rate_over(now)

        live = tuple(
            sorted(
                self._threads.values(),
                key=lambda t: t.op_rate_over(now),
                reverse=True,
            )
        )
        worst = live[0] if live and live[0].op_rate_over(now) > 0 else None

        return Snapshot(
            now=now,
            connected=self._connected,
            active_threads=self._heartbeat_active or sum(
                1 for t in live if t.op_rate_over(now) > 0 and not t.waiting
            ),
            queued_threads=self._heartbeat_queued,
            total_threads_seen=len(live),
            frame_time_ms=self._frame_time_ms,
            game_frame_count=self._game_frames,
            uptime_seconds=self._uptime,
            working_set_mb=self._working_set / (1024 * 1024),
            private_mb=self._private / (1024 * 1024),
            handles=self._handles,
            os_threads=self._os_threads,
            streamed_cells=self._streamed,
            events_emitted=self._emitted,
            events_dropped=self._dropped,
            total_op_rate=total_rate,
            threads=live,
            worst_thread=worst,
            series=self._series,
            mod_loads=self._mod_loads,
            exceptions=self._exceptions,
            save_bloats=self._save_bloats,
            diags=tuple(self._recent_diags),
        )
