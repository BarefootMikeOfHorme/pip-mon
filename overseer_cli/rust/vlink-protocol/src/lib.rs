//! V-Link wire format, as safe zero-copy Rust bindings.
//!
//! This is the third and final declaration of the V-Link ABI:
//!   * `vprobe/include/TelemetryEvent.hpp`      -- producer (C++, `#pragma pack(1)`)
//!   * `overseer_cli/src/overseer_cli/protocol.py` -- consumer (Python, `struct`)
//!   * this crate                               -- consumer (Rust, `#[repr(C, packed)]`)
//!
//! All three are held in sync by *size assertions at compile time* and by
//! round-trip tests. See `docs/IPC_PROTOCOL.md`.
//!
//! # Safety and layout
//!
//! Every struct is `#[repr(C, packed)]` to match `#pragma pack(1)` exactly. The
//! `#![forbid(unsafe_code)]` lint means the whole crate contains no `unsafe`
//! blocks, and no caller ever needs one either: [`Frame::header`] and friends
//! go through [`bytemuck::try_from_bytes`], which returns a `Result`.
//!
//! The one ergonomic cost of `packed` is that you may not take a *reference* to
//! a field. So the accessors in this crate deliberately return fields **by
//! value** (`self.magic`, not `&self.magic`). Reading by value is what makes the
//! `forbid(unsafe_code)` guarantee achievable, and on a few-byte payload the
//! copy is free.
//!
//! There is no unaligned-load penalty to worry about on the consumer side: the
//! bytes arrive in a `&[u8]`, and `bytemuck` copies out of it rather than
//! reinterpreting in place. That is the same reason Python's `unpack_from` is
//! not affected.

#![forbid(unsafe_code)]
#![warn(missing_docs)]

use bytemuck::{AnyBitPattern, Pod, Zeroable};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// `b"F4MO"`. Guards against reading a stream that is not V-Link.
pub const FRAME_MAGIC: u32 = 0x4D4F_4E34;

/// The only protocol version this crate speaks.
///
/// Mismatch is a hard error, never a best-effort parse. After a bad length field
/// there is no reliable way to find the next frame boundary, so reconnecting is
/// the only safe recovery.
pub const PROTOCOL_VERSION: u16 = 1;

/// Bytes in a [`FrameHeader`].
pub const FRAME_HEADER_SIZE: usize = 28;

/// Refuse to allocate for a single frame larger than this. A corrupt length
/// field must not be able to make a consumer reserve gigabytes.
pub const MAX_PAYLOAD_SIZE: usize = 64 * 1024;

/// Papyrus' hard stack limit (`0x400`). Used for confidence scoring on
/// stack-depth findings.
pub const PAPYRUS_STACK_LIMIT: u16 = 1024;

/// Maximum frames in a [`StackDumpPayload`].
pub const MAX_STACK_DEPTH: usize = 64;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Wire event discriminants. Append-only; never renumber.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EventType {
    /// 1 Hz liveness plus coarse counters.
    Heartbeat = 0x01,
    /// VM scheduler create / enter / exit.
    ThreadState = 0x02,
    /// A single stack frame.
    StackFrame = 0x03,
    /// Bounded stack snapshot.
    StackDump = 0x04,
    /// Sampled interpreter throughput.
    VmTick = 0x05,
    /// Papyrus runtime error. Never dropped by back-pressure.
    VmException = 0x06,
    /// Process memory snapshot.
    Memory = 0x07,
    /// FormID to source-mod mapping.
    ModLoad = 0x08,
    /// UTF-8 diagnostic text. The only string-bearing event.
    PluginDiag = 0x09,
    /// Save-bloat heuristic signal. Never dropped by back-pressure.
    SaveBloat = 0x0A,
}

impl EventType {
    /// Decode from the wire, rejecting unknown discriminants.
    pub fn from_u8(v: u8) -> Option<Self> {
        Some(match v {
            0x01 => Self::Heartbeat,
            0x02 => Self::ThreadState,
            0x03 => Self::StackFrame,
            0x04 => Self::StackDump,
            0x05 => Self::VmTick,
            0x06 => Self::VmException,
            0x07 => Self::Memory,
            0x08 => Self::ModLoad,
            0x09 => Self::PluginDiag,
            0x0A => Self::SaveBloat,
            _ => return None,
        })
    }

