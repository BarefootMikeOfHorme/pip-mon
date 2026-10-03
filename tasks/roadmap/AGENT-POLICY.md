# POLICY FOR DELEGATED AGENTS

Binding on any agent working this repo unattended. Read this before touching
anything. It exists so the rules are in one auditable place rather than repeated
in three prompts that will drift apart.

## 1. Revertability, always

- **One commit per verified task.** Never batch two tasks into one commit.
- Every commit message states **VERIFIED:** and **NOT VERIFIED:**. Both, always.
  A commit stating only what was verified is incomplete.
- Commit after **5–10 minutes** of work, whichever comes first.
- Nothing is committed unverified. If you cannot verify it, say so in the commit
  and in your report rather than claiming success.

## 2. No deletes

- **Never** delete a file, a directory, a line, or the contents of a file.
- **Never** empty a file to reuse its name.
- **Never** `git commit --amend`, `git reset --hard`, or `git push`.
  Rewriting visible history destroys the evidence of what was tried, which is the
  one thing this project keeps its superseded files FOR.
- If something is genuinely wrong with an existing file, add a numbered variant
  and say in the report which one is authoritative. Do not "clean it up".

## 3. Small repair vs major change

**Small repair** — one or two lines inside a long snippet, surrounding lines
correct and staying correct:
edit in place, commit with a diff and a changelog line naming the file, the line,
what was wrong, and why the old value was a lie.

**Major change** — anything longer than a couple of lines, anything that replaces
a block, anything that adds a field or changes a shape:
the previous version stays on disk. Write a **numbered** file. The original is
never edited, truncated, or emptied. A pointer file declares which is
authoritative; never imply it by recency or timestamp.

```
ai_context/spec/program_components.json        <- original, untouched
ai_context/spec/program_components.2.json     <- the change
```

## 4. File ownership is absolute

Each agent owns a disjoint set of paths. **Do not write a file you do not own**,
even to fix something that looks like a one-liner. If another agent's file looks
wrong, report it; do not correct it. Cross-agent findings go in your report.

Always stage with an **explicit pathspec**. `git add -A` will sweep another
agent's half-finished work into your commit.

```powershell
git add -- tools/pipmon.ps1 tools/agent_watchdog.ps1    # correct
git add -A                                             # NEVER - collides
```

Commit subject prefix, so the history stays attributable:

```
A1: <task> - <what changed>
A2: <task> - <what changed>
A3: <task> - <what changed>
```

## 5. Verify before you report, not after

Minimum bar for a task to be called done:

1. **It parses.** PowerShell: `[System.Management.Automation.Language.Parser]::ParseFile`.
   Python: `python -m py_compile`. JSON: `ConvertFrom-Json`.
2. **The project's gates still pass.** At minimum:
   ```
   python tools\spec_lint.py
   python tools\surfaces_gate.py
   python tools\changelog_gate.py
   ```
3. **You ran it at least twice** — once to observe the behaviour before the
   change, once after. For a defect, the before-run is what proves the defect
   existed. Record both numbers.
4. **The gates you were asked to write actually discriminate.** Mask or break the
   thing they check and confirm they go RED. A gate that cannot fail is
   decoration — `ai_context/spec/schema.json` line 187 already says this about
   status vocabularies, and it applies to gates too.

## 6. Do not guess

- **Refuse rather than infer.** A tool that declines is more useful than one that
  invents a value it did not read.
- **Never invent a status, a schema field, or a vocabulary value.** The exit-code
  vocabulary is closed. `ATTENTION` is emitted but undefined and its meaning is
  **the owner's decision, still owed** (F2.1b). If your task seems to need a new
  state, put the evidence in `data` instead and report that you wanted a state.
- If a task turns out to be blocked, **stop that task**, note it in your report
  with the evidence, and move to the next one. A blocked task reported honestly
  is worth more than a guessed fix.
- Do not add a dependency. No new npm, pip, or nuget package.

## 7. What you may not touch at all

Outside your ownership, and not to be corrected even if wrong:

| path | why |
|---|---|
| `tasks/roadmap/CHANGELOG.md` | shared index, written by the coordinator after your commits land |
| `tasks/roadmap/families/**` | the same |
| `tools/changelog_gate.py` | the coordinator's gate |
| `ai_context/spec/legacy_replacement.json` | the replacement map, `spec_id` referenced by others |
| `ai_context/spec/schema.json` | read it; do not edit it |
| `build_all.bat` | the build gate |

## 8. Hard limits

- **Launch no third-party process.** No `xFOEdit64`, `CreationKit.exe`,
  `Fallout4.exe`, `PapyrusCompiler.exe`. No `build_all.bat`.
- **Write nothing outside the project.** Not `%LOCALAPPDATA%`, not `%APPDATA%`,
  not `%TEMP%`, not the game install. Reading outside is fine — the CK and game
  data are read-only sources.
- **Nothing longer than ~60 seconds.** If a verification would take longer,
  report that and move on.
- `tools\pipmon.ps1 validate` blocks for up to 420 s. `verify` re-runs the whole
  build. **Do not run either.**

## 9. The standing rules of this project

- **SKIP is never PASS.** A check that could not run is reported as unverified,
  never as fine. Collapsing the two is how a workspace starts lying.
- **A fact with no provenance may not exist.** Every claim names its file or run.
- **Refuse rather than guess.**
- **Green gates are not goal alignment.** The build gate proves build integrity.
  A fully green gate is consistent with S0 unproven, the facility plugin holding
  0 records, and no vtable slot hooked.
- **Never build on F4SE, never rely on it, never suggest it.**
  `ai_context/f4se_prohibition.md` is `ACTIVE — BINDING CONSTRAINT`.

## 10. Your report

Return, in this order:

1. **Committed** — sha and one line each.
2. **Verified** — the actual numbers, including the before/after pair for every
   defect.
3. **NOT verified** — everything you could not prove, and why.
4. **Blocked** — tasks you stopped, with the evidence that stopped you.
5. **Cross-agent observations** — problems you saw in files you do not own.
   Do not fix them.
6. **Worth doing next** — in your area, in order.

If you could not finish everything, that is a fine outcome. An honest partial
with evidence is worth more than a complete-looking report with a guess in it.
