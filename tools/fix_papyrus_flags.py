#!/usr/bin/env python3
"""fix_papyrus_flags.py -- add the Papyrus user flags the COMPILER says are missing.

WHY THIS EXISTS
    The FO4 Papyrus compiler refuses a script that uses an undeclared user flag
    and names the offender: "Unknown user flag conditional". The flags file was
    previously maintained by hand from that message, which works but leaves the
    knowledge in someone's scrollback.

WHY IT IS DRIVEN BY THE COMPILER AND NOT BY SCANNING THE SOURCES
    A first attempt here derived the list by regex-scanning the CK's base
    scripts. It reported 2,737 undeclared "flags", essentially every variable in
    the base game, because `if <word>` and declaration lines cannot be told
    apart from Papyrus with a regex. Appending that would have been worse than
    useless.

    The compiler is the authority and it is exact: it prints every flag it
    could not resolve, and nothing else. This tool reads that list, appends only
    what is missing, and changes nothing else -- existing Flag blocks and the
    comments explaining them are preserved verbatim.

THE LOOP
    compile -> read this tool's report -> compile again, until no unknown flags
    remain. Each pass adds only newly-named flags, so the loop converges.

FLAG SCOPE
    New flags are declared broadly (script, property, struct var, function,
    variable). The type block scopes where a flag may appear; declaring a flag
    more widely than strictly necessary is inert, while declaring it too
    narrowly fails the build. Narrowing can be done deliberately later with the
    compiler as the check.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

UNKNOWN_FLAG = re.compile(r"Unknown user flag ([A-Za-z_]\w*)")
NOT_ALLOWED = re.compile(r"Flag ([A-Za-z_]\w*) is not allowed on ([A-Za-z_]\w*)")
DECLARED = re.compile(r"^\s*Flag\s+(\w+)\s+(\d+)", re.IGNORECASE | re.MULTILINE)

# The scope tokens the compiler accepts inside a Flag block. Papyrus allows a
# flag on a group or an else-block as well as on a declaration, and a flag
# declared without the scope it is actually used in is rejected with "Flag X is
# not allowed on Y" -- a different message from the unknown-flag one, and just
# as fatal. Both are handled here.
FLAG_BLOCK = """// Added by tools/fix_papyrus_flags.py: the compiler reported this flag as
// undeclared while building against the CK's base scripts.
Flag {name} {index}
{{
Script
Property
StructVar
Function
Variable
Group
}}

"""


# The scope words the compiler uses in "Flag X is not allowed on Y", mapped to
# the tokens its flags grammar accepts. Measured from this compiler's own
# messages: it says "groups", the file needs "Group".
SCOPE_TOKENS = {
    "group": "Group",
    "groups": "Group",
    "script": "Script",
    "scripts": "Script",
    "property": "Property",
    "properties": "Property",
    "function": "Function",
    "functions": "Function",
    "variable": "Variable",
    "variables": "Variable",
    "structvar": "StructVar",
    "structvars": "StructVar",
    "elseblocks": "ElseBlock",
    "else block": "ElseBlock",
}


def widen_scope(flg: str, name: str, scope: str) -> str | None:
    """Add a scope token to an existing Flag block. Returns None if not found."""
    m = re.search(rf"(^\s*Flag\s+{re.escape(name)}\s+\d+\s*\n\s*\{{)(.*?)(^\s*\}})",
                  flg, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not m:
        return None
    body = m.group(2)
    if re.search(rf"^\s*{re.escape(scope)}\s*$", body, re.IGNORECASE | re.MULTILINE):
        return flg
    return flg[:m.end(2)] + f"\n{scope}\n" + flg[m.end(2):]


def decode(raw: bytes) -> str:
    # The compiler emits UTF-16LE on this install. Decoding it as UTF-8 yields
    # text with NULs between characters, which would defeat the regex.
    for enc in ("utf-16-le", "utf-8"):
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if UNKNOWN_FLAG.search(re.sub(r"\x00", "", text)):
            return text
    return raw.decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fix_papyrus_flags.py")
    ap.add_argument("--log", required=True, help="compiler output to read")
    ap.add_argument("--flags", required=True, help="the .flg to update")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    text = decode(Path(args.log).read_bytes())
    text = re.sub(r"\x00", "", text)
    missing_in_build = sorted({m.group(1) for m in UNKNOWN_FLAG.finditer(text)})
    scope_errors = sorted({(m.group(1), m.group(2))
                           for m in NOT_ALLOWED.finditer(text)})

    flags_path = Path(args.flags)
    flg = flags_path.read_text(encoding="utf-8")
    declared = {m.group(1).lower() for m in DECLARED.finditer(flg)}

    missing = [f for f in missing_in_build if f.lower() not in declared]

    changed = False
    for name, scope in scope_errors:
        token = SCOPE_TOKENS.get(scope.lower())
        if token is None:
            # The compiler names scopes in English plurals; the flags grammar
            # wants singular PascalCase tokens. Guessing the mapping produced a
            # literal "groups" line in the file that the compiler still rejected,
            # so unmapped scopes are reported rather than written.
            print(f"fix_papyrus_flags: no grammar token known for scope {scope!r} "
                  f"(flag {name}); not modifying the file")
            continue
        widened = widen_scope(flg, name, token)
        if widened is not None and widened != flg:
            print(f"fix_papyrus_flags: widened flag {name} to allow '{token}'")
            flg = widened
            changed = True

    if missing:
        index = max((int(m.group(2)) for m in DECLARED.finditer(flg)), default=-1) + 1
        for name in missing:
            flg += FLAG_BLOCK.format(name=name, index=index)
            index += 1
            changed = True
        print(f"fix_papyrus_flags: declared {len(missing)} new flag(s): "
              f"{', '.join(missing)}")

    if not changed:
        print("fix_papyrus_flags: nothing to add"
              + (f" (build mentioned: {', '.join(missing_in_build)})" if missing_in_build else ""))
        return 0

    if not flg.endswith("\n"):
        flg += "\n"
    flags_path.write_text(flg, encoding="utf-8")
    print(f"  wrote {flags_path}")
    # Distinct exit code so a caller can loop "compile -> fix -> compile" until
    # this reports 0. Sharing 0 with the nothing-to-do case is what made the
    # first version of that loop stop after a single pass.
    return 3


if __name__ == "__main__":
    raise SystemExit(main())

