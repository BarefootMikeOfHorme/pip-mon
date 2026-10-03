# Hard-coded paths and defaults — where to change them

Written 2026-10-01 because the values are scattered across `.bat`, `.ps1` and
`.py` with different defaults for the same thing, and a change to one does not
reach the others. That is the defect this file names; fixing it is a separate
piece of work (a single config resolver). Until then, **this is the map.**

Line numbers are as of the commit this was written against and will drift. The
literal text in the right-hand column is the reliable part — search for it.

**Amended 2026-10-03, because that reassurance was doing too much work.** On
re-verification, three rows cited a line whose file does not contain the literal
at all (`config.py`, `fix_papyrus_flags.py`, `selfalign.py` — see sections 1 and
4). So "search for the literal" was not a safe fallback for those rows: a reader
following this page's own advice would have searched, found nothing, and had no
way to tell a moved line from a removed hard-code. Every row now carries its own
verification state, and the three dead rows say so in place rather than being
deleted.

Every entry below was checked against the live machine on 2026-10-03. The five
values in the summary table all exist on disk.

## The five things that are hard-coded

| Thing | Value used on this machine | Where it is defined | Verified 2026-10-03 |
|---|---|---|---|
| Game install dir | `C:\Program Files (x86)\Steam\steamapps\common\Fallout 4` | see below | present on disk |
| Active plugin list | `%LOCALAPPDATA%\Fallout4\plugins.txt` | see below | present on disk |
| xEdit dir | `%LOCALAPPDATA%\Temp\opencode\xedit\x` | see below | present on disk |
| Papyrus compiler | `...\Fallout 4\Papyrus Compiler\PapyrusCompiler.exe` | see below | present on disk |
| Papyrus stage dir | `%TEMP%\pipmon_papyrus_stage` | see below | present on disk |

## 1. Game install dir — `Fallout 4`

