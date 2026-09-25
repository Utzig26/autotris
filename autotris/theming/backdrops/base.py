"""What lives behind the board."""
from __future__ import annotations

import math
from abc import ABC, abstractmethod

from ...display.color import lerp


class Backdrop(ABC):
    """Fills the canvas background, then may draw on top of it."""

    def draw(self, canvas, theme, field, t, flash=0.0):
        pulse = 0.5 + 0.5 * math.sin(t * 0.7)
        for y in range(canvas.height):
            depth = y / max(1, canvas.height - 1)
            color = self.row_color(theme, depth, y, t, pulse)
            if flash:
                color = lerp(color, theme.accent, flash)
            row = canvas.bg[y]
            for x in range(canvas.width):
                row[x] = color
        self.overlay(canvas, theme, field, t)

    @abstractmethod
    def row_color(self, theme, depth, y, t, pulse):
        ...

    def overlay(self, canvas, theme, field, t):
        pass
