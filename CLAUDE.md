# autotris — notes for Claude

A self-playing tetris for a spare monitor. Pure standard library, Python 3.10+
(needs `int.bit_count`).

## Run and test

```bash
python3 -m autotris                                  # normal run
python3 -m autotris --frames 300 --no-alt            # N frames, no alt screen
python3 -m autotris --frames 300 --no-alt --plain    # ... print last frame as text
python3 -m autotris --frames 300 --no-alt --deterministic --digest
```

`--deterministic` swaps the wall clock for a frame counter, so a seed fully
determines the run (including theme cycling). `--digest` prints a sha256 over
every rendered frame. Together they are a golden test: capture digests across
themes and sizes before a change, compare after. `COLUMNS`/`LINES` set the
canvas when stdout is not a tty.

## Packages

| package | responsibility |
|---------|---------------|
| `core/` | board, pieces, scoring, and the `Game` state machine. Emits events; knows nothing about drawing. |
| `ai/` | `Brain` picking a move via an `Evaluator` (how good is a placement) and a `Strategy` (what to do with the scored options). |
| `display/` | `Canvas` of coloured cells, colour maths, and `Screen` (terminal ownership). |
| `theming/` | `Theme` plus `BlockStyle` / `Backdrop` implementations, Omarchy loading, and the registry. |
| `view/` | `Widget` implementations: panels, board, overlays, transitions, effects. |
| `input/` | key decoding and one `Command` per binding. |
| `session.py` | wires it together and runs the frame loop. |
| `clock.py` | `RealClock` or `FixedStepClock`. |

Dependencies point inwards: `core` imports nothing from the rest, `ai` imports
only `core`, `view` and `theming` depend on `display`.

## Things that will bite you

**The board is resizable.** `Board` carries its own `columns`/`rows`; nothing
caches them. AI thresholds are fractions of the board height (`PANIC_FRACTION`,
`CALM_FRACTION`, `FLAT_FRACTION`), never absolute row counts.

**Two board representations coexist on purpose.** The cell grid keeps which
piece filled each square, because the renderer needs colours. `Bitboard` keeps
one integer per row, and every heuristic runs on that — worth 5-27x over
per-cell loops and what makes an 80x50 board affordable.

**Piece masks are normalised** so the leftmost cell is bit 0 (`Rotation.left`
converts back to board space). Iterate the absolute column from zero; never
shift a mask by a negative amount.

**`features.wells` is subtle.** A well starts where an empty cell has both
neighbours filled, then runs down while the column stays empty — cells below
the mouth need no neighbours. Getting it wrong is silent: it only shows up as
slightly worse play.

**Effects order matters.** `Effects.update` reacts to events, then advances,
then spawns particles. That ordering is what makes a shake decay on the frame it
starts while a new particle does not. Changing it changes every rendered frame.

**Draw order matters.** The backdrop paints characters, so panels use
`frame(..., fill=...)` (which wipes characters) rather than a background-only
rect. The status line draws after particles so they fly behind it.

**Never use a character wider than one column.** Check with
`unicodedata.east_asian_width(c) in ("W", "F")` before adding a glyph.

## The AI, and how it was tuned

Levels: `CHAOS`, `ROOKIE`, `PLAIN` (bare El-Tetris), `STACKER`, `MASTER`
(stacking plus one-piece lookahead, the default).

Stacking reserves a well column and refuses partial clears — but a buried hole
outranks that: with holes on the board it flips to DIGGING and clears normally
until the stack is clean, then resumes. Above `PANIC_FRACTION` it drops the
stacking terms entirely until it comes back down to `CALM_FRACTION`.

Constants in `ai/tuning.py` were fitted by simulation, not guessed. Without
DIGGING the AI averaged 2.08 buried holes; with it, 0.12 *and* a higher tetris
rate. **If you touch them, re-measure** — measure holes, tetris share and deaths
together, since improving one alone is easy and meaningless.

## Conventions

- Code, comments and UI strings are in English.
- Near-zero comments: names and small classes carry the meaning. Only keep a
  comment that prevents a real bug.
- No third-party runtime dependencies. `tools/record.py` may use PIL because it
  is a build tool, not part of the game.
- Commits are only made when asked, and never carry a co-author trailer.