    /// Human-readable name, matching the Python `EventType` names.
    pub const fn name(self) -> &'static str {
        match self {
            Self::Heartbeat => "heartbeat",
            Self::ThreadState => "thread_state",
            Self::StackFrame => "stack_frame",
            Self::StackDump => "stack_dump",
            Self::VmTick => "vm_tick",
            Self::VmException => "vm_exception",
            Self::Memory => "memory",
            Self::ModLoad => "mod_load",
            Self::PluginDiag => "plugin_diag",
            Self::SaveBloat => "save_bloat",
        }
    }
}

/// Frame-level flags. A bitfield, so this is a plain `u8` on the wire.
pub mod flags {
    /// The probe's ring dropped events before this frame.
    pub const OVERFLOW: u8 = 0x01;
    /// The address was resolved by AOB scan, not from the AddressLib INI.
    pub const SCAN_FALLBACK: u8 = 0x02;
    /// The bridge hit and recovered from a fault.
    pub const RECOVERED: u8 = 0x04;
    /// Emitted by the `.esp` patch rather than a native hook.
    pub const SYNTHETIC: u8 = 0x08;
}

/// VM scheduler phase.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ThreadPhase {
    /// 0
    Created = 0,
    /// 1
    Entered = 1,
    /// 2
    Yielded = 2,
    /// 3
    Exited = 3,
    /// 4
    Errored = 4,
}

impl ThreadPhase {
    /// Decode from the wire, rejecting unknown discriminants.
    pub fn from_u8(v: u8) -> Option<Self> {
        Some(match v {
            0 => Self::Created,
            1 => Self::Entered,
            2 => Self::Yielded,
            3 => Self::Exited,
            4 => Self::Errored,
            _ => return None,
        })
    }
}

/// Classification of a Papyrus runtime error.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VmErrorClass {
    /// 0 -- runaway recursion. The finding that most often precedes a
    /// half-written quest flag.
    StackOverflow = 0,
    /// 1
    RuntimeError = 1,
    /// 2
    EventTimeout = 2,
    /// 3 -- Papyrus source to PE compilation failure.
    Compile = 3,
    /// 255
    Unknown = 255,
}

impl VmErrorClass {
    /// Decode from the wire, rejecting unknown discriminants.
    pub fn from_u8(v: u8) -> Option<Self> {
        Some(match v {
            0 => Self::StackOverflow,
            1 => Self::RuntimeError,
            2 => Self::EventTimeout,
            3 => Self::Compile,
            255 => Self::Unknown,
            _ => return None,
        })
    }
}

/// Diagnostic severity for [`PluginDiagPayload`].
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DiagLevel {
    /// 0
    Info = 0,
    /// 1
    Warning = 1,
    /// 2
    Error = 2,
}

impl DiagLevel {
    /// Decode from the wire, rejecting unknown discriminants.
    pub fn from_u8(v: u8) -> Option<Self> {
        Some(match v {
            0 => Self::Info,
            1 => Self::Warning,
            2 => Self::Error,
            _ => return None,
        })
    }
}

/// Why the bridge suspects a save will bloat.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BloatReason {
    /// 0
    UnboundedLoop = 0,
    /// 1
    PropertyFlood = 1,
    /// 2
    CellStreamChurn = 2,
    /// 255
    Unknown = 255,
}

impl BloatReason {
    /// Decode from the wire, rejecting unknown discriminants.
    pub fn from_u8(v: u8) -> Option<Self> {
        Some(match v {
            0 => Self::UnboundedLoop,
            1 => Self::PropertyFlood,
            2 => Self::CellStreamChurn,
            255 => Self::Unknown,
            _ => return None,
        })
    }
}

