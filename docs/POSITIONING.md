================================================================================
 PIP-MON - POSITIONING AND REPLACEMENT SCOPE
================================================================================

STATUS: adopted as project direction. Written down so that every later design
decision can be checked against it, and so that "is this reinventing something
that already exists?" has a documented answer.


--------------------------------------------------------------------------------
1. THE ONE-LINE VERSION
--------------------------------------------------------------------------------

Papyrus is native to Fallout 4 and cannot be replaced. PIP-MON replaces the
layer that EXTENDS and INTERACTS with Papyrus -- the script extender and the
mod ecosystem built on top of it -- and absorbs the useful ideas from those
projects as inspiration.


--------------------------------------------------------------------------------
2. THE LINE: WHAT IS REPLACED AND WHAT IS NOT
--------------------------------------------------------------------------------

  NATIVE TO THE GAME - we target it, never replace it
  -----------------------------------------------
  * The Papyrus virtual machine and its bytecode format
  * ScriptExtender-style plugin containers we still have to READ (.esp/.esm/.esl)
  * The Creation Kit plugin record format
  * The game executable itself

  REPLACEABLE - this is PIP-MON's actual job
  -----------------------------------------
  * F4SE (and its plugin/addon ecosystem)
  * Script extender hosted papyrus extensions
  * Garden of Eden and its plugin family
  * PAP and comparable papyrus helper frameworks
  * Standalone papyrus script packs, and the conventions they established

  INSPIRATION ONLY - ideas taken, no code, no dependency, no identity
  -----------------------------------------------------------------
  * AOB / signature scanning methodology
  * Relocation-database concepts (static RVA per build, with a scan fallback)
  * Console command and script-property API design
  * Load-order conflict resolution techniques
  * The idea that a "papyrus debugger" is worth having at all


--------------------------------------------------------------------------------
3. WHY THE DISTINCTION IS DRAWN HERE AT ALL
--------------------------------------------------------------------------------

Three reasons, and the first is the one that matters:

  1. An AI agent that sees a reference implementation in the context will
     naturally reach for it -- vendor the library, call its API, or copy its
     structure. That is the failure mode this document exists to prevent. The
     correct move is to reimplement from the specification and the game, not to
     depend on someone else's project that may be abandoned, forked, or
     relicensed.

  2. A dependency is a liveness obligation. If F4SE stops being maintained, and
     PIP-MON is built on F4SE, PIP-MON dies with it. PIP-MON is intended to
     outlive everything it learns from.

  3. Replacement requires incompatibility, not extension. If PIP-MON were a
     set of F4SE plugins it could never replace F4SE -- it would be a
     dependency wearing a costume. The goal explicitly includes F4SE no longer
     being required.


--------------------------------------------------------------------------------
4. CURRENT REALITY, STATED PLAINLY
--------------------------------------------------------------------------------

CORRECTED 2026-10-03 (agent A3, task F1.5). This section previously opened
"F4SE is a HARD RUNTIME DEPENDENCY TODAY". That was true when written and is
false now. The failed claim is recorded in full at the end of this section
rather than deleted, because a document edited to look as though it was never
wrong teaches the reader nothing.

