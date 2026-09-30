# vlink_probe.py -- read frames from a live PIP-MON runtime.
#
# WHY THIS EXISTS SEPARATELY FROM THE DASHBOARD
#   The dashboard is a Textual app and a good place to live, but it is the
#   wrong tool for the question "is a single frame arriving?". This is a
#   headless, dependency-free reader whose entire job is to connect once, read
#   for a bounded time, print what it saw, and disconnect cleanly.
#
# TWO BUGS THIS SCRIPT EXISTS TO NOT REPEAT
#
#   1. The handshake events were created in one process and waited on in
#      another. A named kernel object is destroyed when its last handle closes,
#      so when the creating process exited the event vanished and the runtime
#      had nothing to signal. The handshake reported "not ready" for a reason
#      that had nothing to do with the runtime. This script creates and waits
#      on the events in ONE process, in ONE try block, and reports honestly if
#      it cannot.
#
#   2. A previous PowerShell probe connected to the pipe and never
#      disconnected, leaving the runtime's single-instance server blocked on a
#      dead client. Every later connect then returned ERROR_BUSY, which reads
#      exactly like "the pipe is broken" when in fact the pipe is fine and a
#      previous reader was rude. This script closes its handle in `finally`,
#      always, and treats ERROR_BUSY as "someone else has it" rather than as a
#      failure of ours.
#
# WHAT IT DELIBERATELY DOES NOT DO
#   It does not retry forever, and it does not claim success on a zero read.
#   "Connected but saw nothing" is reported as exactly that, because a runtime
#   that opens a pipe and never writes to it is a real and interesting
#   failure mode -- not an error to be smoothed over.
import argparse
import json
import re
import ctypes
import ctypes.wintypes as wt
import struct
import sys
import time

# --- Win32, by hand. ctypes.wintypes is enough and avoids pywin32. ----------
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE = ctypes.c_void_p(-1).value
ERROR_BUSY = 161
ERROR_PIPE_BUSY = 231

kernel32.CreateFileW.restype = wt.HANDLE
kernel32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD,
                                 ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
kernel32.ReadFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                              ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
kernel32.CloseHandle.argtypes = [wt.HANDLE]

# --- the wire format, restated here on purpose -----------------------------
# Duplicated from the C++ header and the Python protocol module ON PURPOSE.
# If this copy ever disagrees with either of those, that is the bug, and a
# three-way check will surface it immediately. A single shared import would
# hide the disagreement behind one wrong definition.
# From vprobe/include/TelemetryEvent.hpp:
#     inline constexpr std::uint32_t kFrameMagic = 0x4D4F4E34;  // "F4MO"
#
# Worth recording HOW this went wrong twice, because the failure mode is the
# dangerous kind. It was first written as 0x4C56 ("VL") on the strength of a
# half-remembered note. The server then sent a perfectly valid frame and this
# probe reported "BAD MAGIC - not our wire format", which sounded like a
# protocol problem and was actually a transcription problem. Worse, when the
# bytes were printed they spelled "F4MO" in ASCII, and the immediate
# conclusion drawn was that "the server is writing text, not binary frames",
# which would have sent the next debugging step in a completely wrong
# direction.
#
# The lesson is not "be careful with hex constants". It is that a decoded
# value which HAPPENS TO LOOK LIKE TEXT is the most dangerous kind of wrong,
# because it invites a story. 0x4D4F4E34 is not a banner; it is a magic number
# that happens to be printable. Always read the constant from the header, never
# from memory of it.
MAGIC = 0x4D4F4E34      # "F4MO"

