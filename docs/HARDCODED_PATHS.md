# Hard-coded paths and defaults — where to change them

Written 2026-10-01 because the values are scattered across `.bat`, `.ps1` and
`.py` with different defaults for the same thing, and a change to one does not
reach the others. That is the defect this file names; fixing it is a separate
piece of work (a single config resolver). Until then, **this is the map.**

Line numbers are as of the commit this was written against and will drift. The
literal text in the right-hand column is the reliable part — search for it.

## The five things that are hard-coded

| Thing | Value used on this machine | Where it is defined |
|---|---|---|
| Game install dir | `C:\Program Files (x86)\Steam\steamapps\common\Fallout 4` | see below |
| Active plugin list | `%LOCALAPPDATA%\Fallout4\plugins.txt` | see below |
| xEdit dir | `%LOCALAPPDATA%\Temp\opencode\xedit\x` | see below |
| Papyrus compiler | `...\Fallout 4\Papyrus Compiler\PapyrusCompiler.exe` | see below |
| Papyrus stage dir | `%TEMP%\pipmon_papyrus_stage` | see below |

## 1. Game install dir — `Fallout 4`

| File | Line | Shape |
|---|---|---|
| `tools/linksync.ps1` | 55 | `[string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4'` |
| `tools/validate_plugin.ps1` | — | game dir default, plus the `Data\` join |
| `tools/ck_session.ps1` | — | `$GameDir`, used to verify every profile entry exists |
| `vprobe/papyrus/build_papyrus.bat` | 51 | `set FO4=C:\Program Files (x86)\Steam\steamapps\common\Fallout 4` |
| `overseer_cli/src/overseer_cli/config.py` | 3 | config default |
| `overseer_cli/src/overseer_cli/envgate.py` | 67 | runtime default |

Breaks on GOG, Microsoft Store, FO4VR, and any non-default Steam library.

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

## 3. xEdit dir — `opencode\xedit\x`

| File | Line | Shape |
|---|---|---|
| `tools/run_gen.ps1` | 37, 50 | `[string]$XEditDir = "$env:LOCALAPPDATA\Temp\opencode\xedit\x"` |
| `tools/validate_plugin.ps1` | 53 | same default |
| `tools/generate_env.ps1` | 34 | same default |
| `tools/unblock_and_generate.ps1` | 38 | same default |

A temp directory holding a tool the entire pipeline depends on. `%TEMP%` is
periodically cleaned, so a machine that loses it loses the editor with no code
change. Belongs in a tools directory.

## 4. Papyrus compiler

| File | Line | Shape |
|---|---|---|
| `vprobe/papyrus/build_papyrus.bat` | 52 | `set CC=%FO4%\Papyrus Compiler\PapyrusCompiler.exe` |
| `tools/fix_papyrus_flags.py` | 5 | compiler path |
| `tools/selfalign.py` | 4, 58 | compiler path |
| `tools/watch_papyrus.ps1` | 85 | compiler path |
| `overseer_cli/src/overseer_cli/envgate.py` | 71, 706, 846 | compiler path |

**The compiler lives at `<game>\Papyrus Compiler\PapyrusCompiler.exe`, at the
game root — not under `Data\`.** Verified 2026-10-01: `Data\Papyrus Compiler\`
does not exist on this machine and `<game>\Papyrus Compiler\` does. Getting this
backwards produces "not found" for a compiler that is installed.

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
- **`orchestrate.py` splits commands with `cmd.split()`** (line 349), so no
  argument in a plan may contain a space. The repo path
  (`...\Pip-mon Script Management system`) and the game path both do. Plans
  naming either will fail at the first space.
- **`linksync.ps1` reads and writes `plugins.txt` as UTF-8 without BOM** as of
  2026-10-01. It used to write ASCII, which turned any non-ASCII plugin name
  into `?`.

## If you only change one thing

Change `%LOCALAPPDATA%`-based xEdit paths (section 3) out of `%TEMP%` first. That
is the one that fails silently and without a code change.
