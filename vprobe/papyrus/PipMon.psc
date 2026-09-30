; ===========================================================================
;  PipMon.psc -- the PIP-MON Papyrus API surface (Layer B, as the script sees
;  it).
;
;  Companion to vprobe/src/PapyrusApi.cpp. The two MUST agree, and the
;  self-test asserts it in both directions: every function declared here has a
;  matching row in the native table, and every row in the table is declared
;  here. A surface that exists only in C++ is invisible to a mod author; one
;  that exists only in Papyrus calls into nothing.
;
;  WHY EVERY FUNCTION IS `Native Global`
;    Native  -- we supply the implementation; the VM resolves it to our
;               registered handler (Layer A). No body, by design.
;    Global  -- callable as PipMon:GetVersion() from anywhere, with no script
;               instance. This is the "API class" pattern (the same one F4SE
;               uses for its F4SE/UI scripts), and it is what makes the surface
;               usable from a quest, a dialogue script, or the console.
;
;  NAMESPACE
;    ScriptName PipMon -- the "PipMon" the VM matches on, held as a constant
;    (kNamespace) in PapyrusApi.hpp. It is a registration key, not a label;
;    a typo here does not warn, it produces a script that calls into nothing.
;    We register into our OWN class and never extend a vanilla type -- see
;    section 24.4. Not System:, not Form, not Actor. That is why this coexists
;    with every other extender instead of competing with them.
;
;  BUILD STATE
;    Functions marked [S0] have a real handler today. Everything else is
;    declared-but-inert: present so the full surface is visible and testable
;    from day one, but invokeNative() refuses them cleanly until their
;    marshaling is proven. See design section 24.3 (stages) / 24.6 (surface).
;
;  NAME CONVENTIONS (section 23)
;    Namespace is PascalCase; functions are PascalCase; parameters use
;    Bethesda's Hungarian prefixes (ai=int, af=float, ab=bool, as=string,
;    aa=array). Our own ESPs are lowercase pip-mon.*.esp -- unrelated to
;    this file's naming, which follows Papyrus's own rules.
; ===========================================================================

;  The script itself is flagged Native. This is REQUIRED: a Papyrus function may
;    only be declared Native if the containing script is also flagged Native, or
;    the compiler rejects every one of them with "cannot be defined as native
;    because the script is not flagged as native". The `Native` on the
;    ScriptName line is what tells the VM to resolve these functions against our
;    registered handlers (Layer A) rather than looking for a body.
ScriptName PipMon Native

; --- STATUS / HEALTH -- the S0 surface --------------------------------------

; [S0] ABI version of this registered surface. The script's handle on which
; build it is talking to; bump-gate callers can refuse cleanly.
Int Function GetVersion() Global Native

; [S0] Capability bitfield (PipmonEntry.hpp PipmonCapability). Lets a script
; ask for a capability and get a clean "not here" instead of silence.
; Currently the same mask as GetCapabilities; expected to split later.
Int Function GetRuntimeStatus() Global Native

; [S0] Feature negotiation mask, same source as the loader's PIPMON_Query.
Int Function GetCapabilities() Global Native

; --- S1 MARSHALING PROBES -- declared, not yet built -----------------------
; These exist to answer one question before the rest of the surface is built
; on an assumption: can a non-int value cross into Papyrus at all? If S1 fails,
; the surface narrows and these two are the canaries.

String Function GetStringTest() Global Native
String[] Function GetStringArrayTest() Global Native

; --- PROBE / RESOLVER INTROSPECTION -----------------------------------------
; Report which probes resolved and HOW (Tier-1 AddressLib, Tier-2 vtable,
; Tier-3 AOB), so a triage tool can explain itself.

Int Function GetResolvedProbeCount() Global Native
String[] Function GetResolvedProbes() Global Native
Bool Function IsHookLive(Int aiProbeId) Global Native

; --- SAVE TRIAGE -------------------------------------------------------------
; Adjudication of a save: the verdict and the basis for it (section 20).

Int Function GetAdjudicationCount() Global Native

; --- EVENTS (S2 poll, then S3 push) -----------------------------------------
; A fixed poll queue first; external/named push rides on top of it later.

Int Function RegisterForEvents(Int aiMask) Global Native
Bool Function UnregisterFromEvents(Int aiToken) Global Native

; --- LIBRARY / INVENTORY ----------------------------------------------------

Int Function GetLibraryCount() Global Native
String[] Function GetLibraryInventory() Global Native
