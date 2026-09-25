from __future__ import annotations

from ...ai.brain import DIGGING, PANIC, STACKING
from ...display import canvas as canvas_module
from ...display.color import shade
from ..widget import Panel

DANGER = (255, 90, 80)
READY_SLOTS = 4


class StackPanel(Panel):
    """What the AI is doing right now: stacking, digging or panicking."""

    title = "STACK"
    height = 6

    def contents(self, canvas, scene):
        game, theme = scene.game, scene.theme
        brain = game.brain
        mode = brain.mode
        if mode == PANIC:
            color = DANGER
        elif mode == STACKING:
            color = theme.accent
        elif mode == DIGGING:
            color = theme.highlight
        else:
            color = theme.muted
        canvas.centered(self.x + self.width // 2, self.y + 1, mode, color)
        ready = min(READY_SLOTS, game.ready_rows)
        canvas.text(self.x + 2, self.y + 2, "ready", theme.muted)
        plain = canvas_module.ascii_only()
        for slot in range(READY_SLOTS):
            filled = slot < ready
            char = ("#" if filled else ".") if plain else ("▰" if filled else "▱")
            canvas.put(self.x + self.width - 6 + slot, self.y + 2, char,
                       theme.highlight if filled else shade(theme.muted, 0.6))
        canvas.text(self.x + 2, self.y + 3, "well", theme.muted)
        well = "col %-2d" % (brain.well + 1)
        canvas.text(self.x + self.width - 2 - 6, self.y + 3, well, theme.foreground)
        scoring = game.scoring
        streak = "b2b %d  combo %d" % (scoring.back_to_back, max(0, scoring.combo))
        hot = scoring.back_to_back or scoring.combo > 0
        canvas.centered(self.x + self.width // 2, self.y + 4, streak,
                        theme.foreground if hot else theme.muted)
