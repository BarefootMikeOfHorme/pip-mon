# PIP-MON Engineering Rules

These are **inviolable**. They are not style preferences or optimisation targets —
each one exists because violating it causes a specific, bad failure in someone's
game. If a change seems to require breaking one of these, the change is wrong.

Terminology note: "game thread" and "main thread" mean the same thing here — the
`Fallout4.exe` thread that owns rendering. Papyrus runs on a separate pool. Both
are in the game process, and **both** are covered by Rule 1, because a Papyrus
thread stalling shows up as a game freeze just as visibly.

---

## Rule 1 — Zero main-thread blocking

**Statement.** V-Probe must never perform file I/O, string formatting, regex
parsing, JSON serialisation, or any unbounded allocation on a game thread.

**Implementation.** A hook does exactly this and nothing else:

1. Read a few fixed-width fields out of the VM structure.
2. `memcpy` a packed struct into a preallocated frame slot.
3. One relaxed atomic store into a lock-free SPSC ring.
4. Return.

Transmission is owned by a dedicated I/O worker thread holding an I/O completion
port. See `IPCServer.hpp` — the producer path is the `publish` overloads and nothing
else touches Win32.

**What this forbids specifically:**

| Forbidden on a game thread | Why | Instead |
|---|---|---|
| `fprintf` / `spdlog` to a file | blocking I/O mid-frame | send a `PluginDiag`; the worker writes it |
| `std::string` construction for a name | heap allocation | intern to a `u32` index |
| `nlohmann::json` | allocation + walk | packed struct on the wire |
| `std::map` / `std::unordered_map` lookup | potential allocation | fixed-size array, indexed |
| any `mutex` the other thread also takes | deadlock | see Rule 5 note below |
| `GetModuleHandle` / `VirtualProtect` | syscall + TLB pressure | do it at init only |

**Review question for any new hook:** *count the instructions between function
entry and return.* If the answer involves a loop with an unbounded bound, it does
not belong on a game thread.

**Note on `spdlog`:** a good logging library is still the wrong tool on a game
thread. If `vprobe` ever writes to disk, it must be from the worker thread, at a
coalesced rate, never per event.

---

## Rule 2 — Dynamic signature resolution with a safe fallback

**Statement.** Never rely exclusively on static offsets. Resolution is two-tier, and
failure of either tier disables *only the affected hook*.

**Tiers, in order:**

1. **AddressLib INI** — a static RVA per game build, read from
   `Data/F4SE/Plugins/vprobe/libs/vprobe.addresses.txt`. Fast, exact.
2. **AOB scan** — signature matching with wildcards over the executable sections of
   `Fallout4.exe` (`DynamicScanner.hpp`).

**Validation is not optional.** A matched pattern is only accepted if it also
passes `looksLikeFunctionEntry` — a real function prologue, inside an executable
section, not across a page boundary. A pattern that matches a jump table or a
string blob produces `Rejected`, and the hook is not installed.

**Three outcomes, all non-fatal:**

| Outcome | Meaning | Effect |
|---|---|---|
| `FromAddressLib` | INI hit, validation passed | hook installed |
| `FromScan` | AOB hit, validation passed | hook installed, `SCAN_FALLBACK` flag |
| `Rejected` | matched but not a function entry | **hook disabled** |
| `NotFound` | no match at all | **hook disabled** |

**Why the strictness.** Papyrus is single-threaded per script and unforgiving. A
detour installed 200 bytes into the wrong function is a crash on the next script
call, which reads to the user as "your mods are broken" — and they will be right,
and it will not be this plugin's fault in a way anyone can debug. A monitor that
disables one hook is a **working monitor**. A monitor that jumps to the wrong
address is a lost save.

**Ambiguity is treated as failure.** If a pattern matches more than once, resolution
returns null. A guess is not a fallback.

**Requirement to keep:** when a hook cannot be installed, say so, loudly, through
`PluginDiag`. `DegradedProbeRule` surfaces it. Silent degradation is the one thing
worse than a disabled hook, because the user cannot tell the difference between
"no anomalies" and "no monitoring".

---

## Rule 3 — Asynchronous control back-pressure

**Statement.** A command from OverseerCLI must never write Papyrus VM memory from
the IPC background thread.

**Reason.** The VM is not thread-safe. A write from the IPC thread can land between
a VM's internal pointer swap and its bookkeeping update, corrupting the thread list
in a way that does not crash immediately — it surfaces later as an inexplicable
quest-state failure.

**Implementation.** The control channel is one-way and queued. The IPC worker
parses the command and hands it to a queue drained on the engine's main-thread task
runner. Execution happens on the next frame, where the VM is in a known state.

**Consequences that are intentional:**

- No synchronous replies. A reply means the game thread waits on the dashboard.
- The UI never knows whether a command *succeeded*, only that it was sent. This is
  the cost of not corrupting saves.
- `force_kill` is a two-step operation, and the UI must confirm it. See pitfall 4.

---

## Rule 4 — Out-of-process analysis primacy

**Statement.** All parsing, heuristics, time-series maths, and rendering live in
OverseerCLI. V-Probe is a dumb probe.

