"""The playfield: a grid of cells that remembers which piece filled each one."""
from __future__ import annotations

from .bitboard import Bitboard
from .tetromino import PIECES

MIN_COLUMNS, MAX_COLUMNS = 5, 80
MIN_ROWS, MAX_ROWS = 8, 80
DEFAULT_COLUMNS, DEFAULT_ROWS = 10, 20


def clamp_size(columns, rows):
    return (max(MIN_COLUMNS, min(MAX_COLUMNS, int(columns))),
            max(MIN_ROWS, min(MAX_ROWS, int(rows))))


class Board:
    """Cells hold the piece name that filled them, or None."""

    def __init__(self, columns=DEFAULT_COLUMNS, rows=DEFAULT_ROWS, cells=None):
        self.columns, self.rows = clamp_size(columns, rows)
        self.cells = cells if cells is not None else self._empty()

    def _empty(self):
        return [[None] * self.columns for _ in range(self.rows)]

    def clear(self):
        self.cells = self._empty()

    @property
    def is_empty(self):
        return all(value is None for row in self.cells for value in row)

    def bits(self):
        return Bitboard.from_cells(self.cells, self.columns)

    def collides(self, cells):
        for x, y in cells:
            if x < 0 or x >= self.columns or y >= self.rows:
                return True
            if y >= 0 and self.cells[y][x] is not None:
                return True
        return False

    def landing_row(self, name, rotation, x, y=-4):
        offsets = PIECES[name][rotation].cells
        while not self.collides([(x + cx, y + 1 + cy) for cx, cy in offsets]):
            y += 1
        return y

    def place(self, name, rotation, x, y):
        landed = []
        for cx, cy in PIECES[name][rotation].cells:
            px, py = x + cx, y + cy
            if py >= 0:
                self.cells[py][px] = name
            landed.append((px, py))
        return landed

    def full_rows(self):
        return [r for r, row in enumerate(self.cells) if all(v is not None for v in row)]

    def collapse(self, rows):
        kept = [row for r, row in enumerate(self.cells) if r not in rows]
        self.cells = [[None] * self.columns for _ in rows] + kept

    def heights(self):
        result = [0] * self.columns
        for c in range(self.columns):
            for r in range(self.rows):
                if self.cells[r][c] is not None:
                    result[c] = self.rows - r
                    break
        return result

    def resized(self, columns, rows):
        """A board of the new size with this stack kept, anchored bottom-left."""
        grown = Board(columns, rows)
        for r in range(min(grown.rows, self.rows)):
            for c in range(min(grown.columns, self.columns)):
                grown.cells[grown.rows - 1 - r][c] = self.cells[self.rows - 1 - r][c]
        done = grown.full_rows()
        if done:
            grown.collapse(done)
        return grown
