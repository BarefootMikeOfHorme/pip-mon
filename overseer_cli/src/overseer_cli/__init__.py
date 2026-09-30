"""PIP-MON Component 2: OverseerCLI.

Out-of-process diagnostic engine and terminal dashboard for Fallout 4. Consumes
V-Link frames from ``\\\\.\\pipe\\vlink_telemetry`` produced by vprobe.dll,
runs the profiling and anomaly heuristics, and renders the TUI.

Nothing in this package loads into the game process. It has no write access to
the game directory and issues no Win32 calls other than opening the pipe.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