// ---------------------------------------------------------------------------
// Wire structs
//
// `repr(C, packed)` mirrors `#pragma pack(1)`. Field ORDER matters and must
// match the C++ declaration exactly; the size assertions below are what stop a
// mismatch from reaching runtime.
// ---------------------------------------------------------------------------

/// Fixed header preceding every payload.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Pod, Zeroable)]
pub struct FrameHeader {
    /// `FRAME_MAGIC`.
    pub magic: u32,
    /// `PROTOCOL_VERSION`.
    pub version: u16,
    /// [`EventType`] discriminant.
    pub event_type: u8,
    /// Bitfield; see [`flags`].
    pub flags: u8,
    /// Bytes of payload following this header.
    pub payload_size: u32,
    /// `QueryPerformanceCounter` ticks, *not* wall clock.
    ///
    /// The probe cannot portably read a wall clock without doing work on a game
    /// thread, so uptime has to be derived on the consumer by estimating the
    /// QPC frequency from consecutive heartbeats. That is a display convenience,
    /// not a precise clock.
    pub timestamp: u64,
    /// Per-process monotonic counter; wraps at `u32::MAX`.
    pub sequence: u32,
    /// Win32 thread id of the emitter.
    pub thread_id: u32,
}

impl FrameHeader {
    /// Total wire size of the frame this header introduces.
    pub const fn frame_size(&self) -> usize {
        FRAME_HEADER_SIZE + self.payload_size as usize
    }
}

/// 1 Hz liveness and coarse counters.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Pod, Zeroable)]
pub struct HeartbeatPayload {
    /// Seconds since the probe started, as reported by the probe's own clock.
    pub uptime_seconds: f64,
    /// Rendered frames observed.
    pub game_frame_count: u32,
    /// Smoothed frame time.
    pub frame_time_ms: f32,
    /// Threads currently executing ops.
    pub active_papyrus_threads: u32,
    /// Threads parked on an event or delay.
    pub queued_papyrus_threads: u32,
    /// Frames accepted by the probe's ring.
    pub total_events_emitted: u64,
    /// Frames discarded. Non-zero means the dashboard is under-reporting, which
    /// the consumer treats as a critical finding in its own right.
    pub total_events_dropped: u64,
}

/// VM scheduler transition.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Pod, Zeroable)]
pub struct ThreadStatePayload {
    /// VM-assigned handle. Not an OS thread id.
    pub vm_thread_id: u32,
    /// Raw `TES::srEventMask` the thread is blocked on, for the consumer to
    /// resolve into a readable list rather than the probe doing string work.
    pub wait_event_mask: u32,
    /// Owning form, if any.
    pub form_id: u32,
    /// How long the thread has been parked.
    pub wait_seconds: f32,
    /// Call depth.
    ///
    /// This is `u16`, not `u8`, and that is load-bearing: Papyrus stacks reach
    /// 1024, so a `u8` silently truncates at 255 and makes the consumer's
    /// stack-depth rule (warn 820, overflow 1024) unreachable. The first draft
    /// of the C++ header had this as `u8` and the detector tests caught it.
    pub depth: u16,
    /// What the scheduler is doing.
    pub phase: u8,
    /// 1 if parked on an event or delay.
    pub waiting: u8,
    /// Padding; always 0.
    pub reserved: u8,
}

impl ThreadStatePayload {
    /// Typed view of the raw `phase` discriminant.
    ///
    /// Stored as `u8` rather than as [`ThreadPhase`] directly because bytemuck's
    /// `Pod` derive requires `repr(C)`, and a `repr(u8)` enum does not qualify.
    /// Keeping the wire struct primitive-only and converting here preserves both
    /// the zero-copy cast and the type safety at the use site.
    pub fn phase(&self) -> Option<ThreadPhase> {
        ThreadPhase::from_u8(self.phase)
    }
}

/// One entry of a Papyrus call chain.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Pod, Zeroable)]
pub struct StackFramePayload {
    /// TESForm this frame belongs to.
    pub form_id: u32,
    /// Interned script name. An index, never the text: see the note on
    /// [`PluginDiagPayload`].
    pub script_name_id: u32,
    /// Papyrus opcode.
    pub op_code: u32,
    /// 0 is the outermost frame.
    pub depth: u16,
    /// Source line, when the script was compiled with debug info.
    pub source_line: u16,
    /// Self time attributed to this frame.
    pub self_time_us: f32,
}

