"""Detector tests.

The detector is the component whose bugs matter most and are hardest to notice.
A rule that never fires produces a dashboard that looks healthy; a rule that always
fires produces one nobody reads. So these tests check both directions, and
explicitly test the *negative* cases.

Time is injected via the snapshot's ``now`` field rather than by mocking
``time.monotonic``, so the tests read as scenarios rather than as call-count
assertions.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest

from overseer_cli import protocol as p
from overseer_cli.detector import (
    Detector,
    DroppedEventRule,
    FrameTimeRule,
    ModIndex,
    RunawayLoopRule,
    SaveBloatRule,
    Severity,
    StackDepthRule,
    VmStarvationRule,
)
from overseer_cli.profiler import Profiler
from overseer_cli.rules_config import DEFAULTS, build_detector, load_rule_config


# --------------------------------------------------------------------------
# Controllable clock
# --------------------------------------------------------------------------


class FakeClock:
    """A monotonic clock the test advances by hand.

    The detector's dwell-time logic (a runaway must stay elevated for N seconds)
    cannot be tested against a real clock: either the test sleeps for real and
    becomes slow and flaky, or it fakes the timestamps and the fake leaks into
    the assertions. Injecting one clock that both the profiler and the detector
    read keeps the scenarios fast and exact.
    """

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeClock]:
    c = FakeClock()
    monkeypatch.setattr(time, "monotonic", c)
    return c


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def feed(profiler: Profiler, et: p.EventType, payload: bytes) -> None:
    frame, _ = p.decode(memoryview(p.pack_frame(et, payload, sequence=1)))
    profiler.ingest(frame)


def tick(thread: int, ops: int, rate: float, form: int = 0x05005678, depth: int = 1) -> bytes:
    # vmThreadId, opCounter, opTotal, windowMs, opRate, formId, depth, opCode,
    # waiting, reserved
    return p._VM_TICK.pack(thread, 64, ops, 0.5, rate, form, depth, 0, 0, 0)


def thread_state(thread: int, phase: p.ThreadPhase, form: int = 0, depth: int = 0) -> bytes:
    # vmThreadId, waitEventMask, formId, waitSeconds, depth, phase, waiting, reserved
    return p._THREAD_STATE.pack(thread, 0, form, 0.0, depth, int(phase), 0, 0)


def heartbeat(active: int = 1, queued: int = 0, emitted: int = 1000, dropped: int = 0) -> bytes:
    return p._HEARTBEAT.pack(60.0, 3600, 16.7, active, queued, emitted, dropped)


def memory(working_set_mb: float, handles: int) -> bytes:
    return p._MEMORY.pack(
        int(working_set_mb * 1024 * 1024),
        int(working_set_mb * 1024 * 1024),
        int(working_set_mb * 2 * 1024 * 1024),
        int(working_set_mb * 1024 * 1024),
        handles,
        180,
        1,
        0,
    )


def build_runaway_detector(**kw) -> Detector:  # noqa: ANN003
    """A detector with only the runaway rule, thresholds tuned for the test."""
    return Detector([RunawayLoopRule(**kw)])


def run_for(
    clock: FakeClock,
    prof: Profiler,
    det: Detector,
    seconds: float,
    rate: float = 3200.0,
    step: float = 0.25,
    *,
    _ops: dict[int, int] | None = None,
) -> list:  # noqa: ANN001
    """Advance the fake clock, feeding a hot thread, then evaluate.

    Two things this gets right that a naive helper does not:

    1. opTotal is derived from elapsed time, so it is monotonic AND consistent
       with the claimed rate. The detector recomputes the rate from the sample
       progression rather than trusting opRatePerSec (an EWMA stays high after a
       script stops), so a fixture that claims 3200 ops/s while advancing 64 ops
       per 0.25 s is correctly read as 256 ops/s.

    2. The op counter persists across calls. If it restarted, opTotal would move
       BACKWARDS between calls, the derived rate would collapse, and the rule
       would legitimately stop firing -- which looks exactly like a detector bug
       but is a fixture bug.
    """
    findings: list = []
    ops_state = {} if _ops is None else _ops
    steps = int(seconds / step)
    for _ in range(steps):
        clock.advance(step)
        total = ops_state.get(7, 0) + max(1, int(rate * step))
        ops_state[7] = total
        feed(prof, p.EventType.VM_TICK, tick(7, total, rate))
        findings = det.evaluate(prof.snapshot())
    return findings


def run_for_low_rate(
    clock: FakeClock,
    prof: Profiler,
    det: Detector,
    rate: float,
    seconds: float,
    ops_state: dict[int, int] | None = None,
) -> list:  # noqa: ANN001
    """Same as run_for at a given rate, with a shareable op counter.

    Pass the same ``ops_state`` dict to consecutive calls to simulate one
    continuous thread rather than several independent ones.
    """
    return run_for(clock, prof, det, seconds, rate=rate, _ops=ops_state)


# --------------------------------------------------------------------------
# Runaway loop
# --------------------------------------------------------------------------


def test_runaway_fires_after_sustained_elevation(clock: FakeClock) -> None:
    prof = Profiler()
    det = build_runaway_detector(threshold_ops=500.0, sustain=2.0)
    findings = run_for(clock, prof, det, seconds=4.0)
    assert findings, "a 3200 ops/s loop held for 4s must fire"
    f = findings[0]
    assert f.rule == "runaway_loop"
    assert f.thread_id == 7
    assert f.form_id == 0x05005678


def test_runaway_does_not_fire_on_a_single_spike(clock: FakeClock) -> None:
    """The core negative test: a brief spike is not a runaway loop.

    A script that loops a container once on start legitimately looks like this.
    """
    prof = Profiler()
    det = build_runaway_detector(threshold_ops=500.0, sustain=2.0)
    ops = 0
    for i in range(20):
        clock.advance(0.25)
        ops += 64
        rate = 3000.0 if i == 5 else 30.0
        feed(prof, p.EventType.VM_TICK, tick(7, ops, rate))
        findings = det.evaluate(prof.snapshot())
    assert not any(f.rule == "runaway_loop" for f in findings)


def test_runaway_does_not_fire_below_threshold(clock: FakeClock) -> None:
    prof = Profiler()
    det = build_runaway_detector(threshold_ops=500.0, sustain=2.0)
    findings = run_for_low_rate(clock, prof, det, rate=400.0, seconds=6.0)
    assert not findings


def test_runaway_severity_escalates_with_persistence(clock: FakeClock) -> None:
    """A short, barely-over-threshold loop must not be CRITICAL."""
    prof = Profiler()
    det = build_runaway_detector(threshold_ops=500.0, sustain=1.0)
    findings = run_for_low_rate(clock, prof, det, rate=600.0, seconds=2.0)
    runaway = [f for f in findings if f.rule == "runaway_loop"]
    assert runaway
    assert runaway[0].severity is Severity.WARN
    assert runaway[0].confidence < 0.75


def test_runaway_findings_are_deduplicated(clock: FakeClock) -> None:
    """A sustained loop must produce one finding, not one per sample."""
    prof = Profiler()
    det = build_runaway_detector(threshold_ops=500.0, sustain=1.0)
    findings = run_for_low_rate(clock, prof, det, rate=3200.0, seconds=5.0)
    keys = [f.key() for f in findings if f.rule == "runaway_loop"]
    assert len(keys) == len(set(keys)) == 1


def test_runaway_preserves_first_seen_across_refreshes(clock: FakeClock) -> None:
    prof = Profiler()
    det = build_runaway_detector(threshold_ops=500.0, sustain=1.0)
    ops: dict[int, int] = {}
    run_for_low_rate(clock, prof, det, rate=3200.0, seconds=2.0, ops_state=ops)
    first = next(f for f in det.active() if f.rule == 'runaway_loop').first_seen
    run_for_low_rate(clock, prof, det, rate=3200.0, seconds=2.0, ops_state=ops)
    later = next(f for f in det.active() if f.rule == "runaway_loop").first_seen
    assert later == first, "first_seen must not restart on every evaluate"


def test_confidence_rises_with_excess_and_duration(clock: FakeClock) -> None:
    prof_a, prof_b = Profiler(), Profiler()
    det_a = build_runaway_detector(threshold_ops=500.0, sustain=1.0)
    det_b = build_runaway_detector(threshold_ops=500.0, sustain=1.0)
    a = run_for_low_rate(clock, prof_a, det_a, rate=600.0, seconds=1.5)
    b = run_for_low_rate(clock, prof_b, det_b, rate=9000.0, seconds=6.0)
    fa = next(f for f in a if f.rule == "runaway_loop")
    fb = next(f for f in b if f.rule == "runaway_loop")
    assert fb.confidence > fa.confidence
    assert 0.0 <= fa.confidence <= 1.0 and 0.0 <= fb.confidence <= 1.0


# --------------------------------------------------------------------------
# Stack depth
# --------------------------------------------------------------------------


def test_stack_depth_warns_above_80_percent(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector([StackDepthRule(warn_depth=820, overflow_depth=1024)])
    feed(prof, p.EventType.VM_TICK, tick(3, 64, 100.0, depth=900))
    findings = det.evaluate(prof.snapshot())
    assert findings and findings[0].rule == "stack_depth"
    assert findings[0].severity is Severity.WARN


def test_stack_overflow_is_critical(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector([StackDepthRule(warn_depth=820, overflow_depth=1024)])
    feed(prof, p.EventType.VM_TICK, tick(3, 64, 100.0, depth=1024))
    findings = det.evaluate(prof.snapshot())
    assert findings[0].severity is Severity.CRITICAL


def test_normal_depth_produces_nothing(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector([StackDepthRule(warn_depth=820, overflow_depth=1024)])
    feed(prof, p.EventType.VM_TICK, tick(3, 64, 100.0, depth=4))
    assert not det.evaluate(prof.snapshot())


def test_stack_depth_detail_advises_saving(clock: FakeClock) -> None:
    """The user-facing text must carry the actionable part."""
    prof = Profiler()
    det = Detector([StackDepthRule(warn_depth=820, overflow_depth=1024)])
    feed(prof, p.EventType.VM_TICK, tick(3, 64, 100.0, depth=1000))
    f = det.evaluate(prof.snapshot())[0]
    assert "save" in f.detail.lower()
    assert "1024" in f.detail


# --------------------------------------------------------------------------
# Save bloat
# --------------------------------------------------------------------------


def test_save_bloat_requires_loop_and_growth_together(clock: FakeClock) -> None:
    """Either signal alone must not fire. This is the rule's whole design."""
    prof = Profiler()
    det = Detector([SaveBloatRule(growth_warn_mb=1.0)])

    # memory only, no loop
    feed(prof, p.EventType.MEMORY, memory(3000.0, 4200))
    det.evaluate(prof.snapshot())
    for _ in range(5):
        feed(prof, p.EventType.MEMORY, memory(3000.0 + _ * 100, 4200))
    loop_only = det.evaluate(prof.snapshot())
    assert not [f for f in loop_only if f.rule == "save_bloat"], (
        "memory growth with no hot script is not a save-bloat finding"
    )

    # now add a hot loop as well
    ops = 0
    for _ in range(6):
        ops += 64
        feed(prof, p.EventType.VM_TICK, tick(3, ops, 2400.0, form=0x01001234))
        feed(prof, p.EventType.MEMORY, memory(3000.0 + _ * 120, 4200))
    both = det.evaluate(prof.snapshot())
    assert [f for f in both if f.rule == "save_bloat"]


