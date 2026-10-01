# xEdit Pascal scripting API

Extracted from `third_party/xedit/Edit Scripts/xEditAPI.pas`, which is xEdit's own
declaration, shipped with the editor. Regenerate with `tools/extract_xedit_api.py`.

## Trust

**This is a declaration, not a measurement.** Where it disagrees with a shipped
working script, the script is right. Known case:

| symbol | declared | called as | measured |
|---|---|---|---|
| `FileWriteToStream` | 2 params, `xEditAPI.pas:334` | 3 params, `SaveAs.pas:63` | 2 params raises `Not enough parameters` |

Counts: **358** declarations across **11** scopes, **24** types, **26** constants.

## Type hierarchy

From the Tome of xEdit §13.5. `xEditAPI.pas` declares the types flat with no
parent links, so this nesting exists only in the documentation. It is the thing
worth having: `Add()` returns `IwbElement` while `FixedFormID()` requires
`IwbMainRecord`, and the hierarchy is why passing one to the other returns a null
instead of raising.

```
IwbContainerBase
  IwbContainer
    IwbDataContainer
      IwbFileHeader
      IwbRecord
        IwbGroupRecord
        IwbMainRecord
      IwbSubRecord
    IwbFile
IwbContainerElementRef
IwbResource
IwbResourceContainer
IwbBA2File
IwbBSAFile
IwbFolder
Unknown but used: TwbDefType, TwbElementState, TwbElementType
```

## Before writing a call

1. Look it up here. Not in a doc transcription, not from memory of another API.
2. If it is here, confirm against a shipped script in `Edit Scripts/` that calls it.
3. If the two disagree, trust the script and record the conflict.

## Globals and types

| kind | name | declaration |
|---|---|---|

## DDS functions

| kind | name | declaration |
|---|---|---|
| function | `wbDDSStreamToBitmap` | `function wbDDSStreamToBitmap (akStream: TStream; akBitmapOut: TBitmap): boolean` |
| function | `wbDDSDataToBitmap` | `function wbDDSDataToBitmap (akData: TBytes; akBitmapOut: TBitmap): boolean` |
| function | `wbDDSResourceToBitmap` | `function wbDDSResourceToBitmap (akUnknown: IInterface; akBitmapOut: TBitmap): boolean` |
| function | `wbDDSStreamToBitmap` | `function wbDDSStreamToBitmap (akStream: TStream; akBitmapOut: TBitmap): boolean` |
| function | `wbDDSDataToBitmap` | `function wbDDSDataToBitmap (akData: TBytes; akBitmapOut: TBitmap): boolean` |
| function | `wbDDSResourceToBitmap` | `function wbDDSResourceToBitmap (akUnknown: IInterface; akBitmapOut: TBitmap): boolean` |

## Global Functions

| kind | name | declaration |
|---|---|---|
| procedure | `AddMessage` | `procedure AddMessage (asMessage: string)` |
| function | `Assigned` | `function Assigned (aeElement: IwbElement): boolean; overload` |
| function | `Assigned` | `function Assigned (aObject: TObject): Boolean; overload` |
| function | `ObjectToElement` | `function ObjectToElement (akObject: TObject): IInterface` |
| function | `FileByIndex` | `function FileByIndex (aiFile: integer): IwbFile` |
| function | `FileByLoadOrder` | `function FileByLoadOrder (aiLoadOrder: integer): IwbFile` |
| function | `FullPathToFilename` | `function FullPathToFilename (asFilename: string): string` |
| procedure | `EnableSkyrimSaveFormat` | `procedure EnableSkyrimSaveFormat ()` |
| procedure | `GetRecordDefNames` | `procedure GetRecordDefNames (akList: TStrings)` |
| procedure | `JumpTo` | `procedure JumpTo (aeElement: IwbElement; unknown: boolean)` |
| procedure | `wbFilterStrings` | `procedure wbFilterStrings (akListIn: TStrings; akListOut: TStrings; asFilter: String)` |
| procedure | `wbRemoveDuplicateStrings` | `procedure wbRemoveDuplicateStrings (akList: TStringList)` |
| procedure | `AddMessage` | `procedure AddMessage (asMessage: string)` |
| function | `Assigned` | `function Assigned (aeElement: IwbElement): boolean; overload` |
| function | `Assigned` | `function Assigned (aObject: TObject): Boolean; overload` |
| function | `ObjectToElement` | `function ObjectToElement (akObject: TObject): IInterface` |
| function | `FileByIndex` | `function FileByIndex (aiFile: integer): IwbFile` |
| function | `FileByLoadOrder` | `function FileByLoadOrder (aiLoadOrder: integer): IwbFile` |
| function | `FullPathToFilename` | `function FullPathToFilename (asFilename: string): string` |
| procedure | `EnableSkyrimSaveFormat` | `procedure EnableSkyrimSaveFormat ()` |
| procedure | `GetRecordDefNames` | `procedure GetRecordDefNames (akList: TStrings)` |
| procedure | `JumpTo` | `procedure JumpTo (aeElement: IwbElement; unknown: boolean)` |
| procedure | `wbFilterStrings` | `procedure wbFilterStrings (akListIn: TStrings; akListOut: TStrings; asFilter: String)` |
| procedure | `wbRemoveDuplicateStrings` | `procedure wbRemoveDuplicateStrings (akList: TStringList)` |

## Global Variables

| kind | name | declaration |
|---|---|---|
| function | `DataPath` | `function DataPath : String` |
| function | `ProgramPath` | `function ProgramPath :  String` |
| function | `ScriptsPath` | `function ScriptsPath :  String` |
| function | `FileCount` | `function FileCount :  Integer` |
| function | `wbAppName` | `function wbAppName : String` |
| function | `wbGameName` | `function wbGameName : String` |
| function | `wbGameMasterEsm` | `function wbGameMasterEsm : String` |
| function | `wbVersionNumber` | `function wbVersionNumber :  Integer` |

## IwbContainer Functions

