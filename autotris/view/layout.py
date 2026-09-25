"""Where everything sits on the canvas."""
from __future__ import annotations

LEFT_WIDTH = 16
RIGHT_WIDTH = 18
GAP = 1
PANEL_HEIGHT = 22
CHROME_HEIGHT = 4
MAX_SCALE = 6


class Layout:
    def __init__(self, canvas_width, canvas_height, board, scale, zen):
        self.scale = scale
        self.zen = zen
        self.board_width = board.columns * 2 * scale + 2
        self.board_height = board.rows * scale + 2
        if zen:
            self.width, self.height = self.board_width, self.board_height
        else:
            self.width = LEFT_WIDTH + GAP + self.board_width + GAP + RIGHT_WIDTH
            self.height = max(self.board_height, PANEL_HEIGHT) + CHROME_HEIGHT
        self.x = (canvas_width - self.width) // 2
        self.y = (canvas_height - self.height) // 2
        if zen:
            self.board_x, self.board_y = self.x, self.y
        else:
            self.board_x = self.x + LEFT_WIDTH + GAP
            self.board_y = self.y + 2
        self.left_x = self.x
        self.right_x = self.board_x + self.board_width + GAP
        self.panel_y = self.board_y

    def fits(self, canvas_width, canvas_height):
        return self.width <= canvas_width and self.height <= canvas_height

    def shift(self, dx, dy):
        for attribute in ("x", "y", "board_x", "board_y", "left_x", "right_x", "panel_y"):
            setattr(self, attribute, getattr(self, attribute) + (dx if "x" in attribute else dy))

    @property
    def board_center_x(self):
        return self.board_x + self.board_width // 2

    @property
    def board_center_y(self):
        return self.board_y + self.board_height // 2

    def cell_x(self, column):
        return self.board_x + 1 + column * 2 * self.scale

    def cell_y(self, row):
        return self.board_y + 1 + row * self.scale


def largest_scale(canvas_width, canvas_height, board, zen):
    scale = 1
    while scale < MAX_SCALE and Layout(canvas_width, canvas_height, board,
                                       scale + 1, zen).fits(canvas_width, canvas_height):
        scale += 1
    return scale
