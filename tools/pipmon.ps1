# =============================================================
#  pipmon.ps1 -- THE SURFACE.
#
#  One entry point for the whole workspace, for AI agents and for humans,
#  covering both Creation Engine hosts: the engine (game runtime) and the
#  editor (FO4 Creation Kit, plus xEdit). Not two tools that disagree about the
#  truth -- one surface that reports both, because the questions are the same
#  questions.
#
#  NAME COLLISIONS, spelled out because they have been conflated before
#    CK    = Fallout 4 Creation Kit (CreationKit.exe). The editor used here.
#    GECK  = Garden of Eden Creation Kit, a Fallout 3 / New Vegas editor. NOT
#            the FO4 CK, and NOT currently in use. It is a separate peer tool on
#            the replacement list, to be modernized through our own mod later.
#    xEdit = FO4Edit, the community record editor and headless script host.
#
#  WHY A SURFACE AND NOT A SCRIPT PER TASK
#    Four separate tools already existed by the end of the first working day,
#    each with its own output format and its own idea of what a failure looks
#    like. That is how a session ended up reporting "done" for three things at
#    once while one of them was quietly skipping. A surface fixes that by
#    having exactly one output contract and exactly one exit-code vocabulary.
#
#  THE CONTRACT
#    Every command emits one JSON envelope on stdout:
#
#      { "schema": "pipmon.surface/1",
#        "command": "<name>",
#        "status":  "GREEN" | "RED" | "SKIP" | "BROKEN" | "OK",
#        "ok":      true|false,
#        "reason":  null | "why, in one sentence",
#        "data":    { ... command specific ... },
#        "provenance": { "script": "...", "generatedUtc": "..." } }
#
#    Exit codes are the same in every command, so a caller can branch without
#    parsing text:
#        0  GREEN / OK   the thing ran and is good
#        1  RED          the thing ran and is wrong
#        2  BROKEN       a precondition is missing (toolchain, file, install)
#        3  SKIP         the check could NOT run; unverified, NOT fine
#        4  usage        the command line was wrong
#
#    SKIP IS NOT PASS. A skip is reported as a skip everywhere, including in
#    any aggregate, because "we did not look" and "we looked and it is fine"
#    are different facts and collapsing them is how a workspace starts lying.
#
#  DESIGN RULES HONOURED HERE
#    - a fact with no provenance may not exist: every envelope names its source
#    - refuse rather than guess: nothing here infers a value it did not read
#    - never touch a running Creation Kit: the editor commands are read-only
#      inspections, and the surface says so rather than implying it drives it
# =============================================================
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = 'status',

    # Sub-command for grouped commands: link status|apply|restore, editor preflight.
    # Declared as the SECOND positional parameter, not just a named one, so that
    # `pipmon.ps1 editor preflight` works. Without Position it was rejected by
    # parameter binding before the switch ever ran, and the error text went to
    # stderr instead of the JSON envelope.
    [Parameter(Position = 1)]
    [string]$Arg,

    [string]$Plugin,
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Fallout 4',
    [switch]$NoDeploy,
    [switch]$Watch,

    # Forwarded to linksync.ps1, which declares [string[]]$Enable and
    # [string[]]$Disable at its lines 45-46 and implements both at 147-155,
    # snapshotting before apply at its line 132.
    #
    # These are declared HERE because caps has advertised them all along. A
    # discovery document listing arguments the entry point rejects is worse than
    # one that lists nothing: it teaches a caller to trust a surface that lies.
    # Pass them comma-joined or repeated; both bind to [string[]].
    [string[]]$Enable = @(),
    [string[]]$Disable = @(),

    [string]$Query,
    [string]$Kind,
    [int]$Limit = 5,
    [int]$MaxLines = 0,
    [int]$Page = 1,
    [string]$Format = 'dense',

    # compat filters. $Status is the closed six-value vocabulary declared in
    # ai_context/spec/schema.json; $RequiresHost is none | game | ck | game+ck.
    # Both are validated against the data rather than trusted, so a typo narrows
    # to an empty result and says so, instead of silently returning everything.
    [string]$Status,
    [string]$RequiresHost
)

$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent $PSScriptRoot
$WatchDir = Join-Path $Repo 'runs\watch'

$EXIT = @{ GREEN = 0; OK = 0; RED = 1; BROKEN = 2; SKIP = 3 }

function New-Envelope($status, $reason, $data) {
    [ordered]@{
        schema      = 'pipmon.surface/1'
        command     = $Command
        status      = $status
        ok          = ($status -in 'GREEN', 'OK')
        reason      = $reason
        data        = $data
        provenance  = [ordered]@{
            script       = 'tools/pipmon.ps1'
            generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
            workspace    = $Repo
        }
    }
}

$script:surfaceExit = 0

