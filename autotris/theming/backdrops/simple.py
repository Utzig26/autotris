"""Backdrops that are only a colour ramp."""
from __future__ import annotations

import math

from ...display.color import lerp, shade
from .base import Backdrop


class Flat(Backdrop):
    def row_color(self, theme, depth, y, t, pulse):
        return theme.background_color


class Gradient(Backdrop):
    def row_color(self, theme, depth, y, t, pulse):
        return lerp(theme.background_color, theme.horizon_color,
                    depth * (0.8 + 0.2 * pulse))


class Scanlines(Backdrop):
    def row_color(self, theme, depth, y, t, pulse):
        color = lerp(theme.background_color, theme.horizon_color, depth)
        if y % 2:
            color = shade(color, 0.55)
        return shade(color, 0.92 + 0.12 * math.sin(t * 9.1 + y * 0.3))


class Sunset(Backdrop):
    stripe = (255, 140, 90)

    def row_color(self, theme, depth, y, t, pulse):
        color = lerp(theme.horizon_color, theme.background_color, depth)
        if depth < 0.45 and int(y + t * 2) % 3 == 0:
            color = lerp(color, self.stripe, 0.22)
        return color