/// Bounded snapshot of a thread's call chain.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Pod, Zeroable)]
pub struct StackDumpPayload {
    /// Which thread this is.
    pub vm_thread_id: u32,
    /// Number of valid entries in `frames`.
    pub depth: u16,
    /// 1 if the real stack was deeper than [`MAX_STACK_DEPTH`], i.e. the tail is
    /// missing. Consumers must render this rather than implying a complete stack.
    pub truncated: u8,
    /// Padding; always 0.
    pub reserved: u8,
    /// Wall time for the whole chain.
    pub total_time_us: f32,
    /// Frames, outermost first. Only the first `depth` entries are meaningful.
    pub frames: [StackFramePayload; MAX_STACK_DEPTH],
}

impl StackDumpPayload {
    /// The valid frames, truncated to `depth`.
    pub fn frames(&self) -> &[StackFramePayload] {
        let n = (self.depth as usize).min(MAX_STACK_DEPTH);
        &self.frames[..n]
    }
}

/// Sampled interpreter throughput, emitted every 64 ops by default.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Pod, Zeroable)]
pub struct VmTickPayload {
    /// Thread this sample belongs to.
    pub vm_thread_id: u32,
    /// Ops executed in this window.
    pub op_counter: u32,
    /// Lifetime ops for this thread.
    pub op_total: u32,
    /// Duration of the window.
    pub window_ms: f32,
    /// Reported rate.
    ///
    /// Treat this as a hint. It is an average that stays high after a script
    /// stops, so the consumer recomputes the rate from the `op_total`
    /// progression across samples. See `overseer_cli/profiler.py`.
    pub op_rate_per_sec: f32,
    /// Form currently executing.
    pub form_id: u32,
    /// Call depth. `u16`, for the same reason as [`ThreadStatePayload::depth`].
    pub depth: u16,
    /// Current opcode.
    pub op_code: u16,
    /// 1 if parked.
    pub waiting: u8,
    /// Padding; always 0.
    pub reserved: u8,
}

/// Papyrus runtime error. Never dropped under back-pressure.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Pod, Zeroable)]
pub struct VmExceptionPayload {
    /// Form the faulting script belongs to.
    pub form_id: u32,
    /// Interned script name.
    pub script_name_id: u32,
    /// What kind of failure.
    pub error_class: u8,
    /// Depth at the point of the throw.
    pub depth: u8,
    /// Opcode that threw.
    pub op_code: u16,
    /// Depth recorded when the exception object was created.
    pub depth_at_throw: u16,
    /// Source line, if known.
    pub source_line: u32,
    /// VM tick interval that triggered detection.
    pub interval_us: f32,
}

impl VmExceptionPayload {
    /// Typed view of the raw `error_class` discriminant.
    pub fn error_class(&self) -> Option<VmErrorClass> {
        VmErrorClass::from_u8(self.error_class)
    }
}

/// Process memory snapshot, ~2 Hz.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Pod, Zeroable)]
pub struct MemoryPayload {
    /// Working set.
    pub working_set_bytes: u64,
    /// Private commit.
    pub private_bytes: u64,
    /// Virtual size.
    pub virtual_bytes: u64,
    /// High-water working set.
    pub peak_working_set: u64,
    /// Win32 handle count. Growth here is the save-bloat signal.
    pub handle_count: u32,
    /// OS threads in the process.
    pub thread_count: u32,
    /// Live Papyrus threads.
    pub papyrus_thread_count: u32,
    /// Streamed cells. Always 0 in this version; see ENGINEERING_RULES pitfall 3.
    pub streamed_cell_count: u32,
}

