unit UserScript;

{
  PIP-MON: reach a loaded plugin and report on it, headlessly, with FO4Edit 4.1.5f.

  ---------------------------------------------------------------------------
  WHAT CHANGED IN THIS REVISION, and why each was fatal
  ---------------------------------------------------------------------------
  1. AssignFile / Rewrite / WriteLn / CloseFile  -- REMOVED.
     The previous version wrote its report with them. They are ordinary Delphi,
     they are NOT available in xEdit's Pascal, and a real run on 2026-09-30
     aborted at 02:17 with [EJvInterpreterError] Undeclared Identifier
     'AssignFile' after the loader had finished. The report is now written with
     TStringList.SaveToFile, which is proven -- it wrote a 3,704 byte report
     across 163 lines on 2026-09-30 20:33.

  2. StringReplace  -- REMOVED.
     Needed only to escape quotes for hand-built JSON. Unproven, and the report
     format does not need it: lines are emitted through the same JStr helpers
     the validator uses, which are plain string concatenation and are proven.

  3. The `for i := 0 to 99 do if not Assigned(FileByIndex(i))` probe -- REPLACED
     with a loop bounded by FileCount.
     The old probe walked off the end of the loaded-file list on purpose and
     relied on Assigned() catching it. FileCount is now PROVEN by execution
     (2026-09-30 20:33: it bounded a loop that ran to completion over the load
     order and located our plugin at index 54), so there is no reason to ask the
     interpreter to survive an out-of-range call.

  ---------------------------------------------------------------------------
  WHAT THIS DELIBERATELY DOES NOT DO
  ---------------------------------------------------------------------------
  It does not create a CELL yet, and that is a decision rather than an omission.

  Creating a record needs a top-level group to put it in, and a cell's group is
  addressed by a LABEL derived from its grid position. The chain that would get
  there is visible in the spec:

      TwbVector  ->  wbPositionToGridCell  ->  wbGridCellToGroupLabel  ->  the group

  All four are listed as existing in ai_context/spec/xedit_api.json, and none is
  proven by execution here. In particular there is no proven way to construct a
  TwbVector from script, and an unproven call does not fail politely in this
  dialect -- it raises, and the whole run aborts with nothing written. So
  calling it blind would trade a known, reported state for an unknown one.

  The next experiment is deliberately narrow: prove ONE link (a TwbVector
  construction, or wbGridCellToGroupLabel on a literal) in isolation, in
  Finalize, where a raise costs one run and says exactly where. Then the chain
  gets built one proven link at a time. Until then this unit reaches, reports,
  and declines -- and says that it declined, so the report cannot be mistaken
  for a generator that quietly did nothing.

  A generator that guesses a group handle writes into whatever it lands on. That
  is worse than one that declines, and it is worse here specifically because the
  target is a plugin someone will load into a real save.
}

var
  sl: TStringList;
  sigs: TStringList;
  cnt: TStringList;
  reportPath: string;
  targetName: string;
  targetLower: string;
  q: string;
  comma: string;
  sig: string;
  loaded: Boolean;
  found: Integer;
  nFiles: Integer;
  nRecords: Integer;
  nCell: Integer;
  i: Integer;
  k: Integer;
  idx: Integer;

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

function Initialize: Integer;
begin
  reportPath := '%%OUTPATH%%';
  targetName := '%%PLUGIN%%';

  AddMessage('PIPMON: Initialize - generator looking for ' + targetName);
  q := Chr(34);
  targetLower := LowerCase(targetName);
  sl := TStringList.Create;
  sigs := TStringList.Create;
  cnt := TStringList.Create;
  loaded := False;
  found := 0;
  nFiles := 0;
  nRecords := 0;
  nCell := 0;

  { PROVEN BY EXECUTION 2026-09-30: FileCount, FileByIndex, GetFileName. }
  nFiles := FileCount;
  AddMessage('PIPMON: Initialize - ' + IntToStr(nFiles) + ' files loaded');
  for i := 0 to nFiles - 1 do
  begin
    if LowerCase(GetFileName(FileByIndex(i))) = targetLower then
    begin
      loaded := True;
      found := i;
      AddMessage('PIPMON: Initialize - REACHED ' + targetName + ' at index ' + IntToStr(i)
        + ' WITHOUT creating anything');
    end;
  end;

  if not loaded then
    AddMessage('PIPMON: Initialize - NOT among the loaded files. That is a load-order '
      + 'problem, not a generator problem. Nothing will be written.');

  Result := 0;