| kind | name | declaration |
|---|---|---|
| function | `Add` | `function Add (aeContainer: IwbContainer; asNameOrSignature: string; abSilent: boolean): IwbElement` |
| procedure | `AddElement` | `procedure AddElement (aeContainer: IwbContainer; aeElement: IwbElement)` |
| function | `AdditionalElementCount` | `function AdditionalElementCount (aeContainer: IwbContainer): integer` |
| function | `ContainerStates` | `function ContainerStates (aeContainer: IwbContainer): byte` |
| function | `ElementByIndex` | `function ElementByIndex (aeContainer: IwbContainer; aiIndex: integer): IwbElement` |
| function | `ElementByName` | `function ElementByName (aeContainer: IwbContainer; asName: string): IwbElement` |
| function | `ElementByPath` | `function ElementByPath (aeContainer: IwbContainer; asPath: string): IwbElement` |
| function | `ElementBySignature` | `function ElementBySignature (aeContainer: IwbContainer; asSignature: string): IwbElement` |
| function | `ElementCount` | `function ElementCount (aeContainer: IwbContainer): integer` |
| function | `ElementExists` | `function ElementExists (aeContainer: IwbContainer; asName: string): boolean` |
| function | `GetElementEditValues` | `function GetElementEditValues (aeContainer: IwbContainer; asPath: string): string` |
| function | `GetElementNativeValues` | `function GetElementNativeValues (aeContainer: IwbContainer; asPath: string): Variant` |
| function | `IndexOf` | `function IndexOf (aeContainer: IwbContainer; aeChild: IwbElement): integer` |
| function | `InsertElement` | `function InsertElement (aeContainer: IwbContainer; aiPosition: integer; aeElement: IwbElement): integer` |
| function | `IsSorted` | `function IsSorted (aeContainer: IwbSortableContainer): boolean` |
| function | `LastElement` | `function LastElement (aeContainer: IwbContainer): IwbElement` |
| function | `RemoveByIndex` | `function RemoveByIndex (aeContainer: IwbContainer; aiIndex: integer; abMarkModified: boolean): IwbElement` |
| function | `RemoveElement` | `function RemoveElement (aeContainer: IwbContainer; avChild: Variant): IwbElement` |
| procedure | `ReverseElements` | `procedure ReverseElements (aeContainer: IwbContainer)` |
| procedure | `SetElementEditValues` | `procedure SetElementEditValues (aeContainer: IwbContainer; asPath: string; asValue: string)` |
| procedure | `SetElementNativeValues` | `procedure SetElementNativeValues (aeContainer: IwbContainer; asPath: string; avValue: Variant)` |
| function | `Add` | `function Add (aeContainer: IwbContainer; asNameOrSignature: string; abSilent: boolean): IwbElement` |
| procedure | `AddElement` | `procedure AddElement (aeContainer: IwbContainer; aeElement: IwbElement)` |
| function | `AdditionalElementCount` | `function AdditionalElementCount (aeContainer: IwbContainer): integer` |
| function | `ContainerStates` | `function ContainerStates (aeContainer: IwbContainer): byte` |
| function | `ElementByIndex` | `function ElementByIndex (aeContainer: IwbContainer; aiIndex: integer): IwbElement` |
| function | `ElementByName` | `function ElementByName (aeContainer: IwbContainer; asName: string): IwbElement` |
| function | `ElementByPath` | `function ElementByPath (aeContainer: IwbContainer; asPath: string): IwbElement` |
| function | `ElementBySignature` | `function ElementBySignature (aeContainer: IwbContainer; asSignature: string): IwbElement` |
| function | `ElementCount` | `function ElementCount (aeContainer: IwbContainer): integer` |
| function | `ElementExists` | `function ElementExists (aeContainer: IwbContainer; asName: string): boolean` |
| function | `GetElementEditValues` | `function GetElementEditValues (aeContainer: IwbContainer; asPath: string): string` |
| function | `GetElementNativeValues` | `function GetElementNativeValues (aeContainer: IwbContainer; asPath: string): Variant` |
| function | `IndexOf` | `function IndexOf (aeContainer: IwbContainer; aeChild: IwbElement): integer` |
| function | `InsertElement` | `function InsertElement (aeContainer: IwbContainer; aiPosition: integer; aeElement: IwbElement): integer` |
| function | `IsSorted` | `function IsSorted (aeContainer: IwbSortableContainer): boolean` |
| function | `LastElement` | `function LastElement (aeContainer: IwbContainer): IwbElement` |
| function | `RemoveByIndex` | `function RemoveByIndex (aeContainer: IwbContainer; aiIndex: integer; abMarkModified: boolean): IwbElement` |
| function | `RemoveElement` | `function RemoveElement (aeContainer: IwbContainer; avChild: Variant): IwbElement` |
| procedure | `ReverseElements` | `procedure ReverseElements (aeContainer: IwbContainer)` |
| procedure | `SetElementEditValues` | `procedure SetElementEditValues (aeContainer: IwbContainer; asPath: string; asValue: string)` |
| procedure | `SetElementNativeValues` | `procedure SetElementNativeValues (aeContainer: IwbContainer; asPath: string; avValue: Variant)` |

## IwbElement Functions

