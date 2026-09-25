"""Draws a piece at scale one, centred in a panel."""
from __future__ import annotations

from ..core.tetromino import PIECES
from ..display import canvas as canvas_module
from ..display.color import shade


def draw_piece(canvas, name, x, y, width, theme, t, dim=False):
    if name is None:
        return
    rotation = PIECES[name][0]
    cells = rotation.cells
    left = min(cx for cx, _ in cells)
    top = min(cy for _, cy in cells)
    origin_x = x + (width - rotation.width * 2) // 2 - left * 2
    origin_y = y - top
    for cx, cy in cells:
        px, py = origin_x + cx * 2, origin_y + cy
        if dim:
            tint = shade(theme.palette[name], 0.35)
            char = "#" if canvas_module.ascii_only() else "█"
            canvas.put(px, py, char, tint)
            canvas.put(px + 1, py, char, tint)
        else:
            theme.blocks.draw(canvas, px, py, 1, theme.palette[name], theme, t=t)
