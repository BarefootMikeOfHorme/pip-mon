"""V-Link protocol: the wire format shared with ``vprobe.dll``.

Framing is deliberately trivial so the hot path on both sides is a memcpy::

    +----------------------------+------------------------+
    | FrameHeader (28 bytes)     | payload (payloadSize)  |
    +----------------------------+------------------------+

The header is ``#pragma pack(1)`` in ``vprobe/include/TelemetryEvent.hpp`` and
the exact struct format below here. Any change to either side is a protocol
version bump; see ``docs/IPC_PROTOCOL.md``.

Rule 4 applies to this module too: it only *decodes*. Reconstruction of stacks,
heuristics and time series belong to :mod:`overseer_cli.profiler` and
:mod:`overseer_cli.detector`.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum, IntFlag
from typing import Any, Final

# --- constants mirrored from vprobe/include/TelemetryEvent.hpp --------------

PROTOCOL_VERSION: Final[int] = 1
FRAME_MAGIC: Final[int] = 0x4D4F4E34  # b"F4MO"

#: ``<I`` magic, ``<H`` version, ``<B`` event, ``<B`` flags, ``<I`` payload
#: size, ``<Q`` timestamp, ``<I`` sequence, ``<I`` thread id.
_HEADER = struct.Struct("<IHBBIQII")
FRAME_HEADER_SIZE: Final[int] = _HEADER.size
assert FRAME_HEADER_SIZE == 28, "header layout does not match the C++ ABI"

#: A corrupt length field must never make the dashboard allocate gigabytes.
MAX_PAYLOAD_SIZE: Final[int] = 64 * 1024
MAX_STACK_DEPTH: Final[int] = 64

# --- payload structs (all packed, matching the C++ #pragma pack(1)) ---------

_HEARTBEAT = struct.Struct("<dIfIIQQ")
_THREAD_STATE = struct.Struct("<IIIfHBBB")
_STACK_FRAME = struct.Struct("<IIIHHf")
_STACK_DUMP_HEAD = struct.Struct("<IHBBf")
_VM_TICK = struct.Struct("<IIIffIHHBB")
_VM_EXCEPTION = struct.Struct("<IIBBHHIf")
_MEMORY = struct.Struct("<QQQQIIII")
_MOD_LOAD = struct.Struct("<IIII")
_PLUGIN_DIAG = struct.Struct("<B3xI")
_SAVE_BLOAT = struct.Struct("<B3xIIIQf")


# --- enums ------------------------------------------------------------------


class EventType(IntEnum):
    """Wire event discriminants. Append-only; never renumber."""

    HEARTBEAT = 0x01
    THREAD_STATE = 0x02
    STACK_FRAME = 0x03
    STACK_DUMP = 0x04
    VM_TICK = 0x05
    VM_EXCEPTION = 0x06
    MEMORY = 0x07
    MOD_LOAD = 0x08
    PLUGIN_DIAG = 0x09
    SAVE_BLOAT = 0x0A


class EventFlags(IntFlag):
    NONE = 0x00
    OVERFLOW = 0x01
    SCAN_FALLBACK = 0x02
    RECOVERED = 0x04
    SYNTHETIC = 0x08


class ThreadPhase(IntEnum):
    CREATED = 0
    ENTERED = 1
    YIELDED = 2
    EXITED = 3
    ERRORED = 4


class VmErrorClass(IntEnum):
    STACK_OVERFLOW = 0
    RUNTIME_ERROR = 1
    EVENT_TIMEOUT = 2
    COMPILE = 3
    UNKNOWN = 255


class BloatReason(IntEnum):
    UNBOUNDED_LOOP = 0
    PROPERTY_FLOOD = 1
    CELL_STREAM_CHURN = 2
    UNKNOWN = 255


class DiagLevel(IntEnum):
    INFO = 0
    WARNING = 1
    ERROR = 2


# --- decoded payloads -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Heartbeat:
    uptime_seconds: float
    game_frame_count: int
    frame_time_ms: float
    active_papyrus_threads: int
    queued_papyrus_threads: int
    total_events_emitted: int
    total_events_dropped: int


@dataclass(frozen=True, slots=True)
class ThreadState:
    vm_thread_id: int
    phase: ThreadPhase
    depth: int
    wait_event_mask: int
    form_id: int
    wait_seconds: float
    waiting: bool = False


@dataclass(frozen=True, slots=True)
class StackFrame:
    form_id: int
    script_name_id: int
    op_code: int
    depth: int
    source_line: int
    self_time_us: float


@dataclass(frozen=True, slots=True)
class StackDump:
    vm_thread_id: int
    frames: tuple[StackFrame, ...]
    truncated: bool
    total_time_us: float


@dataclass(frozen=True, slots=True)
class VmTick:
    vm_thread_id: int
    op_counter: int
    op_total: int
    window_ms: float
    op_rate_per_sec: float
    form_id: int
    waiting: bool
    depth: int
    op_code: int


@dataclass(frozen=True, slots=True)
class VmException:
    form_id: int
    script_name_id: int
    error_class: VmErrorClass
    depth: int
    op_code: int
    depth_at_throw: int
    source_line: int
    interval_us: float


@dataclass(frozen=True, slots=True)
class MemorySample:
    working_set_bytes: int
    private_bytes: int
    virtual_bytes: int
    peak_working_set: int
    handle_count: int
    thread_count: int
    papyrus_thread_count: int
    streamed_cell_count: int


@dataclass(frozen=True, slots=True)
class ModLoad:
    form_id: int
    mod_index: int
    source_name_id: int
    load_flags: int


@dataclass(frozen=True, slots=True)
class PluginDiag:
    level: DiagLevel
    text: str


@dataclass(frozen=True, slots=True)
class SaveBloat:
    reason: BloatReason
    form_id: int
    source_name_id: int
    script_name_id: int
    estimated_records_added: int
    confidence: float


@dataclass(frozen=True, slots=True)
class Frame:
    """One decoded V-Link frame. ``payload`` is None for zero-length events."""

    event_type: EventType
    flags: EventFlags
    timestamp: int
    sequence: int
    thread_id: int
    payload: Any


class ProtocolError(Exception):
    """Raised when a frame cannot be decoded.

    The reader treats this as fatal for the *stream*, not for one frame: a bad
    length field means we can no longer find frame boundaries, so the only safe
    recovery is to reconnect.
    """


# --- decoders ---------------------------------------------------------------


def _d_heartbeat(b: memoryview, o: int, n: int) -> Heartbeat:
    if n < _HEARTBEAT.size:
        raise ProtocolError("short heartbeat")
    return Heartbeat(*_HEARTBEAT.unpack_from(b, o))


def _d_thread_state(b: memoryview, o: int, n: int) -> ThreadState:
    if n < _THREAD_STATE.size:
        raise ProtocolError("short thread state")
    vid, mask, form, wait, depth, phase, waiting, _res = _THREAD_STATE.unpack_from(b, o)
    return ThreadState(vid, ThreadPhase(phase), depth, mask, form, wait, waiting != 0)


def _d_stack_dump(b: memoryview, o: int, n: int) -> StackDump:
    if n < _STACK_DUMP_HEAD.size:
        raise ProtocolError("short stack dump head")
    vid, depth, truncated, _res, total_us = _STACK_DUMP_HEAD.unpack_from(b, o)
    if depth > MAX_STACK_DEPTH:
        raise ProtocolError(f"stack depth {depth} exceeds ABI max {MAX_STACK_DEPTH}")
    body = o + _STACK_DUMP_HEAD.size
    if n < _STACK_DUMP_HEAD.size + depth * _STACK_FRAME.size:
        raise ProtocolError("short stack dump body")
    frames = tuple(
        StackFrame(*_STACK_FRAME.unpack_from(b, body + i * _STACK_FRAME.size)) for i in range(depth)
    )
    return StackDump(vid, frames, bool(truncated), total_us)


def _d_vm_tick(b: memoryview, o: int, n: int) -> VmTick:
    if n < _VM_TICK.size:
        raise ProtocolError("short vm tick")
    vid, opc, opt, wms, rate, form, depth, opcode, waiting, _res = _VM_TICK.unpack_from(b, o)
    # `waiting` is a u8 on the wire but a bool in the dataclass. Coerce here
    # rather than relying on truthiness at every use site -- `waiting is False`
    # is a reasonable thing for a caller to write, and it would silently fail.
    return VmTick(vid, opc, opt, wms, rate, form, waiting != 0, depth, opcode)


def _d_vm_exception(b: memoryview, o: int, n: int) -> VmException:
    if n < _VM_EXCEPTION.size:
        raise ProtocolError("short vm exception")
    # EIGHT fields, not seven. The struct is <IIBBHHIf -- form, nameId, err,
    # depth, opCode, depthAtThrow, sourceLine, intervalUs -- and unpacking it
    # into seven names raised "too many values to unpack" on EVERY
    # VM_EXCEPTION frame.
    #
    # That was not merely a dropped field. The ValueError is not a
    # ProtocolError, so the client's dispatch handler did not catch it: it
    # propagated out and was swallowed by the broad reconnect handler, which
    # tore down the connection. VM_EXCEPTION is the highest-signal event we
    # emit (it is where Papyrus errors surface) and it was killing the stream
    # on arrival. The suite stayed green because there was no VmException
    # round-trip test -- the same gap that let this in.
    (form, name_id, err, depth, opcode, depth_at_throw, line,
     interval) = _VM_EXCEPTION.unpack_from(b, o)
    return VmException(form, name_id, VmErrorClass(err), depth, opcode,
                       depth_at_throw, line, interval)


def _d_memory(b: memoryview, o: int, n: int) -> MemorySample:
    if n < _MEMORY.size:
        raise ProtocolError("short memory")
    return MemorySample(*_MEMORY.unpack_from(b, o))


def _d_mod_load(b: memoryview, o: int, n: int) -> ModLoad:
    if n < _MOD_LOAD.size:
        raise ProtocolError("short mod load")
    return ModLoad(*_MOD_LOAD.unpack_from(b, o))


def _d_plugin_diag(b: memoryview, o: int, n: int) -> PluginDiag:
    if n < _PLUGIN_DIAG.size:
        raise ProtocolError("short plugin diag")
    level, text_len = _PLUGIN_DIAG.unpack_from(b, o)
    if n < _PLUGIN_DIAG.size + text_len:
        raise ProtocolError("plugin diag text truncated")
    raw = bytes(b[o + _PLUGIN_DIAG.size : o + _PLUGIN_DIAG.size + text_len])
    return PluginDiag(DiagLevel(level), raw.decode("utf-8", errors="replace"))


def _d_save_bloat(b: memoryview, o: int, n: int) -> SaveBloat:
    if n < _SAVE_BLOAT.size:
        raise ProtocolError("short save bloat")
    reason, form, source, script, records, conf = _SAVE_BLOAT.unpack_from(b, o)
    return SaveBloat(BloatReason(reason), form, source, script, records, conf)


def _d_single_frame(b: memoryview, o: int, n: int) -> StackDump:
    """A lone STACK_FRAME carries no depth, so present it as a depth-1 stack."""
    if n < _STACK_FRAME.size:
        raise ProtocolError("short stack frame")
    return StackDump(0, (StackFrame(*_STACK_FRAME.unpack_from(b, o)),), False, 0.0)


_DECODERS = {
    EventType.HEARTBEAT: _d_heartbeat,
    EventType.THREAD_STATE: _d_thread_state,
    EventType.STACK_DUMP: _d_stack_dump,
    EventType.STACK_FRAME: _d_single_frame,
    EventType.VM_TICK: _d_vm_tick,
    EventType.VM_EXCEPTION: _d_vm_exception,
    EventType.MEMORY: _d_memory,
    EventType.MOD_LOAD: _d_mod_load,
    EventType.PLUGIN_DIAG: _d_plugin_diag,
    EventType.SAVE_BLOAT: _d_save_bloat,
}


def frame_length(buf: memoryview, offset: int = 0) -> int | None:
    """Total byte length of the frame at ``offset``, or ``None`` if the header
    is not yet complete. Lets the reader size its buffer without decoding."""
    if len(buf) - offset < FRAME_HEADER_SIZE:
        return None
    _, _, _, _, payload_size, *_ = _HEADER.unpack_from(buf, offset)
    return FRAME_HEADER_SIZE + payload_size


def peek_header(buf: memoryview, offset: int = 0) -> tuple[int, int, int, int]:
    """Return ``(magic, version, event_type, payload_size)`` without decoding."""
    magic, version, etype, _flags, payload_size, *_ = _HEADER.unpack_from(buf, offset)
    return magic, version, etype, payload_size


def decode(buf: memoryview, offset: int = 0) -> tuple[Frame, int]:
    """Decode one frame at ``offset``.

    Returns the frame and the offset just past it. Raises :class:`ProtocolError`
    on a bad magic, an unsupported version, an unknown event type, or a payload
    size we refuse to trust -- any of which means the stream is desynchronised
    and the caller must reconnect rather than resync by guesswork.
    """
    if len(buf) - offset < FRAME_HEADER_SIZE:
        raise ProtocolError("incomplete header")

    magic, version, etype, flags, payload_size, ts, seq, tid = _HEADER.unpack_from(buf, offset)

    if magic != FRAME_MAGIC:
        raise ProtocolError(f"bad magic 0x{magic:08X}")
    if version != PROTOCOL_VERSION:
        raise ProtocolError(
            f"protocol version {version} from probe, this CLI speaks {PROTOCOL_VERSION}. "
            "Update OverseerCLI or rebuild vprobe."
        )
    if payload_size > MAX_PAYLOAD_SIZE:
        raise ProtocolError(f"payload size {payload_size} exceeds cap {MAX_PAYLOAD_SIZE}")

    end = offset + FRAME_HEADER_SIZE + payload_size
    if end > len(buf):
        raise ProtocolError("incomplete payload")

    try:
        et = EventType(etype)
    except ValueError as exc:
        raise ProtocolError(f"unknown event type 0x{etype:02X}") from exc

    payload: Any = None
    decoder = _DECODERS.get(et)
    if decoder is not None and payload_size:
        payload = decoder(buf, offset + FRAME_HEADER_SIZE, payload_size)

    return Frame(et, EventFlags(flags), ts, seq, tid, payload), end


def pack_frame(
    event_type: EventType,
    payload: bytes = b"",
    *,
    timestamp: int = 0,
    sequence: int = 0,
    thread_id: int = 0,
    flags: EventFlags = EventFlags.NONE,
) -> bytes:
    """Encode a frame. Used by the test suite's fake probe and by the
    ``--inject`` debugging path; not on the hot path."""
    if len(payload) > MAX_PAYLOAD_SIZE:
        raise ValueError(f"payload too large: {len(payload)}")
    return _HEADER.pack(
        FRAME_MAGIC,
        PROTOCOL_VERSION,
        int(event_type),
        int(flags),
        len(payload),
        timestamp,
        sequence,
        thread_id,
    ) + payload
