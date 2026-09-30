"""Fake V-Link probe.

A standalone, pure-Python producer that speaks the real binary protocol on a
real Win32 named pipe. It exists so the whole stack -- framing, decoding,
profiling, detection, TUI -- is testable end to end without launching Fallout 4.

It is also the answer to "how do I reproduce a runaway loop report": the
scenarios below are the ones users actually report, so they double as
regression fixtures for the detector.

Run it directly::

    python tests/fake_probe.py --scenario runaway
    overseer-cli --mode headless
"""

from __future__ import annotations

import argparse
import ctypes
import math
import random
import sys
import time
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from overseer_cli import protocol as proto  # noqa: E402

PIPE_NAME = r"\\.\pipe\vlink_telemetry"

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD] + [wintypes.DWORD] * 5
_k32.CreateNamedPipeW.restype = wintypes.HANDLE
_k32.ConnectNamedPipe.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_k32.ConnectNamedPipe.restype = wintypes.BOOL
_k32.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_k32.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_char_p, wintypes.DWORD,
                           ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
_k32.WriteFile.restype = wintypes.BOOL

PIPE_ACCESS_OUTBOUND = 0x00000004
PIPE_TYPE_BYTE = 0x00000000
PIPE_READMODE_BYTE = 0x00000000
PIPE_WAIT = 0x00000000
PIPE_UNLIMITED_INSTANCES = 255
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

# Papyrus' hard stack limit, from the VM's own stack check.
PAPYRUS_STACK_LIMIT = 1024


def _f(values: tuple) -> bytes:
    """Pack a float tuple with the protocol's float format."""
    import struct

    return struct.pack(f"<{len(values)}f", *values)


