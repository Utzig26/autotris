"""autotris engine: pieces, board, scoring and the auto-player brain.

The board is a list of rows of cell values (piece letter or None) because the
renderer needs colours. The AI never touches that: it converts the board into
one integer per row and does every heuristic with bit operations, which is what
keeps large boards affordable.
"""
from __future__ import annotations

COLS, ROWS = 10, 20          # mutable, see set_size()
MIN_COLS, MAX_COLS = 5, 80
MIN_ROWS, MAX_ROWS = 8, 80
FULL = (1 << COLS) - 1
ORDER = "IJLOSTZ"


def set_size(cols, rows):
    """Resize the board. Any existing grid becomes invalid."""
    global COLS, ROWS, FULL
    COLS = max(MIN_COLS, min(MAX_COLS, int(cols)))
    ROWS = max(MIN_ROWS, min(MAX_ROWS, int(rows)))
    FULL = (1 << COLS) - 1
    return COLS, ROWS


_BASE = {
    "I": ["....", "IIII", "....", "...."],
    "J": ["J..", "JJJ", "..."],
    "L": ["..L", "LLL", "..."],
    "O": ["OO", "OO"],
    "S": [".SS", "SS.", "..."],
    "T": [".T.", "TTT", "..."],
    "Z": ["ZZ.", ".ZZ", "..."],
}


def _rot_cw(m):
    n = len(m)
    return ["".join(m[n - 1 - r][c] for r in range(n)) for c in range(len(m[0]))]


def _cells(m):
    return tuple((x, y) for y, row in enumerate(m) for x, ch in enumerate(row) if ch != ".")


ROT = {}
for _k, _m in _BASE.items():
    _seen, _cur = [], _m
    for _ in range(4):
        if _cur not in _seen:
            _seen.append(_cur)
        _cur = _rot_cw(_cur)
    ROT[_k] = [_cells(r) for r in _seen]

SPAN = {k: [(min(x for x, _ in c), max(x for x, _ in c)) for c in rots] for k, rots in ROT.items()}


def _piece_bits(cells):
    """Masks normalised so the leftmost cell is bit 0 - shifts are never negative.

    Returns (rows as (dy, mask) pairs, height, cell count, sum of dy, lo, width).
    """
    lo = min(cx for cx, _ in cells)
    hi = max(cx for cx, _ in cells)
    by = {}
    for cx, cy in cells:
        by[cy] = by.get(cy, 0) | (1 << (cx - lo))
    pairs = tuple(sorted(by.items()))
    return (pairs, max(by) + 1, len(cells), sum(cy for _, cy in cells), lo, hi - lo + 1)


PIECE = {k: [_piece_bits(c) for c in rots] for k, rots in ROT.items()}


class Bag:
    """Standard 7-bag randomiser."""

    def __init__(self, rng):
        self.rng = rng
        self.q = []

    def _fill(self):
        b = list(ORDER)
        self.rng.shuffle(b)
        self.q.extend(b)

    def take(self):
        if not self.q:
            self._fill()
        return self.q.pop(0)

    def peek(self, n):
        while len(self.q) < n:
            self._fill()
        return self.q[:n]


# ------------------------------------------------------------- cell board

def new_grid():
    return [[None] * COLS for _ in range(ROWS)]


def spawn_x(kind, rot=0):
    lo, hi = SPAN[kind][rot]
    return (COLS - (hi - lo + 1)) // 2 - lo


def cells_at(kind, rot, x, y):
    return [(x + cx, y + cy) for cx, cy in ROT[kind][rot]]


def collides(grid, cells):
    for cx, cy in cells:
        if cx < 0 or cx >= COLS or cy >= ROWS:
            return True
        if cy >= 0 and grid[cy][cx] is not None:
            return True
    return False


def drop_y(grid, kind, rot, x, y=-4):
    while not collides(grid, cells_at(kind, rot, x, y + 1)):
        y += 1
    return y


def full_rows(grid):
    return [r for r in range(ROWS) if all(v is not None for v in grid[r])]


def collapse(grid, rows):
    keep = [row for r, row in enumerate(grid) if r not in rows]
    return [[None] * COLS for _ in range(len(rows))] + keep


def height_map(grid):
    hs = [0] * COLS
    for c in range(COLS):
        for r in range(ROWS):
            if grid[r][c] is not None:
                hs[c] = ROWS - r
                break
    return hs


def ready_rows(grid, well):
    """Rows that are complete except for the well column - tetris fuel."""
    n = 0
    for r in range(ROWS):
        row = grid[r]
        if row[well] is None and all(row[c] is not None for c in range(COLS) if c != well):
            n += 1
    return n


def holes(grid):
    return _holes_b(to_bits(grid))


# --------------------------------------------------------------- bitboard

def to_bits(grid):
    """One integer per row; bit c set means column c is occupied."""
    out = []
    for row in grid:
        m = 0
        for c, v in enumerate(row):
            if v is not None:
                m |= 1 << c
        out.append(m)
    return out