| kind | name | declaration |
|---|---|---|
| function | `BaseName` | `function BaseName (aeElement: IwbElement): string` |
| procedure | `BuildRef` | `procedure BuildRef (aeElement: IwbElement)` |
| function | `CanContainFormIDs` | `function CanContainFormIDs (aeElement: IwbElement): boolean` |
| function | `CanMoveDown` | `function CanMoveDown (aeElement: IwbElement): boolean` |
| function | `CanMoveUp` | `function CanMoveUp (aeElement: IwbElement): boolean` |
| function | `Check` | `function Check (aeElement: IwbElement): string` |
| procedure | `ClearElementState` | `procedure ClearElementState (aeElement: IwbElement; aiState: TwbElementState)` |
| function | `ContainingMainRecord` | `function ContainingMainRecord (aeElement: IwbElement): IwbMainRecord` |
| function | `DefType` | `function DefType (aeElement: IwbElement): TwbDefType` |
| function | `DisplayName` | `function DisplayName (aeElement: IwbElement): string` |
| function | `ElementAssign` | `function ElementAssign (aeContainer: IwbContainer; aiIndex: integer; aeSource: IwbElement; abOnlySK: boolean): IwbElement` |
| function | `ElementType` | `function ElementType (aeElement: IwbElement): TwbElementType` |
| function | `EnumValues` | `function EnumValues (aeElement: IwbElement): string` |
| function | `Equals` | `function Equals (aeElement1: IwbElement; aeElement2: IwbElement): boolean` |
| function | `FlagValues` | `function FlagValues (aeElement: IwbElement): string` |
| function | `FullPath` | `function FullPath (aeElement: IwbElement): string` |
| function | `GetContainer` | `function GetContainer (aeElement: IwbElement): IwbContainer` |
| function | `GetEditValue` | `function GetEditValue (aeElement: IwbElement): string` |
| function | `GetElementState` | `function GetElementState (aeElement: IwbElement; aiState: TwbElementState): TwbElementState` |
| function | `GetFile` | `function GetFile (aeElement: IwbElement): IwbFile` |
| function | `GetNativeValue` | `function GetNativeValue (aeElement: IwbElement): Variant` |
| function | `IsEditable` | `function IsEditable (aeElement: IwbElement): boolean` |
| function | `IsInjected` | `function IsInjected (aeElement: IwbElement): boolean` |
| function | `LinksTo` | `function LinksTo (aeElement: IwbElement): IwbElement` |
| procedure | `MarkModifiedRecursive` | `procedure MarkModifiedRecursive (aeElement: IwbElement)` |
| procedure | `MoveDown` | `procedure MoveDown (aeElement: IwbElement)` |
| procedure | `MoveUp` | `procedure MoveUp (aeElement: IwbElement)` |
| function | `Name` | `function Name (aeElement: IwbElement): string` |
| function | `Path` | `function Path (aeElement: IwbElement): string` |
| function | `PathName` | `function PathName (aeElement: IwbElement): string` |
| procedure | `Remove` | `procedure Remove (aeElement: IwbElement)` |
| procedure | `ReportRequiredMasters` | `procedure ReportRequiredMasters (aeElement: IwbElement; akListOut: TStrings; akUnknown1: boolean; akUnknown2: boolean)` |
| function | `SetEditValue` | `function SetEditValue (aeElement: IwbElement; asValue: string): string` |
| function | `SetElementState` | `function SetElementState (aeElement: IwbElement; aiState: TwbElementState): TwbElementState` |
| function | `SetNativeValue` | `function SetNativeValue (aeElement: IwbElement; avValue: variant): string` |
| procedure | `SetToDefault` | `procedure SetToDefault (aeElement: IwbElement)` |
| function | `ShortName` | `function ShortName (aeElement: IwbElement): string` |
| function | `SortKey` | `function SortKey (aeElement: IwbElement): string` |
| function | `wbCopyElementToFile` | `function wbCopyElementToFile (aeElement: IwbElement; aeFile: IwbFile; abAsNew: boolean; abDeepCopy: boolean): IwbElement` |
| function | `wbCopyElementToFileWithPrefix` | `function wbCopyElementToFileWithPrefix (aeElement: IwbElement; aeFile: IwbFile; abAsNew: boolean; abDeepCopy: boolean; akUnknown1: IInterface; akUnknown2: IInterface; akUnknown3: IInterface): IwbElement` |
| function | `wbCopyElementToRecord` | `function wbCopyElementToRecord (aeElement: IwbElement; aeRecord: IwbMainRecord; abAsNew: boolean; abDeepCopy: boolean): IwbElement` |
| function | `BaseName` | `function BaseName (aeElement: IwbElement): string` |
| procedure | `BuildRef` | `procedure BuildRef (aeElement: IwbElement)` |
| function | `CanContainFormIDs` | `function CanContainFormIDs (aeElement: IwbElement): boolean` |
| function | `CanMoveDown` | `function CanMoveDown (aeElement: IwbElement): boolean` |
| function | `CanMoveUp` | `function CanMoveUp (aeElement: IwbElement): boolean` |
| function | `Check` | `function Check (aeElement: IwbElement): string` |
| procedure | `ClearElementState` | `procedure ClearElementState (aeElement: IwbElement; aiState: TwbElementState)` |
| function | `ContainingMainRecord` | `function ContainingMainRecord (aeElement: IwbElement): IwbMainRecord` |
| function | `DefType` | `function DefType (aeElement: IwbElement): TwbDefType` |
| function | `DisplayName` | `function DisplayName (aeElement: IwbElement): string` |
| function | `ElementAssign` | `function ElementAssign (aeContainer: IwbContainer; aiIndex: integer; aeSource: IwbElement; abOnlySK: boolean): IwbElement` |
| function | `ElementType` | `function ElementType (aeElement: IwbElement): TwbElementType` |
| function | `EnumValues` | `function EnumValues (aeElement: IwbElement): string` |
| function | `Equals` | `function Equals (aeElement1: IwbElement; aeElement2: IwbElement): boolean` |
| function | `FlagValues` | `function FlagValues (aeElement: IwbElement): string` |
| function | `FullPath` | `function FullPath (aeElement: IwbElement): string` |
| function | `GetContainer` | `function GetContainer (aeElement: IwbElement): IwbContainer` |
| function | `GetEditValue` | `function GetEditValue (aeElement: IwbElement): string` |
| function | `GetElementState` | `function GetElementState (aeElement: IwbElement; aiState: TwbElementState): TwbElementState` |
| function | `GetFile` | `function GetFile (aeElement: IwbElement): IwbFile` |
| function | `GetNativeValue` | `function GetNativeValue (aeElement: IwbElement): Variant` |
| function | `IsEditable` | `function IsEditable (aeElement: IwbElement): boolean` |
| function | `IsInjected` | `function IsInjected (aeElement: IwbElement): boolean` |
| function | `LinksTo` | `function LinksTo (aeElement: IwbElement): IwbElement` |
| procedure | `MarkModifiedRecursive` | `procedure MarkModifiedRecursive (aeElement: IwbElement)` |
| procedure | `MoveDown` | `procedure MoveDown (aeElement: IwbElement)` |
| procedure | `MoveUp` | `procedure MoveUp (aeElement: IwbElement)` |
| function | `Name` | `function Name (aeElement: IwbElement): string` |
| function | `Path` | `function Path (aeElement: IwbElement): string` |
| function | `PathName` | `function PathName (aeElement: IwbElement): string` |
| procedure | `Remove` | `procedure Remove (aeElement: IwbElement)` |
| procedure | `ReportRequiredMasters` | `procedure ReportRequiredMasters (aeElement: IwbElement; akListOut: TStrings; akUnknown1: boolean; akUnknown2: boolean)` |
| function | `SetEditValue` | `function SetEditValue (aeElement: IwbElement; asValue: string): string` |
| function | `SetElementState` | `function SetElementState (aeElement: IwbElement; aiState: TwbElementState): TwbElementState` |
| function | `SetNativeValue` | `function SetNativeValue (aeElement: IwbElement; avValue: variant): string` |
| procedure | `SetToDefault` | `procedure SetToDefault (aeElement: IwbElement)` |
| function | `ShortName` | `function ShortName (aeElement: IwbElement): string` |
| function | `SortKey` | `function SortKey (aeElement: IwbElement): string` |
| function | `wbCopyElementToFile` | `function wbCopyElementToFile (aeElement: IwbElement; aeFile: IwbFile; abAsNew: boolean; abDeepCopy: boolean): IwbElement` |
| function | `wbCopyElementToFileWithPrefix` | `function wbCopyElementToFileWithPrefix (aeElement: IwbElement; aeFile: IwbFile; abAsNew: boolean; abDeepCopy: boolean; akUnknown1: IInterface; akUnknown2: IInterface; akUnknown3: IInterface): IwbElement` |
| function | `wbCopyElementToRecord` | `function wbCopyElementToRecord (aeElement: IwbElement; aeRecord: IwbMainRecord; abAsNew: boolean; abDeepCopy: boolean): IwbElement` |

