# Architecture

## Naming

| Role | Component | Binary / identifier | Responsibility |
|---|---|---|---|
| System | PIP-MON | `pip-mon-suite` | The whole telemetry, monitoring and debugging ecosystem |
| In-game probe | V-Probe | `vprobe.dll` | Native F4SE plugin, AOB resolution, VM hooks, streams raw metrics |
| IPC API | V-Link | `\\.\pipe\vlink_telemetry` | The zero-copy transport and wire protocol between probe and CLI |
| External TUI | OverseerCLI | `overseer-cli` | Out-of-process engine + terminal dashboard |
| In-game patch | Overseer Event Bridge | `OverseerEventBridge.esp` | Optional; exposes Papyrus event hooks and console commands |

`V-Probe` and `V-Link` share the `v` prefix deliberately: they are the two halves of
one interface, and the pipe is named after the API rather than after the producer, so
renaming the probe does not break anyone's saved config.

**Trademark.** "Overseer" is an ordinary English noun and franchise lore vocabulary.
It is used descriptively here, with no Bethesda/ZeniMax assets and no claim of
affiliation. Keep it that way: no official logos, no "official tool" language, no
storefront branding.

---

## Layout

```
pip-mon-suite/
├── vprobe/                          # Component 1: in-game native probe (C++20, CMake)
│   ├── CMakeLists.txt
│   ├── include/
│   │   ├── DynamicScanner.hpp        # AOB pattern matching + module validation
│   │   ├── IPCServer.hpp             # async Win32 named pipe producer
│   │   ├── PapyrusHooks.hpp          # VM execution + thread stack interception
│   │   ├── VersionConfig.hpp         # AddressLib + version-agnostic resolution
│   │   ├── Signatures.hpp            # the AOB signature table
│   │   ├── Detour.hpp                # x64 trampoline detours
│   │   ├── TelemetryEvent.hpp        # the wire ABI
│   │   ├── FrameQueue.hpp            # lock-free SPSC ring
│   │   └── InternTable.hpp           # string interning
│   └── src/
│       ├── main.cpp                  # F4SE entry, bootstrap, watchdog
│       ├── IPCServer.cpp
│       ├── DynamicScanner.cpp
│       ├── VersionConfig.cpp
│       ├── PapyrusHooks.cpp
│       └── Detour.cpp
│
├── overseer_cli/                     # Component 2: external TUI (Python 3.12, Textual)
│   ├── pyproject.toml
│   ├── src/overseer_cli/
│   │   ├── main.py                   # entry point, tui | headless
│   │   ├── ipc_client.py             # async V-Link consumer
│   │   ├── protocol.py                # the wire format
│   │   ├── profiler.py                # rolling 5 s window
│   │   ├── detector.py                # heuristics (isolated from UI)
│   │   └── ui/                        # Textual rendering
│   └── tests/
│       ├── test_protocol.py
│       ├── test_detector.py
│       └── fake_probe.py              # synthetic producer, no game required
│
├── overseer_event_bridge/            # Component 3: optional in-game plugin
│   ├── OverseerEventBridge.esp
│   └── Scripts/Source/OverseerBridge.psc
│
├── docs/
│   ├── IPC_PROTOCOL.md               # the contract between the two halves
│   ├── ENGINEERING_RULES.md          # inviolable rules + pitfalls
│   ├── ANOMALY_RULES.md              # heuristic definitions
│   └── ARCHITECTURE.md               # this file
└── README.md
```

The two build targets are **completely decoupled**. V-Probe is CMake, needs no
Python. OverseerCLI is a Python package, needs no compiler and no game install. Either
can be built, tested and shipped on its own. Nothing in `overseer_cli` imports
anything from `vprobe/`; they share only the protocol, defined twice — once in
`TelemetryEvent.hpp`, once in `protocol.py` — and held in sync by size assertions on
both sides and by `test_protocol.py`.

---

## Thread model

Three threads, with a strict ownership rule: **only the I/O worker touches Win32.**

