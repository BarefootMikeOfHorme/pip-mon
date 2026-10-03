# Compendium build state, 2026-10-01

Where the RAG subjects stand, what is real, and what is a shell. Read this before
believing any subject file exists in a usable form.

**Rule for this repo: a file that says `STATUS: SKELETON — INERT` has had
nothing built. It contains research and open questions, not a build plan.** The
word INERT is the whole point. A skeleton is a placeholder that records what is
known so the next session does not re-derive it.

---

## 1. Subject registry

| Subject | File | State | What is actually true |
|---|---|---|---|
| spatial | `cre_spatial.md` | partial | unit scale + container model + precombine wall; **retracted** claim that unloaded = unreachable |
| weather | `cre_weather.md` | **SKELETON** | file surface named; no WTHR/CLMT read; visibility distance unmeasured |
| boundary | `cre_boundary.md` | **SKELETON** | 2 corrections + ranked options; nothing built |
| cotosbunker | `cotosbunker.md` | **SKELETON** | dependency + power chain + markers measured; cells not read |
| tparadise | `tparadise.md` | **SKELETON** | identity + header + unit correction measured; extent **unmeasured** |
| f4se | `f4se_prohibition.md` | **BINDING** | standing rule; base core currently violates it |
| layout | `testenv_layout.md` | researched | container model, fast-travel chain; not built |
| xedit | `xedit_command_reference.md` | good | plus `ai_context/reference/xedit_pascal_api.md` |
| ck | `ck_command_reference.md` | good | CK commands |
| papyrus | `engine/papyrus_surface/README.md` | good | the FO4 Papyrus reference |

**Four of six environment subjects are shells.** The two non-skeletons
(`testenv_layout.md`, `cre_spatial.md`) are research notes, not builds.

---

## 2. The corrections that matter most

These were found during this session and invalidate earlier plans. All are
written into the subject files, not just here.

1. **Unit scale is `1 unit = 1/64 yard = 1.42875 cm` (69.99125 u/m), CONFIRMED
   from the archived CK wiki `FT = Unit * 0.046875`.** The circulating
   `64 units = 1 m` is a units slip — 64 units is exactly **one yard**, and the
   author labelled the yard "metre." Error +9.36% on a cell. The earlier working
   value of 70 units/m is now *derived* rather than lucky.
   → `tparadise.md` §3, corrects `cre_spatial.md` §1.1.

2. **"No navmesh" does not stop the player.** It stops AI pathing only. The
   player, `MoveTo`, vehicles, jumping, and fast travel all ignore it. An earlier
   design used an unloaded, unnavmeshed ring as a boundary — **that does not
   work.**
   → `cre_boundary.md` §1, **retracts** the reachability claim in
   `cre_spatial.md` and `paradise_bubbles.svg`.

3. **DBLOCK could not be confirmed to exist** as a Creation Engine feature. No
   primary, reverse-engineering, or community source. It had been proposed as
   the fog-ring mechanism.
   → `cre_boundary.md` §2. Border regions and `xLODGen` are the real candidates.

4. **The base core loads three F4SE-dependent plugins with no F4SE installed**,
   and the validator would report green.
   → `f4se_prohibition.md` §3.

5. **`tools/esp_cells.py` cannot parse any FO4 plugin**, including
   `Fallout4.esm` and our own 66-byte `PipMonTestFacility.esp`. Cause partly
   diagnosed (6-byte subrecord header, not 8) but **the format is not solved** —
   a brute-force search over GRUP geometries found none that walks to EOF. A
   validator that cannot read the artifact cannot independently validate it.
   → `cotosbunker.md` §8.

---

## 3. The identity answer

"Paradise" = **`theparadiseproject.esp`**, 1,271,923 B, author `uituit`,
subtitle `V4`, entry 32 of 35 in `dplugins.txt`. It is a **loose file, not a
Vortex install** — 1 hard link, no reparse point, no mention in Vortex's
71-mod list or its state database.

Both subject mods (this and Coto's Bunker) sit outside Vortex's management.
Practical effect: Vortex cannot detect conflicts between them and anything it
does manage, and a future deploy can change what they override without Vortex
knowing.

---

## 4. Not built, in one list

So it is unambiguous:

- no test cell, no worldspace, no interior — nothing exists in the CK
- no weather file authored; no `.wthr`, `.clmt`, or weather `.esl`
- no boundary of any kind constructed or tested in game
- no CELL record persisted to disk; `PipMonTestFacility.esp` is 66 bytes
- no staging→promote cycle run end to end
- no fast-travel chain, no NPC cohort, no blueprint, no template
- `ck-rig` is mid-refactor, unversioned, and not safe to execute
- `paradise_bubbles.svg` validates as XML but **has not been rendered in a
  browser**, and uses literal arithmetic in SVG numeric attributes
- Wrye: not adopted, deliberately
- BodySlide: recommended, not installed

---

## 5. Open questions, ranked

1. **Is `theparadiseproject.esp` even the right subject?** The owner's
   description — 100 m diameter, fog rolling in, a wall of no-going — has not
   been matched to this mod's contents, because our reader cannot parse it.
   **Confirm before building anything.**
2. **Playable diameter: 100 m or something else?** The owner's 100 m is better
   than the earlier 4096-unit-radius proposal (117 m) and should replace it.
   Vertibird math makes this tight: 12–15 m span, ~30 m pad, ~60 m approach, a
   **90 m envelope in a 100 m diameter.**
3. **How far does weather render beyond the resident grid?** Resident span at
   `uGridsToLoad=5` is 146.3 m per side. If particles clip there, a storm
   outside the area is never seen coming, and the intended effect is
   unachievable by fog. One cheap measurement decides it.
4. **GRUP layout.** Blocks independent validation. See item 2 in §2.
5. **Per-cell object budget.** Undocumented anywhere. Decides whether
   precombine can be skipped entirely, which would remove all 3×3 cluster
   complexity.

---

## 6. Next actions

In the order they unblock the most:

1. Fix `esp_cells.py` against a known-good file, then re-verify all four
   plugins. Unblocks: independent validation, Paradise's actual extent, and
   question 1.
2. Fix the base core's F4SE violation and add a gate for absent runtimes.
   Cheap, and currently the repo contradicts its own binding rule.
3. Rebuild the RAG index — it does not yet include the skeletons or
   `cre_spatial.md`'s corrections — and add subject-tag assertions, which
   currently have no known-answer test at all.
4. Measure unit scale in the CK with a known-length NIF, closing the
   "no primary FO4 source" gap on §2 item 1.
5. Only then build geometry, one module at a time, with the 3×3 previs cluster
   boundary respected.