F4SE is NOT a runtime dependency. Nothing here needs it, and it is not
deployed.

  * No F4SE loader exists. Any file under Data/F4SE/ is inert.
    Source: ai_context/project_blueprint.md, "No F4SE loader is deployed, by
    design. The DLLs under Data\F4SE\Plugins, if present, are inert."
  * vprobe.dll loads through OUR OWN path or not at all: launcher/
    src/ProcessLaunch.cpp does CREATE_SUSPENDED, verify build identity,
    LoadLibraryW one DLL, resume. With no F4SE present, vprobe.dll runs. The
    reverse is not true, and that asymmetry is the whole design.
  * The F4SE ABI entry points are RETAINED, ON PURPOSE, and they point the
    other way. vprobe/include/PipmonEntry.hpp:115 declares F4SEAPI_MakePluginInfo
    as an ADAPTER: F4SE calls US. This is coexistence, not dependency. A user
    running the F4SE mod ecosystem keeps working, and removing a working
    integration in order to make a point about independence would be the
    opposite of the coexistence contract.
    Verified in the built artefact, 2026-10-03: the strings F4SEAPI_MakePluginInfo,
    VPROBE_OnLoad, PIPMON_Query, PIPMON_Initialize and PIPMON_LastError are all
    present in runs/20260930-073747/vprobe.dll (961,024 bytes). Their presence
    is NOT evidence of a dependency, which is exactly why the old sentence in
    this section was wrong.
  * No F4SE, no CommonLibF4, no extender is linked, imported or required. The
    runtime import table of the built vprobe.dll is KERNEL32.dll ONLY; link
    inputs are kernel32, user32, Psapi and vendored Zydis.
    Source: HANDOVER.md section 2, "INDEPENDENCE (verified by inspection of the
    built artefact)".
  * vprobe reads its own libraries from Data\PIP-MON\libs, not from
    Data\F4SE\Plugins\vprobe\libs. vprobe/src/main.cpp records why, and it is
    the same lesson as the paragraph above: the old path worked on any machine
    that happened to have F4SE installed and broke on exactly the machine we
    are building for, and the dependency was invisible precisely because it was
    satisfied.
  * This is binding, not a preference: ai_context/f4se_prohibition.md,
    status "ACTIVE - BINDING CONSTRAINT". Never build on F4SE, never rely on
    it, never suggest it.

  Still true, re-checked 2026-10-03:

  * Garden of Eden and PAP are referenced in NO CODE. No code, no config
    parsing, no asset reuse. They are now rows in
    ai_context/spec/legacy_replacement.json instead of being merely mentioned:
    "GoE Script Extender" and "PAP (Power of Ascension)", both PLANNED, both
    naming KaDag plus the Rust daemon pipeline as the equivalent. Note the
    standing trap: a DIFFERENT Garden of Eden exists (G.E.C.K., a Fallout 3 /
    New Vegas editor), it is a peer tool, and conflating the two is a documented
    hazard. See ai_context/spec/nomenclature.json.
  * CommonLibF4 and AddressLib appear in vprobe/CMakeLists.txt as FetchContent
    declarations (lines 74-83) behind option VPROBE_FETCH_DEPS, which is ON by
    default. The declarations are real; the dependency is not. The current
    sources are self-contained and link neither. The relocation-INI *concept*
    is borrowed; the code is not used. Contrast CommonLibF4, which IS
    depended on: it is a layout library, so depending on it is depending on
    facts about the game.

  One known live violation, recorded rather than smoothed over: per
  ai_context/f4se_prohibition.md section 3 (found 2026-10-01, still open),
  XDI.esm, FCOM.esp and Cheat Terminal are enabled in dplugins.txt and none of
  them has its runtime present. Our validator does not check for this, so it
  would report green.

WHAT THIS SECTION USED TO SAY, AND WHY IT STOPPED BEING TRUE

  The previous text was:

    "F4SE is a HARD RUNTIME DEPENDENCY TODAY, and that is a known gap.
     vprobe.dll exports F4SEAPI_MakePluginInfo and is loaded by F4SE from
     Data/F4SE/Plugins/. With no F4SE, it does not run.
     F4SE is retained FOR TESTING because it is the only way to load a plugin
     into the game today."

  It was not a careless sentence. It was correct while vprobe's load contract
  really was F4SE's: the entry points were F4SEAPI_MakePluginInfo plus
  VPROBE_OnLoad, called by the extender. Two facts changed under it.

  1. The launcher path was built. It loads a DLL into the game without any
     extender, so "the only way to load a plugin into the game today" stopped
     being true.
  2. The load contract was inverted. The header comment at
     vprobe/include/PipmonEntry.hpp:4-20 records the change in its own words:
     vprobe "originally exposed F4SE's plugin ABI ... That made an F4SE
     installation a hard runtime dependency of a project whose entire premise
     is replacing F4SE ... So: the contract becomes OURS, and F4SE becomes an
     ADAPTER that calls into it."

  Where the correction is recorded besides here:
    ai_context/spec/program_components.json, entry F4SE - "NOT a dependency,
      NOT a target API, NOT deployed"
    ai_context/project_blueprint.md - "No F4SE loader is deployed, by design"
    HANDOVER.md section 2 - the independence block, read off the built artefact
    ai_context/f4se_prohibition.md - ACTIVE - BINDING CONSTRAINT
    ai_context/spec/program_components.2.json, entry F4SE - names the two
      F4SE rows it takes over and which of them are built

  What git cannot tell you: the repository has a single squashed initial commit
  (2d5f832, 2026-09-29), so there is no commit that dates the switch from
  dependency to adapter. The two source files above are the record. Stating
  that is better than inventing a date.

  Section 6 below still describes the original four-phase path to F4SE
  independence and calls it "Not scheduled". Phase A is done: the F4SE export is
  retained AND a standalone bootstrap exists. Phases B to D are not
  independently verifiable from here; the replacement map
  (ai_context/spec/legacy_replacement.json) is the current statement of which
  jobs are covered, which of them are merely planned, and which are declined.


