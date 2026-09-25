"""Anything that draws itself onto the canvas."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Scene:
    """Everything a widget is allowed to look at."""
    game: object
    theme: object
    layout: object
    effects: object
    session: object
    t: float


class Widget(ABC):
    @abstractmethod
    def draw(self, canvas, scene):
        ...


class Panel(Widget):
    """A framed box of fixed height, stacked in a column by the HUD."""

    title = ""
    height = 3

    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 0

    def place(self, x, y, width):
        self.x, self.y, self.width = x, y, width
        return self

    def draw(self, canvas, scene):
        theme = scene.theme
        canvas.frame(self.x, self.y, self.width, self.height,
                     self.border_color(scene), theme.frame_chars,
                     self.title, theme.accent, fill=self.fill_color(scene))
        self.contents(canvas, scene)

    def border_color(self, scene):
        return scene.theme.muted

    def fill_color(self, scene):
        from ..display.color import shade
        theme = scene.theme
        return shade(theme.background_color, 0.94 if theme.light else 1.35)

    @abstractmethod
    def contents(self, canvas, scene):
        ...