def test_handle_growth_is_reported(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector([SaveBloatRule(handle_warn=100, handle_critical=5000)])
    feed(prof, p.EventType.MEMORY, memory(3000.0, 4200))
    det.evaluate(prof.snapshot())
    for _ in range(4):
        feed(prof, p.EventType.MEMORY, memory(3000.0, 4200 + _ * 300))
    findings = det.evaluate(prof.snapshot())
    leaks = [f for f in findings if f.rule == "handle_leak"]
    assert leaks and leaks[0].severity is Severity.WARN


def test_handle_critical_escalates(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector([SaveBloatRule(handle_warn=100, handle_critical=5000)])
    feed(prof, p.EventType.MEMORY, memory(3000.0, 4200))
    det.evaluate(prof.snapshot())
    for _ in range(4):
        feed(prof, p.EventType.MEMORY, memory(3000.0, 4200 + _ * 3000))
    leaks = [f for f in det.evaluate(prof.snapshot()) if f.rule == "handle_leak"]
    assert leaks and leaks[0].severity is Severity.CRITICAL


# --------------------------------------------------------------------------
# Starvation, frame time
# --------------------------------------------------------------------------


def test_vm_starvation_needs_multiple_busy_threads(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector([VmStarvationRule(min_op_rate=50.0, min_busy_threads=2)])
    feed(prof, p.EventType.VM_TICK, tick(1, 64, 900.0))
    assert not [f for f in det.evaluate(prof.snapshot()) if f.rule == "vm_starvation"]

    feed(prof, p.EventType.VM_TICK, tick(2, 128, 900.0))
    assert [f for f in det.evaluate(prof.snapshot()) if f.rule == "vm_starvation"]


def test_frame_time_names_a_hot_script_as_culprit(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector([FrameTimeRule(warn_ms=33.3, critical_ms=66.7)])
    feed(prof, p.EventType.MEMORY, memory(3000.0, 4200))
    for _ in range(6):
        feed(prof, p.EventType.VM_TICK, tick(3, 64 * _, 3000.0))
        feed(prof, p.EventType.HEARTBEAT, heartbeat(emitted=1000, dropped=0))
        snap = prof.snapshot()
    # Force the series to reflect a slow frame.
    prof._series["frame_time"].points.clear()
    for i in range(10):
        prof._series["frame_time"].push(time.monotonic(), 45.0)
    findings = det.evaluate(prof.snapshot())
    ft = [f for f in findings if f.rule == "frame_time"]
    assert ft, "45 ms mean is above the 33.3 ms threshold"
    assert "Probable contributor" in ft[0].detail


# --------------------------------------------------------------------------
# Transparency rules
# --------------------------------------------------------------------------


def test_dropped_events_is_critical_above_ratio(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector([DroppedEventRule(critical_ratio=0.05)])
    feed(prof, p.EventType.HEARTBEAT, heartbeat(emitted=1000, dropped=100))
    f = det.evaluate(prof.snapshot())[0]
    assert f.rule == "dropped_events"
    assert f.severity is Severity.CRITICAL


def test_dropped_events_warns_below_ratio(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector([DroppedEventRule(critical_ratio=0.5)])
    feed(prof, p.EventType.HEARTBEAT, heartbeat(emitted=10000, dropped=100))
    f = det.evaluate(prof.snapshot())[0]
    assert f.severity is Severity.WARN


def test_degraded_probe_names_the_disabled_hooks(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector()
    report = (
        '{"kind":"resolver_report","tier1":2,"tier2":0,"rejected":1,"missing":2,'
        '"entries":[{"name":"PapyrusScript::Execute","state":"addresslib","rva":1},'
        '{"name":"PapyrusThread::Execute","state":"missing","rva":0},'
        '{"name":"PapyrusVM::DebugPrint","state":"rejected","rva":0}]}'
    )
    frame, _ = p.decode(
        memoryview(p.pack_frame(p.EventType.PLUGIN_DIAG, p._PLUGIN_DIAG.pack(0, len(report)) + report.encode()))
    )
    det.ingest(frame)
    findings = det.evaluate(prof.snapshot())
    degraded = [f for f in findings if f.rule == "degraded_probe"]
    assert degraded
    assert "PapyrusThread::Execute" in degraded[0].detail
    assert "PapyrusVM::DebugPrint" in degraded[0].detail
    assert "PapyrusScript::Execute" not in degraded[0].detail, "healthy hooks are not listed"


# --------------------------------------------------------------------------
# ModIndex
# --------------------------------------------------------------------------


def test_mod_index_resolves_formid_via_load_order_byte(clock: FakeClock) -> None:
    mods = ModIndex()
    mods.set_mod_index(0x01, "SkyUI.esm")
    mods.set_mod_index(0x05, "SkyFC06.esp")
    assert mods.mod_for(0x05005678) == "SkyFC06.esp"
    assert mods.mod_for(0x01001234) == "SkyUI.esm"
    assert mods.mod_for(0) == "unknown"


def test_mod_index_prefers_explicit_record(clock: FakeClock) -> None:
    mods = ModIndex()
    mods.set_mod_index(0x05, "SkyFC06.esp")
    mods.set_mod_index(0x01, "SkyUI.esm")
    mods.note_form(0x01001234, 0x01)
    assert mods.mod_for(0x01001234) == "SkyUI.esm"


def test_mod_index_falls_back_to_index_label(clock: FakeClock) -> None:
    mods = ModIndex()
    assert mods.mod_for(0x2A000001) == "index 2A"


def test_name_table_is_parsed_from_diag_json(clock: FakeClock) -> None:
    mods = ModIndex()
    text = '{"names":["Script_TCMain","Script_WorkshopRef"]}'
    frame, _ = p.decode(
        memoryview(
            p.pack_frame(
                p.EventType.PLUGIN_DIAG,
                p._PLUGIN_DIAG.pack(0, len(text)) + text.encode(),
            )
        )
    )
    mods.ingest(frame)
    assert mods.name_of(0) == "Script_TCMain"
    assert mods.name_of(1) == "Script_WorkshopRef"


# --------------------------------------------------------------------------
# Acknowledgement and robustness
# --------------------------------------------------------------------------


def test_acknowledge_marks_but_does_not_hide(clock: FakeClock) -> None:
    """Acknowledgement suppresses the notification, not the visibility.

    A runaway script the user dismissed is still running. Hiding it entirely
    would be the exact failure this module exists to avoid, so an acknowledged
    finding stays in `active()` flagged, and drops out of `unacknowledged()`.
    """
    prof = Profiler()
    det = build_runaway_detector(threshold_ops=500.0, sustain=1.0)
    ops: dict[int, int] = {}
    run_for_low_rate(clock, prof, det, rate=3200.0, seconds=3.0, ops_state=ops)
    f = next(x for x in det.active() if x.rule == "runaway_loop")
    det.acknowledge(f.key())

    stored = next(x for x in det.active() if x.rule == "runaway_loop")
    assert stored.acknowledged is True
    assert f.key() not in {x.key() for x in det.unacknowledged()}, (
        "acknowledged findings must leave the notification set"
    )
    assert det.counts()["acknowledged"] == 1
    assert det.counts()["warn"] == 0


def test_acknowledged_finding_rearms_after_it_clears(clock: FakeClock) -> None:
    """Dismiss, let it stop, then let it start again: the user IS warned again.

    Without the re-arm, a user who acknowledged a runaway once would never be
    warned about that script again, even after it had stopped, been fixed, and
    started up again ten minutes later.
    """
    prof = Profiler()
    det = build_runaway_detector(threshold_ops=500.0, sustain=1.0)
    ops: dict[int, int] = {}
    run_for_low_rate(clock, prof, det, rate=3200.0, seconds=3.0, ops_state=ops)
    f = next(x for x in det.active() if x.rule == "runaway_loop")
    det.acknowledge(f.key())

    # The loop stops. Drain past the window so the finding genuinely clears.
    run_for_low_rate(clock, prof, det, rate=5.0, seconds=20.0, ops_state=ops)
    assert not any(x.rule == "runaway_loop" for x in det.unacknowledged())

    # It comes back as a new occurrence.
    run_for_low_rate(clock, prof, det, rate=3200.0, seconds=3.0, ops_state=ops)
    again = next(x for x in det.active() if x.rule == "runaway_loop")
    assert again.acknowledged is False, "a new occurrence must re-arm the warning"
    assert again.key() == f.key()


def test_a_raising_rule_does_not_kill_the_dashboard(clock: FakeClock) -> None:
    class Exploding:
        name = "exploding"

        def evaluate(self, snap, mods, now):  # noqa: ANN001, ANN202
            raise RuntimeError("boom")

        def reset(self) -> None:
            pass

    prof = Profiler()
    det = Detector([Exploding()])
    findings = det.evaluate(prof.snapshot())
    assert any(f.rule == "detector_error" for f in findings)


def test_findings_sorted_by_severity_then_recency(clock: FakeClock) -> None:
    prof = Profiler()
    det = Detector()
    feed(prof, p.EventType.HEARTBEAT, heartbeat(emitted=100, dropped=90))
    findings = det.evaluate(prof.snapshot())
    ranks = [f.severity.rank for f in findings]
    assert ranks == sorted(ranks, reverse=True)


def test_clear_resets_every_rule(clock: FakeClock) -> None:
    prof = Profiler()
    det = build_runaway_detector(threshold_ops=500.0, sustain=1.0)
    run_for_low_rate(clock, prof, det, rate=3200.0, seconds=3.0)
    assert det.active()
    det.clear()
    assert not det.active()


# --------------------------------------------------------------------------
# Config wiring
# --------------------------------------------------------------------------


def test_defaults_match_the_documented_values(clock: FakeClock) -> None:
    """docs/ANOMALY_RULES.md is the contract; this keeps the two from drifting."""
    assert DEFAULTS["runawayLoop"]["thresholdOpsPerSec"] == 500.0
    assert DEFAULTS["runawayLoop"]["sustainSeconds"] == 2.0
    assert DEFAULTS["stackDepth"]["warnDepth"] == 820
    assert DEFAULTS["stackDepth"]["overflowDepth"] == 1024
    assert DEFAULTS["frameTime"]["warnMs"] == 33.3
    assert DEFAULTS["frameTime"]["criticalMs"] == 66.7
    assert DEFAULTS["saveBloat"]["handleGrowthWarn"] == 1500
    assert DEFAULTS["saveBloat"]["handleGrowthCritical"] == 6000


def test_missing_config_yields_defaults_and_no_warning(tmp_path) -> None:  # noqa: ANN001
    rc = load_rule_config(tmp_path / "nope.jsonc")
    assert rc.source is None
    assert not rc.warnings
    assert rc.values == DEFAULTS


def test_config_override_reaches_the_rule(tmp_path) -> None:  # noqa: ANN001
    cfg = tmp_path / "overseer_rules.jsonc"
    cfg.write_text(
        """
        // user has a heavy load order
        {
            "runawayLoop": {
                "thresholdOpsPerSec": 1200.0,  // their scripts are legitimately busy
                "sustainSeconds": 3.0,
            },
        }
        """,
        encoding="utf-8",
    )
    rc = load_rule_config(cfg)
    assert rc.source == cfg
    assert rc.number("runawayLoop.thresholdOpsPerSec", 0) == 1200.0

    det = build_detector(rc)
    runaway = next(r for r in det.rules if r.name == "runaway_loop")
    assert runaway.threshold == 1200.0
    assert runaway.sustain == 3.0


def test_disabled_rule_is_not_constructed(tmp_path) -> None:  # noqa: ANN001
    cfg = tmp_path / "overseer_rules.jsonc"
    cfg.write_text('{"runawayLoop": {"enabled": false}}', encoding="utf-8")
    det = build_detector(load_rule_config(cfg))
    assert not [r for r in det.rules if r.name == "runaway_loop"]
    # Transparency rules survive: a user must not be able to silence the warning
    # that their telemetry is incomplete.
    assert [r for r in det.rules if r.name == "dropped_events"]
    assert [r for r in det.rules if r.name == "degraded_probe"]


def test_broken_config_falls_back_with_a_warning(tmp_path) -> None:  # noqa: ANN001
    cfg = tmp_path / "overseer_rules.jsonc"
    cfg.write_text('{"runawayLoop": {"thresholdOpsPerSec": "fast"}}', encoding="utf-8")
    rc = load_rule_config(cfg)
    assert rc.warnings, "a wrong type must be reported, not silently ignored"
    assert rc.values == DEFAULTS, "and the defaults must still be usable"


def test_unknown_key_is_reported(tmp_path) -> None:  # noqa: ANN001
    cfg = tmp_path / "overseer_rules.jsonc"
    cfg.write_text('{"runawayLoops": {"thresholdOpsPerSec": 900}}', encoding="utf-8")
    rc = load_rule_config(cfg)
    assert "runawayLoops" in rc.unknown_keys[0]


def test_inverted_thresholds_are_flagged(tmp_path) -> None:  # noqa: ANN001
    cfg = tmp_path / "overseer_rules.jsonc"
    cfg.write_text('{"stackDepth": {"warnDepth": 2000, "overflowDepth": 1024}}', encoding="utf-8")
    rc = load_rule_config(cfg)
    assert any("warnDepth must be below overflowDepth" in w for w in rc.warnings)


def test_override_propagates_to_dependent_rules(tmp_path) -> None:  # noqa: ANN001
    """One override must move every rule that uses the runaway threshold."""
    cfg = tmp_path / "overseer_rules.jsonc"
    cfg.write_text('{"runawayLoop": {"thresholdOpsPerSec": 2000.0}}', encoding="utf-8")
    det = build_detector(load_rule_config(cfg))
    for name in ("save_bloat", "frame_time"):
        rule = next(r for r in det.rules if r.name == name)
        assert rule.runaway_threshold == 2000.0, f"{name} still uses the stale threshold"