## IwbFile Functions

| kind | name | declaration |
|---|---|---|
| procedure | `AddMasters` | `procedure AddMasters (aeFile: IwbFile; aMasters: TStrings)` |
| procedure | `AddMasterIfMissing` | `procedure AddMasterIfMissing (aeFile: IwbFile; asMasterFilename: string; aSortMasters: Boolean = True)` |
| function | `AddNewFileName` | `function AddNewFileName (asFileName: string): IwbFile` |
| procedure | `CleanMasters` | `procedure CleanMasters (aeFile: IwbFile)` |
| function | `FileFormIDtoLoadOrderFormID` | `function FileFormIDtoLoadOrderFormID (aeFile: IwbFile; aiFormID: cardinal): cardinal` |
| procedure | `FileWriteToStream` | `procedure FileWriteToStream (aeFile: IwbFile; akOutStream: TStream)` |
| function | `GetFileName` | `function GetFileName (aeFile: IwbFile): string` |
| function | `GetIsESM` | `function GetIsESM (aeFile: IwbFile): boolean` |
| function | `GetLoadOrder` | `function GetLoadOrder (aeFile: IwbFile): integer` |
| function | `GetNewFormID` | `function GetNewFormID (aeFile: IwbFile): cardinal` |
| function | `GroupBySignature` | `function GroupBySignature (aeFile: IwbFile; asSignature: string): IwbGroupRecord` |
| function | `HasGroup` | `function HasGroup (aeFile: IwbFile; asSignature: string): boolean` |
| function | `HasMaster` | `function HasMaster (aeFile: IwbFile; asMasterFilename: string): boolean` |
| function | `LoadOrderFormIDtoFileFormID` | `function LoadOrderFormIDtoFileFormID (aeFile: IwbFile; aiFormID: cardinal): cardinal` |
| function | `MasterByIndex` | `function MasterByIndex (aeFile: IwbFile; aiIndex: integer): IwbFile` |
| function | `MasterCount` | `function MasterCount (aeFile: IwbFile): cardinal` |
| function | `RecordByEditorID` | `function RecordByEditorID (aeFile: IwbFile; asEditorID: string): IwbMainRecord` |
| function | `RecordByFormID` | `function RecordByFormID (aeFile: IwbFile; aiFormID: integer; abAllowInjected: boolean): IwbMainRecord` |
| function | `RecordByIndex` | `function RecordByIndex (aeFile: IwbFile; aiIndex: integer): IwbMainRecord` |
| function | `RecordCount` | `function RecordCount (aeFile: IwbFile): cardinal` |
| procedure | `SetIsESM` | `procedure SetIsESM (aeFile: IwbFile; abFlag: boolean)` |
| procedure | `SortMasters` | `procedure SortMasters (aeFile: IwbFile)` |
| procedure | `AddMasters` | `procedure AddMasters (aeFile: IwbFile; aMasters: TStrings)` |
| procedure | `AddMasterIfMissing` | `procedure AddMasterIfMissing (aeFile: IwbFile; asMasterFilename: string; aSortMasters: Boolean = True)` |
| function | `AddNewFileName` | `function AddNewFileName (asFileName: string): IwbFile` |
| procedure | `CleanMasters` | `procedure CleanMasters (aeFile: IwbFile)` |
| function | `FileFormIDtoLoadOrderFormID` | `function FileFormIDtoLoadOrderFormID (aeFile: IwbFile; aiFormID: cardinal): cardinal` |
| procedure | `FileWriteToStream` | `procedure FileWriteToStream (aeFile: IwbFile; akOutStream: TStream)` |
| function | `GetFileName` | `function GetFileName (aeFile: IwbFile): string` |
| function | `GetIsESM` | `function GetIsESM (aeFile: IwbFile): boolean` |
| function | `GetLoadOrder` | `function GetLoadOrder (aeFile: IwbFile): integer` |
| function | `GetNewFormID` | `function GetNewFormID (aeFile: IwbFile): cardinal` |
| function | `GroupBySignature` | `function GroupBySignature (aeFile: IwbFile; asSignature: string): IwbGroupRecord` |
| function | `HasGroup` | `function HasGroup (aeFile: IwbFile; asSignature: string): boolean` |
| function | `HasMaster` | `function HasMaster (aeFile: IwbFile; asMasterFilename: string): boolean` |
| function | `LoadOrderFormIDtoFileFormID` | `function LoadOrderFormIDtoFileFormID (aeFile: IwbFile; aiFormID: cardinal): cardinal` |
| function | `MasterByIndex` | `function MasterByIndex (aeFile: IwbFile; aiIndex: integer): IwbFile` |
| function | `MasterCount` | `function MasterCount (aeFile: IwbFile): cardinal` |
| function | `RecordByEditorID` | `function RecordByEditorID (aeFile: IwbFile; asEditorID: string): IwbMainRecord` |
| function | `RecordByFormID` | `function RecordByFormID (aeFile: IwbFile; aiFormID: integer; abAllowInjected: boolean): IwbMainRecord` |
| function | `RecordByIndex` | `function RecordByIndex (aeFile: IwbFile; aiIndex: integer): IwbMainRecord` |
| function | `RecordCount` | `function RecordCount (aeFile: IwbFile): cardinal` |
| procedure | `SetIsESM` | `procedure SetIsESM (aeFile: IwbFile; abFlag: boolean)` |
| procedure | `SortMasters` | `procedure SortMasters (aeFile: IwbFile)` |

