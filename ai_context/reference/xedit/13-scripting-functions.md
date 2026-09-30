---
source_url: https://tes5edit.github.io/docs/13-Scripting-Functions.html
title: xEdit Scripting Functions
retrieved_utc: 2026-09-30T20:42:22Z
retrieved_by: fetch-agent
content_kind: upstream-documentation-verbatim
trust: upstream primary source, quoted verbatim, NOT paraphrased or summarized
---

  xEdit Scripting Functions | Tome of xEdit                 

![xEdit Icon](img/tes5edit-ico-blue.png)

# xEdit Scripting Functions

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

# xEdit Scripting Functions

## Contents...

•  [13.1 Description](#Description)

•  [13.2 Using the Delphi IDE to Edit TES5Edit Scripts](#UsingtheDelphiIDEtoEditTES5EditScripts)

•  [13.3 Instructions to get started editing xEdit scripts with Delphi](#InstructionstogetstartededitingxEditscriptswithDelphi)

•  [13.4 TES5Edit Global Variables](#TES5EditGlobalVariables)

•  [13.5 TES5Edit Scripting Functions](#TES5EditScriptingFunctions)

•  [13.6 Global functions](#Globalfunctions)

•  [13.7 IwbElement](#IwbElement)

•  [13.8 IwbContainer](#IwbContainer)

•  [13.9 IwbFile](#IwbFile)

•  [13.10 IwbMainRecord](#IwbMainRecord)

•  [13.11 IwbGroupRecord](#IwbGroupRecord)

•  [13.12 IwbResource](#IwbResource)

•  [13.13 Misc functions](#Miscfunctions)

•  [13.14 NIF functions](#NIFfunctions)

•  [13.15 DDS functions](#DDSfunctions)

•  [13.16 Script Structure](#ScriptStructure)

•  [13.17 Base Script Functions](#BaseScriptFunctions)

•  [13.18 Hotkeys](#Hotkeys)

•  [13.19 Script References](#ScriptReferences)

•  [13.20 Script User Interface](#ScriptUserInterface)

•  [13.21 Simple Script Sample](#SimpleScriptSample)

•  [13.22 Pascal implementation](#Pascalimplementation)

•  [13.23 xEdit extensions to JvInterpreter](#xEditextensionstoJvInterpreter)

•  [13.24 Unsupported language features](#Unsupportedlanguagefeatures)

•  [13.25 Unsupported operators](#Unsupportedoperators)

•  [13.26 Unsupported keywords](#Unsupportedkeywords)

•  [13.27 Unsupported classes and tools](#Unsupportedclassesandtools)

### 13.1 - Description

Work in progress: To become the future home of scripting functions for TES5Edit. If you make scripts for TES5Edit please contribute to this page.

TES5Edit implements a script engine based on Pascal syntax. The following table enumerates the functions exported by TES5Edit to the script engine that allows interacting with the editor's elements to perform various tasks such as finding records, fixing record conflicts, etc.

The information in the table is not complete so please contribute by explaining these functions, their uses and by fixing mistakes in this information.

### 13.2 - Using the Delphi IDE to Edit TES5Edit Scripts

As of TES5Edit version 3.2.1, there is a file in the `Edit Scripts` directory called [xEditAPI.pas](href=)

The contents of that file match what is published here. The xEditAPI.pas includes xEdit API declarations to be used for editing scripts using Delphi. With this file you can now edit xEdit scripts using Delphi. This gives you full IDE benefits like checking for warnings and errors before executing your script, as well as intellisense and code insights.

For example purposes in this documentation, we assume a user created xEdit script named `GreatScript.pas`. However, you can name your script almost anything. There are some limitations though, because the name of the script must match the unit declaration of the script, and unit names have limitations. See [Delphi Identifiers](href=)

### 13.3 - Instructions to get started editing xEdit scripts with Delphi

•  Download the free Delphi Starter edition, called RAD Studio (current version is 10.2) from [Embarcadero Delphi Starter](https://www.embarcadero.com/products/delphi/starter)

•  Create new console application project named `GreatScriptApp`

•  Add the files `xEditAPI.pas` and `GreatScript.pas` to the project (menu Project -> Add to project)

•  At the top of the script, modify or add the `unit` clause. The name of the unit must match exactly the filename of your script without the .pas extension.

•  Then add/update the `interface`, `implementation`, and `uses` clauses to your script below. Afterwards, the top of your script file should look like this:

  unit GreatScript;

  interface
  implementation
  uses xEditAPI, Classes, SysUtils, StrUtils, Windows;

•  You can add additional Delphi units to the `uses` clause needed, for example `IniFiles` if script works with them.

•  Check that project can be compiled `Ctrl+F9` and the same script can be applied in xEdit without errors.

•  While editing your script, before running it in xEdit, press `Ctrl+F9` in Delphi to compile and ensure that the code is valid.

•  You can also modify the GreatScriptApp file and have it run your xEdit script from Delphi by pressing `F9`. Make GreatScriptApp look something like this:

program GreatScriptApp;

  {$APPTYPE CONSOLE}

  {$R \*.res}

  uses
    Windows,
    Winapi.ShellApi,
    System.SysUtils,
    xEditAPI in 'C:\\Games\\FO4Edit 3.2\\Edit Scripts\\xEditAPI.pas';
    GreatScript in 'C:\\Games\\FO4Edit 3.2\\Edit Scripts\\GreatScript.pas',

  begin
    try
      ShellExecute(0, Nil, 'C:\\Games\\FO4Edit 3.2\\FO4Edit.exe', '-script:"GreatScript.pas" -nobuildrefs', 'C:\\Games\\FO4Edit 3.2', SW\_SHOWNORMAL);
    except
      on E: Exception do
        Writeln(E.ClassName, ': ', E.Message);
    end;
  end.

[Previous Section](#s_111) [Top of this Group](#s_112)

### 13.4 - TES5Edit Global Variables

These are predefined **read-only** variables that can be called at any time.

Name

Type

Description

Note

**DataPath**

String

Provides the file path to Skyrim's data folder as a String

**ProgramPath**

String

Provides the file path to Tes5edit's installation folder as a String

**ScriptsPath**

String

Provides the file path to Tes5Edit's 'Edit Scripts' folder as a String.

If launching TES5Edit via a .tes5pas file, ScriptsPath will change to the directory where the .te5pas file is located. (therefore if your script has any .pas file it is grabbing functions from, they also need to be in the that same directory.)

**FileCount**

Integer

Provides the number of loaded files in your current TES5Edit session

"Skyrim.Hardcoded.keep.this..." (aka. Skyrim.exe) is considered a file and is reflected in this variable.

**wbAppName**

String

Returns 'TES5','TES4','FNV','FO3'

**wbVersionNumber**

Integer

Returns xEdit version number.

[Previous Section](#s_112) [Top of this Group](#s_113)

### 13.5 - TES5Edit Scripting Functions

xEdit scripts only have access to a generic type called *IInterface*, which wraps around every object that xEdit returns. However, different types are used internally to classify different objects. To illustrate this with an example: files are coded as *IwbFile* objects, while forms are coded as *IwbMainRecord* objects. However, an xEdit script will only ever see IInterface objects, and any IInterface can be a IwbFile *or* an IwbMainRecord. Functions like *GetIsESM* can be called on any IInterface, but are designed to work with IwbFiles and will not produce a meaningful result for other types (i.e. *GetIsESM* would always return false for any other type).

The functions below are sorted by the internal types that they operate on. This is to make it easier to find certain functions and to make this page easier to maintain (because frankly, fixing up row colors on a massive table is just a big disincentive to even editing the page).

The relationships between internal types are as follows:

[IwbElement](#IwbElement)

+  IwbContainerBase

+  [IwbContainer](#IwbContainer)

| + IwbDataContainer

| | + IwbFileHeader

| | + IwbRecord

| | + [IwbGroupRecord](#IwbGroupRecord)

| | + [IwbMainRecord](#IwbMainRecord)

| | + [IwbSubRecord](#IwbSubRecord)

| |

| + [IwbFile](#IwbFile)

|

+  IwbContainerElementRef

[IwbResource](#IwbResource)

IwbResourceContainer

+  IwbBA2File

+  IwbBSAFile

+  IwbFolder

Other Types Used but Unknown

+  TwbDefType

+  TwbElementState

+  TwbElementType

+  TwbGridCell

+  TwbVector

+  TwbFastStringList

+  TGameResourceType

[Misc functions](#Misc_functions)

+  [DDS](#DDS_functions)

+  [NIF](#NIF_functions)

[Previous Section](#s_113) [Top of this Group](#s_114)

### 13.6 - Global functions

These functions can be called on anything and should return a meaningful result.

Function

Returns

Arguments

Description

**AddMessage**

asMessage: string

Pushes a line to TES5Edit's Information tab.

**Assigned**

boolean

aeElement: IwbElement

An extension to Delphi's native [Assigned](http://www.delphibasics.co.uk/RTL.asp?Name=Assigned) function: returns true if *aeElement* is not *Nil*, and returns false otherwise.

**ObjectToElement**

IInterface

akObject

If you have stored an IInterface inside of a TList or TStringList, you must call this function when retrieving the object from the list, i.e. `ObjectToElement(myList.Items[0])`.

**FileByIndex**

IwbFile

aiFile: integer

Returns a file by index. 0 is Fallout4.esm, 1 is Fallout4.exe, 2 is DLC or first mod loaded. See also: *FileCount*.

**FileByLoadOrder**

IwbFile

aiLoadOrder: integer

Returns a file by load order. 0 is Fallout4.esm, 1 is DLC or first mod loaded.

**FullPathToFilename**

string

asFilename: string

Returns the full path to the filename *asFilename*.

**EnableSkyrimSaveFormat**

As of xEdit 3.1.2, calling this function will corrupt saved plugins until xEdit is restarted.

**GetRecordDefNames**

akList: TStrings

Unverified: Modifies *akList* by adding entries based on the contents of the global *wbRecordDefs*.

**wbFilterStrings**

akListIn: TStrings;  
akListOut: TStrings;  
asFilter: String

Modifies *akListOut*, adding every entry in *akListIn* that contains the substring *asFilter*.

**wbRemoveDuplicateStrings**

akList: TStringList

Modifies *akList*, removing any duplicate entries that it contains.

[Previous Section](#s_114) [Top of this Group](#s_1141)

### 13.7 - IwbElement

These functions can be called on any IwbElement IInterface.

Function

Returns

Arguments

Description

**BaseName**

string

aeElement: IwbElement

Identical to *Name* except that it handles IwbFiles differently. *Name* will prepend a load order index (i.e. `[02] PluginName.esp`), while *BaseName* will not.

**BeginUpdate**

aeElement: IwbElement

For use on container elements only when performing a lot of operations with it like adding/removing children elements in batch. Needs to be paired with [EndUpdate](#EndUpdate)

    BeginUpdate(e);
    try
        // do things with e
    finally
        EndUpdate(e);
    end;

**BuildRef**

aeElement: IwbElement

Builds reference information for the element and all of its descendants. Note that this function will run even if reference information has already been built.

**CanContainFormIDs**

boolean

aeElement: IwbElement

Guaranteed to return *True* if the element can contain FormIDs, but not guaranteed to return *False* if it can't. This accesses an internal property, *CanContainFormIDs*, which the internal implementation of *BuildRef* uses to skip processing certain descendant elements.

**CanMoveDown**

boolean

aeElement: IwbElement

Returns true if the element is part of an array and can be moved further down using *MoveDown*.

**CanMoveUp**

boolean

aeElement: IwbElement

Returns true if the element is part of an array and can be moved further up using *MoveUp*.

**Check**

string

aeElement: IwbElement

Returns the error message produced when the "Check for Errors" functionality is run on *aeElement*; or else an empty string if no error is found.

**ClearElementState**

aeElement: IwbElement;  
aiState: TwbElementState

Manipulates the internal flags of an element, e.g. `ClearElementState(eElement, wsModified);`. See also: *GetElementState*, *SetElementState*.

**ContainingMainRecord**

IwbMainRecord

aeElement: IwbElement

Returns the main record that contains the element.

**DefType**

TwbDefType

aeElement: IwbElement

Returns the def-type of the element.

**DisplayName**

string

aeElement: IwbElement

Returns the display name of the element, if it has one; otherwise, this behaves identically to *Name*. See also: *BaseName*, *ShortName*.

**ElementAssign**

IwbElement

aeContainer: IwbContainer;  
aiIndex: integer;  
aeSource: IwbElement;  
abOnlySK: boolean

Copy the contents of one element into a container element, or create and append an element to a container.

aeContainer

Destination element.

aiIndex

Where to place the new element, if the destination is an array. Specify *HighInteger* to append. Specify *LowInteger* or a negative value to add to non-arrays.

aeSource

Element to copy from. Use *Nil* to create a blank element of the appropriate type.

abOnlySK

Sorted Key Only; : Only apply to elements participating in container sorting, for internal xEdit usage. Use False.

Sample: there is a script to copy VMAD subrecords "Skyrim - Copy VMAD subrecord.pas"

**ElementType**

TwbElementType

aeElement: IwbElement

Returns the type of the element. This is one of the following values: etFile, etMainRecord, etGroupRecord, etSubRecord, etSubRecordStruct, etSubRecordArray, etSubRecordUnion, etArray, etStruct, etValue, etFlag, etStringListTerminator,etUnion, etStructChapter.

**EndUpdate**

aeElement: IwbElement

For use on container elements only when performing a lot of operations with it like adding/removing children elements in batch. Needs to be paired with [BeginUpdate](#BeginUpdate)

    BeginUpdate(e);
    try
        // do things with e
    finally
        EndUpdate(e);
    end;

**EnumValues**

string

aeElement: IwbElement

If *aeElement* is a set of named enum values, this function returns the names of any values that have been set, separated with spaces.

**Equals**

boolean

aeElement1: IwbElement;  
aeElement2: IwbElement

Compares two elements by their ElementID. This is sometimes necessary, as different IInterface variables pointing to the same element don't always compare properly when using the `=` operator.

**FlagValues**

string

aeElement: IwbElement

If *aeElement* is a set of flags, this function returns the names of all set flags, separated with spaces.

**FullPath**

string

aeElement: IwbElement

Returns the full path to the element, going all the way down to its containing file. See also: *Path*, *PathName*.

**GetContainer**

IwbContainer

aeElement: IwbElement

Returns the element's container.

**GetEditValue**

string

aeElement: IwbElement

Returns a string representation of the element's value. See also: *SetEditValue*, *GetElementEditValues*, *SetElementEditValues*.

**GetElementState**

TwbElementState

aeElement: IwbElement;  
aiState: TwbElementState

Checks the internal flags of an element. See also: *ClearElementState*, *SetElementState*.

**GetFile**

IwbFile

aeElement: IwbElement

Returns the file that contains the element.

**GetNativeValue**

variant

aeElement: IwbElement

Returns the element's value. See also: *SetNativeValue*, *GetElementNativeValues*, *SetElementNativeValues*.

**IsEditable**

boolean

aeElement: IwbElement

Returns true if the record can be edited. In some cases, xEdit will block edits to files like Skyrim.esm.

**IsInjected**

boolean

aeElement: IwbElement

Returns true if the element is an injected record.

**LinksTo**

IwbElement

aeElement: IwbElement

Obtains the referenced element. Not to be confused with ReferencedBy Elements. Call this function on any container element (etSubRecord) to get the iwbMainRecord of that form. (Ex: Calling LinksTo() on any 'LNAM - FormID' subRecord found in a FormID List will return the IwbMainRecord of that record).

**MarkModifiedRecursive**

aeElement: IwbElement

Marks the element and all of its descendants as modified. This forces xEdit to serialize them.

**MoveDown**

aeElement: IwbElement

If the element is part of an array, this function moves it down by one slot. See also: *CanMoveDown*.

**MoveUp**

aeElement: IwbElement

If the element is part of an array, this function moves it up by one slot. See also: *CanMoveUp*.

**Name**

string

aeElement: IwbElement

Returns the name of the element, if it has one. If *aeElement* is an IwbFile or certain linds of IwbMainRecords, *Name* will return a "pretty" name, while *BaseName* or *ShortName* will return a more basic string. See also: *DisplayName*.

**Path**

string

aeElement: IwbElement

Returns the *path component* of *aeElement* — that is, *one single piece* of the path that *FullPath* would return. You could use this when manually constructing a path to supply to *ElementByPath*. See also (and don't confuse with): *FullPath*, *PathName*.

**PathName**

string

aeElement: IwbElement

Similar to *FullPath* except that names in the path are prefixed with brackets, to uniquely identify each element's unique position among its siblings (see *IndexOf*).

Example: `\[02] neromancer.esp\[7] Worldspace\[1] World Children\[1] Children of 00000D74\[0] Persistent\[2] [REFR:00100452]`

**Remove**

aeElement: IwbElement

Removes the element from its file.

**ReportRequiredMasters**

aeElement: IwbElement;  
akListOut: TStrings;  
akUnknown1: boolean;  
akUnknown2: boolean

Checks which master files *aeElement* depends on, and adds their filenames to *akListOut*. First boolean is Recursive to go over children elements if it is a container, second is Initial which is false by default.

**SetEditValue**

string

aeElement: IwbElement;  
asValue: string

Sets the element's value to one that matches the string representation passed in. See also: *GetEditValue*, *GetElementEditValues*, *SetElementEditValues*.

**SetElementState**

TwbElementState

aeElement: IwbElement;  
aiState: TwbElementState

Manipulates the internal flags of an element. Returns the value prior to modification. See also: *ClearElementState*, *GetElementState*.

**SetNativeValue**

string

aeElement: IwbElement;  
avValue: variant

Sets the element's value. See also: *GetNativeValue*, *GetElementNativeValues*, *SetElementNativeValues*.

**SetToDefault**

aeElement: IwbElement

Resets the element's data and adds missing fields if any

**ShortName**

string

aeElement: IwbElement

Generally the same as *Name* unless *aeElement* is a reference, cell, or similar record. *Name* will return detailed information for those records, while *ShortName* will return the signature and FormID in the format `[XXXX:01234567]`.

**SortKey**

string

aeElement: IwbElement

Returns a string unique to the element entered. This can be used for sorting elements or for comparing them; for example, you could compare the SortKey for two elements in records which override each other to see if they are different from each other.

**wbCopyElementToFile**

IwbElement

aeElement: IwbElement;  
aeFile: IwbFile;  
abAsNew: boolean;  
abDeepCopy: boolean

Copies an IwbMainRecord, IwbGroupRecord, or IwbContainer to the specified file. The *abAsNew* boolean controls whether or not you're copying the record as an override record. Returns the copied element.

**wbCopyElementToFileWithPrefix**

IwbElement

aeElement: IwbElement;  
aeFile: IwbFile;  
abAsNew: boolean;  
abDeepCopy: boolean;  
aPrefixRemove;  
aPrefix;  
aSuffix: string

Details unknown. Returns the copied element.

**wbCopyElementToRecord**

IwbElement

aeElement: IwbElement;  
aeRecord: IwbMainRecord;  
abAsNew: boolean;  
abDeepCopy: boolean

Copies an element to a record, e.g. the "Conditions" element on a [Constructible Object (COBJ)](https://www.creationkit.com/index.php?title=Constructible_Object) record or a faction from an [ActorBase (NPC\_)](https://www.creationkit.com/index.php?title=ActorBase) record. Returns the copied element.

[Previous Section](#s_1141) [Top of this Group](#s_1142)

### 13.8 - IwbContainer

Function

Returns

Arguments

Description

**Add**

IwbElement

aeContainer: IwbContainer;  
asNameOrSignature: string;  
abSilent: boolean

Creates a child element with the name-or-signature *asNameOrSignature* in *aeContainer* if no such child already exists; otherwise, marks the existing child as modified. Returns the created or existing element.

**AddElement**

aeContainer: IwbContainer;  
aeElement: IwbElement

Adds *aeElement* as a child of *aeContainer*. Throws an error if *aeElement* already has a container.

**AdditionalElementCount**

integer

aeContainer: IwbContainer

Returns the number of "fake" elements xEdit adds before the "Record Header". For references it shows "Cell" for example. This getter accesses an internal function used internally for imposing some order on the sub-elements; it checks whether this element "counts," and if so, how many times. Seems to return 1 or 2 for (main?) records, and 0 for record fields (sub-records).

**ContainerStates**

byte

aeContainer: IwbContainer

Returns the internal container flags for *aeContainer* (e.g. whether it's initialized, or whether it has had references built) as a bitmask. Refer to "Worldspace browser.pas" for a usage example.

**ElementByIndex**

IwbElement

aeContainer: IwbContainer;  
aiIndex: integer

Returns the *aiIndex*\-th child element in *aeContainer*. See also: *ElementCount*.

**ElementByName**

IwbElement

aeContainer: IwbContainer;  
asName: string

Searches *aeContainer* for the child element with name *asName*, and returns the found element or *Nil*. See also: *ElementExists*.

**ElementByPath**

IwbElement

aeContainer: IwbContainer;  
asPath: string

Searches *aeContainer* for the descendant element specified by path *asPath*, and returns the found element or *Nil*.

**ElementBySignature**

IwbElement

aeContainer: IwbContainer;  
asSignature: string

Searches *aeContainer* for the child element with signature *asSignature*, and returns the found element or *Nil*.

**ElementCount**

integer

aeContainer: IwbContainer

Returns the number of child elements in *aeContainer*. See also: *ElementByIndex*.

**ElementExists**

boolean

aeContainer: IwbContainer;  
asName: string

Returns true if *aeContainer* as a child element whose name is *asName*. See also: *ElementByName*.

**GetElementEditValues**

string

aeContainer: IwbContainer;  
asPath: string

Finds the element within *aeContainer* specified by *asPath*, and returns a string representation of its value.

**GetElementNativeValues**

variant

aeContainer: IwbContainer;  
asPath: string

Finds the element within *aeContainer* specified by *asPath*, and returns its value.

**IndexOf**

integer

aeContainer: IwbContainer;  
aeChild: IwbElement

Returns the index of *aeChild* in *aeContainer*, or -1 if *aeChild* is not a child element of *aeContainer*.

**InsertElement**

aeContainer: IwbContainer;  
aiPosition: Integer;  
aeElement: IwbElement

Inserts *aeElement* as a child of *aeContainer* at the specified position.

**IsSorted**

boolean

aeContainer: IwbSortableContainer

Checks whether xEdit always keeps *aeContainer* sorted. If so, this function will return *True*, and calling *CanMoveUp* and *CanMoveDown* on child elements will always return *False*.

**LastElement**

IwbElement

aeContainer: IwbContainer

Returns the last child element in *aeContainer*, or *Nil* if there are no child elements.

**RemoveByIndex**

IwbElement

aeContainer: IwbContainer;  
aiIndex: integer;  
abMarkModified: boolean

Removes the *aiIndex*\-th child from *aeContainer*, and returns it.

**RemoveElement**

IwbElement

aeContainer: IwbContainer;  
avChild: variant

Removes *avChild* from *aeContainer* and returns the removed element. The *avChild* argument can be: the index of an element to remove from an array container; the mame or signature of an element to remove; or an IwbElement to remove.

**ReverseElements**

aeContainer: IwbContainer

Reverses the order of the child elements in *aeContainer*.

**SetElementEditValues**

aeContainer: IwbContainer;  
asPath: string;  
asValue: string

Finds the element within *aeContainer* specified by *asPath*, and sets its value based on the string representation *asValue*.

**SetElementNativeValues**

aeContainer: IwbContainer;  
asPath: string;  
asValue: variant

Finds the element within *aeContainer* specified by *asPath*, and sets its value to *asValue*.,/td>

[Previous Section](#s_1142) [Top of this Group](#s_1143)

### 13.9 - IwbFile

Function

Returns

Arguments

Description

**AddMasterIfMissing**

aeFile: IwbFile;  
asMasterFilename: string

Adds the specified file as a master for *aeFile*, if it isn't already a master.

**AddNewFileName**

aeFile: IwbFile

FileName: String  
(optional) ESLFlag: Boolean  

Creates a new, empty plugin using FileName as the name in the game's plugin folder (Data) and adds it to the end of the plugins list. if applicable, the ESL flag can be set.

**AddNewFile**

aeFile: IwbFile

(optional) ESLFlag: Boolean  

Creates a new, empty plugin in the game's plugin folder (Data) and adds it to the end of the plugins list. if applicable, the ESL flag can be set.

**CleanMasters**

aeFile: IwbFile

Appears to find unnecessary files in *aeFile*'s master list and remove them, updating all form indices accordingly. Don't confuse this within "cleaning master files" as in "removing ITMs and UDRs from official DLCs." This function is used in "Skyrim - Book Covers Patch.pas".

**FileFormIDtoLoadOrderFormID**

cardinal

aeFile: IwbFile; aiFormID: cardinal

Converts *aiFormID* from a FormID relative to *aeFile*'s master list (like that returned by *FixedFormID*) to a load order-relative FormID (like that returned by *FormID*). See also: *LoadOrderFormIDtoFileFormID*.

**FileWriteToStream**

aeFile: IwbFile;  
akOutStream: TStream

Writes the contents of *aeFile* to *akOutStream*. Used in "SaveAs.pas" to allow a user to save a loaded file under a new name; that script creates a TFileStream object and uses this function to write to it.

**GetFileName**

string

aeFile: IwbFile

Returns *aeFile*'s filename.

**GetIsESM**

boolean

aeFile: IwbFile

Returns *True* if *aeFile* is flagged as an ESM. See also: *SetIsESM*.

**GetLoadOrder**

integer

aeFile: IwbFile

Returns *aeFile*'s index in the load order, or -1 if called on something that is not an IwbFile.

**GetNewFormID**

cardinal

aeFile: IwbFile

Returns a new FormID, the same way that `Add(..., ..., True)` does.

**GroupBySignature**

IwbGroupRecord

aeFile: IwbFile;  
asSignature: string

If *aeFile* has a top-level group with the specified signature, that group is returned.

**HasGroup**

boolean

aeFile: IwbFile;  
asSignature: string

Returns *True* if *aeFile* contains a top-level group with the specified signature.

**HasMaster**

boolean

aeFile: IwbFile;  
asMasterFilename: string

Returns *True* if *aeFile* has a file with the name *asMasterFilename* as a master.

**LoadOrderFormIDtoFileFormID**

cardinal

aeFile: IwbFile; aiFormID: cardinal

Converts *aiFormID* from a load order-relative FormID (like that returned by *FormID*) to a FormID relative to *aeFile*'s master list (like that returned by *FixedFormID*). See also: *FileFormIDtoLoadOrderFormID*.

**MasterByIndex**

IwbFile

aeFile: IwbFile;  
aiIndex: integer

Returns the *aiIndex*\-th master file for *aeFile*.

**MasterCount**

cardinal

aeFile: IwbFile

Returns the number of master files that *aeFile* has.

**RecordByEditorID**

IwbMainRecord

aeFile: IwbFile;  
asEditorID: string

Returns the [Magic Effect (MGEF)](https://www.creationkit.com/index.php?title=Magic_Effect) or [Setting (GMST)](https://www.creationkit.com/index.php?title=Category:Settings) record in *aeFile* that has the specified EditorID. For all other record types, use something like `MainRecordByEditorID(GroupBySignature(f, 'ECZN'), 'RandomEncounterZone1')`.

**RecordByFormID**

IwbMainRecord

aeFile: IwbFile;  
aiFormID: integer;  
abAllowInjected: boolean

Returns the main record in *aeFile* that has the specified FormID, or *Nil* if no records match. The FormID must be local to the file (see *FixedFormID*).

**RecordByIndex**

IwbMainRecord

aeFile: IwbFile;  
aiIndex: integer

Returns the *aiIndex*\-th record in *aeFile*.

**RecordCount**

cardinal

aeFile: IwbFile

Returns the number of records that *aeFile* has.

**SetIsESM**

aeFile: IwbFile;  
abFlag: boolean

Modifies the ESM flag for *aeFile*. See also: *GetIsESM*.

**SortMasters**

aeFile: IwbFile

Attempts to sort the masters for *aeFile* by their place in the current load order.

[Previous Section](#s_1143) [Top of this Group](#s_1144)

### 13.10 - IwbMainRecord

Function

Returns

Arguments

Description

**BaseRecord**

IwbMainRecord

aeRecord: IwbMainRecord

If *aeRecord* is a [Reference](https://www.creationkit.com/index.php?title=Reference), this function returns the IwbMainRecord of its base form. Otherwise, the function returns *Nil*.

**BaseRecordID**

cardinal

aeRecord: IwbMainRecord

Appears to return the load order-relative FormID of *aeRecord*.

**ChangeFormSignature**

aeRecord: IwbMainRecord;  
asNewSignature: string

Changes *aeRecord*'s signature to *asNewSignature*. No other information is modified.

**ChildGroup**

IwbGroupRecord

aeRecord: IwbMainRecord

Returns the group that *aeRecord* contains, if any. For example, a [Worldspace(WRLD)](https://www.creationkit.com/index.php?title=Worldspace) record will be followed by a GRUP containing the worldspace's [Cell (CELLs)](https://www.creationkit.com/index.php?title=Cell), and you would use this function to retrieve that group.

**CompareExchangeFormID**

boolean

aeRecord: IwbMainRecord;  
aiOldFormID: cardinal;  
aiNewFormID: cardinal

Attempts to change *aeRecord*'s FormID from *aiOldFormID* to *aiNewFormID*, and returns *True* if the operation succeeds.

**EditorID**

string

aeRecord: IwbMainRecord

Returns the record's EditorID.

**FixedFormID**

cardinal

aeRecord: IwbMainRecord

Returns the local FormID of the record. Local records will not have a load order prefix (i.e. 0x00FFFFFF), and overrides will have a prefix relative to the record's file's masters. See also: *FormID*, *GetLoadOrderFormID*.

**FormID**

cardinal

aeRecord: IwbMainRecord

Returns the record's FormID. See also: *FixedFormID*, *GetLoadOrderFormID*.

**GetFormVCS1**

cardinal

aeRecord: IwbMainRecord

Returns the value of the Version Control Info 1 field. See also: *SetFormVCS1*.

**GetFormVCS2**

cardinal

aeRecord: IwbMainRecord

Returns the value of the Version Control Info 2 field. See also: *SetFormVCS2*.

**GetFormVersion**

cardinal

aeRecord: IwbMainRecord

Get Form Version field from the record's header. See also: *SetFormVersion*.

**GetGridCell**

TwbGridCell

aeRecord: IwbMainRecord

If *aeRecord* is an exterior [Cell (CELL)](https://www.creationkit.com/index.php?title=Cell), this function will return its grid coordinates as a TwbGridCell; you can access the coordinates by checking `returnValue.x` and `returnValue.y`.

**GetIsDeleted**

boolean

aeRecord: IwbMainRecord

Checks the record's "deleted" flag. See also: *SetIsDeleted*.

**GetIsInitiallyDisabled**

boolean

aeRecord: IwbMainRecord

Checks the record's "initially disabled" flag. See also: *SetIsInitiallyDisabled*.

**GetIsPersistent**

boolean

aeRecord: IwbMainRecord

Checks the record's "persistent" flag. See also: *SetIsPersistent*.

**GetIsVisibleWhenDistant**

boolean

aeRecord: IwbMainRecord

Checks the record's "visible when distant" flag. See also: *SetIsVisibleWhenDistant*.

**GetLoadOrderFormID**

cardinal

aeRecord: IwbMainRecord

Returns the record's FormID relative to the current load order. See also: *FixedFormID*, *SetLoadOrderFormID*.

**GetPosition**

TwbVector

aeRecord: IwbMainRecord

If *aeRecord* is a [Reference](https://www.creationkit.com/index.php?title=Reference) (or a subtype, like ACHR), this function will return its position.

**GetRotation**

TwbVector

aeRecord: IwbMainRecord

If *aeRecord* is a [Reference](https://www.creationkit.com/index.php?title=Reference) (or a subtype, like ACHR), this function will return its rotation.

**HasPrecombinedMesh**

boolean

aeRecord: IwbMainRecord

Checks whether *aeRecord* is a Fallout 4 [Reference](https://www.creationkit.com/index.php?title=Reference) that has precombined mesh data generated. See also: *PrecombinedMesh*.

**HighestOverrideOrSelf**

IwbMainRecord

aeRecord: IwbMainRecord  
aiMaxIndex: integer

if *aeRecord* is overridden, returns the highest override. otherwise, returns *aeRecord* See also: *WinningOverride*.

**IsMaster**

boolean

aeRecord: IwbMainRecord

Returns *True* if *aeRecord* is a master, and false if it is an override or not an IwbMainRecord. See also: *Master*, *MasterOrSelf*.

**IsWinningOverride**

boolean

aeRecord: IwbMainRecord

Returns *True* if *aeRecord* is the last loaded override for its master. See also: *Master*, *MasterOrSelf*.

**Master**

IwbMainRecord

aeRecord: IwbMainRecord

**MasterOrSelf**

IwbMainRecord

aeRecord: IwbMainRecord

If *aeRecord* is an override, the function returns the master record that it overrides. Otherwise, the function returns *aeRecord* itself. See also: *IsMaster*, *IsWinningOverride*.

**OverrideByIndex**

IwbMainRecord

aeRecord: IwbMainRecord;  
aiIndex: integer

Returns the *aiIndex*\-th override of *aeRecord*.

**OverrideCount**

cardinal

aeRecord: IwbMainRecord

Returns the number of records that override *aeRecord*.

**PrecombinedMesh**

string

aeRecord: IwbMainRecord

Returns the path to *aeRecord*'s precombined mesh file, if *aeRecord* is a Fallout 4 [Reference](https://www.creationkit.com/index.php?title=Reference) that could have that data (i.e. not a placed actor). See also: *HasPrecombinedMesh*.

**ReferencedByIndex**

IwbMainRecord

aeRecord: IwbMainRecord;  
aiIndex: integer

Returns the *aiIndex*\-th record that references *aeRecord*.

**ReferencedByCount**

cardinal

aeRecord: IwbMainRecord

Returns the number of records that refer to *aeRecord*.

**SetEditorID**

string

aeRecord: IwbMainRecord;  
asEditorID: string

Sets the record's EditorID, and then returns it.

**SetFormVersion**

aeRecord: IwbMainRecord;  
aiVersion: cardinal

Set Form Version field for the record's header. See also: *GetFormVersion*.

**SetIsDeleted**

boolean

aeRecord: IwbMainRecord;  
abFlag: boolean

Modifies the record's "deleted" flag. See also: *GetIsDeleted*.

**SetIsInitiallyDisabled**

boolean

aeRecord: IwbMainRecord;  
abFlag: boolean

Modifies the record's "initially disabled" flag. See also: *GetIsInitiallyDisabled*.

**SetIsPersistent**

boolean

aeRecord: IwbMainRecord;  
abFlag: boolean

Modifies the record's "persistent" flag. See also: *GetIsPersistent*.

**SetIsVisibleWhenDistant**

boolean

aeRecord: IwbMainRecord;  
abFlag: boolean

Modifies the record's "visible when distant" flag. See also: *GetIsVisibleWhenDistant*.

**SetLoadOrderFormID**

cardinal

aeRecord: IwbMainRecord;  
aiFormID: cardinal;

Modifies the record's FormID, with the specified ID relative to the current load order. See also: *GetLoadOrderFormID*.

**SetFormVCS1**

aeRecord: IwbMainRecord;  
aiValue: cardinal

Modifies the Version Control Info 1 field. See also: *GetFormVCS1*.

**SetFormVCS2**

aeRecord: IwbMainRecord;  
aiValue: cardinal

Modifies the Version Control Info 2 field. See also: *GetFormVCS2*.

**Signature**

string

aeRecord: IwbMainRecord

Returns the record's signature, a four-character code such as [ActorBase(NPC\_)](https://www.creationkit.com/index.php?title=ActorBase) or [Topic(DIAL)](https://www.creationkit.com/index.php?title=Topic).

**UpdateRefs**

aeRecord: IwbMainRecord

Appears to be the same as *BuildRef*, except that it aborts if references are already in the middle of being built.

**WinningOverride**

IwbMainRecord

aeRecord: IwbMainRecord

Returns the last loaded override for *aeRecord*. See also: *HighestOverrideOrSelf*.

[Previous Section](#s_1144) [Top of this Group](#s_1145)

### 13.11 - IwbGroupRecord

Function

Returns

Arguments

Description

**ChildrenOf**

IwbMainRecord

aeGroup: IwbGroupRecord

If *aeGroup* is a child group, this function returns the main record that it is associated with. For example, a [Dialogue Topic (DIAL)](https://www.creationkit.com/index.php?title=Topic) is followed by a group (GRUP) that contains its [Infos (INFO)](https://www.creationkit.com/index.php?title=Topic_Info) and passing that GRUP to this function would retrieve the DIAL. [Cells (CELL)](https://www.creationkit.com/index.php?title=Cell) and [Worldspaces (WRLD)](https://www.creationkit.com/index.php?title=Worldspace) have their contents set up similarly to Dialogue Topics, so this function will work with them as well.

**FindChildGroup**

IwbGroupRecord

aeGroup: IwbGroupRecord;  
aiType: integer;  
aeMainRecord: IwbMainRecord;  

Finds the group record inside another group. The *aiType* value should match the group-type values used in [the file format](href=). The "Worldspace browser.pas" script uses `FindChildGroup(ChildGroup(cell), 9, cell);` to get the "Temporary" group within a CELL.

**GroupLabel**

cardinal

aeGroup: IwbGroupRecord

Returns the raw group label, as specified in [the file format](href=).

**GroupType**

integer

aeGroup: IwbGroupRecord

Returns the raw group type, as specified in [the file format](http://en.uesp.net/wiki/Tes5Mod:Mod_File_Format#Groups).

**MainRecordByEditorID**

IwbMainRecord

aeGroup: IwbGroupRecord;  
asEditorID: string

Searches *aeGroup* for a main record whose EditorID is *asEditorID* and returns the matching record or *Nil*. This is not a performant function.

[Previous Section](#s_1145) [Top of this Group](#s_1146)

### 13.12 - IwbResource

These functions are used in "Assets browser.pas", "Assets manager.pas", and "Skyrim - List used scripts.pas".

Function

Returns

Arguments

Description

**ResourceContainerList**

akContainers: TwbFastStringList

Fills *akContainers* with the full filenames (directory + name) of all loaded BSA and BA2 files, as well as the name of the Data directory. *akContainers* can be a TwbFastStringList or a TStringList.

**ResourceCopy**

asContainerName: string;  
asFilename: string;  
asPathOut: string

Retrieves the resource named *asFilename* from the resource container named *asContainerName* (see *ResourceContainerList*), and saves that resource to the specified file path *asPathOut*. The "Assets browser.pas" script uses this to let users extract a resource from a BSA/BA2.

**ResourceCount**

cardinal

asFilename: string;  
akContainers: TStrings

Fills *akContainers* with a list of the loaded containers (BSA, BA2, Data directory) that a file named *asFilename* appears in. The "Assets browser.pas" script uses this to allow users to decide which version of a file to view, when the file is overridden at least once within their load order.

**ResourceExists**

boolean

asFilename: string

Checks whether any loaded container has a file with the specified name.

**ResourceList**

asContainerName: string;  
akContainers: TStrings

Accesses the container with the full filename *asContainerName* (see *ResourceContainerList*), and adds a list of all contained filenames to *akContainers*. Note that added entries are unsorted, and there may be duplicates among them.

**ResourceOpenData**

TBytesStream

asContainerName: string;  
asFilename: string

*asFilename* should be formatted similar to the other Resource-oriented xEdit scripts. *asContainerName* should be filled with a string generated by the function *ResourceContainerList*. The *ResourceOpenData* function should only be used in conjunction with *NifTextureList*, as *ResourceCopy* removes any other need for this function.

[Previous Section](#s_1146) [Top of this Group](#s_1147)

### 13.13 - Misc functions

Function

Returns

Arguments

Description

**LocalizationGetStringsFromFile**

asFilename: string;  
akListOut: TStrings

**wbAlphaBlend**

boolean

akDestinationDeviceContext: unknown;  
aiDestinationX: integer;  
aiDestinationY: integer;  
aiDestinationWidth: integer;  
aiDestinationHeight: integer;  
akSourceDeviceContext: unknown;  
aiSourceX: integer;  
aiSourceY: integer;  
aiSourceWidth: integer;  
aiSourceHeight: integer;  
aiAlpha: integer

A wrapper for *Windows.AlphaBlend* which returns its result.

**wbBlockFromSubBlock**

TwbGridCell

akSubBlock: TwbGridCell

See also: *wbPositionToGridCell*, *wbSubBlockFromGridCell*, *wbGridCellToGroupLabel*, *wbIsInGridCell*.

**wbCRC32Data**

cardinal

akData: TBytes

See also: *wbCRC32File*, *wbSHA1Data*, *wbSHA1File*, *wbMD5Data*, *wbMD5File*.

**wbCRC32File**

cardinal

asFilename: string

See also: *wbCRC32Data*, *wbSHA1Data*, *wbSHA1File*, *wbMD5Data*, *wbMD5File*.

**wbCRC32Resource**

cardinal

asContainerName: string; asFileName: string

**wbFindREFRsByBase**

aeREFR: IwbMainRecord;  
asSignatures: string;  
aiFlags: integer;  
akOutList: TList

Searches for sibling records to *aeREFR* whose base records' signatures match *asSignatures*, and adds them to *akOutList*. Further filtering can be done with *aiFlags*: specify 1 to exclude deleted references, 2 to exclude initially disabled references, and 4 to exclude references that have an enable parent.

**wbFlipBitmap**

akBitmap: TBitmap;  
aiAxes: integer

Flips the image data contained in *akBitmap* based on the specified axes. Specify 1 to flip horizontally, 2 to flip vertically, or 0 to flip on both axes.

**wbGetSiblingRecords**

aeRecord: IwbElement;  
asSignatures: string;  
abIncludeOverrides: boolean;  
akOutList: TList

Adds sibling records of *aeRecord* to *akOutList* if their signatures match *asSignatures*. If *abIncludeOverrides* is not *True*, then overrides will not be included in the result.

**wbGridCellToGroupLabel**

cardinal

akGridCell: TwbGridCell

Returns an integer of the format 0xXXXXYYYY. See also: *wbBlockFromSubBlock*, *wbPositionToGridCell*, *wbIsInGridCell*, *wbSubBlockFromGridCell*.

**wbIsInGridCell**

boolean

akPosition: TwbVector;  
akGridCell: TwbGridCell

See also: *wbBlockFromSubBlock*, *wbGridCellToGroupLabel*, *wbPositionToGridCell*, *wbSubBlockFromGridCell*.

**wbMD5Data**

cardinal

akData: TBytes

See also: *wbCRC32Data*, *wbCRC32File*, *wbMD5File*, *SHA1Data*, *wbSH1Data*.

**wbMD5File**

cardinal

asFilename: string

Calculation time is about 2.5 times longer than CRC32. See also: *wbCRC32Data*, *wbCRC32File*, *wbMD5Data*, *SHA1Data*, *wbSH1Data*.

**wbNormalizeResourceName**

string

asResourceName: string; akResourceType: TGameResourceType

*akResourceType* can be any of the following values: *resMesh*, *resTexture*, *resSound*, *resMusic*.

**wbPositionToGridCell**

TwbGridCell

akPosition: TwbVector

Converts *akPosition* to grid coordinates. In practice, this is done by dividing the physical coordinates by 4096, the lateral length and width of a cell. See also: *wbBlockFromSubBlock*, *wbGridCellToGroupLabel*, *wbIsInGridCell*, *wbSubBlockFromGridCell*.

**wbSHA1Data**

cardinal

akData: TBytes

See also: *wbCRC32Data*, *wbCRC32File*, *SHA1File*, *wbMD5Data*, *wbMD5File*.

**wbSHA1File**

cardinal

asFilename: string

Calculation time is about two times longer than CRC32. See also: *wbCRC32Data*, *wbCRC32File*, *SHA1Data*, *wbMD5Data*, *wbMD5File*.

**wbStringListInString**

integer

akList: TStringList; asSubstring: string

Checks if any of the strings in *akList* contains *asSubstring*. Returns the index of the first matching entry, or -1. Checks are case-insensitive.

**wbSubBlockFromGridCell**

TwbGridCell

akGridCell: TwbGridCell

See also: *wbBlockFromSubBlock*, *wbGridCellToGroupLabel*, *wbIsInGridCell*, *wbPositionToGridCell*.

[Previous Section](#s_1146) [Top of this Group](#s_1147)

### 13.14 - NIF functions

Function

Returns

Arguments

Description

**NifBlockList**

boolean

akData: TBytes;  
akListOut: TStrings

Retrieves block information from the NIF file in *akData*, and adds it to *akListOut*. Each added index in *akListOut* will match up with a string key of the form "BlockName=BlockType" and (as an object) a pointer to the NIF block's index number. Returns *True* if the operation succeeded.

**NifTextureList**

boolean

akData: TBytes;  
akListOut: TStrings

Searches the NIF file in *akData* for all texture paths, and adds them to *akListOut*. Returns *True* if the operation succeeded.

**NifTextureListResource**

boolean

akData: variant;  
akListOut: TStrings

Searches the NIF file in *akData* for all texture paths, and adds them to *akListOut*. Returns *True* if the operation succeeded.

**NifTextureListUVRange**

boolean

akData: TBytes;  
afUVRange: Single;  
akListOut: TStrings

Searches the NIF file in *akData* for all texture paths, and adds them to *akListOut*. Textures are only added if none of the relevant NiTriShape's UV sets have UVs greater than *afUVRange* or less than *\-afUVRange*. Returns *True* if the operation succeeded.

[Previous Section](#s_1148) [Top of this Group](#s_11481)

### 13.15 - DDS functions

Function

Returns

Arguments

Description

**wbDDSStreamToBitmap**

boolean

akStream: TStream;  
akBitmapOut: TBitmap

Modifies *akBitmapOut* to contain the DDS information sourced from *akStream*. Returns *True* if the operation succeeds.

**wbDDSDataToBitmap**

boolean

akData: TBytes;  
akBitmapOut: TBitmap

Modifies *akBitmapOut* to contain the DDS information sourced from *akData*. Returns *True* if the operation succeeds.

**wbDDSResourceToBitmap**

boolean

akUnknown;  
akBitmapOut: TBitmap

Modifies *akBitmapOut* to contain the DDS information sourced from the resource *akUnknown*. Returns *True* if the operation succeeds.

[Previous Section](#s_11481) [Top of this Group](#s_11482)

### 13.16 - Script Structure

### 13.17 - Base Script Functions

The are three special functions that TES5Edit will call when a script is run:

•  **Initialize**: This function is called when the script starts. It's useful to initialize variables.

•  **Process**: This function is called for every record selected in the TES5Edit tree. If a plugin is selected then it will be called for each record defined in the plugin. The same happens if a record type is selected in the tree.

•  **Finalize**: This function is called when the script has finished processing every record. Generally useful for saving files and freeing the allocated resources.

All these functions are optional, so if they are not needed they can be omitted.

[Previous Section](#s_11482) [Top of this Group](#s_11451)

### 13.18 - Hotkeys

TES5Edit can assign *hotkeys* to scripts. The script hotkey is defined in the description like this:

{
	Script description.
	------------------------
	Hotkey: Ctrl+Alt+Shift+E
}

[Previous Section](#s_11451) [Top of this Group](#s_11452)

### 13.19 - Script References

Scripts can use functions defined in other scripts. That allows creating *toolkits* to avoid duplicating code. To make use of this feature the following instruction is used: (use below the unit name)

uses 'MyTools';

With that command we instruct the script to load another script named "MyTools.pas" and the functions in that script will be available. Note that any conflict in names can be resolved by the unit name. So it's suggested to change the *toolkit* script unit name appropriately.

[Previous Section](#s_11452) [Top of this Group](#s_11453)

### 13.20 - Script User Interface

-   *AddMessage(asMessage)* pushes a line to TES5Edit's Information tab.

-   *InputQuery(asWindowTitle, asWindowText, out sVariableToSet)* displays a prompt dialog; it returns False if the user clicked Cancel or X, or True otherwise, and sets the output variable to whatever the user types if the user hits "OK."

-   *SelectDirectory(asPromptStringOfSomeKind, asInitialDirectory, asRootDirectory, nil)* returns a path as a string; used in "Assets browser.pas"

-   *ShellExecute* seen in "Execute external applications.pas", used to call another program

-   *TCheckListBox* used in "Copy as override.pas"

-   *TListView* used in "Assets browser.pas"

-   *TMemo* used in "Assets browser.pas"

-   *TMenuItem* used in "Assets browser.pas"

-   *TPopupMenu* used in "Assets browser.pas"

-   *TSaveDialog* used in "Assets browser.pas"

-   *TScrollBox' used in "ExportImportTexts.pas"*

-   *I highly recommend viewing/using MatorTheEternal's [mtefunctions.pas](https://github.com/matortheeternal/TES5EditScripts/blob/master/Edit%20Scripts/mteFunctions.pas) for examples as well.*

Class

Reference

Description

Use example

Note

**TButton**

[TButton](http://docs.embarcadero.com/products/rad_studio/delphiAndcpp2009/HelpUpdate2/EN/html/delphivclwin32/StdCtrls_TButton.html)

Button

Assets browser.pas

The button doesn't automatically expand its width to accommodate its contents.

**TCheckBox**

[TCheckBox](href=)

Checkbox

none

You can apply a label using the `Caption` property; you don't need to make your own TLabel. Note, for more advanced scripts, that `OnChange` is not supported; use `OnClick` (which listens for more than just clicks) instead. Manually changing the `Checked` property will also fire an OnClick event; to avoid recursion where needed, you can set `OnClick` to `nil`, change `Checked`, and then restore `OnClick`'s value.

**TComboBox**

[TComboBox](href=)

Combobox

none

Set the `Style` property to `csDropDownList` to disallow custom text entry, mimicking the function of a typical drop-down menu

**TForm**

[TForm](href=)

A dialog?

ExportImportTexts.pas

**TLabel**

[TLabel](href=)

Used to display ordinary text.

none

Set the [`Caption`](href=) property to your text. To show line breaks, concatenate `#13#10` into your string (e.g. `'Line 1' + #13#10 + 'Line 2'`).

**TPanel**

[TPanel](href=)

General-purpose container for UI widgets

ExportImportTexts.pas

**TStaticText**

[TStaticText](href=)

Apparently used to display ordinary text.

none

Pretty much the same as a TLabel, but it cuts off any text that has line breaks. Not particularly useful.

TES5Edit appears to provide the following variables:

Name

Type

Description

Note

**frmFileSelect**

TForm

Returns a copy of the plugin select dialog, which can be shown by calling `fMyDialogVariable.ShowModal`

You can get a reference to the checkbox list (as a TCheckListBox) by calling `TCheckListBox(fMyDialogVariable.FindComponent('CheckListBox1'))`

[Previous Section](#s_11453) [Top of this Group](#s_11454)

### 13.21 - Simple Script Sample

This is a sample script which will only export every selected NPC to a TXT file:

{
	Script description: Exports the FormID and EditorID of the selected NPCs
}

// This is the unit name that will contain all the script functions
unit ExportScripts;

// Global variables
var NPCList : TStringList;

// Called when the script starts
function Initialize : integer;
begin
	NPCList := TStringList.Create;
	NPCList.Add('FormID;EditorID');
end;

// Called for each selected record in the TES5Edit tree
// If an entire plugin is selected then all records in the plugin will be processed
function Process(e : IInterface) : integer;
begin
	if Signature(e) <> 'NPC\_' then exit;
	NPCList.Add(IntToHex(FixedFormID(e), 8) + ';' + GetElementEditValues(e, 'EDID'));
end;

// Called after the script has finished processing every record
function Finalize : integer;
var filename : string;
begin
	filename := ProgramPath + 'Edit Scripts\\NPCs.txt';
	AddMessage('Saving NPC list to ' + filename);
	NPCList.SaveToFile(filename);
	NPCList.Free;
end;

end.

[Previous Section](#s_1154) [Top of this Group](#s_116)

### 13.22 - Pascal implementation

TES5Edit uses JvInterpreter from [JVCL](href=) to execute Delphi as a scripting language. The standard libraries offered by JvInterpreter directly wrap whatever libraries the containing application (xEdit) was compiled with.

An examination of [xEdit's own source code](href=) indicates that it provides (JvInterpreter's versions of) the following standard libraries to scripts, even if those scripts do not include the libraries via the `uses` command:

-   Buttons

-   Classes

-   Comctrls

-   Contnrs

-   Controls

-   Dialogs

-   ExtCtrls

-   Forms

-   Graphics

-   Menus

-   StdCtrls

-   System

-   SysUtils

-   Windows

Misc notes:

-   In TES5Edit's Pascal implementation, values are returned by assigning to `Result`, rather than by assigning to the function name.

-   TES5Edit's Pascal implementation does not appear to support constructions such as `TList<Integer>`.

-   If you try to store a Variant (e.g. the return value of GetElementNativeValues) in a Float variable and that variant has returned `nil`, then that Float will also contain `nil` and will throw errors when used.

-   JvInterpreter throws an error if any identifiers in the global scope are redeclared; reportedly, this differs from [the behavior that Delphi has shown since 1987](href=), wherein global identifiers in later-included files shadow those in earlier-included files. Defining them in `implementation` blocks doesn't make any difference.
    
    -   In addition to this, including a unit multiple times triggers these errors, as its own definitions conflict with themselves.
        
        -   And no, Delphi has no equivalent to `#pragma once`, and JvInterpreter wouldn't support it anyway
        
    

-   According to Delphi documentation across the web, Const directives inside of functions and procedures are supposed to define static local variables: these variables are not supposed to be constants, and their values are supposed to persist until the script has finished executing. However, in JvInterpreter, Const directives in functions and procedures just define ordinary local variables, whose values will be lost the instant the function or procedure finishes executing. Among other things, this means you can't use getters with static variables to work around the issues with global variables.

-   The scripting environment will not throw errors upon encountering the `interface` or `implementation` keywords, but it also does not honor them: definitions within the implementation will be available to a file's users. It appears that these keywords are purely semantic.
    
    -   JvInterpreter may encounter parser errors if it finds a forward-declared function or procedure, owing to the lack of Begin and End keywords.
    
    -   JvInterpreter does not throw errors if you redefine a function within the same file, even if the redefinition changes that function's signature. Sometimes, it uses the last definition; other times, however, it uses the first definition.
    

-   JvInterpreter doesn't throw errors if multiple files use the same unit name, but having multiple files use the same unit name will break the parser. Errors like "*Error in unit 'UnitName' on line 42: 'begin' expected but 'x' found*", where "x" is the middle of another keyword, a variable name, or even a string, are common in this situation.

-   JvInterpreter does not short-circuit conditions such as `If Assigned(myList) And (myList.IndexOf('Test')) Then`; even if the first clause fails, the second will still execute (and end up throwing an exception). You need to nest the conditions: `If A Then If B Then C;`.
    
    -   A simpler example: `If (myInt = 0) Or (otherInt Mod myInt = 0)` will yield a divide-by-zero error.
    

-   Be careful when refactoring your code. If you move functions between units, JvInterpreter will not handle this sanely; calling the function on the old unit (i.e. `WrongUnit.SomeFunction;`) is likely to cause a memory access violation without any intelligible explanation.

[Previous Section](#s_116) [Top of this Group](#s_117)

### 13.23 - xEdit extensions to JvInterpreter

xEdit extends units (standard libraries) provided by JvInterpreter with the following keywords. Note that since these are automatically included in your script, you can reference them directly and unprefixed (i.e. `Pred` instead of `System.Pred`).

-   Controls
    
    -   akLeft
    
    -   akRight
    
    -   akTop
    
    -   akBottom
    

-   FileCtrl
    
    -   *function* SelectDirectory
    

-   Forms
    
    -   pmAuto
    
    -   pmExplicit
    
    -   pmNone
    
    -   poMainFormCenter
    

-   Math *\[xEdit doesn't offer the module itself; only these functions are provided\]*
    
    -   *function* Ceil
    
    -   *function* Floor
    
    -   *function* IntPower
    
    -   *function* Max *(note: this casts its arguments to integers before comparing them)*
    
    -   *function* Min *(note: this casts its arguments to integers before comparing them)*
    
    -   *function* Power
    

-   Menus
    
    -   maAutomatic
    
    -   maManual
    

-   ShellApi
    
    -   *function* ShellExecute
    
    -   *function* ShellExecuteWait
    

-   System
    
    -   *function* StringOfChar
    
    -   MaxInt
    
    -   MinInt
    

-   SysUtils
    
    -   *function* Dec
    
    -   *function* DirectoryExists
    
    -   *function* ExcludeTrailingBackslash
    
    -   *function* FileExists
    
    -   *function* ForceDirectories
    
    -   *function* Frac
    
    -   *function* Inc
    
    -   *function* IncludeTrailingBackslash
    
    -   *function* Int
    
    -   *function* IntToHex64
    
    -   *function* Pred
    
    -   *function* SameText
    
    -   *function* StringReplace
    
    -   *function* StrToInt64
    
    -   *function* StrToInt64Def
    
    -   *function* StrToFloatDef
    
    -   *function* Succ
    
    -   LowInteger
    
    -   HighInteger
    
    -   cbChecked
    
    -   cbGrayed
    
    -   cbUnchecked
    
    -   fmCreate
    
    -   lpAbove
    
    -   lpBelow
    
    -   lpLeft
    
    -   lpRight
    
    -   rfReplaceAll
    
    -   rfIgnoreCase
    

-   Windows
    
    -   *function* CopyFile
    
    -   *function* CreateProcessWait
    
    -   *function* Sleep
    
    -   SW\_HIDE
    
    -   SW\_MAXIMIZE
    
    -   SW\_MINIMIZE
    
    -   SW\_RESTORE
    
    -   SW\_SHOW
    
    -   SW\_SHOWDEFAULT
    
    -   SW\_SHOWMAXIMIZED
    
    -   SW\_SHOWMINIMIZED
    
    -   SW\_SHOWMINNOACTIVE
    
    -   SW\_SHOWNA
    
    -   SW\_SHOWNOACTIVATE
    
    -   SW\_SHOWNORMAL
    

The following classes are also extended (or simply offered, if JvInterpreter didn't already offer them):

-   TBinaryReader
    
    -   *get* Create
    
    -   *get* Read
    
    -   *get* ReadBoolean
    
    -   *get* ReadByte
    
    -   *get* ReadBytes
    
    -   *get* ReadChar
    
    -   *get* ReadDouble
    
    -   *get* ReadShortInt
    
    -   *get* ReadSmallInt
    
    -   *get* ReadUInt16
    
    -   *get* ReadUInt32
    
    -   *get* ReadInteger
    
    -   *get* ReadSingle
    
    -   *get* ReadString
    

-   TBinaryWriter
    
    -   *get* Create
    
    -   *get* Write
    
    -   *get* WriteSingle
    

-   TBitmap
    
    -   *get* SetSize
    

-   TBoundLabel

-   TBytesStream
    
    -   *get* Create
    

-   TCheckListBox
    
    -   *get* Create
    
    -   *get* CheckAll
    
    -   *get/set* AllowGrayed
    
    -   *get/set* Checked
    
    -   *get/set* Header
    
    -   *get/set* ItemEnabled
    
    -   *get/set* State
    
    -   *event* TNotifyEvent
    

-   TComboBox
    
    -   *get/set* DropDownCount
    

-   TCustomForm
    
    -   *get/set* PopupMode
    
    -   *get/set* PopupParent
    

-   TCustomIniFile
    
    -   *get* DeleteKey
    
    -   *get* EraseSection
    
    -   *get* ReadBool
    
    -   *get* ReadFloat
    
    -   *get* ReadInteger
    
    -   *get* ReadSection
    
    -   *get* ReadSections
    
    -   *get* ReadSectionValues
    
    -   *get* ReadString
    
    -   *get* SectionExists
    
    -   *get* UpdateFile
    
    -   *get* ValueExists
    
    -   *get* WriteBool
    
    -   *get* WriteFloat
    
    -   *get* WriteInteger
    
    -   *get* WriteString
    

-   TCustomLabeledEdit
    
    -   *get* Create
    
    -   *get* EditLabel
    
    -   *get/set* LabelPosition
    
    -   *get/set* LabelSpacing
    

-   THashedStringList
    
    -   *get* Create
    

-   TLabeledEdit
    
    -   *get* Create
    

-   TListItem
    
    -   *get/set* SubItems
    

-   TListItems
    
    -   *set* Count
    

-   TListView
    
    -   *event* TLVOwnerDataEvent
    
    -   *event* TLVSelectItemEvent
    

-   TIniFile
    
    -   *get* Create
    

-   TMemIniFile
    
    -   *get* Create
    
    -   *get* GetStrings
    
    -   *get* SetStrings
    

-   TMenu
    
    -   *get/set* AutoHotKeys
    

-   TMenuItem
    
    -   *get* Clear
    

-   TPerlRegex
    
    -   *get* Compile
    
    -   *get* Compiled
    
    -   *get* ComputeReplacement
    
    -   *get* Create
    
    -   *get* EscapeRegexChars
    
    -   *get* FoundMatch
    
    -   *get* GroupCount
    
    -   *get* GroupLengths
    
    -   *get* GroupOffsets
    
    -   *get* Match
    
    -   *get* MatchAgain
    
    -   *get* MatchedLength
    
    -   *get* MatchedOffset
    
    -   *get* MatchedText
    
    -   *get* NamedGroup
    
    -   *get/set* Options
    
    -   *get/set* Regex
    
    -   *get* Replace
    
    -   *get* ReplaceAll
    
    -   *get/set* Replacement
    
    -   *get* Split
    
    -   *get* SplitCapture
    
    -   *get/set* Start
    
    -   *get/set* Stop
    
    -   *get* StoreGroups
    
    -   *get* Studied
    
    -   *get* Study
    
    -   *get/set* Subject
    
    -   *get* SubjectLeft
    
    -   *get* SubjectRight
    

-   TPerlRegexOptions
    
    -   *const* preAnchored
    
    -   *const* preCaseLess
    
    -   *const* preExtended
    
    -   *const* preMultiLine
    
    -   *const* preNoAutoCapture
    
    -   *const* preNotBOL
    
    -   *const* preNotEmpty
    
    -   *const* preNotEOL
    
    -   *const* preSingleLine
    
    -   *const* preUnGreedy
    

-   TRegistryIniFile
    
    -   *get* Create
    

-   TStrings
    
    -   *get/set* DelimitedText
    
    -   *get/set* Delimiter
    
    -   *set* NameValueSeparator
    
    -   *set* StrictDelimiter
    
    -   *get/set* ValueFromIndex
    

-   TStringList
    
    -   *get/set* CaseSensitive
    

-   TWinControl
    
    -   *get/set* DoubleBuffered
    

[Previous Section](#s_117) [Top of this Group](#s_1171)

### 13.24 - Unsupported language features

Feature

Details

anonymous methods

Refer to the [Embarcadero documentation](href=).

array arguments

A function cannot accept an argument with a type like `array of integer`.

function overloading

Allows the same function to have multiple sets of arguments.

object types

The `object` keyword isn't implemented.

out parameters

Out parameters always receive default values, such as false for a boolean. Use var parameters instead.

procedural types

Refer to the [Embarcadero documentation](href=).

structured types

Refer to the [Embarcadero documentation](href=).

subclasses

The `constructor` keyword isn't implemented. Subclasses without a constructor can be defined, but attempts to instantiate them (`MyClass.Create`) will always break.

try

Doesn't catch all runtime errors.

[Previous Section](#s_1171) [Top of this Group](#s_1172)

### 13.25 - Unsupported operators

Operator

Description

&

Prefix; suppresses parsing of a keyword (e.g. `&For` is a variable named "For").

@

Prefix; retrieves the address of a variable for use as a pointer; compare to `&` in C++.

^

Dereferences a pointer; compare to `*` in C++.

<<

Used for bit shifting, but returns a junk result in xEdit. Use `Shl` instead.

\>>

Used for bit shifting, but returns a junk result in xEdit. Use `Shr` instead.

[Previous Section](#s_1172) [Top of this Group](#s_1173)

### 13.26 - Unsupported keywords

Keyword

Description

absolute

Allows two or more variables to occupy the same location in memory.

as

Used to cast a variable to a given class.

constructor

Used to declare a constructor function for subclasses; absence of this keyword makes subclasses impossible to use.

in

Used in expressions like `myChar in ['a','b']`. It's either entirely broken or it only works in other situations.

is

Used to test whether a variable is an instance of a given class; for anything derived from `TObject`, you can use the `ClassName` method instead.

object

Used to create [object types](href=).

type

Partial implementation. You can use it to alias a class name, but it's broken for every single other use and its existence is therefore pointless.

with

Statement.

[Previous Section](#s_1173) [Top of this Group](#s_1174)

### 13.27 - Unsupported classes and tools

Feature

Description

[Variant support routines](href=)

Makes it easier to identify a variant's current type, and cast variants. Relevant type keywords like `varInteger` are also missing.

Move

This function is supposed to copy data from one memory location to another. Instead, it either throws an error, or fails silently and nulls out the target location.

[Previous Section](#s_1174) [Top of this Group](#s_1175)

[« Previous Page](12-cheat-sheets-and-quick-reference-charts.html) [Next Page »](14-Scripting-Resources.html)

[docs](https://github.com/TES5Edit/docs) is maintained by [TES5Edit](https://github.com/TES5Edit). This page was generated by [GitHub Pages](https://pages.github.com).