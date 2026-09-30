# Tool output format

A single convention for every tool in `tools/`, so that a long capture is
readable by a person *and* parseable by a program without either mode being an
afterthought.

## Why this exists

The original `vlink_probe.py` printed indented text and nothing else. Reading a
30-frame capture meant scrolling, and every check ("is `gameFrameCount` still
0?", "did anything get dropped?", "did the sequence regress?") was answered by
eyeballing. That is slow, and it is unreliable — the eye skips a `0` and reads
a `1`.

It also cost real time in practice: a probe blocked for six seconds on
`ERROR_BUSY` and looked like a hang, because the tool had no way to say "I am
retrying" in a form a machine could interrupt.

## The two modes

    --format text     indented, for a human reading a terminal (default)
    --format jsonl    one JSON object per line, for parsing

**JSONL, not a single JSON document.** A capture is streamed, not buffered: a
reader that dies at frame 40 of a single document has nothing at all, whereas
every object already emitted is still usable. That property is worth more than
the convenience of one bracket at the end.

## Record kinds

Every line has a `kind`:

| `kind`     | when |
|------------|------|
| `frame`    | one protocol frame: `seq`, `type`, `name`, `tid`, `payload`, `fields` |
| `handshake`| the two runtime signals, at the end of the session |
| `error`    | a failure, with a stable `code` |
| `summary`  | the closing record: totals, per-type counts, invariants |

`fields` carries **raw unpacked values** — ints and floats, not pre-formatted
strings. A `totalEventsDropped` of `0` must be comparable as a number; a
formatted `"0"` invites a careless string comparison that also matches `"0"`.
Display formatting happens only in the text path, at emit time.

## Filters

All filters compose, and all of them are applied *after* the counters are
updated — so a filter never changes what the summary describes. A capture that
matched nothing reports `matched 0`, it does not report success.

| flag | effect |
|------|--------|
| `-e, --event` | keep only these event types. Repeatable and comma-separated. Accepts `Heartbeat` or `0x01`. |
| `-m, --match` | regex over the rendered frame text. The general "show me the one frame where X happened". |
| `-F, --field` | regex over field *names*; projects the output down instead of scrolling it. |

Examples:

    # is the game actually ticking frames yet?
    vlink_probe.py --format jsonl -e Heartbeat -m 'gameFrameCount\s+[1-9]'

    # one-line verdict, no scroll
    vlink_probe.py --summary-only

    # just the counters, projected
    vlink_probe.py --format jsonl -F 'total.*|gameFrame'

## Error codes

Stable, and distinct where the responses differ:

| code | meaning |
|------|---------|
| `no_listener` | nothing is on the pipe. Expected when the game is not running. |
| `stale_client` | the server is up but single-instance is already claimed. Needs a game restart. |

`no_listener` and `stale_client` are deliberately different codes: collapsing
them sends someone to restart a game that was never running. Both cost minutes
to diagnose wrongly.

## Exit codes

| code | meaning |
|------|---------|
| 0 | connected, frames received |
| 1 | no listener, or stale client |
| 2 | bad magic — the pipe is not our wire format |
| 3 | connected but zero frames. **A real finding, not a pass.** |

Exit 3 matters: "the transport is up and the runtime is writing nothing" looks
like a quiet success in a log, and it is the opposite.

## For the runtime's own log

`logLine(level, text)` in the runtime, and the `PluginDiag` payload, both carry
machine-readable JSON. The resolver report is JSON precisely so a tool never has
to scrape prose to find out what resolved — which is the same mistake this
format exists to stop repeating.
