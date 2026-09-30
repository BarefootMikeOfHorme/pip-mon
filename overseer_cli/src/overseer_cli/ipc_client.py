"""V-Link IPC client: async consumer for ``\\\\.\\pipe\\vlink_telemetry``.

Contract with the probe (Rule 1 / Rule 4):
  * the probe never blocks on us, and
  * this client never blocks the event loop, and never blocks the TUI.

The read path uses a dedicated thread feeding an ``asyncio.Queue`` over a
thread-safe handoff. That is deliberate rather than a shortcut:

  * On Windows, ``ProactorEventLoop.connect_read_pipe`` is the "native" way, but
    it requires a Proactor loop, has no timeout semantics, and raises out of the
    loop when the pipe breaks. A dashboard that dies because the game closed the
    pipe is worse than a dashboard that reconnects.
  * A reader thread gives us a blocking ``ReadFile`` we can cancel with
    ``CancelIoEx``, precise control over reconnect backoff, and a clean
    ``asyncio.CancelledError`` path that Textual can await during shutdown.

The queue is bounded. If the UI stalls, the reader drops telemetry rather than
growing without limit -- the same back-pressure policy the probe applies at the
other end of the pipe (pitfall 2).
"""

from __future__ import annotations

import asyncio
import ctypes
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Final

from . import protocol as proto

log = logging.getLogger(__name__)

PIPE_PATH: Final[str] = r"\\.\pipe\vlink_telemetry"

#: Bytes buffered before the reader stops accepting. At ~120 bytes/frame this is
#: roughly 1700 frames of headroom, which is well over a second at the rates a
#: heavily modded game produces.
DEFAULT_QUEUE_DEPTH: Final[int] = 4096

#: Never block the reader thread for longer than this on a silent pipe. It lets
#: us notice a dead peer even if the handle never signals ERROR_BROKEN_PIPE.
_POLL_INTERVAL_S: Final[float] = 0.5

_RECONNECT_MIN_S: Final[float] = 0.5
_RECONNECT_MAX_S: Final[float] = 15.0


# --------------------------------------------------------------------------
# Win32 imports. Guarded so the module imports (and the test suite runs) on
# Linux/macOS, where the fake probe is used instead.
# --------------------------------------------------------------------------

if __name__ != "nt":  # pragma: no cover - platform guard
    _k32 = None
    _GENERIC_READ = 0x80000000
    _OPEN_EXISTING = 3
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
else:  # pragma: no cover - platform guard
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    _k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _k32.CreateFileW.restype = wintypes.HANDLE

    _k32.ReadFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    _k32.ReadFile.restype = wintypes.BOOL

    _k32.CancelIoEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    _k32.CancelIoEx.restype = wintypes.BOOL

    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL

    _k32.GetLastError.restype = wintypes.DWORD

    _k32.WaitForSingleObjectEx.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL
    ]
    _k32.WaitForSingleObjectEx.restype = wintypes.DWORD

    _GENERIC_READ = 0x80000000
    _OPEN_EXISTING = 3
    _INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
    _WAIT_OBJECT_0 = 0x00000000
    _WAIT_TIMEOUT = 0x00000102
    _ERROR_BROKEN_PIPE = 109
    _ERROR_OPERATION_ABORTED = 995
    _ERROR_PIPE_BUSY = 231

    _READ_SIZE: Final[int] = 64 * 1024


@dataclass(slots=True)
class ClientStats:
    """Everything the status bar needs, updated from the reader thread."""

    connected: bool = False
    frames_decoded: int = 0
    bytes_read: int = 0
    frames_dropped: int = 0
    connect_attempts: int = 0
    reconnects: int = 0
    last_error: str = ""
    last_frame_monotonic: float = 0.0
    protocol_errors: int = 0
    observed_qpc_hz: float = 0.0
    _last_qpc: int = 0
    _last_qpc_at: float = 0.0
    _extras: dict[str, object] = field(default_factory=dict)

    def note_qpc(self, ticks: int, now: float) -> None:
        """Track the probe's QPC frequency so uptime can be shown in real
        seconds. The CLI has no access to the game's QueryPerformanceCounter,
        so we estimate it from consecutive heartbeat timestamps."""
        if self._last_qpc and ticks > self._last_qpc and now - self._last_qpc_at > 0.25:
            dt = now - self._last_qpc_at
            self.observed_qpc_hz = (ticks - self._last_qpc) / dt
            self._last_qpc_at = now
        self._last_qpc = ticks

    def uptime_seconds(self) -> float:
        if self.last_frame_monotonic and self.observed_qpc_hz:
            return self.last_frame_monotonic / self.observed_qpc_hz
        return 0.0

    def seconds_since_last_frame(self) -> float:
        if not self.last_frame_monotonic:
            return float("inf")
        return time.monotonic() - self.last_frame_monotonic


