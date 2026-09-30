"""Protocol decode tests.

These are the tests that protect the C++/Python ABI boundary. Every payload
struct gets a round-trip here, because a silent field-order mismatch between
``TelemetryEvent.hpp`` and ``protocol.py`` produces telemetry that decodes
cleanly and reports the wrong numbers -- the worst kind of bug in a profiler.

The expected sizes are written as literals rather than read from the C++
header, so a change on either side fails here until both are updated
deliberately.
"""

from __future__ import annotations

import struct

import pytest

from overseer_cli import protocol as p


def test_header_size_is_the_abi_constant() -> None:
    # FrameHeader is #pragma pack(1) in C++: 4+2+1+1+4+8+4+4 = 28.
    assert p.FRAME_HEADER_SIZE == 28
    assert p.PROTOCOL_VERSION == 1
    assert p.FRAME_MAGIC == 0x4D4F4E34


@pytest.mark.parametrize(
    ("struct_obj", "expected"),
    [
        (p._HEARTBEAT, 40),  # f64 uptime, u32 frames, f32 frametime, u32 active, u32 queued, u64 sent, u64 dropped
        (p._THREAD_STATE, 21),  # u32, u32, u32, f32, u16 depth, u8, u8, u8
        (p._STACK_FRAME, 20),  # u32, u32, u32, u16, u16, f32
        (p._STACK_DUMP_HEAD, 12),  # u32, u16, u8, u8, f32
        (p._VM_TICK, 30),  # u32, u32, u32, f32, f32, u32, u16 depth, u16, u8, u8
        (p._VM_EXCEPTION, 22),  # u32, u32, u8, u8, u16, u16, u32, f32
        (p._MEMORY, 48),  # 4x u64, 4x u32
        (p._MOD_LOAD, 16),  # 4x u32
        (p._PLUGIN_DIAG, 8),  # u8, 3 pad, u32
        (p._SAVE_BLOAT, 28),  # u8, 3 pad, 3x u32, u64, f32
    ],
)
def test_payload_sizes_match_cxx(struct_obj: struct.Struct, expected: int) -> None:
    assert struct_obj.size == expected, (
        f"{struct_obj.format} is {struct_obj.size} bytes in Python but "
        f"{expected} in TelemetryEvent.hpp -- the ABI is out of sync"
    )


def test_heartbeat_roundtrip() -> None:
    raw = p._HEARTBEAT.pack(123.5, 4200, 16.7, 3, 1, 9000, 12)
    frame = p.pack_frame(p.EventType.HEARTBEAT, raw, timestamp=7, sequence=9, thread_id=4)
    decoded, end = p.decode(memoryview(frame))

    assert end == len(frame)
    assert decoded.event_type is p.EventType.HEARTBEAT
    assert decoded.timestamp == 7
    assert decoded.sequence == 9
    assert decoded.thread_id == 4
    hb = decoded.payload
    assert isinstance(hb, p.Heartbeat)
    assert hb.uptime_seconds == pytest.approx(123.5)
    assert hb.game_frame_count == 4200
    assert hb.active_papyrus_threads == 3
    assert hb.total_events_dropped == 12


def test_vm_tick_roundtrip_preserves_rate() -> None:
    raw = p._VM_TICK.pack(7, 64, 10240, 0.25, 256.0, 0x05005678, 3, 42, 0, 0)
    decoded, _ = p.decode(memoryview(p.pack_frame(p.EventType.VM_TICK, raw)))
    tick = decoded.payload
    assert isinstance(tick, p.VmTick)
    assert tick.vm_thread_id == 7
    assert tick.op_rate_per_sec == pytest.approx(256.0)
    assert tick.form_id == 0x05005678
    assert tick.waiting is False
    assert tick.depth == 3
    assert tick.op_code == 42


def test_vm_tick_depth_survives_papyrus_full_stack() -> None:
    """Regression: depth was u8, so 900 and 1024 were unrepresentable.

    Papyrus' limit is 1024. A u8 depth truncated at 255, which made the
    consumer's stack_depth rule (warn 820 / overflow 1024) silently unreachable.
    This asserts the full range survives the wire.
    """
    for depth in (255, 256, 820, 1023, 1024):
        raw = p._VM_TICK.pack(7, 64, 10240, 0.25, 256.0, 0x05005678, depth, 0, 0, 0)
        decoded, _ = p.decode(memoryview(p.pack_frame(p.EventType.VM_TICK, raw)))
        tick = decoded.payload
        assert isinstance(tick, p.VmTick)
        assert tick.depth == depth, f"depth {depth} was corrupted on the wire"


