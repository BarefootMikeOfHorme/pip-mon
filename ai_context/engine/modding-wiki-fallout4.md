---
source_url: https://modding.wiki/en/fallout4?format=md
title: Fallout 4 | Modding.wiki
retrieved_utc: 2026-09-30T21:33:40Z
content_kind: upstream-documentation-verbatim
trust: upstream community reference, quoted verbatim. NOT verified against a compiler.
---

Fallout 4 | Modding.wiki















  Cover artwork for Fallout 4

Fallout 4 is an RPG video game developed by Bethesda Game Studios and published by Bethesda Softworks, set predominantly in the Post-Apocalyptic Wasteland of Boston, Massachusetts and the area surrounding it. It was released on November 10, 2015, for Microsoft Windows, Xbox One, and PlayStation 4.
 
¶ Brief Synopsis
Fallout 4 is set in a post-apocalyptic world in the year 2287, 210 years after a devastating nuclear war. The player assumes the role of the "Sole Survivor," who emerges from Vault 111, a cryogenic facility, after being frozen for over two centuries.
The story begins in the pre-war era in the year 2077, where the Sole Survivor lives with their spouse, infant son Shaun and a Mister Handy Robot named Codsworth. As nuclear bombs fall, the family rushes to Vault 111 but are unknowingly tricked by the cunning Vault-Tec Corporation into Cryogenic stasis. The protagonist awakens to witness their spouse being murdered and Shaun being kidnapped by unknown assailants. The Sole Survivor is re-frozen and awakens again in 2287, determined to find their son and uncover the truth behind the kidnapping.
Throughout the game, the player explores the Commonwealth, a wasteland encompassing the remains of Boston and its surrounding areas. The journey involves interacting with various factions, both returning and new, such as the Brotherhood of Steel, the Institute, the Railroad, and the Minutemen, each with its own ideologies and goals. Among other smaller, but still significant factions. The player must navigate these alliances and conflicts to progress.
Key decisions taken throughout one's play-through, as with other Fallout titles, shapes the future of the Commonwealth.
¶ Modding Documentation
This section includes links to a few articles that may be useful to users who are new to modding or are looking to create mods for Fallout 4. To discover more content, use the search at the top of the page or the “Browse” button at the top of the left navigation panel to see the full list of articles in the “Fallout 4” section. You can help expand this wiki by using the “New Page” button at the top of the page. 
¶ Using Mods
¶ A. Key Terminologies and General Modding Knowledge

  Vanilla/Clean Game: A "vanilla" or "clean" game means that the game files are in their original state, just as they come from Bethesda when you download the game. Vanilla files are those that have not been altered unofficially in any way. Both modding and piracy alter the game files. Therefore, if you have previously modded the game, you should revert to a vanilla state or obtain a legitimate copy of the game from either Steam or GOG before modding your game.
  Plugins: A Plugin is how the game loads game data. Plugins define characteristics that the game loads at runtime. Fallout 4 plugins utilize the following file extensions;
      .esm: ‘Elder Scrolls Master.’ These are always loaded early by the game. The base game and DLCs are .esm files.
      .esp: ‘Elder Scrolls Plugin.’ Most mods use .esp files as their position in your load order is much more flexible than .esm or .esl files.
      .esl: ‘Elder Scrolls Light.’ Light plugins can contain fewer new records than other plugins, but many more can be loaded. They follow the same early-loading rules as .esm files. Creation Club content uses .esl files.
          .esl plugins are not supported in Fallout 4 VR, as the VR build is based on a game version that did not have ESL support. VR users are limited to .esm and .esp files.
        
      
    
  
  Plugin Flags: Plugin files can have various ‘flags’ set to change their behavior. The file name extensions above instruct the game to automatically enable some of these. Plugins with the .esm extension always have the ESM flag enabled. Plugins with the .esl extension always have both the ESM and ESL flags enabled. The ESM flag is what results in the early-loading behavior, among other things. A common example of plugin flagging is so-called ‘ESPFE’ plugins. These are .esp files with the ESL flag enabled. This combines the increased count benefits of Light plugins with the load order placement flexibility of a .esp file due to not having the ESM flag auto-enabled as with .esl files.
  Plugin Count Limits: There are two types of plugins: Full/Regular with a limit of 254, and Light with a limit of 4096. Any plugin with the ESL flag set is a Light plugin (these can have any file name extension). All others are Full/Regular plugins. Exceeding either limit will cause the game to crash-to-desktop (CTD).
  Plugin New Record Limits: Full/Regular plugins can add roughly 16 million new records to the game. Light plugins, in exchange for being able to load so many more, can add only 4095 new records. This is due to using more digits to store their load order position, but fewer to number new records.

