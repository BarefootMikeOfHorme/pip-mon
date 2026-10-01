unit UserScript;

{
  PIP-MON: validate ONE plugin (the target) and emit a verdict.

  Job:     report measured facts about targetName and end with PASS, FAIL or SKIP.
  Not job: inventory of the load order, repair, semantic validation.

  Verdicts (SKIP is not PASS: the property it covers is UNVERIFIED)
    SKIP  target is not in the loaded load order, so nothing could be checked
    FAIL  target loaded but is header-only, or has records and no CELL
    PASS  target loaded, has records, and has at least one CELL

  Constraints this file respects (earlier versions died on these)
    - no AssignFile/WriteLn: the report is written with TStringList.SaveToFile
    - every function is declared before its first use
    - no try/except
    - GetFile/GetFileName/FileCount/FileByIndex/MasterCount/MasterByIndex are
      standard xEdit script calls. FIRST RUN IS THE TEST for them: a compile
      error shows as a dialog and costs one load.

  Edit ONLY the two lines marked GENERATOR in Initialize.
  Failure history lives in HANDOVER.md, not here.
}

var
  sl: TStringList;
  sigs: TStringList;
  cnt: TStringList;
  masterNames: TStringList;
  reportPath: string;
  targetName: string;
  tgtLower: string;
  verdict: string;
  reason: string;
  q: string;
  sig: string;
  comma: string;
  tgt: IInterface;
  loaded: Boolean;
  nRecords: Integer;
  nCell: Integer;
  nMasters: Integer;
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
  targetName := 'PipMonTestFacility.esp';                                                              // GENERATOR
  reportPath := 'C:\Users\Administrator\Desktop\Pip-mon Script Management system\runs\watch\xedit-validation-report.json'; // GENERATOR

  q := Chr(34);
  tgtLower := LowerCase(targetName);
  sl := TStringList.Create;
  sigs := TStringList.Create;
  cnt := TStringList.Create;
  masterNames := TStringList.Create;
  nRecords := 0;
  nCell := 0;
  nMasters := 0;
  loaded := False;

  for i := 0 to FileCount - 1 do
  begin
    if LowerCase(GetFileName(FileByIndex(i))) = tgtLower then
    begin
      tgt := FileByIndex(i);
      loaded := True;
    end;
  end;

  if loaded then
  begin
    nMasters := MasterCount(tgt);
    for k := 0 to nMasters - 1 do
      masterNames.Add(GetFileName(MasterByIndex(tgt, k)));
  end;

  Result := 0;
end;

function Process(e: IInterface): Integer;
begin
  Result := 0;

  if loaded then
  begin
    if LowerCase(GetFileName(GetFile(e))) = tgtLower then
    begin
      sig := Signature(e);
      if sig <> 'TES4' then
      begin
        nRecords := nRecords + 1;
        if sig = 'CELL' then
          nCell := nCell + 1;

        idx := sigs.IndexOf(sig);
        if idx < 0 then
        begin
          sigs.Add(sig);
          cnt.Add('1');
        end
        else
          cnt[idx] := IntToStr(StrToInt(cnt[idx]) + 1);
      end;
    end;
  end;
end;

function Finalize: Integer;
begin
  if not loaded then
  begin
    verdict := 'SKIP';
    reason := 'target plugin is not in the loaded load order; nothing was checked';
  end
  else if nRecords = 0 then
  begin
    verdict := 'FAIL';
    reason := 'target plugin is header-only: 0 records';
  end
  else if nCell = 0 then
  begin
    verdict := 'FAIL';
    reason := 'target plugin has records but no CELL record';
  end
  else
  begin
    verdict := 'PASS';
    reason := 'header loaded, records parse, at least one CELL; semantics not checked';
  end;

  sl.Add('{');
  sl.Add(JStr('schema', 'pipmon.plugin.validation/4'));
  sl.Add(JStr('target', targetName));
  sl.Add(JStr('verdict', verdict));
  sl.Add(JStr('reason', reason));
  sl.Add(JBool('target_loaded', loaded));
  sl.Add(JNum('records', nRecords));
  sl.Add(JNum('cell_records', nCell));
  sl.Add(JNum('masters', nMasters));

  sl.Add('  ' + q + 'master_names' + q + ': [');
  for k := 0 to masterNames.Count - 1 do
  begin
    if k < masterNames.Count - 1 then comma := ',' else comma := '';
    sl.Add('    ' + q + masterNames[k] + q + comma);
  end;
  sl.Add('  ],');

  sl.Add('  ' + q + 'signature_counts' + q + ': {');
  for k := 0 to sigs.Count - 1 do
  begin
    if k < sigs.Count - 1 then comma := ',' else comma := '';
    sl.Add('    ' + q + sigs[k] + q + ': ' + cnt[k] + comma);
  end;
  sl.Add('  },');

  sl.Add('  ' + q + 'not_checked' + q + ': [');
  sl.Add('    ' + q + 'semantic validity: a parsed record is not necessarily a correct record' + q + ',');
  sl.Add('    ' + q + 'cell contents: geometry, placement and door wiring' + q + ',');
  sl.Add('    ' + q + 'every other plugin in the load order' + q);
  sl.Add('  ]');
  sl.Add('}');

  sl.SaveToFile(reportPath);
  AddMessage('PIPMON: ' + verdict + ' - ' + reason);
  AddMessage('PIPMON: wrote ' + reportPath);

  masterNames.Free;
  cnt.Free;
  sigs.Free;
  sl.Free;
  Result := 0;
end;

end.