def test_thread_state_depth_is_u16() -> None:
    raw = p._THREAD_STATE.pack(4, 0, 0x05005678, 1.5, 1024, int(p.ThreadPhase.ENTERED), 0, 0)
    decoded, _ = p.decode(memoryview(p.pack_frame(p.EventType.THREAD_STATE, raw)))
    ts = decoded.payload
    assert isinstance(ts, p.ThreadState)
    assert ts.depth == 1024
    assert ts.phase is p.ThreadPhase.ENTERED
    assert ts.waiting is False


def test_stack_dump_roundtrip() -> None:
    depth = 5
    frames = b"".join(
        p._STACK_FRAME.pack(0x05005678, 1, 7, d, 100 + d, float(d) * 1.5) for d in range(depth)
    )
    head = p._STACK_DUMP_HEAD.pack(3, depth, 0, 0, 12.5)
    decoded, _ = p.decode(memoryview(p.pack_frame(p.EventType.STACK_DUMP, head + frames)))
    dump = decoded.payload
    assert isinstance(dump, p.StackDump)
    assert dump.vm_thread_id == 3
    assert len(dump.frames) == depth
    assert dump.frames[4].depth == 4
    assert dump.frames[4].self_time_us == pytest.approx(6.0)
    assert dump.truncated is False
    assert dump.total_time_us == pytest.approx(12.5)


def test_stack_dump_truncation_flag_survives() -> None:
    head = p._STACK_DUMP_HEAD.pack(3, 64, 1, 0, 0.0)
    frames = p._STACK_FRAME.pack(1, 1, 0, 0, 0, 0.0) * 64
    decoded, _ = p.decode(memoryview(p.pack_frame(p.EventType.STACK_DUMP, head + frames)))
    dump = decoded.payload
    assert isinstance(dump, p.StackDump)
    assert dump.truncated is True
    assert len(dump.frames) == 64


def test_plugin_diag_utf8_roundtrip() -> None:
    text = '{"kind":"resolver_report","entries":[]}'
    body = text.encode("utf-8")
    raw = p._PLUGIN_DIAG.pack(int(p.DiagLevel.WARNING), len(body)) + body
    decoded, _ = p.decode(memoryview(p.pack_frame(p.EventType.PLUGIN_DIAG, raw)))
    diag = decoded.payload
    assert isinstance(diag, p.PluginDiag)
    assert diag.level is p.DiagLevel.WARNING
    assert diag.text == text


def test_bad_magic_is_rejected() -> None:
    good = bytearray(p.pack_frame(p.EventType.HEARTBEAT, b""))
    good[0] ^= 0xFF
    with pytest.raises(p.ProtocolError, match="bad magic"):
        p.decode(memoryview(bytes(good)))


def test_version_mismatch_names_both_sides() -> None:
    frame = bytearray(p.pack_frame(p.EventType.HEARTBEAT, b""))
    struct.pack_into("<H", frame, 4, 99)
    with pytest.raises(p.ProtocolError, match="protocol version 99"):
        p.decode(memoryview(bytes(frame)))


def test_oversized_payload_is_refused() -> None:
    frame = bytearray(p.pack_frame(p.EventType.HEARTBEAT, b""))
    struct.pack_into("<I", frame, 8, p.MAX_PAYLOAD_SIZE + 1)
    with pytest.raises(p.ProtocolError, match="exceeds cap"):
        p.decode(memoryview(bytes(frame)))


def test_unknown_event_type_is_rejected() -> None:
    frame = bytearray(p.pack_frame(p.EventType.HEARTBEAT, b""))
    frame[6] = 0xEE
    with pytest.raises(p.ProtocolError, match="unknown event type"):
        p.decode(memoryview(bytes(frame)))


def test_incomplete_frame_raises() -> None:
    frame = p.pack_frame(p.EventType.HEARTBEAT, b"\x00" * 44)
    with pytest.raises(p.ProtocolError, match="incomplete payload"):
        p.decode(memoryview(frame[:-1]))


def test_frame_length_agrees_with_decode() -> None:
    raw = p._VM_TICK.pack(1, 64, 1, 0.1, 100.0, 0, 0, 1, 0, 0)
    frame = p.pack_frame(p.EventType.VM_TICK, raw)
    mv = memoryview(frame)
    assert p.frame_length(mv) == len(frame)
    _, end = p.decode(mv)
    assert end == p.frame_length(mv)


def test_frame_length_none_when_header_partial() -> None:
    frame = p.pack_frame(p.EventType.HEARTBEAT, b"")
    assert p.frame_length(memoryview(frame[:10])) is None


