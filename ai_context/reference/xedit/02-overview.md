---
source_url: https://tes5edit.github.io/docs/2-overview.html
title: xEdit Overview
retrieved_utc: 2026-09-30T20:42:22Z
retrieved_by: fetch-agent
content_kind: upstream-documentation-verbatim
trust: upstream primary source, quoted verbatim, NOT paraphrased or summarized
---

  xEdit Overview | Tome of xEdit                 

![xEdit Icon](img/tes5edit-ico-blue.png)

# xEdit Overview

## xEdit Documentation

[Sharlikran](https://sharlikran.github.io/) [xEdit](https://tes5edit.github.io/) [ESOUI Code Collection](https://esouimods.github.io/) [PokemonGo](https://pokemon-fansite.github.io/) [Yu-Gi-Oh!](https://yu-gi-oh-duel-links-fansite.github.io/) [Fallout shelter Wiki](http://sharlikran.github.io/fsdoc/) [Wrye-Code-Collection](https://wrye-code-collection.github.io/) [Wrye-Code-Collection Wiki](https://wrye-code-collection.github.io/wcc-wiki/)

[Home](index.html)

# Main Table Of Contents

## [1\. Introduction](index.html)

## [2\. Overview](2-overview.html)

## [3\. xEdit Basic Use](3-basicuse.html)

## [4\. ModGroups](4-modgroups.html)

## [5\. Conflict Detection and Resolution](5-conflict-detection-and-resolution.html)

## [6\. The Method](6-themethod.html)

## [7\. Mod Cleaning and Error Checking](7-mod-cleaning-and-error-checking.html)

## [8\. Managing Mod Files](8-managing-mod-files.html)

## [9\. Mod Utilities](9-mod-utilities.html)

## [10\. FO3Edit FAQ](10-fo3edit-faq.html)

## [11\. Appendix](11-appendix.html)

## [12\. Cheat Sheets and Quick Reference Charts](12-cheat-sheets-and-quick-reference-charts.html)

## [13\. Scripting Functions](13-Scripting-Functions.html)

## [14\. Scripting Resources](14-Scripting-Resources.html)

## [15\. Tutorials](15-tutorials.html)

## [16\. xLODGen](16-xLODGen.html)

## [17\. DynDoLod](17-DynDoLod.html)

## [18\. xEdit What's New and Version Info](18-whatsnew.html)

# xEdit Overview

## Contents...

•  [2.1 Introducing xEdit](#IntroducingxEdit)

•  [2.2 Acquisition and Installation](#AcquisitionandInstallation)

•  [2.2.1 Downloading xEdit from the Nexus](#DownloadingxEditfromtheNexus)

•  [2.2.2 DirectX and Requirements - \[FO3Edit/FNVEdit/TES4Edit\]](#DirectXandRequirementsFO3EditFNVEditTES4Edit)

•  [2.2.3 Windows Vista and UAC Security](#WindowsVistaandUACSecurity)

•  [2.3 Starting xEdit](#StartingxEdit)

•  [2.4 xEdit Startup Errors](#xEditStartupErrors)

•  [2.5 Choosing a Theme](#ChoosingaTheme)

•  [2.5.1 From the Title Bar](#FromtheTitleBar)

•  [2.5.2 From Options](#FromOptions)

•  [2.6 Tour of User Interface](#TourofUserInterface)

•  [2.6.1 Master/Plugin Selection View](#MasterPluginSelectionView)

•  [2.6.2 Navigation Tree](#NavigationTree)

•  [2.6.3 View Tab](#ViewTab)

•  [2.6.4 Referenced By Tab](#ReferencedByTab)

•  [2.6.5 Message Tab](#MessageTab)

•  [2.6.6 Information Tab](#InformationTab)

•  [2.6.7 Main Context Menu](#MainContextMenu)

•  [2.6.8 Other Context Menu](#OtherContextMenu)

•  [2.6.9 View Tab Context Menu](#ViewTabContextMenu)

•  [2.6.10 View Tab Column Header Context Menu](#ViewTabColumnHeaderContextMenu)

•  [2.6.11 ModGroups Context Menu](#ModGroupsContextMenu)

•  [2.6.12 Options Menu](#OptionsMenu)

•  [2.6.13 Filter Menu](#FilterMenu)

•  [2.6.14 Remove Filter](#RemoveFilter)

•  [2.7 Saving and Confirmation](#SavingandConfirmation)

•  [2.8 Quick Tips and Shortcuts](#QuickTipsandShortcuts)

•  [2.8.1 Command Line Switches](#CommandLineSwitches)

•  [2.8.2 Keyboard Shortcuts](#KeyboardShortcuts)

•  [2.8.3 Module Selection Treeview](#ModuleSelectionTreeview)

•  [2.8.4 Main Treeview](#MainTreeview)

•  [2.8.5 Navagation Treeview](#NavagationTreeview)

•  [2.8.6 View Tab](#ViewTab1)

•  [2.8.7 Messages Tab](#MessagesTab)

•  [2.8.8 Referenced By Tab:](#ReferencedByTab2)

•  [2.8.9 Modgroup Editor](#ModgroupEditor)

## 2.1 - Introducing xEdit

xEdit is short for any version for example [SSEEdit](https://www.nexusmods.com/skyrimspecialedition/mods/164). xEdit is an advanced graphical module viewer/editor and conflict detector, with many additional functions that make it akin to a Swiss-army knife for modders and mod-authors alike. The primary function of xEdit is to help you spot conflicts between mods and resolve them, as well as to prepare your mod-list for a smooth run-time.

For the mod author xEdit provides the capability of viewing mod files at great depth, cleaning mod files of extraneous and duplicated records, merging mods together, changing ESPs to ESMs and scanning references in mod files for reach ability, form errors and specific references. These functions are very important to mod authors in the Fallout3 environment, as they will clean the mod of unintended changes, erroneous records and potential conflicts with other mainstream mods that players run.

Thus, whether you use mods to enhance your gaming experience or create mods for others to enjoy, using xEdit is both a wise investment in time and a beneficial act for the modding community. Authors who clean and prepare their mods with xEdit will experience fewer conflict and compatibility problems once published, and Players who [de-conflict](5-conflict-detection-and-resolution.html) their load orders are much less likely to experience crashes and headaches. In general, the use of xEdit can only improve the inter-operability of all mods, and this can only be a good thing.

If I have not convinced you by now to invest an evening to learn how to use xEdit, then you should be sacked and have a live Nuka-grenade stuffed down your trousers. If however you wish to do the right thing by the modding community, grab a coffee and let's get to work! xEdit is not a difficult tool to use, but it does require that your CPU (brain) be involved in the process, and that is what this tutorial is designed to teach.

## 2.2 - Acquisition and Installation

### 2.2.1 - Downloading xEdit from the Nexus

xEdit works on Windows XP, Vista, Windows 7, 8, and 10. Other platforms or Windows simulators may or may not work and are not officially supported. xEdit is available for download from Nexus, one of the most outstanding sources for Bethesda content.

 Downloads

[FO3Edit Nexus Link](http://www.nexusmods.com/fallout3/mods/637)

[FNVEdit Nexus Link](http://www.nexusmods.com/newvegas/mods/34703)

[FO4Edit Nexus Link](http://www.nexusmods.com/fallout4/mods/2737)

[TES4Edit Nexus Link](http://www.nexusmods.com/oblivion/mods/11536)

[TES5Edit Nexus Link](http://www.nexusmods.com/skyrim/mods/25859)

[SSEEdit Nexus Link](http://www.nexusmods.com/skyrimspecialedition/mods/164)

[EnderalEdit Nexus Link](http://www.nexusmods.com/enderal/mods/23)

Be sure you download the proper version for the proper game. TES5Edit is for Skyrim and SSEEdit is for Skyrim SE.

![Download File](img/image002.jpg)

The following page will display from the TES5Edit Nexus site. You will need to first click on, "Files" to display the list of xEdit versions. Once loaded, check the Version number in the upper-right corner (B) to ensure you download the most current revision. Then click on that revision of xEdit in the Main Files section (C).

Once you download the program, you will need an archive extraction tool that can handle 7-Zip files (.7z), such as 7-Zip, which is available at: [http://www.7-zip.org/](http://www.7-zip.org/)

![Extract Files](img/image004.jpg)

Once the archive is open, you will need to extract the TES5Edit files into the right place for it to function. That place is the Skyrim\\ directory, where the TESV.exe program is installed. Do Not install into the Skyrim\\Data directory or the program will not function correctly. Also refer to [Windows Vista and UAC Security](#WindowsVistaandUACSecurity).

Technically you can run the xEdit exe from any location except the game's Data folder.

Previously all xEdit packages contained a special file of hard coded values not found in the main ESM or DLC. This is now part of xEdit, and the loose file is no longer required or included. All future releases will no longer include them.

If have used previous versions of xEdit, you can remove files like `Skyrim.Hardcoded.dat` as they are no longer needed.

[Top of this Group](#AcquisitionandInstallation)

### 2.2.2 - DirectX and Requirements - \[FO3Edit/FNVEdit/TES4Edit\]

This does not apply to TES5Edit, SSEEedit, or FO4Edit! It also does not apply to Windows 7, 8.1 or 10

![d3dxerror](img/d3dxerror.jpg)

With FO3Edit, FNVEdit, or TES4Edit installed let's review some system parameters and drivers that you will need in order to successfully operate the tool for Windows XP. xEdit will require current DirectX drivers from Microsoft. You can tell if your system is up-to-spec by simply launching the tool. If xEdit loads and presents you with a Master/Plugin Selector view, your good to go but you can skip this next step. If you get an error about d3dx9\_\*.dll not being installed, you need to update your DirectX to at least the March 2008 Version.

DirectX can be found here: [Microsoft DirectX® 9.0c End-User Runtime](https://www.microsoft.com/en-us/download/details.aspx?id=34429)

Once DirectX is installed, you should be able launch the xEdit application successfully. If you still get errors, please report them to ElminsterAU.

[Previous Section](#DownloadingxEditfromtheNexus) [Top of this Group](#AcquisitionandInstallation)

### 2.2.3 - Windows Vista and UAC Security

The UAC Security feature of Vista, Windows 7, 8, and 10 protects the Program Files directory from un-authorized access. Unfortunately, this also causes problems for xEdit and Bethesda games, and requires some manual intervention on your part to resolve. You have 3 options for dealing with UAC Security:

•  Disable the UAC completely, but this will leave your system more vulnerable. (not recommended)

•  Install your Bethesda game and xEdit in the C:\\Games folder. For example, C:\\Games\\steamapps\\common\\Skyrim. Which is not controlled by UAC and will prevent conflicts. (recommended)

•  Assign the "Users" group "Full Control" of the C:\\Games folder (and subfolders) in UAC, which will prevent UAC from causing problems.

Any of the above options will work, though it is probably a better option to install your Bethesda game and xEdit into C:\\Games directory and avoid the Program Files directory all-together. That leaves your system secure and averts the UAC problem for Bethesda fames.

If you are unable to get past the UAC restrictions, you may want to look for forums that people frequent for additional assistance with Windows. If all went well with the install, you should be able to successfully run xEdit.

[Previous Section](#DirectXandRequirementsFO3EditFNVEditTES4Edit) [Top of this Group](#AcquisitionandInstallation)

## 2.3 - Starting xEdit

When xEdit starts, you get a dialog to select which modules you want to load. Fallout 3, Fallout NV, and Oblivion use the time date stamp of the files to determine load order. Skyrim, Skyrim SE, and Fallout 4 use other files maintained by your mod manager. Load order cannot be changed with xEdit. If you need to change your load order, close xEdit and change the load order, then re-launch xEdit.

For FO3/FNV some prefer to use FOMM as a mod manager. There are several versions available.

•  [FOMM Q and Timeslip v0.13.21(Last update 24 Nov 2010)](https://www.nexusmods.com/fallout3/mods/640)

•  [FOMM by Q, Timeslip, and kaburke v0.13.21(Last update 24 Nov 2010)](https://www.nexusmods.com/newvegas/mods/36901)

•  [FOMM by NiveusEverto v0.14.14.5(Last update 16 Dec 2018)](https://www.nexusmods.com/newvegas/mods/54991)

BOSS and LOOT will also sort mods if you are familiar with them.

•  [BOSS v2.3.2 by deathssoul (latest version)](https://github.com/boss-developers/boss/releases/tag/v2.3.2)

•  [BOSS v2.3.0 by WrinklyNinja (last version by this author)](https://github.com/boss-developers/boss/releases/tag/v2.3.0)

•  [LOOT v0.15.1 by WrinklyNinja](https://github.com/loot/loot/releases)

![module_select](img/module_select.jpg)

Select the mods that you want to load into xEdit, which can be all (for conflict detection) or just one if you're working on a specific mod-file. Once you have confirmed that dialog the selected modules will start loading in the background. The first time you run xEdit, depending on your system, it will take several minutes to load while it creates a cache of important data. xEdit subsequently loads much faster after building the cache.

![image006.jpg](img/image006.jpg)

The Navigation Tree appears on the left and shows all active modules in their correct load order. From the Navagation Tree you can look at every single record in any of your modules. An example of a successful launch of xEdit is shown, though you may also see additional error information if errors were found during start-up.

[Previous Section](#WindowsVistaandUACSecurity) [Top of this Group](#AcquisitionandInstallation)

## 2.4 - xEdit Startup Errors

When started it will automatically find your game's Data directory via the system registry (not by where it was installed). If you immediately get errors indicating that xEdit can't find the game's configuration files, it means one of two things. You moved the files to another directory or for games installed with Steam, you verified the integrity of your game cache.

As a reminder, this is what verifying your game cache looks like.

![verifygamecache](img/verifygamecache.jpg)

This is what the error would look like from FNVEdit.

![error_part_1](img/error_part_1.jpg)

After you click OK xEdit will finish loading and the messages tab will display the following message.

![error_part_2](img/error_part_2.jpg)

If you moved the install it is recommended to move the files back to their original location or re-install the Game again. If you verified the game cache from Steam, run the game's official launcher. Below is an example of the Fallout 4 launcher.

![Fallout-4-game-launcher](img/Fallout-4-game-launcher.jpg)

[Previous Section](#StartingxEdit) [Top of this Group](#AcquisitionandInstallation)

[Previous Group](#IntroducingxEdit)

## 2.5 - Choosing a Theme

### 2.5.1 - From the Title Bar

One way to select a theme is to Right Click the title bar and go to Theme. There are around 40 Themes to choose from. The one pictured in these docs is the Tablet Dark Theme.

![Theme-Menu](img/Theme-Menu.jpg)

The requirements are Desktop Window Manager, Themes services enabled, Desktop Composition, and an Aero Theme selected.

**NOTE:** Your screen will be blank if you previously selected a Theme but disabled any of its requirements.

### 2.5.2 - From Options

You can also select a theme by bringing up the xEdit contextual menu, options, and select UI Theme.

![Theme-Menu](img/theme-options.jpg)

[Previous Section](#xEditStartupErrors) [Top of this Group](#AcquisitionandInstallation)

## 2.6 - Tour of User Interface

This section of the manual will take you on a brief tour of xEdit to introduce you to the different views and screens that you will be working with. This tour is designed for beginner-level users and does not discuss the functionality of the views at any depth just yet. The tour is recommended for all levels of user, especially if you have not used xEdit within the last several months as there have been many updates.

### 2.6.1 - Master/Plugin Selection View

![error_part_1](img/image008.jpg)

The Master/Plugin Selection view is presented to you when xEdit is first launched and allows you to select/un-select the mods that you want xEdit to load. You can also Right-Click in open space to access more options, such as "Select All" or "Select None".

To change the load order of mods, close xEdit and open [FOMM](#links_fomm). Change the load order as desired, close FOMM and re-open xEdit.

There is an additional option you can use to quickly load a single mod – simply Double-Click on a mod file in the list. Double-clicking a mod will automatically un-select all other mod files and will load the selected mod file. It's a short-cut to loading single mods.

[Top of this Group](#TourofUserInterface)

### 2.6.2 - Navigation Tree

![image010](img/image010.jpg)

The Navigation Tree shows a hierarchical data structure for all references as well as a status bar and search boxes for hunting-down specific FormIDs, EditorIDs, or by filename.

The main context menu (B) contains all the major xEdit functions, including Filters, Reference hunts, Error checking, Removing Extraneous content and many more. There are also several functions that only apply to Oblivion but the rest apply to all games. We will discuss each of the important options in [Main Context Menu](2-overview.html#MainContextMenu).

[Previous Section](#MasterPluginSelectionView) [Top of this Group](#TourofUserInterface)

### 2.6.3 - View Tab

![image020](img/image020.jpg)

The View Tab is used to display the details about any record that you click-select in the Navigation Tree. The View Tab is where most of the work of conflict resolution takes place. Each mod that has a copy/version of a selected record is shown in the view with its own Column. This way, all the mods that have a version of the same record can be shown side-by-side to more easily navigated and spot conflicts.

We discuss this view at depth in the chapter on [Conflict Detection and Resolution](5-conflict-detection-and-resolution.html), but for now, it's only important to understand its high-level function and how to navigate to it. As in the Referenced By Tab, within the View Tab you can Right-click on any reference to receive an additional context menu. You can edit and remove any entry, as well as tell xEdit what kind of view your looking for; with or without de-conflicted rows (rows without a conflict of any kind).

[Previous Section](#NavigationTreeview) [Top of this Group](#TourofUserInterface)

### 2.6.4 - Referenced By Tab

![image018](img/image018.jpg)

The Referenced By Tab is used to locate all occurrences of a reference such as Soda Bottles, Projectiles and Explosions. If you select a reference in the Navigation Tree, such as the "Glass Explosion" from the [Destroyable Environments](https://www.nexusmods.com/fallout3/mods/1904) Mod by [Bigkid7834](https://www.nexusmods.com/fallout3/users/173512), where every occurrence of that Glass Explosion in the in the game is displayed.

You can also Left-Click on any reference in the Referenced By Tab to present a copy/remove menu. Here you can literally delete the reference of the object out of the mod or copy it into another mod (perhaps a patch plugin, discussed in detail in the chapter on [Conflict Detection and Resolution](5-conflict-detection-and-resolution.html). These functions are especially useful for gaining a high-level understanding of what the mod contains, and where references can be found (a task which can be exceedingly difficult in the GECK).

You can also double click entries in that list to directly jump to that record (and switch to the View tab), you can then use the backward button in the top right corner or on your mouse (if it got more than 2 buttons).

[Previous Section](#ViewTab) [Top of this Group](#TourofUserInterface)

### 2.6.5 - Message Tab

![image016](img/image016.jpg)

The Messages Tab acts like a running log-file of what xEdit is doing in response to your actions. When you first load xEdit, the Messages Tab is displayed by default so that you can watch the loading process in real-time. This is important as any Errors in the mod files such as missing references, missing files or dirty-edits to a mod file done in a hex-editor can all result in errors. Most of these will be harmless, but some are lethal, and you can see them all in the Messages Tab while they are loaded into xEdit.

Any actions that you take which result in changes to the files, such as Saving, will also print their output into the Messages Tab. Thus, it is important to check this tab often while working in xEdit, as there are cases in which a mod file won't save due to errors – and you want to know about that as soon as a problem occurs.

[Previous Section](#ReferencedByTab) [Top of this Group](#TourofUserInterface)

### 2.6.6 - Information Tab

![image010](img/image014.jpg)

The Information Tab holds a textural version of the xEdit help guide, including basic information on mod conflict resolution and a legend on [how to interpret the color scheme](5-conflict-detection-and-resolution.html#ColorSchemesandDisplayOrder) of text and background. You can reference this tab at any time as a cheat-sheet of sorts on how to use xEdit.

You can also capture any/all sections of the help information by Right-Clicking in the view-pane and selecting one of the textural options presented to you.

[Previous Section](#MessageTab) [Top of this Group](#TourofUserInterface)

### 2.6.7 - Main Context Menu

![oblivion_context_menu](img/oblivion_context_menu.jpg)

The main context menu is accessed by Right-clicking in the [Navigation Tree](2-overview.html#NavigationTree), and acts as the main navigation and function selection point for xEdit. As such, much time and explanation are provided on how to utilize this menu, as well as a Reference Chart (shown below) to help illustrate what each function does.

There are some functions such as, "Generate Object LOD" and the "Set VWD for all REFR…" options that only work on Oblivion and should not be used with Fallout3. With some functions you will be presented with additional options, while with others such as "Check for Errors", the output is sent to the [Messages Tab](#MessageTab) (or other tabs with other functions).

Each of these functions is described in-detail within the tutorial, and Quick Links to those detailed sections can be found in the list below for easy-access. Additional description is provided below for each function on the main context menu.

•  [Compare To](8-managing-mod-files.html#ComparingTwoVersionsofaMod) — Loads another module at the same load order index as the one under the cursor when you right clicked. Works very well to compare 2 different versions of the same module against each other.

•  [Create delta patch using](18-whatsnew.html#Createdeltapatchusing) — After loading the old version of a module you can make a copy of only the records that have changed between the two versions of the compared modules.

•  [Remove Filter](2-overview.html#RemoveFilter) — This function will remove the current filter, so that all loaded-data will be presented and processed.

•  [Apply Filter](5-conflict-detection-and-resolution.html#ApplyingConflictFilters) — This function will present you with the [Filter Menu](2-overview.html#FilterMenu), where you can select options on how you want to filter (restrict) the data shown in xEdit.

•  [Apply Filter to show Conflicts](5-conflict-detection-and-resolution.html#ApplyingTheConflictFilter) — Automatically apply the conflict filter.

•  [Checking for Errors](7-mod-cleaning-and-error-checking.html#CheckingForErrors) — This function is used to check for reports any case where the information in the module file does not match the xEdit record definitions. This is Not a check for missing references, physical or data errors — that is done during the loading process with results available in the [Messages Tab](#MessageTab).

•  [Checking for Circular Leveled Lists](7-mod-cleaning-and-error-checking.html#CheckingforCircularLeveledLists) — Leveled Lists can reference other Leveled Lists, it's possible in this case to build a circular reference (with as little as 2 leveled lists directly referencing each other, or any number of additional leveled lists in the chain). When the game engine then tries to resolve that leveled lists down to an item/creature/NPC it can get caught in the endless loop and crash.

•  [Renumbering FormIDs](8-managing-mod-files.html#ChangingModFormIDs) — This function will re-number all references in a selected mod file, starting from a number that you specify. This function does not in any way resolve conflicts and should be used only if you know exactly what you are doing (as it will result in incompatibilities with existing save games and any module which uses this module as a master). This function was implemented for the Better Cities team, so that they could assign non-overlapping FormIDs to each of their city specific esps, to prevent the need for changing FormIDs when merging the city-specific esps into the alternative "full" esp which contains all cities.

•  [Applying Scripts Into](9-mod-utilities.html#ApplyingScriptsInto) — This function is used to apply a script(s) into a specific reference and writes the resulting new or override records into the specified module.

•  [Set VWD for all REFR with VWD Mesh in this file](9-mod-utilities.html#s_78) \[TES4\] This function only works with Oblivion.

•  [Set VWD for all REFR with VWD Mesh copy as override](9-mod-utilities.html#s_78) \[TES4\] This function only works with Oblivion.

•  [Add (Reference)](9-mod-utilities.html#ChangingandAddingReferences) — What exactly that menu shows you is depending on the context, if you right click on a file node you will get a list of all groups that don't exist yet, if you right click on a group you get a list of all records that can be added to it and so on. And yes, this can be used to add new records, so you can basically build a mod from scratch with it.

•  [Mark Modified](9-mod-utilities.html#MarkingNodesasModified) — It will mark the currently selected node and all child nodes as modified. To minimize the chance that xEdit breaks something that it doesn't fully understand when saving, only records that are marked as modified are assembled field by field, sub record by sub record. Any record or even complete group that is not marked as modified is simply copied unchanged as a blob of bytes from the old module file into the newly saved one.

•  [Add Masters](8-managing-mod-files.html#AddingMasterFilestoaPlugin) — This adds a new master to the MAST sub record in the file header and correctly renumbers the FormIDs in the module. This function is also used to create an ESM/ESP pair from a single ESP plugin.

•  [Sort Masters](7-mod-cleaning-and-error-checking.html#SortingMasterFileLoadOrders) — This function will sort the global load order of master files to match the order of global load order.

•  [Clean Masters](7-mod-cleaning-and-error-checking.html#UsingCleanMasterstopurgeunusedMasterFileReferences) — This function will scan a Plugin for Master dependencies, determine if any Masters are un-used by the plugin and remove them.

•  [Copy Idle Animations Into](9-mod-utilities.html#CopyingandReplicatingIdleAnimations) — This function is used to copy all the idle animations from one skeleton to another, which replicating monsters.

•  [Hidden](8-managing-mod-files.html#hidden)— This function hides the selected mod file(s) or references from further view/processing by xEdit.

[Previous Section](#InformationTab) [Top of this Group](#TourofUserInterface)

### 2.6.8 - Other Context Menu

![other_context_menu](img/other_context_menu.jpg)

•  [Creating a Merged Patch](5-conflict-detection-and-resolution.html#CreatingaMergedPatchAutomaticMethod) — This function is used to build the foundation of a merged patch-file, resulting in a new mod file using a name you select. More on this in the section on [Mod Conflict Resolution](5-conflict-detection-and-resolution.html).

•  [Creating Start-Game Enabled Quest (SEQ) Files](9-mod-utilities.html#CreatingStartGameEnabledQuestSEQFilesTES5SSE) \[TES5/SSE\]

•  [Generate Object LOD](9-mod-utilities.html#s_78) Various updates have been made to LODGen mode. Thanks sheson! This mode will work for all games.

•  [Building Reachable Info](9-mod-utilities.html#BuildingReachableInformation) — This function scans all references in a selected mod and will determine which are reachable (by the player in-game) from those that cannot ever be reached or accessed by the player. This function considers the totality of all loaded modules (looking only at the contents of the winning version of each record). So, it's possible for the reachable status to be different for a record, depending on which other modules you've loaded.

[Previous Section](#MainContextMenu) [Top of this Group](#TourofUserInterface)

### 2.6.9 - View Tab Context Menu

![viewtabcontextmenu](img/viewtabcontextmenu.jpg) ![viewtabcontextmenu_add](img/viewtabcontextmenu_add.jpg)

This context menu is available from the [View Tab](#ViewTab) when you Right-Click as shown for (D) in the View Tab's screen shot.

### 2.6.10 - View Tab Column Header Context Menu

![viewtabcolumnheadercontextmenu](img/viewtabcolumnheadercontextmenu.jpg)

This context menu is available from the [View Tab](#ViewTab) when you Right-Click the column header as shown for (A) in the View Tab's screen shot.

### 2.6.11 - ModGroups Context Menu

![modgroupsmenu](img/modgroupsmenu.png)

This context menu is available from the [View Tab](#ViewTab) when you Right-Click as shown for (D) in the View Tab's screen shot and hover over ModGroups.

### 2.6.12 - Options Menu

![other_context_menu](img/optionsmenu.jpg)

The options menu allows you to alter some of the xEdit functionality such as hiding unused or ignored information. It is best to leave things at the default settings.

Unhiding the ignored and unused information will make it harder to determine valid conflict resolution. Unused and ignored information are things that the CK does not alter when editing the plugin. Therefore you do not need to worry about resolving conflicts with those values. They do not need decoding or investigating.

It is also recommended to leave Simple Records checked because to edit those you need the CK to render a 3D view. xEdit does not have the capability to render the world in 3D so those records should be changed with the CK.

With CELL and WRLD some of its subrecords may be altered if you know what you are doing and how the changes will affect the game.

[Previous Section](#OtherContextMenu) [Top of this Group](#TourofUserInterface)

### 2.6.13 - Filter Menu

![image022](img/image022.jpg)

The Filter Menu can be used for several purposes in xEdit. Conflict resolution, reference viewing, and reach ability data are a few examples. All are achieved by activating an xEdit Filter. The Filters essentially work to restrict what data you see in xEdit to just what you want to see or are working on, and in some cases, data is parsed (such as in conflict detection). When resolving conflicts [Applying The Conflict Filter](5-conflict-detection-and-resolution.html#ApplyingTheConflictFilter) is also a filter but it is automated.

### 2.6.14 - Remove Filter

![image024](img/image024.jpg)

Removing the filter returns everything to its default state and all the expanded trees in the Navagation Tree will be closed.

[Previous Section](#FilterMenu) [Top of this Group](#TourofUserInterface)

[Previous Section](#AcquisitionandInstallation)

## 2.7 - Saving and Confirmation

![image026](img/image026.jpg)

You can save your changes at any time by pressing, "CTRL" and "S", and when you exit xEdit (if there are changes to save). If you have not saved for a while, xEdit may also remind you that it's a good time to save. When the, "Save changed files" window is presented, click on the mods you want to save.

The output of each save is shown in the Messages Tab. It is important to check this, as sometimes errors in a mod file can prevent you from successfully saving it.

[Previous Section](#RemoveFilter)

## 2.8 - Quick Tips and Shortcuts

There are several important keyboard short-cuts that can make your usage of xEdit more efficient with less keystrokes for some common functions.

### 2.8.1 - Command Line Switches

•  `-cp-general:<codepage>` where `<codepage>` is either `utf8` or a [codepage number](18-whatsnew.html#Languages). NOTE: It should not be necessary to override this.

•  `-cp:<codepage>` or `-cp-trans:<codepage>` sets `<codepage>` for [Translatable Strings](18-whatsnew.html#Translatablestrings) to a [codepage number](18-whatsnew.html#Languages) or `utf8`

•  `-l:<language>` Sets [Language](18-whatsnew.html#Defaultlanguage), affects used `<codepage>` and .strings files

•  `-edit` Enables Edit Mode

•  `-view` Enables View Mode

•  `-saves` Enable Saves Mode View Mode Only

•  `-IgnoreESL` Will load all modules as full modules, even if ESL flagged.

•  `-PseudoESL` Will check if the module falls within ESL constraints and loads the file like an ESL if possible. ESL specifications are explained in the [Appendix:ESL vs ESM](11-appendix.html#ESLvsESM)

•  `-DontCache` Completely disables ref caching

•  `-DontCacheLoad` Don't load cache files if present, but save if possible

•  `-DontCacheSave` Don't save cache files after building refs

•  `-AllowDirectSaves:<filename list>` The file may be an .esm, .esl, or .esp. Without a list of files, this will load non-official (official = game master, official dlcs, CCs) modules without using memory mapped files. Optionally you can specify a list of files. Which will only load the listed modules without using memory mapped files. This optional list may include official modules.

•  `-<gamemode>` Specifies which game mode to use. `<gamemode>` can be any of the following: `['tes5vr', 'fo4vr', 'tes4', 'tes5', 'enderal', 'sse', 'fo3', 'fnv', 'fo4', 'fo76']`

•  `-moprofile:<profilename>` Opens the plugin selection from the MO profile named in the switch.

•  `-setesm` \[Set ESM flag. Plugin selection screen will appear.\]

•  `-clearesm` \[Remove ESM flag. Plugin selection screen will appear.\]

•  `-quickshowconflicts` or `-qsc`

•  `-veryquickshowconflicts` `-vqsc` \[loads all modules according to plugins.txt without showing module selection, except if CTRL is pressed on start\]

•  `-quickclean` or `-qc` \[cleans and prompts to save the file\]

•  `-quickautoclean` or `-qac` \[Cleans 3 times and saves in between each step\]

•  `-autogamelink` or `-agl`

•  `-NoAutoMarkModified` prevents mark modified from being applied to Dawnguard.esm (resulting in the Soul Cairn error described below)

•  `-ForceMarkModified` always applies mark modified to the cleaned file (if there was anything to clean)

•  `-C:<path>` \[path to use for cache files\]

•  `-S:<path>` \[Path to look for scripts\]

•  `-T:<path>` \[Temporary Directory\]

•  `-D:<path>` \[Specify a Data Directory\]

•  `-O:<path>` \[Specify path for generated LOD files\]

•  `-I:<path>` \[Game INI Files\]

•  `-G:<path>` \[Save Game Path\]

•  `-P:<path><filename>` \[Custom Plugins.txt file\]

•  `-B:<path>` \[Backups path i.e. Edit Backups\\\]

•  `-R:<path><filename>` \[Custom xEdit Log Filename\]

All path parameters must be specified with trailing backslash. For example `C:\SomePath\for_xedit_xache\`

### 2.8.2 - Keyboard Shortcuts

•  Holding `Shift+Ctrl+Alt` while starting shows a dialog asking if the setting file should be deleted.

•  Holding `Shift` while starting to reset window position

### 2.8.3 - Module Selection Treeview

•  `Hold SHIFT` to skip building/loading references for all plugins.

•  `[UP/DOWN]` arrow to navigate plugin list. If multiple plugins are selected, this will deselect them.

•  `[Space]` to check or uncheck selected plugins.

### 2.8.4 - Main Treeview

•  `Ctrl + S` Opens the Save Files dialog.

•  `Ctrl + F3` to open Assets Browser

•  `Alt + F3` to open Worldspace Browser

### 2.8.5 - Navagation Treeview

•  `Ctrl + 1 through 5` to set a Bookmark.

•  `ALT + 1 through 5` to jump to a Bookmark.

•  Press `F2` with the record selected in the Navigation Tree: Edit the FormID of the selected Record.

•  `Ctrl or Shift` while clicking to select several records/plugins at once

•  `Del` To delete a record or a group of records

•  `Alt + Click` to fully expand a tree. This can take a lot of time when expanding large trees.

•  `[Right Arrow]` or `+` to expand current node

•  `[Left Arrow]` or `-` to collapse current node

•  `*` Expand treview (recursive)

•  `/` Collapse treeview (recursive)

### 2.8.6 - View Tab

•  `Ctrl + UP/DOWN` to move elements in unordered lists.

•  Press `F2` with the field selected in the View Tab: Edit the field with the In-Place Editor.

•  `Ctrl + Click` on a FormID in the View Tab: Jump to the selected Record in the Navagation treeview

•  `[Double Click]` on text field to open multiline viewer

•  `[Double Click]` on `[Integer, Float, or FormID]` to open In-Place Editor

•  `Shift + [Double Click]` on text field to open multiline editor

•  `Ctrl + C` to copy to clipboard

•  `Ctrl + W` from a weather record to open the visual weather editor

•  `Alt + CRSR` while in View Tab to navigate within the Navagation Treeview

### 2.8.7 - Messages Tab

•  `CTRL + [Double Click]` on FormID to switch focus to that record

### 2.8.8 - Referenced By Tab:

•  `Double click` on an entry in the Referenced By Tab: Jump to the selected Record in the Navagation Tree.

### 2.8.9 - Modgroup Editor

•  `CTRL UP/DOWN` - Move entry

•  `INSERT` - Insert entry (Insert Module or CRC depending on which is selected)

•  `SHIFT + INSERT` - Insert crc (when on a module)

•  `DELETE` - Delete a module or crc

•  `SPACE / Mouse Click` - toggle flag when a flag is currently focused

[Previous Section](#SavingandConfirmation)

[« Previous Page](index.html) [Next Page »](3-basicuse.html)

[docs](https://github.com/TES5Edit/docs) is maintained by [TES5Edit](https://github.com/TES5Edit). This page was generated by [GitHub Pages](https://pages.github.com).
