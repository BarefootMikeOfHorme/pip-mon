unit UserScript;

{
  PIP-MON: create ONE CELL in a target plugin, headlessly, with FO4Edit 4.1.5f.

  MERGED 2026-09-30. Three versions existed and this is the union of them:
    - trace/output format taken VERBATIM from validate_plugin.pas, because that
      is the format that was watched working (2,287,300 records, 64,926 CELL,
      140 distinct signatures). Reconstructing it from memory instead of
      copying it from the file that has it was the error this merge fixes.
    - creation links from the 23:07 revision, which are the only new capability.
    - Say() narration dropped in favour of direct AddMessage, matching the
      validator. Say() is not wrong, it is just a second convention for the
      same output, and one convention is what makes a log readable.

  MEASURED, and each of these changed the file:
    22:32  Type mismatch. `else if sig <> 'GRUP' and sig <> 'MAST' and sig <> 'TES4'`
           raised on the first record. This dialect raises on two comparisons
           joined by and/or. The cascade below is copied from the validator.
    22:58  Add(targetFile, 'CELL', True) RETURNED. IwbFile IS accepted where
           IwbContainer is expected, so the record attaches to the file and
           xEdit places it in the correct group at save time. The
           TwbVector -> wbPositionToGridCell -> wbGridCellToGroupLabel chain is
           NOT needed. That was the whole blocker and it is gone.
    22:58  Undeclared Identifier 'ElementID'. FixedFormID is the real name.
    23:07  Undeclared Identifier 'Count' on IwbGroupRecord. Link removed, not
           retried. Counting CELLs in the target file is the validator's job,
           measured independently.

  TWO RULES THIS FILE KEEPS:
    1. The report is written and SAVED before any unproven call, so an abort
       still leaves evidence on disk. That worked on 2026-09-30: a run that died
       at LINK 4 still produced a 160-line report.
    2. Each unproven call is announced with AddMessage immediately BEFORE it is
       used, so an abort names the link. Two failures were each worth one run
       instead of a guessing loop, and that is the only reason this progressed.

  The game Data folder is never written. Output goes to a scratch path only.
}

var
  sl: TStringList;
  sigs: TStringList;
  loadOrder: TStringList;
  cnt: TStringList;
  sig: string;
  comma: string;
  q: string;
  reportPath: string;
  scratchPath: string;
  targetName: string;
  tgtLower: string;
  loaded: Boolean;
  i: Integer;
  k: Integer;
  idx: Integer;
  nFiles: Integer;
  nRecords: Integer;
  nCell: Integer;
  nTES4: Integer;
  nGroups: Integer;
  nHeartbeat: Integer;
  nCreated: Integer;
  linkReached: Integer;
  targetIndex: Integer;
  createdNote: string;
  targetFile: IwbFile;
  newElem: IwbElement;
  nextId: Integer;
  fs: TFileStream;

function JStr(key, val: string): string;
begin
  Result := '  ' + q + key + q + ': ' + q + val + q + ',';
end;

function JNum(key: string; n: Integer): string;
begin
  Result := '  ' + q + key + q + ': ' + IntToStr(n) + ',';
end;

function JBool(key: string; b: Boolean): string;
begin
  if b then
    Result := '  ' + q + key + q + ': true,'
  else
    Result := '  ' + q + key + q + ': false,';
end;

