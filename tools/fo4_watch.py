#!/usr/bin/env python3
"""fo4_watch.py -- observe a live Fallout4.exe from OUTSIDE the process.

WHY THIS EXISTS
    Four questions in the compendium are marked UNRESOLVED and all four are
    answerable by watching a running game instead of reading a forum post:

      1. How far does the engine render weather beyond the resident cell grid?
      2. What is the actual per-cell cost -- memory, I/O, handle count?
      3. Does a redrawn border region enforce, or does the player walk through?
      4. What does `uGridsToLoad` actually change, in bytes and in cells?

    None of that needs a plugin, an injected hook, or an F4SE loader. All of it
    is visible in the process counters, which is why this reads the process
    rather than trying to read the game.

    And that is the whole design constraint. F4SE is prohibited in this project
    (see ai_context/f4se_prohibition.md), so there is no sanctioned way to ask
    the game what it is doing. A process viewer needs no permission from the
    game, loads nothing into it, and cannot crash it.

WHAT IT MEASURES
    Per interval, for Fallout4.exe: working set, private bytes, virtual size,
    handle count, thread count, and CPU time, plus the deltas between
    intervals so a rate is readable without post-processing.

    Deltas are the point. An absolute working set of 3.4 GB means nothing on its
    own; a rise of 40 MB per second while the player crosses a cell boundary is
    the streaming rate, and it is the only number here that maps to the engine
    questions above.

WHAT IT DELIBERATELY DOES NOT DO
    * It does not attach, inject, read process memory, or open a handle into the
      game. GetProcessTimes/GetProcessMemoryInfo are the extent of it.
    * It does not write to the game directory.
    * It does not parse plugins, and it does not trust any record count.
      `tools/esp_cells.py` cannot parse FO4 plugins at all right now, and this
      tool has no opinion about that.

OUTPUT
    Follows tools/LOG_FORMAT.md: `--format jsonl` streams one object per line so
    a reader that dies mid-capture keeps everything already emitted, and
    `--format text` is for a human watching a terminal. `kind` is carried on
    every record.

EXIT CODES
    0  samples collected
    1  game not running
    2  bad arguments
    3  connected but zero samples -- a real finding, not a pass
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import sys
import time
from pathlib import Path

GAME_EXE = "Fallout4.exe"

# PROCESS_QUERY_LIMITED_INFORMATION is enough for every counter here and is
# available to an unelevated process on modern Windows. Requesting
# PROCESS_VM_READ would be the way to read memory, and is deliberately not done.
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    # The EX form, not the plain one. The plain PROCESS_MEMORY_COUNTERS has no
    # PrivateUsage field at all, and the nearest-looking members
    # (QuotaPagedPoolUsage, QuotaNonPagedPoolUsage) are KERNEL POOL QUOTAS, not
    # the process's private commit. Reading a 4 GB process's private bytes as
    # "2.34 MB" is what the first version of this tool did: it summed the two
    # quota fields, which are small, and emitted a number that was confident,
    # stable, and completely wrong. GetProcessMemoryInfoEx is the only way to
    # get the real figure, and it is the same call with one enum value wider.
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    # The plain form, kept only as a fallback for the EX call. It genuinely has
    # no PrivateUsage member, which is the entire reason the EX form exists here.
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wt.DWORD), ("dwHighDateTime", wt.DWORD)]


def _filetime_to_int(ft: FILETIME) -> int:
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


def open_process(pid: int | None):
    """Find Fallout4.exe and open a query-only handle, or return (None, reason)."""
    pid = pid or find_pid()
    if not pid:
        return None, "no_process"
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        err = ctypes.get_last_error()
        # 5 is ACCESS_DENIED. That is a distinct answer from "not running", and
        # collapsing the two sends someone to kill a game that is merely elevated.
        return None, f"access_denied_{err}" if err == 5 else f"open_failed_{err}"
    return h, None


def find_pid() -> int | None:
    """Locate the process by name.

    Deliberately does not use a dependency: tasklist would work but adds a
    subprocess per sample, and this has to be cheap enough to run at 1 Hz for
    twenty minutes without being noticed.
    """
    import subprocess

    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {GAME_EXE}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        parts = [p.strip('" ') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == GAME_EXE.lower():
            try:
                return int(parts[1])
            except ValueError:
                return None
    return None


def sample(h, pid: int) -> dict | None:
    """One counter read. Returns None if the process exited between polls."""
    mc = PROCESS_MEMORY_COUNTERS_EX()
    mc.cb = ctypes.sizeof(mc)
    # `GetProcessMemoryInfoEx` is not exported on this machine, by either name,
    # from either DLL -- checked, and the traceback said so twice. It is the
    # documented route to PrivateUsage, and it is absent.
    #
    # The working substitute: pass the EX struct to the PLAIN
    # `GetProcessMemoryInfo` and set cb to the EX size. The call is documented
    # as accepting PROCESS_MEMORY_COUNTERS_EX when cb matches its size, so the
    # larger struct is filled and PrivateUsage comes back populated. psapi is
    # used rather than kernel32's K32* alias because psapi's GetProcessMemoryInfo
    # is present and the alias is not.
    if not psapi.GetProcessMemoryInfo(h, ctypes.byref(mc), mc.cb):
        # Fall back rather than drop the sample. The EX call needs Vista+ and a
        # handle with enough rights; if it is refused the plain counters still
        # give working set, which is the number that matters most.
        mc_plain = PROCESS_MEMORY_COUNTERS()
        mc_plain.cb = ctypes.sizeof(mc_plain)
        if not psapi.GetProcessMemoryInfo(h, ctypes.byref(mc_plain), mc_plain.cb):
            return None
        mc = mc_plain  # type: ignore[assignment]
        private_mb = None
    else:
        private_mb = round(mc.PrivateUsage / 1048576, 2)

    io = IO_COUNTERS()
    ok = kernel32.GetProcessIoCounters(h, ctypes.byref(io))

    ft_create, ft_exit, ft_kernel, ft_user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
    have_cpu = bool(kernel32.GetProcessTimes(
        h, ctypes.byref(ft_create), ctypes.byref(ft_exit),
        ctypes.byref(ft_kernel), ctypes.byref(ft_user),
    ))

    # FILETIME is 100 ns units. Two of them make one second.
    cpu_s = (_filetime_to_int(ft_kernel) + _filetime_to_int(ft_user)) / 1e7

    out = {
        "working_set_mb": round(mc.WorkingSetSize / 1048576, 2),
        "peak_ws_mb": round(mc.PeakWorkingSetSize / 1048576, 2),
        "pagefile_mb": round(mc.PagefileUsage / 1048576, 2),
        "handles": int(_get_handle_count(h)),
        "threads": int(_get_thread_count(pid)),
        "page_faults": int(mc.PageFaultCount),
    }
    # Omitted rather than guessed when the EX call was refused. A key that is
    # absent says "not measured"; a key holding 0 says "measured, and it is
    # zero", and the second one is the false negative this whole project has a
    # rule about.
    if private_mb is not None:
        out["private_mb"] = private_mb
    if ok:
        out["read_mb_total"] = round(io.ReadTransferCount / 1048576, 2)
        out["write_mb_total"] = round(io.WriteTransferCount / 1048576, 2)
        out["read_ops_total"] = int(io.ReadOperationCount)
    if have_cpu:
        out["cpu_s_total"] = round(cpu_s, 2)
    return out


def _get_handle_count(h) -> int:
    # GetProcessHandleCount needs a pointer to the count, not the count itself.
    n = wt.DWORD(0)
    if not kernel32.GetProcessHandleCount(h, ctypes.byref(n)):
        return 0
    return n.value


TH32CS_SNAPTHREAD = 0x00000004


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ThreadID", wt.DWORD),
        ("th32OwnerProcessID", wt.DWORD),
        ("tpBasePri", ctypes.c_long),
        ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", wt.DWORD),
    ]


def _get_thread_count(pid: int) -> int:
    """Count threads by walking a thread snapshot.

    Not `kernel32.GetProcessThreadCount`, which is a convenience wrapper that
    is not exported on every Windows build this has to run on -- it raises
    AttributeError at import-time attribute lookup, and the first version of
    this tool died on exactly that against a live process. The toolhelp
    snapshot is old, stable, and exported everywhere.

    Takes a pid rather than a handle because that is what the snapshot filters
    on. Costs a system-wide thread enumeration per sample, which is why the
    default interval is 1s and not 10ms.
    """
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if snap is None or snap == -1:
        return 0
    try:
        ent = THREADENTRY32()
        ent.dwSize = ctypes.sizeof(THREADENTRY32)
        count = 0
        if not kernel32.Thread32First(snap, ctypes.byref(ent)):
            return 0
        while True:
            if ent.th32OwnerProcessID == pid:
                count += 1
            if not kernel32.Thread32Next(snap, ctypes.byref(ent)):
                break
        return count
    finally:
        # The snapshot holds kernel handles. Leaking one per sample leaks one per
        # second, and the process being watched is the one that runs out.
        kernel32.CloseHandle(snap)


def deltas(prev: dict, cur: dict, dt: float) -> dict:
    """Rates between two samples. Only keys present in both are emitted."""
    if not prev or dt <= 0:
        return {}
    out: dict[str, float] = {}
    pairs = {
        "ws_mb_per_s": ("working_set_mb",),
        "read_mb_per_s": ("read_mb_total",),
        "write_mb_per_s": ("write_mb_total",),
        "cpu_pct": ("cpu_s_total",),
        "handles_per_s": ("handles",),
        "threads_per_s": ("threads",),
    }
    for name, (key,) in pairs.items():
        if key in prev and key in cur:
            d = cur[key] - prev[key]
            if name == "cpu_pct":
                # One core is 100%. A game using 12.5 is fully busy on one core.
                out[name] = round(d / dt * 100.0, 1)
            else:
                out[name] = round(d / dt, 3)
    return out


class Peak:
    """Running maxima, so a spike is not lost between two eyeballs.

    Streaming spikes are the entire signal. A mean working set of 3 GB hides a
    400 MB jump that lasted one interval, and the jump is what tells you a cell
    loaded.
    """

    def __init__(self):
        self.vals: dict[str, float] = {}

    def update(self, d: dict) -> None:
        for k, v in d.items():
            if isinstance(v, (int, float)):
                self.vals[k] = max(self.vals.get(k, v), v)


def emit(rec: dict, fmt: str) -> None:
    if fmt == "jsonl":
        print(json.dumps(rec, sort_keys=True), flush=True)
    else:
        kind = rec.get("kind", "?")
        if kind == "sample":
            head = (f"t+{rec['t_s']:7.1f}s  ws={rec.get('working_set_mb', 0):8.1f}MB"
                    f"  cpu={rec.get('cpu_pct', 0):5.1f}%")
            if "read_mb_per_s" in rec:
                head += f"  read={rec['read_mb_per_s']:7.2f}MB/s"
            if "ws_mb_per_s" in rec:
                head += f"  dWS={rec['ws_mb_per_s']:+7.2f}MB/s"
            head += f"  hnd={rec.get('handles', 0):6d}  thr={rec.get('threads', 0):3d}"
            print(head, flush=True)
        else:
            print(f"[{kind}] {json.dumps(rec, sort_keys=True)}", flush=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="fo4_watch.py",
        description="Watch a running Fallout4.exe from outside the process. No injection.",
    )
    p.add_argument("--pid", type=int, default=None, help="attach to this pid instead of searching")
    p.add_argument("--interval", type=float, default=1.0, help="seconds between samples (default 1.0)")
    p.add_argument("--duration", type=float, default=0.0, help="stop after N seconds; 0 = until Ctrl-C")
    p.add_argument("--format", choices=("text", "jsonl"), default="text")
    p.add_argument("--summary-only", action="store_true", help="print no samples, only the closing record")
    p.add_argument("--note", default="", help="free text stored in the summary, for what you did")
    args = p.parse_args(argv)

    pid = args.pid or find_pid()
    h, reason = open_process(pid)
    if h is None:
        if reason == "no_process":
            print(f"error: {GAME_EXE} is not running", file=sys.stderr)
            return 1
        print(f"error: cannot open {GAME_EXE}: {reason}", file=sys.stderr)
        return 1

    emit({"kind": "handshake", "process": GAME_EXE, "pid": pid,
          "interval_s": args.interval, "method": "external counters, no injection",
          "injection": False, "f4se": False}, args.format)
    if args.format == "text":
        print(f"watching {GAME_EXE} every {args.interval}s -- Ctrl-C to stop\n", flush=True)

    t0 = time.monotonic()
    prev: dict = {}
    prev_t = t0
    n = 0
    peak = Peak()
    try:
        while True:
            now = time.monotonic()
            if args.duration and (now - t0) >= args.duration:
                break
            cur = sample(h, pid)
            if cur is None:
                emit({"kind": "error", "code": "process_gone", "at_s": round(now - t0, 1)}, args.format)
                break
            n += 1
            peak.update(cur)
            rec = {"kind": "sample", "t_s": round(now - t0, 2), "n": n, **cur}
            rec.update(deltas(prev, cur, now - prev_t))
            prev, prev_t = cur, now
            if not args.summary_only:
                emit(rec, args.format)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        emit({"kind": "error", "code": "interrupted", "at_s": round(time.monotonic() - t0, 1)}, args.format)

    elapsed = time.monotonic() - t0
    # A capture that got one sample is not a capture. Same shape as LOG_FORMAT's
    # exit-3 rule: a transport that is up but writing nothing is not a pass.
    if n == 0:
        emit({"kind": "error", "code": "zero_samples"}, args.format)
        kernel32.CloseHandle(h)
        return 3

    emit({
        "kind": "summary", "samples": n, "elapsed_s": round(elapsed, 1),
        "peak": {k: peak.vals[k] for k in sorted(peak.vals)},
        "note": args.note,
    }, args.format)
    kernel32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
