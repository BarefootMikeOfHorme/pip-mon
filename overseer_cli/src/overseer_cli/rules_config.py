"""Rule configuration: JSONC overrides for anomaly thresholds.

Follows the project's "config over code" preference, but with one constraint that
shapes the whole design: **a missing or partial file must be completely normal.**
The overwhelming majority of users will never open this file, and the defaults in
``ANOMALY_RULES.md`` are the documented, supported configuration.

So: no file → defaults, no warning. File with only ``runawayLoop`` → defaults
elsewhere. File with a typo → the key is reported, because a threshold that silently
became a no-op is a monitoring tool lying to its user (Rule 4, same reasoning as the
``dropped_events`` rule).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config as cfg
from .detector import (
    DegradedProbeRule,
    Detector,
    DroppedEventRule,
    FrameTimeRule,
    RunawayLoopRule,
    SaveBloatRule,
    StackDepthRule,
    VmStarvationRule,
)
from .profiler import WINDOW_SECONDS

log = logging.getLogger(__name__)

#: Defaults mirror docs/ANOMALY_RULES.md. Changing a number here without changing
#: that doc makes the documentation wrong, so they are asserted equal in
#: test_detector.py rather than left to discipline.
DEFAULTS: dict[str, Any] = {
    "windowSeconds": WINDOW_SECONDS,
    "runawayLoop": {
        "enabled": True,
        "thresholdOpsPerSec": 500.0,
        "sustainSeconds": 2.0,
    },
    "stackDepth": {
        "enabled": True,
        "warnDepth": 820,
        "overflowDepth": 1024,
    },
    "saveBloat": {
        "enabled": True,
        "workingSetGrowthMbPerSec": 1.0,
        "handleGrowthWarn": 1500,
        "handleGrowthCritical": 6000,
    },
    "frameTime": {
        "enabled": True,
        "warnMs": 33.3,
        "criticalMs": 66.7,
    },
    "vmStarvation": {
        "enabled": True,
        "minOpRate": 50.0,
        "minBusyThreads": 2,
    },
    "telemetryIntegrity": {
        # dropped_events and degraded_probe are transparency rules, not
        # heuristics. They are not user-disableable on purpose: a user must not
        # be able to silence the warning that the dashboard is incomplete.
        "droppedEventCriticalRatio": 0.05,
    },
}

#: Types per key, for validation. Nested to match DEFAULTS.
SPEC: dict[str, Any] = {
    "windowSeconds": (int, float),
    "runawayLoop": {
        "enabled": bool,
        "thresholdOpsPerSec": (int, float),
        "sustainSeconds": (int, float),
    },
    "stackDepth": {"enabled": bool, "warnDepth": int, "overflowDepth": int},
    "saveBloat": {
        "enabled": bool,
        "workingSetGrowthMbPerSec": (int, float),
        "handleGrowthWarn": int,
        "handleGrowthCritical": int,
    },
    "frameTime": {"enabled": bool, "warnMs": (int, float), "criticalMs": (int, float)},
    "vmStarvation": {"enabled": bool, "minOpRate": (int, float), "minBusyThreads": int},
    "telemetryIntegrity": {"droppedEventCriticalRatio": (int, float)},
}


@dataclass(slots=True)
class RuleConfig:
    """Validated, merged configuration with provenance."""

    values: dict[str, Any] = field(default_factory=lambda: cfg.deep_merge(DEFAULTS, {}))
    source: Path | None = None
    unknown_keys: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def section(self, name: str) -> dict[str, Any]:
        return self.values.get(name, {})

    def number(self, path: str, default: float) -> float:
        """Dotted lookup with a fallback, for call sites that must not raise."""
        node: Any = self.values
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node if isinstance(node, (int, float)) else default

    def flag(self, path: str, default: bool = True) -> bool:
        node: Any = self.values
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node if isinstance(node, bool) else default


def load_rule_config(path: str | Path | None = None) -> RuleConfig:
    """Load JSONC rule config. Never raises for a missing file."""
    found = cfg.find_config(path) if path else cfg.find_config()
    if found is None:
        return RuleConfig(source=None)

    try:
        raw = cfg.load_jsonc(found)
    except cfg.ConfigError as exc:
        # A broken config must not stop the dashboard: fall back to defaults and
        # say so, rather than leaving the user with no monitor at all.
        log.error("%s -- using built-in defaults", exc)
        return RuleConfig(source=found, warnings=[str(exc)])

    merged = cfg.deep_merge(DEFAULTS, raw)
    try:
        validated = cfg.coerce(merged, SPEC)
    except cfg.ConfigError as exc:
        log.error("%s: %s -- using built-in defaults", found, exc)
        return RuleConfig(source=found, warnings=[str(exc)])

    unknown = validated.pop("__unknown_keys__", [])
    warnings = [f"{found}: ignoring unknown key '{k}'" for k in unknown]
    for w in warnings:
        log.warning("%s", w)

    result = RuleConfig(values=validated, source=found, unknown_keys=unknown, warnings=warnings)
    _sanity_check(result)
    return result


def _sanity_check(rc: RuleConfig) -> None:
    """Catch overrides that are self-defeating or unsafe.

    Not fatal. A user who sets a nonsense threshold gets a warning and the value
    they asked for, because silently overriding user config is worse than telling
    them it will not work.
    """
    rl = rc.section("runawayLoop")
    if rl.get("sustainSeconds", 0) < 0.5:
        rc.warnings.append(
            "runawayLoop.sustainSeconds below 0.5 s will flag ordinary mod scripts "
            "that loop a container once on start"
        )
    sd = rc.section("stackDepth")
    if sd.get("warnDepth", 0) >= sd.get("overflowDepth", 1024):
        rc.warnings.append("stackDepth.warnDepth must be below overflowDepth")

    ft = rc.section("frameTime")
    if ft.get("warnMs", 0) >= ft.get("criticalMs", 66.7):
        rc.warnings.append("frameTime.warnMs must be below criticalMs")

    # A non-positive threshold disables the rule by accident rather than by
    # intent, which is the worst possible failure mode for a detector.
    if rc.number("runawayLoop.thresholdOpsPerSec", 500.0) <= 0:
        rc.warnings.append("runawayLoop.thresholdOpsPerSec must be positive")
    if rc.number("saveBloat.workingSetGrowthMbPerSec", 1.0) <= 0:
        rc.warnings.append("saveBloat.workingSetGrowthMbPerSec must be positive")
    if rc.number("windowSeconds", 5.0) < 1.0:
        rc.warnings.append("windowSeconds below 1 s makes the rate estimates unusable")


def build_detector(rc: RuleConfig | None = None) -> Detector:
    """Construct a Detector with thresholds from config.

    Rules are constructed explicitly rather than mutated, so a threshold is
    applied in exactly one place and the resulting rule set is inspectable.
    """
    rc = rc or RuleConfig()
    rules: list = [
        RunawayLoopRule(
            threshold_ops=rc.number("runawayLoop.thresholdOpsPerSec", 500.0),
            sustain=rc.number("runawayLoop.sustainSeconds", 2.0),
        ),
        SaveBloatRule(
            growth_warn_mb=rc.number("saveBloat.workingSetGrowthMbPerSec", 1.0),
            handle_warn=int(rc.number("saveBloat.handleGrowthWarn", 1500)),
            handle_critical=int(rc.number("saveBloat.handleGrowthCritical", 6000)),
            # Injected so one override of runawayLoop.thresholdOpsPerSec moves
            # every rule that depends on "what counts as hot", instead of
            # leaving save_bloat and frame_time disagreeing with runaway_loop.
            runaway_threshold=rc.number("runawayLoop.thresholdOpsPerSec", 500.0),
        ),
        StackDepthRule(
            warn_depth=int(rc.number("stackDepth.warnDepth", 820)),
            overflow_depth=int(rc.number("stackDepth.overflowDepth", 1024)),
        ),
        VmStarvationRule(
            min_op_rate=rc.number("vmStarvation.minOpRate", 50.0),
            min_busy_threads=int(rc.number("vmStarvation.minBusyThreads", 2)),
        ),
        FrameTimeRule(
            warn_ms=rc.number("frameTime.warnMs", 33.3),
            critical_ms=rc.number("frameTime.criticalMs", 66.7),
            runaway_threshold=rc.number("runawayLoop.thresholdOpsPerSec", 500.0),
        ),
        # Transparency rules: always on, thresholds fixed. Deliberately not
        # config-disableable -- see the docstring.
        DroppedEventRule(
            critical_ratio=rc.number("telemetryIntegrity.droppedEventCriticalRatio", 0.05)
        ),
        DegradedProbeRule(),
    ]

    enabled_flags = {
        "runaway_loop": rc.flag("runawayLoop.enabled", True),
        "save_bloat": rc.flag("saveBloat.enabled", True),
        "stack_depth": rc.flag("stackDepth.enabled", True),
        "frame_time": rc.flag("frameTime.enabled", True),
        "vm_starvation": rc.flag("vmStarvation.enabled", True),
    }
    rules = [r for r in rules if enabled_flags.get(r.name, True)]

    det = Detector(rules)
    # Carried so the UI can surface config warnings next to the findings rather
    # than only on stderr, where a user running the TUI will never look.
    det.config = rc  # type: ignore[attr-defined]
    return det


__all__ = [
    "DEFAULTS",
    "RuleConfig",
    "build_detector",
    "load_rule_config",
]
