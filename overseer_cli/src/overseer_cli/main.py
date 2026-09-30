"""OverseerCLI entry point.

Two modes:

  tui     the default: the three-panel Textual dashboard
  headless stream frames to stdout as JSON lines, for piping into jq or a file

The headless mode exists because a dashboard is the wrong tool when you are
post-mortemming: you want the raw timeline after a crash, written to disk, not
a UI you have to keep open. Both modes share one client and one decoder.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
from typing import TYPE_CHECKING

from . import __version__, protocol as proto
from .ipc_client import PIPE_PATH, PipeUnavailable, VLinkClient

if TYPE_CHECKING:
    pass


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="overseer-cli",
        description="PIP-MON: out-of-process Papyrus telemetry dashboard for Fallout 4.",
        epilog=(
            "Requires vprobe.dll loaded in the game. The dashboard waits for the "
            "pipe rather than failing, so you can start it before or after launch."
        ),
    )
    p.add_argument("--pipe", default=PIPE_PATH, help="V-Link pipe path (default: %(default)s)")
    p.add_argument(
        "--mode",
        choices=("tui", "headless"),
        default="tui",
        help="tui: interactive dashboard. headless: JSON lines to stdout.",
    )
    p.add_argument(
        "--output", "-o", help="headless mode: write JSON lines here instead of stdout"
    )
    p.add_argument(
        "--config",
        help="path to a JSONC rule config (default: ./overseer_rules.jsonc if present)",
    )
    p.add_argument(
        "--low-detail",
        action="store_true",
        help="drain fewer frames per tick; use if the terminal cannot keep up",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="headless mode: exit when the probe disconnects instead of retrying",
    )
    p.add_argument("-v", "--verbose", action="count", default=0, help="repeat for more logging")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # The environment gate. It is a flag rather than a subcommand so that the
    # documented `tui` / `headless` invocations keep working exactly as they
    # are, and it short-circuits before any pipe or Textual import: the gate has
    # to be runnable with no game, no editor and no dashboard, because that is
    # one of the three hosts it exists to report on (G16 -- everything that
    # matters is reachable from a command line first).
    p.add_argument(
        "--verify",
        action="store_true",
        help="run the environment gate and exit (no game required)",
    )
    p.add_argument(
        "--depth", type=int, choices=(0, 1, 2), default=1,
        help="--verify depth: 0 verdict, 1 per-check, 2 adds evidence",
    )
    p.add_argument(
        "--layer", action="append", default=None,
        help="--verify: restrict to a layer (repeatable): "
             "artefact identity deploy editor runtime",
    )
    p.add_argument(
        "--json", action="store_true",
        help="--verify: machine-readable output",
    )
    return p

def _configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr,
    )


async def _run_headless(args: argparse.Namespace) -> int:
    out = open(args.output, "w", encoding="utf-8", buffering=1) if args.output else sys.stdout
    try:
        async with VLinkClient(args.pipe, reconnect=not args.once) as client:
            print(
                f"# OverseerCLI {__version__} headless -> {args.pipe}", file=sys.stderr
            )
            async for frame in client.frames():
                record = {
                    "t": frame.timestamp,
                    "seq": frame.sequence,
                    "os_tid": frame.thread_id,
                    "ev": frame.event_type.name.lower(),
                }
                p = frame.payload
                if p is not None:
                    record["data"] = _jsonable(p)
                print(json.dumps(record, separators=(",", ":")), file=out, flush=True)
                if args.once and not client.stats.connected:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if out is not sys.stdout:
            out.close()
    return 0


def _jsonable(payload: object) -> object:
    """Convert a decoded payload dataclass to plain JSON types.

    ``dataclasses.asdict`` would work, but it is noticeably slower and we call
    this once per frame in headless mode; the explicit mapping is a straight
    field read.
    """
    from dataclasses import fields, is_dataclass
    from enum import Enum

    if isinstance(payload, Enum):
        return payload.name.lower()
    if is_dataclass(payload) and not isinstance(payload, type):
        return {f.name: _jsonable(getattr(payload, f.name)) for f in fields(payload)}
    if isinstance(payload, (list, tuple)):
        return [_jsonable(v) for v in payload]
    if isinstance(payload, float):
        # Keep the JSON small: telemetry precision beyond 3 decimals is noise.
        return round(payload, 3)
    return payload


async def _run_tui(args: argparse.Namespace) -> int:
    from .rules_config import build_detector, load_rule_config
    from .ui import OverseerApp

    rule_config = load_rule_config(args.config)
    for w in rule_config.warnings:
        print(f"config: {w}", file=sys.stderr)
    if rule_config.source:
        print(f"config: loaded {rule_config.source}", file=sys.stderr)
    else:
        print("config: no overseer_rules.jsonc found, using built-in defaults", file=sys.stderr)

    async with VLinkClient(args.pipe) as client:
        app = OverseerApp(
            client,
            detector=build_detector(rule_config),
            low_detail=args.low_detail,
        )
        # Textual installs its own SIGINT handler; make Ctrl-C close the client
        # cleanly so the probe sees a tidy disconnect and does not log a fault.
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, app.exit)
            except NotImplementedError:
                pass  # Windows event loop: Textual handles it.
        await app.run_async()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _configure_logging(args.verbose)

    # Before the platform warning: the gate is the one path that must work
    # everywhere, including a non-Windows dev box, where it reports hosts as
    # absent rather than refusing to run.
    if args.verify:
        from .envgate import main as gate_main

        gate_argv: list[str] = ["--depth", str(args.depth)]
        for layer in args.layer or []:
            gate_argv += ["--layer", layer]
        if args.json:
            gate_argv.append("--json")
        if args.pipe != PIPE_PATH:
            # The gate reads the filesystem, not the wire. Say so rather than
            # accepting a flag that would silently do nothing.
            print(
                "note: --pipe does not affect --verify; the gate reads artefacts "
                "and recorded runs, and never opens the V-Link pipe.",
                file=sys.stderr,
            )
        return gate_main(gate_argv)

    if sys.platform != "win32":
        # Not fatal: the protocol layer is testable anywhere, and someone may be
        # developing from WSL. Warn clearly and continue.
        print(
            "warning: V-Link uses Win32 named pipes; running on "
            f"{sys.platform} will not connect to the game.",
            file=sys.stderr,
        )

    if args.mode == "headless":
        return asyncio.run(_run_headless(args))
    return asyncio.run(_run_tui(args))


if __name__ == "__main__":
    raise SystemExit(main())