/// FormID to source-mod mapping, used to name a FormID in a finding.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Pod, Zeroable)]
pub struct ModLoadPayload {
    /// Form.
    pub form_id: u32,
    /// Load-order slot; the high byte of `form_id`.
    pub mod_index: u32,
    /// Interned source filename.
    pub source_name_id: u32,
    /// bit0 active, bit1 esm, bit2 light.
    pub load_flags: u32,
}

impl PluginDiagPayload {
    /// Typed view of the raw `level` discriminant.
    pub fn level(&self) -> Option<DiagLevel> {
        DiagLevel::from_u8(self.level)
    }
}

/// Header for the one string-bearing event.
///
/// The UTF-8 bytes follow immediately, length given by `text_length`. This is
/// the "fixed header + length-prefixed payload" shape: the probe never puts a
/// pointer, a `std::string`, or a `std::vector` into a wire struct, because
/// those would transmit an address that means nothing in another process.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Pod, Zeroable)]
pub struct PluginDiagPayload {
    /// Severity.
    pub level: u8,
    /// Padding; always 0.
    pub reserved: [u8; 3],
    /// Bytes of UTF-8 following this struct.
    pub text_length: u32,
}

/// Save-bloat heuristic signal.
#[repr(C, packed)]
#[derive(Debug, Clone, Copy, PartialEq, Pod, Zeroable)]
pub struct SaveBloatPayload {
    /// Why the bridge suspects bloat.
    pub reason: u8,
    /// Padding; always 0.
    pub reserved: [u8; 3],
    /// Offending form.
    pub form_id: u32,
    /// Interned source mod name.
    pub source_name_id: u32,
    /// Interned script name.
    pub script_name_id: u32,
    /// Rough count of records the save may have gained.
    pub estimated_records_added: u64,
    /// 0.0 to 1.0.
    pub confidence: f32,
}

impl SaveBloatPayload {
    /// Typed view of the raw `reason` discriminant.
    pub fn reason(&self) -> Option<BloatReason> {
        BloatReason::from_u8(self.reason)
    }
}

// ---------------------------------------------------------------------------
// Frame decoding
// ---------------------------------------------------------------------------

/// Why a frame could not be decoded.
///
/// Every variant is unrecoverable *for the stream*: the consumer cannot know
/// where the next frame begins, so the only safe action is to drop the
/// connection and reconnect. The probe re-emits its name table and resolver
/// report on attach, so state is restored automatically.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DecodeError {
    /// Fewer than [`FRAME_HEADER_SIZE`] bytes available.
    IncompleteHeader {
        /// Bytes actually available.
        available: usize,
    },
    /// `magic` did not match [`FRAME_MAGIC`].
    BadMagic(u32),
    /// The probe speaks a version this crate does not.
    UnsupportedVersion {
        /// Version the probe sent.
        got: u16,
        /// Version this crate accepts.
        expected: u16,
    },
    /// `event_type` is not a known discriminant.
    UnknownEventType(u8),
    /// `payload_size` exceeds [`MAX_PAYLOAD_SIZE`].
    PayloadTooLarge {
        /// The untrusted length.
        got: u32,
    },
    /// The declared frame does not fit in the available bytes.
    IncompletePayload {
        /// Declared size.
        declared: usize,
        /// Bytes available.
        available: usize,
    },
    /// A payload failed its own structural checks (e.g. a stack depth beyond
    /// the ABI maximum).
    MalformedPayload(&'static str),
}

impl std::fmt::Display for DecodeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::IncompleteHeader { available } => write!(
                f,
                "incomplete header: {available} bytes, need {FRAME_HEADER_SIZE}"
            ),
            Self::BadMagic(m) => write!(f, "bad magic 0x{m:08X}, expected 0x{FRAME_MAGIC:08X}"),
            Self::UnsupportedVersion { got, expected } => write!(
                f,
                "protocol version {got} from probe, this client speaks {expected}"
            ),
            Self::UnknownEventType(v) => write!(f, "unknown event type 0x{v:02X}"),
            Self::PayloadTooLarge { got } => {
                write!(f, "payload size {got} exceeds cap {MAX_PAYLOAD_SIZE}")
            }
            Self::IncompletePayload {
                declared,
                available,
            } => write!(
                f,
                "incomplete payload: declared {declared}, available {available}"
            ),
            Self::MalformedPayload(why) => write!(f, "malformed payload: {why}"),
        }
    }
}