# The authoritative layout is vprobe/include/TelemetryEvent.hpp, FrameHeader,
# packed to 28 bytes and guarded there by a static_assert:
#
#     uint32 magic        uint16 version   uint8 eventType   uint8 flags
#     uint32 payloadSize  uint64 timestamp uint32 sequence   uint32 threadId
#
# "<" means no alignment padding, which is what #pragma pack(1) gives.
#
# The first version of this file got this WRONG twice: it omitted threadId
# entirely and put the fields in a different order, so the format string
# described 24 bytes of a 28-byte header. It failed loudly on the first read,
# which is the only reason it was caught before any data was misinterpreted --
# a header that is merely the wrong LENGTH is survivable; one that is the
# right length in the wrong order decodes into confident nonsense.
#
# The three languages must agree on this exactly. If this ever disagrees with
# the C++ struct, THAT is the bug, and this file is where to look first.
HEADER_FMT = "<IHBBIQII"   # 4+2+1+1+4+8+4+4 = 28
HEADER_LEN = 28
assert struct.calcsize(HEADER_FMT) == HEADER_LEN, "header layout disagrees with C++"

# EventType values, copied from the same C++ enum. Note these are NOT the
# 0..16 sequence the first draft guessed -- they start at 0x01 and are sparse.
EVENT_NAMES = {
    0x01: "Heartbeat", 0x02: "ThreadState", 0x03: "StackFrame",
    0x04: "StackDump", 0x05: "VmTick", 0x06: "VmException",
    0x07: "Memory", 0x08: "ModLoad", 0x09: "PluginDiag",
    0x0A: "SaveBloat",
}


ERROR_FILE_NOT_FOUND = 2
ERROR_PATH_NOT_FOUND = 3


def connect(pipe: str, attempts: int, delay: float):
    """Connect once, retrying only on BUSY.

    ERROR_BUSY means the server already has an instance in use. That is a
    different situation from "the pipe does not work", and reporting it as a
    failure is how the previous probe produced a false negative.

    ERROR_FILE_NOT_FOUND is returned, not raised: "nothing is running" is an
    expected state for this tool and deserves a sentence, not a traceback.
    """
    for i in range(attempts):
        h = kernel32.CreateFileW(pipe, GENERIC_READ | GENERIC_WRITE, 0,
                                 None, OPEN_EXISTING, 0, None)
        if h not in (None, INVALID_HANDLE):
            return h, i
        err = ctypes.get_last_error()
        if err in (ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND):
            return None, -1
        if err not in (ERROR_BUSY, ERROR_PIPE_BUSY):
            raise OSError(err, f"CreateFileW failed: {err}")
        time.sleep(delay)
    return None, attempts


# --- payload layouts, read from vprobe/include/TelemetryEvent.hpp -----------
#
# Why bother decoding fields at all, when "the framing is valid" already
# proved the transport works? Because framing is the easy half. A header can
# be perfectly well formed while the payload is being written from the wrong
# struct, from a stale offset, or with fields in the wrong order -- and none
# of that shows up in a framing check. Claiming "telemetry works" on the
# strength of magic numbers and a sequence count would be exactly the kind of
# overclaiming this project has been correcting all session.
#
# MemoryPayload is decoded first and in full because it is eight plain
# integers with no floats and no padding ambiguity. If the offsets are wrong,
# it is wrong visibly: a working set of 3 GB cannot be 186 bytes, and a thread
# count cannot be in the tens of thousands. HeartbeatPayload is more
# forgiving, because frameTimeMs is a float and a wrong offset still yields a
# number that looks like a number.
#
# The C++ side is #pragma pack(1), so "<" with no alignment is correct here.
PAYLOAD_FMT = {
    0x07: ("<QQQQIIII", [                       # MemoryPayload, 48 bytes
        "workingSetBytes", "privateBytes", "virtualBytes", "peakWorkingSet",
        "handleCount", "threadCount", "papyrusThreadCount", "streamedCellCount",
    ]),
    0x01: ("<dIfIIQQ", [                          # HeartbeatPayload, 40 bytes
        "uptimeSeconds", "gameFrameCount", "frameTimeMs", "activePapyrusThreads",
        "queuedPapyrusThreads", "totalEventsEmitted", "totalEventsDropped",
    ]),
}