function Emit($status, $reason, $data) {
    # An unrecognised status must never become a pass. The mechanism is not the
    # obvious one: $EXIT[$status] on a missing key does NOT return $null, it
    # raises a non-terminating NullArrayIndex error, so the assignment below is
    # SKIPPED and $surfaceExit silently KEEPS the value it already held -- which
    # is 0, set at line 101. That is how a failed deploy verification exited 0
    # with "ok": false in the envelope, and it is also why nothing looked wrong:
    # stdout carried a clean envelope and the error went to stderr.
    #
    # BROKEN is the honest landing, not RED. The precondition that is missing is
    # "this status is in the exit table", and BROKEN already means a missing
    # precondition at line 39. RED would claim the thing ran and is wrong, which
    # is a claim about the SUBJECT; this is a claim about the SURFACE.
    #
    # This is a net, not a fix. The named residuals are F2.12 (validate's
    # PASS/FAIL/SKIP are not surface statuses and must be mapped, not caught) and
    # F2.1b (what ATTENTION is MEANS is still undecided). A net that turns a
    # silent wrong answer into a loud wrong answer is worth having; it is not the
    # same as a right answer.
    # The null test is NOT redundant. Hashtable.ContainsKey($null) throws
    # ArgumentNullException rather than returning false, so without it a null
    # status skips this guard entirely and reaches $EXIT[$null] below, which is
    # the original silent pass. A null status is reachable: verify's exit map
    # covers 0-3 only, so any child exit above 3 yields null (F2.4).
    $unknown = if ($null -eq $status) { '<null>' } else { $status }
    if ($null -eq $status -or -not $EXIT.ContainsKey($status)) {
        $reason = "surface emitted status '$unknown', which is not in the exit table, so the verdict is untrustworthy and is reported as BROKEN. Declared: $($EXIT.Keys -join ', '). Original reason: $reason"
        $status = 'BROKEN'
    }
    # Printed, not returned: a `return` here writes the exit code into the
    # output stream and corrupts the JSON envelope for every caller.
    Write-Output ((New-Envelope $status $reason $data) | ConvertTo-Json -Depth 6)
    $script:surfaceExit = $EXIT[$status]
}

# The inputs a papyrus report describes, read out of vprobe\papyrus\build_papyrus.bat
# -- it stages *.psc and *.flg from these three roots (its lines 104-138). Mirrored
# by pattern rather than listed file by file, so a source added to any of the three
# roots is covered without this surface having to be edited to notice.
function Get-PapyrusInputs {
    $roots = @(
        (Join-Path $Repo 'vprobe\papyrus'),
        (Join-Path $Repo 'overseer_event_bridge\Scripts\Source'),
        (Join-Path $Repo 'pip_mon_testlab\Scripts\Source')
    )
    $out = @()
    foreach ($r in $roots) {
        if (Test-Path -LiteralPath $r) {
            $out += @(Get-ChildItem -LiteralPath $r -File -Recurse -ErrorAction SilentlyContinue |
                      Where-Object { $_.Extension -in '.psc', '.flg' } |
                      ForEach-Object { $_.FullName })
        }
    }
    return $out
}

# The pascal program xEdit executes. validate_plugin.ps1 generates a copy from it
# (runs\watch\validate_plugin.gen.pas) and runs that, so the template is an input
# to the verdict the report records. The plugin under test is NOT named here:
# the report carries its own `plugin` field and Read-Report reads that from the
# report, so a validation aimed at a different .esp is compared against the right
# file instead of a hardcoded default.
function Get-XeditInputs {
    return @((Join-Path $Repo 'testfacility\xedit\validate_plugin.pas'))
}

function Read-Report($name, $extraInputs) {
    $p = Join-Path $WatchDir $name
    if (-not (Test-Path $p)) { return $null }
    try { $rep = Get-Content $p -Raw | ConvertFrom-Json } catch { return $null }
    if ($null -eq $rep) { return $null }
    # A report that parsed to something other than an object (an array, a bare
    # string) has no fields to date against and cannot carry a freshness block.
    # It is returned as it is rather than decorated with a guess.
    if ($rep -isnot [System.Management.Automation.PSCustomObject]) { return $rep }

    # FRESHNESS -- F2.3. A report is a statement about the tree as it was. This
    # function read one and returned it with no check at all, and four call sites
    # (status x2, build, validate) presented the result as current truth. On this
    # workspace, right now, `runs\watch\papyrus-latest.json` reads GREEN from
    # 2026-09-30 19:08 while pip_mon_testlab\Scripts\Source\PipMon_LeakTest.psc is
    # dated 2026-10-01 02:30 -- the report describes a tree that has since changed,
    # and nothing in the envelope said so.
    #
    # STALENESS IS DATA, NOT A STATUS, and that is a constraint rather than a
    # preference. The exit vocabulary is closed; STALE is not in it, and adding a
    # state is F2.1b, still owed to the owner and deliberately not started. A
    # caller gets `data.<report>.freshness.stale` today, and inventing a sixth
    # status would have added a state with no agreed exit number -- decoration by
    # the project's own test -- rather than a fact.
    #
    # Compared against the file's own mtime, not the `generatedUtc` stamp inside
    # it, because mtime is what the filesystem can be asked about and a stamp is a
    # claim by the writer.
    $inputs = @()
    foreach ($k in 'plugin', 'flagsFile') {
        $named = $rep.$k
        if ($named -and (Test-Path -LiteralPath $named)) { $inputs += $named }
    }
    $inputs += @($extraInputs | Where-Object { $_ })

    $reportTime = (Get-Item -LiteralPath $p).LastWriteTime
    $missing = @()
    $newest = $null
    $newestPath = $null
    foreach ($i in $inputs) {
        if (Test-Path -LiteralPath $i) {
            $mt = (Get-Item -LiteralPath $i).LastWriteTime
            if ($null -eq $newest -or $mt -gt $newest) { $newest = $mt; $newestPath = $i }
        } else {
            $missing += $i
        }
    }
    # Strictly newer. Equal mtimes are not stale: filesystem timestamp granularity
    # is a second or two here, and a report written in the same second as its input
    # has not been outrun by it.
    $stale = ($null -ne $newest) -and ($newest -gt $reportTime)

    $rep | Add-Member -NotePropertyName 'freshness' -Force -NotePropertyValue ([ordered]@{
        stale             = $stale
        report            = $p
        reportModifiedUtc = $reportTime.ToUniversalTime().ToString('o')
        input             = $newestPath
        inputModifiedUtc  = if ($null -ne $newest) { $newest.ToUniversalTime().ToString('o') } else { $null }
        inputsChecked     = @($inputs).Count
        inputsMissing     = @($missing)
        ageSeconds        = if ($null -ne $newest) { [math]::Round(($reportTime - $newest).TotalSeconds, 0) } else { $null }
        rule              = 'stale when an input the report describes is newer than the report file; file mtime, not the generatedUtc stamp inside it'
    })
    return $rep
}