class FakeProbe:
    def __init__(self, scenario: str = "healthy", hz: int = 60) -> None:
        self.scenario = scenario
        self.hz = hz
        self.seq = 0
        self.start = time.perf_counter()
        self.qpc = int(time.perf_counter() * 1e7)  # stand-in for QPC ticks
        self.op_total = 0
        self.op_accum = 0.0
        self.mem_mb = 3200.0
        self.handles = 4200
        self.frame_ms = 16.7

    # -- frame helpers ----------------------------------------------------

    def _frame(self, et: proto.EventType, payload: bytes, os_tid: int = 0) -> bytes:
        self.seq += 1
        return proto.pack_frame(
            et,
            payload,
            timestamp=self.qpc,
            sequence=self.seq,
            thread_id=os_tid or 1000 + (self.seq % 4),
        )

    def heartbeat(self, active: int, queued: int, dropped: int = 0) -> bytes:
        return self._frame(
            proto.EventType.HEARTBEAT,
            proto._HEARTBEAT.pack(
                time.perf_counter() - self.start,
                int((time.perf_counter() - self.start) * self.hz),
                self.frame_ms,
                active,
                queued,
                self.seq,
                dropped,
            ),
        )

    def vm_tick(
        self,
        thread_id: int,
        ops: int,
        rate: float,
        form_id: int = 0,
        depth: int = 0,
        waiting: bool = False,
        window_ms: float = 0.5,
    ) -> bytes:
        return self._frame(
            proto.EventType.VM_TICK,
            proto._VM_TICK.pack(
                thread_id, ops, self.op_total, window_ms, rate, form_id,
                int(waiting), depth, 0,
            ),
            os_tid=2000 + thread_id,
        )

    def thread_state(
        self, thread_id: int, phase: proto.ThreadPhase, form_id: int = 0, depth: int = 0
    ) -> bytes:
        return self._frame(
            proto.EventType.THREAD_STATE,
            # _THREAD_STATE is <IIIfHBBB = 8 fields: threadId, waitEventMask, formId,
    # waitSeconds, depth, phase, waiting, reserved. The previous call passed
    # only 7, so this raised "pack expected 8 items" the moment a thread-state
    # scenario ran. Corrected to the real field order.
    proto._THREAD_STATE.pack(thread_id, 0, form_id, 0.0, depth, int(phase), 0, 0),
        )

    def stack_dump(self, thread_id: int, form_id: int, script_name_id: int, depth: int) -> bytes:
        frames = b"".join(
            proto._STACK_FRAME.pack(form_id, script_name_id, 0, d, 0, 1.0)
            for d in range(min(depth, proto.MAX_STACK_DEPTH))
        )
        head = proto._STACK_DUMP_HEAD.pack(
            thread_id, min(depth, proto.MAX_STACK_DEPTH),
            int(depth > proto.MAX_STACK_DEPTH), 0, float(depth) * 1.0,
        )
        return self._frame(proto.EventType.STACK_DUMP, head + frames)

    def memory(self, papyrus_threads: int) -> bytes:
        return self._frame(
            proto.EventType.MEMORY,
            proto._MEMORY.pack(
                int(self.mem_mb * 1024 * 1024),
                int(self.mem_mb * 0.6 * 1024 * 1024),
                int(self.mem_mb * 1024 * 1024 * 2),
                int(self.mem_mb * 1024 * 1024),
                self.handles,
                180 + papyrus_threads,
                papyrus_threads,
                0,
            ),
        )

    def exception(self, form_id: int, script_name_id: int, cls: proto.VmErrorClass) -> bytes:
        return self._frame(
            proto.EventType.VM_EXCEPTION,
            # _VM_EXCEPTION is <IIBBHHIf = 8 fields; the previous call passed 7 and
    # raised on use. depthAtThrow is the missing one.
    proto._VM_EXCEPTION.pack(form_id, script_name_id, int(cls), 0, 0, 0, 0, 0.0),
        )

    def save_bloat(self, form_id: int, reason: proto.BloatReason, records: int) -> bytes:
        return self._frame(
            proto.EventType.SAVE_BLOAT,
            proto._SAVE_BLOAT.pack(int(reason), form_id, 0, 0, records, 0.8),
        )

    def mod_load(self, form_id: int, mod_index: int, source_name_id: int) -> bytes:
        return self._frame(
            proto.EventType.MOD_LOAD,
            proto._MOD_LOAD.pack(form_id, mod_index, source_name_id, 1),
        )

    def diag(self, text: str, level: proto.DiagLevel = proto.DiagLevel.INFO) -> bytes:
        body = text.encode("utf-8")
        return self._frame(
            proto.EventType.PLUGIN_DIAG, proto._PLUGIN_DIAG.pack(int(level), len(body)) + body
        )

    # -- scenarios ---------------------------------------------------------

    def _on_connect(self) -> list[bytes]:
        """Sent once, like the probe does on attach: name table + report."""
        out = [
            self.diag('{"names":["Script_TCMain","Script_WorkshopRef","Script_QuestTick"]}'),
            self.diag(
                '{"kind":"resolver_report","tier1":4,"tier2":2,"rejected":0,"missing":0,'
                '"entries":[{"name":"PapyrusScript::Execute","state":"addresslib","rva":1234},'
                '{"name":"PapyrusVM::DebugPrint","state":"scan","rva":5678}]}'
            ),
            self.mod_load(0x001A0001, 0x00, 0),
            self.mod_load(0x01001234, 0x01, 1),
            self.mod_load(0x05005678, 0x05, 2),
        ]
        return out

    def tick(self, t: float) -> list[bytes]:
        """One simulated frame at time ``t`` seconds."""
        out: list[bytes] = []
        s = self.scenario
        self.qpc = int(t * 1e7)
        self.op_total += 64

        if s == "healthy":
            self.op_accum += 1
            if int(self.op_accum) % 4 == 0:
                out.append(self.vm_tick(1, self.op_total, 40.0 + random.random() * 30, 0x01001234, 2))
            if int(self.op_accum) % 17 == 0:
                out.append(self.vm_tick(2, self.op_total, 12.0, 0x05005678, 1, waiting=True))
            self.frame_ms = 16.7 + random.random() * 2
            self.mem_mb += random.random() * 0.4
            self.handles += random.randint(-3, 8)
            out.append(self.heartbeat(1, 0))

        elif s == "runaway":
            # A tight loop at ~3200 ops/s, the classic endless-while pattern.
            out.append(self.vm_tick(7, self.op_total, 3200.0 + math.sin(t) * 200, 0x05005678, 3))
            out.append(self.stack_dump(7, 0x05005678, 0, 4))
            self.frame_ms = 34 + math.sin(t) * 3
            self.mem_mb += 6.0  # ~6 MiB/s growth
            self.handles += 240
            out.append(self.heartbeat(1, 0))

        elif s == "recursion":
            depth = min(int(t * 90), PAPYRUS_STACK_LIMIT + 20)
            out.append(self.vm_tick(9, self.op_total, 800.0, 0x05005678, depth))
            out.append(self.stack_dump(9, 0x05005678, 0, depth))
            self.frame_ms = 41
            out.append(self.heartbeat(1, 0))
            if depth >= PAPYRUS_STACK_LIMIT:
                out.append(self.exception(0x05005678, 0, proto.VmErrorClass.STACK_OVERFLOW))

        elif s == "saturation":
            for i in range(1, 9):
                out.append(self.vm_tick(i, self.op_total, 700.0 + i * 30, 0x01001234 + i, 2))
            self.frame_ms = 38
            out.append(self.heartbeat(8, 12))

        elif s == "degraded":
            # Some probes unresolved: exercises the DegradedProbeRule path.
            out.append(self.diag(
                '{"kind":"resolver_report","tier1":2,"tier2":0,"rejected":1,"missing":2,'
                '"entries":[{"name":"PapyrusScript::Execute","state":"addresslib","rva":1},'
                '{"name":"PapyrusThread::Execute","state":"missing","rva":0},'
                '{"name":"PapyrusVM::DebugPrint","state":"rejected","rva":0}]}'
            ))
            out.append(self.vm_tick(1, self.op_total, 50.0, 0x01001234, 1))
            out.append(self.heartbeat(1, 0))

        elif s == "savebloat":
            out.append(self.vm_tick(3, self.op_total, 2400.0, 0x01001234, 4))
            self.mem_mb += 9.0
            self.handles += 900
            out.append(self.save_bloat(0x01001234, proto.BloatReason.UNBOUNDED_LOOP, 48000))
            out.append(self.heartbeat(1, 0))

        if int(t * 2) % 2 == 0:
            out.append(self.memory(1))
        if int(t) % 1 == 0:
            out.append(self.heartbeat(1, 0))
        return out


