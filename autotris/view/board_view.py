"""The playfield itself: stack, ghost, live piece, trails."""
from __future__ import annotations

import math

from ..core import game as states
from ..core.tetromino import cells_at
from ..display import canvas as canvas_module
from ..display.color import lerp, shade
from .widget import Widget

DANGER = (255, 60, 60)
CLEAR_FRAMES = 14
FACE_COLOR = (30, 20, 40)


class BoardView(Widget):
    def draw(self, canvas, scene):
        game, theme, layout = scene.game, scene.theme, scene.layout
        board = game.board
        pulse = 0.55 + 0.45 * math.sin(scene.t * 2.0)
        border = lerp(shade(theme.accent, 0.45), theme.accent, pulse)
        if game.danger > 0.02:
            border = lerp(border, DANGER, game.danger * (0.45 + 0.55 * pulse))
        canvas.frame(layout.board_x, layout.board_y, layout.board_width, layout.board_height,
                     border, theme.frame_chars,
                     fill=shade(theme.background_color, 0.88 if theme.light else 1.18))
        self._stack(canvas, scene)
        self._trails(canvas, scene)
        self._live(canvas, scene)

    def _stack(self, canvas, scene):
        game, theme, layout = scene.game, scene.theme, scene.layout
        board = game.board
        clearing = game.state == states.CLEARING
        phase = game.timer / CLEAR_FRAMES
        middle = (board.columns - 1) / 2
        reach = board.columns / 2
        well = game.brain.well
        marked = game.brain.stacking
        scale = layout.scale
        plain = canvas_module.ascii_only()
        for row in range(board.rows):
            for column in range(board.columns):
                x, y = layout.cell_x(column), layout.cell_y(row)
                name = board.cells[row][column]
                if name is None:
                    if column == well and marked:
                        for j in range(scale):
                            canvas.put(x + 2 * scale - 1, y + j, "|" if plain else "▕",
                                       shade(theme.muted, 0.35))
                    if theme.grid_dot:
                        canvas.put(x + scale - 1, y + (scale - 1) // 2,
                                   "." if plain else theme.grid_dot, shade(theme.muted, 0.42))
                    continue
                if game.state == states.FINISHED and row >= board.rows - game.dead_rows:
                    mode = "dead"
                elif clearing and row in game.clearing_rows:
                    if phase > abs(column - middle) / reach:
                        continue
                    mode = "flash"
                else:
                    mode = "solid"
                theme.blocks.draw(canvas, x, y, scale, theme.palette[name], theme,
                                  mode=mode, t=scene.t)

    def _trails(self, canvas, scene):
        theme, layout = scene.theme, scene.layout
        rows = scene.game.board.rows
        scale = layout.scale
        plain = canvas_module.ascii_only()
        for column, row, age, name in scene.effects.trails:
            if not 0 <= row < rows:
                continue
            color = shade(theme.palette[name], 0.18 + 0.07 * age)
            char = "|" if plain else ("│" if age < 6 else "║")
            x, y = layout.cell_x(column), layout.cell_y(row)
            for j in range(scale):
                canvas.put(x + scale - 1, y + j, char, color)
                canvas.put(x + scale, y + j, char, shade(color, 0.6))

    def _live(self, canvas, scene):
        game, theme, layout = scene.game, scene.theme, scene.layout
        if game.state in (states.PLACING, states.DROPPING) and game.name:
            if game.state == states.PLACING:
                for column, row in cells_at(game.name, game.rotation, game.x, game.ghost_row):
                    if row >= 0:
                        theme.blocks.draw(canvas, layout.cell_x(column), layout.cell_y(row),
                                          layout.scale, theme.palette[game.name], theme,
                                          mode="ghost", t=scene.t)
            boost = 0.35 if game.state == states.DROPPING else 0.10 + 0.10 * math.sin(scene.t * 9)
            cells = game.cells
            face_cell = cells[len(cells) // 2]
            for column, row in cells:
                if row < 0:
                    continue
                x, y = layout.cell_x(column), layout.cell_y(row)
                theme.blocks.draw(canvas, x, y, layout.scale, theme.palette[game.name],
                                  theme, boost=boost, t=scene.t)
                if theme.faces and (column, row) == face_cell and not canvas_module.ascii_only():
                    eyes = ("^", "^") if game.state == states.DROPPING else ("•", "•")
                    canvas.put(x + layout.scale - 1, y + (layout.scale - 1) // 2, eyes[0], FACE_COLOR)
                    canvas.put(x + layout.scale, y + (layout.scale - 1) // 2, eyes[1], FACE_COLOR)
        if game.state == states.SETTLING:
            for column, row in game.settled_cells:
                if row >= 0:
                    theme.blocks.draw(canvas, layout.cell_x(column), layout.cell_y(row),
                                      layout.scale, theme.palette[game.name], theme,
                                      mode="flash", t=scene.t)
