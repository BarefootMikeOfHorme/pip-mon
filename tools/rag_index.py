"""Local, provenance-carrying retrieval index for the PIP-MON workspace.

Standard library only: SQLite for storage, BM25 for retrieval, no network and no
embedding model. Every chunk keeps its source path, mtime, size and SHA-256, so
any hit can be traced back to the exact file and line range it came from.

    python tools/rag_index.py --rebuild
    python tools/rag_index.py
"""
import argparse
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "rag" / "index.sqlite3"

EXTS = {
    ".md", ".txt", ".json", ".pyr", ".ps1", ".py", ".pas", ".psc", ".ppc", ".cpp", ".c",
    ".h", ".hpp", ".ini", ".flg", ".csv", ".xml", ".yml", ".yaml", ".toml",
    ".log", ".bat", ".cfg", ".jsonl", ".def", ".sh",
}
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "target", "obj",
    "bin", "dist", "build", ".vs", ".idea", "Edit Scripts", "FO4Edit Backups",
    "FO4Edit Cache", "loaddata", "textures",
}
MAX_BYTES = 1_500_000
# Paths dropped for exceeding MAX_BYTES, reported at the end of the run rather than
# vanishing. See the note at the size check in walk().
OVERSIZE = []

# The address database exists in seven places on this tree (runs/*, stage/*,
# vprobe/libs/*). Indexing all of them produced 3,451 chunks that were 28% of
# the corpus and near-identical to each other, so a query about an address
# returned the same answer seven times. The DERIVED copies are excluded; the
# source of truth at vprobe/libs is kept. Same reasoning as .gitignore: a
# derived artefact must never be committable, and must never be retrievable
# either.
EXCLUDE_SUBPATHS = (
    "runs/", "stage/", "rag/",
    "inspiration archive/",
)

# Mis-decoded logs. Two Papyrus logs are UTF-16 being read as UTF-8, which
# yields three-character and empty chunks: not merely useless, but actively
# misleading, because an empty chunk looks like an authoritative absence.
MIN_MEANINGFUL_RATIO = 0.60
TARGET = 1400
OVERLAP = 200

# Configuration, not content. ai_context/vocabulary.json is a list of the exact
# words queries use, so indexing it makes it match every query and -- because it
# sits under ai_context/ -- earn the curated boost on top. It then outranked the
# files that actually answer the question. It stays readable through
# `rag vocabulary`; it just must never come back as a hit.
NOT_INDEXED = {"ai_context/vocabulary.json", "ai_context/ranking.json", "rag/index.sqlite3"}

CODE_EXTS = {".py", ".ps1", ".pas", ".psc", ".ppc", ".cpp", ".c", ".h", ".hpp", ".bat", ".sh"}


def load_ranking():
    p = REPO / "ai_context" / "ranking.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


RANKING = load_ranking()


def classify_authority(head, kind):
    """Decide how much a file's claims are worth, from what the file says about itself.

    Deliberately not a hand-maintained table: a table drifts, and a drifted table
    would quietly promote a stale or speculative file over a measured one, which
    is the exact failure this project treats as worst. An explicit
    `authority: <tier>` in the first lines always wins; otherwise the first
    matching keyword group decides, highest tier first.
    """
    low = head.lower()
    for tier in (RANKING.get("authority") or {}):
        if tier.startswith("_"):
            continue
        if ("authority: %s" % tier) in low:
            return tier
    for tier, kws in (RANKING.get("authority_keywords") or {}).items():
        if tier.startswith("_"):
            continue
        if any(kw in low for kw in kws):
            return tier
    return "derived"


def scope_for(rel: Path) -> str:
    """Whose world is this file in. third_party is reference material about the
    ENGINE, not about our program, and 458 files of it was crowding out the
    project's own surfaces. Ranking can now treat it as a different scope."""
    s = rel.as_posix().lower()
    if s.startswith("third_party/"):
        return "third_party"
    if s.startswith("ai_context/"):
        return "curated"
    if s.startswith("runs/"):
        return "evidence"
    return "project"


def kind_for(rel: Path) -> str:
    s = rel.as_posix().lower()
    if s.startswith("inspiration archive/"):
        return "archive"
    if s.startswith("runs/"):
        return "log" if rel.suffix.lower() == ".log" else "run"
    if s.startswith("tasks/") or rel.suffix.lower() == ".json":
        return "state"
    if s.startswith("docs/") or s.startswith("stage/notes/") or rel.name.endswith("HANDOVER.md"):
        return "doc"
    if s.startswith("tools/"):
        return "tool"
    if rel.suffix.lower() in CODE_EXTS:
        return "code"
    if rel.suffix.lower() == ".md":
        return "doc"
    return "text"


def sha_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def tokenize(s: str):
    out = []
    cur = []
    for ch in s.lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if len(cur) >= 2:
                out.append("".join(cur))
            cur = []
    if len(cur) >= 2:
        out.append("".join(cur))
    return out