def _row_trans_b(rows):
    t = 0
    left = 1
    right = 1 << (COLS - 1)
    half = FULL >> 1
    for row in rows:
        t += ((row ^ (row >> 1)) & half).bit_count()
        if not row & left:
            t += 1                      # wall on the left counts as filled
        if not row & right:
            t += 1
    return t


def _col_trans_b(rows):
    t = 0
    prev = rows[0]
    for r in range(1, ROWS):
        cur = rows[r]
        t += (cur ^ prev).bit_count()
        prev = cur
    return t + (~prev & FULL).bit_count()   # floor counts as filled


def _holes_b(rows):
    n = 0
    covered = 0
    for row in rows:
        n += (covered & ~row & FULL).bit_count()
        covered |= row
    return n


def _wells_b(rows, skip=None):
    """Sum of 1..depth for every well. `skip` excludes the reserved column.

    A well starts where an empty cell has both neighbours filled (walls count),
    and then runs down for as long as the column stays empty - the cells below
    the mouth do not need neighbours, which is what the original heuristic does.
    """
    cols = [0] * COLS
    for r, row in enumerate(rows):
        m = row
        while m:
            b = m & -m
            cols[b.bit_length() - 1] |= 1 << r
            m ^= b
    rowmask = (1 << ROWS) - 1
    total = 0
    for c in range(COLS):
        if c == skip:
            continue
        ec = ~cols[c] & rowmask
        if not ec:
            continue
        lf = cols[c - 1] if c > 0 else rowmask
        rf = cols[c + 1] if c < COLS - 1 else rowmask
        mouths = ec & lf & rf
        r = 0
        while mouths >> r:
            rem = mouths >> r
            r += (rem & -rem).bit_length() - 1      # next mouth
            inv = ~(ec >> r) & ((1 << (ROWS - r)) - 1)
            d = (ROWS - r) if inv == 0 else (inv & -inv).bit_length() - 1
            total += d * (d + 1) // 2
            r += d
    return total


def _heights_b(rows):
    hs = [0] * COLS
    seen = 0
    for r, row in enumerate(rows):
        new = row & ~seen
        while new:
            b = new & -new
            hs[b.bit_length() - 1] = ROWS - r
            new ^= b
        seen |= row
    return hs


def _stack_h_b(rows, skip=None):
    mask = FULL if skip is None else (FULL & ~(1 << skip))
    for r, row in enumerate(rows):
        if row & mask:
            return ROWS - r
    return 0


def _ready_b(rows, well):
    bit = 1 << well
    target = FULL & ~bit
    return sum(1 for row in rows if (row & target) == target and not row & bit)


def _drop_b(rows, pairs, height, x):
    """Lowest y where the piece rests. Rows above the board are free."""
    y = -height
    while True:
        ny = y + 1
        for dy, m0 in pairs:
            rr = ny + dy
            if rr >= ROWS:
                return y
            if rr >= 0 and rows[rr] & (m0 << x):
                return y
        y = ny


def _place_b(rows, pairs, x, y):
    """Returns (new rows, cleared count). Assumes the placement is legal."""
    out = rows[:]
    for dy, m0 in pairs:
        rr = y + dy
        if rr >= 0:
            out[rr] |= m0 << x
    cleared = 0
    kept = []
    for row in out:
        if row == FULL:
            cleared += 1
        else:
            kept.append(row)
    if cleared:
        out = [0] * cleared + kept
    return out, cleared


# --------------------------------------------------------------- heuristic

# El-Tetris weights (Islam El-Ashi): plays clean, but clears one row at a time
W = (-4.500158825082766, 3.4181268101392694, -3.2178882868487753,
     -9.348695305445199, -7.899265427351652, -3.3855972247263626)

MIGRATE = 5           # only move the well if the current one is this much higher
PANIC_F = 0.78        # stack height fraction that triggers panic
CALM_F = 0.45         # and how far it must come down to resume stacking
LAST_F = 0.88         # last resort: clear anything
FLAT_F = 0.50         # height above which stacking starts to cost
# tuned by simulation: ~87% of lines come out as tetrises, ~0.1 holes, no deaths
K_TETRIS, K_PARTIAL, K_WELL, K_READY, K_HEIGHT = 900.0, 200.0, 500.0, 10.0, 3.0
K_DIG, K_DIGCLEAR = 300.0, 100.0   # digging: never abandon a buried hole
LOOKAHEAD = 0.25      # how much the next piece weighs (MASTER level)
LEVELS = ("CHAOS", "ROOKIE", "PLAIN", "STACKER", "MASTER")


def default_well():
    return COLS - 1


def panic_h():
    return max(4, int(ROWS * PANIC_F))


def calm_h():
    return max(2, int(ROWS * CALM_F))


