# V-Link IPC Protocol Specification

**Component:** V-Link (the API name for the bridge between V-Probe and OverseerCLI)
**Transport:** Win32 Named Pipe, byte-stream mode
**Endpoint:** `\\.\pipe\vlink_telemetry`
**Direction:** V-Probe → OverseerCLI (telemetry), OverseerCLI → V-Probe (control, fire-and-forget)
**Status:** v1, implemented on both sides

---

## 1. Format decision, and why it is not CBOR

The general guidance for machine-side IPC is CBOR, MessagePack, or Protobuf. PIP-MON
uses **neither**, and the reason is Rule 1 (zero main-thread work) — see
`ENGINEERING_RULES.md`.

Every candidate format requires the *producer* to run an **encoder** before the bytes
reach the pipe. That encoder is real work: for CBOR and MessagePack it walks the
struct, writes variable-length integers, and in practice allocates. That work would
run on a hooked Papyrus thread, inside the game, at whatever rate the VM decides to
call us.

PIP-MON instead defines the payload as a **fixed-layout packed struct** that both
sides already agree on byte-for-byte. The producer does one `memcpy` into a
preallocated frame; the consumer does one `struct.unpack_from`. Neither side
allocates, formats, or parses.

| Format | Producer cost | Version agnostic | Adopted |
|---|---|---|---|
| Raw JSON | format + escape + alloc | easy | No — Rule 1 |
| JSONC | as raw JSON, larger | easy | **On-disk config only** |
| CBOR | encode + alloc | easy | No — Rule 1 |
| MessagePack | encode + alloc | easy | No — Rule 1 |
| Protobuf | encode, generated code | strict schema | No — needs a codegen toolchain in a plugin that must not crash |
| **Packed struct (this)** | **`memcpy` only** | **version-gated integer** | **Yes** |

The real cost of this choice is **schema evolution**: adding a field means both
sides must be rebuilt. That cost is paid explicitly and visibly by the
`version` field and the rejection behaviour in §6, rather than silently through a
schema-negotiation handshake that could itself fail inside the game process.

**Rejected Protobuf specifically** because a `.proto` codegen step inside the F4SE
build is a hard dependency on `protoc` at build time for a plugin whose failure mode
is a crashed game. A static struct and a `static_assert` cannot rot.

JSONC **is** used, per the recommendation, for everything human-authored on disk:
`vprobe_settings.jsonc` and `overseer_rules.jsonc`. See §8.

---

## 2. Stream framing

A byte stream, not a message stream, so frames are concatenated with no padding and
no delimiter. One `WriteFile` can carry many frames.

```
+--------------------------------+---------------------------+
|  FrameHeader (28 bytes)        |  payload (payloadSize B)  |
+--------------------------------+---------------------------+
```

### 2.1 FrameHeader

`#pragma pack(1)` in C++, `struct.Struct("<IHBBIQII")` in Python.

| Offset | Size | Field | Type | Notes |
|---:|---:|---|---|---|
| 0 | 4 | `magic` | `u32` | `0x4D4F4E34` — ASCII `F4MO` |
| 4 | 2 | `version` | `u16` | `1`. Consumer rejects anything else |
| 6 | 1 | `eventType` | `u8` | see §3 |
| 7 | 1 | `flags` | `u8` | bitfield, see §3.1 |
| 8 | 4 | `payloadSize` | `u32` | bytes immediately following the header |
| 12 | 8 | `timestamp` | `u64` | probe QPC ticks, **not** wall clock |
| 20 | 4 | `sequence` | `u32` | per-process monotonic, wraps at `UINT32_MAX` |
| 24 | 4 | `threadId` | `u32` | Win32 TID that emitted the frame |

`static_assert(sizeof(FrameHeader) == 28)` guards the C++ side;
`test_header_size_is_the_abi_constant` guards the Python side.

> **Timestamp caveat.** The probe has no portable wall clock (calling `GetSystemTime`
> from a game thread is unnecessary work), so timestamps are `QueryPerformanceCounter`
> ticks. The consumer **estimates** the QPC frequency from consecutive heartbeat
> timestamps and derives uptime from that. It is a display convenience, not a
> precise clock. Anything needing real time must be done on the consumer side.

### 2.2 Alignment and endianness

Explicitly little-endian on both sides. The payload structs are `pack(1)`, so no
padding bytes are transmitted. This is not "native" by accident — the `0x00BF` in
Papyrus' `waitEventMask` and the `float` rates would otherwise be unaligned on the
wire and produce a bus error on strict-alignment targets.

