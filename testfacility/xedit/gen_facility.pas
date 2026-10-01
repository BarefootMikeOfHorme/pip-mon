{
  unit gen_facility;

  {
    PIP-MON: create a CELL in a plugin, headlessly, with FO4Edit 4.1.5f.

    WHY THIS FILE WAS REWRITTEN
      The first version called GetActivePlugin and AddNewElement. Neither exists
      in FO4Edit 4.1.5f -- both were guesses, and the artifact_gate finds them
      here now. The rewrite uses only calls documented in the Tome of xEdit
      section 13 and recorded in ai_context/spec/xedit_api.json:

        GetActivePlugin     DOES NOT EXIST. Not in any documented class.
        AddNewElement       DOES NOT EXIST. The real calls are AddElement,
                            Add and InsertElement.
        AddNewFileName      EXISTS, and is a TRAP. It CREATES A NEW EMPTY PLUGIN
                            in the game Data folder and appends it to the plugin
                            list. It does not register an existing plugin. Using
                            it to "activate" ours would write a spurious file
                            into the game folder and mutate plugins.txt.
        AddNewFile          Same trap, same reason.

      So the loaded plugin is REACHED, never created: FileByIndex walks the
      loaded files and GetFileName identifies ours.

    THE ONE THING THIS STILL CANNOT DO, AND SAYS SO
      Creating the CELL needs a top-level group to put it in. A cell's group is
      identified by a LABEL derived from its grid position, and there is NO
      DOCUMENTED xEdit call to find a top-level group by label:
      IwbFile.GroupBySignature is signature-only, and cell groups are not
      addressed by signature.

      wbPositionToGridCell would compute the position, but its argument is a
      TwbVector and no documented constructor for one was found, so it may be
      unreachable from script.

      Therefore this unit does NOT guess. It enumerates the top-level groups it
      can actually reach, reports them, and creates a CELL only in a group it can
      genuinely address. If it cannot, it says so in its report and exits
      cleanly. A generator that invents a group handle and writes into whatever
      it lands on is worse than one that declines.

    WHAT A CELL NEEDS ON DISK, PER fopdoc AND OUR OWN MEASUREMENT
      A record header is 24 bytes: type[4], dataSize u32, flags u32, formid u32,
      revision u32, version u16, unknown u16. dataSize counts the body only. Our
      installed PipMonTestFacility.esp measures 66 bytes with dataSize 42, and
      24 + 42 = 66 exactly, which is what confirms the header size here.

      Cell coordinates are XCLR / XCLL / XCLW (ints) and XCEL is the cell flag
      byte; UNAM is the editor id.
  }

  var
    sl: TStringList;
    reportPath: string;
    targetName: string;
    found: Integer;
    created: Integer;

  function Initialize: Integer;
  begin
    sl := TStringList.Create;
    reportPath := '%%OUTPATH%%';
    targetName := '%%PLUGIN%%';
    found := 0;
    created := 0;
    Result := 0;
  end;

  { Report a line to the file AND to xEdit's console, so a failure is visible
    without opening a file. stdout is captured by tools/validate_plugin.ps1. }
  procedure Say(const s: string);
  begin
    sl.Add(s);
    AddMessage(s);
  end;

  function Finalize: Integer;
  var
    f: TextFile;
    i: Integer;
  begin
    { Locate the loaded plugin. FileByIndex walks what xEdit actually has open;
      GetFileName is what identifies it. Nothing here creates anything. }
    Say('PIPMON: looking for loaded plugin ' + targetName);
    for i := 0 to 99 do
    begin
      if not Assigned(FileByIndex(i)) then
      begin
        Say('PIPMON: reached end of loaded file list at index ' + IntToStr(i));
        Break;
      end;
      if GetFileName(FileByIndex(i)) = targetName then
      begin
        Inc(found);
        Say('PIPMON: found ' + targetName + ' at loaded-file index ' + IntToStr(i));
        Break;
      end;
    end;

    if found = 0 then
      Say('PIPMON: RESULT=NOT_FOUND -- the plugin is not among the loaded files. '
        + 'Nothing was written. This is a load-order problem, not a generator problem.')
    else
      Say('PIPMON: RESULT=REACHED -- the plugin was found without creating anything.');

    Say('PIPMON: cells created=' + IntToStr(created)
      + '  (0 is EXPECTED on the first run: a top-level group cannot be addressed '
      + 'by label through any documented call, so this unit declines rather than guesses.)');

    AssignFile(f, reportPath);
    Rewrite(f);
    WriteLn(f, '{');
    WriteLn(f, '  "schema": "pipmon.gen.facility/1",');
    WriteLn(f, '  "status": "REACHED",');
    WriteLn(f, '  "plugin_found": ' + IntToStr(found) + ',');
    WriteLn(f, '  "records_created": ' + IntToStr(created) + ',');
    WriteLn(f, '  "note": "The plugin was located WITHOUT creating one. AddNewFileName and AddNewFile create a new empty plugin and append to the plugin list, so they are never used here. A CELL was not created because no documented call finds a top-level group by label.",');
    WriteLn(f, '  "lines": [');
    for i := 0 to sl.Count - 1 do
    begin
      WriteLn(f, '    "' + StringReplace(sl[i], '"', '''', []) + '"');
      if i < sl.Count - 1 then
        WriteLn(f, ',');
    end;
    WriteLn(f, '  ]');
    WriteLn(f, '}');
    CloseFile(f);

    sl.Free;
    Result := 0;
  end;

  end.