def decode_payload(etype: int, body: bytes, raw: bool = False):
    """Return [(name, value)] or None if the layout is unknown or too short.

    Returning None rather than guessing is deliberate: an unknown event type
    must not produce invented field names, because a plausible-looking decode
    of the wrong struct is the failure mode this whole function exists to
    prevent.

    `raw=True` skips the display formatting and yields the values exactly as
    unpacked, so a machine-readable consumer gets ints and floats rather than
    pre-formatted strings. Without it, "--format jsonl" would be lossy in the
    one place it matters: "is gameFrameCount still 0?" cannot be answered
    reliably by matching a formatted string.
    """
    spec = PAYLOAD_FMT.get(etype)
    # PluginDiag is the odd one out: a fixed 8-byte header (level, 3 pad,
    # textLength) followed by a variable-length JSON text tail. It was absent
    # from PAYLOAD_FMT entirely, so every diagnostic decoded to nothing -- which
    # is why the resolver report was invisible on the wire even once it was
    # being delivered. The report IS the payload; not surfacing it makes the
    # whole frame look empty.
    if etype == 0x09:
        n = len(body)
        if n < 8:
            return [("SHORT PAYLOAD", f"{n}B < 8B needed")]
        level, text_len = struct.unpack_from("<B3xI", body, 0)
        # A textLength that overruns the body would silently yield a short
        # string; clamp and say so, rather than decoding whatever is there.
        tail = body[8:8 + text_len]
        if len(tail) < text_len:
            return [("level", level), ("textLength", text_len),
                    ("TRUNCATED", f"declared {text_len}B, only {len(tail)}B present")]
        try:
            decoded_text = tail.decode("utf-8")
        except UnicodeDecodeError:
            decoded_text = repr(tail)
        return [("level", level), ("textLength", text_len),
                ("text", decoded_text)]
    if spec is None:
        return None
    fmt, names = spec
    if len(body) < struct.calcsize(fmt):
        msg = f"{len(body)}B < {struct.calcsize(fmt)}B needed"
        return [("SHORT PAYLOAD", msg)]
    values = struct.unpack(fmt, body[: struct.calcsize(fmt)])
    out = []
    for name, val in zip(names, values):
        if raw:
            out.append((name, val))
        elif name.endswith("Bytes"):
            out.append((name, f"{val:,} ({val / (1024**3):.2f} GiB)"))
        elif name == "frameTimeMs":
            out.append((name, f"{val:.2f}"))
        elif name == "uptimeSeconds":
            out.append((name, f"{val:.1f}"))
        else:
            out.append((name, f"{val:,}"))
    return out


