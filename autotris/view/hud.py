"""Title, side panels and the status line."""
from __future__ import annotations

import math

from ..display.color import lerp, shade
from .layout import LEFT_WIDTH, RIGHT_WIDTH
from .panels import BrainPanel, HoldPanel, QueuePanel, StackPanel, StatsPanel
from .widget import Widget

TITLE = "A U T O T R I S"


class Hud(Widget):
    def __init__(self):
        self.left = [HoldPanel(), StatsPanel(), StackPanel()]
        self.right = [QueuePanel(), BrainPanel()]

    def draw(self, canvas, scene):
        if scene.layout.zen:
            return
        self._title(canvas, scene)
        self._stack(canvas, scene, self.left, scene.layout.left_x, LEFT_WIDTH)
        self._stack(canvas, scene, self.right, scene.layout.right_x, RIGHT_WIDTH)

    def _title(self, canvas, scene):
        layout, theme = scene.layout, scene.theme
        start = layout.x + (layout.width - len(TITLE)) // 2
        for index, char in enumerate(TITLE):
            canvas.put(start + index, layout.y, char,
                       lerp(theme.accent, theme.highlight,
                            (math.sin(scene.t * 1.8 + index * 0.35) + 1) / 2))
        subtitle = (theme.name + " · " + theme.tagline)[:layout.width]
        canvas.centered(layout.x + layout.width // 2, layout.y + 1, subtitle,
                        shade(theme.muted, 1.15))

    def _stack(self, canvas, scene, panels, x, width):
        y = scene.layout.panel_y
        for panel in panels:
            panel.place(x, y, width).draw(canvas, scene)
            y += panel.height

class StatusLine(Widget):
    """Ticker and footer, drawn last so particles fly behind them."""

    def draw(self, canvas, scene):
        if scene.layout.zen:
            return
        layout, theme, session = scene.layout, scene.theme, scene.session
        ticker = "  ".join(entry[0] for entry in scene.effects.ticker[-2:])
        canvas.centered(layout.x + layout.width // 2, layout.y + layout.height - 2,
                        ticker[:layout.width], shade(theme.highlight, 0.9))
        canvas.centered(layout.x + layout.width // 2, layout.y + layout.height - 1,
                        session.status_line(theme, layout)[:layout.width],
                        shade(theme.muted, 0.85))