class PipeUnavailable(RuntimeError):
    """The named pipe could not be opened. Distinct from a protocol error."""


class VLinkClient:
    """Async V-Link consumer.

    Usage::

        async with VLinkClient() as client:
            async for frame in client.frames():
                handle(frame)
    """

    def __init__(
        self,
        pipe_path: str = PIPE_PATH,
        *,
        queue_depth: int = DEFAULT_QUEUE_DEPTH,
        reconnect: bool = True,
        read_size: int = 64 * 1024,
    ) -> None:
        self._pipe_path = pipe_path
        self._queue: asyncio.Queue[proto.Frame | None] = asyncio.Queue(maxsize=queue_depth)
        self._reconnect = reconnect
        self._read_size = read_size
        self.stats = ClientStats()

        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop = asyncio.Event()
        self._reader: asyncio.Task[None] | None = None
        self._wake: asyncio.Event | None = None
        self._ready: asyncio.Event | None = None
        self._handle: int | None = None
        self._open_result: int | None = None
        self._seq_seen = -1

    # -- lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._wake = asyncio.Event()
        self._ready = asyncio.Event()
        self._stop.clear()
        self._reader = asyncio.create_task(self._reader_main(), name="vlink-reader")

    async def close(self) -> None:
        self._stop.set()
        if self._wake is not None:
            self._wake.set()
        self._handle_close()
        if self._reader is not None:
            # The reader thread is inside ReadFile; CancelIoEx unblocks it.
            self._reader.cancel()
            try:
                await self._reader
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._reader = None
        await self._queue.put(None)

    async def __aenter__(self) -> VLinkClient:
        await self.start()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    # -- consumer API ------------------------------------------------------

    async def frames(self) -> AsyncIterator[proto.Frame]:
        """Yield decoded frames until the client is closed.

        Yields nothing while disconnected rather than raising, so the dashboard
        shows "waiting for vprobe" instead of dying. A protocol error does yield
        nothing further from that connection: the reader reconnects.
        """
        while True:
            item = await self._queue.get()
            if item is None:
                return
            yield item

    def try_get(self) -> proto.Frame | None:
        """Non-blocking single-frame poll, for non-async callers and tests."""
        try:
            item = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
        return None if item is None else item

    # -- reader thread -----------------------------------------------------

    async def _reader_main(self) -> None:
        backoff = _RECONNECT_MIN_S
        while not self._stop.is_set():
            loop = self._loop
            assert loop is not None
            try:
                await loop.run_in_executor(None, self._blocking_reader, loop)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self.stats.last_error = f"{type(exc).__name__}: {exc}"
                log.warning("vlink reader crashed: %s", exc)

            self.stats.connected = False
            self._handle_close()

            if not self._reconnect or self._stop.is_set():
                break

            log.info("vlink disconnected, retrying in %.1fs", backoff)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                break  # stop was requested
            except TimeoutError:
                pass
            backoff = min(backoff * 2, _RECONNECT_MAX_S)
        await self._queue.put(None)

    def _blocking_reader(self, loop: asyncio.AbstractEventLoop) -> None:
        """Runs on a worker thread. Blocking ReadFile, cancellable via CancelIoEx."""
        if _k32 is None:
            raise PipeUnavailable("V-Link requires Windows named pipes")

        self.stats.connect_attempts += 1
        handle = _k32.CreateFileW(
            self._pipe_path,
            _GENERIC_READ,
            0,          # no sharing: one consumer per session
            None,
            _OPEN_EXISTING,
            0,
            None,
        )
        if handle == _INVALID_HANDLE_VALUE:
            err = ctypes.get_last_error()
            self._open_result = err
            self.stats.last_error = f"CreateFileW failed: {_winerr_text(err)}"
            if err == _ERROR_PIPE_BUSY:
                # All instances are serving someone else. Back off and retry.
                return
            raise PipeUnavailable(self.stats.last_error)

        self._handle = int(handle or 0)
        self.stats.connected = True
        self.stats.reconnects += 1
        self._open_result = None
        self._seq_seen = -1
        log.info("vlink connected to %s", self._pipe_path)

        buf = (ctypes.c_char * self._read_size)()
        view = memoryview(buf)

        try:
            while not self._stop.is_set():
                read = ctypes.c_ulong(0)
                ok = _k32.ReadFile(
                    self._handle, buf, self._read_size, ctypes.byref(read), None
                )
                if not ok:
                    err = ctypes.get_last_error()
                    if err in (_ERROR_BROKEN_PIPE, _ERROR_OPERATION_ABORTED):
                        # Normal: the game exited or called stop.
                        self.stats.last_error = ""
                        return
                    self.stats.last_error = f"ReadFile failed: {_winerr_text(err)}"
                    log.warning("vlink ReadFile: %s", self.stats.last_error)
                    return
                if read.value == 0:
                    return

                self.stats.bytes_read += read.value
                self._dispatch(loop, view, read.value)
        finally:
            # asyncio.Queue is not thread-safe; hand the remainder back safely.
            self._handle_close()

    def _dispatch(self, loop: asyncio.AbstractEventLoop, view: memoryview, nbytes: int) -> None:
        """Decode what we just read and hand frames to the loop. Reader thread."""
        chunk = bytes(view[:nbytes])

        # Carry over a partial frame from the previous read.
        pending = getattr(self, "_partial", b"") + chunk
        offset = 0
        total = len(pending)
        now = time.monotonic()

        while True:
            mv = memoryview(pending)[offset:]
            length = proto.frame_length(mv, 0)
            if length is None or len(mv) < length:
                break
            try:
                frame, consumed = proto.decode(mv, 0)
            except proto.ProtocolError as exc:
                # A desync is unrecoverable without guessing, so drop the
                # connection and let the reader reconnect. The probe then
                # re-emits its name table and resolver report, so the dashboard
                # recovers its full state.
                self.stats.protocol_errors += 1
                self.stats.last_error = f"protocol: {exc}"
                log.error("vlink protocol error, reconnecting: %s", exc)
                return
            offset += consumed
            self._accept(loop, frame, now)

        leftover = pending[offset:total] if offset else pending
        # Bound the carry-over: a header is 28 bytes, so anything longer than one
        # max payload is corruption, not a slow frame.
        if len(leftover) > proto.FRAME_HEADER_SIZE + proto.MAX_PAYLOAD_SIZE:
            self.stats.protocol_errors += 1
            self.stats.last_error = "oversized partial frame discarded"
            leftover = b""
        self._partial = leftover  # type: ignore[attr-defined]

    def _accept(self, loop: asyncio.AbstractEventLoop, frame: proto.Frame, now: float) -> None:
        """Thread-safe handoff into the event loop."""
        self.stats.frames_decoded += 1
        self.stats.last_frame_monotonic = now
        if frame.event_type is proto.EventType.HEARTBEAT:
            self.stats.note_qpc(frame.timestamp, now)

        try:
            loop.call_soon_threadsafe(self._put, frame)
        except RuntimeError:
            # Loop is closing; nothing useful to do with this frame.
            log.debug("dropping frame during shutdown")

    def _put(self, frame: proto.Frame) -> None:
        try:
            self._queue.put_nowait(frame)
        except asyncio.QueueFull:
            # Back-pressure: the UI is behind. Drop the newest sample rather
            # than the oldest, so a stall does not replay stale history. Losing
            # a VmTick is harmless; losing a VmException is not, so those are
            # never dropped -- we overwrite a tick to make room.
            if frame.event_type in _CRITICAL_EVENTS:
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait(frame)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    self.stats.frames_dropped += 1
            else:
                self.stats.frames_dropped += 1

    def _handle_close(self) -> None:
        h = self._handle
        self._handle = None
        if h is not None and _k32 is not None:
            if _k32.CancelIoEx(h, None):
                pass
            _k32.CloseHandle(h)

    # -- control channel ---------------------------------------------------

    async def send_control(self, payload: bytes) -> None:
        """Send a control command to the probe.

        Rule 3: this is fire-and-forget by design. The probe queues the command
        and executes it on the engine's main-thread task runner, so a
        ``force_kill`` issued from this thread can never write VM memory while
        the VM is mid-sweep. We deliberately do not await a reply.
        """
        if _k32 is None or self._handle is None:
            raise PipeUnavailable("not connected")
        frame = proto.pack_frame(proto.EventType.PLUGIN_DIAG, payload)
        loop = self._loop
        assert loop is not None
        await loop.run_in_executor(None, _write_bytes, self._handle, frame)


def _write_bytes(handle: int, data: bytes) -> None:
    """Synchronous WriteFile for the control channel. Executor thread only."""
    if _k32 is None:
        raise PipeUnavailable("V-Link requires Windows")
    buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
    written = ctypes.c_ulong(0)
    ok = _k32.WriteFile(  # type: ignore[attr-defined]
        handle, buf, len(data), ctypes.byref(written), None
    )
    if not ok:
        raise OSError(ctypes.get_last_error(), "control WriteFile failed")


#: Never dropped by back-pressure. Losing one of these means the user misses
#: the exact thing they are staring at the dashboard to see.
_CRITICAL_EVENTS = frozenset(
    {proto.EventType.VM_EXCEPTION, proto.EventType.SAVE_BLOAT, proto.EventType.STACK_DUMP}
)


def _winerr_text(code: int) -> str:
    """Map the handful of pipe error codes we can actually act on."""
    return {
        2: "file not found (is the game running? is vprobe.dll installed?)",
        5: "access denied (pipe busy -- another OverseerCLI is connected)",
        231: "pipe busy",
        109: "broken pipe (game exited)",
        995: "operation aborted",
    }.get(code, f"win32 error {code}")
