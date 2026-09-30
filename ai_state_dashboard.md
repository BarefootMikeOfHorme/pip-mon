# AI state dashboard

> GENERATED FILE -- do not edit. Regenerate with `tools\agent_watchdog.ps1`.
> A hand edit here is discarded on the next run, silently. Fix the source instead.

- generated : 2026-09-30 13:17:52 -05:00
- workspace : `C:\Users\Administrator\Desktop\Pip-mon Script Management system`
- purpose   : one place to read what is VERIFIED, what is NOT, and what is BLOCKED,
              so a fresh session never re-derives it or trusts a stale claim.

## Papyrus surface

source: `tools\watch_papyrus.ps1` -> `vprobe\papyrus\build_papyrus.bat`

- status  : **GREEN** (exit 0, 1 pass(es) of 6)
- built   : `PipMon.pex` = 1034 B
- built   : `PipMonTestFacility.pex` = 12080 B
- deployed: `Data\Scripts\PipMon.pex` = 1034 B
- deployed: `Data\Scripts\PipMonTestFacility.pex` = 12080 B

## Deployment (game folder)

source: `testfacility\ck\verify_deploy.ps1` (read-only)

```

PIP-MON deploy verification
  game dir : C:\Program Files (x86)\Steam\steamapps\common\Fallout 4

Papyrus surface
  [ OK ] Data\Scripts\PipMon.pex            1034 B, magic valid
  [ OK ] Data\Scripts\PipMonTestFacility.pex 12080 B, magic valid

Address database
  [ OK ] Data\PIP-MON\libs\vprobe.addresses.txt 541674 B
  [ OK ] Data\PIP-MON\libs\vprobe.addresses.bin 103428 B

Plugin
  [ OK ] PipMonTestFacility.esp             973 B  09-30 12:50

Toolchain
  [ OK ] CreationKit.exe                    1.11.240.0
  [ OK ] CK matches game build              CK 1.11.240.0 / game 1.11.240.0
  [FAIL] CKPE installed                     absent -- render crashes likely on large cells

  1 check(s) failed
```

## Load order link

source: `tools\linksync.ps1 status` (snapshot/apply/restore lives beside it)

```

link status
-----------
  file        : C:\Users\Administrator\AppData\Local\Fallout4\plugins.txt
  modified    : 9/30/2026 5:58:37 AM
  lines       : 177
  enabled     : 61
  our plugin  : PipMonTestFacility.esp
  our plugin  : *PipMonTestFacility.esp -- enabled, last (active file)
  deployed    : 973 B, 9/30/2026 12:50:54 PM

  snapshots   :
    20260930-054118  
```

## Plugin validation

source: `tools\validate_plugin.ps1` -> xEdit headless + `testfacility\xedit\validate_plugin.pas`

- status : **SKIP** (exit 3)
- reason : xEdit did not complete headlessly in 90s. On this machine it has never been run interactively, so it blocks on its first-run notice; click through that notice once and this becomes a real validation instead of a skip.
- note   : SKIP is not PASS. A skip means the check could not run, so the
          property it covers is UNVERIFIED, not fine.

## Live runtime (most recent run)

source: `runs\20260930-073747`

```
{
  "startedUtc": "2026-09-30T07:37:48.7180511Z",
  "endedUtc": "2026-09-30T07:37:51.6985343Z",
  "elapsedSec": 3,
  "pid": 31512,
  "summary": "ready_then_exit",
  "exitCode": 0,
  "stillRunning": false,
  "boundedSec": 120,
  "traceArmed": true,
  "debug": false,
  "dllBytes": 961024,
  "reachedReady": true,
  "lastLine": "[02:37:50] [STARTUP] bootstrap complete; runtime ready",
  "note": "pipe intentionally never opened; see Trace.hpp"
}
```

```
[02:37:48] [STARTUP] game module located; settling
[02:37:50] [STARTUP] bootstrap entered
[02:37:50] [STARTUP] vlink pipe opened
[02:37:50] [STARTUP] bootstrap complete; runtime ready
```

## Summary

| check | state |
|---|---|
| papyrus | GREEN |
| deploy | ATTENTION |
| pluginValidation | SKIP |
| xEditExit | 3 |

## Still blocked (unchanged by this run)

1. **No vtable slot is hooked.** Layer A does not exist, so a compiled .psc cannot
   reach our natives and S0 is unproven. Blocked on one input: a BSScript class
   declaration in method order, to turn a slot index into a name.
2. **xEdit headless** cannot run until its first-run notice is clicked through once.
3. **CKPE absent**: the CK render window crash-risks large cells; three CK crash
   dumps recorded. On the in-house replacement list.
4. **The facility cell does not exist yet.** PipMonTestFacility.esp is a valid
   header with no records; the CK session or a headless generator must add them.