## IwbGroupRecord Functions

| kind | name | declaration |
|---|---|---|
| function | `ChildrenOf` | `function ChildrenOf (aeGroup: IwbGroupRecord): IwbMainRecord` |
| function | `FindChildGroup` | `function FindChildGroup (aeGroup: IwbGroupRecord; aiType: integer; aeMainRecord: IwbMainRecord): IwbGroupRecord` |
| function | `GroupLabel` | `function GroupLabel (aeGroup: IwbGroupRecord): cardinal` |
| function | `GroupType` | `function GroupType (): integer` |
| function | `MainRecordByEditorID` | `function MainRecordByEditorID (aeGroup: IwbGroupRecord; asEditorID: string): IwbMainRecord` |
| function | `ChildrenOf` | `function ChildrenOf (aeGroup: IwbGroupRecord): IwbMainRecord` |
| function | `FindChildGroup` | `function FindChildGroup (aeGroup: IwbGroupRecord; aiType: integer; aeMainRecord: IwbMainRecord): IwbGroupRecord` |
| function | `GroupLabel` | `function GroupLabel (aeGroup: IwbGroupRecord): cardinal` |
| function | `GroupType` | `function GroupType (): integer` |
| function | `MainRecordByEditorID` | `function MainRecordByEditorID (aeGroup: IwbGroupRecord; asEditorID: string): IwbMainRecord` |

## IwbMainRecord Functions

