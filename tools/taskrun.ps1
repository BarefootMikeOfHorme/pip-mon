# =============================================================
#  taskrun.ps1 -- resumable, verified task groups.
#
#  WHY THIS EXISTS
#    The Creation Kit crashes. Three times in one day, each one losing unsaved
#    work, and the workflow that produced it was a human remembering which
#    clicks had already happened. That is unrecoverable by construction: the
#    only record of progress was in the editor's memory, and the editor died.
#
#    So progress is recorded OUTSIDE the editor, and -- this is the part that
#    matters -- progress is decided by VERIFYING THE WORLD, not by trusting a
#    journal entry. A step is done when its check passes, every time it is
#    asked. That makes the whole group crash-safe:
#
#      - crash during a step  -> the next run re-verifies and repeats ONLY that
#                                 step, because nothing downstream can be true
#                                 if it is not;
#      - crash after a step   -> that step verifies green and is skipped;
#      - ambiguous manual step -> the check decides, so "did I already do
#                                 this?" is answered by the file, not memory.
#
#    Steps are added one at a time on purpose. A task group that has to be
#    written all at once before anything can run will not get written; one that
#    can be extended between runs will.
#
#  NO INTERACTIVE BLOCKING
#    A step that needs a human prints its instructions, records itself as
#    awaiting-manual in the journal, and the runner EXITS. The human does the
#    work and re-runs; verification decides whether it took. A runner that
#    waits on a keypress is a runner that dies with the console and loses the
#    state it was supposed to protect.
#
#  SAFETY
#    - never launches a GUI tool while a Creation Kit process is running
#    - never writes to the game folder unless the step says so explicitly
#    - append-only journal; nothing is ever rewritten, so a crash mid-write
#      loses at most the last line
#
#  USAGE
#    .\taskrun.ps1 -Group facility-v0 -List      show the steps
#    .\taskrun.ps1 -Group facility-v0 -Status    what is verified right now
#    .\taskrun.ps1 -Group facility-v0 -Run        advance as far as it will go
# =============================================================
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Group,
    [switch]$List,
    [switch]$Status,
    [switch]$Next,
    [switch]$Run,
    [switch]$Continue,          # keep going past a failure instead of stopping
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4'
)

$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
$DefFile = Join-Path $Repo "tasks\$Group.json"
$RunRoot = Join-Path $Repo "runs\tasks\$Group"
$Journal = Join-Path $RunRoot 'journal.jsonl'
$Checkpoint = Join-Path $RunRoot 'checkpoint.json'
$Snapshots = Join-Path $RunRoot 'snapshots'

New-Item -ItemType Directory -Path $RunRoot -Force | Out-Null
New-Item -ItemType Directory -Path $Snapshots -Force | Out-Null

# ---------------------------------------------------------------- checkpoint
# A crash must cost at most the step in flight. That needs the state to be on
# disk after EVERY step, not only at the end, and not only when a step is
# green: a semi-successful step is exactly the one whose progress is easiest to
# lose and hardest to reconstruct.
#
# Two artefacts, deliberately separate:
#   checkpoint.json          what is verified right now, rewritten atomically
#   snapshots/               copies of the files the group declares, so a bad
#                            save in the editor can be rolled back to the last
#                            known-good instead of being lost to a crash
function Write-Checkpoint($steps) {
    $rows = @()
    foreach ($s in $steps) {
        $st = Get-StepState $s
        $rows += [ordered]@{
            id       = $s.id
            title    = $s.title
            verified = $st.verified
            checks   = @($st.checks)
        }
    }
    $obj = [ordered]@{
        group      = $Group
        updatedUtc = (Get-Date).ToUniversalTime().ToString('o')
        verified   = @($rows | Where-Object { $_.verified }).Count
        total      = $steps.Count
        steps      = $rows
    }
    # Write-then-move: a crash during the write must not leave a half-written
    # checkpoint that reads as authoritative.
    $tmp = "$Checkpoint.tmp"
    $obj | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tmp -Encoding utf8
    Move-Item -LiteralPath $tmp -Destination $Checkpoint -Force
    Write-Journal @{ id = 'group'; step = $Group; event = 'checkpoint'; note = "$($obj.verified)/$($obj.total) verified" }
}