¶ B. Setting up the Game for Modding
Before going further, ensure that the game is not installed in the Program Files folder to prevent Windows from interfering with mod functionality. Modding games installed in folders controlled by unrelated software can cause issues. These controlled folders include, but are not limited to, Documents, Program Files, Program Files (x86), Downloads, and any OneDrive folders. To avoid complications, consider moving your Steam library to a different folder outside of these locations.
Next, make sure to launch the game at least once and get to the main menu. This is required for the game to generate user files, typically referred to as INI’s or INI files. These are required for the game to function and thus are created on a vanilla copy of the game. These generated user files are independent of the game version so files generated on Next Gen will still work if you downgrade and go to the Old Gen version of the game.
Finally, decide which version of the game you will be modding. There are two main versions: 1.10.984.0 (Next Gen) and 1.10.163 (Old Gen). Once you have chosen the game version, you can proceed to select an appropriate mod manager.
To optimally prepare the game for modding, it is recommended, though not necessary, to downgrade from Next Gen to Old Gen and use the Backported Archive2 Support System (BASS) mod by Nukem. This approach allows access to the extensive catalog of mods available for Old Gen while maintaining compatibility with BA2 archives created with the Next Gen version of the Creation Kit, including Next Gen Creation Club Content.It is also recommended to install Creation Kit Platform Extended (CKPE) by perchik71 for various fixes and improvements to the Creation Kit.
¶ C. DLCs
While it is generally recommended to have all DLCs, you should at least obtain the two main ones, Nuka-World and Far Harbor. Missing out on DLCs will restrict your access to many mods. If you haven't bought the game yet, it is highly recommended to purchase the GOTY Edition, which includes all DLCs in a single package, allowing you to use mods that require them. The High Resolution Texture Pack, although free, should be avoided as it is known to cause texture bugs such as the infamous Black/Brown Face Bug; consider using a mod as an alternative.
¶ D. Choosing a Mod Manager
A Mod Manager is a utility tool designed to handle mods, enabling users to install, modify, and delete mods effortlessly. These managers also offer features that facilitate the modding process for specific games.
To select an effective Mod Manager, consider the following factors:

  Compatibility with the game in question.
  User-friendliness of the Mod Manager (a subjective measure).
  Availability of support and resources for troubleshooting issues with the Manager.

Below is a table highlighting the most notable mod managers for Fallout 4:
 

  
    
      
        
          Vortex Mod Manager
        
        Vortex is the official mod manager developed by Nexus Mods, supporting multiple games (See Supported Games).
      
    
    
      
        
          Mod Organizer 2
        
        MO2 is an alternative mod manager that supports Fallout 4 as well as many other games.
      
      
        Nexus Mod Manager
      
        NMM is an older mod manager originally developed by Nexus Mods. Though no longer supported by Nexus Mods, it is maintained by volunteers.
      
    
  

