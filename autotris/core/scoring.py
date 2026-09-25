"""Line scoring, combo and back-to-back bookkeeping."""
from __future__ import annotations

LINE_SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
ROWS_PER_LEVEL = 10


class Scoring:
    def __init__(self):
        self.reset()

    def reset(self):
        self.score = 0
        self.lines = 0
        self.level = 1
        self.tetrises = 0
        self.combo = -1
        self.back_to_back = 0

    def break_combo(self):
        self.combo = -1

    def register(self, cleared):
        self.lines += cleared
        self.combo += 1
        tetris = cleared == 4
        gain = LINE_SCORES[cleared] * self.level
        if tetris:
            self.tetrises += 1
            if self.back_to_back:
                gain = int(gain * 1.5)
            self.back_to_back += 1
        else:
            self.back_to_back = 0
        if self.combo > 0:
            gain += 50 * self.combo * self.level
        self.score += gain
        level = 1 + self.lines // ROWS_PER_LEVEL
        promoted = level != self.level
        self.level = level
        return gain, promoted
