---
source_url: https://github.com/Ez0n3/F4SE-Plugins
retrieved_utc: 2026-09-30T21:28:15Z
content_kind: index-authored
trust: This index is authored. Every .cpp/.h/.def/.psc/.vcxproj/.sln listed below is upstream source, saved verbatim and verified byte-identical to its upstream git blob SHA.
---

# F4SE Plugin Structure — Index

> ## READ THIS FIRST: F4SE IS **NOT** A DEPENDENCY AND **NOT** A TARGET API
>
> **PIP-MON does not use F4SE and will not depend on it.**
> F4SE is studied here for **structural inspiration ONLY** — that is, for the
> *organisational shape* of an extender: how a compiled DLL is versioned, gated,
> loaded and torn down; how a runtime interface is queried and held; how a plugin
> registers functions with a script VM; how a plugin checks version compatibility
> before going live; how source files are laid out in a plugin project.
>
> Do **not** treat anything in this folder as an API to call, an ABI to match, a
> header to include, or a deployment dependency. Specifically:
>
> * Do not add `f4se.dll`, `f4se_loader.exe` or `f4se_common` as requirements.
> * Do not include `f4se/*.h` headers in PIP-MON code.
> * Do not register with, or depend on, any F4SE interface or event bus.
> * If PIP-MON ever needs native game hooks it will have its own loader/bridge
>   mechanism; F4SE's approach is a *reference for design*, not a component.
>
> What legitimately transfers: the lifecycle shape (`Query` → `Load` →
> `Preload`), the "check compatibility, then hard-fail loudly" discipline, the
> separation of *declarations* (`.def` exports, `config.h` constants) from
> *behaviour* (`main.cpp`), and the general project-file conventions.
>
> FO4 upstream commit: `96f34d9499ff5f27887c22791823779fce507077` (branch `main`).

Local path prefix: `ai_context\systems\F4SE-Plugins\` — repo structure preserved exactly.

---

## A. The plugin template — `f4se_plugins\ez_f4se_plugin_example\`

The cleanest available example of "a compiled DLL hooks a script". All files verbatim.

| Repo path | Bytes | Blob SHA (short) | What it shows |
|---|---|---|---|
| `f4se_plugins/ez_f4se_plugin_example/main.cpp` | 7944 | `0bdfded2` | The whole lifecycle in one file: export, query, load, native registration |
| `f4se_plugins/ez_f4se_plugin_example/config.h` | 8286 | `9a7a05aa` | All tunable constants isolated from logic (version, name, runtime gate) |
| `f4se_plugins/ez_f4se_plugin_example/exports.def` | 73 | `664df85e` | Explicit export surface — only the lifecycle entry points |
| `f4se_plugins/ez_f4se_plugin_example/ez_f4se_plugin_example.vcxproj` | 5765 | `e5eb86cb` | Project layout: which include dirs, output, and link settings |
| `f4se_plugins/ez_f4se_plugin_example/ez_f4se_plugin_example.sln` | 2867 | `35adc510` | Solution structure |
| `.../Data/Scripts/Source/EzF4sePluginExampleQuestScript.psc` | 2256 | `41569bdc` | Papyrus side of the hook: script that calls into the DLL |
| `.../Data/Scripts/Source/EzF4seTestClass.psc` | 76 | `b2cc9dd5` | The native function declaration stub the C++ side binds to |

### The lifecycle, as actually written in `main.cpp`

Exported (`extern "C"`) symbols, in order of appearance:

```
F4SEPluginVersionData F4SEPlugin_Version   // static version blob — plugin fails to load without it
bool F4SEPlugin_Query(const F4SEInterface*, PluginInfo*)
bool F4SEPlugin_Load(const F4SEInterface*)          // called every load
bool F4SEPlugin_Preload(const F4SEInterface*)       // commented out; before globals init
```

`Plugin_Query` contract, straight from the source comments:

1. Open the log (`gLog.OpenRelative(CSIDL_MYDOCUMENTS, PLUGIN_LOG_FILE)`).
2. Write version banner via `_MESSAGE`.
3. Populate `info->infoVersion`, `info->name`, `info->version`.
4. Call `IsCompatible(f4se)`; return false to refuse loading.
5. `// Note: Nothing should be assigned below this point`.

`IsCompatible` performs two independent gates:

* `f4se->isEditor` → refuse (`_FATALERROR`, return false). A plugin that is
  unsafe in the editor must not half-load there.
* `IVersionCheck::IsCompatibleVersion(runtime, MINIMUM, SUPPORTED, STRICT)` →
  refuse on mismatch. `SUPPORTED_RUNTIME_VERSION_STRICT` is the knob that
  chooses "range" vs "exact pin".

`Plugin_Load` order of operations:

1. Re-open log, banner, re-run `IsCompatible` (defence in depth — Query can be
   called at a different time to Load).
