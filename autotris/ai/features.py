"""Board measurements, all of them on row bit masks."""
from __future__ import annotations


def row_transitions(bits):
    total = 0
    left = 1
    right = 1 << (bits.columns - 1)
    inner = bits.full >> 1
    for row in bits.rows:
        total += ((row ^ (row >> 1)) & inner).bit_count()
        if not row & left:
            total += 1
        if not row & right:
            total += 1
    return total


def column_transitions(bits):
    total = 0
    previous = bits.rows[0]
    for row in bits.rows[1:]:
        total += (row ^ previous).bit_count()
        previous = row
    return total + (~previous & bits.full).bit_count()


def holes(bits):
    total = 0
    covered = 0
    for row in bits.rows:
        total += (covered & ~row & bits.full).bit_count()
        covered |= row
    return total


def wells(bits, skip=None):
    """A well opens where an empty cell has both neighbours filled, then runs
    down while the column stays empty - the cells below the mouth need no
    neighbours, which is what the original El-Tetris heuristic measures."""
    columns = bits.columns_as_ints()
    span = (1 << bits.height) - 1
    total = 0
    for c in range(bits.columns):
        if c == skip:
            continue
        empty = ~columns[c] & span
        if not empty:
            continue
        left = columns[c - 1] if c > 0 else span
        right = columns[c + 1] if c < bits.columns - 1 else span
        mouths = empty & left & right
        r = 0
        while mouths >> r:
            remaining = mouths >> r
            r += (remaining & -remaining).bit_length() - 1
            blocked = ~(empty >> r) & ((1 << (bits.height - r)) - 1)
            depth = (bits.height - r) if blocked == 0 else (blocked & -blocked).bit_length() - 1
            total += depth * (depth + 1) // 2
            r += depth
    return total


def heights(bits):
    result = [0] * bits.columns
    seen = 0
    for r, row in enumerate(bits.rows):
        fresh = row & ~seen
        while fresh:
            bit = fresh & -fresh
            result[bit.bit_length() - 1] = bits.height - r
            fresh ^= bit
        seen |= row
    return result


def stack_height(bits, skip=None):
    mask = bits.full if skip is None else (bits.full & ~(1 << skip))
    for r, row in enumerate(bits.rows):
        if row & mask:
            return bits.height - r
    return 0


def ready_rows(bits, well):
    bit = 1 << well
    target = bits.full & ~bit
    return sum(1 for row in bits.rows if (row & target) == target and not row & bit)