| kind | name | declaration |
|---|---|---|
| function | `BaseRecord` | `function BaseRecord (aeRecord: IwbMainRecord): IwbMainRecord` |
| function | `BaseRecordID` | `function BaseRecordID (aeRecord: IwbMainRecord): cardinal` |
| procedure | `ChangeFormSignature` | `procedure ChangeFormSignature (aeRecord: IwbMainRecord; asNewSignature: string)` |
| function | `ChildGroup` | `function ChildGroup (aeRecord: IwbMainRecord): IwbGroupRecord` |
| function | `CompareExchangeFormID` | `function CompareExchangeFormID (aeRecord: IwbMainRecord; aiOldFormID: cardinal; aiNewFormID: cardinal): boolean` |
| function | `EditorID` | `function EditorID (aeRecord: IwbMainRecord): string` |
| function | `FixedFormID` | `function FixedFormID (aeRecord: IwbMainRecord): cardinal` |
| function | `FormID` | `function FormID (aeRecord: IwbMainRecord): cardinal` |
| function | `GetFormVCS1` | `function GetFormVCS1 (aeRecord: IwbMainRecord): cardinal` |
| function | `GetFormVCS2` | `function GetFormVCS2 (aeRecord: IwbMainRecord): cardinal` |
| function | `GetFormVersion` | `function GetFormVersion (aeRecord: IwbMainRecord): cardinal` |
| function | `GetGridCell` | `function GetGridCell (aeRecord: IwbMainRecord): TwbGridCell` |
| function | `GetIsDeleted` | `function GetIsDeleted (aeRecord: IwbMainRecord): boolean` |
| function | `GetIsInitiallyDisabled` | `function GetIsInitiallyDisabled (aeRecord: IwbMainRecord): boolean` |
| function | `GetIsPersistent` | `function GetIsPersistent (aeRecord: IwbMainRecord): boolean` |
| function | `GetIsVisibleWhenDistant` | `function GetIsVisibleWhenDistant (aeRecord: IwbMainRecord): boolean` |
| function | `GetLoadOrderFormID` | `function GetLoadOrderFormID (aeRecord: IwbMainRecord): cardinal` |
| function | `GetPosition` | `function GetPosition (aeRecord: IwbMainRecord): TwbVector` |
| function | `GetRotation` | `function GetRotation (aeRecord: IwbMainRecord): TwbVector` |
| function | `HasPrecombinedMesh` | `function HasPrecombinedMesh (aeRecord: IwbMainRecord): boolean` |
| function | `HighestOverrideOrSelf` | `function HighestOverrideOrSelf (): IwbMainRecord` |
| function | `IsMaster` | `function IsMaster (aeRecord: IwbMainRecord): boolean` |
| function | `IsWinningOverride` | `function IsWinningOverride (aeRecord: IwbMainRecord): boolean` |
| function | `Master` | `function Master (aeRecord: IwbMainRecord): IwbMainRecord` |
| function | `MasterOrSelf` | `function MasterOrSelf (aeRecord: IwbMainRecord): IwbMainRecord` |
| function | `OverrideByIndex` | `function OverrideByIndex (aeRecord: IwbMainRecord; aiIndex: integer): IwbMainRecord` |
| function | `OverrideCount` | `function OverrideCount (aeRecord: IwbMainRecord): cardinal` |
| function | `PrecombinedMesh` | `function PrecombinedMesh (aeRecord: IwbMainRecord): string` |
| function | `ReferencedByIndex` | `function ReferencedByIndex (aeRecord: IwbMainRecord; aiIndex: integer): IwbMainRecord` |
| function | `ReferencedByCount` | `function ReferencedByCount (aeRecord: IwbMainRecord): cardinal` |
| function | `SetEditorID` | `function SetEditorID (aeRecord: IwbMainRecord): string` |
| procedure | `SetFormVersion` | `procedure SetFormVersion (aeRecord: IwbMainRecord; aiVersion: cardinal)` |
| function | `SetIsDeleted` | `function SetIsDeleted (aeRecord: IwbMainRecord; abFlag: boolean): boolean` |
| function | `SetIsInitiallyDisabled` | `function SetIsInitiallyDisabled (aeRecord: IwbMainRecord; abFlag: boolean): boolean` |
| function | `SetIsPersistent` | `function SetIsPersistent (aeRecord: IwbMainRecord; abFlag: boolean): boolean` |
| function | `SetIsVisibleWhenDistant` | `function SetIsVisibleWhenDistant (aeRecord: IwbMainRecord; abFlag: boolean): boolean` |
| function | `SetLoadOrderFormID` | `function SetLoadOrderFormID (aeRecord: IwbMainRecord; aiFormID: cardinal): cardinal` |
| procedure | `SetFormVCS1` | `procedure SetFormVCS1 (aeRecord: IwbMainRecord; aiValue: cardinal)` |
| procedure | `SetFormVCS2` | `procedure SetFormVCS2 (aeRecord: IwbMainRecord; aiValue: cardinal)` |
| function | `Signature` | `function Signature (aeRecord: IwbMainRecord): string` |
| procedure | `UpdateRefs` | `procedure UpdateRefs ()` |
| function | `WinningOverride` | `function WinningOverride (aeRecord: IwbMainRecord): IwbMainRecord` |
| function | `BaseRecord` | `function BaseRecord (aeRecord: IwbMainRecord): IwbMainRecord` |
| function | `BaseRecordID` | `function BaseRecordID (aeRecord: IwbMainRecord): cardinal` |
| procedure | `ChangeFormSignature` | `procedure ChangeFormSignature (aeRecord: IwbMainRecord; asNewSignature: string)` |
| function | `ChildGroup` | `function ChildGroup (aeRecord: IwbMainRecord): IwbGroupRecord` |
| function | `CompareExchangeFormID` | `function CompareExchangeFormID (aeRecord: IwbMainRecord; aiOldFormID: cardinal; aiNewFormID: cardinal): boolean` |
| function | `EditorID` | `function EditorID (aeRecord: IwbMainRecord): string` |
| function | `FixedFormID` | `function FixedFormID (aeRecord: IwbMainRecord): cardinal` |
| function | `FormID` | `function FormID (aeRecord: IwbMainRecord): cardinal` |
| function | `GetFormVCS1` | `function GetFormVCS1 (aeRecord: IwbMainRecord): cardinal` |
| function | `GetFormVCS2` | `function GetFormVCS2 (aeRecord: IwbMainRecord): cardinal` |
| function | `GetFormVersion` | `function GetFormVersion (aeRecord: IwbMainRecord): cardinal` |
| function | `GetGridCell` | `function GetGridCell (aeRecord: IwbMainRecord): TwbGridCell` |
| function | `GetIsDeleted` | `function GetIsDeleted (aeRecord: IwbMainRecord): boolean` |
| function | `GetIsInitiallyDisabled` | `function GetIsInitiallyDisabled (aeRecord: IwbMainRecord): boolean` |
| function | `GetIsPersistent` | `function GetIsPersistent (aeRecord: IwbMainRecord): boolean` |
| function | `GetIsVisibleWhenDistant` | `function GetIsVisibleWhenDistant (aeRecord: IwbMainRecord): boolean` |
| function | `GetLoadOrderFormID` | `function GetLoadOrderFormID (aeRecord: IwbMainRecord): cardinal` |
| function | `GetPosition` | `function GetPosition (aeRecord: IwbMainRecord): TwbVector` |
| function | `GetRotation` | `function GetRotation (aeRecord: IwbMainRecord): TwbVector` |
| function | `HasPrecombinedMesh` | `function HasPrecombinedMesh (aeRecord: IwbMainRecord): boolean` |
| function | `HighestOverrideOrSelf` | `function HighestOverrideOrSelf (): IwbMainRecord` |
| function | `IsMaster` | `function IsMaster (aeRecord: IwbMainRecord): boolean` |
| function | `IsWinningOverride` | `function IsWinningOverride (aeRecord: IwbMainRecord): boolean` |
| function | `Master` | `function Master (aeRecord: IwbMainRecord): IwbMainRecord` |
| function | `MasterOrSelf` | `function MasterOrSelf (aeRecord: IwbMainRecord): IwbMainRecord` |
| function | `OverrideByIndex` | `function OverrideByIndex (aeRecord: IwbMainRecord; aiIndex: integer): IwbMainRecord` |
| function | `OverrideCount` | `function OverrideCount (aeRecord: IwbMainRecord): cardinal` |
| function | `PrecombinedMesh` | `function PrecombinedMesh (aeRecord: IwbMainRecord): string` |
| function | `ReferencedByIndex` | `function ReferencedByIndex (aeRecord: IwbMainRecord; aiIndex: integer): IwbMainRecord` |
| function | `ReferencedByCount` | `function ReferencedByCount (aeRecord: IwbMainRecord): cardinal` |
| function | `SetEditorID` | `function SetEditorID (aeRecord: IwbMainRecord): string` |
| procedure | `SetFormVersion` | `procedure SetFormVersion (aeRecord: IwbMainRecord; aiVersion: cardinal)` |
| function | `SetIsDeleted` | `function SetIsDeleted (aeRecord: IwbMainRecord; abFlag: boolean): boolean` |
| function | `SetIsInitiallyDisabled` | `function SetIsInitiallyDisabled (aeRecord: IwbMainRecord; abFlag: boolean): boolean` |
| function | `SetIsPersistent` | `function SetIsPersistent (aeRecord: IwbMainRecord; abFlag: boolean): boolean` |
| function | `SetIsVisibleWhenDistant` | `function SetIsVisibleWhenDistant (aeRecord: IwbMainRecord; abFlag: boolean): boolean` |
| function | `SetLoadOrderFormID` | `function SetLoadOrderFormID (aeRecord: IwbMainRecord; aiFormID: cardinal): cardinal` |
| procedure | `SetFormVCS1` | `procedure SetFormVCS1 (aeRecord: IwbMainRecord; aiValue: cardinal)` |
| procedure | `SetFormVCS2` | `procedure SetFormVCS2 (aeRecord: IwbMainRecord; aiValue: cardinal)` |
| function | `Signature` | `function Signature (aeRecord: IwbMainRecord): string` |
| procedure | `UpdateRefs` | `procedure UpdateRefs ()` |
| function | `WinningOverride` | `function WinningOverride (aeRecord: IwbMainRecord): IwbMainRecord` |

