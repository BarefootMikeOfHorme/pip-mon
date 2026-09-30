---
title: PIP-MON project blueprint
purpose: What this project is, how it is layered, and what is currently true. Read before making an architectural change.
derived_from:
  - HANDOVER.md
  - PIP-MON_CONSOLIDATED.txt
  - docs/ARCHITECTURE.md
  - docs/ENGINEERING_RULES.md
  - docs/POSITIONING.md
  - docs/IPC_PROTOCOL.md
  - vprobe/papyrus/PipMon.psc
  - vprobe/src/PapyrusApi.cpp
  - tasks/capabilities.json
  - ai_context/papyrus_syntax_rules.md
  - ai_context/fo4_records_guide.md
authority: judgement
trust: architecture is as documented; current-state claims are dated 2026-09-30 and must be re-verified with tools\pipmon.ps1 status
---

# PIP-MON: what this is

## The one-line version

PIP-MON is a Fallout 4 extender built **without F4SE**. It owns the scripting
and telemetry layer that F4SE, AddressLib, Buffout, po3, MCM, Canary and CKPE
would otherwise own, and everything else in a load order is an add-on built
around it.

## The load-bearing constraint

**No F4SE loader is deployed, by design.** The DLLs under `Data\F4SE\Plugins`,
if present, are inert. Anything that depends on F4SE and is not yet replaced
will not work, and that is a known, accepted interim state rather than a bug to
be worked around. The replacement is the work.

## Hosts, and the naming trap

- **CK** = Fallout 4 Creation Kit. The authoring host.
- **GECK** = Garden of Eden Creation Kit, a **Fallout 3 / New Vegas** editor.
  Not the FO4 CK, not in use. It is a separate peer tool on the replacement
  list, to be modernized through our own mod later.
- **xEdit** = FO4Edit, the community record editor and headless script host.
- The playable game is the runtime host.

CK and the game are tandem hosts on the same mod, linked through Creation Sync.
The CK authors, the game plays, and the same plugin is validated by both.

## Layering

**Layer A** is the VM hook: the BSScript vtable slot that lets native code
intercept a Papyrus function call. **Layer B** is the Papyrus-visible API
surface declared in `PipMon.psc` and implemented in `PapyrusApi.cpp`.

Layer A does not exist yet. That is the central open question, and it is why
S0 is unproven: a compiled `.psc` calling `PipMon.GetVersion()` has never been
shown to reach a native we registered, with no F4SE.

We register into **our own class** and never extend a vanilla type. Not
`System:`, not `Form`, not `Actor`. That is why this coexists with every other
extender instead of competing with them.

## The tiered resolver

| Tier | Mechanism | Role |
| --- | --- | --- |
| 1 | AddressLib lookup against an address database | The stable path when the database is current |
| 2 | vtable slot derivation | Survives a moved function, given a class declaration |
| 3 | AOB / signature scanning | Last resort, and the one that breaks on patch days |

The surface reports **which tier** resolved each probe, so a triage tool can
explain itself instead of printing a bare success.

**18 of 18 probes resolve** through Tier 1 on this install. Layer A/native
registration remains unproven, so dispatch has never been exercised.

## The wire

Native code and Papyrus do not share memory. Findings travel over a wire whose
contract is in `docs/IPC_PROTOCOL.md` -- **partly fiction; see HANDOVER
section 11** before trusting it. T4 of the design is the dashboard and CLI,
which is the project's actual output channel, rather than an in-game menu.

## The S0 experiment

`vprobe/papyrus/PipMonTestFacility.psc` is the first script in the project that
calls the PipMon native surface. Nothing else does: the test-lab scripts
exercise loop, leak and terminal behaviour, and the bridge drives console
commands, but none invokes `PipMon.GetVersion()`. So the central question has
never actually been posed to the game. This file poses it.

It runs its probe from a one-shot timer rather than from `OnInit`, because a
cell that loads and immediately fires native calls is indistinguishable from a
bug while diagnosing one.

Read `ai_context/papyrus_syntax_rules.md` before editing it. `OnInit` is the
only event that script can declare, and the reason is a hard toolchain
constraint, not a preference.

## Tooling and the surface

`tools\pipmon.ps1` is the single entry point. Every command emits one JSON
envelope with one exit-code vocabulary, and `SKIP` is never collapsed into
`PASS`. `tools\pipmon.ps1 caps` is the discovery document.

Supporting tools: `taskrun.ps1` (resumable task groups with capability deltas),
`linksync.ps1` (owns `plugins.txt`; Vortex can rewrite it and strip unmanaged
plugins),`ck_session.ps1` (curated load-order swap), `watch_papyrus.ps1`
(compile, fix compiler-named flags, verify, deploy), `validate_plugin.ps1`
(headless xEdit), and the local RAG in `tools/rag_index.py` / `rag_query.py`.

## Retrieval

Ask the index before grepping and guessing:

```powershell
tools\pipmon.ps1 rag index
tools\pipmon.ps1 rag query -Query "xEdit pascal API" -Limit 3
tools\pipmon.ps1 rag query -Query "load order" -Kind state
```

635 files and 10,762 chunks, SQLite plus BM25, standard library only, no
network and no model. Every hit carries path, line range and hash.

## Load order

35 curated core entries in `tasks/session-profiles.json`, with
`PipMonTestFacility.esp` last. SS2 and Place Everywhere are excluded. The
previous 61-entry order is preserved under `runs\ck-session`.

Whispers files are present but unmanaged by Vortex and backed up under
`stage\unmanaged\whispers`. CK's `File -> Data` does **not** read the game
`plugins.txt` tick state; CK and game load order are separate ownership.

## Current state, 2026-09-30

- `Data\PipMonTestFacility.esp` is 66 bytes, CRC32 `E1DD5E4D`, **0 records**.
  No cell, no fixtures, no geometry, no properties.
- `PipMon.pex` (1034 B) and `PipMonTestFacility.pex` (12080 B) are deployed and
  valid.
- 18/18 probes resolve; **S0 is unproven** because no vtable slot is hooked.
- The Creation Kit has three crash dumps on record and no CKPE. An in-house
  replacement is wanted.
- xEdit headless is now proven to load the full core, but no validation run has
  yet produced a report. The first attempt to write one aborted on a
  non-existent API; see `runs/xedit/fo4edit-4.1.5f-pascal-api.md`.
- The cell generator in `testfacility/xedit/gen_facility.pas` is **wrong**: it
  calls `AddNewElement` and `GetActivePlugin`, neither of which exists. The
  documented replacements are in `ai_context/fo4_records_guide.md` section 5.

Re-verify with `tools\pipmon.ps1 status` and `tools\pipmon.ps1 caps` rather than
trusting this section.

## Non-negotiables

1. **SKIP is never PASS.** "We did not look" and "we looked and it is fine" are
   different facts.
2. **A fact with no provenance may not exist.** Name the file or the run.
3. **Refuse rather than guess.** A tool that declines is more useful than one
   that infers a value it did not read.
4. **Save after every complete or partially complete step.** Restore points are
   cheap; lost sessions are not.
5. **Never touch a running CK or xEdit.**
6. **Never block on a long third-party run.** Launch detached, poll short,
   delegate the wait. Never invent progress.
7. **Read the raw source when uncertain.** Recollection is not evidence.
