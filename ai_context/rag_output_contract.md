---
title: RAG output contract
purpose: >
  Exact input and output formats of the local retrieval surface, so a program or
  agent can drive it without reading tools/rag_query.py. Read this before
  parsing rag output or writing a query.
applies_to: tools/rag_index.py, tools/rag_query.py, tools/pipmon.ps1 (rag verb)
vocabulary_source: ai_context/vocabulary.json
scope: meta
authority: measured
trust: verified by the test battery on 2026-09-30. Formats are stable; the index contents are not.
---

# Retrieval contract

## 1. Commands

```powershell
tools\pipmon.ps1 rag index                                   # rebuild
tools\pipmon.ps1 rag stats                                   # shape of the index
tools\pipmon.ps1 rag vocabulary [-Format json]               # the words this index knows
tools\pipmon.ps1 rag query -Query "<terms>" [-Kind <k>] [-Limit <n>]
                                  [-MaxLines <n>] [-Page <n>] [-Format <fmt>]
```

The Python tools take the same flags directly and are what the surface calls.

| Flag | Default | Meaning |
| --- | --- | --- |
| `-Query` | required | Free text. Not a query language. |
| `-Kind` | all | `archive` `doc` `code` `tool` `state` `log` `run` `text` |
| `-Limit` | 5 | Maximum hits. Also the main driver of total output size. |
| `-MaxLines` | 0 | Cap body lines per hit. 0 = whole chunk. |
| `-Page` | 1 | 1-based page, only meaningful with `-MaxLines`. |
| `-Format` | `dense` | `dense` `tsv` `paths` `json` |
| `--no-expand` | off | Skip vocabulary expansion. |
| `--explain` | off | Print the full weight breakdown per hit. |
| `--no-weights` | off | Score on BM25 alone, ignoring `ranking.json`. For A/B. |

## 1b. Ranking is weighted, and auditable

Scores are **not** raw BM25. `ai_context/ranking.json` multiplies each hit by an
authority tier, a curated boost, an objective multiplier, a constraint bonus and
a staleness penalty. `--explain` prints every factor by name:

```
w=authority[compile-verified]=2.600 curated=1.350 objective[papyrus-correctness]=1.250 constraint=1.300
```

`--no-weights` disables all of it, which is how the model's effect is kept
visible and arguable rather than becoming an unexamined default. Scores are
comparable within a query, never across queries. Full rationale:
`ai_context/ranking_model.md`.

## 2. Query expansion is on by default

A query is expanded across `ai_context/vocabulary.json`: if any surface form of
a concept group appears, every form in that group is added. Expansion is
symmetric, because which form a given file happens to use is not something the
caller can know.

Measured effect on `make the papyrus event fire`:

| | score | matched terms |
| --- | --- | --- |
| `--no-expand` | 13.7 | 3 |
| default | 72.6 | 10 |

Expansion is reported in the hit header as `x=N[...]`, so a hit that only
matched because of expansion is visible rather than mysterious. Use
`--no-expand` when diagnosing why something did or did not match.

**To add words, edit `ai_context/vocabulary.json`, not the code.** Only add
forms that actually occur in an indexed file; a synonym present nowhere in the
corpus cannot help recall and only dilutes precision.

## 3. `dense` format (default)

One header line per hit, then one `lineno|text` line per body line.

```
1 score=11.893 ai_context/fo4_records_guide.md L90-122/32 kind=doc sha=af5e865a24ac9982 mtime=2026-09-30T15:55 m=addnewfilename page=1/6 win=12-17 roll=+0
 101|some source line
 102*|**AddNewFileName**
```

| Field | Meaning |
| --- | --- |
| `score` | BM25, boosted 1.35x for curated sources. Not comparable across queries. |
| `path` | Repo-relative. |
| `L<start>-<end>/<total>` | Line range within the chunk, and chunk length. |
| `kind` | Source class, see `-Kind`. |
| `sha` | First 16 hex of SHA-256 of the file. Verify with the file's mtime. |
| `mtime` | File modification time, local, minute precision. |
| `m=` | Comma-separated query terms present in this chunk. |
| `page=P/T` | Present only when capped. `T` is total pages for that chunk. |
| `win=a-b` | Body lines actually shown, chunk-relative. |
| `roll=+N` | Line delta applied after paging. |
| `x=N[...]` | Terms added by vocabulary expansion. Absent when nothing was added. |

`*` in the first column marks a line containing a query term. A hit with no `*`
anywhere is a ranking artefact, not evidence.

Trailing line: `hits=N chunks=N`. `chunks` is the searched space after
filtering, not the whole index.

**No match** prints `no chunk matched <terms>` and exits 0. This is not an
error; an empty result and a failed run are different facts.

## 4. `tsv` format

Metadata rows only, no body. Nine tab-separated fields, no quoting, so it pipes
straight into anything that reads TSV.

```
rank  score  path  Lstart-end  chunkLines  kind  sha  matchedTerms
```

Use when scanning many hits and only needing to know which files matter.

## 5. `paths` format

```
rank  score  path  Lstart-end
```

The cheapest possible discovery call: "which files are about this?"

## 6. `json` format

Array of objects, `--json` or `-Format json`:

```json
[{ "score": 11.893, "path": "...", "chunk": 0, "lines": [90, 122],
   "kind": "doc", "sha": "...", "indexed": "2026-09-30", "text": "..." }]
```

`text` is the **whole chunk**, regardless of `-MaxLines`. JSON is the format to
use when a program needs the complete evidence rather than a window.

## 7. Chunk size, and why output gets large

Chunks are capped at roughly 1400 characters, so **one chunk cannot reach
hundreds of lines**:

```
chunk_lines p50=21 p90=46 p99=65 max=118
```

Large output comes from **hit count**: `--limit 10` with whole chunks is ~330
lines. Bound it with `-MaxLines`. To page a long chunk, set `-MaxLines N` and
step `-Page`; the header reports `page=P/T` so the range is never a guess.
Out-of-range pages clamp rather than error. `--page` without `-MaxLines` is
ignored and says so.

## 8. The surface envelope

Every `tools\pipmon.ps1 rag` command returns the standard envelope:

```json
{ "schema": "pipmon.surface/1", "command": "rag", "status": "GREEN",
  "ok": true, "reason": null, "data": { "query": "...", "limit": 5,
  "maxLines": 0, "page": 1, "format": "dense", "exit": 0, "hits": ["..."] },
  "provenance": { "script": "tools/pipmon.ps1", "generatedUtc": "..." } }
```

`hits` is an array of output lines as strings, so the surface is lossless
regardless of which format was requested. Exit codes are the surface's standard
vocabulary: 0 GREEN, 1 RED, 2 BROKEN, 3 SKIP, 4 usage.

## 9. A retrieval program should do this

1. Call `rag vocabulary` once at startup. Do not hardcode the project's words.
2. Query with the user's own phrasing and let expansion handle synonyms.
3. Read `dense` when a human will look at it, `json` when the program needs
   complete evidence, `paths` when only file discovery matters.
4. Page with `-MaxLines`/`-Page` rather than re-querying with rephrased terms.
5. Treat `x=` in a header as "this matched partly because of expansion" and
   verify against the file when the claim matters.
6. Check `sha` and `mtime` before repeating a claim. The index is a cache; the
   file is the fact.
