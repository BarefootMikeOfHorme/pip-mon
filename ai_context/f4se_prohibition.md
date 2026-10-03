---
title: F4SE prohibition — standing constraint
purpose: >
  The standing rule that this project must not build on or rely on F4SE, why it
  exists, and what to do instead. Read before suggesting any native plugin,
  extender, or SKSE-dependent mod. BINDING.
authority: measured
status: ACTIVE — BINDING CONSTRAINT
---

# F4SE prohibition

> **BINDING. This is not a preference or a soft preference to revisit.**
>
> F4SE was the initial inspiration for this script-management system. It was
> abandoned because it repeatedly broke the owner's games. The project exists to
> do the job without it.

---

## 1. The rule

**Never build on F4SE. Never rely on F4SE. Never suggest it, and never add it as
a dependency.**

If a design needs something F4SE provides, that is a signal the design is wrong,
not that F4SE is needed. Find the in-engine or file-format route instead.

Concretely, this means:

- no F4SE plugin as a dependency of anything built here
- no F4SE-dependent mod in the default active set
- no "install F4SE first" step in any setup or rig
- no Papyrus that assumes an F4SE-exposed function exists
- not using Wrye SSC as a substitute route, for the reason in §4

---

## 2. What F4SE is here, and why it is vendored

`ai_context/systems/F4SE-Plugins/` and `ai_context/systems/f4se-plugin-structure.md`
exist in this repo. That is deliberate and is **not** a contradiction:

- the F4SE **plugin interface** is vendored as **reference material**, to
  understand the shape of the problem and what a native hook surface looks like
- `ai_context/spec/compat_f4se_map.json` maps what F4SE exposes so we know what
  we are deliberately **not** depending on
- `ranking.json` scores the `replacement` objective, which includes `f4se` as a
  marker — the project is a replacement for this class of tool, and retrieval
  has to find that

Nothing in `ai_context/systems/F4SE-Plugins/` is compiled, linked, loaded, or
shipped. It is a documented reference surface.

**The test:** if removing F4SE from the equation changes whether a feature is
possible, the feature is out of scope. If it only changes how hard it is, the
in-engine route is the one to build.

---

## 3. Consequence for the current base core

**Known defect, found 2026-10-01, not yet fixed.**

| Entry | In `dplugins.txt` | Files on disk | Runtime present? |
|---|---|---|---|
| `XDI.esm` | enabled | yes | **no F4SE** |
| `FCOM.esp` | enabled | yes | **no F4SE** |
| `Cheat Terminal` | enabled | yes | **no F4SE** |

Verified: no `f4se_loader.exe`, no `f4se_steam_loader.dll`, no F4SE files of any
kind in the game `Data` folder, while `XDI.esm` is deployed and enabled. All 35
entries in `dplugins.txt` are present on disk, so this is not a stale-list
problem — the files are real and their dependency is absent.

`XDI.esm` is the clearest case: it is a **dependency-resolution plugin whose entire
purpose is to be loaded by an extender.** With no extender it is inert at best.

**This violates §1 as the base core stands.** Three entries are F4SE-dependent
and enabled, and our validator does not check for it, so it would report green.

TODO: classify these into a documented F4SE-dependent group, keep that group out
of the default active set, and add a gate that fails the build when an enabled
plugin requires an absent runtime. Not yet done. Until it is, treat
`dplugins.txt` as containing a known violation of this rule.

---

## 4. Why not Wrye SSC as a substitute

Considered 2026-10-01 and rejected. Recorded so it does not get re-proposed.

Wrye SSC is a **Skyrim Special Edition** product. Fallout 4's extender is F4SE.
Treating Wrye SSC as an FO4 route was a mistake in an earlier discussion, and
F4SE is the only FO4 equivalent — so substituting it changes nothing about §1.

Separately, Wrye ESI was considered as tooling and rejected for the CK
environment:

- Wrye is a **post-install** tool that rewrites installed game files; the CK
  harness is a **pre-install** authoring path. Wrye running first means the CK
  authors against Wrye's rewritten vanilla.
- `WryeESP.esp` is a **generated** master. It is recomputed on every Wrye run, so
  record counts, `nextFormId`, and file hashes all move. That breaks the
  baseline we already trust and breaks the FormID arithmetic the project depends
  on.
- Wrye's active-mods whitelist is a **runtime** list. This project deliberately
  separates CK authoring authority from what the game loads, via `dplugins.txt`
  and `plugins.txt`. Adopting Wrye's whitelist would undo that decision.

The one arguable benefit — Wrye's ESL optimisation shrinking vanilla, which would
speed up the 2.29M-record xEdit walk — costs a re-baseline of
`2,287,300 records / 64,926 CELL / 140 signatures`. Bad trade for a test
environment. **Not adopted.**

---

## 5. The replacement route

Where F4SE would have been the answer, the project's routes are:

| Need | Route |
|---|---|
| Read/write plugin records | xEdit scripting, or our own parser — see `ai_context/spec/fo4_record_format.json` |
| Address lookup for a native call | Address Library, from `ai_context/engine/address_mapping/` |
| Papyrus extension | CK + `.psc` sources; see `ai_context/papyrus_syntax_rules.md` |
| CK editor extension | CKPE, from `ai_context/systems/ckpe/` |
| Native runtime | **Layer A**, currently unhooked — the long pole |

`ai_context/goal_alignment.md` and the `replacement` objective in `ranking.json`
track this. Layer A is the honest answer to "what replaces it," and it is not
yet hooked — so that row is aspirational, not available.