--------------------------------------------------------------------------------
5. CONFLICT AVOIDANCE - THE ACTUAL RISK SURFACE
--------------------------------------------------------------------------------

Ideas cannot conflict. Identity can. The vectors that would genuinely collide
with a legacy mod, and where PIP-MON currently stands:

  VECTOR                  PIP-MON POSITION                        STATUS
  ----------------------  --------------------------------------  ---------
  Console command names    mon_*, vpr_*, tq_*, lk_* (namespaced)   clear
  Plugin filename          OverseerEventBridge.esp                unique
  Mod namespace            pip_montestlab (TestLab only)          unique
  Script properties        declared only on PIP-MON's own script  clear
  Config file names        vprobe_settings.jsonc,                 ours
                           overseer_rules.jsonc
  Third-party configs      we read NONE                            clear
  FormIDs                  assigned by the CK, never hand-picked   clear

If PIP-MON is ever extended with a script that touches a shared form, that form
MUST get a PIP-MON-prefixed property. Never a bare name.


--------------------------------------------------------------------------------
6. THE ROAD TO F4SE-INDEPENDENCE
--------------------------------------------------------------------------------

Not scheduled. Recorded so it is not rediscovered later, and so the sequencing
is deliberate rather than accidental.

  phase A - dual-load (keep F4SE working, add a second entry path)
      * Retain the F4SE export. Costs nothing, breaks nothing.
      * Add a standalone bootstrap so vprobe.dll loads with no extender present.
      * Gate every extender-typed call behind #if FO4MON_HAS_F4SE so the DLL
        builds and runs either way.

  phase B - own plugin loading
      * Load .esp/.esl/.esm ourselves, apply our own load order.
      * Own the Papyrus script host: compile, register, invoke, and instrument
        scripts without delegating to an extender.

  phase C - own command + script API
      * Console commands, script properties, and custom events registered by
        PIP-MON, replacing the extender's equivalents.

  phase D - extender no longer required
      * A user installs PIP-MON and needs nothing else to get papyrus
        instrumentation, a script console, and script management.

Each phase is independently shippable. None of them require rewriting what
already exists -- vprobe's telemetry pipeline survives all four unchanged,
because it was built to Rule 4: it reports facts and never depends on who
installed it.


--------------------------------------------------------------------------------
7. HOW TO CHECK A NEW FEATURE AGAINST THIS DOCUMENT
--------------------------------------------------------------------------------

  Q: Does this add a dependency on F4SE, GoE, PAP, CommonLibF4, or AddressLib?
     If yes, it needs an explicit justification recorded here. "It was already
     imported" is not a justification.

  Q: Could this be implemented from the game and the file formats alone?
     If yes, do that. The answer is almost always yes.

  Q: Does this make PIP-MON harder to remove from?
     Extensibility that only works through someone else's host is a
     replacement in name only.

  Q: Would a user who has never heard of F4SE be able to use this feature?
     That user is the target.
