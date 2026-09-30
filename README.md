# PIP-MON

A diagnostics and control ecosystem for Fallout 4's Papyrus scripting layer:
a native in-process runtime, a Papyrus API surface, and the tooling to inspect
what is actually happening while the game runs.

**Status: in development. The native runtime works. The Papyrus integration is
built but not yet proven against a live game.** See
[What actually works](#what-actually-works) before relying on anything.

---

## The one-paragraph version

PIP-MON replaces the *tooling role* that F4SE and the Papyrus extenders fill —
live introspection, diagnostics, and script-extending libraries — without
requiring F4SE to be installed. The game and the Papyrus VM are never
reimplemented or monkey-patched; the whole point is to instrument them as they
are and change only the parameters.

---

## What actually works

Being blunt here on purpose. A README that oversells is worse than none.

### Verified

| | |
|---|---|
| **In-process runtime** | Loads into a live Fallout 4 with **no F4SE and no extenders**. Runtime imports are `KERNEL32.dll` only. |
| **Telemetry** | Live V-Link stream: heartbeats, memory, resolver state. Verified with `totalEventsDropped = 0` and a monotonic sequence. |
| **Address resolution** | **18** vtable targets resolved from a validated address database. Every one has its RTTI class name confirmed against the binary and its slot count **measured** from the real table; the build fails if the two ever disagree. |
| **Papyrus API surface** | 13 functions declared, compiled to a real `.pex` by the Creation Kit, and cross-checked against the C++ dispatch table **in both directions** by the build. |
| **Build gate** | 5 stages, all green: native, Papyrus, launcher, Python, Rust. |

### Not verified — and the largest of these is the important one

- **The Papyrus integration is NOT proven.** The dispatch table exists and is
  tested, but nothing has yet asked a live game's VM to actually resolve one of
  our functions. That experiment is the project's central open question, and it
  has not been run.
- **No vtable slot is hooked yet, and that is deliberate.** Resolving 18
  interfaces tells you they exist and how big they are. It does not tell you
  which slot is which method — that needs a C++ class declaration in
  declaration order, which this project does not have for BSScript. Hooking a
  guessed slot index means detouring into an unrelated function, so nothing is
  hooked rather than something hooked at a guess. See `HANDOVER.md` §13.
- **The six old signature-scanned targets are gone, not pending.** Fallout 4
  has no class named `PapyrusVM`, `PapyrusThread` or `PapyrusScript`; the
  patterns were written for classes that do not exist, so no byte tuning could
  ever have matched them. Their real counterparts are in the table above.
- **The dashboard has never been run.** It imports and its tests pass, but no
  one has looked at it.
- **There is no installer.** Staging is currently a manual copy, which is the
  single most user-visible gap.

---

## Build

```
build_all.bat
```

Expected output:

```
V-Probe self-test: 15 pass, 0 fail, 2 skip
  OK  every declared vtable matches the binary     (18 targets)
45 passed          (launcher)
67 passed          (python)
test result: ok. 5 passed    (rust)
#  ALL GATES PASSED
```

If your self-test count differs from 15, or the vtable line is missing, the
build is not what this README describes. Check `HANDOVER.md`, which records the
current state.

### Toolchain

- Visual Studio 2022 BuildTools (`vcvars64.bat` is called explicitly; **cmake is
  not used for native code** on this machine because neither Visual Studio
  install is enumerated by `vswhere`)
- Python 3.12
- Rust / cargo
- **Creation Kit** (Steam app **1946160**) for the Papyrus compiler. The Papyrus
  stage **skips** without it rather than failing, so the native side is still
  buildable — but the `.pex` will not be produced.

---

## Running it

```
powershell -ExecutionPolicy Bypass -File tools\attach_inject.ps1 `
    -ProcessName Fallout4 -DllPath stage\stage\vprobe.dll

python tools\vlink_probe.py --summary-only
```

Attach to a **running** game, or use the launcher. See
`tools/LOG_FORMAT.md` for the reader's output and filter options.

---

## Layout

```
build_all.bat                    the gate. Start here.
HANDOVER.md                      current state, cold-start brief
PIP-MON_CONSOLIDATED.txt         the design record (26 sections)

vprobe/            in-process runtime (C++, x64)
  include/           PipmonEntry, PapyrusApi, VersionConfig, Signatures,
                     IPCServer
  src/               main, PapyrusApi, VersionConfig, IPCServer, SelfTest
  papyrus/           the PipMon: surface: .psc, .ppj, flags, build
  libs/              per-build address database + the derived binary blob

tools/             read-only inspectors and the build-time generators
  read_rtti.py       the game's own RTTI class names, out of Fallout4.exe
  measure_vtable.py  vtable identity and extent, offline, gated
overseer_cli/      the consumer tier: Textual dashboard + Rust protocol crate
launcher/          pre-flight and process launch
docs/              wire protocol, engineering rules, anomaly rules
```

---

## Naming

Three layers, deliberately different, and conflating them is a real bug — it
happened once and the self-test now catches it.

| Thing | Name | Why |
|---|---|---|
| The product | `PIP-MON` | prose and titles |
| The runtime binary | `vprobe.dll` | shown as `V-Probe` to F4SE, so F4SE users see a familiar name |
| The Papyrus namespace | `PipMon:` | our own class. We never extend a vanilla type. |
| Our own mods | `pip-mon.<name>.esp` | matches community convention, and makes our plugins identifiable by prefix |

**We register into a namespace we own.** Not `System:`, not `Form`, not
`Actor` — extending a vanilla type is what makes extender plugins collide, and
a diagnostics tool that must coexist with every other extender has no business
doing it. The test suite asserts this.

---

## Architecture

Six layers, each written in its own idiom, each with a stated cost ceiling.
Full reasoning in section 26 of the design doc.

| Tier | What it is | Written for | Cost allowed |
|------|-----------|-------------|--------------|
| **T0** | `Fallout4.exe` as bytes | accuracy | raw, no comfort |
| **T1** | Oracle — extracts facts from T0 | provenance | slow, offline |
| **T2** | Library — the facts, queryable | speed | zero-alloc in-game |
| **T3** | Surface — the contracts | explicitness | versioned, refuses cleanly |
| **T4** | Consumer — dashboard, CLI, Papyrus | clarity | the user's language |

Plus a **hallway**: a stateless access layer providing navigation, a `depth`
axis (one-line verdict → raw bytes), provenance, and polite refusal.

The governing rules:

> A layer may never be made more comfortable than its cost allows.
>
> A fact with no provenance may not exist.
>
> Refuse, do not guess.

---

## Dependencies

Third-party components keep their own licences. **None of them is vendored
into this repository's git history.**

- Zydis (MIT) — disassembly for the detour layer
- CommonLibF4 (MIT) — a **data reference only**; nothing links or compiles it
- The Creation Kit — proprietary, used as a compiler, never redistributed
- Fallout 4 / F4SE — proprietary, never redistributed, and **F4SE is not
  required to run PIP-MON**

No game asset or extender binary is included in this project.

---

## Licence

Personal Use Licence — see [`LICENSE`](LICENSE).

Short version: **use it, mod with it, change it for yourself, share the
compiled binary. Do not publish the source, do not sell it, do not claim it.**
Not an open-source licence.

---

## Contributing

Changes are accepted under the same licence. Before opening one:

```
build_all.bat
```

must be green. If you are adding a subsystem, read section 26 of
`PIP-MON_CONSOLIDATED.txt` first — new code is reviewed against those rules.