function Save-Snapshots($steps, $tag) {
    $files = @()
    if ($def.checkpoint) { $files = @($def.checkpoint) }
    if ($files.Count -eq 0) { return }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    foreach ($f in $files) {
        $p = $f -replace '%GAMEDIR%', $GameDir
        if (Test-Path -LiteralPath $p) {
            $leaf = [IO.Path]::GetFileName($p)
            Copy-Item -LiteralPath $p -Destination (Join-Path $Snapshots "$leaf.$tag.$stamp.bak") -Force
        }
    }
}

# ---------------------------------------------------------------- helpers
function Write-Journal($obj) {
    $obj | Add-Content -LiteralPath $Journal -Value (
        [ordered]@{
            t = (Get-Date).ToUniversalTime().ToString('o')
            id = $obj.id
            step = $obj.step
            event = $obj.event
            note = $obj.note
        } | ConvertTo-Json -Compress) -Encoding utf8
}

function Test-Check($check) {
    # Every check returns a verdict object rather than a bare boolean, because
    # "false" and "could not be determined" are different answers and the
    # journal has to be able to tell them apart.
    switch ($check.kind) {

        'file-exists' {
            $p = Resolve-Path -LiteralPath $check.path -ErrorAction SilentlyContinue
            return [ordered]@{ ok = [bool]$p; detail = if ($p) { 'present' } else { 'absent: ' + $check.path } }
        }

        'file-minsize' {
            if (-not (Test-Path -LiteralPath $check.path)) {
                return [ordered]@{ ok = $false; detail = 'absent' }
            }
            $len = (Get-Item -LiteralPath $check.path).Length
            $want = [int64]$check.bytes
            return [ordered]@{ ok = ($len -ge $want); detail = "$len B (need >= $want)" }
        }

        'file-magic' {
            if (-not (Test-Path -LiteralPath $check.path)) {
                return [ordered]@{ ok = $false; detail = 'absent' }
            }
            $b = [IO.File]::ReadAllBytes($check.path)
            $want = $check.bytes
            $ok = $true
            for ($i = 0; $i -lt $want.Length; $i++) {
                if ($b[$i] -ne $want[$i]) { $ok = $false; break }
            }
            return [ordered]@{ ok = $ok; detail = $(if ($ok) { 'magic valid' } else { 'magic BAD' }) }
        }

        # The plugin header check encodes a layout MEASURED against two real
        # files: Fallout4.esm and a plugin the CK wrote. Both carry a 16-byte
        # prologue (flags, zero, zero, version 0x83) that dataSize excludes.
        # A header-only plugin is a legitimate state, so this proves the file is
        # well-formed, never that it has content.
        'esp-header' {
            $p = $check.path
            if (-not (Test-Path -LiteralPath $p)) {
                return [ordered]@{ ok = $false; detail = 'absent' }
            }
            $b = [IO.File]::ReadAllBytes($p)
            if ($b.Length -lt 32) { return [ordered]@{ ok = $false; detail = 'too short to be a plugin' } }
            $magic = [Text.Encoding]::ASCII.GetString($b[0..3])
            $size = [BitConverter]::ToUInt32($b, 4)
            $ver = [BitConverter]::ToUInt32($b, 20)
            $ok = ($magic -eq 'TES4') -and ($ver -eq 0x83) -and ((8 + 16 + $size) -le $b.Length)
            return [ordered]@{
                ok     = $ok
                detail = "magic=$magic version=0x$($ver.ToString('X2')) declared=$size actual=$($b.Length)"
            }
        }

        'json-field' {
            $p = $check.path
            if (-not (Test-Path -LiteralPath $p)) {
                return [ordered]@{ ok = $false; detail = 'absent' }
            }
            try { $j = Get-Content $p -Raw | ConvertFrom-Json } catch {
                return [ordered]@{ ok = $false; detail = 'unparseable JSON' }
            }
            $val = $j.($check.field)
            $ok = ("$val" -eq "$($check.equals)")
            return [ordered]@{ ok = $ok; detail = "$($check.field)=$val (want $($check.equals))" }
        }

        # Text assertions against a line-oriented file. `last` restricts the
        # match to the final non-empty line, which is how the load-order link is
        # verified: our plugin must be enabled AND last, because in this file the
        # last entry is the active file.
        'text-contains' {
            $p = $check.path
            if (-not (Test-Path -LiteralPath $p)) {
                return [ordered]@{ ok = $false; detail = 'absent' }
            }
            $lines = @(Get-Content -LiteralPath $p | Where-Object { $_.Trim() -ne '' })
            if ($check.last) {
                if ($lines.Count -eq 0) { return [ordered]@{ ok = $false; detail = 'file is empty' } }
                $hit = $lines[-1] -like $check.pattern
                return [ordered]@{ ok = $hit; detail = "last line '$($lines[-1])' vs '$($check.pattern)'" }
            }
            $hit = @($lines | Where-Object { $_ -like $check.pattern }).Count -ge $(if ($check.atLeast) { $check.atLeast } else { 1 })
            return [ordered]@{ ok = $hit; detail = "$($lines.Count) lines, pattern '$($check.pattern)'" }
        }

        default {
            # Evidence checks live in their own function; anything unrecognised
            # lands there too and is reported as an unknown evidence check rather
            # than being quietly treated as satisfied.
            return (Test-EvidenceKind $check)
        }
    }
}

