"""OverseerCLI Textual dashboard.

Rule 4 boundary: this package only *renders* what the profiler and detector
produce. It holds no counters, computes no thresholds, and does no parsing.

Three panels, matching the operational layout:

  Panel 1  Live Papyrus stack & active thread count
  Panel 2  Memory & event stream rate
  Panel 3  Anomaly warnings & mod heuristic reports
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Label, Sparkline, Static

from .. import protocol as proto
from ..detector import Detector, Finding, Severity
from ..profiler import WINDOW_SECONDS, Profiler, Snapshot

if TYPE_CHECKING:
    from ..ipc_client import VLinkClient

#: Seconds between dashboard refreshes. 4 Hz is fast enough to feel live and
#: slow enough that a terminal over SSH does not become the bottleneck.
REFRESH_HZ: float = 4.0

_SEVERITY_STYLE = {
    Severity.INFO: "dim",
    Severity.WARN: "bold yellow",
    Severity.CRITICAL: "bold white on dark_red",
}


def _fmt_bytes(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(n) < 1024 or unit == "GiB":
            return f"{n:,.1f} {unit}" if unit != "B" else f"{n:,.0f} B"
        n /= 1024
    return f"{n:.1f} GiB"


def _fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def _fmt_formid(form_id: int) -> str:
    return f"{form_id:08X}" if form_id else "-"


class StackPanel(Vertical):
    """Panel 1: live Papyrus stack and active thread count."""

    def compose(self) -> ComposeResult:
        yield Label("Papyrus Threads", classes="panel-title")
        yield Static(id="thread-summary")
        yield DataTable(id="thread-table", cursor_type="row", zebra_stripes=True)

    def update_from(self, snap: Snapshot, mods) -> None:
        summary = self.query_one("#thread-summary", Static)
        idle = sum(1 for t in snap.threads if t.waiting or t.op_rate_over(snap.now) == 0)
        summary.update(
            Text.assemble(
                ("active ", "bold"),
                (f"{snap.active_threads}", "bold green"),
                ("  queued ", "bold"),
                (f"{snap.queued_threads}", "bold cyan"),
                ("  parked ", "dim"),
                (f"{idle}", "dim"),
                ("  threads seen ", "dim"),
                (f"{snap.total_threads_seen}", "dim"),
                ("\ntotal ", "bold"),
                (f"{snap.total_op_rate:,.0f} ops/s", "bold magenta"),
            )
        )

        table = self.query_one("#thread-table", DataTable)
        if not table.columns:
            table.add_columns("VM thread", "FormID", "script", "mod", "ops/s", "depth", "state")
        table.clear()

        # Show the busiest first, and cap the rows: a 300-thread debug session
        # would otherwise push the memory panel off screen.
        for ts in sorted(snap.threads, key=lambda t: t.op_rate_over(snap.now), reverse=True)[:24]:
            rate = ts.op_rate_over(snap.now)
            name = mods.script_name_for(
                proto.StackDump(ts.vm_thread_id, ts.frames, ts.stack_truncated, 0.0)
                if ts.frames
                else None,
                ts.form_id,
            )
            state = "waiting" if ts.waiting else ("idle" if rate == 0 else "RUNNING")
            state_style = "dim" if state != "RUNNING" else (
                "bold red" if rate > 500 else "green"
            )
            table.add_row(
                Text(f"{ts.vm_thread_id:>4}", style="dim"),
                Text(_fmt_formid(ts.form_id)),
                Text(name or "-"),
                Text(mods.mod_for(ts.form_id), style="cyan"),
                Text(f"{rate:,.0f}", style="bold magenta" if rate > 500 else ""),
                Text(f"{ts.depth}"),
                Text(state, style=state_style),
            )


class MemoryPanel(Vertical):
    """Panel 2: memory and event stream rate."""

    def compose(self) -> ComposeResult:
        yield Label("Memory & Event Stream", classes="panel-title")
        yield Static(id="mem-summary")
        yield Horizontal(
            Sparkline(id="spark-mem", data=[0.0] * 60, max_=1024.0),
            Sparkline(id="spark-events", data=[0.0] * 60, max_=1024.0),
            id="spark-row",
        )
        yield Static(id="stream-summary", classes="dim")

    def update_from(self, snap: Snapshot) -> None:
        self.query_one("#mem-summary", Static).update(
            Text.assemble(
                ("working set ", "dim"), (_fmt_bytes(snap.working_set_mb * 1024 * 1024), "bold"),
                ("   private ", "dim"), (_fmt_bytes(snap.private_mb * 1024 * 1024), ""),
                ("\nhandles ", "dim"), (f"{snap.handles:,}", "bold"),
                ("   os threads ", "dim"), (f"{snap.os_threads}", ""),
                ("   streamed cells ", "dim"), (f"{snap.streamed_cells}", ""),
            )
        )

        self.query_one("#spark-mem", Sparkline).data = [
            v for _, v in snap.series["memory"].history(snap.now, 60.0)
        ] or [0.0]
        self.query_one("#spark-events", Sparkline).data = [
            v for _, v in snap.series["event_rate"].history(snap.now, 60.0)
        ] or [0.0]

        dropped_pct = (
            snap.events_dropped / max(snap.events_emitted, 1) * 100 if snap.events_emitted else 0.0
        )
        self.query_one("#stream-summary", Static).update(
            Text.assemble(
                (f"stream {snap.events_emitted:,} frames", "dim"),
                (f"  dropped {snap.events_dropped:,}", "bold red" if dropped_pct > 1 else "dim"),
                (f"  ({dropped_pct:.2f}%)", "dim"),
                (f"  frame {snap.frame_time_ms:.1f} ms", "dim"),
                (f"  uptime {_fmt_duration(snap.uptime_seconds)}", "dim"),
            )
        )


class AnomalyPanel(Vertical):
    """Panel 3: anomaly warnings and mod heuristic reports."""

    def compose(self) -> ComposeResult:
        yield Label("Anomalies", classes="panel-title")
        yield DataTable(id="anomaly-table", cursor_type="row", zebra_stripes=True)
        yield Static(id="anomaly-detail", classes="detail")

    def update_from(self, snap: Snapshot, findings: list[Finding]) -> None:
        table = self.query_one("#anomaly-table", DataTable)
        if not table.columns:
            table.add_columns("sev", "rule", "script", "formid", "mod", "conf")
        table.clear()

        for f in findings[:50]:
            table.add_row(
                Text(f.severity.value.upper(), style=_SEVERITY_STYLE[f.severity]),
                Text(f.rule, style="dim"),
                Text(f.script_name or f.title),
                Text(_fmt_formid(f.form_id)),
                Text(f.source_mod, style="cyan"),
                Text(f"{f.confidence:.0%}", style="dim"),
                key=f.key(),
            )
        if not findings:
            table.add_row(Text("OK", style="green"), Text("-"), Text("no anomalies"), Text("-"), Text("-"), Text("-"))

        detail = self.query_one("#anomaly-detail", Static)
        selected = findings[table.cursor_row] if 0 <= table.cursor_row < len(findings) else None
        detail.update(
            Text(selected.detail if selected else "", style=_SEVERITY_STYLE[selected.severity])
            if selected
            else Text("", style="dim")
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = str(event.row_key.value)
        if self.app.query_one("#anomaly-table", DataTable).cursor_row >= 0:
            self.app.post_message(("acknowledge", key))


class OverseerApp(App):
    """The dashboard application."""

    CSS_PATH = "overseer.tcss"
    TITLE = "PIP-MON :: OverseerCLI"
    SUB_TITLE = "Fallout 4 Papyrus telemetry"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "acknowledge", "Acknowledge"),
        ("A", "acknowledge_all", "Ack all"),
        ("c", "clear", "Clear findings"),
        ("d", "toggle_diag", "Toggle log"),
        ("r", "refresh_now", "Refresh"),
    ]

    show_diag = reactive(False)

    def __init__(
        self,
        client: VLinkClient,
        *,
        detector: Detector | None = None,
        low_detail: bool = False,
    ) -> None:
        super().__init__()
        self._client = client
        self._profiler = Profiler()
        # Injected so thresholds come from JSONC config (rules_config), not from
        # hard-coded defaults. Rule 4: the UI never constructs a rule itself.
        self._detector = detector if detector is not None else Detector()
        self._low_detail = low_detail
        self._status = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            StackPanel(id="panel-stack"),
            MemoryPanel(id="panel-memory"),
            AnomalyPanel(id="panel-anomaly"),
            id="panels",
        )
        yield VerticalScroll(Static(id="diag-log"), id="diag-wrap")
        with Static(id="status-bar", classes="status"):
            yield Label("", id="status-label")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#diag-wrap").display = False
        self.set_interval(1.0 / REFRESH_HZ, self._tick)
        self.set_interval(0.5, self._poll)
        self._tick()

    # -- data path ---------------------------------------------------------

    def _poll(self) -> None:
        """Drain the IPC queue. Cheap; runs more often than the render."""
        drained = 0
        # Bounded so a burst cannot stall a frame: the reader thread keeps the
        # queue for the rest.
        limit = 512 if self._low_detail else 4096
        while drained < limit:
            frame = self._client.try_get()
            if frame is None:
                break
            drained += 1
            self._profiler.ingest(frame)
            self._detector.ingest(frame)
        self._profiler.set_connected(self._client.stats.connected)

    def _tick(self) -> None:
        snap = self._profiler.snapshot()
        findings = self._detector.evaluate(snap)

        self.query_one("#panel-stack", StackPanel).update_from(snap, self._detector.mods)
        self.query_one("#panel-memory", MemoryPanel).update_from(snap)
        self.query_one("#panel-anomaly", AnomalyPanel).update_from(snap, findings)

        if self.show_diag:
            self._render_diag(snap)

        self._update_status(snap, findings)

    def _render_diag(self, snap: Snapshot) -> None:
        lines = []
        for level, text in list(snap.diags)[-200:]:
            if text.startswith("{"):
                try:
                    data = json.loads(text)
                    kind = data.get("kind", "?")
                    text = f"[{kind}] " + json.dumps(
                        {k: v for k, v in data.items() if k != "kind"}, separators=(",", ":")
                    )
                except ValueError:
                    pass
            style = {proto.DiagLevel.INFO: "dim", proto.DiagLevel.WARNING: "yellow",
                     proto.DiagLevel.ERROR: "red"}[level]
            lines.append(Text(f"[{level.name[:4]}] {text}", style=style))
        self.query_one("#diag-log", Static).update(
            Text("\n").join(lines) if lines else Text("no diagnostics received", style="dim")
        )

    def _update_status(self, snap: Snapshot, findings: list[Finding]) -> None:
        st = self._client.stats
        crit = sum(1 for f in findings if f.severity is Severity.CRITICAL)
        warn = sum(1 for f in findings if f.severity is Severity.WARN)

        parts = [
            Text("● ", style="green" if st.connected else "red"),
            Text("connected" if st.connected else "waiting for vprobe",
                 style="green" if st.connected else "bold red"),
            Text("   pipe \\\\.\\pipe\\vlink_telemetry", style="dim"),
        ]
        if not st.connected:
            silent = st.seconds_since_last_frame()
            if 0 < silent < 5:
                parts.append(Text(f"  (retrying, {silent:.0f}s)", style="dim"))
            parts.append(
                Text(
                    "  Is the game running with vprobe.dll loaded?",
                    style="dim italic",
                )
            )
        if crit:
            parts.append(Text(f"   {crit} CRITICAL", style="bold white on dark_red"))
        if warn:
            parts.append(Text(f"   {warn} warn", style="yellow"))
        parts.append(Text(f"   window {WINDOW_SECONDS:.0f}s", style="dim"))
        if st.frames_dropped:
            parts.append(Text(f"   {st.frames_dropped:,} dropped", style="yellow"))

        self._status = "".join(p.plain for p in parts)
        self.query_one("#status-label", Label).update(Text.assemble(*parts))

    # -- actions -----------------------------------------------------------

    def action_acknowledge(self) -> None:
        table = self.query_one("#anomaly-table", DataTable)
        if table.cursor_row >= 0 and table.row_count:
            row = table.get_row_at(table.cursor_row)
            if row:
                # The key is not retrievable from the row data, so match on the
                # displayed rule+form which is unique per finding in practice.
                rule = str(row[1])
                for f in self._detector.active():
                    if f.rule == rule:
                        self._detector.acknowledge(f.key())
                        break
        self._tick()

    def action_acknowledge_all(self) -> None:
        self._detector.acknowledge_all()
        self._tick()

    def action_clear(self) -> None:
        self._detector.clear()
        self._tick()

    def action_toggle_diag(self) -> None:
        self.show_diag = not self.show_diag
        self.query_one("#diag-wrap").display = self.show_diag

    def action_refresh_now(self) -> None:
        self._poll()
        self._tick()

    def on_key(self, event) -> None:  # noqa: ANN001
        if event.key == "d":
            self.action_toggle_diag()

    def on_unmount(self) -> None:
        self._status = "disconnected"
