# FIX BACKLOG — findings from the cold-start eval, 2026-09-30

Not a plan. A record of what the eval found, kept out of the way until the
environment work is done. Each item states what was **measured**, not what is
suspected. Ordered by value-per-line, not by severity.

Read with: `HANDOVER.md` (resume), `ai_context/spec/surfaces.json` (statuses),
`docs/ENGINEERING_RULES.md` (rules), `runs/watch/` (the evidence below).

---

## A. The validator cannot see compile errors. This is the top item.

**Measured.** `runs/watch/` holds a 104 KB `xFOEdit64Exception.log`
(`%LOCALAPPDATA%\Temp\opencode\xedit\x\`) that nobody reads. Its message is:

```
Message: 'unit' expected but 'var' found
  ...
  xejviScriptHost.TxejviScript.Create (Line 767, "xejviScriptHost.pas")
  xeScriptHost.TxeScriptHost.CreateScript (Line 81, "xeScriptHost.pas")
  xeMainForm.TfrmMain.ApplyScript (Line 8404, "xeMainForm.pas")
```

The callstack is `CreateScript`, **not** `Initialize`/`Process`/`Finalize`. The
script **never compiled.** It is a parse error, raised before a single line of
our code runs.

**Why it matters.** `validate_plugin.ps1` reads exactly three things:
`FO4Script_log.txt` (tail 25), `xedit-stdout.log`, `xedit-stderr.log`. The
exception log is not among them, and the three it does read were **0 bytes** on
the last run. So the one artefact containing the actual cause was invisible, and
the tool's verdict came back `SKIP`/`FAIL` with no reason a human could act on.

**This is the same failure class the project already names twice** — HANDOVER
§4B ("a silent drop is the worst failure shape") and §12 ("every one of these
had a passing build and a healthy-looking pipe"). Third occurrence, same shape.

**Fix.** `validate_plugin.ps1` must read `xFOEdit64Exception.log` and surface
`Message:` as the report `reason` whenever no report was produced. A compile
error and a missing report are different bugs and must not share a verdict.

---

## B. The documented root cause is wrong.

**Measured.** `HANDOVER.md` §4C and `ai_context/spec/surfaces.json`
(`creation.xedit`) both state the abort is because the script "called
`GetPluginName`, which does not exist in FO4Edit 4.1.5f", and that it "aborted
in Finalize at 2m15s".

The evidence on disk is a **parse error at compile time**, with no
`EJvInterpreterError` and no `Undeclared Identifier` anywhere in the log. Those
are different failures with different fixes. Two documents currently record a
cause that the evidence does not support.

**Also unresolved.** `FO4Script_log.txt` ends with:

```
[00:00] Start: Applying script "validate_plugin.gen"
[10:23] Exception in unit UserScript line 86: [EAbort] Operation aborted
```

Line 86 of the generated file is `found := True;` — not an abort, and the file
contains no `Abort` call at all. Either the line number is unreliable or this
is a different run from the exception log. **Unresolved; do not build on either
reading until one run produces both artefacts from the same invocation.**

---

## C. The committed validator has never been run.

**Measured.**

| file | bytes | mtime | what it is |
|---|---:|---|---|
| `testfacility/xedit/validate_plugin.pas` | 5,222 | 19:44:24 | committed source (619f581) — one-plugin verdict |
| `runs/watch/validate_plugin.gen.pas` | 4,448 | 19:18:56 | what actually executed — load-order **inventory** |

They are **different documents**. The last executed artefact is not the
committed source, so no result — pass, fail or skip — describes the code we
have. Any "the validator ran" claim is about a file that is no longer there.

**Unproven in the new template, by its own admission** (line 20: "FIRST RUN IS
THE TEST"): `GetFileName`, `GetFile`, `FileCount`, `FileByIndex`, `MasterCount`,
`MasterByIndex`, plus `TStringList.IndexOf`, `LowerCase`, `Chr`. A compile
error costs one full load to discover. Check each against
`ai_context/spec/xedit_api.json` **before** spending a load.

---

## D. Stage 2 is unscoped, and that is a design decision nobody made.

**Measured.** Confirmed by the operator: the run was at 156 K of process read
when it was cut off. The old template's own comment (line 31) states it plainly:

> xEdit loads the whole active load order even when handed a single path

So "validate one plugin" still pays for all 61 enabled plugins
(`plugins.txt`, 61 enabled of 177 lines) — ~2m15s measured, and growing with the
load order. Every future run pays it again.

**Undecided.** Levers, none chosen:
- a scratch `Data` folder with a minimal `plugins.txt` — truest, most setup
- temporarily swap `plugins.txt` via `tools/linksync.ps1` (snapshot/apply/restore
  already exists) — cheapest, touches a live file
- accept it and always run detached — no code, keeps the cost

This is a plan decision, so it belongs in `ai_context/plans/create_environment.pyr`,
not in a script.

---

## E. Orchestrator gaps (the operator's list, restated against the code)

`tools/orchestrate.py`, read against what was asked for:

| # | asked for | measured | where |
|---|---|---|---|
| E1 | save valid progress at end of each stage | `run_plan` prints `"verified."` and continues. **Nothing is written.** No state file, no resume, no checkpoint. | `orchestrate.py:214-215` |
| E2 | trace log in the log output | `record()` writes JSONL with exit codes only. The gates' actual output is captured into `detail` and then **discarded** — it is never printed. | `orchestrate.py:59-63`, `135-137` |
| E3 | dashboard short output | none. Long output is printed inline with no summary. | `orchestrate.py:177-187` |
| E4 | counts + error code at the bottom | none. No per-phase tally, no final code line. | whole file |
| E5 | declared state / progress level | `blocked_reason` exists per phase, but no run-level state and no "where did we get to". | `orchestrate.py:172-175` |
| E6 | scope the work | `SHELL` allowlist is 5 entries; phase P1's actions include `Get-Process xFOEdit64`, handled by a special case. Any new command needs adding. | `orchestrate.py:43-50` |

**Shape of the fix**, if it is wanted as one change: a `state` object written
atomically after every phase (satisfies E1/E5), a `trace()` that both prints a
human line and appends to the JSONL (E2), and a `summary()` that prints one
compact block — phases run/ok/blocked/failed, gate tallies, and the exit code
(E3/E4). That is ~40 lines in one file and touches no plan.

---

## F. Spec claims that contradict each other or the disk

Not blockers. Recorded so a later reader does not lose an afternoon to them.

| claim | source | measured |
|---|---|---|
| index is 777 files / 12,223 chunks | `surfaces.json` `ai.retrieval` | 751 files / 9,836 chunks (`pipmon.ps1 rag stats`) |
| python checks = 106 | README, HANDOVER | 108 in `goal_alignment.md` and `program_components.json` |
| CommonLibF4 "has **no** BSScript headers at all" | `HANDOVER.md` §7.1a | **false** — see G |
| BSScript.h "holds native declarations in method order" | `surfaces.json` `provider.commonlib` | true, but at a path nobody has been using |
| F4SE is a hard runtime dependency | `POSITIONING.md` §4 | runtime imports `KERNEL32.dll` only; no F4SE deployed |
| `docs/ENGINEERING_RULES.md` = STALE, not started | HANDOVER §8, §11 | confirmed still stale (Rule 2 says two-tier, now four) |

`POSITING.md` §4 is the one that will actually mislead someone: it says
`vprobe.dll` is loaded by F4SE from `Data/F4SE/Plugins/`, which is the opposite
of the current design.

---

## G. Lead, not a claim: the Layer A input may already be in the tree

**Measured.** `HANDOVER.md` §7.1a names one missing input — a BSScript class
declaration in method order — and says the pinned clone carries "vtable
ADDRESSES but NO BSScript headers at all". The header is present:

```
third_party/CommonLibF4/CommonLibF4/include/RE/Bethesda/BSScript.h   65,388 B
```

(note the doubled directory: it is a full `.git` clone, so the repo root is one
level deeper than every spec path assumes — which is very likely why it read as
absent.)

It carries `namespace RE { namespace BSScript {`, per-class
`static constexpr auto VTABLE{...}`, virtual methods **in declaration order**,
and trailing **slot index annotations** (`// 00`, `// 01`, … `// 3D`).

Spot check against the 18 measured slot counts in HANDOVER §13:

```
IVirtualMachine  62 == 62  YES      IClientVM      3 ==  3  YES
IMemoryPagePolicy 6 ==  6  YES      ILoader        4 ==  4  YES
IProfilePolicy    5 ==  5  YES      IFunction     21 == 21  YES
ErrorLogger       9 !=  3  conflict  IComplexType   9 !=  2  conflict
```

Six agree. Two conflict — most likely my throwaway scanner bleeding into the
next class, **not** a real disagreement; it needs a proper parse before anyone
treats it as either. Ten of the eighteen had no annotations found at all.

**So: promising, unproven, and cheap to settle.** The honest statement is that
the input HANDOVER says is missing is present and has never been parsed against
the measured counts. That is a real task with a real gate — and it is the
difference between Layer A being blocked on an external dependency and blocked
on an afternoon's work. Do not record it as unblocked until a gate passes.

Two traps visible in the header already:
- **declaration order ≠ slot order.** Overloads are annotated out of sequence
  (`CreateObject` is `// 17` then `// 16`; `GetVariableValue` `// 26` then
  `// 25`). Counting virtuals will produce wrong indices. The annotation is the
  authority.
- the annotations stop at `0x3D` for a table measured at 62 slots, so the tail
  of that class is not annotated in the header and needs another source.

---

## H. Housekeeping

- `runs/watch/xedit-job.json` holds a **dead** pid (311200) from 19:18.
  `xedit-latest.json` is a `SKIP` from a different, earlier attempt. Nothing
  cleans up after a killed run, so the next launch has to re-derive that
  nothing is in flight.
- `xedit-stdout.log` and `xedit-stderr.log` are 0 bytes. Zero bytes is
  information — it is what a stalled-at-dialogue run looks like — but nothing
  labels it as such, so it reads as "no news".
- `third_party/CommonLibF4` path depth: every spec that names
  `third_party/CommonLibF4/include/...` is wrong by one level.