def read_exact(handle, n: int) -> bytes:
    buf = ctypes.create_string_buffer(n)
    got = wt.DWORD(0)
    if not kernel32.ReadFile(handle, buf, n, ctypes.byref(got), None):
        return b""
    return buf.raw[: got.value]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Read frames from a live PIP-MON runtime.",
        epilog="Filters compose: --event Heartbeat --match 'gameFrameCount\\s+[1-9]' "
               "keeps only heartbeat frames whose game frame count is non-zero. "
               "Use --format jsonl with --summary-only for a one-line verdict.")
    ap.add_argument("--pipe", default=r"\\.\pipe\vlink_telemetry")
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--max-frames", type=int, default=25)

    # --- output shape ------------------------------------------------------
    ap.add_argument("--format", choices=("text", "jsonl"), default="text",
                    help="text = indented for a human; jsonl = one JSON object "
                         "per line, streamed, for parsing")
    ap.add_argument("--summary-only", action="store_true",
                    help="emit only the closing summary; suppresses per-frame "
                         "lines. The fastest way to get a verdict out of a long "
                         "capture.")

    # --- filters -----------------------------------------------------------
    # A long capture is mostly noise unless it can be cut. All of these compose,
    # and all of them still count toward the summary, so a filter that matches
    # nothing is visibly a "matched 0" rather than a silent success.
    ap.add_argument("--event", "-e", action="append", default=[],
                    help="keep only these event types; repeatable, and "
                         "comma-separated. Accepts a name (Heartbeat) or a hex "
                         "type (0x01).")
    ap.add_argument("--match", "-m", default=None,
                    help="regex; keep a frame only if it matches anywhere in the "
                         "rendered frame text. This is the general escape hatch "
                         "for 'show me the one frame where X happened'.")
    ap.add_argument("--field", "-F", action="append", default=[],
                    help="regex; keep only decoded field names matching it, and "
                         "keep only frames that then have at least one field. "
                         "Project the output down instead of scrolling it.")
    ap.add_argument("--connect-attempts", type=int, default=12,
                    help="retries on ERROR_BUSY. Lower this when a wedged server "
                         "is suspected: 12 x 0.5s blocks for six seconds before "
                         "reporting, which is long enough to look like a hang.")
    args = ap.parse_args()

    want_events = {e.strip().lower() for e in
                   (x for v in args.event for x in v.split(",")) if e.strip()}
    field_rx = re.compile(args.field[0]) if args.field else None
    match_rx = re.compile(args.match) if args.match else None

    def event_selected(etype: int) -> bool:
        if not want_events:
            return True
        name = EVENT_NAMES.get(etype, "?").lower()
        return name in want_events or f"0x{etype:02x}" in want_events

    def emit(obj: dict) -> None:
        """Write one record in the selected format.

        Two shapes, deliberately:
          text   indented, for a human reading a terminal
          jsonl  one JSON object per line, for anything parsing this

        JSONL rather than a single JSON document because a long capture is
        streamed, not buffered: a single document would be all-or-nothing, so a
        reader that died at frame 40 would have nothing at all. One object per
        line means every frame already emitted is still usable.
        """
        if args.format == "jsonl":
            print(json.dumps(obj, default=str), flush=True)
        else:
            kind = obj.get("kind")
            if kind == "frame":
                print(f"  frame {obj['n']:2d} seq={obj['seq']:<5d} "
                      f"type=0x{obj['type']:02X} {obj['name']:<12s} "
                      f"tid={obj['tid']:<6d} payload={obj['payload']}B")
                for k, v in obj.get("fields", {}).items():
                    print(f"           {k:<22} {v}")
            elif kind == "handshake":
                print(f"  handshake: loaded={obj['loaded']} ready={obj['ready']}")
            elif kind == "error":
                # lstrip: the JSON form carries its own indentation inside
                # `message`, and prepending more here double-indents the text
                # form. The structured value stays untouched.
                print(f"  {obj['message'].lstrip()}")
                for line in obj.get("detail", []):
                    print(f"    {line}")
            elif kind == "summary":
                print(f"  TOTAL FRAMES: {obj['frames']}")
                for k, v in obj.get("notes", []):
                    print(f"  {k}: {v}")

    if args.format == "text":
        print(f"probe: {args.pipe}", flush=True)

    # Create and hold the handshake events in THIS process. They are released
    # when this function returns, which is exactly the lifetime the runtime
    # needs -- long enough to signal, short enough not to leak.
    kernel32.CreateEventW.restype = wt.HANDLE
    kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
    kernel32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    loaded_ev = kernel32.CreateEventW(None, True, False, "Local\\pipmon_runtime_loaded")
    ready_ev = kernel32.CreateEventW(None, True, False, "Local\\pipmon_runtime_ready")

    handle, tries = connect(args.pipe, args.connect_attempts, 0.5)
    if handle is None:
        if tries == -1:
            emit({"kind": "error", "code": "no_listener", "message":
                  "  no runtime is listening on that pipe.",
                  "detail": ["Expected when the game is not running, or when "
                             "vprobe has not reached the point of opening its "
                             "pipe yet."]})
        else:
            # Distinct code from no_listener on purpose: "nobody is there" and
            # "someone is there but already taken" call for completely
            # different responses, and collapsing them sends people to restart a
            # game that was never running.
            emit({"kind": "error", "code": "stale_client", "message":
                  f"  the pipe stayed busy for {tries} attempts.",
                  "detail": ["A previous reader left its connection open, so the "
                             "server is still single-instance. That is a stale "
                             "client, not a broken pipe -- restart the game to "
                             "clear it."]})
        return 1
    if args.format == "text":
        print(f"  connected (after {tries} retries)" if tries else "  connected", flush=True)

    frames = 0
    shown = 0
    by_type = {}
    last_heartbeat = None
    seq_last = None
    seq_regressions = 0
    skipped_event = 0
    skipped_field = 0
    skipped_match = 0
    bad_magic = None
    deadline = time.time() + args.seconds
    try:
        while time.time() < deadline and frames < args.max_frames:
            head = read_exact(handle, HEADER_LEN)
            if len(head) < HEADER_LEN:
                break
            (magic, ver, etype, flags, plen,
             ts, seq, tid) = struct.unpack(HEADER_FMT, head)
            if magic != MAGIC:
                bad_magic = magic
                emit({"kind": "error", "code": "bad_magic",
                     "message": f"BAD MAGIC 0x{magic:04X} - not our wire format"})
                break
            body = read_exact(handle, plen) if plen else b""
            frames += 1
            # Counters are tracked on EVERY frame read, before any filter runs.
            # A filter that changed what "frames" means would make the summary
            # describe a different stream than the one the transport carried --
            # which is exactly the confusion this is meant to remove.
            by_type[etype] = by_type.get(etype, 0) + 1
            if seq_last is not None and seq <= seq_last:
                seq_regressions += 1
            seq_last = seq
            if etype == 0x01:
                last_heartbeat = decode_payload(etype, body)

            if not event_selected(etype):
                skipped_event += 1
                continue
            decoded = decode_payload(etype, body)
            if field_rx is not None and decoded:
                decoded = [(k, v) for k, v in decoded if field_rx.search(k)]
                if not decoded:
                    skipped_field += 1
                    continue
            if match_rx is not None:
                rendered = " ".join(f"{k} {v}" for k, v in (decoded or []))
                if not match_rx.search(rendered):
                    skipped_match += 1
                    continue

            if not args.summary_only:
                shown += 1
                emit({"kind": "frame", "n": shown, "seq": seq, "type": etype,
                      "name": EVENT_NAMES.get(etype, "?"), "tid": tid,
                      "payload": plen,
                      "fields": dict(decoded) if decoded else {}})

        loaded = kernel32.WaitForSingleObject(loaded_ev, 0) == 0
        ready = kernel32.WaitForSingleObject(ready_ev, 0) == 0
        emit({"kind": "handshake", "loaded": loaded, "ready": ready})
    finally:
        # Always close. The previous probe's missing Disconnect is what left
        # the runtime blocked, and a leaked handle outlives this process.
        kernel32.CloseHandle(handle)
        if loaded_ev:
            kernel32.CloseHandle(loaded_ev)
        if ready_ev:
            kernel32.CloseHandle(ready_ev)

    notes = [("by type", ", ".join(
        f"{EVENT_NAMES.get(t, '?')}={n}" for t, n in sorted(by_type.items())))]
    if seq_regressions:
        # A non-monotonic sequence means frames were reordered or lost in
        # flight. Always worth surfacing: it invalidates any "ordered stream"
        # claim made from this capture.
        notes.append(("SEQUENCE REGRESSIONS", seq_regressions))
    if skipped_event or skipped_field or skipped_match:
        notes.append(("filtered out",
                      f"event={skipped_event} field={skipped_field} match={skipped_match}"))
    hb = dict(last_heartbeat or [])
    if hb:
        notes.append(("heartbeat", " ".join(
            f"{k}={v}" for k, v in (last_heartbeat or [])
            if k in ("uptimeSeconds", "gameFrameCount", "totalEventsEmitted",
                     "totalEventsDropped", "activePapyrusThreads"))))
    emit({"kind": "summary", "frames": frames, "shown": shown, "notes": notes,
          "bad_magic": bad_magic})

    if bad_magic is not None:
        return 2
    if frames == 0:
        if args.format == "text":
            print("  connected but no frames arrived. The transport is up and the")
            print("  runtime is writing nothing. That is a real finding, not a pass.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