```
  Fallout4.exe main thread        Papyrus VM threads            OverseerCLI
  ────────────────────────        ─────────────────            ────────────
  frame loop, render
        │                             │                            │
        │  ┌── hook body ────────────►│                            │
        │  │  read fixed fields       │                            │
        │  │  memcpy packed struct    │                            │
        │  │  one relaxed atomic      │                            │
        │  └──► SpscRing ────────────┼──► IPCServer worker ────────┼──► pipe
        │                             │      (IOCP, heartbeat,      │      │
        │                             │       memory, name table)   │      ▼
        │                             │                            │   decoder
        │                             │                            │      │
        │                             │                            │      ▼
        │                             │                            │   profiler
        │                             │                            │      │
        │                             │                            │      ▼
        │                             │                            │   detector
        │                             │                            │      │
        │                             │                            │      ▼
        │                             │                            │   Textual UI
```

**The zero-overhead guarantee** lives in the leftmost hop. A hook body reads a few
`u32`s, `memcpy`s a POD struct into a preallocated frame, and does one relaxed atomic
store. No allocation, no formatting, no lock, no syscall. Transmission, heartbeats,
memory sampling, and all string handling happen on the worker thread.

**Back-pressure is shed at both ends**, never buffered. See pitfall 2 in
`ENGINEERING_RULES.md` and §3.2 of `IPC_PROTOCOL.md`.

**The consumer never blocks the loop.** A reader thread does a blocking `ReadFile`
(cancellable via `CancelIoEx`) and hands frames to the event loop through
`call_soon_threadsafe`. This is deliberate over Windows' `connect_read_pipe`: it
needs a Proactor loop, has no timeout semantics, and raises out of the loop when the
pipe breaks — a dashboard that dies because the game exited is worse than one that
reconnects.

---

## Version agnosticism

Both game generations run the same `vprobe.dll`.

```
  1.10.163 (Old Gen)                    1.10.980+ (Next Gen)
         │                                        │
         ├─ AddressLib INI ──── RVA ────┐         ├─ AddressLib INI ── RVA ─┐
         │                              │         │                          │
         │                        validate     validate                     │
         │                              │         │                          │
         ├─ AOB fallback ──── match ───┤         ├─ AOB fallback ── match ──┤
         │                              ▼         │                          ▼
         └──────────────────► validated function pointer ◄───────────────────┘
                                    │
                          ┌─────────┴─────────┐
                          │  prologue check    │  fails → hook disabled, reported
                          └───────────────────┘
```

The INI is preferred because it is exact. The AOB scan exists because the INI goes
stale: new builds, runtime patches, ASI loaders, and Next Gen retargeting all shift
targets. **The scan is a complete fallback, not a supplement** — a user with no
AddressLib install still gets a working monitor, just a slower start.

There is no build-number branching anywhere in the code. A target is a *signature*,
not a version.

### Degradation is a first-class state

A hook that cannot be resolved is disabled and **reported** through
`PluginDiag` → `DegradedProbeRule`, which names the dead probes in the dashboard.

This is the most important design decision in the probe. The alternative — silently
not hooking — is a lie the user cannot detect. A disabled hook means "this panel
shows less"; a silent failure means "this panel shows nothing and you think the game
is healthy".

---

## Adding a capability

The three questions to ask first, in order:

1. **Where does this belong?** Anything involving parsing, heuristics, or
   presentation is OverseerCLI (Rule 4). If it is not just "read a value out of the
   VM and hand it over", it does not belong in V-Probe.
2. **What does it cost on a game thread?** Ideally nothing. If it cannot be free, it
   needs a sampling interval or an aggregate, not a per-event hook.
3. **What happens when the address does not resolve?** The answer must be "that one
   feature is off and the user is told", never "the plugin fails to load".

Then: extend `TelemetryEvent.hpp` (append, add a `static_assert`), mirror it in
`protocol.py`, add the decode test **with the expected size as a literal**, decide
the drop priority, and document it in `IPC_PROTOCOL.md` §3.
