# Resume here

Written at the end of the 2026-10-01 xEdit session, after context compaction.

**Read `HANDOVER-SESSION-2026-10-01.md` first** (7.8 KB, current). `HANDOVER.md`
is 42 KB but dated 09-30 01:53 and predates this session.

## State

| | |
|---|---|
| commit | `10e9bb7` on `main` |
| remote | public, https://github.com/BarefootMikeOfHorme/pip-mon |
| local | `master` tracking `origin/main` |
| gates green | `spec_lint` 0 · `artifact_gate` 0 · `surfaces_gate` 0 |
| gates red | `door_lint` (2 problems, 17 unregistered) · `rag_selftest` · P4 |
| RAG | 774 files, GREEN · `@ck` / `@xedit` subject tags working |
| plugin | `PipMonTestFacility.esp` **still 66 B, 0 records** |

## Do these in order. Do not skip 1.

1. **Fix the P4 gate.** It requires `records_created > 0` from a generator that
   could not create records. A red P4 after a *successful* create would be read
   as the create failing — that is the trap.

2. `wbCopyElementToFile(aBaseCell, targetFile, True, True)` — documented,
   untested, and needs **no group addressing**. That retires the `TwbVector`
   chain which was treated as the blocker all session.

3. `FileWriteToStream(targetFile, fs, False)` — **three** arguments.
   `SaveAs.pas:63`. The declaration at `xEditAPI.pas:334` is stale and says two.
   Two args measurably raised `Not enough parameters`.

4. Verify the scratch `.esp` grew, then `pipmon.ps1 validate -Plugin <path>`.

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
- Local `README.md` still claims `ALL GATES PASSED` while two gates are red.
- GitHub reports `NOASSERTION` for the licence because the PolyForm text is
  written rather than pasted canonically.

All three fixable later.
