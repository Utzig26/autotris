"""Backdrops with something moving in them."""
from __future__ import annotations

import math

from ...display import canvas as canvas_module
from ...display.color import lerp, shade
from ..blocks import GLYPHS
from .base import Backdrop
from .simple import Gradient


class Starfield(Gradient):
    def overlay(self, canvas, theme, field, t):
        for x_ratio, y_ratio, phase in field.stars:
            twinkle = 0.5 + 0.5 * math.sin(t * 2.2 + phase)
            if twinkle <= 0.55:
                continue
            char = "·" if twinkle < 0.85 else "✦"
            canvas.put(int(x_ratio * canvas.width), int(y_ratio * canvas.height),
                       char, shade(theme.highlight, 0.25 + twinkle * 0.5))


class GlyphRain(Gradient):
    def overlay(self, canvas, theme, field, t):
        plain = canvas_module.ascii_only()
        for drop in field.rain:
            drop[0] = (drop[0] + drop[1]) % (canvas.height + 24)
            x = drop[2] % canvas.width
            head = int(drop[0])
            length = drop[3]
            for offset in range(length):
                y = head - offset
                if not 0 <= y < canvas.height:
                    continue
                tint = shade(theme.accent, max(0.04, 0.55 - offset * (0.5 / length)))
                if offset == 0:
                    tint = shade(theme.highlight, 0.75)
                char = "01"[(x + y) % 2] if plain else GLYPHS[(x * 3 + y * 5 + int(t * 8)) % len(GLYPHS)]
                canvas.put(x, y, char, tint)


class Gears(Backdrop):
    teeth_plain = "+x*"
    teeth = "╬✳❋"

    def row_color(self, theme, depth, y, t, pulse):
        return lerp(theme.background_color, theme.horizon_color, depth * (0.7 + 0.3 * pulse))

    def overlay(self, canvas, theme, field, t):
        plain = canvas_module.ascii_only()
        teeth = self.teeth_plain if plain else self.teeth
        for x_ratio, y_ratio, radius, speed in field.gears:
            cx, cy = x_ratio * canvas.width, y_ratio * canvas.height
            count = int(radius * 3)
            for i in range(count):
                angle = math.tau * i / count + t * speed
                canvas.put(int(cx + math.cos(angle) * radius * 2),
                           int(cy + math.sin(angle) * radius),
                           teeth[i % len(teeth)], shade(theme.muted, 0.55))
            canvas.put(int(cx), int(cy), "o" if plain else "◎", shade(theme.muted, 0.7))
        for index, (x_ratio, y_ratio, speed) in enumerate(field.steam):
            y = int((y_ratio * canvas.height - t * speed * 4) % canvas.height)
            x = int((x_ratio * canvas.width + math.sin(t * 0.7 + index) * 2) % canvas.width)
            canvas.put(x, y, "·" if plain else "°", shade(theme.foreground, 0.18))
