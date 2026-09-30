---
source_url: https://github.com/TES5Edit/xEditScripts ; https://github.com/TES5Edit/mxpf ; https://github.com/Ez0n3/F4SE-Plugins ; https://github.com/reg2k/hudframework ; https://www.nexusmods.com/fallout4/articles/371
retrieved_utc: 2026-09-30T21:28:15Z
content_kind: index-authored
trust: This log is authored. Every success row below was hash-verified byte-identical to its upstream git blob. Failure rows record verbatim error text. No file in this retrieval was fabricated, reconstructed or substituted.
---

# Retrieval Log — Fallout 4 modding reference fetch

Date (UTC): 2026-09-30. Method: `git clone --depth 1` followed by
`git cat-file blob <sha>` redirection, then `git hash-object --no-filters`
verification of every saved file.

## Summary

| # | Target | Outcome |
|---|---|---|
| 1 | `TES5Edit/xEditScripts` | SUCCESS — real source, 12 `.pas` selected from 121 |
| 2 | `TES5Edit/mxpf` | SUCCESS — real source, 9 `.pas` (all of them) + docs |
| 3 | `Ez0n3/F4SE-Plugins` | SUCCESS — real source, full plugin template + Scaleform code |
| 4 | `reg2k/hudframework` | PARTIAL — repo retrieved, but contains **no source code** (README only) |
| — | `nexusmods.com/fallout4/articles/371` | FAILED — HTTP 403 |
| — | `nexusmods.com/fallout4/articles/372` | NOT ATTEMPTED — same host/domain returned 403 |
| — | `nexusmods.com/fallout4/mods/20309` | NOT ATTEMPTED — same host/domain returned 403 |

## Commits retrieved

| Repo | Branch | Commit | Date |
|---|---|---|---|
| TES5Edit/xEditScripts | master | `c93d6266059496e94eb20e7dcc0f14c122885943` | 2016-10-20 |
| TES5Edit/mxpf | master | `f63f9328c096ecd38c8cd37b24494405894a56d8` | 2019-01-16 |
| Ez0n3/F4SE-Plugins | main | `96f34d9499ff5f27887c22791823779fce507077` | 2025-08-20 |
| reg2k/hudframework | master | `dc608cddaf9ff7dbdff631e1c9dd1aa3fea485ba` | 2017-03-11 |

## Failure detail

**URL:** `https://www.nexusmods.com/fallout4/articles/371`
(HUDFramework "Widget Creation" walkthrough)
**Error, verbatim:** `StatusCode: non 2xx status code (403 GET https://www.nexusmods.com/fallout4/articles/371)`

Nexus Mods blocks automated retrieval with HTTP 403. No content from that page
was saved, paraphrased or reconstructed. The sibling article
`/fallout4/articles/372` and the mod page `/fallout4/mods/20309` were not
attempted after the 403, as the same block applies host-wide.

**Not a failure — an upstream absence:** `reg2k/hudframework` cloned cleanly
(commit `dc608cd`) but its `git ls-files` returns exactly one entry,
`README.md`. HUDFramework's implementation is closed-source and binary-distributed
on Nexus Mods. There is no widget source to fetch. See
`hudframework-and-scaleform.md`.

## URL discovery notes

Two corrections to the URLs in the brief, both confirmed to resolve:

* `https://github.com/TES5Edit/mxpf` — **correct**, the repo exists at that exact
  path (a mirror of `matortheeternal/mxpf`; same author, same
  `Edit Scripts/lib/mxpf.pas`). Used as given.
* HUDFramework — the brief said "likely under a community org"; the actual repo is
  `https://github.com/reg2k/hudframework` (registrator2000 / reg2k). Located via
  search, then verified with `git ls-remote` before cloning.

## Verification

Per saved file: upstream blob SHA obtained with `git rev-parse HEAD:<path>`,
contents written with `git cat-file blob <sha>` (byte-level redirect, bypassing
Git's checkout filters), then re-hashed with `git hash-object --no-filters`.
All 58 files matched. Byte sizes reported in the sibling index files are the
upstream blob sizes (LF line endings), not Windows-checkout sizes.

Total saved: 58 files, 0 retrieval failures, 0 hash mismatches, 0 substitutions.