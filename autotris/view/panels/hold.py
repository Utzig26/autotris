from __future__ import annotations

from ..pieces_preview import draw_piece
from ..widget import Panel


class HoldPanel(Panel):
    title = "HOLD"
    height = 5

    def border_color(self, scene):
        return scene.theme.highlight if scene.session.hold_flash else scene.theme.muted

    def contents(self, canvas, scene):
        draw_piece(canvas, scene.game.hold, self.x + 2, self.y + 2, self.width - 4,
                   scene.theme, scene.t, dim=not scene.session.hold_flash)
