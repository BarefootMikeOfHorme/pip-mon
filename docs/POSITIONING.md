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

F4SE is a HARD RUNTIME DEPENDENCY TODAY, and that is a known gap.

  * vprobe.dll exports F4SEAPI_MakePluginInfo and is loaded by F4SE from
    Data/F4SE/Plugins/. With no F4SE, it does not run.
  * Garden of Eden and PAP are referenced NOWHERE in the codebase. No code, no
    config parsing, no asset reuse. They exist in this project only as
    documented inspiration.
  * CommonLibF4 and AddressLib appear in vprobe/CMakeLists.txt as OPTIONAL
    FetchContent entries. The current sources are self-contained and link
    neither. The relocation-INI *concept* is borrowed; the code is not used.

F4SE is retained FOR TESTING because it is the only way to load a plugin into
the game today. It is scaffolding, not architecture. See section 6.


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
