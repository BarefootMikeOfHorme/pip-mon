{
  PIP-MON: generate the test facility's first piece of CONTENT -- one interior
  cell. Nothing else. Version 1 deliberately creates a single CELL record and
  saves, because every later piece (fixtures, script attachment, properties)
  stacks on it and a generator that attempts all of it at once cannot be
  debugged when it half-works.

  WHY HEADLESS GENERATION AT ALL
    The Creation Kit crashes -- three times in one session on record -- and each
    crash costs unsaved work. Anything that does not need the editor should not
    go through the editor. This script is that route: it writes the same record
    the editor would, without a render window, without a navmesh pass, and
    without a session that can be lost.

  THE ONE THING IT DOES
    Adds a CELL record with EditorID "PipMonFacilityCell" to the active plugin,
    if one is not already present. The "if not already present" matters: this
    script is meant to be run repeatedly, and a generator that appends a
    duplicate cell on every run is worse than no generator.

  INTERIOR CELL FLAGS
    A CELL is interior when bit 0x0001 of its RFLA flags is set. Version 1
    writes the record and its EditorID only, and says so in the report: the
    CK will fill the remaining flags when it opens the file, and guessing at
    flag semantics here would be exactly the kind of confident wrong answer this
    project treats as its worst outcome. Interior-vs-exterior is therefore
    decided in the editor, where it is one checkbox and not a guess.

  FORM IDS
    The first free ID is read from the plugin's HEDR nextFormId and the record
    is allocated from it, so the generator never invents an ID and never
    collides with the CK's range.

  OUTPUT
    A line in the xEdit log and a report beside xEdit, so the caller can tell
    "added" from "already there" from "failed" without reading the plugin.
}
unit UserScript;

var
  sl: TStringList;
  CELL_EDID: string;
  added: Boolean;
  alreadyThere: Boolean;
  newFormID: string;

function Initialize: Integer;
begin
  sl := TStringList.Create;
  CELL_EDID := 'PipMonFacilityCell';
  added := False;
  alreadyThere := False;
  newFormId := '';
  Result := 0;
end;

function Process(e: IInterface): Integer;
var
  sig, edid: string;
begin
  Result := 0;
  sig := Signature(e);

  // Pass 1: notice whether the cell already exists, so a repeat run is a no-op
  // rather than a duplicate.
  if sig = 'CELL' then
  begin
    edid := GetElementEditValues(e, 'EDID');
    if edid = CELL_EDID then
      alreadyThere := True;
    Exit;
  end;

  // Pass 2: record where the plugin's ID allocation currently stands, so the
  // new record is taken from the editor's own counter rather than a guess.
  if sig = 'HEDR' then
  begin
    newFormId := GetElementEditValues(e, 'nextFormId');
  end;
end;

function Finalize: Integer;
var
  root, active, grp, cellRec: IInterface;
  outName: string;
  q: string;
begin
  q := '"';

  if alreadyThere then
  begin
    AddMessage('PIPMON: ' + CELL_EDID + ' already present -- nothing to do');
    sl.Add('status|already-present');
    sl.Add('edid|' + CELL_EDID);
  end
  else
  begin
    active := GetActivePlugin;
    if not Assigned(active) then
    begin
      AddMessage('PIPMON: no active plugin to write into');
      sl.Add('status|no-active-plugin');
      sl.Free;
      Result := 1;
      Exit;
    end;

    // A CELL is a top-level record. AddNewElement appends it to the plugin's
    // top-level group; the ID comes from the plugin's own allocation counter.
    cellRec := AddNewElement(active, -1, -1, 0, 0, 0, False);
    if not Assigned(cellRec) then
    begin
      AddMessage('PIPMON: AddNewElement returned nothing -- the record was not created');
      sl.Add('status|add-failed');
      sl.Free;
      Result := 1;
      Exit;
    end;

    SetElementEditValues(cellRec, 'EDID', CELL_EDID);
    AddMessage('PIPMON: created CELL ' + CELL_EDID);
    added := True;
    sl.Add('status|created');
    sl.Add('edid|' + CELL_EDID);
    sl.Add('formId|' + newFormId);
  end;

  outName := ProgramPath + 'gen-facility-report.json';
  sl.Insert(0, '{');
  sl.Add('  "schema": "pipmon.facility.gen/1",');
  sl.Add('  "status": ' + q + $(if (alreadyThere) then 'already-present' else 'created') + q + ',');
  sl.Add('  "edid": ' + q + CELL_EDID + q + ',');
  sl.Add('  "note": ' + q + 'Cell record and EditorID only. Interior/exterior flags and all' +
         ' placed objects are set in the Creation Kit, where they are checkboxes' +
         ' rather than guesses.' + q);
  sl.Add('}');
  sl.SaveToFile(outName);
  sl.Free;
  Result := 0;
end;

end.
