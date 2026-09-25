from __future__ import annotations

from ...display import canvas as canvas_module
from ...display.color import shade
from ..widget import Panel

SHOWN = 3


class BrainPanel(Panel):
    """The chosen move and how the runners-up scored."""

    title = "BRAIN"
    height = 8

    def contents(self, canvas, scene):
        game, theme = scene.game, scene.theme
        canvas.centered(self.x + self.width // 2, self.y + 1, game.brain.label, theme.highlight)
        move = game.move
        if move:
            canvas.text(self.x + 2, self.y + 2, "rot %d  col %-2d %s" % (
                move.rotation, move.column + 1, "H" if move.hold else " "), theme.foreground)
        self._bars(canvas, scene)

    def _bars(self, canvas, scene):
        theme = scene.theme
        ranked = scene.game.ranked[:SHOWN]
        scores = [option.score for option in ranked] or [0]
        low, high = min(scores), max(scores)
        width = self.width - 10
        plain = canvas_module.ascii_only()
        for index, option in enumerate(ranked):
            ratio = 1.0 if high == low else (option.score - low) / (high - low) * 0.7 + 0.3
            filled = max(1, int(width * ratio))
            color = theme.accent if index == 0 else shade(theme.muted, 1.5)
            for step in range(width):
                char = "█" if step < filled else ("." if plain else "░")
                canvas.put(self.x + 2 + step, self.y + 4 + index, char,
                           color if step < filled else shade(theme.muted, 0.55))
            canvas.text(self.x + self.width - 7, self.y + 4 + index,
                        "%5.0f" % option.score, shade(theme.muted, 1.2))