def chunk_text(text: str):
    lines = text.splitlines()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        buf = []
        size = 0
        j = i
        while j < n and size < TARGET:
            ln = lines[j]
            if size and size + len(ln) + 1 > TARGET:
                break
            buf.append(ln)
            size += len(ln) + 1
            j += 1
        body = "\n".join(buf).strip()
        if body:
            out.append((i + 1, j, body))
        if j >= n:
            break
        back = j
        acc = 0
        while back > i + 1 and acc < OVERLAP:
            back -= 1
            acc += len(lines[back]) + 1
        i = back
    return out


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB))
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS files(
            path TEXT PRIMARY KEY, kind TEXT, size INTEGER, mtime REAL,
            sha TEXT, chunks INTEGER, indexed_utc TEXT, authority TEXT, scope TEXT);
        CREATE TABLE IF NOT EXISTS chunks(
            id INTEGER PRIMARY KEY, path TEXT, idx INTEGER,
            start_line INTEGER, end_line INTEGER, text TEXT);
        CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path);
        """
    )
    cols = {r[1] for r in con.execute("PRAGMA table_info(files)")}
    for col in ("authority", "scope"):
        if col not in cols:
            con.execute("ALTER TABLE files ADD COLUMN %s TEXT" % col)
    con.commit()
    return con


def classify_scope(head, rel=None):
    """`scope: meta` marks a file that documents the tooling rather than the domain.

    Needed because otherwise the ranking model's own explanation of the S0
    weight outranks the documents that actually explain S0. Discussing an
    objective is not advancing it, so a meta file keeps its authority tier but
    forfeits the objective multipliers and takes an off-domain penalty.

    Filename patterns apply automatically. Tagging by hand did not survive:
    vocabulary.json, ranking.json, ranking_model.md and goal_alignment.md each
    became the top hit for a domain question before this rule existed.
    """
    for line in head.splitlines()[:60]:
        if line.strip().lower().startswith("scope:"):
            return line.split(":", 1)[1].strip().lower() or None
    name = (rel.name if rel is not None else "").lower()
    for pat in (RANKING.get("auto_meta") or {}).get("patterns", []):
        if name.endswith(pat.lower()):
            return "meta"
    return None


def candidates():
    for p in REPO.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        rel = p.relative_to(REPO).as_posix()
        if rel in NOT_INDEXED:
            continue
        if any(rel.startswith(sp) for sp in EXCLUDE_SUBPATHS):
            continue
        if "addresses.txt" in rel and not rel.startswith("vprobe/libs/"):
            continue
        if p.suffix.lower() not in EXTS:
            continue
        if p.stat().st_size > MAX_BYTES:
            # RECORDED, not skipped in silence. This used to be a bare `continue`
            # with no print and no counter, so a 7 MB file was dropped and the
            # run still reported "indexed 24 unchanged 738" with every number
            # true. Nothing anywhere said the file was missing. A size cap that
            # does not announce itself is indistinguishable from a working
            # index, which is the failure this project treats as its worst.
            if (rel, p.stat().st_size) not in OVERSIZE:
                OVERSIZE.append((rel, p.stat().st_size))
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    con = connect()
    if args.rebuild:
        con.execute("DELETE FROM files")
        con.execute("DELETE FROM chunks")
        con.commit()

    now = time.time()
    known = {r[0]: (r[1], r[2]) for r in con.execute("SELECT path, sha, size FROM files")}

    indexed = skipped = removed = empty = 0
    for p in candidates():
        rel = p.relative_to(REPO)
        key = rel.as_posix()
        try:
            data = p.read_bytes()
        except OSError:
            continue
        digest = sha_of(data)
        size = len(data)
        if key in known and known[key][0] == digest and known[key][1] == size:
            skipped += 1
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            # Not UTF-8. Indexing the replacement characters produces chunks of
            # "���" that look like real content. Skip and say so.
            print("skipping (not utf-8): %s" % key)
            continue
        # A file that decodes but is mostly whitespace or one repeated
        # replacement glyph is not content. Detect rather than assume.
        sample = text[:4096]
        if sample:
            printable = sum(1 for c in sample if c.isprintable() or c in "\r\n\t")
            if printable / len(sample) < MIN_MEANINGFUL_RATIO:
                print("skipping (not meaningful text): %s" % key)
                continue
        pieces = chunk_text(text)
        con.execute("DELETE FROM chunks WHERE path = ?", (key,))
        for idx, (start, end, body) in enumerate(pieces):
            con.execute(
                "INSERT INTO chunks(path, idx, start_line, end_line, text) VALUES(?,?,?,?,?)",
                (key, idx, start, end, body),
            )
        head = "\n".join(text.splitlines()[:60])
        con.execute(
            "INSERT OR REPLACE INTO files(path, kind, size, mtime, sha, chunks, indexed_utc, authority, scope)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (key, kind_for(rel), size, p.stat().st_mtime, digest, len(pieces),
             time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
             classify_authority(head, kind_for(rel)), classify_scope(head, rel)),
        )
        indexed += 1
        if not pieces:
            empty += 1
        if not args.quiet and indexed % 25 == 0:
            print("indexed %d files" % indexed, flush=True)

    live = {p.relative_to(REPO).as_posix() for p in candidates()}
    for (key,) in con.execute("SELECT path FROM files").fetchall():
        if key not in live:
            con.execute("DELETE FROM files WHERE path = ?", (key,))
            con.execute("DELETE FROM chunks WHERE path = ?", (key,))
            removed += 1

    con.commit()
    total = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    files = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    con.close()
    print("db: %s" % DB)
    print("indexed %d  unchanged %d  removed %d  empty %d" % (indexed, skipped, removed, empty))
    if OVERSIZE:
        print("")
        print("NOT INDEXED -- %d file(s) exceed MAX_BYTES (%d B). They are absent from"
              % (len(OVERSIZE), MAX_BYTES))
        print("the index and a query will not find them. Split them, or raise the cap")
        print("deliberately -- do not leave this looking like a working index:")
        for rel, sz in sorted(OVERSIZE, key=lambda x: -x[1]):
            print("   %9d B  %s" % (sz, rel))
    print("totals: %d files, %d chunks" % (files, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())


