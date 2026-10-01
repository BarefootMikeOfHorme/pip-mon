"""Extract the xEdit scripting API from the shipped declaration into a reference.

WHY THIS EXISTS
    third_party/xedit/Edit Scripts/xEditAPI.pas is 67,829 bytes of xEdit's own
    Pascal declaration. It is the authority for what the scripting host
    exposes. It was sitting in the workspace indexed as one opaque blob of
    "code", which means retrieval could find a fragment but could not answer
    "does this function exist and what are its arguments".

    That cost real time. Four separate calls were guessed wrong -- ElementID,
    IwbGroupRecord.Count, GetPluginName, and the FileWriteToStream arity --
    each time because the answer was in this file and was not consulted. So the
    declaration is parsed into a table, and the table is what gets read.

    A NOTE ON TRUST, because it matters and is easy to get backwards:
    this file is xEdit's declaration, not a measurement. Where the declaration
    and a shipped working script disagree, the WORKING SCRIPT is right and the
    declaration is stale. FileWriteToStream is exactly that case: declared with
    two parameters at xEditAPI.pas:334, called with three at SaveAs.pas:63, and
    passing two raises [EJvInterpreterError] Not enough parameters. So the
    reference records both and flags the conflict rather than picking a winner.

WHAT IT EMITS
    ai_context/reference/xedit_pascal_api.md -- grouped by unit/interface, with
    each entry's kind (function / procedure / property / type / constant), its
    declaration, and any doc comment shipped with it.

    ai_context/reference/xedit_pascal_api.json -- the same data structured, for
    anything that wants to query it rather than read it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "third_party" / "xedit" / "Edit Scripts" / "xEditAPI.pas"
OUT_MD = REPO / "ai_context" / "reference" / "xedit_pascal_api.md"
OUT_JSON = REPO / "ai_context" / "reference" / "xedit_pascal_api.json"

# A declaration we care about. xEditAPI.pas is a real Delphi unit, so this
# matches the shape rather than trying to parse Delphi properly -- a full parser
# would be more code than the thing it parses, and this only has to be right
# about lines that declare a name this project might call.
DECL = re.compile(
    r"^\s*(?P<kind>function|procedure|property)\s+"
    r"(?P<name>[A-Za-z_]\w*)"
    r"(?P<rest>.*)$"
)
CLASSY = re.compile(r"^\s*(?P<kind>function|procedure|property)\s+"
                   r"(?P<name>[A-Za-z_]\w*)\s*\.\s*(?P<owner>[A-Za-z_]\w*)")
# xEditAPI.pas declares every interface as a flat alias of IInterface --
# "IwbElement = IInterface;" -- with no nesting and no parent links. So the
# declaration file alone cannot tell you that IwbMainRecord is not an IwbElement,
# which is precisely the distinction that made FixedFormID(newElem) return a null
# instead of raising. The hierarchy has to come from the Tome; see HIERARCHY.
TYPEDECL = re.compile(r"^\s*(?:type\s+)?(?P<name>[A-Za-z_]\w*)\s*=\s*"
                     r"(?P<body>IInterface|interface|class|record|set of|array of|\()")
CONST = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<body>[^;]+);")


def strip_comments(block: str) -> str:
    """Doc comments shipped above a declaration are evidence, so keep them."""
    out = []
    for raw in block.splitlines():
        s = raw.strip()
        if s.startswith("///") or s.startswith("//") or s.startswith("(*"):
            out.append(s.lstrip("/ ").rstrip("*").strip())
    return " ".join(x for x in out if x)


def main() -> int:
    if not SRC.exists():
        print(f"FAIL: declaration not found at {SRC}")
        return 1
    lines = SRC.read_text(encoding="utf-8", errors="replace").splitlines()

    entries: list[dict] = []
    pending_doc: list[str] = []
    scope = "(unsectioned)"

    # Scope comes from the banner comments, which is how the declaration is
    # actually organised:
    #     // ****************************************************
    #     // IwbFile Functions
    #     // ****************************************************
    # A dotted "Owner.Name" form was assumed first and matched nothing, which
    # put all 359 declarations in one bucket. The methods are not dotted; the
    # file is sectioned, and the banner is the only thing that says which
    # interface a declaration belongs to.
    BANNER = re.compile(r"^\s*//\s*([A-Za-z]\w*(?: [A-Za-z]\w*)*)\s*$")

    for i, raw in enumerate(lines):
        s = raw.strip()
        if s.startswith("///") or s.startswith("//"):
            if s.startswith("///"):
                pending_doc.append(raw)
            else:
                b = BANNER.match(raw)
                if b and "*" not in raw:
                    scope = b.group(1)
            continue

        m = DECL.match(raw)
        if not m:
            if s and not s.startswith(("{", "}", "unit", "interface", "implementation", "end", "uses", "var", "const")):
                pending_doc = []
            continue
        name = m.group("name")
        kind = m.group("kind")
        rest = m.group("rest")

        decl = " ".join(x.strip() for x in [f"{kind} {name}", rest] if x.strip())
        decl = decl.rstrip(";").strip()
        if not decl or ("(" not in decl and kind == "function"):
            if not pending_doc:
                pending_doc = []
                continue

        entries.append({
            "name": name,
            "owner": scope,
            "kind": kind,
            "declaration": decl,
            "line": i + 1,
            "doc": strip_comments("\n".join(pending_doc)),
        })
        pending_doc = []

    # Types and constants get their own pass; they are what the host exposes as
    # vocabulary rather than as callable things.
    # Types and constants get their own pass; they are what the host exposes as
    # vocabulary rather than as callable things. The type HIERARCHY is the single
    # most useful thing in this file and it is not a declaration at all -- it is
    # the nesting of the interface names in the Tome of xEdit section 13.5. It is
    # transcribed from the documentation because xEditAPI.pas declares the types
    # flat, with no parent links.
    HIERARCHY = """
