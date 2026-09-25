"""Piece randomiser."""
from __future__ import annotations

from .tetromino import NAMES


class SevenBag:
    """Shuffles all seven pieces, deals them, repeats."""

    def __init__(self, rng):
        self._rng = rng
        self._queue = []

    def _refill(self):
        batch = list(NAMES)
        self._rng.shuffle(batch)
        self._queue.extend(batch)

    def take(self):
        if not self._queue:
            self._refill()
        return self._queue.pop(0)

    def peek(self, count):
        while len(self._queue) < count:
            self._refill()
        return self._queue[:count]
