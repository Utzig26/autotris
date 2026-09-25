"""How a theme paints one cell of the board."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..display import canvas as canvas_module
from ..display.color import lerp, shade

GLYPHS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽﾊﾋﾜ01"
WHITE = (255, 255, 255)


class Ghost(ABC):
    """Draws the preview of where the piece will land."""

    @abstractmethod
    def draw(self, canvas, x, y, scale, color, style):
        ...


class ShadeGhost(Ghost):
    factor = 0.30

    def draw(self, canvas, x, y, scale, color, style):
        char = ":" if canvas_module.ascii_only() else style.glyph(x, y, 0.0)
        tint = shade(color, self.factor)
        for j in range(scale):
            for i in range(2 * scale):
                canvas.put(x + i, y + j, char, tint)


class DottedGhost(Ghost):
    def draw(self, canvas, x, y, scale, color, style):
        char = ":" if canvas_module.ascii_only() else "░"
        tint = shade(color, 0.45)
        for j in range(scale):
            for i in range(2 * scale):
                canvas.put(x + i, y + j, char, tint)


class OutlineGhost(Ghost):
    def draw(self, canvas, x, y, scale, color, style):
        width, height = 2 * scale, scale
        tint = shade(color, 0.55)
        plain = canvas_module.ascii_only()
        for j in range(height):
            for i in range(width):
                if not (i == 0 or i == width - 1 or j == 0 or j == height - 1):
                    continue
                if plain:
                    char = "+"
                elif i == 0:
                    char = "▏"
                elif i == width - 1:
                    char = "▕"
                else:
                    char = "▁"
                canvas.put(x + i, y + j, char, tint)


class BlockStyle(ABC):
    """Paints a filled cell; subclasses change the glyph and the shading."""

    bevelled = True
    ghost = ShadeGhost()

    @abstractmethod
    def glyph(self, x, y, t):
        ...

    def background(self, color, mode):
        return None

    def draw(self, canvas, x, y, scale, color, theme, mode="solid", boost=0.0, t=0.0):
        if mode == "ghost":
            return self.ghost.draw(canvas, x, y, scale, color, self)
        if mode == "flash":
            color = WHITE if not theme.light else (40, 40, 48)
        elif mode == "dead":
            faded = shade(color, 0.30)
            color = (int(faded[0] * .5 + 70), int(faded[1] * .5 + 70), int(faded[2] * .5 + 75))
        elif boost:
            color = lerp(color, WHITE, boost)
        flat = not self.bevelled or mode in ("flash", "dead")
        width, height = 2 * scale, scale
        bg = self.background(color, mode)
        for j in range(height):
            for i in range(width):
                char = self.glyph(x + i, y + j, t)
                if flat:
                    tint = color
                else:
                    factor = 1.0
                    if j == 0:
                        factor *= 1.20
                    if i == 0:
                        factor *= 1.10
                    if j == height - 1:
                        factor *= 0.74
                    if i == width - 1:
                        factor *= 0.86
                    tint = theme.lighten(color, factor) if factor >= 1.0 else theme.darken(color, factor)
                canvas.put(x + i, y + j, char, tint, bg)
        self.decorate(canvas, x, y, scale, color, theme, mode)

    def decorate(self, canvas, x, y, scale, color, theme, mode):
        pass


class SolidBlocks(BlockStyle):
    def __init__(self, bevelled=True, ghost=None):
        self.bevelled = bevelled
        if ghost is not None:
            self.ghost = ghost

    def glyph(self, x, y, t):
        return "#" if canvas_module.ascii_only() else "█"


class ShadedBlocks(BlockStyle):
    ghost = DottedGhost()

    def glyph(self, x, y, t):
        return "#" if canvas_module.ascii_only() else "▓"


class DottedBlocks(BlockStyle):
    def glyph(self, x, y, t):
        return "#" if canvas_module.ascii_only() else "▒"


class GlyphBlocks(BlockStyle):
    """Cells made of drifting characters, with a dim wash so they read as solid."""

    ghost = DottedGhost()

    def glyph(self, x, y, t):
        if canvas_module.ascii_only():
            return "#"
        return GLYPHS[(x * 7 + y * 13 + int(t * 6)) % len(GLYPHS)]

    def background(self, color, mode):
        return shade(color, 0.22) if mode == "solid" else None


class RivetBlocks(SolidBlocks):
    def decorate(self, canvas, x, y, scale, color, theme, mode):
        if scale >= 2 and mode == "solid" and not canvas_module.ascii_only():
            canvas.put(x + scale - 1, y + scale // 2, "•", theme.lighten(color, 1.45))
