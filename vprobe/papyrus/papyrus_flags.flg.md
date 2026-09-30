# papyrus_flags.flg

User-defined Papyrus flags for the PIP-MON build. **The `.flg` itself must
contain nothing but bare flag names, one per line** — the FO4 compiler parses
it with an ANTLR grammar that rejects comments and punctuation, so a `;` line
produces a wall of "no viable alternative" errors. That is why the
explanation lives here instead of in the file.

## Why this file is needed

The game's own compile step (`Papyrus Compiler\ScriptCompile.bat`) invokes:

    PapyrusCompiler.exe %1 -f="Institute_Papyrus_Flags.flg" ...

but `Institute_Papyrus_Flags.flg` is **not shipped** with the installed
Creation Kit — only the compiler that consumes it is. Without a flags file,
compiling against the base game sources fails at `ScriptObject.psc` with
`Unknown user flag hidden`, because this compiler requires even the flags the
documentation lists as built-in to be declared before it will accept a script
using them.

## Where the list came from

Scanned the `ScriptName` lines of every `.psc` in
`Data\Scripts\Source` (installed by the Creation Kit) and collected the
non-builtin flags actually referenced:

- `hidden`, `quest`
- the JSkyLuaScript family: `jvalue`, `jstring`, `jmap`, `jlua`, `jintmap`,
  `jformmap`, `jformdb`, `jdb`, `jcontainers`, `jatomic`, `jarray`

Built-in flags (`native`, `const`, `betaonly`, `default`) are accepted by the
compiler without declaration, so they are not listed.

## Maintenance

If a future base script introduces a flag not listed here, the compiler names
it explicitly and adding one line to the `.flg` is the entire fix.
