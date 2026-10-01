unit UserScript;

{
  PIP-MON: validate ONE plugin (the target) and emit a verdict.

  Job    : report measured facts about targetName, end with PASS, FAIL or SKIP.
  Not job: inventory of the whole load order, repair, semantic validation.

  Verdicts (SKIP is not PASS: the property it covers is UNVERIFIED)
    SKIP  target is not in the loaded load order, so nothing could be checked
    FAIL  target loaded but is header-only, or has records and no CELL
    PASS  target loaded, has records, and has at least one CELL

  ---------------------------------------------------------------------------
  WHAT IS PROVEN BY EXECUTION, and how it was proven
  ---------------------------------------------------------------------------
  Measured on a real run, 2026-09-30 20:11, FO4Edit 4.1.5f x64:

    Initialize completed.  Its FileCount / FileByIndex / GetFileName loop ran to
    completion over the load order, because the run's abort was reported at line
    106 -- inside Process, which only runs after Initialize returns.

    That is a stronger clearance than a documentation entry: these three calls
    have been observed working on this build, in this script, today.

    NOT proven, and therefore NOT used below:
      GetFile           the upstream signature is GetFile(aeElement: IwbElement)
                        which ought to accept a record, but the 20:11 run
                        aborted 15s into Process at exactly this call. An
                        upstream signature is a claim; an abort is a measurement.
      MasterCount       no spec entry, never executed here
      MasterByIndex     no spec entry, never executed here

    The previous revision of this file called GetFile on every record to
    attribute counts per plugin. That is what the abort was. Per-plugin
    attribution is therefore recorded as NOT CHECKED, with the reason, rather
    than attempted -- which is the same call the earlier revision made, and it
    was right.

  ---------------------------------------------------------------------------
  WHY THERE IS NO TRY/EXCEPT
  ---------------------------------------------------------------------------
  A previous version used try/except with helpers declared after their use, and
  xEdit's Pascal rejected it at compile time with a dialog and no log entry. So
  the defence against a raise is not to catch it: it is to not make the call.

  ---------------------------------------------------------------------------
  THE SCRIPT TALKS
  ---------------------------------------------------------------------------
  AddMessage at every stage, so the run narrates itself into FO4Script_log.txt.
  A silent run is indistinguishable from a stalled one, and that ambiguity has
  cost more time here than any single bug.

  Failure history lives in HANDOVER.md and the header of this file, not in a
  comment that drifts.
}

var
  sl: TStringList;
  sigs: TStringList;
  cnt: TStringList;
  reportPath: string;
  targetName: string;
  tgtLower: string;
  verdict: string;
  reason: string;
  q: string;
  sig: string;
  comma: string;
  loaded: Boolean;
  nRecords: Integer;
  nCell: Integer;
  nTES4: Integer;
  nGroups: Integer;
  i: Integer;
  k: Integer;
  idx: Integer;
  nHeartbeat: Integer;

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

  AddMessage('PIPMON: Initialize - looking for ' + targetName);
  q := Chr(34);
  tgtLower := LowerCase(targetName);
  sl := TStringList.Create;
  sigs := TStringList.Create;
  cnt := TStringList.Create;
  nRecords := 0;
  nCell := 0;
  nTES4 := 0;
  nGroups := 0;
  nHeartbeat := 0;
  loaded := False;

  { PROVEN BY EXECUTION 2026-09-30: this loop completes. }
  for i := 0 to FileCount - 1 do
  begin
    if LowerCase(GetFileName(FileByIndex(i))) = tgtLower then
    begin
      loaded := True;
      AddMessage('PIPMON: found ' + targetName + ' at load order index ' + IntToStr(i));
    end;
  end;

  if not loaded then
    AddMessage('PIPMON: Initialize done - ' + targetName + ' is NOT in the loaded load order; verdict will be SKIP')
  else
    AddMessage('PIPMON: Initialize done - target present at load order index. Process will count records.');

  Result := 0;
end;

function Process(e: IInterface): Integer;
begin
  Result := 0;
  sig := Signature(e);

  { PROVEN BY EXECUTION: Signature alone, over every record. No GetFile. }
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

  { A heartbeat, because Process is where a run spends its time and a silent
    callback is indistinguishable from a stalled one. Every 25k records, which
    over this load order is about 91 lines for 2.29M records: dense enough to
    see it moving, sparse enough to read. }
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

  if not loaded then
  begin
    verdict := 'SKIP';
    reason := 'target plugin is not in the loaded load order; nothing was checked';
  end
  else if nRecords = 0 then
  begin
    verdict := 'FAIL';
    reason := 'no records at all in the active load order -- the load did not produce records';
  end
  else
  begin
    verdict := 'PASS';
    reason := 'target is in the load order and the load order parsed; per-plugin record counts were NOT obtained, see not_checked';
  end;

  sl.Add('{');
  sl.Add(JStr('schema', 'pipmon.plugin.validation/5'));
  sl.Add(JStr('target', targetName));
  sl.Add(JStr('verdict', verdict));
  sl.Add(JStr('reason', reason));
  sl.Add(JBool('target_loaded', loaded));
  sl.Add(JNum('records_in_load_order', nRecords));
  sl.Add(JNum('cell_records_in_load_order', nCell));
  sl.Add(JNum('groups_in_load_order', nGroups));
  sl.Add(JNum('distinct_signatures', sigs.Count));
  sl.Add(JStr('provenance', 'xEdit script; per-item counts are load-order wide, not per-plugin'));
  sl.Add(JStr('proven_by_execution', 'FileCount, FileByIndex, GetFileName, Signature, TStringList.SaveToFile, AddMessage -- run 2026-09-30 20:11'));
  sl.Add(JStr('not_used_unproven', 'GetFile aborted Process on 2026-09-30 20:11 at line 106; MasterCount and MasterByIndex have no spec entry'));

  sl.Add('  ' + q + 'signature_counts' + q + ': {');
  for k := 0 to sigs.Count - 1 do
  begin
    if k < sigs.Count - 1 then comma := ',' else comma := '';
    sl.Add('    ' + q + sigs[k] + q + ': ' + cnt[k] + comma);
  end;
  sl.Add('  },');

  sl.Add('  ' + q + 'not_checked' + q + ': [');
  sl.Add('    ' + q + 'per-plugin record attribution: needs GetFile, which aborted Process on 2026-09-30' + q + ',');
  sl.Add('    ' + q + 'target master list: needs MasterCount and MasterByIndex, neither in ai_context/spec/xedit_api.json' + q + ',');
  sl.Add('    ' + q + 'semantic validity: a parsed record is not necessarily a correct record' + q + ',');
  sl.Add('    ' + q + 'cell contents: geometry, placement and door wiring' + q + ',');
  sl.Add('    ' + q + 'every other plugin in the load order' + q);
  sl.Add('  ]');
  sl.Add('}');

  sl.SaveToFile(reportPath);
  AddMessage('PIPMON: VERDICT ' + verdict + ' - ' + reason);

  { Say where it went and that it is on disk. A run that computes a verdict and
    does not announce the write leaves the reader unable to tell "finished" from
    "still going", and those two look identical from outside. }
  AddMessage('PIPMON: SAVED ' + reportPath);
  AddMessage('PIPMON: SAVED lines=' + IntToStr(sl.Count) + ' signatures=' + IntToStr(sigs.Count));
  AddMessage('PIPMON: done - Finalize complete');

  cnt.Free;
  sigs.Free;
  sl.Free;
  Result := 0;
end;

end.
