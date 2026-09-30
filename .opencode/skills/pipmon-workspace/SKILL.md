---
name: pipmon-workspace
scope: meta
description: Operating rules for the PIP-MON / Fallout 4 Creation Sync workspace on this machine. Use when working in "Pip-mon Script Management system", when driving tools\pipmon.ps1, when running headless xEdit (FO4Edit) or the Creation Kit, or when asked what state the project is in. Covers the never-block-on-long-runs rule, the JSON surface contract, CK vs GECK naming, and the measured xEdit 4.1.5f scripting limits.
---

# PIP-MON workspace: how to work here

## The one rule that matters most

**Never block on a long third-party run.** xEdit takes ~3 minutes to load the
curated core. The Creation Kit can hang indefinitely. A blocking tool call means
no new input, no visibility, and a strong temptation to kill a process that was
actually working.

Correct pattern:

1. Launch detached (`-Async`, `Start-Process -WindowStyle Hidden`, or a `Task`
   subagent), returning immediately.
2. Poll with **short** calls (`tools\validate_plugin.ps1 -Collect`, or
   `Start-Sleep -Seconds 20` inside one bounded call).
3. Delegate the polling to a subagent when the wait is long, so the main thread
   stays useful.
4. Never invent progress. If a log has not moved, say it has not moved.

The user can also paste tool output directly; that is a first-class input, not a
failure.

## One surface, one contract

`tools\pipmon.ps1` is the entry point. Every command emits one JSON envelope:

```
{ "schema": "pipmon.surface/1", "command": ..., "status": GREEN|RED|SKIP|BROKEN|OK,
  "ok": bool, "reason": null|string, "data": {...}, "provenance": {...} }
```

Exit codes: `0` GREEN/OK, `1` RED, `2` BROKEN, `3` SKIP, `4` usage.

`tools\pipmon.ps1 caps` is the discovery document. Read it first.

**SKIP is never PASS.** "We did not look" and "we looked and it is fine" are
different facts. Never collapse them, in any report or aggregate.

## Retrieval: ask the index, do not grep and guess

The workspace has a local, dependency-free RAG (SQLite + BM25, no network, no
model). Every hit carries path, line range and hash.

```powershell
tools\pipmon.ps1 rag index                                  # rebuild
tools\pipmon.ps1 rag stats                                  # what is indexed
tools\pipmon.ps1 rag vocabulary                             # the words this index knows
tools\pipmon.ps1 rag query -Query "xEdit pascal API" -Limit 3
tools\pipmon.ps1 rag query -Query "load order" -Kind state
tools\pipmon.ps1 rag query -Query "cell creation" -Format paths   # cheapest discovery
```

**Query with the project's own words and let expansion do the rest.** The index
is lexical, so vocabulary mismatch is the main way a query fails. Expansion is
on by default and raised a measured query from 13.7 to 72.6. To add words, edit
`ai_context/vocabulary.json` — never the code. `rag vocabulary` is the
machine-readable version; a program should call it at startup rather than
hardcoding terms.

Useful groups: `editor_xedit` `editor_ck` `editor_geck` `scripting_language`
`xedit_api` `record_format` `load_order` `pipmon` `layering` `resolver` `wire`
`stages` `facility` `locations` `checks` `tooling` `retrieval`.

Formats: `dense` (default, `lineno|text`, `*` marks a matching line, one
metadata header per hit), `tsv` (metadata rows), `paths` (rank+path only),
`json` (whole chunk). Paging is `-MaxLines N -Page P`, and the header reports
`page=P/T`. Chunks cap at ~1400 chars so max 118 lines; large output comes from
hit count, not chunk size. Full spec: `ai_context/rag_output_contract.md`.

Two honesty rules that apply to retrieval: `x=N[...]` in a header means the hit
matched partly via expansion, so verify against the file before repeating the
claim. And `no chunk matched` is an empty result, not a pass.

## Ranking: constraint over aspiration

Scores are weighted, not raw BM25. The governing rule: **content encoding a
constraint or a measured limit outranks content describing an aspiration**,
because acting on an aspiration yields a broken build and acting on a constraint
yields a correct one. Authority tiers run `compile-verified` (2.6) >
`measured` (2.4) > `upstream-verbatim` (2.1) > `derived` (1.6) >
`judgement` (1.0) > `unproven` (0.7) > `aspiration` (0.35).

`--explain` prints every factor by name; `--no-weights` gives raw BM25 so the
policy stays arguable. Weights live in `ai_context/ranking.json` and must never
be hardcoded in the tools. Never cite a hit from an `aspiration` or `unproven`
tier as fact — say it is unproven. Rationale: `ai_context/ranking_model.md`.

