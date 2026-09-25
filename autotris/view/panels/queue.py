from __future__ import annotations

from ..pieces_preview import draw_piece
from ..widget import Panel

PREVIEW_COUNT = 4
PREVIEW_SPACING = 3


class QueuePanel(Panel):
    title = "NEXT"
    height = 14

    def contents(self, canvas, scene):
        for index, name in enumerate(scene.game.bag.peek(PREVIEW_COUNT)):
            draw_piece(canvas, name, self.x + 2, self.y + 2 + index * PREVIEW_SPACING,
                       self.width - 4, scene.theme, scene.t)