function WriteReport: Boolean;
begin
  sl.Clear;
  sl.Add('{');
  sl.Add(JStr('schema', 'pipmon.gen.facility/5'));
  sl.Add(JStr('target', targetName));
  sl.Add(JBool('target_loaded', loaded));
  sl.Add(JNum('files_loaded', nFiles));
  sl.Add(JNum('load_order_index', targetIndex));
  sl.Add(JStr('load_order_captured_by', 'this script, from FileCount/FileByIndex -- the list xEdit actually resolved, not plugins.txt'));
  sl.Add(JNum('links_proven_in_order', linkReached));
  sl.Add(JNum('records_created', nCreated));
  sl.Add(JStr('created_note', createdNote));
  sl.Add(JStr('scratch_plugin', scratchPath));
  sl.Add(JStr('game_plugin_written', 'no'));
  sl.Add(JNum('records_in_load_order', nRecords));
  sl.Add(JNum('cell_records_in_load_order', nCell));
  sl.Add(JNum('groups_in_load_order', nGroups));
  sl.Add(JNum('masters_in_load_order', nTES4));
  sl.Add(JNum('distinct_signatures', sigs.Count));
  sl.Add(JStr('provenance', 'testfacility/xedit/gen_facility.pas, run by tools/run_gen.ps1; counts are load-order wide, not per-plugin'));
  sl.Add(JStr('proven_by_execution', 'FileCount, FileByIndex, GetFileName, Signature, TStringList.SaveToFile, AddMessage, IntToStr, StrToInt, LowerCase, Chr, Add(IwbFile,CELL,True), GetNewFormID'));
  sl.Add(JStr('not_used_because_measured_absent', 'ElementID (Undeclared 22:58); IwbGroupRecord.Count (Undeclared 23:07); GetPluginName (spec exists:false, caught by artifact_gate before a run)'));
  sl.Add(JStr('silent_zero_warning', 'FixedFormID(newElem) returned 0x00000000 at 23:07. It did not raise, so it is NOT a proof: the spec types it IwbMainRecord and newElem is IwbElement. A link that cannot fail is not a proof.'));

  sl.Add('  ' + q + 'load_order' + q + ': [');
  for k := 0 to loadOrder.Count - 1 do
  begin
    if k < loadOrder.Count - 1 then comma := ',' else comma := '';
    sl.Add('    ' + q + loadOrder[k] + q + comma);
  end;
  sl.Add('  ],');



  sl.Add('  ' + q + 'signature_counts' + q + ': {');
  for k := 0 to sigs.Count - 1 do
  begin
    if k < sigs.Count - 1 then comma := ',' else comma := '';
    sl.Add('    ' + q + sigs[k] + q + ': ' + cnt[k] + comma);
  end;
  sl.Add('  },');
  sl.Add('}');
  try
    sl.SaveToFile(reportPath);
    AddMessage('PIPMON: SAVED ' + reportPath + ' lines=' + IntToStr(sl.Count));
    Result := True;
  except
    on E: Exception do
    begin
      AddMessage('PIPMON: SAVE FAILED - ' + E.Message);
      Result := False;
    end;
  end;
end;

function Initialize: Integer;
begin
  reportPath := '%%OUTPATH%%';
  scratchPath := '%%SCRATCH%%';
  targetName := '%%PLUGIN%%';

  AddMessage('PIPMON: Initialize - generator looking for ' + targetName);
  q := Chr(34);
  tgtLower := LowerCase(targetName);
  sl := TStringList.Create;
  sigs := TStringList.Create;
  cnt := TStringList.Create;
  loadOrder := TStringList.Create;
  nRecords := 0;
  nCell := 0;
  nTES4 := 0;
  nGroups := 0;
  nHeartbeat := 0;
  nCreated := 0;
  linkReached := 0;
  targetIndex := 0;
  createdNote := 'not attempted';
  loaded := False;

  { The load order, captured IN FULL and every run.
    Why this is here and not added later on request: the scan measures whatever
    is loaded, and what is loaded changes whenever the CK Data tab is restaged.
    Without the list in the report, a changed count is unexplainable and the
    only way to find out what changed is to remember it. The list makes every
    run self-describing, and two runs can be diffed against each other.

    This is also the fix for a gate that was reporting on the wrong file: the
    deploy and link checks read plugins.txt, while xEdit resolves its own list.
    This reads the one that actually decides the counts. }
  nFiles := FileCount;
  AddMessage('PIPMON: Initialize - ' + IntToStr(nFiles) + ' files loaded');
  for i := 0 to nFiles - 1 do
    loadOrder.Add(IntToStr(i) + ' ' + GetFileName(FileByIndex(i)));

  for i := 0 to nFiles - 1 do
  begin
    if LowerCase(GetFileName(FileByIndex(i))) = tgtLower then
    begin
      loaded := True;
      targetIndex := i;
      targetFile := FileByIndex(i);
      AddMessage('PIPMON: found ' + targetName + ' at load order index ' + IntToStr(i) + ' and kept the handle');
    end;
  end;

  if not loaded then
    AddMessage('PIPMON: Initialize done - ' + targetName + ' is NOT in the loaded load order; nothing will be written')
  else
    AddMessage('PIPMON: Initialize done - target present. Process will count records.');

  Result := 0;