| File | Line | Shape |
|---|---|---|
| `tools/linksync.ps1` | 49 | `[string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4'` |
| `tools/validate_plugin.ps1` | 52 | game dir default, plus the `Data\` join |
| `tools/ck_session.ps1` | 36 | `$GameDir`, used to verify every profile entry exists |
| `vprobe/papyrus/build_papyrus.bat` | 51 | `set FO4=C:\Program Files (x86)\Steam\steamapps\common\Fallout 4` |
| `overseer_cli/src/overseer_cli/config.py` | — | **no longer here.** See the note below; the row is kept, not deleted. |
| `overseer_cli/src/overseer_cli/envgate.py` | 67 | runtime default — `DEFAULT_GAME_DIR = Path(r"...Fallout 4")` |

Breaks on GOG, Microsoft Store, FO4VR, and any non-default Steam library.

**Two corrections, 2026-10-03.** `tools/linksync.ps1` was cited at line 55; the
parameter default is at **49**. Line 55 is `$SnapshotRoot = Join-Path $Repo
'runs\linksync'`, which has nothing to do with the game dir — so the old number
pointed a reader at the wrong line and the entry looked unverified.

`overseer_cli/src/overseer_cli/config.py` was cited at line 3 as "config
default". It no longer holds the game dir at all: a search of all 252 lines for
`Program Files (x86)\Steam\steamapps\common\Fallout 4` returns **zero matches**.
Line 3 is prose about Fallout 4 not parsing JSON natively. The row is left in
place because policy 2 forbids deleting a line, but it is no longer a place the
game dir is hard-coded, and a reader counting definition sites from this table
was counting one that does not exist.

## 2. Active plugin list — `plugins.txt`

| File | Line | Shape |
|---|---|---|
| `tools/linksync.ps1` | 54 | `$PluginTxt = Join-Path $env:LOCALAPPDATA 'Fallout4\plugins.txt'` |
| `tools/ck_session.ps1` | 42 | same expression |
**This one is the dangerous entry.** `linksync.ps1` takes a `-GameDir` parameter
and *still* ignores it for the plugin list — `$PluginTxt` is built from
`$env:LOCALAPPDATA` alone, before `-GameDir` is ever consulted. So there is no
way to point `linksync apply` at a test directory: it always writes the live
file. Verified 2026-10-01 while testing a non-ASCII round trip, where the only
way to exercise the real code path was to write to the live list and restore
afterwards.

Anything that wants to sandbox a load-order change must either override
`$env:LOCALAPPDATA` for the child process or this line has to change.

**Re-verified 2026-10-03, and it still holds.** `tools/linksync.ps1:54` builds
`$PluginTxt` from `$env:LOCALAPPDATA` alone, and `$GameDir` is referenced at
exactly two lines in the whole file: 49, its own default, and 107. Nothing
between the parameter block and the write consults it for the plugin list. This
is the one entry on this page that is a correctness problem rather than a
portability one, and it is unchanged.

## 3. xEdit dir — `opencode\xedit\x`

| File | Line | Shape |
|---|---|---|
| `tools/run_gen.ps1` | 50 | `[string]$XEditDir = "$env:LOCALAPPDATA\Temp\opencode\xedit\x"` |
| `tools/validate_plugin.ps1` | 53 | same default |
| `tools/generate_env.ps1` | 34 | same default |
| `tools/unblock_and_generate.ps1` | 38 | same default |

**CORRECTION, 2026-10-03 — the risk here was stated too strongly, and the
stronger version is more useful.** This page said a machine that loses the
directory "loses the editor with no code change". That is true of the four
configured paths and false of the pipeline, because **the editor is also
vendored in the repository**: `third_party/xedit/xFOEdit64.exe` and
`%LOCALAPPDATA%\Temp\opencode\xedit\x\xFOEdit64.exe` are byte-identical,
SHA256 `5A27B76D…85A94AF` on both, 36,535,296 bytes. So a `%TEMP%` clean breaks
every tool by default and silently — which is the real hazard, and it is
unchanged — but it does not destroy the editor.

What is still true, and still the reason this is the first entry to move:

  * Nothing in this repository provisions that directory. No `.bat`, `.ps1` or
    `.py` extracts anything into `%LOCALAPPDATA%\Temp\opencode\xedit\`, so there
    is no in-tree restore path. A user who never ran the manual unpack has no
    documented way to get it back.
  * The installer's own archive, `xEdit.7z` (31,345,110 B), sits **inside** that
    temp directory too, so `%TEMP%` holds both the unpacked tree and the only
    copy of the thing that unpacked it.

`%TEMP%` is periodically cleaned, and a temp directory holding a tool the entire
pipeline depends on is the shape of that problem. The original note ended "Belongs
in a tools directory"; that judgement is the owner's and is left standing, with
the finding above added rather than substituted for it.

The `tools/run_gen.ps1` row was cited as "37, 50". Line 50 is the parameter
default; line 37 is a comment about the timeout budget and never held the path.

## 4. Papyrus compiler

| File | Line | Shape |
|---|---|---|
| `vprobe/papyrus/build_papyrus.bat` | 52 | `set CC=%FO4%\Papyrus Compiler\PapyrusCompiler.exe` |
| `tools/fix_papyrus_flags.py` | — | **no longer here.** See the note below; the row is kept, not deleted. |
| `tools/selfalign.py` | — | **no longer here.** See the note below; the row is kept, not deleted. |
| `tools/watch_papyrus.ps1` | 85 | `$compiler = Join-Path $GameDir 'Papyrus Compiler\PapyrusCompiler.exe'` |
| `overseer_cli/src/overseer_cli/envgate.py` | 71, 701 | `COMPILER_REL` at 71; a second reference at 701 |

**The compiler lives at `<game>\Papyrus Compiler\PapyrusCompiler.exe`, at the
game root — not under `Data\`.** Verified 2026-10-01, and **re-verified
2026-10-03**: `Data\Papyrus Compiler\PapyrusCompiler.exe` does not exist on this
machine and `<game>\Papyrus Compiler\PapyrusCompiler.exe` does. Getting this
backwards produces "not found" for a compiler that is installed.

**Three corrections, 2026-10-03.** `tools/fix_papyrus_flags.py` was cited at
line 5 and `tools/selfalign.py` at lines 4 and 58, all three as "compiler path".
None of the three files contains the string `PapyrusCompiler.exe` or
`Papyrus Compiler` anywhere — 173 lines and 180 lines respectively, zero matches
each. The cited lines are prose about user flags. Both rows are left in place
because policy 2 forbids deleting a line; neither file is a place the compiler is
hard-coded, so counting definition sites from this table was counting two that do
not exist.

`overseer_cli/src/overseer_cli/envgate.py` was cited at "71, 706, 846". Line 71
is `COMPILER_REL` and is correct. The other reference is at **701**, not 706.
Line 846 is the string `"Papyrus compiler reachable"` — a check *name* in an
argument list, not a path, and never was one.

## 5. Papyrus stage dir

| File | Line | Shape |
|---|---|---|
| `vprobe/papyrus/build_papyrus.bat` | 53 | `set STAGE=%TEMP%\pipmon_papyrus_stage` |

Shared, persistent, and `del /q %STAGE%\*.pex` runs on every build, so two
concurrent builds (a manual one and an orchestrated one) race. A per-run
subdirectory or a lock file would fix it.

## Also worth knowing

- **The compiler cannot parse paths containing spaces.** Every invocation
  therefore uses a space-free staging directory and relative arguments. This is
  documented at the top of `build_papyrus.bat` and it is the reason the stage
  exists at all. Do not "simplify" it by using the real game path.
  *Re-verified 2026-10-03:* still stated at `build_papyrus.bat:8-14`, unchanged.
- **`orchestrate.py` splits commands with `cmd.split()`** (line **353**, was
  cited as 349), so no argument in a plan may contain a space. The repo path
  (`...\Pip-mon Script Management system`) and the game path both do. Plans
  naming either will fail at the first space.
  *2026-10-03: there are now four `cmd.split()` call sites, not one — 353, 380,
  435 and 441. Any of them will split on the same space.*
- **`linksync.ps1` reads and writes `plugins.txt` as UTF-8 without BOM** as of
  2026-10-01. It used to write ASCII, which turned any non-ASCII plugin name
  into `?`.
  *Re-verified 2026-10-03:* still true — the write side builds
  `System.Text.UTF8Encoding($false)` at line 183 and announces "UTF-8 without
  BOM" at 185; the read side is explicit at line 67; the old ASCII write survives
  only as a commented line at 165.

## Naming trap: five filename suffixes cost you every objective multiplier

Recorded 2026-10-03 because it is a live trap for anyone naming a document in
this repository, and nothing on this page said so.

`ai_context/ranking.json` carries an `auto_meta` rule. Any file whose name
**ends with** `_model.md`, `_contract.md`, `_alignment.md`, `_audit.md` or
`SKILL.md` is tagged `scope: meta` automatically. The indexer applies it at
`tools/rag_index.py:239` and retrieval applies it at `tools/rag_query.py`:

  * **Every objective multiplier is forfeited.** `rag_query.py:344` replaces the
    objective's multiplier with a flat `1.0` for a meta file. Discussing an
    objective is not advancing it.
  * **A 0.6 off-domain penalty is applied** (`rag_query.py:337`,
    `meta_scope.off_domain_penalty`) — unless the query itself is about
    retrieval.

Currently tagged, confirmed against `rag/index.sqlite3`:

| File |
|---|
| `ai_context/goal_alignment.md` |
| `ai_context/rag_output_contract.md` |
| `ai_context/ranking_model.md` |
| `.opencode/skills/pipmon-workspace/SKILL.md` |

Two things worth knowing before renaming anything. First, the rule is a
**suffix** match, so `docs/HARDCODED_PATHS.md` is unaffected — but so would be
`HARDCODED_PATHS_contract.md`, and the cost is invisible until a query misses.
Second, frontmatter wins: `rag_index.py:235` reads a `scope:` key from the first
60 lines and returns it before the filename rule is consulted, so a document that
declares `scope: <something else>` in frontmatter escapes the trap. That is a way
out, not a recommendation — hand-tagging is what `auto_meta` exists to stop
relying on, and `tools/rag_selftest.py` enforces that the four files above stay
tagged. `rag_selftest.py` currently passes 10 of 10.

## If you only change one thing

Change `%LOCALAPPDATA%`-based xEdit paths (section 3) out of `%TEMP%` first. That
is the one that fails silently and without a code change.

Still the right first move on 2026-10-03, and it is now cheaper than it looks:
section 3 records that `third_party/xedit/xFOEdit64.exe` is byte-identical to the
copy in `%TEMP%`, so the fix is pointing four `$XEditDir` defaults at a path the
repository already holds rather than relocating a 274 MB tool tree.