---

## 3. Event types

`enum EventType : u8`. **Append-only. Never renumber or reorder.** A gap in the enum
is how a future version extends the protocol.

| Value | Name | Payload | Rate | Notes |
|---:|---|---|---|---|
| `0x01` | `HEARTBEAT` | `Heartbeat` (40 B) | 1 Hz | liveness + coarse counters |
| `0x02` | `THREAD_STATE` | `ThreadState` (21 B) | per transition | VM scheduler create/enter/exit |
| `0x03` | `STACK_FRAME` | `StackFrame` (20 B) | rare | single frame; folded to depth-1 on decode |
| `0x04` | `STACK_DUMP` | `StackDump` (12 + 20·N B) | per exit | bounded snapshot, N ≤ 64 |
| `0x05` | `VM_TICK` | `VmTick` (30 B) | per 64 ops | the throughput signal |
| `0x06` | `VM_EXCEPTION` | `VmException` (22 B) | on error | **never dropped** |
| `0x07` | `MEMORY` | `Memory` (48 B) | 2 Hz | working set, handles |
| `0x08` | `MOD_LOAD` | `ModLoad` (16 B) | on load | FormID → source mod |
| `0x09` | `PLUGIN_DIAG` | `PluginDiag` (8 + N B) | on connect | UTF-8 text; see §7 |
| `0x0A` | `SAVE_BLOAT` | `SaveBloat` (28 B) | on detection | **never dropped** |

### 3.1 Flags

| Bit | Name | Meaning |
|---:|---|---|
| `0x01` | `OVERFLOW` | ring dropped events before this frame |
| `0x02` | `SCAN_FALLBACK` | address came from AOB, not the AddressLib INI |
| `0x04` | `RECOVERED` | the bridge hit and recovered from a fault |
| `0x08` | `SYNTHETIC` | emitted by the `.esp` patch, not a native hook |

### 3.2 Priority

Not on the wire — enforced at both ends.

V-Probe drops **low-priority** frames (trace-level `VM_TICK`, `STACK_FRAME`,
`MOD_LOAD`) when its ring is full or the consumer is slow, and preserves
`VM_EXCEPTION`, `STACK_DUMP` and `SAVE_BLOAT`. OverseerCLI does the same on
`asyncio.QueueFull`: a non-critical frame is dropped to make room, a critical one
evicts a non-critical one. Losing a throughput sample is invisible; losing the
exception the user is looking at is not.

---

## 4. Payload layouts

All `pack(1)`. Sizes are asserted on both sides.

### Heartbeat (40 B) — `"<dIfIIQQ"`
`f64 uptimeSeconds, u32 gameFrameCount, f32 frameTimeMs, u32 activePapyrusThreads, u32 queuedPapyrusThreads, u64 totalEventsEmitted, u64 totalEventsDropped`

### ThreadState (21 B) — `"<IIIfHBBB"`
`u32 vmThreadId, u32 waitEventMask, u32 formId, f32 waitSeconds, u16 depth, u8 phase, u8 waiting, u8 reserved`

`phase`: 0 created, 1 entered, 2 yielded, 3 exited, 4 errored.
`waitEventMask` is the raw `TES::srEventMask` — the consumer resolves it to a readable
list ("waiting on OnMenuClose", …) rather than the probe doing string work.

### StackFrame (20 B) — `"<IIIHHf"`
`u32 formId, u32 scriptNameId, u32 opCode, u16 depth, u16 sourceLine, f32 selfTimeUs`

### StackDump (12 + 20·N B) — head `"<IHBBf"`
`u32 vmThreadId, u16 depth, u8 truncated, u8 reserved, f32 totalTimeUs`, then N × StackFrame.

`depth` is clamped to 64 by the producer. `truncated` tells the consumer the tail
is missing, so it renders "…" rather than implying a complete stack.

### VmTick (30 B) — `"<IIIffIBBH"`
`u32 vmThreadId, u32 opCounter, u32 opTotal, f32 windowMs, f32 opRatePerSec, u32 formId, u16 depth, u16 opCode, u8 waiting, u8 reserved`

Emitted every 64 ops rather than every op. At 60 Hz that is a ~1 ms cadence at
1000 ops/s — fine enough to show a spike, coarse enough that sampling cost is
irrelevant.