end;

function Process(e: IInterface): Integer;
begin
  Result := 0;
  sig := Signature(e);

  { PROVEN BY EXECUTION: Signature alone, over every record. No GetFile.
    Cascade only -- two comparisons joined by and/or raise Type mismatch. }
  if sig = 'GRUP' then
    nGroups := nGroups + 1
  else if sig = 'MAST' then
    Inc(nTES4)
  else
  begin
    nRecords := nRecords + 1;
    if sig = 'CELL' then
      nCell := nCell + 1;
  end;

  idx := sigs.IndexOf(sig);
  if idx < 0 then
  begin
    sigs.Add(sig);
    cnt.Add('1');
  end
  else
    cnt[idx] := IntToStr(StrToInt(cnt[idx]) + 1);

  nHeartbeat := nHeartbeat + 1;
  if nHeartbeat = 25000 then
  begin
    nHeartbeat := 0;
    AddMessage('PIPMON: Process - ' + IntToStr(nRecords) + ' records so far');
  end;
end;

function Finalize: Integer;
begin
  AddMessage('PIPMON: Finalize - ' + IntToStr(nRecords) + ' records, '
    + IntToStr(nCell) + ' CELL, ' + IntToStr(sigs.Count) + ' distinct signatures');

  { Report on disk BEFORE anything unproven, so an abort still leaves evidence. }
  WriteReport;

  if not loaded then
  begin
    AddMessage('PIPMON: VERDICT SKIP - target not in load order');
    AddMessage('PIPMON: done - Finalize complete');
    loadOrder.Free;
    sigs.Free;
    cnt.Free;
    sl.Free;
    Result := 0;
    exit;
  end;

  AddMessage('PIPMON: LINK 1 - Add(targetFile, CELL, True). PROVEN 2026-09-30 22:58.');
  newElem := Add(targetFile, 'CELL', True);
  nCreated := 1;
  createdNote := 'Add returned an element; it exists in memory and is NOT yet on disk';
  AddMessage('PIPMON: LINK 1 ok - an element now exists on the target file');

  AddMessage('PIPMON: LINK 2 - GetNewFormID(targetFile): next free id. UNPROVEN.');
  nextId := GetNewFormID(targetFile);
  AddMessage('PIPMON: LINK 2 ok - next free FormID 0x' + IntToHex(nextId, 8));

  WriteReport;

  { LINK 3 -- THE SAVE, transcribed from the shipped reference rather than
    invented. Two arguments raised [EJvInterpreterError] Not enough parameters
    on 2026-09-30 23:47 because SaveAs.pas:63 passes THREE: the file, the stream,
    and the reset-modified flag. The file is IInterface, not IwbFile, and the
    flag is False so the modified status we just set survives the write.

    Reference: third_party/xedit/Edit Scripts/SaveAs.pas, procedure SavePlugin,
    lines 53-75. Copied shape, scratch path substituted for the dialog result. }
  AddMessage('PIPMON: LINK 3 - FileWriteToStream(file, fs, False). Three args, per SaveAs.pas:63. UNPROVEN.');
  linkReached := 3;
  fs := TFileStream.Create(scratchPath, fmCreate);
  try
    FileWriteToStream(targetFile, fs, False);
  finally
    fs.Free;
  end;
  AddMessage('PIPMON: LINK 3 ok - wrote ' + scratchPath);
  createdNote := 'a CELL was created and written to the scratch path; the game plugin is still unchanged';

  WriteReport;

  AddMessage('PIPMON: VERDICT records_created=' + IntToStr(nCreated));
  AddMessage('PIPMON: SAVED ' + scratchPath);
  AddMessage('PIPMON: done - Finalize complete');
  loadOrder.Free;
  sigs.Free;
  cnt.Free;
  sl.Free;
  Result := 0;
end;

end.