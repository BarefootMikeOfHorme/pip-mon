{
  PIP-MON: inventory the CELL records of the loaded plugin.

  WHY THIS EXISTS
    Launching straight into a test cell needs the cell's EDITOR ID -- `coc`
    takes a name, not a FormID -- and nobody has written that list down. This
    is also the check on whether the plugin is loadable at all.

  WHY xEdit AND NOT A HAND-ROLLED PARSER
    An earlier attempt at tools/esp_cells.py got the TES4 header layout wrong
    twice and reported a perfectly valid 613 KB plugin as MALFORMED. That is
    M11 exactly: a second implementation of a well-specified structure, written
    from memory, disagreeing with the real one -- and the disagreement was
    presented as a confident verdict rather than as uncertainty. xEdit already
    parses this format correctly and has done for fifteen years. Reuse it.

  OUTPUT
    One line per cell: FormID;EditorID;Name  -> cells.txt beside xEdit.
    Written inside the project on purpose (G15): scratch output belongs in the
    project, never in a temp folder that may later be swept.
}
unit UserScript;

var
  sl: TStringList;
  count: integer;

function Initialize: integer;
begin
  sl := TStringList.Create;
  count := 0;
  Result := 0;
end;

function Process(e: IInterface): integer;
var
  edid, full, fid: string;
begin
  Result := 0;
  if Signature(e) <> 'CELL' then
    Exit;

  edid := GetElementEditValues(e, 'EDID');
  full := GetElementEditValues(e, 'FULL');
  fid  := IntToHex(FixedFormID(e), 8);

  // Name and EditorID both go in the file. `coc` wants the EditorID, but the
  // FULL name is what a human recognises, and shipping only one of them is how
  // you end up grepping a plugin for a string that is not in it.
  sl.Add(fid + ';' + edid + ';' + full);
  Inc(count);
end;

function Finalize: integer;
var
  fname: string;
begin
  fname := ProgramPath + 'cells.txt';
  sl.SaveToFile(fname);
  AddMessage('PIPMON: wrote ' + IntToStr(count) + ' CELL records to ' + fname);
  sl.Free;
  Result := 0;
end;

end.