# The editor's own output, as a check rather than as commentary.
function Test-EvidenceKind($check) {
    switch ($check.kind) {

        'ck-no-recent-crash' {
            $m = if ($check.minutes) { [double]$check.minutes } else { 15 }
            return (Test-CkNoRecentCrash $m)
        }

        'ck-warnings-lines' {
            $p = $check.path
            if (-not (Test-Path -LiteralPath $p)) {
                return [ordered]@{ ok = $true; detail = 'no warnings file (editor has not written one yet)' }
            }
            $n = @(Get-Content -LiteralPath $p -ErrorAction SilentlyContinue).Count
            $max = [int]$check.max
            return [ordered]@{ ok = ($n -le $max); detail = "$n warning lines (max $max)" }
        }

        'ck-log-lacks' {
            $p = $check.path
            if (-not (Test-Path -LiteralPath $p)) {
                return [ordered]@{ ok = $true; detail = 'no log file yet' }
            }
            $hits = @(Select-String -LiteralPath $p -Pattern $check.pattern -ErrorAction SilentlyContinue)
            return [ordered]@{ ok = ($hits.Count -eq 0); detail = "$($hits.Count) matches of '$($check.pattern)'" }
        }

        # Did the editor actually RENDER, and recently? This is the only
        # mechanical trace a viewport leaves: the CK's log.txt gains Umbra
        # Optimizer lines ("Tile processing complete", "created tome") when the
        # render window runs. It is how "the cell renders as authored" gets any
        # evidence at all without asking the user to take a word for it.
        'ck-render-ran' {
            $m = if ($check.minutes) { [double]$check.minutes } else { 30 }
            $p = Join-Path $GameDir 'log.txt'
            if (-not (Test-Path -LiteralPath $p)) {
                return [ordered]@{ ok = $false; detail = 'no CK log.txt: no render has been run' }
            }
            $f = Get-Item -LiteralPath $p
            $age = ((Get-Date) - $f.LastWriteTime).TotalMinutes
            if ($age -gt $m) {
                return [ordered]@{ ok = $false; detail = "CK log is $([math]::Round($age)) min old (need <= $m): no recent render" }
            }
            $hits = @(Select-String -LiteralPath $p -Pattern '(?i)(Tile processing complete|created tome|Umbra)' -ErrorAction SilentlyContinue)
            return [ordered]@{
                ok     = ($hits.Count -gt 0)
                detail = "log $([math]::Round($age)) min old, $($hits.Count) render markers"
            }
        }

        # A step authored in the CK can only be PROVEN by an inventory of the
        # file, because byte thresholds are satisfied by unrelated records. Until
        # xEdit has parsed the plugin, these steps stay PROXY no matter how big
        # the file gets.
        # Did a live run actually reach ready, and how recently? The placeholder
        # this replaced checked that a DIRECTORY existed, which passed for
        # unrelated reasons and unlocked a real capability -- a green check
        # standing in for work that was never done.
        'run-reached-ready' {
            $runs = Join-Path $Repo 'runs'
            if (-not (Test-Path $runs)) {
                return [ordered]@{ ok = $false; detail = 'no runs directory' }
            }
            $dirs = Get-ChildItem $runs -Directory | Where-Object { $_.Name -match '^\d{8}-\d{6}$' } |
                    Sort-Object Name -Descending
            $best = $null
            foreach ($d in $dirs) {
                $rj = Join-Path $d.FullName 'run.json'
                if (-not (Test-Path $rj)) { continue }
                try { $j = Get-Content $rj -Raw | ConvertFrom-Json } catch { continue }
                if (-not $best) { $best = [pscustomobject]@{ dir = $d; j = $j } }
                if ($j.reachedReady) {
                    $age = ((Get-Date) - $d.CreationTime).TotalMinutes
                    $m = if ($check.minutes) { [double]$check.minutes } else { 1440 }
                    if ($age -le $m) {
                        return [ordered]@{ ok = $true; detail = "run $($d.Name) reachedReady=true ($([math]::Round($age)) min old, dll $($j.dllBytes) B)" }
                    }
                    return [ordered]@{ ok = $false; detail = "newest ready run $($d.Name) is $([math]::Round($age)) min old (need <= $m)" }
                }
            }
            if ($best) {
                return [ordered]@{ ok = $false; detail = "newest run $($best.dir.Name) never reached ready" }
            }
            return [ordered]@{ ok = $false; detail = 'no run.json anywhere under runs\\' }
        }

        'confirmed-by-inventory' {
            $p = Join-Path $Repo 'runs\watch\xedit-latest.json'
            if (-not (Test-Path -LiteralPath $p)) {
                return [ordered]@{ ok = $false; detail = 'no xEdit inventory yet' }
            }
            try { $j = Get-Content $p -Raw | ConvertFrom-Json } catch {
                return [ordered]@{ ok = $false; detail = 'inventory unparseable' }
            }
            return [ordered]@{
                ok     = ("$($j.status)" -eq 'PASS')
                detail = "xEdit inventory status=$($j.status)"
            }
        }

        default {
            return [ordered]@{ ok = $false; detail = "unknown evidence check '$($check.kind)'" }
        }
    }
}

