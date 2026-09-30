{
  PIP-MON: read the vanilla fixture candidates out of the loaded master.

  WHY THIS EXISTS
    The headless build needs three placed objects -- a workbench, a power armour
    station, and a terminal -- and their FormIDs. A FormID written from memory
    is a guess, and this project refuses rather than guesses: a wrong ID produces
    a placed reference that resolves to nothing and fails SILENTLY, which is
    indistinguishable from a working fixture. So the IDs are read out of the real
    master file rather than recalled.

  SCOPE
    STAT / FURN / CONT / XM / LIGH records whose EditorID mentions a fixture word.
    STAT is the one that matters: in vanilla Fallout 4 a workbench, a power
    armour station and a terminal are all placed statics with furniture behaviour,
    so one record type covers all three fixtures.

  OUTPUT
    signature;FormID;EditorID  ->  fixtures.txt beside xEdit. Inside the project
    copy of the output (G15) rather than a temp dir that gets swept.
}
unit UserScript;

var
  sl: TStringList;
  hits: integer;

function Initialize: integer;
begin
  sl := TStringList.Create;
  hits := 0;
  Result := 0;
end;

function Process(e: IInterface): integer;
var
  sig, edid, up: string;
begin
  Result := 0;
  sig := Signature(e);

  if (sig <> 'STAT') and (sig <> 'FURN') and (sig <> 'CONT') and
     (sig <> 'XM') and (sig <> 'LIGH') then
    Exit;

  edid := GetElementEditValues(e, 'EDID');
  if edid = '' then
    Exit;

  up := UpperCase(edid);

  if (Pos('WORKBENCH', up) > 0) or (Pos('BENCH', up) > 0) or
     (Pos('POWERARMORSTATION', up) > 0) or (Pos('PASTATION', up) > 0) or
     (Pos('ARMORSTATION', up) > 0) or (Pos('STATION', up) > 0) or
     (Pos('TERMINAL', up) > 0) or (Pos('MARKER', up) > 0) then
  begin
    sl.Add(sig + ';' + IntToHex(FixedFormID(e), 8) + ';' + edid);
    Inc(hits);
  end;
end;

function Finalize: integer;
var
  fname: string;
begin
  fname := ProgramPath + 'fixtures.txt';
  sl.SaveToFile(fname);
  AddMessage('PIPMON: wrote ' + IntToStr(hits) + ' fixture candidates to ' + fname);
  sl.Free;
  Result := 0;
end;

end.
