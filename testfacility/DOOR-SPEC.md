# DOOR-SPEC — Paradise → Bunker, a load-door pair

**Status:** designed, not built. Blocked on one inventory (see §5).
**Why written now:** the coupling is easy to get subtly wrong, and "it didn't
work" in an interior/exterior link is indistinguishable from "the mod is broken".

---

## 1. What is actually being built

A **load door pair**: one door in the outside cell (Paradise) and one in the
interior cell (the bunker), cross-referenced to each other. Walking into the
outside door loads the interior cell and places the player at the inside door.
Because it is a *load* door, the exterior cell is unloaded while the player is
inside — which is the whole point of doing it this way rather than with two
doors and a teleport trigger.

```
   PARADISE (exterior)                        BUNKER (interior cell)
   ┌──────────────────────┐                  ┌──────────────────────┐
   │  DOOR  "ParadiseTo-  │  ── XTEL ──────▶ │  DOOR  "BunkerInside" │
   │  Bunker"  (outside)  │                  │  (inside)            │
   │  XFLR: load bit set  │                  │  XFLR: load bit set  │
   │  XTEL → inside door  │ ◀── XTEL ─────── │  XTEL → outside door │
   └──────────────────────┘                  └──────────────────────┘
```

Both directions carry a link. A one-way link loads the cell and then drops the
player at nothing, or at the wrong end.

## 1b. What a load door actually IS

A load door is a **location-change request with a door on the front**. That is
not a figure of speech: it asks the engine for the same "put the player over
there" transition that fast travel asks for, differing only in that the request
is triggered by geometry the player walks into rather than by a menu choice.
Fast travel points are, in effect, doors that are never rendered and can only be
chosen from a list. That is why both appear to "load" something.

The practical consequence is an **options ladder**, cheapest first:

| Option | What you author | Cost | Good enough for |
|---|---|---|---|
| console `coc <cellEditorID>` | nothing at all | free | the S0 experiment |
| a fast travel destination | one marker, no link pair | low | **worldspace** destinations |
| a load door pair | two doors + two links + flag semantics | high | **interior** cells |

The catch, and the reason the door exists at all, is that interiors are not
fast travel destinations in this engine — you cannot fast travel *into* a room.
That claim is the kind that must be checked rather than believed, and it is
checkable: vanilla ships load doors into every interior (Vault 111, any
premade), so if fast travel could target interiors the door pair would be
redundant. **Verification step, once xEdit runs:** read one vanilla load door's
`XFLR`/`XTEL` and confirm the flag bit that distinguishes "load" from "slide" —
that flag is the entire difference, and reading it off a shipped door is cheaper
and safer than inferring it from documentation.

So: for the *experiment*, `coc` is free and sufficient. For *content*, the door
pair is the only native route into an interior, and the work above is the price
of that.

## 2. Who owns which end — the decision that matters

**We place BOTH doors.** Not one door linking into the bunker mod's existing
entrance.

Reasons, in order of weight:

1. **FormIDs move.** This install has 200+ mods and Vortex; the bunker's
   entrance door FormID is a fact about *today's* load order. A hardcoded link
   to it breaks silently the first time a mod shifts that record, and the
   symptom is a door that opens onto nothing.
2. **We cannot verify it without the inventory we do not yet have** (§5).
3. **An override inside someone else's cell is unavoidable either way** — we
   must place our door *somewhere* in their space — so owning both ends costs
   no extra coupling and removes one.

Consequence: our plugin references the bunker cell (to place a door in it) and
the Paradise cell (to place the outside door), so `Cotozic's Bunker Ravine.esp`
and `theparadiseproject.esp` become **masters** of `PipMonTestFacility.esp`.
Both are already installed and enabled; the CK adds the master entries itself.

## 3. What each record needs

| Record | Needs | Notes |
|---|---|---|
| Outside door, in Paradise | a DOOR record + a placed reference in the Paradise cell + the **load** bit set + `XTEL` → the inside door | the model can be a vanilla bunker hatch or door |
| Inside door, in the bunker cell | a DOOR record + a placed reference in the bunker interior + load bit + `XTEL` → the outside door | placed by us, inside their cell |

