# HANDOVER — session 2026-09-30/10-01

State at the end of the xEdit generation session. Read this before touching
`testfacility/xedit/`, `tools/orchestrate.py`, or the RAG.

## The one thing to know

**`PipMonTestFacility.esp` is still a 66-byte header with zero records.** Nothing
has been created in it. Everything below is either infrastructure, corrections
to wrong beliefs, or measured facts about the two hosts.

## What is proven

| | evidence |
|---|---|
| xEdit loads a script and reaches `Finalize` | report at 20:33, PASS, 2,287,300 records, 64,926 CELL, 140 signatures |
| `Add(targetFile, 'CELL', True)` works | twice, 22:58 and 23:29 — an element exists on the file |
| `GetNewFormID(targetFile)` works | `0x00004C50` |
| `wbCopyElementToFile` is the documented create primitive | Tome of xEdit §13.8 — **not yet executed here** |
| `FileWriteToStream` needs **three** args | passing two raises `Not enough parameters`; `SaveAs.pas:63` uses three |
| CK/xEdit 25K heartbeat format | watched live, counting to 2,250,000 |
| Papyrus builds | `pipmon.ps1 build -NoDeploy` GREEN; 1,034 B and 12,080 B pex |
| deploy verification | exit 0, all checks passed |

## The next thing to try

`wbCopyElementToFile(aBaseCell, targetFile, abAsNew := True, abDeepCopy := True)`
then `FileWriteToStream(targetFile, fs, False)`.

It is the documented primitive and it **does not need group addressing at all**,
which retires the `TwbVector → wbPositionToGridCell → wbGridCellToGroupLabel`
chain that was treated as the blocker for the whole session. `Add` on the file
also works but is undocumented for that use; prefer the documented call.

## Wrong beliefs corrected this session

Each of these was asserted and then measured false. They are the expensive ones.

1. **Papyrus has no record-creation API.** Wrong question. Creation is an xEdit
   host call, not a Papyrus one.
2. **Two comparisons joined by `and`/`or` raise `Type mismatch`.** True, measured
   22:32. Now `dialect_rules` in `xedit_api.json`, enforced by `artifact_gate.py`.
3. **`ElementID` / `IwbGroupRecord.Count` / `GetPluginName` do not exist.** True,
   but the first two were never looked up — the real names are `FixedFormID` and
   there is no `Count`. The declaration was in `third_party/xedit/Edit Scripts/
   xEditAPI.pas` the whole time.
4. **`FixedFormID` returning `0x00000000` was a pass.** It was a **silent null**.
   `Add` returns `IwbElement`; `FixedFormID` requires `IwbMainRecord`; the
   hierarchy puts them on different branches. A call that cannot fail is not a
   proof. The hierarchy is in `ai_context/reference/xedit_pascal_api.md`.
5. **B7 "do not author in the CK" is a policy.** It is a first-step tactic. The
   CK is the authoring host and the project intends to replace the *extensions*,
   not skip the editor.
6. **CKPE absent = broken deployment.** No. It is a scripting extension this
   project replaces; its absence is a pre-operation state. Now `[INFO]`, exit 0.
7. **Nothing pins the load order.** `pipmon.ps1 link` owns
   `AppData\Local\Fallout4\plugins.txt`, 35/35 matching profile, with snapshots.

## Two RAG bugs that made everything look broken

- **cp1252 stdout.** `rag_query.py` raised `UnicodeEncodeError` printing any hit
  containing `→` or `—`, *after* finding and ranking it. The wrapper reported a
  nonzero exit and no hits. Two freshly indexed documents were unretrievable
  with the ranker holding them at position 1. Fixed at the stream.
- **Subject tags are a partition, not a weight.** `@ck navmesh finalize` could
  not beat a spec file scoring 211 on "finalize" with any sane multiplier, and
  raising one wrecked untagged ordering. Tagged files now sort ahead of the
  corpus and rank by score only among their peers. Untagged queries are
  unchanged because the feature is absent from the comparison.

