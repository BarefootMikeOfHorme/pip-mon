# How changes are made here, and how they are undone

Owner instruction, 2026-10-03. This file is the rule; every commit message in
`tasks/roadmap/` cites it.

## The two change classes

Every edit is one of these. Nothing is a third kind.

### Class A — small repair

**Definition:** one or two lines inside a long snippet, where the surrounding
lines are correct and stay correct.

**Rule:** edit in place. Commit with a changelog line naming the file, the
line, what was wrong, and why the previous value was a lie.

**Why in place is safe here:** the rest of the snippet is unchanged, so the diff
is the whole story and `git diff` shows it without reading the file.

### Class B — substantive change

**Definition:** anything longer than a couple of lines, anything that replaces a
block, anything that adds a field or changes a shape, anything you could not
reconstruct from the diff alone.

**Rule:** the previous version stays on disk. The new one is a **new numbered
file**. The old file is not edited, not truncated, not deleted, and not emptied.
Its name keeps its original form so the history stays walkable.

Naming: `<name>.<n>.ext`, counting up. Never reuse a number. Never renumber.

```
ai_context/spec/program_components.json            <- original, untouched
ai_context/spec/program_components.2.json           <- adds `replaces` to 13 entries
ai_context/spec/program_components.3.json           <- later, unrelated
```

Which one is authoritative is **declared in a pointer file**, never implied by
recency or by a timestamp:

```json
{ "authoritative": "ai_context/spec/program_components.3.json",
  "supersedes":    ["ai_context/spec/program_components.json",
                    "ai_context/spec/program_components.2.json"],
  "note": "Superseded files are retained as history. Do not edit them." }
```

## Paths are never erased either

If a plan names a path that turns out to be wrong, the wrong path is **not
deleted**. It is marked superseded and the working path is recorded next to it.

This already has a precedent in the tree, kept from commit `1344d4d`:

| path | state |
|---|---|
| `testfacility/xedit/out/PipMonTestFacility.probe.esp` | superseded by `1a61a21`, retained as evidence |
| the testfacility plugin itself | the working path |

## What is never done

- No deletions. Not of files, not of lines, not of directories.
- No emptying a file to reuse its name.
- No wholesale replacement of a long snippet. Whole snippet in, whole snippet
  out, or a numbered variant.
- No force-push, no amend of a commit you can still see, no history rewrite.
- No push unless the owner asks. Commits are **local**.

## The commit cadence

Every task gets its own commit. Not every keystroke, not every file — every
**task**. A commit message states what is VERIFIED and what is NOT, because that
is the project's own standing rule and it is the only part of a message that
stays true six weeks later.

Every commit appends to [`CHANGELOG.md`](CHANGELOG.md). The changelog is the
human-walkable version of `git log`: what changed, which family, why, and what
it cost.

## How to walk it back

```powershell
git log --oneline -20                          # find the task
git show <sha>                                 # read what it claimed
git show <sha> --stat                          # what it touched
git diff <sha>^ <sha>                          # the actual change
git revert --no-commit <sha>                   # undo, stage it, inspect, then commit
```

`git revert`, never `git reset --hard`. A reset throws away the evidence of what
was tried; a revert keeps the attempt visible, which is the point of keeping the
superseded files.

### Revert newest-first, or expect a conflict

**This was measured, not assumed.** See `CHANGELOG.md` R4.

`git revert` in chronological order conflicts on any commit whose files a *later*
commit also touched — which is most of them, because later commits refine earlier
ones. Reverting the six commits of 2026-10-03 oldest-first:

| commit | oldest-first | newest-first |
|---|---|---|
| `9bfb5c5` schema | clean | clean |
| `e499138` the map | **CONFLICT** | clean |
| `ec6ff02` F1 plan | **CONFLICT** | clean |
| `c4eb641` F2 plan | **CONFLICT** | clean |
| `997e2cb` F2.0 + row 31 | clean | clean |
| `7d03986` changelog | clean | clean |

Newest-first, all six revert cleanly and land **bit-identical to `1344d4d`**.
Oldest-first, three conflict.

So: **unwind from the top.** To abandon one task in the middle, revert it and
everything above it, in reverse order.

### A clean revert is not always a safe revert

Also measured, and this one matters more. Reverting `9bfb5c5` **alone** — the
schema commit — while keeping the map:

```
revert 9bfb5c5 alone      : CLEAN
map still present         : True
map still USES the fields : True
schema still DECLARES them: False
spec_lint                 : 0 problems
```

A clean revert, a green lint, and the spec layer now **lies**: the map uses four
fields the schema no longer declares, and nothing notices. `spec_lint` never
read `entry_optional`, which is exactly why declaring those fields was inert —
and exactly why their removal is also unchecked.

**Rule: a revert that breaks a declaration needs the declaration's consumers
reverted with it.** The dependency is a logical one, not a textual one, so git
cannot see it. Until a lint enforces it, check it by hand after reverting a
schema or contract commit. Carried as a task in `F2-truth-honesty/PLAN.md`.

## What this buys

The owner asked for revertability "consistent with each improvement." That means
at every point, the question *what did this look like before, and why* has an
answer that does not depend on remembering. `git log -- tasks/roadmap/` plus
`CHANGELOG.md` is that answer.

## Where this is weakest

Known, named, not solved:

- A 20-commit run has no single index. `CHANGELOG.md` is the index; it is only
  as good as the discipline writing it.
- Superseded files accumulate. Nothing prunes them, deliberately, but the day
  there are forty the walk becomes hard. The pointer file is what keeps it
  navigable; a `superseded/` prefix would be the next step if it gets bad.
- `git revert` of a commit that touched a numbered variant leaves the variant
  orphaned rather than deleting it. That is intended — orphans are evidence —
  but it does mean file count grows faster than task count.
