# FRONT LIST — get a rendered initial environment

The shortest path from "nothing generated" to "we can see it and know it stuck."
Eight steps. Each one ends in a **save point**, because the editor crashes and
the only thing that has ever been lost here is unsaved work.

Owner key: **[me]** = I run it · **[you]** = your hands on the CK / one click

| # | Step | Owner | Checkpoint after it | Blocked by |
|---|---|---|---|---|
| 1 | Snapshot the current state | [me] | `runs/tasks/facility-v0/snapshots/` | — |
| 2 | Close the CK, then click xEdit's first-run notice **once** | [you] | xEdit's own config | one click |
| 3 | Generate the **cell** headlessly, verify bytes grew | [me] | snapshot + byte check | 2 |
| 4 | Generate **fixtures**: workbench, PA station, terminal, spawn marker | [me] | snapshot + byte check | 3 |
| 5 | Attach the script + fill the 4 properties | [me] | snapshot + byte check | 4 |
| 6 | Open the CK once: set interior flag, **render the cell**, look at it, save | [you] | CK save + `EditorWarnings.txt` | 5 |
| 7 | Inventory the plugin with xEdit; confirm records, masters, links | [me] | task runner marks steps DONE | 6 |
| 8 | Live run: `coc` the cell, run the 9-stage ladder, read the verdict | [both] | `run.json` + session log | 7 |

## Why this order

- Steps 3–5 are content generation, and **none of them need the editor**. Doing
  them headlessly means the editor is opened once, for one thing (step 6: the
  interior flag and the visual check), instead of being the tool that does
  everything and loses work when it crashes.
- Step 6 is last on purpose. Rendering is the step most likely to crash (no
  CKPE, three dumps on record), so it is isolated where a crash costs one step
  and nothing else.
- Step 7 is what turns "the file got bigger" into "the right records exist".
  Until the inventory runs, every step before it is **PROXY**: plausible, not
  proven.

## The save rule

Save after each of steps 3–8, even when a step is only half done:

```
pipmon.ps1 snapshot <tag>        # e.g. "after-cell", "after-fixtures"
```

That writes a timestamped copy of the plugin and both `.pex` files into
`runs/tasks/facility-v0/snapshots/`, and pulls in the editor's own backups too.
It is one command and it is the difference between losing one step and losing
the session.

## If you would rather not click anything

Skip steps 2–5 and do the cell in the CK directly — you are already in there:

1. World → Worldspaces → `DefaultWorld` → new CELL, EditorID `PipMonFacilityCell`
2. Interior cell, small
3. Drag in: a weaponsmith workbench, a power armour station, a terminal, one marker
4. **Save** (that is step 6's save point)
5. Render the cell and look at it

Then I verify from the bytes and the inventory. It is the same end state; the
headless route just keeps the editor out of the work.

## Revert points available right now

| file | bytes | what |
|---|---|---|
| `PipMonTestFacility.esp` (live) | 66 | empty plugin, saved 14:49 — nothing generated yet |
| `PRIOR-WORK-973B.esp` | 973 | your earlier session's plugin, preserved |
| `PipMon.pex` / `PipMonTestFacility.pex` | 1,034 / 12,080 | compiled surface, deployed and current |