Other mod managers exist, but they are not included here due to their limited significance and to maintain brevity. It is advisable to try both Vortex and Mod Organizer 2 to determine which one best suits your preferences.
¶ E. Modding the Game
¶ 1. Should I use Collections/Wabbajacks or make my own modlist
After choosing a mod manager and the game version to mod, you need to decide whether to use an already curated list of mods or build a mod list yourself. A curated list allows you to install a set of mods that have been tested and patched to work together with minimal effort on your part, letting you quickly dive into the modded game experience. However, these lists may include mods that you don't like or want. Building your own mod list provides the freedom to choose exactly what you want but requires more effort, time, and patience. The result is a modding experience specifically tailored to your preferences.
If you chose Vortex as your mod manager, curated lists are referred to as Collections. For Mod Organizer 2, they are called Wabbajacks. Although they serve the same purpose, Collections and Wabbajacks are not interchangeable due to differences in the mod managers.
¶ 2. Getting started with conflict resolution
From this point forward, we will assume you have already installed your chosen mods, either through a curated mod list or by selecting them yourself. Since there is no singular "best" mod and suggestions are subjective, we won't be listing specific mods you should get. Instead, we will focus on how to ensure your mods work properly with minimal or no conflicts. Here are some tools you will likely use to resolve these conflicts;
 

  
    
      
        Tool Name
        	
      
    
    
      
        xEdit (FO4Edit)
        xEdit will be your primary tool for resolving conflicts. It provides an in-depth view of the data contained in each plugin in your load order and how they interact with one another. With xEdit, you can modify anything from minor details like a weapon's damage or its ammo type to more complex elements such as Leveled Lists or Worldspace Edits, making it a versatile tool for fine-tuning your mods.
      
      
        Creation Kit
        While xEdit allows for most of the edits you'd want, the Creation Kit (CK) offers advantages for resolving more advanced conflicts that xEdit can't handle. These include script or quest-related conflicts and worldspace or cell edits. The Creation Kit's 3D Renderer provides a real-time view of how your edits will appear in-game, making it far more efficient for visual adjustments, which xEdit lacks when dealing with in-game world edits. However, these advanced edits are typically for more experienced users. Newer modders should rely on pre-made patches available for the game to avoid potential complications.
      
      
        Wrye Bash
        Most of Wrye Bash's core functions have become redundant with the introduction of the ESL or Light Plugin system. However, it still offers a few unique features, particularly in the context of Fallout 4, that make it a valuable conflict-resolution tool. One key feature is the “Plugin Checker” utility, which scans your enabled plugins and provides a report on issues such as ITMs (Identical to Masters) or Deleted Navmesh References. Less experienced users can use this report to remove problematic mods or find patches, while more advanced users may attempt to repair the plugins themselves.
      
    
  

– WIP --
¶ ZZZ. Do's and Don'ts
Here is a concise table with some key do’s and don’ts for modding Fallout 4, though this is not an exhaustive list:
 

  
    
      
        Do's
        Don'ts
      
    
    
      
        Use a Mod Manager
        Don't mod the game manually unless you absolutely have to.
      
      
        Read Mod Descriptions and look at the requirements (if any) for the mod you're downloading
        	
      
    
      
        If not using curated lists, test mods in small batches instead of installing all the mods you want at once.
        If using curated lists, avoid adding extra mods unless you have enough experience with conflict resolution to handle potential issues.
      
    
  

¶ Creating Mods
Learn how to create your mods for Fallout 4. 
¶ Technical Information
 

  
    
      
        Game Information
        	
      
    
    
      
        DLCs
        
          
            Automatron
            Wasteland Workshop
            Far Harbor
            Contraptions Workshop
            Vault-Tec Workshop
            Nuka-World
            High-Resolution Texture Pack
          
        
      
      
        Steam App ID
        377160
      
      
        GOG App ID
        1998527297
      
      
        Xbox Game Pass ID
        BethesdaSoftworks.Fallout4-PCC3KLDKZBHNCZ
      
      
        Nexus Mods ID
        fallout4 (1151) 
      
    
  


 

  
    
      
        Modding Information
        	
      
    
    
      
        Engine
        Creation Engine
      
      
      
        Mod Managers
        
          
            Vortex
            Mod Organizer 2
            Nexus Mod Manager
          
        
      
    

¶ Useful Links

  Fallout 4 Mods at Nexus Mods
  Independent Fallout 4 Wiki
