"""Things drawn on top of everything else."""
from __future__ import annotations

import math

from ..display import canvas as canvas_module
from ..display.color import lerp, shade
from .widget import Widget

TETRIS_TOKEN = "__TETRIS__"


class Particles(Widget):
    def draw(self, canvas, scene):
        theme = scene.theme
        for ring_x, ring_y, radius, life in scene.effects.rings:
            steps = max(8, int(radius * 5))
            for i in range(steps):
                angle = math.tau * i / steps
                color = lerp(theme.accent, theme.highlight,
                             (math.sin(angle + scene.t) + 1) / 2)
                canvas.put(int(ring_x + math.cos(angle) * radius * 2),
                           int(ring_y + math.sin(angle) * radius * 0.75),
                           "·" if life < 6 else ("*" if canvas_module.ascii_only() else "•"),
                           shade(color, max(0.15, life / 14)))
        for particle in scene.effects.particles:
            canvas.put(int(particle.x), int(particle.y), particle.char,
                       shade(particle.color or theme.accent,
                             0.25 + 0.75 * particle.life / max(1, particle.span)))


class Banner(Widget):
    """The headline that slides in when something big happens."""

    def draw(self, canvas, scene):
        banner = scene.effects.banner
        if not banner:
            return
        text, life, span = banner
        theme, layout = scene.theme, scene.layout
        ratio = life / span
        word = theme.tetris_word if text == TETRIS_TOKEN else text
        inner = layout.board_width - 2
        word = word[:inner - 2]
        slide = int((1 - min(1.0, (1 - ratio) * 4)) * 3) - int(max(0.0, (0.35 - ratio) * 8))
        top = layout.board_y + 1 + max(0, layout.board_height // 5) + slide
        fade = min(1.0, ratio * 3.5)
        plate = shade(theme.background_color, 0.45 if not theme.light else 1.4)
        canvas.wash(layout.board_x + 1, top, inner, 3, plate)
        rule = "-" if canvas_module.ascii_only() else "─"
        for i in range(inner):
            color = lerp(theme.accent, theme.highlight, (math.sin(scene.t * 3 + i * 0.25) + 1) / 2)
            canvas.put(layout.board_x + 1 + i, top, rule, shade(color, 0.35 + 0.45 * fade), plate)
            canvas.put(layout.board_x + 1 + i, top + 2, rule, shade(color, 0.35 + 0.45 * fade), plate)
        start = layout.board_x + 1 + (inner - len(word)) // 2
        for i, char in enumerate(word):
            color = lerp(theme.accent, theme.highlight, (math.sin(scene.t * 4 + i * 0.4) + 1) / 2)
            canvas.put(start + i, top + 1, char, shade(color, 0.3 + 0.7 * fade), plate)


class Toast(Widget):
    def draw(self, canvas, scene):
        toast = scene.session.toast
        if not toast:
            return
        layout, theme = scene.layout, scene.theme
        y = layout.y + layout.height + (1 if layout.zen else 0)
        canvas.centered(canvas.width // 2, min(canvas.height - 1, y), " %s " % toast[0],
                        shade(theme.background_color, 0.3), theme.accent)


class PauseMark(Widget):
    def draw(self, canvas, scene):
        if not scene.session.paused:
            return
        theme = scene.theme
        canvas.centered(scene.layout.board_center_x, scene.layout.board_center_y,
                        "  PAUSED  ", shade(theme.background_color, 0.3), theme.highlight)


class HelpCard(Widget):
    """The key list, toggled with h."""

    width = 44

    def draw(self, canvas, scene):
        if not scene.session.help_visible:
            return
        theme, session = scene.theme, scene.session
        lines = session.help_lines()
        height = len(lines) + 4
        x = (canvas.width - self.width) // 2
        y = (canvas.height - height) // 2
        canvas.frame(x, y, self.width, height, theme.accent, theme.frame_chars,
                     "CONTROLS", theme.highlight,
                     fill=shade(theme.background_color, 1.45 if not theme.light else 0.92))
        for index, (keys, description) in enumerate(lines):
            canvas.text(x + 3, y + 2 + index, keys.ljust(7), theme.highlight)
            canvas.text(x + 11, y + 2 + index, description[:self.width - 13], theme.foreground)
        canvas.centered(x + self.width // 2, y + height - 1,
                        " %d themes · %s " % (session.theme_count, theme.name), theme.muted)