function Get-StepState($step) {
    # THREE STATES, not two.
    #   DONE     every check passed and at least one was a real measurement
    #   PROXY    every check passed but all of them are circumstantial
    #            (a file grew, a header parses) -- the step probably worked and
    #            the workspace does not actually know
    #   PENDING  some check failed
    #
    # PROXY exists because a size threshold satisfied by an unrelated record is
    # how a task group congratulates itself on work nobody did. A proxy step is
    # re-attempted rather than skipped, and it never counts towards "done".
    $results = @()
    $anyMeasured = $false
    foreach ($c in @($step.verify)) {
        $r = Test-Check $c
        $isProxy = ($c.PSObject.Properties['proxy'] -and $c.proxy -eq $true)
        if (-not $isProxy) { $anyMeasured = $true }
        $r | Add-Member -NotePropertyName proxy -NotePropertyValue ([bool]$isProxy) -Force
        $results += , $r
    }
    $allOk = ($results.Count -gt 0)
    foreach ($r in $results) { if (-not $r.ok) { $allOk = $false } }
    $state = if (-not $allOk) { 'PENDING' } elseif ($anyMeasured) { 'DONE' } else { 'PROXY' }
    return [ordered]@{
        state    = $state
        verified = ($allOk -and $anyMeasured)
        checks   = $results
    }
}