## Load order — the number that kept moving

`FileCount` is 55/60/44 across runs. Not a bug. Your core is
`AppData\Local\Fallout4\plugins.txt`, 35 entries, unchanged since 14:36;
Vortex's `loadorder.txt` is 202 entries with `.ghost` entries and is what xEdit
resolves. The documented blocker `xedit-load-width` says exactly this: xEdit
loads `Fallout4.ccc` and the DLC list *in addition to* the core, so the 35-entry
core does not bound the load. **A moving count is about DLC, not about your edit.**

`ck-session prepare` no longer overwrites anything — it writes
`plugins.txt.proposed.txt` and names what a standard-state restore would add and
drop. The `Set-Content` that ate the CK Data tab changes is gone.

## Do not repeat

- **Rewriting a file to "fix" it.** `gen_facility.pas` was overwritten three
  times; the diff was 231+/105- when the claim was "in-place repair". Repair with
  `Edit`, show the diff, keep a backup.
- **Regex surgery on a working file.** A `re.sub` to strip a block deleted 72
  lines including the whole query pipeline. Restore from git **after** checking
  what uncommitted work that would destroy.
- **Guessing an API name and then reporting absence.** Look it up in
  `xEditAPI.pas` or the shipped `Edit Scripts/`.
- **Treating a forum post as a measurement.** The "navmesh autogenerate is
  unreliable" note was one author's experience, written up as a finding.

## Gates

```
artifact_gate   0 errors   spec_lint  0 problems   surfaces_gate  0 problems
rag             774 files / 16,444 chunks, GREEN
orchestrator    P1-P3 SKIPPED under --from P4; P4 FAILED at LINK 3
```

`rag_selftest` and `door_lint` remain RED and are pre-existing. Bare
`python tools/orchestrate.py` still exits 2 where usage output and exit 0 were
asked for.

## Two open decisions — settle these before spending runs

**1. P4's gate is a wall, and it will fail forever.**

It requires `--gen-key records_created > 0` from a generator that, until this
session, could not create records at all. A gate that cannot pass is not a gate;
it is a wall. It was tightened when the generator looked like it was about to
create something, and it was never replaced when creation turned out to need a
different call.

So P4 failing tells you **nothing** about whether `wbCopyElementToFile` works.
Fix it before the next run, or the next run is another 2-minute sweep producing
the same red. Two ways:

- replace the gate with what the stage can actually prove — that a record was
  created *in memory* and written to the scratch path, and that the scratch
  `.esp` grew
- or keep `records_created > 0` **only after** step 1 below has been shown to
  work, and treat the first run as a diagnostic that bypasses the gate

**2. "Test env running" means two different things, and they need different work.**

- **records exist and load** — unblocked. `wbCopyElementToFile` →
  `FileWriteToStream` → copy to the game folder → `pipmon.ps1 validate`. This is
  the next 30 minutes of work.
- **something executes in-game** — needs **Layer A**, and nothing else gets
  there. No vtable slot is hooked, so no compiled `.psc` can reach a native
  function. A correct plugin and a clean `.pex` still prove nothing at runtime.

Worth naming which one is being asked for, because the first is nearly done and
the second is a much larger track. Everything in this session was on the first.

## Blockers

| id | state |
|---|---|
| `facility-empty` | 66-byte plugin, 0 records. Needs one cell created and saved. |
| `xedit-untested-api` | findings now in `reference/xedit_pascal_api.md` |
| `layer-a` | no vtable slot hooked; nothing Papyrus does reaches native code |
| `ckpe` | replaced by this project, not a deployment failure |
| `xedit-load-width` | DLC + `.ccc` on top of the 35-entry core |

**Layer A is the long pole.** Records on disk are not a working environment, and
no amount of generator work reaches live gameplay.
