"""Particles, shake, flashes and the banner, driven by game events."""
from __future__ import annotations

import math

from ..core import events as ev
from ..display.color import shade

TRAIL_LIFE = 9
SHAKE_DECAY = 0.80
FLASH_DECAY = 0.72
TICKER_LIFE = 90


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "span", "char", "color", "gravity")

    def __init__(self, x, y, vx, vy, life, char, color, gravity=0.035):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.span = life
        self.char, self.color, self.gravity = char, color, gravity

    def advance(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1


class Effects:
    def __init__(self, rng):
        self.rng = rng
        self.particles = []
        self.trails = []
        self.rings = []
        self.shake = 0.0
        self.flash = 0.0
        self.banner = None
        self.ticker = []

    def announce(self, text, life=34):
        self.banner = [text, life, life]

    def log(self, text):
        self.ticker.append([text, TICKER_LIFE])
        if len(self.ticker) > 4:
            self.ticker.pop(0)

    def update(self, events, theme, layout, game):
        self._react(events, theme, game)
        self._advance()
        self._emit(events, theme, layout, game)

    def _react(self, events, theme, game):
        for event in events:
            if isinstance(event, ev.GameStarted):
                self.log("new game")
            elif isinstance(event, ev.PieceFell):
                for x, y in event.cells:
                    for row in range(max(0, event.from_row), y):
                        self.trails.append([x, row, TRAIL_LIFE, event.name])
            elif isinstance(event, ev.PieceLocked):
                self.shake = max(self.shake, 0.6 + event.rows_cleared * 1.5)
            elif isinstance(event, ev.LevelReached):
                self.log("LEVEL %d" % event.level)
            elif isinstance(event, ev.RowsCleared):
                self._celebrate(event)
            elif isinstance(event, ev.ToppedOut):
                self.announce("GAME OVER", 60)
                self.log("topped out · restarting")

    def _celebrate(self, event):
        if event.perfect:
            self.announce("PERFECT CLEAR", 48)
            self.log("PERFECT CLEAR")
        elif event.count == 4:
            self.announce("__TETRIS__", 42)
            self.log("TETRIS +%d" % event.gain)
        elif event.combo >= 2:
            self.announce("COMBO x%d" % event.combo, 26)

    def _advance(self):
        for particle in self.particles:
            particle.advance()
        self.particles = [p for p in self.particles if p.life > 0 and -2 < p.y < 200]
        self.trails = [[x, y, age - 1, name] for x, y, age, name in self.trails if age > 1]
        self.flash *= FLASH_DECAY
        if self.flash < 0.01:
            self.flash = 0.0
        self.shake *= SHAKE_DECAY
        if self.shake < 0.05:
            self.shake = 0.0
        if self.banner:
            self.banner[1] -= 1
            if self.banner[1] <= 0:
                self.banner = None
        for ring in self.rings:
            ring[2] += 1.35
            ring[3] -= 1
        self.rings = [r for r in self.rings if r[3] > 0]
        for entry in self.ticker:
            entry[1] -= 1
        self.ticker = [e for e in self.ticker if e[1] > 0]

    def _emit(self, events, theme, layout, game):
        for event in events:
            if isinstance(event, ev.PieceSettled):
                self._dust(event, theme, layout)
            elif isinstance(event, ev.RowsIgnited):
                self._burst_rows(event, theme, layout)

    def _center(self, layout, column, row):
        scale = layout.scale
        return (layout.cell_x(column) + scale - 1, layout.cell_y(row) + (scale - 1) // 2)

    def _dust(self, event, theme, layout):
        cells = [c for c in event.cells if c[1] >= 0]
        if not cells:
            return
        floor = max(y for _, y in cells)
        for column, row in cells:
            if row != floor:
                continue
            x, y = self._center(layout, column, row)
            for direction in (-1, 1):
                self.particles.append(Particle(
                    x, y, direction * self.rng.uniform(0.5, 1.4),
                    -self.rng.uniform(0.05, 0.3), self.rng.randint(7, 13),
                    self.rng.choice(list(theme.particles)), theme.palette[event.name], 0.06))

    def _burst_rows(self, event, theme, layout):
        count = len(event.rows)
        for index, row in enumerate(event.rows):
            for column, name in enumerate(event.names[index]):
                x, y = self._center(layout, column, row)
                self.scatter(x, y, 3 if count < 4 else 5,
                             [theme.palette[name or "I"], theme.foreground, theme.accent],
                             list(theme.particles), 1.0 + 0.3 * count, 20, 0.04)
        middle = self._center(layout, 0, int(sum(event.rows) / count))[1]
        if count >= 3:
            self.rings.append([layout.board_x + layout.board_width / 2, middle, 1.0, 14])
        if count == 4:
            self.rings.append([layout.board_x + layout.board_width / 2, middle, 0.5, 20])
            self.flash = 0.55
        elif count == 3:
            self.flash = 0.22

    def scatter(self, x, y, amount, colors, chars, speed=0.8, life=22, gravity=0.035):
        for _ in range(amount):
            angle = self.rng.uniform(0, math.tau)
            magnitude = self.rng.uniform(0.25, 1.0) * speed
            self.particles.append(Particle(
                x, y, math.cos(angle) * magnitude * 1.9, math.sin(angle) * magnitude,
                int(life * self.rng.uniform(0.6, 1.2)),
                self.rng.choice(chars), self.rng.choice(colors), gravity))
