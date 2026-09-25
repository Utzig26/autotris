"""A theme: palette, block style, frame characters and a background."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..display import canvas as canvas_module
from ..display.color import shade
from . import frames


@dataclass
class Theme:
    key: str
    name: str
    tagline: str
    palette: dict
    background_color: tuple
    horizon_color: tuple
    foreground: tuple
    muted: tuple
    accent: tuple
    highlight: tuple
    blocks: object
    backdrop: object
    frame: str = frames.THIN
    grid_dot: str = ""
    particles: tuple = ("*", "+", ".")
    faces: bool = False
    light: bool = False
    group: str = "builtin"
    tetris_word: str = "T E T R I S"

    @property
    def frame_chars(self):
        return frames.PLAIN if canvas_module.ascii_only() else self.frame

    def lighten(self, color, factor=1.18):
        return shade(color, (2.0 - factor) if self.light else factor)

    def darken(self, color, factor=0.72):
        return shade(color, (2.0 - factor) if self.light else factor)