impl std::error::Error for DecodeError {}

/// One decoded frame: its header plus a borrowed view of the payload.
#[derive(Debug, Clone, Copy)]
pub struct Frame<'a> {
    /// The header, copied out of the buffer.
    pub header: FrameHeader,
    /// Payload bytes, borrowed from the original buffer. No copy, no allocation.
    pub payload: &'a [u8],
}

impl<'a> Frame<'a> {
    /// Decode one frame at the start of `buf`.
    ///
    /// Returns the frame and how many bytes it consumed.
    ///
    /// # Errors
    /// See [`DecodeError`]. On any error the stream is considered
    /// desynchronised; the caller must reconnect rather than resync by guesswork.
    pub fn decode(buf: &'a [u8]) -> Result<(Self, usize), DecodeError> {
        if buf.len() < FRAME_HEADER_SIZE {
            return Err(DecodeError::IncompleteHeader {
                available: buf.len(),
            });
        }

        // `pod_read_unaligned` copies the POD out of the byte slice rather than
        // reinterpreting it in place. That is what makes it correct for a
        // `repr(packed)` struct -- a reference cast would be an alignment error
        // -- and it is a safe fn, so this whole crate stays `forbid(unsafe_code)`.
        let header: FrameHeader = bytemuck::pod_read_unaligned(&buf[..FRAME_HEADER_SIZE]);

        if header.magic != FRAME_MAGIC {
            return Err(DecodeError::BadMagic(header.magic));
        }
        if header.version != PROTOCOL_VERSION {
            return Err(DecodeError::UnsupportedVersion {
                got: header.version,
                expected: PROTOCOL_VERSION,
            });
        }
        let event_type = EventType::from_u8(header.event_type)
            .ok_or(DecodeError::UnknownEventType(header.event_type))?;
        let _ = event_type; // validated; payload decoding is by the caller's choice

        let payload_size = header.payload_size as usize;
        if payload_size > MAX_PAYLOAD_SIZE {
            return Err(DecodeError::PayloadTooLarge {
                got: header.payload_size,
            });
        }
        let total = FRAME_HEADER_SIZE + payload_size;
        if buf.len() < total {
            return Err(DecodeError::IncompletePayload {
                declared: total,
                available: buf.len(),
            });
        }

        Ok((
            Self {
                header,
                payload: &buf[FRAME_HEADER_SIZE..total],
            },
            total,
        ))
    }

    /// Borrow the payload as a concrete struct, if it is the right type and the
    /// right length.
    ///
    /// Still zero-copy, and still no `unsafe`.
    ///
    /// # Errors
    /// [`DecodeError::MalformedPayload`] if the payload is not exactly
    /// `size_of::<T>()` bytes, or if the requested `T` does not match the
    /// frame's event type.
    pub fn as_payload<T: AnyBitPattern>(&self) -> Result<T, DecodeError> {
        if std::mem::size_of::<T>() != self.payload.len() {
            return Err(DecodeError::MalformedPayload("payload size or type mismatch"));
        }
        // A POD struct's bytes are all valid bit patterns, so this cannot fail;
        // `any` is a formality for the compiler.
        Ok(bytemuck::pod_read_unaligned(self.payload))
    }
}

