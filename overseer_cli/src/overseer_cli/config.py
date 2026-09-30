"""JSONC configuration loading.

Fallout 4 does not parse JSON natively; F4SE plugins do, and mod authors edit these
files by hand. Standard JSON forces them to strip comments and trailing commas before
saving, which produces syntax errors and a bad experience. So the on-disk format is
JSONC.

The comment stripping is deliberately minimal and conservative: it is a *lexer* pass
that tracks string literals, so a ``//`` inside a string value is not treated as a
comment. A regex-based strip cannot do that correctly, and this project uses paths and
regex-ish values in its config.

Note this is only ever used for on-disk config. The V-Link telemetry stream is binary
and never goes near a JSON parser on the hot path (see docs/IPC_PROTOCOL.md §1).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")

DEFAULT_CONFIG_NAMES: tuple[str, ...] = (
    "overseer_rules.jsonc",
    "overseer_rules.json",
    "pipmon.jsonc",
    "pipmon.json",
)


class ConfigError(Exception):
    """Raised for a config file that exists but cannot be used.

    A *missing* file is never an error; it means built-in defaults. Only a file
    that is present and broken raises, because silently ignoring a typo'd
    threshold would be a monitoring tool lying to its user.
    """


def strip_jsonc(text: str) -> str:
    """Remove ``//`` and ``/* */`` comments and trailing commas.

    Tracks string state and escapes so a comment marker inside a quoted value is
    preserved. Preserves line numbering by replacing removed comment characters
    with spaces rather than deleting them, so JSON parse errors report the right
    line.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escaped = False

    while i < n:
        ch = text[i]

        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                # Line comment: blank it, keep the newline.
                while i < n and text[i] != "\n":
                    out.append(" ")
                    i += 1
                continue
            if nxt == "*":
                # Block comment: blank it but preserve newlines for line numbers.
                out.append("  ")
                i += 2
                while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                    out.append("\n" if text[i] == "\n" else " ")
                    i += 1
                if i < n:
                    out.append("  ")
                    i += 2
                continue

        out.append(ch)
        i += 1

    return _strip_trailing_commas("".join(out))


def _strip_trailing_commas(text: str) -> str:
    """Remove ``,`` immediately before ``}`` or ``]``, outside strings."""
    out: list[str] = []
    in_string = False
    escaped = False
    pending_comma: int | None = None

    for ch in text:
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            pending_comma = None
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            pending_comma = None
            continue

        if ch == ",":
            # Defer: this comma may turn out to be trailing.
            pending_comma = len(out)
            out.append(ch)
            continue

        if ch in "}]" and pending_comma is not None:
            # Everything between the comma and here was whitespace, so this is a
            # trailing comma.
            out[pending_comma] = " "
            pending_comma = None
            out.append(ch)
            continue

        if not ch.isspace():
            # Whitespace must NOT clear the pending comma. A trailing comma
            # followed by a line comment (which strip_jsonc has already blanked
            # into spaces) is still a trailing comma, and treating the spaces as
            # significant is what made this fail on realistic config files.
            pending_comma = None
        out.append(ch)

    return "".join(out)


def load_jsonc(path: str | Path) -> dict[str, Any]:
    """Parse a JSONC file. Raises :class:`ConfigError` with the file and line."""
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConfigError(f"cannot read {p}: {exc}") from exc

    try:
        data = json.loads(strip_jsonc(raw))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{p}:{exc.lineno}: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"{p}: top level must be an object, got {type(data).__name__}")
    return data


def find_config(start: str | Path | None = None, *extra: str) -> Path | None:
    """Search for a config file. Returns None if none exists (use defaults)."""
    candidates: list[Path] = []
    if start is not None:
        base = Path(start)
        candidates += [base, base / f"{base.stem}.jsonc" if base.suffix else base / "overseer_rules.jsonc"]
    if extra:
        candidates += [Path(e) for e in extra]
    candidates += [Path.cwd() / name for name in DEFAULT_CONFIG_NAMES]

    seen: set[Path] = set()
    for c in candidates:
        c = c.expanduser()
        if c in seen:
            continue
        seen.add(c)
        if c.is_file():
            return c
    return None


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base``.

    Nested dicts merge; every other type (including lists) replaces. A list of
    thresholds in a config is a deliberate override, not something to append to
    defaults.
    """
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def coerce(data: dict[str, Any], spec: dict[str, Any], path: str = "") -> dict[str, Any]:
    """Validate and coerce a config against a spec.

    ``spec`` maps key -> python type (or tuple of types). Unknown keys are
    **dropped with the key names returned**, because a config typo should be
    visible rather than silently inert. A wrong type is an error: better to fail
    at startup than to run a monitor with a threshold that quietly became 0.
    """
    out: dict[str, Any] = {}
    unknown: list[str] = []
    errors: list[str] = []

    for key, value in data.items():
        full = f"{path}.{key}" if path else key
        if key not in spec:
            unknown.append(full)
            continue
        expected = spec[key]
        if isinstance(value, dict) and isinstance(expected, dict):
            out[key] = coerce(value, expected, full)
            continue
        if not isinstance(value, expected):
            names = (
                expected.__name__
                if isinstance(expected, type)
                else "/".join(t.__name__ for t in expected)
            )
            errors.append(f"{full}: expected {names}, got {type(value).__name__}")
            continue
        out[key] = value

    if errors:
        raise ConfigError("; ".join(errors))
    if unknown:
        out["__unknown_keys__"] = unknown
    return out


__all__ = [
    "ConfigError",
    "coerce",
    "deep_merge",
    "find_config",
    "load_jsonc",
    "strip_jsonc",
]
