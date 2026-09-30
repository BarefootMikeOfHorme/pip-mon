---
source_url: https://modding.wiki/en/skyrim/users/plugin-load-order?format=md
title: Plugin Load Order | Modding.wiki
retrieved_utc: 2026-09-30T21:31:10Z
content_kind: upstream-documentation-verbatim
trust: upstream community reference, quoted verbatim. NOT verified against a compiler.
---

Plugin Load Order | Modding.wiki

















¶ What is plugin load order?
When talking about load order in relation to plugins, we are referring to the order in which each of the plugin data files are loaded by the Creation Engine. This order also affects the asset loadorder. If you're unfamiliar with plugins, you should first read this article: About Plugins.
To get the information required to decide the plugin load order we can call upon three main sources: plugin file extensions, plugin headers and LOOT metadata.
¶ Plugin headers and file extensions
The header of a plugin will vary slightly by game. Morrowind uses an older TES3 format, whereas all Bethesda titles up to Fallout 76 use a TES4 header. More detailed technical information about these headers is available on the UESP wiki (TES3, TES4).
¶ Header flags
Plugin headers contain flags which help the engine work out how to load it. These are the ESM and ESL flags which hold either a true or false value.

The ESL flag and .esl file extension only apply to plugins for Fallout 4, Skyrim Special Edition (v1.5.3+) and newer games.


The Override flag only applies to plugins for Starfield.

You may sometimes hear mention of an ESP flag too, however, this is simply a shorthand way of saying the plugin has neither the ESM or ESL flags set to true.
While it can be slightly confusing, these flags are related to but independent of the file extensions .esm, .esp and .esl. It is the combination of file extension and header flags which decide how and where the engine loads the plugin.



File Extension
ESM Flag
ESL Flag
Overlay Flag
Outcome




.esm
✔*
❌
❌
Master


.esm
✔*
❌
✔
TBC


.esl
✔ *
✔*
❌
Light Master


.esl
✔ *
✔*
✔
Light Master (Overlay is ignored)


.esp
❌
❌
❌
Plugin


.esp
❌
❌
✔
TBC


.esp
✔
❌
❌
Master


.esp
✔
❌
✔
TBC


.esp
❌
✔
❌
Light Plugin


.esp
❌
✔
✔
TBC


.esp
✔
✔
❌
Light Master


.esp
✔
✔
✔
Light Master (Overlay is ignored)



* This flag is automatically applied based on the file extension.
With these different types in mind, the load order used by the game will group and load the plugins as follows:
{Native Plugins - Loaded by the EXE}
{Master-flagged Plugins}
{Other non-Master Plugins}

This is a very basic explanation of the way the game loads plugins. A more detailed explanation is avaiable on the AFK forums.
¶ Masters
The other piece of important information plugin headers contain for load ordering are the master files. In very simple terms, a master file is another plugin - referenced by name - that must be loaded before the current one in order for it to function properly. For example, the Skyrim DLC plugin Dawngard.esm has a master of Skyrim.esm because it makes edits to some records (game objects) provided by it.
In most cases, even if your load order has these mods arranged improperly the engine will automatically load master files before their dependencies. Loading the game without all the required masters will result in a "Missing Masters" error, which may immediately crash the game.
¶ Overlay Plugins

As of Starfield 1.7.36, overlay plugins should not be used due to oddities in the way the engine builds the load order. Overlay flagged plugins containing new records will corrupt the data from their masters.

This is a new concept introduced in Starfield. An overlay plugin is a plugin that consists entirely of records that overwrite other plugins in the load order - meaning it has no new data of it's own. These plugins are loaded based on their position in the load order but do not count as taking up a slot as their overriding records are simply applied to their masters in memory.
¶ LOOT Metadata
The Load Order Optimization Tool (LOOT) is an application designed and maintained by the modding community and contains a list of plugins with data about their relationship to other plugins including optimal load order position, incompatibilities and requirements that are not contained in the plugin headers. Each Creation Engine game has a single document known as a masterlist which contains all the community-sourced knowledge for that title. The LOOT engine can use the masterlist data to suggest the optimal load order for your game.
While a mod author may provide some basic compatibility information on the mod page, it would be unreasonable to expect them to test every single other plugin in existence with their mod to understand the quirks various combinations can cause. To remedy this, the LOOT masterlist is completely independent of the actual plugins files and can be updated by anyone in the community by submitting your findings to the LOOT team.
Most modern mod managers implement some level of integration with LOOT masterlists, from simply showing relevant plugin messages to using the LOOT algorithm to generate the optimal load order for you. You can learn more about LOOT at the official website.
¶ Why is the plugin load order important?
The data structure of plugins can include records which overwrite data in the master files. Creation Engine games work on the rule of one, meaning that only the change from one plugin will be used in game - this will always be the plugin loaded last relative to others making the same edits.
Plugin load order can also cause indirect conflicts which manifest in the form of assets being loaded incorrectly or changes to game objects that may not be directly related causing a conflict or error in another plugin that relies on that data.
For this reason, you may encounter numerous different mod pages stating your must "load this mod last" as the easiest way to guarantee that one mod's changes are applied uninterrupted is to place it at the very bottom of your load order.
This approach is somewhat flawed in that it's physically impossible to load every single plugin last. A better way to think about this is that to preserve all changes from particular plugin it must be loaded after all other plugins that edit the same records. We'll a very basic example below:
[...]
Flowers A.esp
Flowers B.esp
Weapons A.esp
Weapons B.esp
Flowers C.esp

In the example, we have five fictional plugins. You'll notice we have two which edit armor in the game. If I want to ensure everything in Weapons A.esp is preserved, I could move it to the very bottom (load last) but this is unnecessary because the only other plugin we have here that edits weapons is Weapons B.esp so in order to keep all the changes I just have to make sure it loads after that plugin.
[...]
Flowers A.esp
Flowers B.esp
Weapons B.esp
Weapons A.esp <-- Now this will overwrite any matching changes above it.
Flowers C.esp

You should apply this principle when arranging your own load order. Community tools like xEdit can be incredibly helpful in understanding exactly which records conflict between different plugins.
If you discover a conflict between two mods which requires a specific order to solve, you should send this information to the LOOT team so your knowledge can be shared with the rest of the community.
¶ Sorting your plugin load order
There are two main schools of thought when it comes to arranging your plugins before playing your game. Many users rely on the LOOT masterlist to use the combined knowledge of the community to create the optimum load order and then tweak as necessary to suit their preferences. Others prefer to painstakingly research and test different plugins orders themselves without relying on existing knowledge to fully understand the impact of different variations of their load order. Both approaches have merit so it is up to you to decide how much time you want to dedicate to organising your plugins.
Within the community, it is highly recommended (especially for new players) that you use a mod manager to help you manage your load order. There are several good choices for Creation Engine games and the pros and cons of each are a subject for discussion in a separate article. When using a mod manager ensure you pay special attention to any warnings or errors presented to help you overcome potential issues.
