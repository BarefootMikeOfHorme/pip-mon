---
title: Using gen_papyrus_ref.py
purpose: >
  How to regenerate the Papyrus surface reference, what each layer means, and what
  the output can and cannot settle. Read before running it, because the layer
  layout is not obvious and a wrong layer split produces a confidently wrong file.
applies_to: gen_papyrus_ref.py, ai_context/engine/papyrus_surface/FO4_Papyrus_Reference.md
authority: measured
provenance:
  - "generated 2026-09-30 from the build's own shipped .psc sources"
trust: "verified by the generator's own parser self-check, plus five compile probes"
---

# The Papyrus surface reference

## What it is

`ai_context/engine/papyrus_surface/FO4_Papyrus_Reference.md` is **generated, never
hand-edited**. It is a complete inventory of every script, function, event, property,
custom event and struct declared by the `.psc` sources that ship with *this* Fallout 4
install — 7,866 scripts, 17,951 unique functions, 3,632 events, 25,717 properties.

It is the **declaration authority for this build**. Not a wiki, not a mod, not a
memory. If a name is not in the `ck` layer, this build does not declare it.

That distinction is the whole reason it exists. Before it, availability questions were
answered by hand and the hand was wrong three times in one session:

| Claim | Hand said | Build says |
|---|---|---|
| `CustomEvent` | not in FO4 | **is** — declared, and it compiles |
| `Debug.Notification` | not in FO4 | **is** — `Debug.psc` declares it native global |
| `SendEvent` | not in FO4 | correct, but it did not say `SendCustomEvent` is the replacement |
| `DebugNotification` | — | **not** in FO4; the form is `Debug.Notification` |

Every one of those was a hand-written entry in `ai_context/spec/papyrus_constructs.json`.
A gate that fails correct code is worse than no gate, because the fix people reach for
is switching it off.

## How to regenerate

Layer order on the command line is display order, and **the earlier layer wins
attribution**. That is the trap: `os.walk` is recursive, so pointing the first layer at
a parent directory claims everything beneath it and every later layer reports zero.

This is exactly what happened on the first run — the `ck` layer contributed
**0 unique functions** because `game`, one level up, had already taken all 19,113.
A file that looks complete and is silently mis-attributed is worse than no file, so
check the per-layer table after every run.

```powershell
$fo4 = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4'

# The 12 top-level game-shipped files must be STAGED, because the layer walker is
# recursive and would otherwise swallow everything underneath them.
$stage = "$env:TEMP\pipmon_ref_game"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage -Force | Out-Null
Copy-Item "$fo4\Data\Scripts\Source\*.psc" $stage -Force

python .\gen_papyrus_ref.py -o "ai_context\engine\papyrus_surface\FO4_Papyrus_Reference.md" `
    --layer "game=$stage" `
    --layer "ck=$fo4\Data\Scripts\Source\Base" `
    --meta "game=GAME-SHIPPED script sources, 12 files. The JContainer / JDB framework." `
    --meta "ck=CREATION KIT base script sources, 7,920 files. THE DECLARATION AUTHORITY for this build."
```

Expected tail: `files=7866 scripts=7866 unique_funcs=17951 unique_events=3632`

### Verify the split before trusting anything else

```
| Layer | Unique functions | Unique events | Unique properties |
| game  | 453              | 0             | 0                  |
| ck    | 17498            | 3632          | 25717              |
```

`ck` must be the large one. If `game` is large, the recursive-walk trap has bitten and
the layer split is wrong.

## What is deliberately NOT in it

`gen_papyrus_ref.py` also knows `f4se`, `mcm`, `baka`, `lighthouse` and `wsfw` as
layers. **None of them are indexed, on purpose.** Those are the extender, config-menu
and utility-framework lineage that PIP-MON exists to replace — see
`docs/POSITIONING.md`. Indexing them would put the thing we replace into the retrieval
corpus as though it were the spec.

There is also no mod layer. This machine has no Vortex and no mod content folder under
the workspace, so there was nothing to scan. If mods are added later they belong in a
**separate** output, not folded into the declaration authority — a mod's scripts are
that mod's business, and blending them makes "does the build declare this?" unanswerable.

## What it settles, and what it does not

**Settles:** whether a name is declared by this build; its exact signature, parameters
and flags; the `extends` hierarchy; which scripts declare custom events; how
`RegisterForX` pairs to the event it delivers; which scripts are entirely `global`.

**Does not settle:**

- **Behaviour.** A signature is not proof of what a function does at runtime.
- **Whether a `.psc` here compiles.** The shipped sources are *reference* sources. At
  least one, `abProtectronRaceScript.psc`, does **not** compile against our flags file
  (missing user flag `collapsedonref`). Presence in this file is not a compile pass.
- **Parameterised `CustomEvent`.** The generator's parser takes `code.split()[1]` — the
  name — so it silently tolerates the invalid form `CustomEvent Foo int` and will not
  flag it. **This is a reference generator, not a linter.** `tools/check_item.py` keeps
  the lint role, and `vprobe/papyrus/probe_papyrus.bat` keeps the compile role. The
  three are complementary and none substitutes for another.

## Pass 3a (optional) and why it is off

`--rag rag/index.sqlite3` adds a top-down trace: Papyrus function → F4SE `BIND()` macro
→ C++ signature → `RE::` engine types, flagging **stub** bindings and **arity
mismatches**. The default `--rag-prefix`
(`third_party/CommonLibF4/F4SEStub/runtime/src/Papyrus/`) matches 31 indexed headers in
our tree, so it would run.

It is not enabled for the shipped reference because it describes the **F4SE stub**, and
this project deploys no F4SE. Pass 3a answers "what would F4SE do", which is a
different question from "what does this build declare". Run it when the question is
about the extender lineage — the arity-mismatch column is genuinely useful for spotting
where a binding and a declaration disagree.

## Provenance rules

- Generated output is a **cache of the sources**, never the source of truth. The CK's
  own `.psc` files outrank this file, and this file outranks any wiki.
- Re-run it after a game or Creation Kit update. The build number is the key; a
  reference generated for 1.11.240.0 says nothing about any other build.
- The `ck` layer's authority is exactly the `<FO4>/Data/Scripts/Source/Base` tree that
  shipped with the installed Creation Kit. It is not guaranteed to match a different
  CK version, which is why re-running after an update is not optional hygiene.