def pick_well(rows, cur):
    """Choose the well column. It migrates if the current one gets buried."""
    hs = _heights_b(rows)
    best = min(range(COLS), key=lambda c: (hs[c], 0 if c == cur else 1,
                                           0 if c in (0, COLS - 1) else 1))
    return best if hs[cur] - hs[best] >= MIGRATE else cur


def _score(rows, cleared, sum_cy, ncells, stack, panic, well, holes0):
    stacking = stack and not panic
    holes1 = _holes_b(rows)
    landing = ROWS - (sum_cy / ncells)
    s = (W[0] * landing + W[1] * cleared + W[2] * _row_trans_b(rows)
         + W[3] * _col_trans_b(rows) + W[4] * holes1
         + W[5] * _wells_b(rows, well if stacking else None))
    if stacking:
        # a buried hole outranks stacking: dig it out, then go back to stacking
        dig = holes0 > 0
        if cleared == 4:
            s += K_TETRIS
        elif cleared:
            s += K_DIGCLEAR * cleared if dig else -K_PARTIAL * cleared
        s += K_READY * _ready_b(rows, well)
        s -= K_HEIGHT * max(0, _stack_h_b(rows, well) - int(ROWS * FLAT_F))
        s += K_DIG * (holes0 - holes1)
    return s


def candidates_bits(rows, kind, stack=False, panic=False, well=None, holes0=None):
    if well is None:
        well = default_well()
    if holes0 is None:
        holes0 = _holes_b(rows)
    stacking = stack and not panic
    wellbit = 1 << well
    out = []
    for rot, (pairs, height, ncells, sumdy, lo, width) in enumerate(PIECE[kind]):
        for xa in range(COLS - width + 1):
            x = xa - lo                       # offset the cell board uses
            y = _drop_b(rows, pairs, height, xa)
            if y < 0:
                continue                      # sticking out of the top
            after, cleared = _place_b(rows, pairs, xa, y)
            s = _score(after, cleared, ncells * y + sumdy, ncells,
                       stack, panic, well, holes0)
            if stacking and cleared < 4:
                for dy, m0 in pairs:
                    if (m0 << xa) & wellbit:
                        s -= K_WELL * (0.3 if holes0 > 0 else 1.0)
                        break
            out.append({"score": s, "rot": rot, "x": x, "y": y,
                        "cleared": cleared, "kind": kind, "hold": False,
                        "rows": after})
    out.sort(key=lambda c: -c["score"])
    return out


def candidates(grid, kind, stack=False, panic=False, well=None):
    return candidates_bits(to_bits(grid), kind, stack, panic, well)


class Brain:
    """Picks the move. The level changes how hard it thinks - and how it fails."""

    def __init__(self, level=3, rng=None, well=None):
        self.level = level
        self.rng = rng
        self.well = default_well() if well is None else well
        self.panic = False
        self.mode = "—"

    @property
    def label(self):
        return LEVELS[self.level]

    def decide(self, grid, kind, alt=None):
        rows = to_bits(grid)
        lvl = self.level
        stack = lvl >= 3
        if self.well >= COLS:
            self.well = default_well()
        holes0 = _holes_b(rows)
        if stack:
            self.well = pick_well(rows, self.well)
            h = _stack_h_b(rows, self.well)
            if self.panic:
                self.panic = h > calm_h()       # hysteresis: calm down properly
            else:
                self.panic = h > panic_h() and _ready_b(rows, self.well) < 4
            if h > ROWS * LAST_F:
                self.panic = True
            self.mode = "PANIC" if self.panic else ("DIGGING" if holes0 else "STACKING")
        else:
            self.panic = False
            self.mode = "CLEARING"
        cand = candidates_bits(rows, kind, stack, self.panic, self.well, holes0)
        if alt and alt != kind:
            for a in candidates_bits(rows, alt, stack, self.panic, self.well, holes0):
                a["hold"] = True
                cand.append(a)
            cand.sort(key=lambda c: -c["score"])
        if not cand:
            return None, [], self
        if lvl == 0:                                   # pure chaos
            pick = self.rng.choice(cand)
            return pick, [pick] + cand[:2], self
        if lvl == 1 and self.rng.random() < 0.55:      # rookie: misses a lot
            pick = self.rng.choice(cand[:max(3, len(cand) // 2)])
            return pick, [pick] + cand[:2], self
        if lvl >= 4 and alt:                           # master: reads the next piece
            width = max(2, min(8, 2400 // max(1, COLS * ROWS)))
            best, bs = None, None
            for c in cand[:width]:
                nxt = candidates_bits(c["rows"], alt, stack,
                                      _stack_h_b(c["rows"], self.well) > panic_h(),
                                      self.well)
                v = c["score"] + LOOKAHEAD * (nxt[0]["score"] if nxt else -500)
                if bs is None or v > bs:
                    best, bs = c, v
            if best is not None:
                return best, [best] + [c for c in cand[:3] if c is not best][:2], self
        return cand[0], cand[:3], self


SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