### VmException (22 B) — `"<IIBBHHIf"`
`u32 formId, u32 scriptNameId, u8 errorClass, u8 depth, u16 opCode, u16 depthAtThrow, u32 sourceLine, f32 intervalUs`

`errorClass`: 0 stack overflow, 1 runtime error, 2 event timeout, 3 compile, 255 unknown.

### Memory (48 B) — `"<QQQQIIII"`
`u64 workingSetBytes, u64 privateBytes, u64 virtualBytes, u64 peakWorkingSet, u32 handleCount, u32 threadCount, u32 papyrusThreadCount, u32 streamedCellCount`

### ModLoad (16 B) — `"<IIII"`
`u32 formId, u32 modIndex, u32 sourceNameId, u32 loadFlags` (bit0 active, bit1 esm, bit2 light)

### PluginDiag (8 + N B) — `"<B3xI"`
`u8 level, 3 pad, u32 textLength`, then `textLength` bytes of UTF-8.
`level`: 0 info, 1 warning, 2 error.

### SaveBloat (28 B) — `"<B3xIIIQf"`
`u8 reason, 3 pad, u32 formId, u32 sourceNameId, u32 scriptNameId, u64 estimatedRecordsAdded, f32 confidence`

---

## 5. String interning

There are no strings in any high-frequency payload. A FormID is 4 bytes; its
mod name and script name are an **interned index** — a `u32` handle into a table the
probe builds and sends once per connection as a `PluginDiag` JSON blob.

Rationale: `OverseerScript_abc123.esp` is 24 bytes of text plus length prefix, sent
on every stack frame, to be resolved into the same string every time. An index costs
4 bytes and one dict lookup. See `Telecomm/InternTable.hpp`.

Consequence: the intern table is **per-connection state**. A reconnecting consumer
must tolerate a fresh table; the probe re-emits it on every attach for exactly this
reason.

---

## 6. Versioning and error handling

The consumer **rejects** the whole stream on: bad magic, unknown `version`, unknown
`eventType`, `payloadSize > 65536`, or `depth > 64`. A wrong `version` is not
auto-negotiated.

This looks strict, and the reasoning matters: after a bad length field there is no
reliable way to find the next frame boundary. Guessing means either resyncing by
scanning for `F4MO` (silently attributing bytes to the wrong event) or dropping the
connection. **Reconnect is the only safe recovery**, and it costs ~1 second of
backoff. The probe re-emits its name table and resolver report on attach, so full
state is restored automatically.

A new event type is therefore a breaking change; a new field inside an existing
payload is not. To add a field: append it, bump nothing, and have the consumer
ignore trailing bytes — which it already does, since it only reads the fields its
own struct declares.

**Not implemented, deliberately:** no checksum, no sequence-gap detection, no
explicit resume. A profiler that has silently lost 30% of its samples is worse than
one that reconnects and says so. Gap detection is on the roadmap and would be
reported by the existing `DroppedEventRule`.

---

## 7. Control channel (OverseerCLI → V-Probe)

Rule 3: a control command **never** touches VM memory from the IPC thread.

OverseerCLI writes a `PluginDiag`-framed command; the probe enqueues it and executes
it on the engine's main-thread task runner on the next frame. There is no reply
channel — commands are fire-and-forget by design, because a synchronous reply would
require the game thread to block on the dashboard, inverting the whole design.

Planned commands, with the safety ordering they must follow:

| Command | Behaviour |
|---|---|
| `soft_cancel <threadId>` | calls `Script.Cancel()` on the owning form. **Always try this first.** |
| `force_kill <threadId>` | purges the VM thread. Must be confirmed in the UI, with a save warning. |
| `dump_stack <threadId>` | re-reads the VM stack **on the main thread** and returns it as a `STACK_DUMP` |
| `set_sampling <interval>` | adjusts VM_TICK cadence at runtime |

`force_kill` is gated in the UI, not merely in the probe. A force-killed thread can
leave a quest flag half-written; that is unrecoverable and not the probe's call to
make. See `ENGINEERING_RULES.md` pitfall 4.

---

## 8. On-disk configuration (JSONC)

JSONC is the format for everything a human edits, per the project guidance.
Fallout 4 does not parse JSON natively — the F4SE plugin does — and standard JSON
forces modders to strip comments and trailing commas before editing.

| File | Read by | Purpose |
|---|---|---|
| `Data/F4SE/Plugins/vprobe/vprobe_settings.jsonc` | V-Probe | sampling interval, ring size, hook toggles, log level |
| `overseer_rules.jsonc` | OverseerCLI | anomaly thresholds, rule enable/disable, severity overrides |

