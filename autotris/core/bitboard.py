"""Row-as-integer view of the stack, used by every AI heuristic."""
from __future__ import annotations


class Bitboard:
    """One integer per row; bit c set means column c is occupied."""

    __slots__ = ("rows", "columns", "height", "full")

    def __init__(self, rows, columns):
        self.rows = rows
        self.columns = columns
        self.height = len(rows)
        self.full = (1 << columns) - 1

    @classmethod
    def from_cells(cls, cells, columns):
        rows = []
        for row in cells:
            mask = 0
            for c, value in enumerate(row):
                if value is not None:
                    mask |= 1 << c
            rows.append(mask)
        return cls(rows, columns)

    def replace(self, rows):
        return Bitboard(rows, self.columns)

    def landing_row(self, rotation, column):
        rows, limit = self.rows, self.height
        y = -rotation.height
        while True:
            candidate = y + 1
            for offset, mask in rotation.masks:
                target = candidate + offset
                if target >= limit:
                    return y
                if target >= 0 and rows[target] & (mask << column):
                    return y
            y = candidate

    def after(self, rotation, column, y):
        """Board once the piece lands, plus how many rows it cleared."""
        rows = self.rows[:]
        for offset, mask in rotation.masks:
            target = y + offset
            if target >= 0:
                rows[target] |= mask << column
        full = self.full
        kept = [row for row in rows if row != full]
        cleared = len(rows) - len(kept)
        if cleared:
            rows = [0] * cleared + kept
        return Bitboard(rows, self.columns), cleared

    def columns_as_ints(self):
        columns = [0] * self.columns
        for r, row in enumerate(self.rows):
            remaining = row
            while remaining:
                bit = remaining & -remaining
                columns[bit.bit_length() - 1] |= 1 << r
                remaining ^= bit
        return columns