## Curated context, and the rule for editing it

`ai_context/` holds the corrected layer over raw sources. It exists because
upstream documentation is authoritative and still misleading: `AddNewFileName`
reads like a registration call and is really a plugin-file creation call, which
produced one wrong recipe before the signatures were read.

- `papyrus_syntax_rules.md` -- FO4-specific Papyrus, compile-verified. The
  negative table is the valuable half: Skyrim habits that do not exist here.
- `fo4_records_guide.md` -- record layout and the xEdit scripting API, with the
  functions that do not exist called out by name.
- `project_blueprint.md` -- architecture, layering, current state.
- `skyrim_capability_adoption.md` -- what to implement from Skyrim, and what to
  refuse. Read before proposing a capability.
- `rag_output_contract.md` -- retrieval input/output formats.
- `vocabulary.json` -- query vocabulary. Edit this to add words, not the code.

## Naming: these get conflated, so do not

- **CK** = Fallout 4 Creation Kit (`CreationKit.exe`). The editor in use here.
- **GECK** = Garden of Eden Creation Kit, a **Fallout 3 / New Vegas** editor.
  NOT the FO4 CK, and not in use. It is a separate peer tool on the replacement
  list, to be modernized through our own mod later.
- **xEdit** = FO4Edit, the community record editor and headless script host.

No F4SE loader is deployed, by design. PIP-MON replaces that layer. `Data\F4SE`
DLLs, if present, are inert.

## xEdit / FO4Edit 4.1.5f: measured limits

Full detail with evidence: `runs\xedit\fo4edit-4.1.5f-pascal-api.md`. Query the
RAG for it rather than re-deriving.

- A full core load reaches the script's `Finalize` at ~2m15s, ~3 min wall clock.
  **Timeouts under ~4 minutes are false negatives.** A 90s and a 110s timeout
  each produced a bogus `SKIP`.
- First headless run hung forever on the first-run notice. A human cleared it
  interactively. Until that happens, headless must report `SKIP`.
- `GetPluginName` **does not exist** in 4.1.5f. Verified working: `Signature`,
  `GetElementEditValues`, `FixedFormID`, `IntToHex`, `TStringList`.
- Unproven, presume absent: `ProgramPath`, `AddMessage`, `GetActivePlugin`,
  `AddNewElement`, `SetElementEditValues`.
- Therefore the pascal template takes `%%OUTPATH%%` / `%%PLUGIN%%` placeholders
  substituted by the PowerShell launcher. Do not "fix" a script by guessing a
  replacement API; substitute literals.
- A failed script emits **nothing**. Always capture xEdit stdout/stderr and the
  `FO4Script_log.txt` tail into the failure report.
- xEdit loads `Fallout4.ccc` and the DLC list *in addition to* `plugins.txt`, so
  the 35-entry core profile does not bound the load. Plugin graph and resource
  graph are different reports.

## Editor safety

- Never launch, script, or write to a running CK or xEdit. Refuse and say why.
- `tools\pipmon.ps1 editor` is read-only by design. Do not make it drive the CK.
- The CK has three crash dumps on record and no CKPE. Prefer headless.
- Snapshot after every complete or partial step: `tools\pipmon.ps1 snapshot <tag>`.
  Prior work is already saved at
  `runs\tasks\facility-v0\snapshots\PRIOR-WORK-973B.esp`.

## Load order

`tools\linksync.ps1` owns `plugins.txt`; Vortex can rewrite it and strip
unmanaged plugins, so re-apply after any Vortex operation. CK's
`File -> Data` does **not** read the game `plugins.txt` tick state; CK and game
load order are separate ownership.

## Current state (verify before trusting)

`Data\PipMonTestFacility.esp` is 66 bytes, CRC32 `E1DD5E4D`, **0 records**. The
facility has no content. Layer A is absent, so S0 (a compiled `.psc` reaching
our natives) is unproven: no BSScript vtable slot is hooked. Re-query
`tools\pipmon.ps1 status` and `caps` instead of trusting this paragraph.

## Green gates are not goal alignment

The five-stage build gate proves build integrity: vprobe compiles /W4 /WX with
17 self-tests, papyrus compiles with the real CK compiler, plus python 108, rust
5 and launcher 45 checks. It says nothing about S0, facility content, control
plane behaviour, or retrieval quality. A fully green gate is consistent with the
facility plugin holding 0 records and no vtable slot being hooked. Do not report
green gates as progress toward a goal; name the goal check separately. Audit:
i_context/goal_alignment.md.

Use -Kind code or --path when the question is *where is the implementation*:
BM25 favours documents that repeat the query terms, so a short source file loses
to a document discussing the topic.