**The load bit and the exact subrecord semantics are to be read off a vanilla
load door, not recalled.** A vanilla door that leads to an interior cell is the
ground truth for what the engine expects in `XFLR`, and which subrecord carries
the destination. That comparison is the first job once xEdit can run (§5) —
guessing at flag semantics here is precisely the failure this project keeps
paying for.

## 4. Why the door is not the first priority

For the v0 experiment — *can a compiled script reach our natives* — the door is
unnecessary. `coc PipMonFacilityCell` reaches the same cell, and Cheat Terminal
is already in the load order. The door becomes valuable when the facility is
meant to be **used like content**, which is the next stage, not this one.

Sequence, so the door never blocks the experiment:

1. cell → fixtures → script attach → properties → **S0 verdict**
2. then the door, as the first piece of "real content"
3. then Paradise/Bunker as the playable destination

## 4a. FINDINGS — 2026-09-30, from reading the plugin files directly

Searched both plugins for readable EditorID strings, without the editor and
without xEdit. A *miss* is inconclusive (records may be compressed); a *hit* is a
fact.

**`theparadiseproject.esp` (1.27 MB): no bunker door.** Its 34 door-ish strings
are all model paths — `Interiors\Vault\Doors\VltGearDoor\…`,
`Uit_SteamTBgRoomBrickDoor04`, and similar vault/steam pieces. Nothing bunker-
related, and no location named for one. **So a Paradise-side door would be
added, not reused.**

**`Cotozic's Bunker Ravine.esp` (613 KB): it already has an outside.**

```
00BunkerRavineLocation          <- interior location
00BunkerRavineLocationEXT       <- EXTERIOR location
COTOSlockedblastdoor / COTOSblastdoorlocked2
COTOSelevatordoorCLOSED / COTOSelevatordoorREF
COTOSautodoortrigger
COTOZIC\COTOHitFloorHatch01.nif  <- floor hatch
00BunkerRavineSettlementQuest
```

`…LocationEXT` is the important one: **the bunker mod already ships an exterior
entrance**, plus blast doors, a floor hatch and an auto-door trigger.

### What this changes

The premise "Paradise is the outside point" may be unnecessary. There are now
two options, and the cheaper one is not the one originally planned:

| Option | Work | Verdict |
|---|---|---|
| **A — use the bunker's own exterior entrance** | none; it already exists | **recommended** for the first playable pass |
| B — add a Paradise-side door tied to a bunker door | two doors + two links (§1–3) | a nice extra once A is proven |

Nothing here says the exterior entrance works *well* — that needs the inventory
and a walk test. But it means the door work is not on the critical path at all,
and Paradise stops being a prerequisite.

### Honest limits of this probe

- It reads **strings only**. A door record whose EditorID says nothing
  interesting is invisible here, so "no bunker door in Paradise" means "no
  bunker-*named* door", not "no usable door".
- The list above is truncated (36 further matches in the bunker plugin), and
  none of it is parsed structure. **The inventory is still the authority**, and
  these findings only tell us which question to ask it first.



| # | Blocker | Needed for | Clears when |
|---|---|---|---|
| 1 | xEdit headless unusable (first-run notice) | knowing the bunker's interior cell EditorID/FormID; reading a vanilla load door's flags | the notice is clicked through once |
| 2 | inventory of `Cotozic's Bunker Ravine.esp` | which cell is the interior, and where to put our inside door | `pipmon.ps1 validate` returns PASS with records |
| 3 | inventory of `theparadiseproject.esp` | which cell to place the outside door in | same |
| 4 | no `paradise` reference point agreed | *where* in Paradise the door goes — a wall, a fence line, a basement? | the user picks a spot |

Blocker 4 is a design question, not a technical one, and it is the only one that
needs a human decision before any work starts.

## 6. Verification, when it is built

- **Structural:** xEdit inventory shows two DOOR records, each placed in the
  right cell, each with a link pointing at the other.
- **Visual (out-of-process):** `coc` into the bunker, then walk out the inside
  door and confirm you arrive in Paradise — and back again. Two directions is
  the test; one direction proves nothing.
- **Negative:** if either door is missing its `XTEL`, the symptom is a door
  that opens onto the void. That is the failure to look for, and it is why the
  inventory check comes before the walk test.