2. `g_pluginHandle = f4se->GetPluginHandle();` — keep the handle for later calls.
3. `g_papyrus = (F4SEPapyrusInterface *)f4se->QueryInterface(kInterface_Papyrus);`
   then hard-fail if null.
4. `g_papyrus->Register(RegisterFuncs);`
5. Optional, commented in upstream: `QueryInterface(kInterface_Messaging)` +
   `RegisterListener(handle, "F4SE", PluginListener)` — the event subscription
   pattern, with `kMessage_PostLoad / PreLoadGame / GameLoaded / ...` switch.

### How a DLL actually gets hooked into a script

The binding is three-part and the pairing is explicit in the comments:

* **Papyrus declares the hook** — `EzF4seTestClass.psc` declares a function.
* **C++ implements it** — `namespace Plugin_Example_Functions { bool Test(StaticFunctionTag *base) }`
  printing via both `_MESSAGE` (plugin log) and `Console_Print` (in-game console).
* **C++ registers the pair** —
  ```cpp
  vm->RegisterFunction(new NativeFunction0<StaticFunctionTag, bool>(
      "Test", "EzF4seTestClass", Plugin_Example_Functions::Test, vm));
  ```
  i.e. *(function name, class name, implementation, VM)* — and `RegisterFuncs`
  returns `false` on failure. `NativeFunction0` = zero-argument; the `N` is the
  Papyrus arity. Signature, argument list and return type must agree on both sides.

`main.cpp` also keeps a commented block of "handles for other things", showing the
convention that each acquired interface is held in one file-scope `static`
pointer and null-checked immediately.

## B. Shared plugin scaffolding — `f4se_plugins\plugins_common\`

| Repo path | Bytes | Blob SHA (short) | What it shows |
|---|---|---|---|
| `f4se_plugins/plugins_common/IPluginCommon.h` | 4581 | `2b39276f` | Version-string/handle types shared by every plugin |
| `f4se_plugins/plugins_common/IVersionCheck.h` | 4770 | `deaf5453` | The reusable compatibility check used by `IsCompatible` |

## C. Loader-side reference — `f4se\f4se\`

| Repo path | Bytes | Blob SHA (short) | What it shows |
|---|---|---|---|
| `f4se/f4se/PluginAPI.h` | 12710 | `189533b6` | The full interface contract: `F4SEInterface`, `PluginInfo`, handle semantics |
| `f4se/f4se/PluginManager.h` | 3253 | `00c0c107` | Plugin registry/lifecycle manager interface |
| `f4se/f4se/PluginManager.cpp` | 23650 | `a6666100` | Real load-order handling, handle allocation, error reporting |
| `f4se/f4se/exports.def` | 20 | `cb127cb6` | Loader export surface |

## D. Fallout 4 Scaleform code — also from this repo

These files answer the HUD/UI question with real Fallout 4 code rather than
prose. See `hudframework-and-scaleform.md` in this folder for the full context
on why they are here.

| Repo path | Bytes | Blob SHA (short) |
|---|---|---|
| `f4se/f4se/Hooks_Scaleform.cpp` | 19176 | `5acdf75f` |
| `f4se/f4se/Hooks_Scaleform.h` | 234 | `7354b588` |
| `f4se/f4se/ScaleformAPI.h` | 671 | `429f9aa2` |
| `f4se/f4se/ScaleformAPI.cpp` | 257 | `ce812fcd` |
| `f4se/f4se/ScaleformMovie.h` | 2609 | `f07879b8` |
| `f4se/f4se/ScaleformLoader.h` | 1252 | `e6871f06` |
| `f4se/f4se/ScaleformCallbacks.h` | 2041 | `1cfecd78` |
| `f4se/f4se/ScaleformCallbacks.cpp` | 278 | `ff205b11` |
| `f4se/f4se/ScaleformState.h` | 2873 | `9be1308d` |
| `f4se/f4se/ScaleformTypes.h` | 753 | `88483e4f` |
| `f4se/f4se/PapyrusScaleformAdapter.h` | 382 | `65ef51ce` |
| `f4se/f4se/PapyrusScaleformAdapter.cpp` | 7472 | `7d67c84e` |
| `f4se/f4se/ScaleformValue.h` | 14122 | `652c4877` |
| `f4se/f4se/GameMenus.h` | 17999 | `ddb78a36` |
| `f4se/f4se/GameMenus.cpp` | 2817 | `fef14e06` |
| `f4se/f4se/GameRTTI.h` | 190458 | `90f8b567` |

Also saved verbatim: `README.md` (9049 B), `LICENSE` (227 B).

## Licensing

Upstream `LICENSE` is MIT (227 B). Note that the per-file copyright headers of
some files carry additional attribution; check each file's header before reusing
code text.