def test_multiple_frames_decode_sequentially() -> None:
    blob = b"".join(
        p.pack_frame(
            p.EventType.HEARTBEAT,
            p._HEARTBEAT.pack(i, i, 16.0, 1, 0, i, 0),
            sequence=i,
        )
        for i in range(5)
    )
    mv = memoryview(blob)
    offset = 0
    seqs = []
    while offset < len(blob):
        frame, offset = p.decode(mv, offset)
        seqs.append(frame.sequence)
    assert seqs == [0, 1, 2, 3, 4]


def test_flags_decode_as_intflag() -> None:
    frame = p.pack_frame(p.EventType.HEARTBEAT, b"", flags=p.EventFlags.OVERFLOW | p.EventFlags.SCAN_FALLBACK)
    decoded, _ = p.decode(memoryview(frame))
    assert decoded.flags & p.EventFlags.OVERFLOW
    assert decoded.flags & p.EventFlags.SCAN_FALLBACK
    assert not decoded.flags & p.EventFlags.RECOVERED


def test_stack_depth_beyond_abi_max_is_refused() -> None:
    # A depth field larger than the ABI allows means we are desynchronised; the
    # decoder must not try to allocate for it.
    head = p._STACK_DUMP_HEAD.pack(1, 200, 0, 0, 0.0)
    with pytest.raises(p.ProtocolError, match="exceeds ABI max"):
        p.decode(memoryview(p.pack_frame(p.EventType.STACK_DUMP, head)))


def test_save_bloat_roundtrip() -> None:
    raw = p._SAVE_BLOAT.pack(int(p.BloatReason.PROPERTY_FLOOD), 0x01001234, 1, 2, 48000, 0.85)
    decoded, _ = p.decode(memoryview(p.pack_frame(p.EventType.SAVE_BLOAT, raw)))
    b = decoded.payload
    assert isinstance(b, p.SaveBloat)
    assert b.reason is p.BloatReason.PROPERTY_FLOOD
    assert b.form_id == 0x01001234
    assert b.estimated_records_added == 48000
    assert b.confidence == pytest.approx(0.85)


def test_vm_exception_roundtrip() -> None:
    """Every VM_EXCEPTION field must survive encode -> decode.

    Added because the decoder unpacked eight values into seven names, which
    raised ValueError on every VM_EXCEPTION frame. Nothing caught it because
    every OTHER payload had a round-trip test and this one did not -- the gap
    was the bug's only hiding place. The count assertion below is the part that
    matters: a size check alone passes while the unpack is wrong, because the
    struct was always the right 22 bytes.
    """
    raw = p._VM_EXCEPTION.pack(0x05005678, 42, int(p.VmErrorClass.RUNTIME_ERROR),
                               3, 7, 19, 128, 16.7)
    frame = p.pack_frame(p.EventType.VM_EXCEPTION, raw, timestamp=7, sequence=9,
                         thread_id=4)
    decoded, end = p.decode(memoryview(frame))

    assert end == len(frame)
    ex = decoded.payload
    assert isinstance(ex, p.VmException)
    assert ex.form_id == 0x05005678
    assert ex.script_name_id == 42
    assert ex.error_class is p.VmErrorClass.RUNTIME_ERROR
    assert ex.depth == 3
    assert ex.op_code == 7
    # The field that was being dropped.
    assert ex.depth_at_throw == 19
    assert ex.source_line == 128
    assert ex.interval_us == pytest.approx(16.7)

    # And the structural guard: every wire field has somewhere to land, so a
    # future field added to the struct without the dataclass cannot pass.
    #
    # Counting the FORMAT's letters is the number of fields, not the byte size:
    # "<IIBBHHIf" has eight fields and 22 bytes, and the pad/digit characters
    # (the '<' byte-order mark, any '3x' filler) are not fields. A dataclass
    # has one slot per field, so that is what the two counts must agree on --
    # asserting slots == size was the first mistake here, and it fails for
    # every struct.
    wire_fields = len([c for c in p._VM_EXCEPTION.format if c.isalpha()])
    assert wire_fields == 8
    assert len(p.VmException.__slots__) == wire_fields
    assert p._VM_EXCEPTION.size == 22


def test_thread_state_roundtrip() -> None:
    """Same guard for ThreadState, which had a 7-into-8 pack in fake_probe."""
    raw = p._THREAD_STATE.pack(7, 0x40, 0x05005678, 1.5, 900, 2, 1, 0)
    frame = p.pack_frame(p.EventType.THREAD_STATE, raw, timestamp=1, sequence=2,
                         thread_id=3)
    decoded, end = p.decode(memoryview(frame))
    assert end == len(frame)
    ts = decoded.payload
    assert isinstance(ts, p.ThreadState)
    assert ts.vm_thread_id == 7
    assert ts.wait_event_mask == 0x40
    assert ts.form_id == 0x05005678
    assert ts.wait_seconds == pytest.approx(1.5)
    assert ts.depth == 900
    assert ts.waiting == 1