IwbContainerBase
  IwbContainer
    IwbDataContainer
      IwbFileHeader
      IwbRecord
        IwbGroupRecord
        IwbMainRecord
      IwbSubRecord
    IwbFile
IwbContainerElementRef
IwbResource
IwbResourceContainer
IwbBA2File
IwbBSAFile
IwbFolder
Unknown but used: TwbDefType, TwbElementState, TwbElementType
""".strip().splitlines()

    types: list[dict] = []
    consts: list[dict] = []
    for i, raw in enumerate(lines):
        s = raw.strip()
        t = TYPEDECL.match(raw)
        if t:
            types.append({"name": t.group("name"), "body": t.group("body"), "line": i + 1})
        c = CONST.match(raw)
        if c and not s.startswith("//"):
            consts.append({"name": c.group("name"), "value": c.group("body").strip(), "line": i + 1})

    by_owner: dict[str, list[dict]] = {}
    for e in entries:
        by_owner.setdefault(e["owner"] or "(global)", []).append(e)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "pipmon.xedit.pascal.api/1",
        "authority": "third_party/xedit/Edit Scripts/xEditAPI.pas -- xEdit's own Pascal declaration, shipped with the editor",
        "authority_is_a_declaration_not_a_measurement": True,
        "known_conflicts": [{
            "symbol": "FileWriteToStream",
            "declared": "procedure FileWriteToStream(aeFile: IwbFile; akOutStream: TStream);  -- xEditAPI.pas:334",
            "called_as": "FileWriteToStream(aFile, fs, aReset);  -- Edit Scripts/SaveAs.pas:63",
            "measured": "passing two arguments raises [EJvInterpreterError] Not enough parameters (2026-09-30 23:47)",
            "rule": "where the declaration and a shipped working script disagree, the working script is right and the declaration is stale",
        }],
        "counts": {
            "declarations": len(entries),
            "scopes": len(by_owner),
            "types": len(types),
            "constants": len(consts),
        },
        "type_hierarchy": [
            {"line": line, "depth": len(line) - len(line.lstrip()), "name": line.strip()}
            for line in HIERARCHY if line.strip() and not line.strip().startswith("Unknown")
        ],
        "hierarchy_source": "Tome of xEdit section 13.5. xEditAPI.pas declares the types flat with no parent links, so this is transcribed from the documentation and is the only place the nesting exists.",
        "declarations": entries,
        "types": types,
        "constants": consts,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    md: list[str] = []
    md.append("# xEdit Pascal scripting API")
    md.append("")
    md.append("Extracted from `third_party/xedit/Edit Scripts/xEditAPI.pas`, which is xEdit's own")
    md.append("declaration, shipped with the editor. Regenerate with `tools/extract_xedit_api.py`.")
    md.append("")
    md.append("## Trust")
    md.append("")
    md.append("**This is a declaration, not a measurement.** Where it disagrees with a shipped")
    md.append("working script, the script is right. Known case:")
    md.append("")
    md.append("| symbol | declared | called as | measured |")
    md.append("|---|---|---|---|")
    md.append("| `FileWriteToStream` | 2 params, `xEditAPI.pas:334` | 3 params, `SaveAs.pas:63` | 2 params raises `Not enough parameters` |")
    md.append("")
    md.append(f"Counts: **{len(entries)}** declarations across **{len(by_owner)}** scopes, "
              f"**{len(types)}** types, **{len(consts)}** constants.")
    md.append("")
    md.append("## Type hierarchy")
    md.append("")
    md.append("From the Tome of xEdit §13.5. `xEditAPI.pas` declares the types flat with no")
    md.append("parent links, so this nesting exists only in the documentation. It is the thing")
    md.append("worth having: `Add()` returns `IwbElement` while `FixedFormID()` requires")
    md.append("`IwbMainRecord`, and the hierarchy is why passing one to the other returns a null")
    md.append("instead of raising.")
    md.append("")
    md.append("```")
    for line in HIERARCHY:
        md.append(line)
    md.append("```")
    md.append("")
    md.append("## Before writing a call")
    md.append("")
    md.append("1. Look it up here. Not in a doc transcription, not from memory of another API.")
    md.append("2. If it is here, confirm against a shipped script in `Edit Scripts/` that calls it.")
    md.append("3. If the two disagree, trust the script and record the conflict.")
    md.append("")
    md.append("## Globals and types")
    md.append("")
    md.append("| kind | name | declaration |")
    md.append("|---|---|---|")
    for e in by_owner.get("(global)", []):
        md.append(f"| {e['kind']} | `{e['name']}` | `{e['declaration']}` |")
    md.append("")

    for owner in sorted(k for k in by_owner if k != "(global)"):
        md.append(f"## {owner}")
        md.append("")
        md.append("| kind | name | declaration |")
        md.append("|---|---|---|")
        for e in by_owner[owner]:
            md.append(f"| {e['kind']} | `{e['name']}` | `{e['declaration'].replace('|', chr(92) + '|')}` |")
        md.append("")

    if types:
        md.append("## Declared types")
        md.append("")
        for t in types:
            md.append(f"- `{t['name']}` = {t['body']}  (line {t['line']})")
        md.append("")

    if consts:
        md.append("## Constants")
        md.append("")
        for c in consts[:200]:
            md.append(f"- `{c['name']}` = {c['value']}  (line {c['line']})")
        md.append("")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"declarations : {len(entries)}  across {len(by_owner)} scopes")
    print(f"types        : {len(types)}")
    print(f"constants    : {len(consts)}")
    print(f"wrote        : {OUT_MD.relative_to(REPO)}  ({OUT_MD.stat().st_size} B)")
    print(f"wrote        : {OUT_JSON.relative_to(REPO)}  ({OUT_JSON.stat().st_size} B)")
    print()
    print("largest scopes:")
    for owner, es in sorted(by_owner.items(), key=lambda kv: -len(kv[1]))[:10]:
        print(f"  {len(es):4d}  {owner}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
