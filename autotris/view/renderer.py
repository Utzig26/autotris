"""Puts one frame together."""
from __future__ import annotations

import math

from ..theming.backdrops import AmbientField
from .board_view import BoardView
from .hud import Hud, StatusLine
from .layout import Layout
from .overlays import Banner, HelpCard, Particles, PauseMark, Toast
from .widget import Scene


class Renderer:
    def __init__(self, rng):
        self.rng = rng
        self.field = AmbientField(rng)
        self.board = BoardView()
        self.hud = Hud()
        self.overlays = [Particles(), Banner(), StatusLine(), Toast(), PauseMark(), HelpCard()]

    def reseed(self):
        self.field.reseed(self.rng)

    def draw(self, canvas, session, t):
        theme = session.theme
        game = session.game
        effects = session.effects
        canvas.fill(theme.background_color)
        theme.backdrop.draw(canvas, theme, self.field, t, effects.flash)
        layout = session.layout
        if effects.shake:
            layout.shift(int(round(math.sin(t * 61) * effects.shake)),
                         int(round(math.cos(t * 47) * effects.shake * 0.5)))
        scene = Scene(game=game, theme=theme, layout=layout, effects=effects,
                      session=session, t=t)
        self.hud.draw(canvas, scene)
        self.board.draw(canvas, scene)
        for overlay in self.overlays:
            overlay.draw(canvas, scene)