**Why this boundary is worth enforcing.** Analysis logic is what changes. Thresholds
get retuned, new heuristics get added, the UI gets redesigned — all of it
out-of-process, all of it shippable as a Python package update with no risk to a
running game. If heuristics lived in the plugin, every threshold tweak would require
rebuilding and redistributing a DLL into someone's live save.

**Enforcement in the code layout:**

| Concern | Lives in | Never in |
|---|---|---|
| decode a frame | `protocol.py` | the probe |
| string matching, script name resolution | `detector.py` | the probe |
| rolling window, rates, time series | `profiler.py` | the probe |
| thresholds, confidence scoring | `detector.py` | the probe |
| render | `ui/` | the probe |

The probe's *only* judgement is structural: is this address a function entry
(Rule 2), and is this FormID plausible. Both are safety checks on the act of
hooking, not analysis.

**Corollary:** the probe must never need to know what a "runaway loop" is. It
reports op counts. OverseerCLI decides that 3200 ops/s for 4 s is a problem.

---

## Rule 5 — No locks shared between game and worker threads

Not in the original four, added because it is the most likely way to violate Rule 1
in practice.

A `std::mutex` taken by a hook and by the IPC worker is a potential deadlock, and
Papyrus deadlocks present to the user as **a freeze with no crash** — the hardest
class of bug to diagnose from a bug report.

**Allowed:** per-thread state in fixed-size arrays indexed by VM thread id, no
allocation, no lock. The intern table is a documented exception — it is written only
at init and on the worker, and read only after that point; if this ever becomes a
concurrent write, it needs a lock *that no game thread can reach*.

**Forbidden:** `std::mutex`, `std::shared_mutex`, `CRITICAL_SECTION` reachable from
a hook body.

---

## Pitfalls

### 1. Papyrus VM lock contention — the silent freeze

**Hazard.** Inspecting or locking a VM thread's stack while the VM is mid-GC or
mid-native-call deadlocks `Fallout4.exe` permanently. Freeze without CTD. No crash
dump. The user reports "the game just stops".

**Prevention.**
- Never lock the VM. Hook entry/exit functions where the state is known stable.
- Never walk a VM thread's native stack from a hook. Instead maintain a **shadow
  stack**: a fixed array of frames pushed at script entry, popped at exit. The
  dashboard reads the shadow, never the live VM.
- Bound the depth and truncate with an explicit flag. An unbounded walk is a
  potential infinite loop on a game thread.
- 0x400 (1024) is the VM's own limit. Do not walk past it — the walk itself is
  unsafe there, which is exactly when the bug is happening.

### 2. Pipe buffer overflow and memory inflation

**Hazard.** Papyrus can emit thousands of events per second. A stalled consumer
fills the Win32 pipe buffer, and the fix that people reach for — a bigger buffer —
converts dropped telemetry into a multi-gigabyte allocation inside the game.

**Prevention.** Fixed-capacity ring (8192 slots) in the probe. Full means drop, never
grow. Priority-aware drop (§3.2 of the protocol doc): preserve exceptions and stack
dumps, shed `VM_TICK` first. Both ends shed. The count is reported as
`eventsDropped`, and the consumer surfaces it as a **critical** finding — because a
profiler silently under-reporting is worse than no profiler, since the user trusts
the number.

### 3. Precombine and cell-load hook overhead

**Hazard.** Hooking cell load and reference-handle creation fires thousands of times
during a fast travel, and the context-switching cost shows up as an extended loading
screen or visible stutter.

**Prevention.** Aggregate. Batch reference events into a multi-entity payload and
flush every 50 ms — never one IPC message per spawned object. If cell telemetry is
ever added, it must be a **count plus a summary**, not an enumeration.

**Current status:** the probe's `FormData::CellStream` signature is declared in
`Signatures.hpp` but no hook is installed for it. `streamedCellCount` in the Memory
payload is expected to be `0` in this version. Do not add a per-reference hook
without solving batching first.

### 4. Save state desynchronisation

**Hazard.** Force-terminating a Papyrus thread mid-execution can leave quest
variables or workshop state half-written. The user's save is silently wrong, and
quest progression breaks in a way that looks like a mod bug.

**Prevention.**
- `soft_cancel` (`Script.Cancel()`) before anything else. Always offer it.
- `force_kill` requires explicit UI confirmation and a visible warning that the save
  may be inconsistent. **Not a dismissible toast — a blocking confirm.**
- The detector never auto-remediates. It reports. A monitoring tool that silently
  changes game state is a liability, not a feature.
- Save-bloat findings recommend saving to a **new slot**, never over the good one.

---

## Change review checklist

Any change touching V-Probe must answer these before merge:

- [ ] Does any code on a game thread allocate, format, or do I/O?
- [ ] Can this hook disable itself if the address does not resolve? (Rule 2)
- [ ] Does this add a lock reachable from a game thread? (Rule 5)
- [ ] Is this a heuristic? It belongs in OverseerCLI. (Rule 4)
- [ ] Does a new payload field change a `static_assert` or a Python struct size?
- [ ] Is there a test for the decode path in `test_protocol.py`?
- [ ] Can the probe still load and run with this hook entirely absent?
- [ ] Is the failure path observable by the user, or silent?