end;

function Process(e: IInterface): Integer;
begin
  Result := 0;
  sig := Signature(e);
  if sig = 'CELL' then
  begin
    nCell := nCell + 1;
    Inc(nRecords);
  end
  else if sig <> 'GRUP' and sig <> 'MAST' and sig <> 'TES4' then
    Inc(nRecords);

  idx := sigs.IndexOf(sig);
  if idx < 0 then
  begin
    sigs.Add(sig);
    cnt.Add('1');
  end
  else
    cnt[idx] := IntToStr(StrToInt(cnt[idx]) + 1);
end;

function Finalize: Integer;
begin
  AddMessage('PIPMON: Finalize - reporting. No record was created; see declined_reason.');

  sl.Add('{');
  sl.Add(JStr('schema', 'pipmon.gen.facility/2'));
  if loaded then
    sl.Add(JStr('status', 'REACHED'))
  else
    sl.Add(JStr('status', 'NOT_FOUND'));
  sl.Add(JStr('target', targetName));
  sl.Add(JBool('plugin_found', loaded));
  sl.Add(JNum('target_index', found));
  sl.Add(JNum('files_loaded', nFiles));
  sl.Add(JNum('records_created', 0));
  sl.Add(JStr('declined_reason', 'a CELL needs a top-level group addressed by a grid-derived label, and no link in that chain (TwbVector -> wbPositionToGridCell -> wbGridCellToGroupLabel) is proven by execution; an unproven call raises and aborts the run with nothing written'));
  sl.Add(JStr('provenance', 'testfacility/xedit/gen_facility.pas, run by tools/run_gen.ps1'));
  sl.Add(JStr('proven_by_execution', 'FileCount, FileByIndex, GetFileName, Signature, TStringList.SaveToFile, AddMessage, IntToStr, StrToInt, LowerCase, Chr'));
  sl.Add(JStr('removed_as_fatal', 'AssignFile, Rewrite, WriteLn, CloseFile (not available in xEdit Pascal -- real abort 2026-09-30 02:17); StringReplace (unproven, and unnecessary)'));

  sl.Add('  ' + q + 'signature_counts' + q + ': {');
  for k := 0 to sigs.Count - 1 do
  begin
    if k < sigs.Count - 1 then comma := ',' else comma := '';
    sl.Add('    ' + q + sigs[k] + q + ': ' + cnt[k] + comma);
  end;
  sl.Add('  },');
  sl.Add(JNum('records_in_load_order', nRecords));
  sl.Add(JNum('cell_records_in_load_order', nCell));
  sl.Add('  ' + q + 'not_checked' + q + ': [');
  sl.Add('    ' + q + 'any semantic validity of any record' + q + ',');
  sl.Add('    ' + q + 'whether the target plugin has a writable top-level group' + q);
  sl.Add('  ]');
  sl.Add('}');

  sl.SaveToFile(reportPath);
  AddMessage('PIPMON: VERDICT ' + sl[3]);
  AddMessage('PIPMON: SAVED ' + reportPath);
  AddMessage('PIPMON: SAVED lines=' + IntToStr(sl.Count) + ' signatures=' + IntToStr(sigs.Count));
  AddMessage('PIPMON: done - Finalize complete');

  cnt.Free;
  sigs.Free;
  sl.Free;
  Result := 0;
end;

end.
