---
source_url: (authored record of this retrieval session)
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: index-authored
trust: "Authored by me. This is a factual log of which URLs were attempted for this directory, with verbatim error strings as returned. Nothing here is inferred."
provenance: "Direct HTTP fetches via PowerShell Invoke-WebRequest and the GitHub REST API (api.github.com), plus websearch to locate candidate URLs. No URL was guessed: every path used was either returned by the GitHub API tree listing or quoted verbatim from a source file."
---

# Fetch log — address_mapping

## The requested target does not exist

`https://github.com/libxse/addresslib` — **HTTP 404**.

Verified as absent rather than merely unreachable: the GitHub API listing for the
`libxse` user returned 12 public repositories, and **none of them is named
`addresslib`**:

```
commonlib-shared, commonlibf4, commonlibf4-template, commonlibf4-tools,
commonlibob64, commonlibob64-template, commonlibsf, commonlibsf-template,
commonlibsse, commonlibsse-ng-template, commonlibsse-template, xse-xmake-repo
```

Consequently there is **no README, no docs, and no `addresslib.json`** to
retrieve from that repository, because the repository does not exist. No
`addresslib.json` was found in any other public repository either.

## Substitution made, and why

Substituted `https://github.com/icodei/f4se-code` (branch `main`), located via
websearch. It ships both halves of the pipeline the task described:

- `AddressLibGen/` — the build step that derives an address blob from a
  version-keyed database
- `AddressLibDecoder/` — a consumer that parses that blob

This is a **third-party fork of the F4SE codebase**, used as a worked example
only. It is not F4SE source, not vendored, and not a dependency. The framing is
recorded in `addresslib-schema.md` so a later session cannot mistake it for an
adopted dependency.

## URLs attempted

| URL | Result | Bytes | Source |
|---|---|---|---|
| `https://github.com/libxse/addresslib` | **FAIL 404** | — | requested target; does not exist |
| `https://api.github.com/users/libxse/repos?per_page=100` | OK | — | GitHub API; used to prove absence |
| `https://api.github.com/repos/libxse/commonlibf4/git/trees/main` | OK | — | GitHub API; checked for an address-library path |
| `https://api.github.com/repos/icodei/f4se-code/git/trees/main?recursive=1` | OK | — | GitHub API; discovered `AddressLib*` paths |
| `.../AddressLibGen/README.md` | OK | 146 | raw.githubusercontent.com |
| `.../AddressLibGen/src/main.cpp` | OK | 7488 | raw.githubusercontent.com |
| `.../AddressLibGen/CMakeLists.txt` | OK | 308 | raw.githubusercontent.com |
| `.../AddressLibDecoder/README.md` | OK | 113 | raw.githubusercontent.com |
| `.../AddressLibDecoder/src/main.cpp` | OK | 1569 | raw.githubusercontent.com |
| `.../AddressLibDecoder/CMakeLists.txt` | OK | 287 | raw.githubusercontent.com |
| `.../AddressLibGen/mappings/dummy` | **not fetched** | — | 0-byte placeholder; no content exists |

All `...` = `https://raw.githubusercontent.com/icodei/f4se-code/main`

## Gaps left open (not filled with invention)

- **Runtime lookup routine: not obtained.** The ID→address resolution used at
  load time lives in F4SE/CommonLibF4, not in the two tools captured here. The
  blob is written id-sorted, which *implies* an indexed lookup, but no source in
  this directory documents the actual search. Recorded as
  `not found in sources` in `addresslib-schema.md`.
- **The 18 header lines per mapping file: undocumented.** The generator reads and
  discards exactly 18 lines without interpreting them. Their content is unknown.
- **`libxse/commonlibf4` contains no address-library code path.** The recursive
  tree listing returned nothing matching `address|version-|REL` except unrelated
  `BGSPreloadable` / `RelativeMarkerHeight` / `hkRelArray` headers. The runtime
  loader was not found there either.
