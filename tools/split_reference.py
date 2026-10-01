"""Split the generated Papyrus reference into parts the retrieval index can hold.

WHY
    The reference is ~6.9 MB, one markdown file. tools/rag_index.py caps a file at
    MAX_BYTES (1,500,000) and drops anything larger, so the whole table was absent
    from the index -- and until this existed the drop was silent, reporting
    "indexed 24 unchanged 738" with every number true and no hint that the
    largest and most useful artefact in the corpus was missing.

    Raising the cap was rejected for two reasons. It changes indexing behaviour
    for every file in the project to accommodate one. And a single 135,000-line
    file chunks into arbitrary fragments: a query for a function name returns a
    slice of a wall with no indication which script it came from.

    Splitting on script boundaries fixes the second problem as well as the first.
    A part starts at a `### <ScriptName>` heading, so every chunk carries its own
    subject, and the path tells you which part to open. The preamble is repeated
    in each part, because a part without it is a table of unknown provenance.

    Idempotent: it rewrites its own outputs and removes stale parts, so a
    regenerated reference does not leave last run's part 07 behind.

    python tools/split_reference.py
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "ai_context" / "engine" / "papyrus_surface" / "FO4_Papyrus_Reference.md"
OUT_DIR = SRC.parent
# Stay under rag_index.MAX_BYTES with room for the repeated preamble.
LIMIT = 1_200_000


def main():
    if not SRC.exists():
        print("nothing to split: %s does not exist" % SRC, file=sys.stderr)
        return 3

    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines()

    # The preamble is everything up to the first script heading. It carries the
    # layer tables, the parser self-check and the call forms -- the parts that
    # explain what the numbers mean, which a bare table does not.
    first = next((i for i, l in enumerate(lines) if l.startswith("### ")), len(lines))
    preamble = lines[:first]
    body = lines[first:]

    # Split points: every `### Name` heading starts a new part.
    parts, cur, size = [], [], 0
    pre_bytes = len("\n".join(preamble)) + 200
    for line in body:
        b = len(line) + 1
        if line.startswith("### ") and cur and (size + b + pre_bytes) > LIMIT:
            parts.append(cur)
            cur, size = [], 0
        cur.append(line)
        size += b
    if cur:
        parts.append(cur)

    # Clear stale parts from a previous, longer run before writing.
    for old in OUT_DIR.glob("FO4_Papyrus_Reference.part*.md"):
        old.unlink()

    written = []
    for i, chunk in enumerate(parts, 1):
        p = OUT_DIR / ("FO4_Papyrus_Reference.part%02d.md" % i)
        head = list(preamble)
        head[0] = "# Fallout 4 Papyrus Reference -- part %d of %d" % (i, len(parts))
        head.insert(1, "")
        head.insert(2, "> Split from `FO4_Papyrus_Reference.md` by `tools/split_reference.py` because")
        head.insert(3, "> the whole table exceeds the retrieval index's per-file cap. Scripts in this")
        head.insert(4, "> part run from `%s` to `%s`." % (
            chunk[0].lstrip("# ").strip() if chunk else "?",
            next((c for c in reversed(chunk) if c.strip()), "?").strip()))
        p.write_text("\n".join(head + chunk) + "\n", encoding="utf-8")
        written.append((p.name, p.stat().st_size))

    over = [n for n, s in written if s > 1_500_000]
    print("split %s into %d part(s) of %d bytes avg" % (SRC.name, len(written),
                                                        sum(s for _, s in written) // max(1, len(written))))
    for n, s in written:
        print("   %-42s %9d B%s" % (n, s, "  OVER CAP" if s > 1_500_000 else ""))
    if over:
        print("FAILED: %d part(s) still exceed the index cap" % len(over), file=sys.stderr)
        return 1

    # Remove the monolith. It is a build intermediate that the generator writes
    # and this script consumes; leaving it in the corpus means every index run
    # reports one permanently-absent file, and a RAG that names something it
    # cannot hold is a RAG misrepresenting its own coverage. The parts ARE the
    # reference -- split_reference.py is part of the generate step, not an
    # occasional repair.
    SRC.unlink()
    print("removed the %d B monolith; the %d parts are the reference" % (len(text), len(written)))
    print("every part is under rag_index.MAX_BYTES; re-run rag_index.py to pick them up")
    return 0


if __name__ == "__main__":
    sys.exit(main())