## IwbResource Functions

| kind | name | declaration |
|---|---|---|
| procedure | `ResourceContainerList` | `procedure ResourceContainerList (akContainers: TwbFastStringList)` |
| procedure | `ResourceCopy` | `procedure ResourceCopy (asContainerName: string; asFilename: string; asPathOut: string)` |
| function | `ResourceCount` | `function ResourceCount (asFilename: string; akContainers: TStrings): cardinal` |
| function | `ResourceExists` | `function ResourceExists (asFilename: string): boolean` |
| procedure | `ResourceList` | `procedure ResourceList (asContainerName: string; akContainers: TStrings)` |
| function | `ResourceOpenData` | `function ResourceOpenData (asContainerName: string; asFilename: string): TBytesStream` |
| procedure | `ResourceContainerList` | `procedure ResourceContainerList (akContainers: TwbFastStringList)` |
| procedure | `ResourceCopy` | `procedure ResourceCopy (asContainerName: string; asFilename: string; asPathOut: string)` |
| function | `ResourceCount` | `function ResourceCount (asFilename: string; akContainers: TStrings): cardinal` |
| function | `ResourceExists` | `function ResourceExists (asFilename: string): boolean` |
| procedure | `ResourceList` | `procedure ResourceList (asContainerName: string; akContainers: TStrings)` |
| function | `ResourceOpenData` | `function ResourceOpenData (asContainerName: string; asFilename: string): TBytesStream` |

## Misc functions

| kind | name | declaration |
|---|---|---|
| procedure | `LocalizationGetStringsFromFile` | `procedure LocalizationGetStringsFromFile (asFilename: string; akListOut: TStrings)` |
| function | `wbAlphaBlend` | `function wbAlphaBlend (akDestinationDeviceContext: IInterface; aiDestinationX: integer; aiDestinationY: integer; aiDestinationWidth: integer; aiDestinationHeight: integer; akSourceDeviceContext: IInterface; aiSourceX: integer; aiSourceY: integer; aiSourceWidth: integer; aiSourceHeight: integer; aiAlpha: integer): boolean` |
| function | `wbBlockFromSubBlock` | `function wbBlockFromSubBlock (akSubBlock: TwbGridCell): TwbGridCell` |
| function | `wbCRC32Data` | `function wbCRC32Data (akData: TBytes): cardinal` |
| function | `wbCRC32File` | `function wbCRC32File (asFilename: string): cardinal` |
| function | `wbCRC32Resource` | `function wbCRC32Resource (asContainerName: string; asFileName: string): cardinal` |
| procedure | `wbFindREFRsByBase` | `procedure wbFindREFRsByBase (aeREFR: IwbMainRecord; asSignatures: string; aiFlags: integer; akOutList: TList)` |
| procedure | `wbFlipBitmap` | `procedure wbFlipBitmap (akBitmap: TBitmap; aiAxes: integer)` |
| procedure | `wbGetSiblingRecords` | `procedure wbGetSiblingRecords (aeRecord: IwbElement; asSignatures: string; abIncludeOverrides: boolean; akOutList: TList)` |
| function | `wbGridCellToGroupLabel` | `function wbGridCellToGroupLabel (akGridCell: TwbGridCell): cardinal` |
| function | `wbIsInGridCell` | `function wbIsInGridCell (akPosition: TwbVector; akGridCell: TwbGridCell): boolean` |
| function | `wbMD5Data` | `function wbMD5Data (akData: TBytes): cardinal` |
| function | `wbMD5File` | `function wbMD5File (asFilename: string): cardinal` |
| function | `wbNormalizeResourceName` | `function wbNormalizeResourceName (asResourceName: string; akResourceType: TGameResourceType): string` |
| function | `wbPositionToGridCell` | `function wbPositionToGridCell (akPosition: TwbVector): TwbGridCell` |
| function | `wbSHA1Data` | `function wbSHA1Data (akData: TBytes): cardinal` |
| function | `wbSHA1File` | `function wbSHA1File (asFilename: string): cardinal` |
| function | `wbStringListInString` | `function wbStringListInString (akList: TStringList; asSubstring: string): integer` |
| function | `wbSubBlockFromGridCell` | `function wbSubBlockFromGridCell (akGridCell: TwbGridCell): TwbGridCell` |
| procedure | `LocalizationGetStringsFromFile` | `procedure LocalizationGetStringsFromFile (asFilename: string; akListOut: TStrings)` |
| function | `wbAlphaBlend` | `function wbAlphaBlend (akDestinationDeviceContext: IInterface; aiDestinationX: integer; aiDestinationY: integer; aiDestinationWidth: integer; aiDestinationHeight: integer; akSourceDeviceContext: IInterface; aiSourceX: integer; aiSourceY: integer; aiSourceWidth: integer; aiSourceHeight: integer; aiAlpha: integer): boolean` |
| function | `wbBlockFromSubBlock` | `function wbBlockFromSubBlock (akSubBlock: TwbGridCell): TwbGridCell` |
| function | `wbCRC32Data` | `function wbCRC32Data (akData: TBytes): cardinal` |
| function | `wbCRC32File` | `function wbCRC32File (asFilename: string): cardinal` |
| function | `wbCRC32Resource` | `function wbCRC32Resource (asContainerName: string; asFileName: string): cardinal` |
| procedure | `wbFindREFRsByBase` | `procedure wbFindREFRsByBase (aeREFR: IwbMainRecord; asSignatures: string; aiFlags: integer; akOutList: TList)` |
| procedure | `wbFlipBitmap` | `procedure wbFlipBitmap (akBitmap: TBitmap; aiAxes: integer)` |
| procedure | `wbGetSiblingRecords` | `procedure wbGetSiblingRecords (aeRecord: IwbElement; asSignatures: string; abIncludeOverrides: boolean; akOutList: TList)` |
| function | `wbGridCellToGroupLabel` | `function wbGridCellToGroupLabel (akGridCell: TwbGridCell): cardinal` |
| function | `wbIsInGridCell` | `function wbIsInGridCell (akPosition: TwbVector; akGridCell: TwbGridCell): boolean` |
| function | `wbMD5Data` | `function wbMD5Data (akData: TBytes): cardinal` |
| function | `wbMD5File` | `function wbMD5File (asFilename: string): cardinal` |
| function | `wbNormalizeResourceName` | `function wbNormalizeResourceName (asResourceName: string; akResourceType: TGameResourceType): string` |
| function | `wbPositionToGridCell` | `function wbPositionToGridCell (akPosition: TwbVector): TwbGridCell` |
| function | `wbSHA1Data` | `function wbSHA1Data (akData: TBytes): cardinal` |
| function | `wbSHA1File` | `function wbSHA1File (asFilename: string): cardinal` |
| function | `wbStringListInString` | `function wbStringListInString (akList: TStringList; asSubstring: string): integer` |
| function | `wbSubBlockFromGridCell` | `function wbSubBlockFromGridCell (akGridCell: TwbGridCell): TwbGridCell` |

