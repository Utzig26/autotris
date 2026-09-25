"""The seven tetrominoes, their rotations, and the bit masks the AI uses."""
from __future__ import annotations

NAMES = "IJLOSTZ"

_SHAPES = {
    "I": ["....", "IIII", "....", "...."],
    "J": ["J..", "JJJ", "..."],
    "L": ["..L", "LLL", "..."],
    "O": ["OO", "OO"],
    "S": [".SS", "SS.", "..."],
    "T": [".T.", "TTT", "..."],
    "Z": ["ZZ.", ".ZZ", "..."],
}


def _rotate(shape):
    n = len(shape)
    return ["".join(shape[n - 1 - r][c] for r in range(n)) for c in range(len(shape[0]))]


def _offsets(shape):
    return tuple((x, y) for y, row in enumerate(shape)
                 for x, ch in enumerate(row) if ch != ".")


def _unique_rotations(shape):
    seen, current = [], shape
    for _ in range(4):
        if current not in seen:
            seen.append(current)
        current = _rotate(current)
    return [_offsets(s) for s in seen]


class Rotation:
    """One orientation of a piece, as cell offsets and as row bit masks.

    Masks are normalised so the leftmost cell is bit 0, which keeps every
    shift non-negative; `left` is the offset that converts back to board space.
    """

    __slots__ = ("cells", "masks", "height", "width", "left", "size", "depth_sum")

    def __init__(self, cells):
        self.cells = cells
        self.left = min(x for x, _ in cells)
        right = max(x for x, _ in cells)
        self.width = right - self.left + 1
        rows = {}
        for x, y in cells:
            rows[y] = rows.get(y, 0) | (1 << (x - self.left))
        self.masks = tuple(sorted(rows.items()))
        self.height = max(rows) + 1
        self.size = len(cells)
        self.depth_sum = sum(y for _, y in cells)


class Tetromino:
    """A piece kind and its rotations."""

    __slots__ = ("name", "rotations")

    def __init__(self, name, shape):
        self.name = name
        self.rotations = [Rotation(c) for c in _unique_rotations(shape)]

    def __len__(self):
        return len(self.rotations)

    def __getitem__(self, index):
        return self.rotations[index % len(self.rotations)]


PIECES = {name: Tetromino(name, shape) for name, shape in _SHAPES.items()}


def cells_at(name, rotation, x, y):
    return [(x + cx, y + cy) for cx, cy in PIECES[name][rotation].cells]


def spawn_column(name, columns, rotation=0):
    rot = PIECES[name][rotation]
    return (columns - rot.width) // 2 - rot.left