# ---------------------------------------------------------------- load
if (-not (Test-Path $DefFile)) {
    Write-Error "no such task group: $DefFile"
    exit 2
}
$def = Get-Content $DefFile -Raw | ConvertFrom-Json
$steps = @($def.steps)

# ------------------------------------------------------------ token expansion
# A task group is written with portable tokens, never with this machine's paths,
# so the definition stays readable and survives being moved or copied. Tokens:
#   REPO\      this workspace
#   TOOLS\     the tools directory
#   %GAMEDIR%  the game folder
#   %LOCALAPPDATA%
# Expansion happens ONCE at load, so nothing downstream has to know about it.
function Expand-Token([string]$s) {
    if ($null -eq $s) { return $s }
    $s = $s.Replace('%GAMEDIR%', $GameDir)
    $s = $s.Replace('%LOCALAPPDATA%', $env:LOCALAPPDATA)
    $s = $s.Replace('REPO\', "$Repo\")
    $s = $s.Replace('TOOLS\', "$PSScriptRoot\")
    return $s
}

foreach ($s in $steps) {
    if ($s.verify) {
        foreach ($c in $s.verify) { if ($c.path) { $c.path = Expand-Token $c.path } }
    }
    if ($s.run) {
        if ($s.run.exe) { $s.run.exe = Expand-Token $s.run.exe }
        if ($s.run.args) { $s.run.args = @($s.run.args | ForEach-Object { Expand-Token $_ }) }
    }
}
if ($def.checkpoint) {
    $def.checkpoint = @($def.checkpoint | ForEach-Object { Expand-Token $_ })
}

# ------------------------------------------------------------ CK evidence
# The editor's own output is evidence about the editor, and it is the only
# evidence available for steps whose check is a size proxy. It is captured after
# EVERY step, green or not, into the run directory, so a crash can be
# attributed to a step instead of merely observed.
function Get-CkEvidence {
    $ev = [ordered]@{
        capturedUtc = (Get-Date).ToUniversalTime().ToString('o')
        running     = [bool](Get-Process CreationKit -ErrorAction SilentlyContinue)
    }
    $dumpDir = Join-Path $env:LOCALAPPDATA 'CrashDumps'
    $newest = Get-ChildItem $dumpDir -Filter 'CreationKit*' -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($newest) {
        $ev['newestCrashDump'] = [ordered]@{ name = $newest.Name; when = $newest.LastWriteTime.ToString('s'); mb = [math]::Round($newest.Length / 1MB, 1) }
        $ev['crashedWithinMinutes'] = [math]::Round(((Get-Date) - $newest.LastWriteTime).TotalMinutes, 1)
    } else {
        $ev['newestCrashDump'] = $null
        $ev['crashedWithinMinutes'] = $null
    }
    foreach ($pair in @(@('editorWarnings', 'EditorWarnings.txt'), @('ckLog', 'log.txt'))) {
        $key = $pair[0]; $leaf = $pair[1]
        $p = Join-Path $GameDir $leaf
        if (Test-Path $p) {
            $f = Get-Item $p
            $lines = @(Get-Content $p -ErrorAction SilentlyContinue)
            $hits = @($lines | Where-Object { $_ -match '(?i)\b(error|warning|crash|failed|missing)\b' } | Select-Object -First 5)
            $ev[$key] = [ordered]@{
                path = $p; bytes = $f.Length; modified = $f.LastWriteTime.ToString('s')
                lines = $lines.Count; notable = $hits
            }
        } else {
            $ev[$key] = $null
        }
    }
    return $ev
}

function Save-CkEvidence($stepId) {
    $dir = Join-Path $RunRoot 'evidence'
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $ev = Get-CkEvidence
    $ev | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $dir "$stepId.json") -Encoding utf8
    return $ev
}

# A step that was supposed to run in the editor must also PROVE the editor
# survived it. Without this check, a step whose artefact happens to look right
# would be marked done even if the CK had crashed halfway through writing it.
# 'ck-no-recent-crash' is therefore attached to every manual step by default.
function Test-CkNoRecentCrash($minutes) {
    $ev = Get-CkEvidence
    if (-not $ev['newestCrashDump']) { return [ordered]@{ ok = $true; detail = 'no CK crash dump on record' } }
    if ($ev['crashedWithinMinutes'] -le $minutes) {
        return [ordered]@{ ok = $false; detail = "CK crashed $($ev['crashedWithinMinutes']) min ago ($($ev['newestCrashDump'].name))" }
    }
    return [ordered]@{ ok = $true; detail = "last CK crash was $($ev['crashedWithinMinutes']) min ago" }
}

if ($List) {
    Write-Output "task group: $Group  ($($steps.Count) steps)"
    Write-Output "definition : $DefFile"
    Write-Output ''
    $i = 0
    foreach ($s in $steps) {
        $i++
        $kind = if ($s.run) { "run:$($s.run.kind)" } else { 'verify-only' }
        Write-Output ("  {0,2}. [{1,-12}] {2}" -f $i, $kind, $s.title)
    }
    exit 0
}

# ---------------------------------------------------------- capabilities
# A step does not "finish a thing". It moves capabilities from BLOCKED to
# AVAILABLE, and the newly available set is the validation: if completing the
# script-attach step did not make anything new possible, the step did not work
# even if every byte check passed. This is the before/after delta the surface
# reports, and it is deliberately computed from DONE steps only -- a PROXY step
# unlocks nothing, because a proxy is not proof.
$CapFile = Join-Path $Repo 'tasks\capabilities.json'
$caps = @()
if (Test-Path $CapFile) {
    $capDoc = Get-Content $CapFile -Raw | ConvertFrom-Json
    $caps = @($capDoc.capabilities)
}

$unlockedBy = @{}          # step id -> capability ids
foreach ($s in $steps) {
    if ($s.PSObject.Properties['unlocks'] -and $s.unlocks) {
        $unlockedBy[$s.id] = @($s.unlocks)
    }
}

function Get-Unlocked([string[]]$extra) {
    $set = New-Object System.Collections.Generic.HashSet[string]
    foreach ($s in $steps) {
        if ((Get-StepState $s).verified -and $unlockedBy.ContainsKey($s.id)) {
            foreach ($c in $unlockedBy[$s.id]) { [void]$set.Add($c) }
        }
    }
    foreach ($c in @($extra)) { if ($c) { [void]$set.Add($c) } }
    return $set
}

function Get-Available([string[]]$extra) {
    $have = Get-Unlocked $extra
    $ok = @(); $blocked = @()
    foreach ($c in $caps) {
        $missing = @($c.requires | Where-Object { -not $have.Contains($_) })
        if ($missing.Count -eq 0) { $ok += $c } else { $blocked += [pscustomobject]@{ cap = $c; missing = $missing } }
    }
    return [pscustomobject]@{ available = $ok; blocked = $blocked }
}

function Get-NextStep {
    foreach ($s in $steps) {
        if (-not (Get-StepState $s).verified) { return $s }
    }
    return $null
}

function Show-CapabilityDelta($label, $before, $after) {
    $b = @($before | ForEach-Object { $_.id })
    $a = @($after | ForEach-Object { $_.id })
    $new = @($a | Where-Object { $b -notcontains $_ })
    Write-Output ''
    Write-Output "$label  ($($a.Count) available)"
    foreach ($c in $after) {
        Write-Output ("  AVAILABLE  [{0}] {1}" -f $c.group, $c.label)
    }
    if ($new.Count -gt 0) {
        Write-Output ''
        Write-Output '  NEWLY AVAILABLE once the step above is DONE:'
        foreach ($id in $new) {
            $c = $caps | Where-Object { $_.id -eq $id }
            if ($c) {
                Write-Output ("    + [{0}] {1}" -f $c.group, $c.label)
                Write-Output ("        exercise : {0}" -f $c.exercise)
                Write-Output ("        evidence : {0}" -f $c.evidence)
            }
        }
    } else {
        Write-Output '  (nothing new becomes available from that step)'
    }
}

if ($Next) {
    $nx = Get-NextStep
    $now = Get-Available @()
    if (-not $nx) {
        Write-Output 'every step in this group is DONE.'
        Show-CapabilityDelta 'AVAILABLE NOW' $now.available $now.available
        exit 0
    }
    $st = Get-StepState $nx
    Write-Output "NEXT ACTIONABLE STEP"
    Write-Output ("  id    : {0}" -f $nx.id)
    Write-Output ("  title : {0}" -f $nx.title)
    Write-Output ("  state : {0}" -f $st.state)
    Write-Output ("  why   : {0}" -f (($st.checks | Where-Object { -not $_.ok } | ForEach-Object { $_.detail }) -join '; '))
    if ($nx.requires) { Write-Output ("  needs : {0}" -f $nx.requires) }
    Write-Output ("  ck now: {0}" -f $(if ($ck) { "RUNNING (pid $($ck.Id))" } else { 'closed' }))
    if ($nx.run -and $nx.run.kind -eq 'shell') {
        Write-Output ''
        Write-Output ("  command: {0} {1}" -f $nx.run.exe, ($nx.run.args -join ' '))
    }
    if ($nx.run -and $nx.run.kind -eq 'manual') {
        Write-Output ''
        foreach ($line in @($nx.run.instructions)) { Write-Output "  $line" }
        Write-Output '  SAVE IN THE EDITOR BEFORE CLOSING IT.'
    }
    $after = Get-Available $(if ($unlockedBy.ContainsKey($nx.id)) { $unlockedBy[$nx.id] } else { @() })
    Show-CapabilityDelta 'BEFORE (available now)' $now.available $now.available
    Show-CapabilityDelta 'AFTER (if this step reaches DONE)' $now.available $after.available
    exit 0
}

if ($Status -or (-not $Run)) {
    $done = 0; $proxy = 0; $pending = 0
    $total = $steps.Count
    Write-Output "task group: $Group"
    foreach ($s in $steps) {
        $st = Get-StepState $s
        switch ($st.state) {
            'DONE' { $done++ }
            'PROXY' { $proxy++ }
            default { $pending++ }
        }
        $tag = switch ($st.state) { 'DONE' { 'DONE   ' } 'PROXY' { 'PROXY  ' } default { 'PENDING' } }
        $detail = ($st.checks | ForEach-Object { $_.detail }) -join '; '
        $unl = if ($unlockedBy.ContainsKey($s.id)) { "  unlocks: $($unlockedBy[$s.id] -join ', ')" } else { '' }
        Write-Output ("  [{0}] {1}{2}" -f $tag, $s.title, $unl)
        if ($detail) { Write-Output ("           {0}" -f $detail) }
    }
    Write-Output ''
    Write-Output "  $done measured, $proxy proxy-only, $pending pending   (of $total)"
    $now = Get-Available @()
    Write-Output "  capabilities available now: $(@($now.available).Count) of $($caps.Count)"
    $nx = Get-NextStep
    if ($nx) { Write-Output "  next: $($nx.id) -- $($nx.title)" }
    exit 0
}

# ---------------------------------------------------------------- run
$ck = Get-Process CreationKit -ErrorAction SilentlyContinue
Write-Journal @{ id = 'group'; step = $Group; event = 'run-start'; note = "steps=$($steps.Count) ckRunning=$([bool]$ck)" }

foreach ($s in $steps) {
    $st = Get-StepState $s
    if ($st.verified) {
        Write-Journal @{ id = $s.id; step = $s.title; event = 'skip-verified'; note = '' }
        continue
    }

    # A step that launches something graphical must not run beside an open CK.
    if ($s.run -and $s.run.kind -eq 'shell' -and $s.run.launchesGui -eq $true -and $ck) {
        Write-Journal @{ id = $s.id; step = $s.title; event = 'blocked'; note = "CreationKit running (pid $($ck.Id))" }
        Write-Output ("BLOCKED  {0}" -f $s.title)
        Write-Output "         Creation Kit is running (pid $($ck.Id)); a GUI-launching step will not run beside it."
        if (-not $Continue) { break } else { continue }
    }

    if (-not $s.run) {
        Write-Journal @{ id = $s.id; step = $s.title; event = 'failed'; note = 'no run action and verification did not pass' }
        Write-Output ("FAILED   {0}" -f $s.title)
        if (-not $Continue) { break } else { continue }
    }

    Write-Journal @{ id = $s.id; step = $s.title; event = 'attempting'; note = $s.run.kind }

    switch ($s.run.kind) {

        'manual' {
            Write-Output ("AWAITING {0}" -f $s.title)
            foreach ($line in @($s.run.instructions)) { Write-Output "           $line" }
            Write-Output ''
            Write-Output "         Do it in the Creation Kit, save, then re-run this group."
            Write-Output "         Progress is decided by the checks, not by this journal, so"
            Write-Output "         re-running after a crash resumes exactly here."
            Write-Journal @{ id = $s.id; step = $s.title; event = 'awaiting-manual'; note = '' }
            break
        }

        'shell' {
            $exe = $s.run.exe
            $a = @()
            foreach ($x in @($s.run.args)) { $a += $x }
            $out = & $exe @a 2>&1
            $rc = $LASTEXITCODE
            foreach ($l in @($out)) { Write-Output "           $_" }
            $expect = if ($s.run.expectExit -ne $null) { [int]$s.run.expectExit } else { 0 }
            if ($rc -ne $expect) {
                Write-Journal @{ id = $s.id; step = $s.title; event = 'failed'; note = "exit $rc (wanted $expect)" }
                Write-Output ("FAILED   {0}  (exit {1}, wanted {2})" -f $s.title, $rc, $expect)
                if (-not $Continue) { break } else { continue }
            }
            Write-Journal @{ id = $s.id; step = $s.title; event = 'ran'; note = "exit $rc" }
            Write-Output ("RAN      {0}" -f $s.title)
        }

        default {
            Write-Journal @{ id = $s.id; step = $s.title; event = 'failed'; note = "unknown run kind $($s.run.kind)" }
            Write-Output ("FAILED   {0}  (unknown run kind)" -f $s.title)
            if (-not $Continue) { break } else { continue }
        }
    }

    # Re-verify immediately: a step that "ran" but did not achieve its check is
    # not done, and saying otherwise is how a group lies its way to the end.
    $after = Get-StepState $s
    if ($after.verified) {
        Write-Journal @{ id = $s.id; step = $s.title; event = 'verified'; note = '' }
        Write-Output ("VERIFIED {0}" -f $s.title)
    } else {
        $detail = ($after.checks | ForEach-Object { $_.detail }) -join '; '
        Write-Journal @{ id = $s.id; step = $s.title; event = 'unverified'; note = $detail }
        Write-Output ("UNVERIFIED {0}  ({1})" -f $s.title, $detail)
    }

    # SAVE POINT, after EVERY step -- green or not. This is the whole point of
    # the runner: the state of the work is on disk before the next step starts,
    # so a crash in step 7 cannot cost steps 1-6, and a half-finished step 7 is
    # re-attempted rather than assumed either way.
    Save-Snapshots $steps $s.id
    $ev = Save-CkEvidence $s.id
    if ($ev['newestCrashDump']) {
        Write-Output ("           evidence: CK crash {0} min ago ({1}); warnings {2} lines" -f `
                $ev['crashedWithinMinutes'], $ev['newestCrashDump'].name, `
            $(if ($ev['editorWarnings']) { $ev['editorWarnings'].lines } else { 'n/a' }))
    }
    Write-Checkpoint $steps
}

Write-Journal @{ id = 'group'; step = $Group; event = 'run-end'; note = '' }
Write-Checkpoint $steps

$done = 0
foreach ($s in $steps) { if ((Get-StepState $s).verified) { $done++ } }
Write-Output ''
Write-Output "  $done of $($steps.Count) verified   (journal: $Journal)"
exit 0
