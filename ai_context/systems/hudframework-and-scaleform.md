---
source_url: https://github.com/reg2k/hudframework ; https://www.nexusmods.com/fallout4/mods/20309 ; https://www.nexusmods.com/fallout4/articles/371
retrieved_utc: 2026-09-30T21:28:15Z
content_kind: index-authored
trust: This index is authored. The single verbatim file saved from reg2k/hudframework is its README.md (150 bytes). The substantive Scaleform material is verbatim source from Ez0n3/F4SE-Plugins. Nexus article text was NOT retrieved (HTTP 403) and is not reproduced here.
---

# HUDFramework and Fallout 4 Scaleform — what actually exists

## 1. The HUDFramework repository is documentation-only

Repo found and cloned in full: `https://github.com/reg2k/hudframework`
(commit `dc608cddaf9ff7dbdff631e1c9dd1aa3fea485ba`, branch `master`).

**The entire repository contains exactly one file.** `git ls-files` output:

```
README.md
```

That `README.md` (150 bytes, saved verbatim at `hudframework\README.md`) is the
complete text:

```
# hudframework
HUDFramework is a UI framework for Fallout 4 that makes it possible for mods to add new UI elements to the HUD in a conflict-free way.
```

**There is no source code, no AS3/AS2, no Papyrus, no C++ in that repository.**
The working implementation of HUDFramework is a closed, binary-distributed
release on Nexus Mods (`nexusmods.com/fallout4/mods/20309`), not open source.

Consequence: there is no verbatim HUDFramework widget source to save. This is a
genuine absence upstream, not a fetch failure on our side.

## 2. Correction: Fallout 4 Scaleform is ActionScript 3, not ActionScript 2

The task brief asked for "Fallout 4 Scaleform/ActionScript 2.0". That premise is
wrong for this game. Fallout 4's Scaleform runtime uses **ActionScript 3**
(Skyrim's is AS2; FO4 moved to AS3).

Evidence from the verbatim source saved in `F4SE-Plugins\`:

* `Hooks_Scaleform.cpp:527` — `movieRoot->Invoke("root.dispatchEvent", ...)`
  `dispatchEvent` is an AS3 `EventDispatcher` method, not AS2.
* `Hooks_Scaleform.cpp:511` — `root.Invoke("getChildAt", &child, &index, 1)`
  `getChildAt` is the AS3 `MovieClip` accessor.
* `Hooks_Scaleform.cpp:501,515` — `root.Invoke("onF4SEObjCreated", nullptr, &f4se, 1)`
  Custom events dispatched into a movie, AS3 style.
* `ScaleformCallbacks.h:67` — `RegisterFunction(GFxValue* dst, GFxMovieRoot* movie, const char* name)`
  plus `Hooks_Scaleform.cpp:461-468`, which register AS3-visible natives on a
  movie root: `GetMembers`, `AllowTextInput`, `SendExternalEvent`,
  `CallFunctionNoWait`, `CallGlobalFunctionNoWait`, `GetDirectoryListing`,
  `MountImage`, `UnmountImage`.

Anything written for FO4 HUD work must therefore target AS3 (`import`/`export`,
`addEventListener`, `dispatchEvent`, `MovieClip.getChildAt`). Do not copy AS2
idioms.

## 3. What was saved instead: real FO4 Scaleform integration code

Because the HUDFramework repo has no code, the widget-registration and
menu-injection mechanism was taken from real Fallout 4 source in
`Ez0n3/F4SE-Plugins`, saved verbatim under
`systems\F4SE-Plugins\f4se\f4se\`. See `f4se-plugin-structure.md` for the
full table with blob SHAs. The instructive parts:

| File | Role |
|---|---|
| `Hooks_Scaleform.cpp` / `.h` | Hooks Scaleform's movie-load path; registers AS3-visible natives onto each movie root |
| `ScaleformCallbacks.h` | `F4SEScaleformInterface` with a `RegisterCallback` contract; `RegisterFunctions()` vtable slot |
| `ScaleformMovie.h` | `Invoke` / `InvokeArgs` wrappers — how a host calls into a movie's ActionScript by dotted path |
| `ScaleformLoader.h` | Movie-loading interception entry points |
| `PapyrusScaleformAdapter.cpp` / `.h` | Exposes Scaleform calls to Papyrus — the script↔movie bridge |
| `ScaleformValue.h` | `GFxValue` variant handling for marshalling values across the boundary |
| `ScaleformState.h`, `ScaleformTypes.h`, `ScaleformAPI.h` | Movie state inspection, type mapping, public interface |
| `GameMenus.h` / `.cpp` | Menu registry: `Register(name, creator)`, `RegisterMenu`, `IsMenuRegistered`, `UnregisterMenu` — the menu injection pattern, with the `bFlashElementsRegistered` flag |

The generalisable pattern, stated plainly: to add UI to FO4 you intercept movie
load, obtain the movie root, and either register native functions the ActionScript
can call, or `Invoke` a dotted path into the movie's own AS3. Cross-cutting
values are marshalled through `GFxValue`.

## 4. HUDFramework's own public interface (NOT retrieved — do not rely on this)

Nexus Mods article 371 ("HUD widget creation walkthrough") and the mod page
`nexusmods.com/fallout4/mods/20309` both returned **HTTP 403** to our fetcher.
Their contents are therefore **not** reproduced or paraphrased in this folder, and
nothing from them should be treated as verified documentation.

For the record, the HUDFramework API names that circulate publicly
(`HUDFramework.GetInstance()`, `RegisterWidget`, `LoadWidget`, `SendMessage`,
`Eval`, `HUD_WidgetLoaded`, the `IHUDWidget` document-class interface) are
**unverified here**. If PIP-MON ever needs them, they must be confirmed against
the Nexus release's own included Dev Kit before use.

## 5. Relationship to PIP-MON

Same rule as the F4SE material: structural inspiration only, not a dependency.
HUDFramework is a Papyrus/SWFW-based conflict-avoidance scheme; PIP-MON is not
adopting it. The transferable idea is the *widget-registry* concept — a single
owner of HUD injection so that multiple mods do not each overwrite `HUDMenu.swf`
— which is the same architectural problem PIP-MON's own bridge/UI layer faces.