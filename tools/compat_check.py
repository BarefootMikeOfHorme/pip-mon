"""Compatibility forwarder: answer "I need F4SE, what do you provide?"

Mods declare F4SE, and sometimes AddressLib, as a hard dependency. This tool
answers the only question that matters to someone reading one: does PIP-MON
cover what this thing needs, plan to, or will never cover.

It deliberately does NOT impersonate F4SE. Writing something that answers to
F4SE's identity would make mods pass a version gate and then call a function we
do not have, which converts an honest "no" into a load-time crash. That is a
worse outcome for a modder than a clean refusal, and it is the reason this is a
reporter rather than a shim. If an actual interop shim is ever wanted, it is a
deliberate decision with a decision record, not a default.

The map is data, not code: ai_context/spec/compat_f4se_map.json, with a status
from a CLOSED vocabulary so this can branch on coverage rather than read prose.

    python tools/compat_check.py                     # summary by status
    python tools/compat_check.py --status COVERED    # what actually works
    python tools/compat_check.py --need "event"      # what covers a topic
    python tools/compat_check.py --load-order        # check a real plugins.txt
    python tools/compat_check.py --json
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "ai_context" / "spec" / "compat_f4se_map.json"
DEFAULT_PLUGINS = Path(os.environ.get("LOCALAPPDATA", "")) / "Fallout4" / "Plugins.txt" \
    if (Path(os.environ.get("LOCALAPPDATA", "")) / "Fallout4" / "Plugins.txt").exists() \
    else None

# Things whose presence in a load order signals an F4SE-era dependency. This is
# a heuristic about INSTALLATION shape, not a claim about any one mod's code.
F4SE_MARKERS = ["f4se.esp", "f4se.tres", "f4se_version_major.ini", "f4se_version_minor.ini"]


def load_map():
    if not SPEC.exists():
        return None
    return json.loads(SPEC.read_text(encoding="utf-8"))


def status_order(m):
    order = ["COVERED", "DECLARED", "PLANNED", "DIFFERENT_MECHANISM",
             "NOT_PLANNED", "REJECTED"]
    return {s: i for i, s in enumerate(order)}


def summarise(m):
    counts = {}
    for e in m["entries"]:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    return counts


def check_load_order(m, plugins):
    """Report F4SE-era markers in the active load order against our coverage."""
    if not plugins or not plugins.exists():
        return {"status": "SKIP", "reason": "no plugins.txt found", "plugins": None}
    active = [ln.strip() for ln in plugins.read_text(encoding="utf-8", errors="replace").splitlines()
              if ln.strip() and not ln.strip().startswith("#")]
    present = [a for a in active if a.lower() in F4SE_MARKERS]
    counts = summarise(m)
    proven = [e for e in m["entries"] if e["status"] == "COVERED"]
    return {
        "status": "RED" if present else "GREEN",
        "plugins": str(plugins),
        "active_count": len(active),
        "f4se_markers_present": present,
        "coverage": counts,
        "proven_capabilities": [e["name"] for e in proven],
        "reason": ("%d F4SE marker(s) active: %s" % (len(present), ", ".join(present)))
        if present else
        ("no F4SE marker in the active load order; %d of %d mapped capabilities are "
         "actually proven, so treat any F4SE-era requirement as unmet"
         % (len(proven), len(m["entries"]))),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status")
    ap.add_argument("--need")
    ap.add_argument("--load-order", action="store_true")
    ap.add_argument("--plugins")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    m = load_map()
    if m is None:
        print("compat_check: no map at %s" % SPEC, file=sys.stderr)
        return 2

    if args.load_order:
        p = Path(args.plugins) if args.plugins else DEFAULT_PLUGINS
        out = check_load_order(m, p)
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print("load order: %s" % (out.get("plugins") or "(not found)"))
            print("  active plugins      : %s" % out.get("active_count"))
            print("  F4SE markers active : %s" % (", ".join(out["f4se_markers_present"]) or "none"))
            print("  proven capabilities : %d of %d" % (len(out["proven_capabilities"]), len(m["entries"])))
            print("  %s" % out["reason"])
        return 0 if out["status"] == "GREEN" else 1

    entries = m["entries"]
    if args.status:
        want = args.status.upper()
        entries = [e for e in entries if e["status"] == want]
    if args.need:
        rx = re.compile(args.need, re.I)
        entries = [e for e in entries
                   if rx.search(e["name"]) or rx.search(e.get("our_equivalent", ""))
                   or rx.search(e.get("mod_uses", ""))]

    counts = summarise(m)
    if args.json:
        print(json.dumps({"counts": counts, "entries": entries}, indent=2))
        return 0

    print("F4SE / AddressLib compatibility -- PIP-MON")
    print("  " + "  ".join("%s=%d" % (k, v) for k, v in sorted(
        counts.items(), key=lambda kv: status_order(m).get(kv[0], 99))))
    print("  PROVEN means it works today. DECLARED means the surface exists but no "
          "handler is proven.\n")
    for e in sorted(entries, key=lambda e: status_order(m).get(e["status"], 99)):
        print("  [%-18s] %s" % (e["status"], e["name"]))
        print("      theirs : %s" % e["source_product"])
        print("      ours   : %s" % e.get("our_equivalent", "none"))
        if e.get("mod_uses"):
            print("      mods use: %s" % e["mod_uses"])
        if e.get("notes"):
            print("      note   : %s" % e["notes"])
    if not entries:
        print("  (no entries matched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