Both tolerate `//` and `/* */` comments and trailing commas. Both are **optional**:
absent file means built-in defaults, never a startup error. A user who deletes
`overseer_rules.jsonc` gets the documented defaults, not a broken dashboard.

### vprobe_settings.jsonc

```jsonc
{
  // Ops between VM_TICK samples. Lower = more detail, more overhead.
  // The 64-op window is the built-in default and is what the detector's
  // thresholds are calibrated against. Changing this changes detector accuracy.
  "vmSampleInterval": 64,

  // Frame ring capacity (power of two). 8192 ≈ 1700 ms of telemetry at 5 kHz.
  // Larger costs memory, not throughput. Dropped frames are counted, never hidden.
  "ringCapacity": 8192,

  "pipePath": "\\\\.\\pipe\\vlink_telemetry",

  "hooks": {
    // Each toggle degrades gracefully: false means the corresponding panel
    // shows less, never that the plugin fails to load.
    "papyrusScriptExecute": true,   // script entry/exit, stack attribution
    "papyrusThreadExecute": true,   // op accounting, thread lifecycle
    "papyrusVmDebugPrint":  true,   // script error capture
    "vmRunningThreadCount": true    // frame pacing
  },

  // "error" | "warn" | "info" | "debug". Logs go through V-Link PluginDiag,
  // never to disk from a game thread (Rule 1).
  "logLevel": "info"
}
```

### overseer_rules.jsonc

Any subset of keys may be present; unspecified thresholds use the built-in values in
`ANOMALY_RULES.md`. Setting a rule's `enabled` to `false` removes it from the
dashboard but keeps the frame ingestion, so re-enabling is instant.

```jsonc
{
  "runawayLoop": {
    "enabled": true,
    // Sustained ops/sec that counts as runaway. 500 ≈ 10x a busy-but-normal
    // frame. Lower it and you will flag ordinary mod scripts.
    "thresholdOpsPerSec": 500.0,
    // How long it must stay above the threshold. Sub-second spikes are normal:
    // a script looping a container once on start legitimately looks runaway.
    "sustainSeconds": 2.0
  },

  "stackDepth": {
    "enabled": true,
    // Papyrus' own hard limit is 1024. 820 is 80% of it.
    "warnDepth": 820,
    "overflowDepth": 1024
  },

  "saveBloat": {
    "enabled": true,
    "workingSetGrowthMbPerSec": 1.0,
    "handleGrowthWarn": 1500,
    "handleGrowthCritical": 6000
  },

  "frameTime": {
    "enabled": true,
    "warnMs": 33.3,   // 30 fps
    "criticalMs": 66.7 // 15 fps
  },

  "vmStarvation": {
    "enabled": true,
    "minOpRate": 50.0,
    "minBusyThreads": 2
  }
}
```

---

## 9. Back-pressure and failure matrix

| Failure | Probe behaviour | Consumer behaviour |
|---|---|---|
| No consumer attached | ring fills, drops, `eventsDropped` rises on next heartbeat | shows "waiting for vprobe" |
| Consumer slow | oldest non-critical frames dropped | `QueueFull` → drop or evict non-critical |
| Consumer dies | `WriteFile` → `ERROR_BROKEN_PIPE`, reconnect with backoff 0.5→15 s | reconnect with same backoff |
| Pipe busy | 4 instances, `PIPE_UNLIMITED_INSTANCES` | `CreateFileW` → ERROR_PIPE_BUSY → back off |
| Game exits | pipe closes, `sessions_` counted | EOF → reconnect (fails harmlessly until game relaunches) |
| Build drift | probe degrades to AOB tier, or disables one hook | `DegradedProbeRule` names the dead probes |
| Protocol mismatch | — | reject stream, reconnect, report version on stderr |

Backoff is exponential and capped at 15 s on **both** sides. A dashboard left open
overnight must not spin on a pipe that does not exist.

---

## 10. Adding an event type

1. Add the `enum EventType` value in `TelemetryEvent.hpp` (append).
2. Add the packed payload struct, with a `static_assert(sizeof(...) == N)`.
3. Add the Python `struct.Struct` and its expected size in `test_protocol.py`.
4. Add the decoder to `_DECODERS`.
5. Decide its **priority** (§3.2) and whether it may be dropped.
6. Document it in §3 with its rate and cost.
7. If it can carry a string, intern it (§5) — do not add a string field.