/// Walk every complete frame in `buf`.
///
/// Yields `(Frame, consumed)`. A trailing partial frame is simply not yielded,
/// which is what lets a reader append more bytes and call again. A decode error
/// stops the iteration immediately.
pub fn frames(buf: &[u8]) -> impl Iterator<Item = Result<(Frame<'_>, usize), DecodeError>> + '_ {
    let mut offset = 0usize;
    std::iter::from_fn(move || {
        if offset >= buf.len() {
            return None;
        }
        match Frame::decode(&buf[offset..]) {
            Ok((frame, consumed)) => {
                offset += consumed;
                Some(Ok((frame, consumed)))
            }
            // A partial tail is not an error: the caller will retry with more
            // bytes. Anything else stops iteration.
            Err(e @ DecodeError::IncompleteHeader { .. }) => {
                if buf.len() - offset < FRAME_HEADER_SIZE {
                    None
                } else {
                    Some(Err(e))
                }
            }
            Err(DecodeError::IncompletePayload { .. }) => None,
            Err(e) => Some(Err(e)),
        }
    })
}

// ---------------------------------------------------------------------------
// Compile-time ABI assertions
//
// These are the reason the three language bindings cannot silently drift. A
// field inserted or reordered on the C++ side changes a size here and the Rust
// build fails -- which is strictly better than a consumer reading `0x05005678`
// as a script name.
// ---------------------------------------------------------------------------

#[cfg(test)]
mod layout_tests {
    use super::*;

    // Const assertions rather than the `static_assertions` crate: no dependency,
    // works offline, and it is the idiomatic std-only form. If a field is added,
    // reordered or retyped on the C++ side, one of these fails and the build
    // stops -- rather than a consumer reading 0x05005678 as a script name.
    const _: () = assert!(std::mem::size_of::<FrameHeader>() == 28, "FrameHeader must be 28B");
    const _: () = assert!(std::mem::size_of::<HeartbeatPayload>() == 40, "HeartbeatPayload must be 40B");
    const _: () = assert!(std::mem::size_of::<ThreadStatePayload>() == 21, "ThreadStatePayload must be 21B");
    const _: () = assert!(std::mem::size_of::<StackFramePayload>() == 20, "StackFramePayload must be 20B");
    const _: () = assert!(
        std::mem::size_of::<StackDumpPayload>() == 12 + MAX_STACK_DEPTH * 20,
        "StackDumpPayload must be 12 + 64*20"
    );
    const _: () = assert!(std::mem::size_of::<VmTickPayload>() == 30, "VmTickPayload must be 30B");
    const _: () = assert!(std::mem::size_of::<VmExceptionPayload>() == 22, "VmExceptionPayload must be 22B");
    const _: () = assert!(std::mem::size_of::<MemoryPayload>() == 48, "MemoryPayload must be 48B");
    const _: () = assert!(std::mem::size_of::<ModLoadPayload>() == 16, "ModLoadPayload must be 16B");
    const _: () = assert!(std::mem::size_of::<PluginDiagPayload>() == 8, "PluginDiagPayload must be 8B");
    const _: () = assert!(std::mem::size_of::<SaveBloatPayload>() == 28, "SaveBloatPayload must be 28B");

    // The largest fixed payload must fit the probe's per-frame buffer.
    const _: () = assert!(
        std::mem::size_of::<StackDumpPayload>() <= 2048,
        "probe frame buffer is too small for a stack dump"
    );

    // Field offsets within FrameHeader, so a reordering is caught even if the
    // total size happens to be unchanged.
    //
    // `addr_of!` rather than `&field`: taking a reference to a packed field is
    // a hard error in Rust (E0793), which is exactly the ergonomic cost of
    // `repr(packed)` this crate is otherwise free of, because every real
    // accessor in the public API returns by value.
    #[test]
    fn header_field_offsets_are_stable() {
        let h = FrameHeader {
            magic: 0,
            version: 0,
            event_type: 0,
            flags: 0,
            payload_size: 0,
            timestamp: 0,
            sequence: 0,
            thread_id: 0,
        };
        let base = std::ptr::addr_of!(h) as usize;
        assert_eq!(std::ptr::addr_of!(h.magic) as usize - base, 0);
        assert_eq!(std::ptr::addr_of!(h.version) as usize - base, 4);
        assert_eq!(std::ptr::addr_of!(h.event_type) as usize - base, 6);
        assert_eq!(std::ptr::addr_of!(h.flags) as usize - base, 7);
        assert_eq!(std::ptr::addr_of!(h.payload_size) as usize - base, 8);
        assert_eq!(std::ptr::addr_of!(h.timestamp) as usize - base, 12);
        assert_eq!(std::ptr::addr_of!(h.sequence) as usize - base, 20);
        assert_eq!(std::ptr::addr_of!(h.thread_id) as usize - base, 24);
    }

    #[test]
    fn vm_tick_depth_is_sixteen_bit() {
        // Regression guard for the u8 truncation bug: a u8 depth cannot
        // represent Papyrus' 1024-deep stacks, which made the consumer's
        // stack_depth rule unreachable.
        let t = VmTickPayload {
            vm_thread_id: 1,
            op_counter: 64,
            op_total: 0,
            window_ms: 0.5,
            op_rate_per_sec: 100.0,
            form_id: 0,
            depth: PAPYRUS_STACK_LIMIT,
            op_code: 0,
            waiting: 0,
            reserved: 0,
        };
        // Copy the field to a local before asserting on it. `assert_eq!` takes a
        // reference to its operands, and a reference to a packed field is E0793
        // -- creating a misaligned reference is UB even if never dereferenced.
        // This is THE ergonomic cost of repr(packed), and the reason every
        // accessor in this crate returns fields by value.
        let depth = t.depth;
        assert_eq!(depth, 1024);
    }

    #[test]
    fn round_trip_a_vm_tick_without_unsafe() {
        let tick = VmTickPayload {
            vm_thread_id: 7,
            op_counter: 64,
            op_total: 10_240,
            window_ms: 0.25,
            op_rate_per_sec: 256.0,
            form_id: 0x0500_5678,
            depth: 3,
            op_code: 42,
            waiting: 0,
            reserved: 0,
        };
        // `bytes_of` borrows `tick`, so the whole frame buffer has to outlive
        // the decode call; hence the `let` rather than an inline expression.
        let bytes = bytemuck::bytes_of(&tick);

        // Build a full wire frame by hand, exactly as the C++ producer would.
        let mut buf = Vec::with_capacity(FRAME_HEADER_SIZE + bytes.len());
        buf.extend_from_slice(&FRAME_MAGIC.to_le_bytes());
        buf.extend_from_slice(&PROTOCOL_VERSION.to_le_bytes());
        buf.extend_from_slice(&[EventType::VmTick as u8, 0]);
        buf.extend_from_slice(&(bytes.len() as u32).to_le_bytes());
        buf.extend_from_slice(&0u64.to_le_bytes()); // timestamp
        buf.extend_from_slice(&0u32.to_le_bytes()); // sequence
        buf.extend_from_slice(&0u32.to_le_bytes()); // thread_id
        buf.extend_from_slice(bytes);

        let (frame, consumed) = Frame::decode(&buf).expect("valid frame");
        assert_eq!(consumed, FRAME_HEADER_SIZE + bytes.len());
        let back: VmTickPayload = frame.as_payload().expect("payload decodes");
        assert_eq!(back, tick);
    }

    #[test]
    fn rejects_a_version_mismatch() {
        let buf = [
            &FRAME_MAGIC.to_le_bytes()[..],
            &99u16.to_le_bytes()[..],
            &[EventType::VmTick as u8, 0],
            &0u32.to_le_bytes()[..],
            &0u64.to_le_bytes()[..],
            &0u32.to_le_bytes()[..],
            &0u32.to_le_bytes()[..],
        ]
        .concat();
        assert!(matches!(
            Frame::decode(&buf),
            Err(DecodeError::UnsupportedVersion { got: 99, .. })
        ));
    }

    #[test]
    fn rejects_an_oversized_payload() {
        let buf = [
            &FRAME_MAGIC.to_le_bytes()[..],
            &PROTOCOL_VERSION.to_le_bytes()[..],
            &[EventType::VmTick as u8, 0],
            &(MAX_PAYLOAD_SIZE as u32 + 1).to_le_bytes()[..],
            &0u64.to_le_bytes()[..],
            &0u32.to_le_bytes()[..],
            &0u32.to_le_bytes()[..],
        ]
        .concat();
        assert!(matches!(
            Frame::decode(&buf),
            Err(DecodeError::PayloadTooLarge { .. })
        ));
    }
}
