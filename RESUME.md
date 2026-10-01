# Resume here

Written at the end of the 2026-10-01 xEdit session, after context compaction.

**Read `HANDOVER-SESSION-2026-10-01.md` first** (7.8 KB, current). `HANDOVER.md`
is 42 KB but dated 09-30 01:53 and predates this session.

## State

| | |
|---|---|
| commit | `048dba9` on `main` |
| remote | public, https://github.com/BarefootMikeOfHorme/pip-mon |
| local | `master` tracking `origin/main` — **commit locally, push daily** |
| build | **`build_all.bat` = ALL GATES PASSED, exit 0** |
| Papyrus | **all 6 `.psc` compile** (was 4 failing / 5 errors) |
| gates green | `spec_lint` 0 · `artifact_gate` 0 · `gate_selftest` 9/9 · `surfaces_gate` 0 · `side_gate` 0 · `ownership` 0 |
| RAG | 762 files / ~16.3k chunks, `rag_selftest` 10/10 |
| plugin | `PipMonTestFacility.esp` **still 66 B, 0 records** |

## Do these in order. Do not skip 1.

1. **Fix the P4 gate — it is a wall.** It requires `records_created > 0` from a
   generator that could not create records, so it *cannot* pass. A red P4 after a
   **successful** `wbCopyElementToFile` would read as the create having failed.
   That is the trap, and it costs a cycle. Detailed in
   `ai_context/plans/create_environment.pyr` → P4 → the second `verify` entry.

2. `wbCopyElementToFile(aBaseCell, targetFile, True, True)` — documented,
   untested, and needs **no group addressing**. That retires the `TwbVector`
   chain which was treated as the blocker all session.

3. `FileWriteToStream(targetFile, fs, False)` — **three** arguments.
   `SaveAs.pas:63`. The declaration at `xedit_api.json` is stale and says two.
   Two args measurably raised `Not enough parameters`.

4. Verify the scratch `.esp` grew past its 66-byte header, then
   `pipmon.ps1 validate -Plugin <path>`.

## CK placement is now required before the cell is playable

Not code — placement, in `create_environment.pyr` → P4 →
`placement_requirements_2026_10_01`:

- **`PipMon_LoopTest` must be ATTACHED to an object**, not left on the quest.
  Its Scriptname is `extends ObjectReference` now, because `self.GetFormID()`
  needs a real static type on `self` and a bare `ScriptObject` cannot be cast.
- **`PipMon_LeakTest` needs at least one** of `ActorSettler` / `ActorRaider` /
  `Workbench` assigned. All unassigned is a **false pass**: the tick falls
  through all three and reports a healthy zero.

## Two capability gaps, both Layer A work

Compile-verified absent from all 2,428 staged base scripts — not typos:

- **No script can start a second thread.** `SpawnThreadFromCustomEvent` is SKSE.
  So `PipMon_LoopTest` **cannot exercise `vm_starvation`** (needs N≥2). It now
  records `RequestedThreads` and `ThreadsSpawned` separately so a run reports
  the gap rather than silently testing N=1 while claiming N.
- **No script can stop itself.** `self.Cancel()` and `GetOwningObjectOfThread`
  are absent, so every termination is a *request* the native runner performs.

## FO4 Papyrus rules discovered 2026-10-01

All compile-verified against 2.8.0.4 and recorded in
`ai_context/papyrus_syntax_rules.md`. The expensive ones:

- **`Int Function Name()`** — the return type goes *before the declaration*.
  `Function Name() int`, `Function Int Name()`, and untyped all fail.
- **`none`, not `0`**, for comparing a reference. `0` gives *"cannot compare a
  objectreference to a int"*.
- **No `break`.** *"variable break is undefined"* — use a guarded flag.
- **A non-`Native` script cannot declare a custom-named event**, and
  `StartTimer` does not help. The name is the problem, not the wiring.
- **`FormList` is the only length-capable container** (`GetSize`/`GetAt`/
  `AddForm`). Plain arrays have no length, and `FormList` is the *only* type in
  the base scripts declaring `GetSize`.
- **A loop error can be blaming a loop that isn't at fault.**
  `SpawnThreadFromCustomEvent` reported `required (...)+ loop` with no loop
  involved. When the compiler names a loop that looks right, look earlier.

## Three things that will bite if forgotten

- **xEdit leaks on every abort.** `Stop-Process xFOEdit64` before relaunching, or
  the instance lock refuses the run.
- **The collector races a just-launched job** and returns "converged" against a
  *stale* exception log. Two false FAILs came from that. Trust the trace, not
  the harness verdict.
- **`ck-session prepare` is inert** and writes `plugins.txt.proposed.txt`. It no
  longer overwrites. Do not restore the `Set-Content`.

## The long pole is not the generator

Layer A is not hooked, so no `.pex` reaches native code.

- *Records exist and load* — roughly 30 minutes away.
- *Something executes in-game* — a different and much larger track.

## Left rough, deliberately

- Remote `README.md` has a wrapped line: `for fo` / `4 and ck`.
- Local `README.md` still claims `ALL GATES PASSED` — **that is now true**, but
  it predates this session and should be rewritten rather than left.
- GitHub reports `NOASSERTION` for the licence because the PolyForm text is
  written rather than pasted canonically.
- OverseerBridge's `BridgeAction` 3/4 and the `CustomEvent` rename mean the
  native side's event names need checking once Layer A exists.

