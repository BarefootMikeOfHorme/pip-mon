#!/usr/bin/env python3
"""
Build FO4_Papyrus_Reference.md from Papyrus .psc sources.

The reference is GENERATED, never hand-edited: point it at real script
sources and it rebuilds every table. Pass 4 of the plan is simply re-running
this against the Base .psc files that ship with YOUR Creation Kit
(<FO4>/Data/Scripts/Source/Base), so the table matches your exact runtime.

Usage:
  python gen_papyrus_ref.py -o FO4_Papyrus_Reference.md \
      --layer vanilla=PATH --layer f4se=PATH --layer baka=PATH \
      --layer mcm=PATH --layer lighthouse=PATH --layer wsfw=PATH \
      [--meta vanilla="Fallout 4 1.10.984.0"] [--meta f4se="F4SE 0.7.4"]

Layer order given on the command line is the display order. "vanilla" should
be first. Each layer is scanned recursively for *.psc.
"""
import argparse
import collections
import os
import re
import sqlite3
import sys

FUNC_RE = re.compile(
    r'^(?:(?P<ret>[A-Za-z_][\w:]*(?:\[\])?)\s+)?Function\s+(?P<name>\w+)\s*'
    r'\((?P<params>.*)\)\s*(?P<flags>.*)$', re.I)
EVENT_RE = re.compile(
    r'^Event\s+(?P<name>[\w.]+)\s*\((?P<params>.*)\)\s*(?P<flags>.*)$', re.I)
PROP_RE = re.compile(
    r'^(?P<type>[A-Za-z_][\w:]*(?:\[\])?)\s+Property\s+(?P<name>\w+)'
    r'(?:\s*=\s*(?P<default>"[^"]*"|\S+))?\s*(?P<flags>.*)$', re.I)
HEAD_RE = re.compile(
    r'^Scriptname\s+(?P<name>[\w:]+)(?:\s+extends\s+(?P<ext>[\w:]+))?\s*(?P<flags>.*)$', re.I)
RAW_FUNC_RE = re.compile(r'^\s*(?:[A-Za-z_][\w:]*(?:\[\])?\s+)?Function\s+\w+\s*\(', re.I)
RAW_EVENT_RE = re.compile(r'^\s*Event\s+[\w.]+\s*\(', re.I)

FLAG_WORDS = {'native', 'global', 'debugonly', 'betaonly', 'const'}


def strip_inline_comment(s):
    inq = False
    for i, ch in enumerate(s):
        if ch == '"':
            inq = not inq
        elif ch == ';' and not inq:
            return s[:i].rstrip()
    return s


def clean_note(parts):
    t = ' '.join(parts)
    t = re.sub(r'[{}]|;/|/;', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' ;')
    return (t[:117] + '...') if len(t) > 120 else t


