"""Theme changes: each one is a function of where the reveal has reached."""
from __future__ import annotations

import math
from abc import ABC, abstractmethod

from ..display.color import shade

FRAMES = 26
EDGE = 0.035


class Transition(ABC):
    """Reveals the new theme over a snapshot of the previous frame."""

    frames = FRAMES
    distorts = False

    def __init__(self, canvas, rng):
        self.rng = rng
        self.elapsed = 0
        self.snapshot = canvas.snapshot()
        self.noise = [[rng.random() for _ in range(canvas.width)] for _ in range(canvas.height)]
        self.columns = [rng.random() * 0.45 for _ in range(canvas.width + 4)]
        self.bands = [rng.random() for _ in range(canvas.height + 4)]
        self.jitter = [rng.randint(-9, 9) for _ in range(canvas.height + 4)]

    @property
    def done(self):
        return self.elapsed >= self.frames

    @abstractmethod
    def reach(self, x, y, width, height):
        """0 means revealed first, 1 means revealed last."""

    def compose(self, canvas, theme):
        progress = self.elapsed / self.frames
        width, height = canvas.width, canvas.height
        for y in range(height):
            offset = self.jitter[y] if (self.distorts and progress < 0.75) else 0
            for x in range(width):
                point = self.reach(x, y, width, height)
                if point <= progress:
                    if abs(point - progress) < EDGE:
                        canvas.fg[y][x] = shade(theme.background_color, 0.4)
                        canvas.bg[y][x] = theme.accent
                    continue
                canvas.restore_cell(self.snapshot, x, y,
                                    min(width - 1, max(0, x + offset)))
        self.elapsed += 1


class Wipe(Transition):
    def reach(self, x, y, width, height):
        return x / max(1, width - 1)


class Iris(Transition):
    def reach(self, x, y, width, height):
        dx = (x - width / 2) / (width / 2)
        dy = (y - height / 2) / (height / 2)
        return min(1.0, math.hypot(dx, dy) / 1.42)


class Dissolve(Transition):
    def reach(self, x, y, width, height):
        return self.noise[y][x]


class FallingBlocks(Transition):
    def reach(self, x, y, width, height):
        return min(1.0, y / max(1, height - 1) * 0.6 + self.columns[x])


class Curtain(Transition):
    def reach(self, x, y, width, height):
        return 1.0 - abs(y - height / 2) / (height / 2 + 1e-6)


class Doors(Transition):
    def reach(self, x, y, width, height):
        return 1.0 - abs(x - width / 2) / (width / 2 + 1e-6)


class Glitch(Transition):
    distorts = True

    def reach(self, x, y, width, height):
        return self.bands[y]


class Scan(Transition):
    def reach(self, x, y, width, height):
        return ((y * 7) % max(1, height)) / max(1, height)


ALL = (Wipe, Iris, Dissolve, FallingBlocks, Curtain, Doors, Glitch, Scan)


def random_transition(canvas, rng):
    return rng.choice(ALL)(canvas, rng)