function Run-Tool($script, $toolArgs) {
    $path = Join-Path $Repo $script
    if (-not (Test-Path $path)) {
        return @{ missing = $true; path = $path; output = @(); exit = 2 }
    }
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File $path @toolArgs 2>&1
    return @{ missing = $false; path = $path; output = @($out | ForEach-Object { [string]$_ }); exit = $LASTEXITCODE }
}

switch ($Command) {

    # ------------------------------------------------------------------ caps
    'caps' {
        # The discovery document. An agent that reads nothing else can call this
        # and learn every command, every exit code and every current blocker.
        $caps = [ordered]@{
            schema     = 'pipmon.surface/1'
            name       = 'PIP-MON workspace surface'
            entrypoint = 'tools/pipmon.ps1'
            generated  = [ordered]@{
                python   = '3.12+'
                game     = 'Fallout 4 1.11.240.0'
                editor   = 'CreationKit.exe 1.11.240.0'
                f4se     = 'NOT required and NOT deployed (replaced by this project)'
            }
            commands   = @(
                @{ n = 'caps';    does = 'this document: commands, exit codes, blockers'; args = @() }
                @{ n = 'status';  does = 'one-pass truth across every host, aggregated'; args = @() }
                @{ n = 'verify';  does = 'regenerate ai_state_dashboard.md and return its summary'; args = @() }
                @{ n = 'build';   does = 'compile Papyrus, fix compiler-named flags, verify, deploy'; args = @('-NoDeploy') }
                @{ n = 'link';    does = 'own plugins.txt: snapshot | apply | restore | status'; args = @('status', '-Disable <plugin>', '-Enable <plugin>') }
                @{ n = 'validate'; does = 'headless plugin validation via xEdit'; args = @('-Plugin <path>') }
                @{ n = 'rag';      does = 'local retrieval over archive/docs/source/state/logs, with provenance'; args = @('index', 'stats', 'vocabulary', 'query -Query "<terms>" -Kind <kind> -Limit <n> -MaxLines <n> -Page <n> -Format <dense|tsv|paths|json>') }
                @{ n = 'editor';  does = 'read-only editor-host inspection: preflight'; args = @('preflight') }
                @{ n = 'ck-session'; does = 'curated load-order swap: inspect | prepare | restore'; args = @('prepare') }
                @{ n = 'snapshot'; does = 'capture a restore point of plugin, pex and CK backups'; args = @('<tag>') }
                @{ n = 'docs';    does = 'where each kind of answer lives'; args = @() }
                @{ n = 'compat';  does = 'the legacy replacement map: what we replace, how, and what we add beyond it'; args = @('-Status <COVERED|DECLARED|PLANNED|DIFFERENT_MECHANISM|NOT_PLANNED|REJECTED>', '-RequiresHost <none|game|ck>') }
            )
            exitCodes  = [ordered]@{ GREEN = 0; OK = 0; RED = 1; BROKEN = 2; SKIP = 3; usage = 4 }
            invariants = @(
                'SKIP is never reported as PASS.',
                'Three commands write OUTSIDE the project, and they are the only three: build (deploy), link apply, link restore, and ck-session restore. ck-session prepare additionally writes plugins.txt.proposed.txt beside the live file without touching the live file. Nothing else writes outside the project.',
                'No command touches a running Creation Kit or xEdit process.',
                'Every fact in a response names the script or file it came from.',
                'Long third-party runs are launched detached and polled, never waited on while holding the caller.'
            )
            blockers   = @(
                @{ id = 'layer-a'; what = 'no vtable slot is hooked, so S0 (a compiled .psc reaching our natives) is unproven'; needs = 'a BSScript class declaration in method order to derive a slot index' }
                @{ id = 'facility-empty'; what = 'PipMonTestFacility.esp is a 66-byte header with 0 records; xEdit confirms it'; needs = 'a cell created and saved, then re-validated' }
                @{ id = 'xedit-untested-api'; what = 'the xEdit pascal API is only partly proven; GetPluginName does not exist in 4.1.5f and AddNewElement is unproven'; needs = 'one verified record-producing run, and the findings are recorded in runs\xedit\fo4edit-4.1.5f-pascal-api.md' }
                @{ id = 'ckpe'; what = 'Creation Kit render window crash-risks large cells (3 dumps recorded)'; needs = 'CKPE, or an in-house replacement' }
                @{ id = 'xedit-load-width'; what = 'xEdit loads Fallout4.ccc and the DLC list in addition to plugins.txt, so the 35-entry core does not bound the load'; needs = 'report plugin graph and resource graph separately' }
            )
        }
        Write-Output ($caps | ConvertTo-Json -Depth 6)
        $script:surfaceExit = 0
    }

    # ---------------------------------------------------------------- status
    'status' {
        $pap = Read-Report 'papyrus-latest.json' (Get-PapyrusInputs)
        $val = Read-Report 'xedit-latest.json' (Get-XeditInputs)

        $link = Run-Tool 'tools\linksync.ps1' @('status', '-GameDir', $GameDir)
        $dep = Run-Tool 'testfacility\ck\verify_deploy.ps1' @('-GameDir', $GameDir)

        # GUARD STATE, surfaced so an agent can see WHY a check will decline
        # before it declines. Read-only: this never signals the editor.
        $ckProc = Get-Process CreationKit -ErrorAction SilentlyContinue
        $guard = [ordered]@{
            creationKitRunning = [bool]$ckProc
            creationKitPid     = if ($ckProc) { $ckProc.Id } else { $null }
            policy             = 'no command writes to the game folder or launches a GUI tool while the editor is open'
        }

        $esp = Join-Path $GameDir 'Data\PipMonTestFacility.esp'
        $espInfo = $null
        if (Test-Path $esp) {
            $f = Get-Item $esp
            $espInfo = [ordered]@{
                path = $esp; bytes = $f.Length; modified = $f.LastWriteTime.ToString('s')
                note = 'a header-only plugin and an authored one are both "small"; size alone does not prove content'
            }
        }

        # A stale report is not evidence. Its recorded verdict describes a tree
        # that has changed since, so it is reported as unverified rather than as
        # the status it used to carry. SKIP is the existing word for "we could
        # not establish this" and invents no new state (F2.1b is still owed).
        $staleReports = @()
        if ($pap -and $pap.freshness.stale) { $staleReports += 'papyrus-latest.json' }
        if ($val -and $val.freshness.stale) { $staleReports += 'xedit-latest.json' }

        # Aggregate honestly: a SKIP anywhere is surfaced, not averaged away.
        $states = [ordered]@{
            papyrus = if (-not $pap) { 'NOT RUN' }
                      elseif ($pap.freshness.stale) { 'SKIP' }
                      else { $pap.status }
            pluginValidation = if (-not $val) { 'NOT RUN' }
                      elseif ($val.freshness.stale) { 'SKIP' }
                      else { $val.status }
            deploy = if ($dep.exit -eq 0) { 'GREEN' } else { 'ATTENTION' }
            link = if ($link.exit -eq 0) { 'GREEN' } else { 'ATTENTION' }
        }
        $overall = 'GREEN'
        # Asked BEFORE the RED branch, and that order is the fix. A stale papyrus
        # report previously reached `-ne 'GREEN'` and produced RED, which claims
        # the build ran and is wrong -- a claim about a build nobody performed. We
        # cannot say it is wrong either; we can only say it is unestablished.
        if ($states.papyrus -eq 'SKIP') { $overall = 'SKIP' }
        elseif ($states.papyrus -ne 'GREEN') { $overall = 'RED' }
        elseif ($states.pluginValidation -notin 'PASS', 'GREEN') { $overall = 'SKIP' }
        elseif ($states.deploy -ne 'GREEN' -or $states.link -ne 'GREEN') { $overall = 'ATTENTION' }

        $reason = switch ($overall) {
            'GREEN' { $null }
            'RED' { 'the Papyrus build is not green; read data.papyrus.tail' }
            'SKIP' {
                if ($states.papyrus -eq 'SKIP') {
                    "the Papyrus report predates the sources it describes ($($staleReports -join ', ')), so the build is UNVERIFIED rather than fine; read data.papyrus.freshness"
                } else {
                    'plugin validation could not run, so the plugin is UNVERIFIED rather than fine'
                }
            }
            default { 'one or more checks need attention; see data' }
        }

        Emit $overall $reason ([ordered]@{
            guard       = $guard
            states      = $states
            staleReports = $staleReports
            papyrus     = $pap
            pluginValidation = $val
            facilityPlugin = $espInfo
            linkOutput  = $link.output
            deployOutput = $dep.output
        })
    }

    # ---------------------------------------------------------------- verify
    'verify' {
        # -GameDir was accepted by the surface and dropped here: @() passed
        # nothing, so `verify -GameDir X` silently verified the default folder.
        # agent_watchdog.ps1 has declared [string]$GameDir since it was written.
        $r = Run-Tool 'tools\agent_watchdog.ps1' @('-GameDir', $GameDir)
        $dash = Join-Path $Repo 'ai_state_dashboard.md'

        # TOTAL BY CONSTRUCTION -- F2.4. The old line was
        #     Emit (@{ 0='GREEN'; 1='RED'; 2='BROKEN'; 3='SKIP' })[$r.exit])
        # and it had two independent failures. The map covered 0-3 only, so any
        # other child exit made the lookup $null; and Emit's own guard turns a
        # $null status into BROKEN (F2.1a), so an unmapped exit was at least loud
        # -- but the reason string was the CONSTANT "dashboard regenerated",
        # which is the thing that made it read as fine. A `default` arm is used
        # rather than relying on the guard two frames away, so the verdict is
        # stated where it is decided.
        $status = switch ($r.exit) {
            0 { 'GREEN' }
            1 { 'RED' }
            2 { 'BROKEN' }
            3 { 'SKIP' }
            default { 'BROKEN' }
        }
        if ($r.missing) { $status = 'BROKEN' }

        $lastLine = @($r.output | Where-Object { $_ -match '\S' } | Select-Object -Last 1)
        $reason = if ($r.missing) {
            "agent_watchdog.ps1 not found at $($r.path), so the dashboard was not regenerated and nothing is verified"
        } elseif ($status -eq 'GREEN') {
            'dashboard regenerated; read the file for the sourced detail'
        } else {
            "dashboard regenerated but the pass did not conclude green (agent_watchdog exit $($r.exit)): $lastLine"
        }

        Emit $status $reason ([ordered]@{
            dashboard = $dash; dashboardExists = (Test-Path $dash)
            exit = $r.exit; watchdog = $r.path; gameDir = $GameDir; output = $r.output
        })
    }

    # ----------------------------------------------------------------- build
    'build' {
        $a = @('-GameDir', $GameDir)
        if ($NoDeploy) { $a += '-NoDeploy' }
        $r = Run-Tool 'tools\watch_papyrus.ps1' $a
        $rep = Read-Report 'papyrus-latest.json' (Get-PapyrusInputs)
        # A report older than the sources it describes is not this build's result.
        # `build` has just run the compiler, so a report that did not move means
        # nothing was written -- and the pre-fix line read the old file and
        # reported its verdict as if it were the build that just happened.
        $status = if (-not $rep -or $rep.freshness.stale) { 'BROKEN' } else { $rep.status }
        if ($status -eq 'GREEN') { $status = 'GREEN' }
        elseif ($status -eq 'RED') { $status = 'RED' }
        else { $status = 'BROKEN' }
        $why = if ($rep -and $rep.freshness.stale) {
            "papyrus compile/fix/verify/deploy produced no fresh report: runs\watch\papyrus-latest.json is older than $($rep.freshness.input), so this build is UNVERIFIED rather than fine"
        } else { 'papyrus compile/fix/verify/deploy' }
        Emit $status $why ([ordered]@{ report = $rep; output = $r.output })
        exit $script:surfaceExit
    }

    # ------------------------------------------------------------------ link
    'link' {
        $sub = if ($Arg) { $Arg } else { 'status' }
        $a = @($sub, '-GameDir', $GameDir)
        # Forwarded rather than dropped. linksync.ps1 has declared and implemented
        # -Enable/-Disable since before this surface advertised them, so the toggle
        # the compiled-environment model depends on was one argument list away and
        # the list was never built. Comma-joined into a single token, which is how
        # PowerShell binds a [string[]] from a splatted argument array.
        if ($Enable)  { $a += @('-Enable',  ($Enable  -join ',')) }
        if ($Disable) { $a += @('-Disable', ($Disable -join ',')) }
        $r = Run-Tool 'tools\linksync.ps1' $a
        if ($r.missing) {
            Emit 'BROKEN' "linksync.ps1 not found at $($r.path)" ([ordered]@{})
            exit $script:surfaceExit
        }
        # exit 2 from linksync is its own "no snapshot to restore from" and its own
        # "the thing is missing", both of which are BROKEN, not RED. That split is
        # F2.5 and is NOT done here: it needs to tell a thrown precondition from a
        # wrong result, and linksync signals both by exit 1 today.
        $status = if ($r.exit -eq 0) { 'GREEN' } elseif ($r.exit -eq 2) { 'BROKEN' } else { 'RED' }
        $toggled = [ordered]@{ enable = @($Enable); disable = @($Disable) }
        Emit $status "load-order link: $sub" ([ordered]@{ exit = $r.exit; toggled = $toggled; output = $r.output })
        exit $script:surfaceExit
    }

    # -------------------------------------------------------------- validate
    'validate' {
        $a = @()
        if ($Plugin) { $a += @('-Plugin', $Plugin) }
        $r = Run-Tool 'tools\validate_plugin.ps1' $a
        $rep = Read-Report 'xedit-latest.json' (Get-XeditInputs)
        # Same reasoning as build: the validator has just run, so a report older
        # than the plugin it describes is a leftover, not this run's verdict.
        $status = if (-not $rep) { 'SKIP' }
                  elseif ($rep.freshness.stale) { 'SKIP' }
                  else { $rep.status }
        # The report's own reason string is only quoted when it is fresh. A stale
        # report's reason describes a run that is not this one, and repeating it
        # verbatim as the surface's reason is the same lie one level up.
        $why = if (-not $rep) { 'no validation report produced' }
               elseif ($rep.freshness.stale) {
                   "validation produced no fresh report: runs\watch\xedit-latest.json is older than $($rep.freshness.input), so the plugin is UNVERIFIED rather than fine"
               }
               elseif ($rep.reason) { $rep.reason }
               else { 'no validation report produced' }
        Emit $status $why `
            ([ordered]@{ report = $rep; output = $r.output })
    }

    # ------------------------------------------------------------ ck-session
    # The curated load-order swap. This is the one command that writes the file
    # every other writer also wants, so it is exposed as its own verb rather
    # than folded into 'link': swapping the order in and out again is a
    # deliberate, reversible act and should look like one.
    'ck-session' {
        $sub = if ($Arg) { $Arg } else { 'inspect' }
        $r = Run-Tool 'tools\ck_session.ps1' @($sub, '-GameDir', $GameDir)
        if ($r.missing) {
            Emit 'BROKEN' "ck_session.ps1 not found at $($r.path)" ([ordered]@{})
            exit $script:surfaceExit
        }
        $status = switch ($r.exit) { 0 { 'GREEN' } 2 { 'BROKEN' } default { 'RED' } }
        Emit $status "creation engine session load order: $sub" ([ordered]@{ exit = $r.exit; output = $r.output })
        exit $script:surfaceExit
    }

    # -------------------------------------------------------------- snapshot
    # The save rule, as a command rather than a habit: capture a restore point
    # whenever something is properly or semi-completely done. The task runner
    # snapshots after every step IT runs, but the editor's saves happen at the
    # keyboard, where no runner is watching -- and the Creation Kit keeps its own
    # backups in Data\Backup\, which is inside the game folder and is not a
    # restore point the project controls.
    'snapshot' {
        $what = if ($Arg) { $Arg } else { 'manual' }
        $dir = Join-Path $Repo 'runs\tasks\facility-v0\snapshots'
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $taken = @()
        # What a snapshot is FOR is a restore point. Zero captured files means
        # there is no restore point, so this cannot report GREEN. The previous
        # version emitted GREEN with files=[] and the reason "snapshot taken",
        # which is a silent success on the one verb whose entire job is to be
        # believed. Reproduced before the fix: exit 0, ok=true, 0 files.
        $want = @('Data\PipMonTestFacility.esp', 'Data\Scripts\PipMonTestFacility.pex', 'Data\Scripts\PipMon.pex')
        $missing = @()
        $got = 0
        foreach ($f in $want) {
            $src = Join-Path $GameDir $f
            if (Test-Path -LiteralPath $src) {
                $leaf = [IO.Path]::GetFileName($src)
                $dst = Join-Path $dir "$leaf.$what.$stamp.bak"
                Copy-Item -LiteralPath $src -Destination $dst -Force
                $taken += [ordered]@{ from = $src; to = $dst; bytes = (Get-Item $dst).Length }
                $got++
            } else {
                $missing += $f
            }
        }
        # The editor's own backups are outside the project and can be swept.
        $ckBak = Join-Path $GameDir 'Backup'
        if (Test-Path $ckBak) {
            Get-ChildItem $ckBak -Filter '*.bak' -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 5 | ForEach-Object {
                    $dst = Join-Path $dir "ck-own.$($_.Name).$stamp"
                    Copy-Item -LiteralPath $_.FullName -Destination $dst -Force
                    $taken += [ordered]@{ from = $_.FullName; to = $dst; bytes = $_.Length }
                }
        }
        # GREEN requires a real restore point. The counts go in data rather than
        # into a new status, because a PARTIAL verdict is a vocabulary decision
        # (F2.1b) and data is branchable today while a new status is not agreed.
        # Deployed artefacts and editor backups are counted SEPARATELY: they are
        # different kinds of thing, and a single captured/expected pair across
        # both implies a ratio that does not mean anything.
        $backups = $taken.Count - $got
        $status = if ($taken.Count -gt 0) { 'GREEN' } else { 'BROKEN' }
        $reason = if ($taken.Count -gt 0) {
            "snapshot '$what' taken: $got of $($want.Count) deployed artefact(s)$(if ($backups) { " plus $backups editor backup(s)" })"
        } else {
            "snapshot '$what' captured NOTHING, so there is no restore point. Searched '$GameDir' for $($want.Count) expected file(s): $($want -join ', ')"
        }
        Emit $status $reason ([ordered]@{
            tag = $what; directory = $dir; files = $taken
            deployedExpected = $want.Count; deployedCaptured = $got; missing = $missing
            editorBackups = $backups
        })
        exit $script:surfaceExit
    }

    # ---------------------------------------------------------------- editor
    'editor' {
        # READ-ONLY. The surface deliberately does not drive the Creation Kit:
        # it has no scriptable interface here, three crash dumps are on record,
        # and sending it keystrokes fights the user for the keyboard.
        $sub = if ($Arg) { $Arg } else { 'preflight' }
        $ck = Join-Path $GameDir 'CreationKit.exe'
        $game = Join-Path $GameDir 'Fallout4.exe'
        $running = [bool](Get-Process CreationKit -ErrorAction SilentlyContinue)

        $facts = [ordered]@{}
        if (Test-Path $ck) { $facts['creationKit'] = (Get-Item $ck).VersionInfo.ProductVersion }
        else { $facts['creationKit'] = $null }
        if (Test-Path $game) { $facts['game'] = (Get-Item $game).VersionInfo.ProductVersion }
        else { $facts['game'] = $null }
        $facts['buildsMatch'] = ($facts['creationKit'] -and $facts['game'] -and $facts['creationKit'] -eq $facts['game'])
        $ckpe = @(Get-ChildItem (Join-Path $GameDir 'Data') -Directory -ErrorAction SilentlyContinue |
                  Where-Object { $_.Name -match 'PlatformExtended|CKPE' })
        $facts['ckpe'] = if ($ckpe.Count) { ($ckpe | Select-Object -ExpandProperty Name) -join ', ' } else { $null }
        $facts['creationKitRunning'] = $running
        $facts['policy'] = 'read-only: this surface never drives the editor and never writes to the game folder'

        if (-not $facts['creationKit']) {
            Emit 'BROKEN' 'CreationKit.exe not found in the game folder' $facts
            exit $script:surfaceExit
        }
        if (-not $facts['buildsMatch']) {
            Emit 'RED' 'Creation Kit and game builds differ; an authored plugin can be rejected on load' $facts
            exit $script:surfaceExit
        }
        if (-not $facts['ckpe']) {
            Emit 'SKIP' 'CKPE is absent, so the editor render window crash-risks larger cells (3 dumps on record)' $facts
            exit $script:surfaceExit
        }
        Emit 'GREEN' $null $facts
        exit $script:surfaceExit
    }

    # -------------------------------------------------------------------- rag
    # Local retrieval over the workspace: the inspiration archive, docs, source,
    # task state and tool logs. Standard library only, no network, no model.
    # Every hit carries its path, line range and hash, so any claim retrieved
    # here can be traced to the file that supports it. This exists so that
    # "where does that live" and "what did we already learn" are answered from
    # an index instead of from a grep plus a guess.
    'rag' {
        $sub = if ($Arg) { $Arg } else { 'stats' }
        $indexer = Join-Path $Repo 'tools\rag_index.py'
        $queryTool = Join-Path $Repo 'tools\rag_query.py'
        $db = Join-Path $Repo 'rag\index.sqlite3'

        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            Emit 'BROKEN' 'python is not on PATH, so the local index cannot be built or queried' ([ordered]@{ indexer = $indexer })
            exit $script:surfaceExit
        }

        if ($sub -eq 'index') {
            $out = & python $indexer 2>&1
            $code = $LASTEXITCODE
            $stats = if (Test-Path $db) { @(& python $queryTool '--stats' 2>&1) } else { @() }
            $status = if ($code -eq 0) { 'GREEN' } else { 'RED' }
            Emit $status $(if ($code -eq 0) { $null } else { 'rag_index.py returned a nonzero exit' }) ([ordered]@{
                    db     = $db
                    exit   = $code
                    output = @($out | ForEach-Object { [string]$_ })
                    stats  = @($stats | ForEach-Object { [string]$_ })
                })
            exit $script:surfaceExit
        }

        if (-not (Test-Path $db)) {
            Emit 'SKIP' "no local index at $db; build it with: tools\pipmon.ps1 rag index" ([ordered]@{ db = $db })
            exit $script:surfaceExit
        }

        if ($sub -eq 'stats') {
            $out = & python $queryTool '--stats' 2>&1
            Emit 'GREEN' $null ([ordered]@{ db = $db; stats = @($out | ForEach-Object { [string]$_ }) })
            exit $script:surfaceExit
        }

        if ($sub -eq 'vocabulary') {
            # Self-description. A program that wants to query this workspace well
            # should read the vocabulary rather than hardcode its own idea of the
            # project's words, and the format is the same one used for hits.
            $va = @($queryTool, '--vocabulary')
            if ($Format -eq 'json') { $va += '--format' }
            $vout = & python @va 2>&1
            Emit 'GREEN' 'retrieval vocabulary: the surface forms this index understands' ([ordered]@{
                    format = $Format
                    terms  = @($vout | ForEach-Object { [string]$_ })
                })
            exit $script:surfaceExit
        }

        if (-not $Query) {
            Emit 'RED' 'rag query needs terms: tools\pipmon.ps1 rag query -Query "..." (-Kind, -Limit)' ([ordered]@{
                    usage = 'rag index | rag stats | rag query -Query <terms> [-Kind <kind>] [-Limit <n>]'
                })
            exit $script:surfaceExit
        }

        $a = @($queryTool, $Query, '--limit', "$Limit")
        if ($Kind) { $a += @('--kind', $Kind) }
        if ($MaxLines -gt 0) { $a += @('--max-lines', "$MaxLines") }
        if ($Page -gt 1) { $a += @('--page', "$Page") }
        if ($Format -and $Format -ne 'dense') { $a += @('--format', $Format) }
        $out = & python @a 2>&1
        $code = $LASTEXITCODE
        $status = if ($code -eq 0) { 'GREEN' } else { 'RED' }
        Emit $status $(if ($code -eq 0) { $null } else { 'rag_query.py returned a nonzero exit' }) ([ordered]@{
                query = $Query; kind = $Kind; limit = $Limit
                maxLines = $MaxLines; page = $Page; format = $Format
                exit = $code
                hits  = @($out | ForEach-Object { [string]$_ })
            })
        exit $script:surfaceExit
    }

    # ------------------------------------------------------------------ docs
    'docs' {
        $doors = [ordered]@{
            'state of everything right now' = 'ai_state_dashboard.md  (generated; read this first)'
            'what to do next / why'         = 'HANDOVER.md  (cold-start brief)'
            'what the project is'           = 'README.md'
            'the design record'             = 'PIP-MON_CONSOLIDATED.txt  (append-only)'
            'this surface, in prose'        = 'tools\pipmon.ps1 caps  (self-describing, generated from the same source so it cannot drift; a dedicated PIPMON_INTERFACE.md is OWED and does not exist)'
            'the test facility'             = 'testfacility\HANDOVER.md, FACILITY-SPEC.md, QUEST-SPEC.md, COVERAGE.md'
            'the CK session checklist'      = 'testfacility\ck\README.md'
            'the wire contract'             = 'docs\IPC_PROTOCOL.md  (partly fiction; see HANDOVER section 11)'
            'heuristics'                    = 'docs\ANOMALY_RULES.md'
            'rules that are inviolable'     = 'docs\ENGINEERING_RULES.md  (stale, but PITFALL 1 is unique)'
            'the original ideas'            = 'inspiration archive\  (inspiration, not decisions)'
            'what xEdit 4.1.5f can actually do' = 'runs\xedit\fo4edit-4.1.5f-pascal-api.md  (measured, not documented)'
            'anything, with provenance'     = 'tools\pipmon.ps1 rag query -Query "..."'
        }
        # A door map that points at a file which does not exist is worse than one
        # with no entry, so the gaps are declared rather than left to be found.
        # All 15 advertised paths were checked on 2026-10-03; this was the only
        # one missing.
        Emit 'GREEN' $null ([ordered]@{
            doors = $doors
            gaps  = @('PIPMON_INTERFACE.md: advertised by this map until 2026-10-03 and absent. The door now points at caps. Writing the document is owed.')
        })
        exit $script:surfaceExit
    }

    # ------------------------------------------------------------------ compat
    'compat' {
        # The verb ai_context/spec/surfaces.json has advertised since before it
        # existed. SERVING it is the fix rather than deleting the claim: shrinking
        # the spec to match a gap would make the disagreement permanent, and this
        # map is the answer to the question a modder actually asks.
        #
        # Host-free by construction: it reads one JSON file inside the project and
        # launches nothing.
        $path = Join-Path $Repo 'ai_context\spec\legacy_replacement.json'
        if (-not (Test-Path -LiteralPath $path)) {
            Emit 'BROKEN' "replacement map not found at $path" ([ordered]@{ expected = $path })
            exit $script:surfaceExit
        }
        try { $map = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json }
        catch {
            Emit 'BROKEN' "replacement map at $path did not parse: $($_.Exception.Message)" ([ordered]@{ path = $path })
            exit $script:surfaceExit
        }
        if (-not $map.entries) {
            Emit 'BROKEN' 'replacement map parsed but has no entries array' ([ordered]@{ path = $path })
            exit $script:surfaceExit
        }

        $rows = @($map.entries)
        $total = $rows.Count

        # Filters are validated against the data, not trusted. A typo narrows to
        # an empty result that says so, rather than silently returning everything.
        #
        # BOTH vocabularies come from the FULL map, computed before any narrowing.
        # Validating the second filter against the already-narrowed set was wrong
        # and was caught by testing: `-Status COVERED -RequiresHost ck` reported
        # BROKEN because the single surviving COVERED row has host=game, which
        # made a legitimate host look invalid. A valid combination that matches
        # nothing is an empty result (SKIP), never a contract violation (BROKEN).
        $statusVocab = @($rows | ForEach-Object { $_.status } | Sort-Object -Unique)
        $hostVocab   = @($rows | ForEach-Object { $_.requires_host } | Sort-Object -Unique)
        $applied = [ordered]@{}
        if ($Status) {
            if ($Status -notin $statusVocab) {
                Emit 'BROKEN' "-Status '$Status' is not a status any row uses" ([ordered]@{ given = $Status; known = $statusVocab })
                exit $script:surfaceExit
            }
            $rows = @($rows | Where-Object { $_.status -eq $Status })
            $applied.status = $Status
        }
        if ($RequiresHost) {
            if ($RequiresHost -notin $hostVocab) {
                Emit 'BROKEN' "-RequiresHost '$RequiresHost' is not a host any row uses" ([ordered]@{ given = $RequiresHost; known = $hostVocab })
                exit $script:surfaceExit
            }
            $rows = @($rows | Where-Object { $_.requires_host -eq $RequiresHost })
            $applied.requiresHost = $RequiresHost
        }

        # Counts are computed over the UNFILTERED set, so the summary always
        # describes the whole map and a filter never looks like shrinkage.
        $byStatus = [ordered]@{}
        foreach ($g in (@($map.entries) | Group-Object status | Sort-Object Name)) { $byStatus[$g.Name] = $g.Count }
        $byHost = [ordered]@{}
        foreach ($g in (@($map.entries) | Group-Object requires_host | Sort-Object Name)) { $byHost[$g.Name] = $g.Count }

        # A filter that matched nothing is an EMPTY RESULT, not a pass and not a
        # failure. SKIP is the honest landing and it must not be read as fine.
        if ($rows.Count -eq 0) {
            Emit 'SKIP' "no replacement-map row matches $((($applied.Keys | ForEach-Object { "$_=$($applied[$_])" }) -join ', '))" `
                ([ordered]@{ filtered = $applied; totalRows = $total; byStatus = $byStatus; byHost = $byHost; rows = @() })
            exit $script:surfaceExit
        }

        Emit 'GREEN' $null ([ordered]@{
            spec        = $map.spec_id
            authority   = $map.authority
            source      = 'ai_context/spec/legacy_replacement.json'
            totalRows   = $total
            byStatus    = $byStatus
            byHost      = $byHost
            filtered    = $applied
            matched     = $rows.Count
            rows        = @($rows | ForEach-Object {
                [ordered]@{
                    name           = $_.name
                    sourceProduct  = $_.source_product
                    status         = $_.status
                    requiresHost   = $_.requires_host
                    ourEquivalent  = $_.our_equivalent
                }
            })
        })
        exit $script:surfaceExit
    }

    default {
        Write-Output '{"schema":"pipmon.surface/1","status":"BROKEN","reason":"unknown command; run: tools\\pipmon.ps1 caps"}'
        $script:surfaceExit = 4
    }
}

exit $script:surfaceExit