def serve(scenario: str, hz: int, duration: float | None) -> int:
    handle = _k32.CreateNamedPipeW(
        PIPE_NAME,
        PIPE_ACCESS_OUTBOUND,
        PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_UNLIMITED_INSTANCES,
        PIPE_UNLIMITED_INSTANCES,
        65536, 65536, 250, None,
    )
    if handle == INVALID_HANDLE_VALUE:
        print(f"error: CreateNamedPipeW failed ({ctypes.get_last_error()})", file=sys.stderr)
        return 1

    print(f"fake vprobe listening on {PIPE_NAME} (scenario={scenario})", file=sys.stderr)
    _k32.ConnectNamedPipe(handle, None)

    probe = FakeProbe(scenario, hz)
    start = time.perf_counter()
    dt = 1.0 / hz

    def write(blob: bytes) -> None:
        buf = ctypes.c_char * len(blob)
        ctypes.memmove(buf, blob, len(blob))
        written = wintypes.DWORD(0)
        if not _k32.WriteFile(handle, buf, len(blob), ctypes.byref(written), None):
            raise OSError(ctypes.get_last_error(), "WriteFile failed")

    try:
        for frame in probe._on_connect():
            write(frame)
        while True:
            t = time.perf_counter() - start
            if duration and t > duration:
                break
            for frame in probe.tick(t):
                write(frame)
            time.sleep(dt)
    except OSError as exc:
        print(f"consumer disconnected: {exc}", file=sys.stderr)
    finally:
        _k32.DisconnectNamedPipe(handle)
        _k32.CloseHandle(handle)
    return 0


SCENARIOS = ("healthy", "runaway", "recursion", "saturation", "degraded", "savebloat")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", choices=SCENARIOS, default="healthy")
    p.add_argument("--hz", type=int, default=60)
    p.add_argument("--duration", type=float, default=0, help="0 = run until Ctrl-C")
    a = p.parse_args()
    if sys.platform != "win32":
        print("fake_probe requires Windows named pipes", file=sys.stderr)
        return 1
    return serve(a.scenario, a.hz, a.duration or None)


if __name__ == "__main__":
    raise SystemExit(main())
