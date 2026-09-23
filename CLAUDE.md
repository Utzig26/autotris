# autotris — notes for Claude

A self-playing tetris for a spare monitor. Five files, standard library only,
Python 3.10+ (needs `int.bit_count`).

## Run it

```bash
python3 autotris.py                       # normal run
python3 autotris.py --frames 300 --no-alt # headless: N frames then exit, no alt screen
python3 autotris.py --frames 300 --no-alt --plain   # ... and print the last frame as text
```

`--frames --no-alt` is the way to smoke-test a change without a terminal. Add
`--plain` to eyeball the layout (colours are stripped, so pipe it through `sed`
to map block glyphs to ASCII if you want to read it).

`COLUMNS`/`LINES` env vars set the canvas size when stdout is not a tty.

## Architecture

| file | responsibility |
|------|---------------|
| `engine.py` | pieces, board, scoring, and the AI. No rendering, no I/O. |
| `render.py` | `Canvas`: a grid of (char, fg, bg) that emits one ANSI string per frame. |
| `themes.py` | `Theme` objects + `draw_cell`. Builds Omarchy themes via `omarchy.py`. |
| `omarchy.py` | Reads `colors.toml` from Omarchy theme dirs; finds the active theme. |
| `autotris.py` | `Game` (state machine), `Fx` (particles), `Renderer`, `Transition`, `App` (keys, loop). |
| `tools/record.py` | Renders frames to PNG with PIL for the demo gif. Not needed at runtime. |

Dependency direction is one-way: `engine` knows nothing about the rest.

## The board can be resized

`E.COLS` / `E.ROWS` are **mutable module globals**, changed only through
`E.set_size(cols, rows)`, which also updates `E.FULL` (the all-ones row mask).
Anything that reads them must read them at call time, never cache them at import
time. Resizing invalidates every existing grid, so `App.set_grid` resets the
game and the brain's well column.

Thresholds are fractions of `ROWS` (`PANIC_F`, `CALM_F`, `LAST_F`, `FLAT_F`),
not absolute row counts, so they keep working on a 50-row board.

## The AI

Two representations coexist on purpose:

- the **cell grid** (`list[list[str | None]]`) is what the renderer needs, because
  it carries which piece each cell came from, i.e. its colour;
- the **bitboard** (`list[int]`, one integer per row) is what the AI uses.

`to_bits()` converts once per decision. Every heuristic (`_row_trans_b`,
`_col_trans_b`, `_holes_b`, `_wells_b`, `_heights_b`, `_ready_b`) works on
integers. That is a 5–27× speedup over per-cell loops and is what makes an
80×50 board playable.

Piece masks in `PIECE[kind][rot]` are **normalised so the leftmost cell is bit
0**, giving `(pairs, height, ncells, sumdy, lo, width)`. Iterate the absolute
column `xa` from 0, and the offset the cell board wants is `x = xa - lo`. Never
shift a mask by a negative amount.

`_wells_b` is subtle: a well *starts* where an empty cell has both neighbours
filled (walls count), and then runs down for as long as the column stays empty —
cells below the mouth do **not** need neighbours. Getting this wrong is silent;
it only shows up as slightly worse play.

### Behaviour, and how it was tuned

Levels: `CHAOS`, `ROOKIE`, `PLAIN` (bare El-Tetris), `STACKER`, `MASTER`
(STACKER + 1-ply lookahead). Default is MASTER.

STACKER/MASTER add stacking terms on top of El-Tetris: a big bonus for a
4-row clear, a penalty for 1–3 row clears, a heavy penalty for covering the
reserved well, and `K_DIG * (holes_before - holes_after)`.

The modes in `Brain.decide` matter:

- **STACKING** — base is clean, refuse partial clears, save for tetrises
- **DIGGING** — `holes > 0`: partial clears flip from penalty to bonus so it digs out
- **PANIC** — above `panic_h()`: drop the stacking terms entirely until `calm_h()`

Without DIGGING the AI buries holes and never returns; it measured 2.08 average
holes. With it, 0.12 holes *and* a higher tetris rate.

The constants (`K_TETRIS`, `K_PARTIAL`, `K_WELL`, `K_READY`, `K_HEIGHT`,
`K_DIG`, `K_DIGCLEAR`, `LOOKAHEAD`) were fitted by simulation, not guessed.
**If you touch them, re-measure** — several plausible values make it worse. A
fast headless harness that mirrors the real game loop (hold included) is the
right tool; measure holes, tetris share, and deaths together, since improving
one alone is easy and meaningless.

## Rendering

`Renderer.frame()` paints in order: background → panels → board → particles →
overlays. The background draws characters, so anything on top must use
`cv.box(..., fill=...)` or `clear_rect`, which wipe characters too — plain
`rect` only changes the background colour and lets glyphs bleed through.

A cell is `2 * scale` characters wide and `scale` tall, which keeps blocks
roughly square in a terminal.

**Never use a character wider than one column.** Fullwidth and emoji-presentation
glyphs break the whole grid. Check with
`unicodedata.east_asian_width(c) in ("W", "F")` before adding one.

Theme transitions snapshot the previous frame, draw the new theme normally, then
`Transition.compose` restores snapshot pixels wherever the reveal has not
arrived, so every transition is one `metric()` function.

## Conventions

- Everything — code, comments, UI strings — is in English.
- No third-party runtime dependencies. `tools/record.py` may use PIL because it
  is a build tool, not part of the game.
- Commits do not carry a co-author trailer.
