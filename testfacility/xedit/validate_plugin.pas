{
  PIP-MON: validate a plugin and emit a machine-readable JSON report.

  WHY THIS EXISTS
    The Creation Kit is the only tool that can author content here, and it is
    also the least reliable: three crash dumps in one session, batch operations
    that abort mid-dataset, and unsaved work lost each time. Everything the CK
    would be used for that does NOT need the CK should run headlessly instead,
    where a failure costs nothing and leaves evidence.

    This answers three questions about a plugin file:
      1. does xEdit parse it at all;
      2. what masters does it declare;
      3. what records does it contain, with FormID and EditorID.

    It deliberately asserts NOTHING about game semantics. "Is this cell
    coherent" is a question about the game's rules, not about a file walk, and
    a tool that guesses at that is worse than one that declines.

  A NOTE ON API CAUTION
    Verified by execution, not by documentation. This unit ran to Finalize on
    2026-09-30 and aborted at the last statement with:

        [EJvInterpreterError] Error in unit 'UserScript' on line 82 :
        Undeclared Identifier 'GetPluginName'

    So in FO4Edit 4.1.5f x64 (7C57FA01) the following ARE real and were proven
    by a full load reaching Finalize: Signature, GetElementEditValues,
    FixedFormID, IntToHex, TStringList. The following are NOT available and
    must never be used again: GetPluginName (undeclared), and by policy
    ProgramPath, since nothing after the failure point has been executed yet
    and an unproven path API would cost another three-minute round trip.

    Consequence: this script now takes the output path and the plugin name as
    LITERAL strings, substituted by tools\validate_plugin.ps1 at launch. That
    removes the dependency entirely instead of guessing at a replacement API.

    A script that fails to compile produces NO output at all, which the caller
    has to distinguish from "the plugin was fine and there was nothing to say".
    That is why the caller now captures xEdit's stdout/stderr and reads this
    file's sibling FO4Script_log.txt before ever believing a result.
}
unit UserScript;

var
  sl: TStringList;
  recordCount: Integer;
  groupCount: Integer;
  masterCount: Integer;
  first: Boolean;

function Initialize: Integer;
begin
  sl := TStringList.Create;
  recordCount := 0;
  groupCount := 0;
  masterCount := 0;
  first := True;
  Result := 0;
end;

function Process(e: IInterface): Integer;
var
  sig, edid, fid, q: string;
begin
  Result := 0;
  sig := Signature(e);

  if sig = 'MAST' then
  begin
    Inc(masterCount);
    sl.Add('M|' + GetElementEditValues(e, 'MAST'));
  end
  else if sig = 'GRUP' then
  begin
    Inc(groupCount);
  end
  else
  begin
    Inc(recordCount);
    fid := IntToHex(FixedFormID(e), 8);
    edid := GetElementEditValues(e, 'EDID');
    q := '"';
    sl.Add('R|' + q + sig + q + '|' + q + fid + q + '|' + q + edid + q);
  end;
end;

function Finalize: Integer;
var
  outName: string;
  i: Integer;
  line: string;
  f: TextFile;
begin
  outName := '%%OUTPATH%%';

  AssignFile(f, outName);
  Rewrite(f);

  WriteLn(f, '{');
  WriteLn(f, '  "schema": "pipmon.plugin.validation/1",');
  WriteLn(f, '  "status": "PASS",');
  WriteLn(f, '  "plugin": "%%PLUGIN%%",');
  WriteLn(f, '  "note": "Parsed by xEdit. Semantic validity is NOT asserted: PASS means the file');
  WriteLn(f, '          parsed and was inventoried, not that the game will accept its content.",');
  WriteLn(f, '  "groups": ' + IntToStr(groupCount) + ',');
  WriteLn(f, '  "records": ' + IntToStr(recordCount) + ',');
  WriteLn(f, '  "masters": [');
  for i := 0 to sl.Count - 1 do
  begin
    line := sl[i];
    if Copy(line, 1, 2) <> 'M|' then
      continue;
    if not first then
      WriteLn(f, ',');
    WriteLn(f, '    "' + Copy(line, 3, Length(line) - 2) + '"');
    first := False;
  end;
  first := True;
  WriteLn(f, '  ],');
  WriteLn(f, '  "records_detail": [');
  for i := 0 to sl.Count - 1 do
  begin
    line := sl[i];
    if Copy(line, 1, 2) <> 'R|' then
      continue;
    if not first then
      WriteLn(f, ',');
    WriteLn(f, '    {' + Copy(line, 3, Length(line) - 2) + '}');
    first := False;
  end;
  WriteLn(f, '  ]');
  WriteLn(f, '}');

  CloseFile(f);

  AddMessage('PIPMON: wrote ' + outName + ' (' + IntToStr(recordCount) +
             ' records, ' + IntToStr(masterCount) + ' masters)');
  sl.Free;
  Result := 0;
end;

end.