## NIF functions

| kind | name | declaration |
|---|---|---|
| function | `NifBlockList` | `function NifBlockList (akData: TBytes; akListOut: TStrings): boolean` |
| function | `NifTextureList` | `function NifTextureList (akData: TBytes; akListOut: TStrings): boolean` |
| function | `NifTextureListResource` | `function NifTextureListResource (akData: Variant; akListOut: TStrings): boolean` |
| function | `NifTextureListUVRange` | `function NifTextureListUVRange (akData: TBytes; afUVRange: Single; akListOut: TStrings): boolean` |
| function | `NifBlockList` | `function NifBlockList (akData: TBytes; akListOut: TStrings): boolean` |
| function | `NifTextureList` | `function NifTextureList (akData: TBytes; akListOut: TStrings): boolean` |
| function | `NifTextureListResource` | `function NifTextureListResource (akData: Variant; akListOut: TStrings): boolean` |
| function | `NifTextureListUVRange` | `function NifTextureListUVRange (akData: TBytes; afUVRange: Single; akListOut: TStrings): boolean` |

## Declared types

- `IwbElement` = IInterface  (line 77)
- `IwbContainerBase` = IInterface  (line 79)
- `IwbContainer` = IInterface  (line 81)
- `IwbSortableContainer` = IInterface  (line 83)
- `IwbDataContainer` = IInterface  (line 85)
- `IwbFileHeader` = IInterface  (line 87)
- `IwbRecord` = IInterface  (line 89)
- `IwbGroupRecord` = IInterface  (line 91)
- `IwbMainRecord` = IInterface  (line 93)
- `IwbSubRecord` = IInterface  (line 95)
- `IwbFile` = IInterface  (line 97)
- `IwbContainerElementRef` = IInterface  (line 99)
- `IwbResource` = IInterface  (line 101)
- `IwbResourceContainer` = IInterface  (line 103)
- `IwbBA2File` = IInterface  (line 105)
- `IwbBSAFile` = IInterface  (line 107)
- `IwbFolder` = IInterface  (line 109)
- `TwbDefType` = IInterface  (line 111)
- `TwbElementState` = IInterface  (line 113)
- `TwbElementType` = IInterface  (line 115)
- `TwbGridCell` = IInterface  (line 117)
- `TwbVector` = IInterface  (line 119)
- `TwbFastStringList` = IInterface  (line 121)
- `TGameResourceType` = IInterface  (line 123)

## Constants

- `LowInteger` = Low(Integer)  (line 66)
- `HighInteger` = High(Integer)  (line 67)
- `IwbElement` = IInterface  (line 77)
- `IwbContainerBase` = IInterface  (line 79)
- `IwbContainer` = IInterface  (line 81)
- `IwbSortableContainer` = IInterface  (line 83)
- `IwbDataContainer` = IInterface  (line 85)
- `IwbFileHeader` = IInterface  (line 87)
- `IwbRecord` = IInterface  (line 89)
- `IwbGroupRecord` = IInterface  (line 91)
- `IwbMainRecord` = IInterface  (line 93)
- `IwbSubRecord` = IInterface  (line 95)
- `IwbFile` = IInterface  (line 97)
- `IwbContainerElementRef` = IInterface  (line 99)
- `IwbResource` = IInterface  (line 101)
- `IwbResourceContainer` = IInterface  (line 103)
- `IwbBA2File` = IInterface  (line 105)
- `IwbBSAFile` = IInterface  (line 107)
- `IwbFolder` = IInterface  (line 109)
- `TwbDefType` = IInterface  (line 111)
- `TwbElementState` = IInterface  (line 113)
- `TwbElementType` = IInterface  (line 115)
- `TwbGridCell` = IInterface  (line 117)
- `TwbVector` = IInterface  (line 119)
- `TwbFastStringList` = IInterface  (line 121)
- `TGameResourceType` = IInterface  (line 123)