def logical_lines(text):
    """Yield (code, preceding_comment). Blank lines break comment adjacency."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\\[ \t]*\n', ' ', text)  # line continuation
    pending = []
    block = None
    for raw in text.split('\n'):
        s = raw.strip()
        if block == 'semi':
            pending.append(s)
            if '/;' in s:
                block = None
            continue
        if block == 'brace':
            pending.append(s)
            if '}' in s:
                block = None
            continue
        if s.startswith(';/'):
            pending.append(s)
            if '/;' not in s[2:]:
                block = 'semi'
            continue
        if s.startswith('{'):
            pending.append(s)
            if '}' not in s:
                block = 'brace'
            continue
        if s.startswith(';'):
            pending.append(s.lstrip('; '))
            continue
        if not s:
            pending = []
            continue
        code = strip_inline_comment(s)
        if code:
            yield code, clean_note(pending)
        pending = []


def split_params(p):
    out, cur, inq = [], '', False
    for ch in p:
        if ch == '"':
            inq = not inq
        if ch == ',' and not inq:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def flags_of(s):
    return sorted({w.lower() for w in s.split() if w.lower() in FLAG_WORDS})


def parse_file(path, layer):
    text = open(path, encoding='utf-8-sig', errors='replace').read()
    raw_f = sum(1 for l in text.splitlines() if RAW_FUNC_RE.match(l.split(';')[0]))
    raw_e = sum(1 for l in text.splitlines() if RAW_EVENT_RE.match(l.split(';')[0]))
    sc = {'layer': layer, 'path': path, 'name': None, 'extends': None, 'flags': [],
          'funcs': [], 'events': [], 'props': [], 'custom': [], 'structs': [],
          'raw_f': raw_f, 'raw_e': raw_e}
    in_prop = in_struct = False
    for code, note in logical_lines(text):
        low = code.lower()
        if in_struct:
            if low.startswith('endstruct'):
                in_struct = False
            continue
        if in_prop:
            if low.startswith('endproperty'):
                in_prop = False
            continue
        m = HEAD_RE.match(code)
        if m and not sc['name']:
            sc['name'] = m.group('name')
            sc['extends'] = m.group('ext')
            sc['flags'] = [w for w in m.group('flags').split() if w]
            continue
        if low.startswith('struct '):
            sc['structs'].append(code.split()[1])
            in_struct = True
            continue
        if low.startswith('customevent '):
            sc['custom'].append(code.split()[1])
            continue
        m = PROP_RE.match(code)
        if m:
            fl = m.group('flags').strip()
            sc['props'].append((m.group('type'), m.group('name'), m.group('default') or '', fl))
            if 'auto' not in fl.lower():
                in_prop = True
            continue
        m = EVENT_RE.match(code)
        if m:
            sc['events'].append({'name': m.group('name'), 'params': split_params(m.group('params')),
                                 'flags': flags_of(m.group('flags')), 'note': note})
            continue
        m = FUNC_RE.match(code)
        if m:
            sc['funcs'].append({'name': m.group('name'), 'ret': m.group('ret') or '',
                                'params': split_params(m.group('params')),
                                'flags': flags_of(m.group('flags')), 'note': note})
    if not sc['name']:
        sc['name'] = os.path.splitext(os.path.basename(path))[0]
    return sc



NOISE_RE = ('BSScript', 'BSFixedString', 'BSTSmartPointer', 'GameScript', 'BSAutoReadLock',
            'BSAutoWriteLock', 'BSTArray', 'BSStringT', 'BSTObjectArray')


def rag_lines(conn, path):
    d = {}
    for st, _e, t in conn.execute('select start_line,end_line,text from chunks where path=? order by idx', (path,)):
        for i, l in enumerate(t.split('\n')):
            d.setdefault(st + i, l)
    return '\n'.join(d[k] for k in sorted(d))


def match_close(txt, i, open_c, close_c):
    depth, inq, n = 0, False, len(txt)
    while i < n:
        ch = txt[i]
        if ch == '"' and txt[i - 1] != '\\':
            inq = not inq
        elif not inq:
            if ch == open_c:
                depth += 1
            elif ch == close_c:
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def split_cpp_params(p):
    out, cur, depth, inq = [], '', 0, False
    for ch in p:
        if ch == '"':
            inq = not inq
        if not inq:
            if ch in '<(':
                depth += 1
            elif ch in '>)':
                depth -= 1
            if ch == ',' and depth == 0:
                out.append(cur.strip())
                cur = ''
                continue
        cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def parse_cpp_defs(txt):
    defs = {}
    for m in re.finditer(r'\binline\s+([^;{}()]*?)\b(\w+)\s*\(', txt):
        name = m.group(2)
        if name in defs or name == 'Bind':
            continue
        po = m.end() - 1
        pc = match_close(txt, po, '(', ')')
        if pc < 0:
            continue
        j = pc + 1
        while j < len(txt) and txt[j] in ' \t\r\n':
            j += 1
        if txt.startswith('noexcept', j):
            j += 8
            while j < len(txt) and txt[j] in ' \t\r\n':
                j += 1
        if j >= len(txt) or txt[j] != '{':
            continue
        bc = match_close(txt, j, '{', '}')
        if bc < 0:
            continue
        ret = re.sub(r'\[\[nodiscard\]\]', '', m.group(1)).strip()
        params = split_cpp_params(txt[po + 1:pc])
        defs[name] = {'ret': ret, 'params': params, 'body': txt[j + 1:bc]}
    return defs


def cpp_param_type(p):
    p = re.sub(r'\[\[[^\]]*\]\]', '', p).strip()
    p = re.sub(r'\bconst\b', '', p).strip()
    m = re.match(r'^(.*?)\s*[&*]*\s*\b\w+$', p)
    t = m.group(1) if m and m.group(1) else p
    return re.sub(r'\s+', ' ', t).strip()


def engine_types(txt):
    c = collections.Counter()
    for t in re.findall(r'\bRE::([A-Za-z_]\w*)', txt):
        if t in NOISE_RE:
            continue
        c[t] += 1
    return [t for t, _ in c.most_common(8)]


def collect_binds(conn, prefix):
    rows = []
    paths = [p for (p,) in conn.execute("select path from files where path like ? and path like '%.h' order by path", (prefix + '%',))]
    for path in paths:
        txt = rag_lines(conn, path)
        om = re.search(r'const auto obj = "([^"]+)"sv', txt)
        if not om:
            continue
        obj = om.group(1)
        defs = parse_cpp_defs(txt)
        for m in re.finditer(r'\bBIND\((\w+)(?:,\s*(\w+))?\)', txt):
            fn, tl = m.group(1), m.group(2)
            d = defs.get(fn)
            row = {'script': obj, 'func': fn, 'tasklet': tl == 'true', 'file': path.rsplit('/', 1)[-1], 'found': d is not None}
            if d:
                params = d['params']
                # delayed-functor bindings take (vm, stackID) before self; they are plumbing, not Papyrus arguments
                core = list(params)
                while core and ('IVirtualMachine' in core[0] or re.search(r'\ba_stackID\b', core[0])):
                    core.pop(0)
                is_global = bool(core) and 'monostate' in core[0]
                nargs = len(core) - 1  # drop self or monostate
                body = re.sub(r'\s+', ' ', d['body']).strip()
                allunused = bool(params) and all('maybe_unused' in q for q in params)
                row.update({'global': is_global, 'cpp_arity': nargs,
                            'cpp_params': ', '.join(cpp_param_type(q) for q in core[1:]),
                            'stub': allunused and body.count(';') <= 1,
                            'engine': engine_types(d['ret'] + ' ' + ' '.join(params) + ' ' + d['body'])})
            rows.append(row)
    return rows


def esc(s):
    return s.replace('|', '\\|')


def sig_params(ps):
    return esc(', '.join(ps)) if ps else ''


def base_type(t):
    return t.replace('[]', '') if t else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--layer', action='append', required=True, help='name=dir')
    ap.add_argument('--meta', action='append', default=[], help='name=free text')
    ap.add_argument('--rag', help='index.sqlite3 holding the F4SE/CommonLibF4 sources (enables Pass 3a)')
    ap.add_argument('--rag-prefix', default='third_party/CommonLibF4/F4SEStub/runtime/src/Papyrus/',
                    help='path prefix of the Papyrus binding headers inside the index')
    a = ap.parse_args()
    meta = dict(m.split('=', 1) for m in a.meta)
    layers = [tuple(l.split('=', 1)) for l in a.layer]

    scripts = []
    for lname, ldir in layers:
        for root, _, files in os.walk(ldir):
            for f in sorted(files):
                if f.lower().endswith('.psc'):
                    scripts.append(parse_file(os.path.join(root, f), lname))

    # merge by script name (F4SE re-declares vanilla scripts with additions)
    merged = collections.OrderedDict()
    for s in scripts:
        key = s['name'].lower()
        m = merged.setdefault(key, {'name': s['name'], 'extends': None, 'flags': [], 'layers': [],
                                    'funcs': [], 'events': [], 'props': [], 'custom': [],
                                    'structs': []})
        if s['extends'] and not m['extends']:
            m['extends'] = s['extends']
        if s['flags'] and not m['flags']:
            m['flags'] = s['flags']
        if s['layer'] not in m['layers']:
            m['layers'].append(s['layer'])
        # The F4SE SDK ships whole copies of vanilla scripts plus additions, so the
        # same declaration can appear in two layers. Keep the first (lowest) layer.
        seen = m.setdefault('seen', set())

        def ptypes(ps):
            return tuple((q.split()[0].lower() if q.split() else '') for q in ps)

        for f in s['funcs']:
            k = ('f', f['name'].lower(), ptypes(f['params']))
            if k in seen:
                continue
            seen.add(k)
            f['layer'] = s['layer']
            m['funcs'].append(f)
        for e in s['events']:
            k = ('e', e['name'].lower(), ptypes(e['params']))
            if k in seen:
                continue
            seen.add(k)
            e['layer'] = s['layer']
            m['events'].append(e)
        for p in s['props']:
            k = ('p', p[1].lower())
            if k in seen:
                continue
            seen.add(k)
            m['props'].append(p + (s['layer'],))
        m['custom'] += s['custom']
        m['structs'] += s['structs']

    # ---------- stats ----------
    by_layer = collections.OrderedDict((l, {'scripts': 0, 'funcs': 0, 'events': 0, 'props': 0,
                                            'raw_f': 0, 'raw_e': 0}) for l, _ in layers)
    for s in scripts:
        b = by_layer[s['layer']]
        b['scripts'] += 1
        b['funcs'] += len(s['funcs'])
        b['events'] += len(s['events'])
        b['props'] += len(s['props'])
        b['raw_f'] += s['raw_f']
        b['raw_e'] += s['raw_e']

    uniq = collections.OrderedDict((l, {'funcs': 0, 'events': 0, 'props': 0}) for l, _ in layers)
    for m in merged.values():
        for f in m['funcs']:
            uniq[f['layer']]['funcs'] += 1
        for e in m['events']:
            uniq[e['layer']]['events'] += 1
        for p in m['props']:
            uniq[p[-1]]['props'] += 1
    allnames = {m['name'].lower(): m['name'] for m in merged.values()}
    flat = []  # (script, kind, rec)
    for m in merged.values():
        for f in m['funcs']:
            flat.append((m['name'], 'F', f))
        for e in m['events']:
            flat.append((m['name'], 'E', e))

    L = []
    w = L.append
    w('# Fallout 4 Papyrus Reference (Creation Engine scripting surface)')
    w('')
    w('Generated by `gen_papyrus_ref.py` from real `.psc` sources. Do not hand-edit: change the sources or the generator and rebuild.')
    w('')
    w('## Plan: passes from minimal to robust')
    w('')
    w('| Pass | Scope | Status |')
    w('|---|---|---|')
    w('| 1 | Complete inventory of every script, function, event and property, with signatures and flags; extends tree; mechanical cross-references (who returns a type, event to register pairing) | Done |')
    w('| 2 | Behavior notes per function: latent or not, threading and save-state effects, known gotchas (from CK wiki, cited) | Not started |')
    w('| 3a | Top-down trace: Papyrus function to native binding to C++ function to engine types (CommonLibF4 sources in your RAG); coverage gaps and stubs | Done if the Pass 3a section is present (needs `--rag`) |')
    w('| 3b | Bottom-up: engine events to Papyrus events, CK surfaces (properties, fragments, terminals), console path | Not started |')
    w('| 4 | Verify: rebuild this file from your own `Data/Scripts/Source/Base`, diff against this one, then compile-test your PipMon scripts against it | Not started |')
    w('')
    w('## Sources and caveats')
    w('')
    w('| Layer | What it is | Source note |')
    w('|---|---|---|')
    desc = {'vanilla': 'Base game scripts', 'f4se': 'Fallout 4 Script Extender additions (needs F4SE at runtime)',
            'baka': 'BakaFramework utility scripts (third party)', 'mcm': 'Mod Configuration Menu API (third party)',
            'lighthouse': 'Lighthouse (third party)', 'wsfw': 'Workshop Framework (third party)'}
    for l, d in layers:
        w(f'| `{l}` | {desc.get(l, "")} | {esc(meta.get(l, d))} |')
    w('')
    w('- Everything outside `vanilla` is **not part of the base game**: a function marked `f4se` fails at runtime if F4SE is not loaded.')
    w('- Signatures come from source, so they are exact. Descriptions are the source comments where one exists; absence of a note means the source had none.')
    w('- A signature is not proof of runtime behavior. Behavior is Pass 2; proof against your build is Pass 4.')
    w('')
    w('### Parser self-check (raw declaration count vs parsed)')
    w('')
    w('| Layer | Scripts | Functions parsed / raw | Events parsed / raw | Properties |')
    w('|---|---:|---:|---:|---:|')
    ok = True
    for l, b in by_layer.items():
        flag = '' if (b['funcs'] <= b['raw_f'] and b['events'] <= b['raw_e']) else ' (check)'
        w(f'| {l} | {b["scripts"]} | {b["funcs"]} / {b["raw_f"]}{flag} | {b["events"]} / {b["raw_e"]} | {b["props"]} |')
    w('')
    w('Parsed counts are lower than raw only where a declaration sits inside a property body (Get/Set) or struct, which are not callable members.')
    w('')
    w('### Unique members after de-duplication')
    w('')
    w('The F4SE SDK ships whole copies of vanilla scripts plus its additions, so the same declaration appears in two layers. Each member is kept once, credited to the lowest layer that declares it. The `f4se` row below is therefore the true set of F4SE additions.')
    w('')
    w('| Layer | Unique functions | Unique events | Unique properties |')
    w('|---|---:|---:|---:|')
    for l, b in uniq.items():
        w(f'| {l} | {b["funcs"]} | {b["events"]} | {b["props"]} |')
    w(f'| **total** | **{sum(b["funcs"] for b in uniq.values())}** | **{sum(b["events"] for b in uniq.values())}** | **{sum(b["props"] for b in uniq.values())}** |')
    w('')

    w('## Call forms (what the "little funny words" look like)')
    w('')
    w('| Form | Example |')
    w('|---|---|')
    w('| Global function (dot-qualified by script) | `Debug.Notification("Hi")`, `Utility.Wait(1.0)`, `Game.GetPlayer()` |')
    w('| Member function (on an object) | `akRef.MoveTo(akTarget)` |')
    w('| Function in own script | `DoThing()` or `Self.DoThing()` |')
    w('| Parent version | `Parent.OnInit()` |')
    w('| Cast and test | `akRef as Actor`, `akRef is Actor` |')
    w('| Event handler (declared, not called) | `Event OnActivate(ObjectReference akActionRef) ... EndEvent` |')
    w('| Register for an event | `RegisterForRemoteEvent(akQuest, "OnStageSet")` then `Event Quest.OnStageSet(...)` |')
    w('| Timer (Fallout 4 uses timers, not Skyrim-style update registration) | `StartTimer(5.0, 1)` then `Event OnTimer(int aiTimerID)` |')
    w('')
    w('Functions always take parentheses. `Debug.Notification "text"` is not valid; it must be `Debug.Notification("text")`.')
    w('')

    # ---------- extends tree ----------
    w('## Script hierarchy (extends)')
    w('')
    children = collections.defaultdict(list)
    roots = []
    for m in merged.values():
        e = (m['extends'] or '').lower()
        if e and e in merged:
            children[e].append(m['name'])
        else:
            roots.append(m['name'])

    def tree(n, depth, out):
        out.append('  ' * depth + f'- {n}')
        for c in sorted(children.get(n.lower(), []), key=str.lower):
            tree(c, depth + 1, out)

    tl = []
    for r in sorted(roots, key=str.lower):
        tree(r, 0, tl)
    # collapse very wide siblings for readability: keep full tree, it is the reference
    L += tl
    w('')

    # ---------- per-script sections ----------
    w('## Script index')
    w('')
    w('| Script | Extends | Layers | Functions | Events | Properties | Flags |')
    w('|---|---|---|---:|---:|---:|---|')
    for m in sorted(merged.values(), key=lambda x: x['name'].lower()):
        w(f'| [{m["name"]}](#{re.sub(r"[^a-z0-9]+", "-", m["name"].lower()).strip("-")}) | {m["extends"] or ""} | {", ".join(m["layers"])} | '
          f'{len(m["funcs"])} | {len(m["events"])} | {len(m["props"])} | {" ".join(m["flags"])} |')
    w('')

    w('## Scripts')
    w('')
    for m in sorted(merged.values(), key=lambda x: x['name'].lower()):
        w(f'### {m["name"]}')
        w('')
        chain = []
        cur = m
        seen = set()
        while cur and cur['extends'] and cur['extends'].lower() not in seen:
            seen.add(cur['extends'].lower())
            chain.append(cur['extends'])
            cur = merged.get(cur['extends'].lower())
        w(f'Extends: {" > ".join(chain) if chain else "(none)"} | Layers: {", ".join(m["layers"])} | Flags: {" ".join(m["flags"]) or "-"}')
        w('')
        if m['funcs']:
            w('| Function | Returns | Parameters | Flags | Layer | Note |')
            w('|---|---|---|---|---|---|')
            for f in sorted(m['funcs'], key=lambda x: x['name'].lower()):
                w(f'| `{f["name"]}` | {f["ret"] or "-"} | {sig_params(f["params"])} | {" ".join(f["flags"])} | {f["layer"]} | {esc(f["note"])} |')
            w('')
        if m['events']:
            w('| Event | Parameters | Flags | Layer | Note |')
            w('|---|---|---|---|---|')
            for e in sorted(m['events'], key=lambda x: x['name'].lower()):
                w(f'| `{e["name"]}` | {sig_params(e["params"])} | {" ".join(e["flags"])} | {e["layer"]} | {esc(e["note"])} |')
            w('')
        if m['props']:
            w('| Property | Type | Default | Flags | Layer |')
            w('|---|---|---|---|---|')
            for t, n, d, fl, lay in m['props']:
                w(f'| `{n}` | {t} | {esc(d)} | {esc(fl)} | {lay} |')
            w('')
        extra = []
        if m['custom']:
            extra.append('Custom events: ' + ', '.join(m['custom']))
        if m['structs']:
            extra.append('Structs: ' + ', '.join(m['structs']))
        if extra:
            w(' | '.join(extra))
            w('')

    # ---------- correlations ----------
    w('## Cross-reference A: registering for events')
    w('')
    w('Registration functions paired to the event they deliver, matched by name (`RegisterForX` to `OnX`). Unmatched registrars are listed after the table; they take the event name as an argument or use another naming scheme.')
    w('')
    ev_decl = collections.defaultdict(list)
    for s, k, r in flat:
        if k == 'E':
            ev_decl[r['name'].lower()].append(s)
    regs = [(s, r) for s, k, r in flat if k == 'F' and r['name'].lower().startswith('registerfor')]
    unregs = {(s, r['name'].lower()) for s, k, r in flat if k == 'F' and r['name'].lower().startswith('unregisterfor')}
    paired, unpaired = [], []
    special = {'singleupdate': 'update', 'update': 'update', 'singleupdategametime': 'updategametime',
               'updategametime': 'updategametime'}
    for s, r in regs:
        suffix = r['name'][len('RegisterFor'):]
        key = special.get(suffix.lower(), suffix.lower())
        cand = 'on' + key
        if cand in ev_decl:
            paired.append((suffix, s, r, cand))
        else:
            unpaired.append((s, r))
    w('| Register function | In | Parameters | Delivers event | Event declared in | Unregister |')
    w('|---|---|---|---|---|---|')
    for suffix, s, r, cand in sorted(paired, key=lambda x: x[0].lower()):
        un = 'UnregisterFor' + suffix
        has_un = any(u[1] == un.lower() for u in unregs)
        evname = next(e['name'] for sc2, k, e in flat if k == 'E' and e['name'].lower() == cand)
        w(f'| `{r["name"]}` | {s} | {sig_params(r["params"])} | `{evname}` | {", ".join(sorted(set(ev_decl[cand])))} | {"yes" if has_un else "-"} |')
    w('')
    fnames = {(sc, r['name']) for sc, k, r in flat if k == 'F'}
    timer_rows = [('StartTimer', 'OnTimer', 'CancelTimer'), ('StartTimerGameTime', 'OnTimerGameTime', 'CancelTimerGameTime')]
    have = [t for t in timer_rows if any(n == t[0] for _, n in fnames)]
    if have:
        w('Timers are started and cancelled rather than registered. Fallout 4 has no `RegisterForSingleUpdate` / `OnUpdate`; use these instead:')
        w('')
        w('| Start | Delivers event | Cancel | Declared in |')
        w('|---|---|---|---|')
        for st, ev, ca in have:
            where = ', '.join(sorted({sc for sc, n in fnames if n == st}))
            w(f'| `{st}` | `{ev}` | `{ca}` | {where} |')
        w('')
    if unpaired:
        w('Registrars with no same-named event: ' + ', '.join(f'`{s}.{r["name"]}`' for s, r in sorted(unpaired, key=lambda x: x[1]['name'].lower())))
        w('')

    w('## Cross-reference B: how to get an object of a type (producers)')
    w('')
    w('For each script type, the functions that return it (or an array of it). "Takes it" counts functions that accept the type as a parameter. Inherited producers are not expanded: a function returning `Actor` is not listed under `ObjectReference`.')
    w('')
    prod = collections.defaultdict(list)
    cons = collections.Counter()
    for s, k, r in flat:
        if k != 'F':
            continue
        bt = base_type(r['ret'])
        if bt.lower() in allnames:
            prod[allnames[bt.lower()]].append(f'{s}.{r["name"]}' + ('[]' if r['ret'].endswith('[]') else ''))
        for p in r['params']:
            pt = base_type(p.split()[0]) if p.split() else ''
            if pt.lower() in allnames:
                cons[allnames[pt.lower()]] += 1
    w('| Type | Returned by | Takes it |')
    w('|---|---|---:|')
    for t in sorted(prod, key=str.lower):
        w(f'| {t} | {", ".join(f"`{x}`" for x in sorted(prod[t], key=str.lower))} | {cons[t]} |')
    w('')

    w('## Cross-reference C: global-function scripts')
    w('')
    w('Scripts whose functions are called as `Script.Function(...)` with no object. A script is listed when every function it declares is `global`.')
    w('')
    w('| Script | Layers | Global functions |')
    w('|---|---|---:|')
    for m in sorted(merged.values(), key=lambda x: x['name'].lower()):
        if m['funcs'] and all('global' in f['flags'] for f in m['funcs']):
            w(f'| {m["name"]} | {", ".join(m["layers"])} | {len(m["funcs"])} |')
    w('')
    w('Scripts that mix global and member functions (for example `Game`-style additions in F4SE layers) are visible in the per-script tables via the Flags column.')
    w('')

    # ---------- Pass 3a ----------
    if a.rag:
        conn = sqlite3.connect('file:%s?mode=ro' % a.rag, uri=True)
        binds = collect_binds(conn, a.rag_prefix)
        ref = {}
        for m in merged.values():
            ref[m['name'].lower()] = {f['name'].lower(): f for f in m['funcs']}
        w('## Pass 3a: from Papyrus down to the engine (top-down trace)')
        w('')
        w('This pass starts at the Papyrus call and follows it toward the engine. The path, for a native function:')
        w('')
        w('```')
        w('Papyrus source:   Debug.Notification("x")  /  akRef.MoveTo(...)')
        w('   -> BSScript VM resolves script + function name against its native-method table')
        w('   -> table entry was added by BindNativeMethod(script, function, C++ function, taskletCallable)')
        w('        vanilla natives: registered inside the game executable (no source in your RAG)')
        w('        F4SE additions:  registered by the plugin at startup via Papyrus::Bind(vm)')
        w('   -> C++ function runs, touching engine types (RE::PlayerCamera, RE::TESDataHandler, ...)')
        w('   -> engine memory, reached through Address Library offsets (not covered here)')
        w('```')
        w('')
        w(f'Source for the F4SE side: `{a.rag_prefix}*.h` in your index. It is a reimplementation (the folder is named `F4SEStub`), so whether it matches the F4SE DLL you actually run is unverified until Pass 4.')
        w('')
        w('- `BIND(Name, true)` means `taskletCallable = true` in `BindNativeMethod` (the VM may call it from a tasklet).')
        w('- A function whose parameters are all `[[maybe_unused]]` with a single-statement body is flagged **stub**: it is registered, so Papyrus can call it, but it only returns a constant.')
        w('- Arity check compares C++ parameter count (minus the self or `std::monostate` first parameter) with the Papyrus declaration. A mismatch means the binding and the indexed script disagree.')
        w('')
        # coverage
        f4se_funcs = collections.defaultdict(list)
        for m in merged.values():
            for f in m['funcs']:
                if f['layer'] == 'f4se':
                    f4se_funcs[m['name']].append(f)
        bound_by = collections.defaultdict(list)
        for b in binds:
            bound_by[b['script']].append(b)
        scripts_all = sorted(set(f4se_funcs) | set(bound_by), key=str.lower)
        w('### Coverage per script: F4SE additions in the indexed scripts vs functions bound in the source')
        w('')
        w('| Script | F4SE functions in scripts | Bound in source | Stub bodies | Declared, not bound | Bound, not declared | Arity mismatch |')
        w('|---|---:|---:|---:|---:|---:|---:|')
        tot = collections.Counter()
        unbound_rows, undeclared_rows, arity_rows = [], [], []
        for sc in scripts_all:
            decl = {f['name'].lower(): f for f in f4se_funcs.get(sc, [])}
            bnd = {b['func'].lower(): b for b in bound_by.get(sc, [])}
            unb = sorted(n for n in decl if n not in bnd)
            und = sorted(n for n in bnd if n not in ref.get(sc.lower(), {}))
            stubs = sum(1 for b in bnd.values() if b.get('stub'))
            ar = []
            for n, b in bnd.items():
                rf = ref.get(sc.lower(), {}).get(n)
                if rf and b.get('found') and len(rf['params']) != b['cpp_arity']:
                    ar.append((b['func'], len(rf['params']), b['cpp_arity']))
            tot.update({'decl': len(decl), 'bound': len(bnd), 'stub': stubs, 'unb': len(unb), 'und': len(und), 'ar': len(ar)})
            if unb:
                unbound_rows.append((sc, [decl[n]['name'] for n in unb]))
            if und:
                undeclared_rows.append((sc, [bnd[n]['func'] for n in und]))
            arity_rows += [(sc,) + x for x in ar]
            w(f'| {sc} | {len(decl)} | {len(bnd)} | {stubs} | {len(unb)} | {len(und)} | {len(ar)} |')
        w(f'| **total** | **{tot["decl"]}** | **{tot["bound"]}** | **{tot["stub"]}** | **{tot["unb"]}** | **{tot["und"]}** | **{tot["ar"]}** |')
        w('')
        if unbound_rows:
            w('### Declared in the F4SE scripts but not bound in the source')
            w('')
            w('These are callable in Papyrus (the script declares them) but have no binding in the indexed source, so they are implemented elsewhere (the real F4SE binary) or are missing from this stub.')
            w('')
            for sc, names in unbound_rows:
                w(f'- **{sc}**: ' + ', '.join(f'`{n}`' for n in names))
            w('')
        if undeclared_rows:
            w('### Bound in the source but absent from the indexed F4SE scripts')
            w('')
            for sc, names in undeclared_rows:
                w(f'- **{sc}**: ' + ', '.join(f'`{n}`' for n in names))
            w('')
        if arity_rows:
            w('### Arity mismatches (Papyrus params vs C++ params)')
            w('')
            w('| Script | Function | Papyrus params | C++ params |')
            w('|---|---|---:|---:|')
            for sc, fn, pa, ca in arity_rows:
                w(f'| {sc} | `{fn}` | {pa} | {ca} |')
            w('')
        # full trace table
        w('### Full trace: bound function to C++ signature to engine types')
        w('')
        w('| Script | Function | Kind | Tasklet | State | C++ parameters (after self) | Engine types touched | Papyrus declares it |')
        w('|---|---|---|---|---|---|---|---|')
        for b in sorted(binds, key=lambda x: (x['script'].lower(), x['func'].lower())):
            rf = ref.get(b['script'].lower(), {}).get(b['func'].lower())
            decl = ('yes (' + rf['layer'] + ')') if rf else 'no'
            if not b['found']:
                w(f'| {b["script"]} | `{b["func"]}` | ? | {"yes" if b["tasklet"] else ""} | definition not found | | | {decl} |')
                continue
            w(f'| {b["script"]} | `{b["func"]}` | {"global" if b["global"] else "member"} | {"yes" if b["tasklet"] else ""} | '
              f'{"stub" if b["stub"] else "implemented"} | {esc(b["cpp_params"])} | {", ".join(b["engine"])} | {decl} |')
        w('')
        # vanilla endpoint
        w('### Where vanilla natives end')
        w('')
        w('Vanilla `native` functions are registered inside the game executable. Their implementation is not in your RAG, so the trace stops at the VM table. Counts below are from the indexed vanilla scripts (flag `native` in the Flags column of each script table).')
        w('')
        w('| Script | Native functions | Non-native (script-side) |')
        w('|---|---:|---:|')
        vt = collections.Counter()
        for m in sorted(merged.values(), key=lambda x: x['name'].lower()):
            v = [f for f in m['funcs'] if f['layer'] == 'vanilla']
            if not v:
                continue
            nat = sum(1 for f in v if 'native' in f['flags'])
            vt.update({'n': nat, 'o': len(v) - nat})
            w(f'| {m["name"]} | {nat} | {len(v) - nat} |')
        w(f'| **total** | **{vt["n"]}** | **{vt["o"]}** |')
        w('')
        w('Non-native functions are written in Papyrus itself and run in the VM; they end at other Papyrus or native calls rather than at the engine directly.')
        w('')
        print(f'pass3a: bound={tot["bound"]} stubs={tot["stub"]} unbound={tot["unb"]} undeclared={tot["und"]} arity={tot["ar"]}')

    open(a.out, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    tot_f = sum(b['funcs'] for b in uniq.values())
    tot_e = sum(b['events'] for b in uniq.values())
    print(f'files={len(scripts)} scripts={len(merged)} unique_funcs={tot_f} unique_events={tot_e} -> {a.out}')


if __name__ == '__main__':
    sys.exit(main())
