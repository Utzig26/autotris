#!/usr/bin/env python3
"""autotris - a tetris that plays itself, built to be left running on a screen.

Keys: h help · z zen · t theme · c auto-cycle · o follow desktop
      i AI · [ ] speed · + - block size · arrows board size · r restart · q quit
"""
from __future__ import annotations
import argparse
import math
import os
import random
import select
import signal
import sys
import termios
import time
import tty

import engine as E
import omarchy
import render
import themes as T
from render import Canvas, lerp, shade
from themes import draw_cell, draw_empty

FPS = 30


def term_size():
    try:
        c, r = os.get_terminal_size()
        if c > 10 and r > 6:
            return c, r
    except OSError:
        pass
    return (int(os.environ.get("COLUMNS", 100)), int(os.environ.get("LINES", 34)))
LW, RW, GAP = 16, 18, 1
PANEL_H = 22


# ------------------------------------------------------------------ layout

class Layout:
    def __init__(self, cw, ch, scale, zen):
        self.s = s = scale
        self.zen = zen
        self.bw = E.COLS * 2 * s + 2
        self.bh = E.ROWS * s + 2
        if zen:
            self.w, self.h = self.bw, self.bh
        else:
            self.w = LW + GAP + self.bw + GAP + RW
            self.h = max(self.bh, PANEL_H) + 4
        self.ox = (cw - self.w) // 2
        self.oy = (ch - self.h) // 2
        if zen:
            self.bx, self.by = self.ox, self.oy
        else:
            self.bx, self.by = self.ox + LW + GAP, self.oy + 2
        self.lx = self.ox
        self.rx = self.bx + self.bw + GAP

    def fits(self, cw, ch):
        return self.w <= cw and self.h <= ch


def fit_scale(cw, ch, zen, want):
    for s in range(max(1, want), 0, -1):
        if Layout(cw, ch, s, zen).fits(cw, ch):
            return s
    return 1


def max_scale(cw, ch, zen):
    s = 1
    while s < 6 and Layout(cw, ch, s + 1, zen).fits(cw, ch):
        s += 1
    return s


# ----------------------------------------------------------------- effects

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "ch", "col", "grav")

    def __init__(self, x, y, vx, vy, life, ch, col, grav=0.035):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.ch, self.col, self.grav = ch, col, grav

    def step(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.grav
        self.life -= 1


class Fx:
    def __init__(self):
        self.parts = []
        self.trails = []
        self.shake = 0.0
        self.banner = None
        self.ring = []
        self.ticker = []
        self.flash = 0.0

    def burst(self, x, y, n, cols, chars, spd=0.8, life=22, grav=0.035, rng=random):
        for _ in range(n):
            a = rng.uniform(0, math.tau)
            sp = rng.uniform(0.25, 1.0) * spd
            self.parts.append(Particle(x, y, math.cos(a) * sp * 1.9, math.sin(a) * sp,
                                       int(life * rng.uniform(0.6, 1.2)),
                                       rng.choice(chars), rng.choice(cols), grav))

    def say(self, text, life=34):
        self.banner = [text, life, life]

    def log(self, text):
        self.ticker.append([text, 90])
        if len(self.ticker) > 4:
            self.ticker.pop(0)

    def step(self):
        for p in self.parts:
            p.step()
        self.parts = [p for p in self.parts if p.life > 0 and -2 < p.y < 200]
        self.trails = [[x, y, a - 1, c] for x, y, a, c in self.trails if a > 1]
        self.flash *= 0.72
        if self.flash < 0.01:
            self.flash = 0.0
        self.shake *= 0.80
        if self.shake < 0.05:
            self.shake = 0.0
        if self.banner:
            self.banner[1] -= 1
            if self.banner[1] <= 0:
                self.banner = None
        for r in self.ring:
            r[2] += 1.35
            r[3] -= 1
        self.ring = [r for r in self.ring if r[3] > 0]
        for t in self.ticker:
            t[1] -= 1
        self.ticker = [t for t in self.ticker if t[1] > 0]


# -------------------------------------------------------------------- game

class Game:
    def __init__(self, rng, speed=1.0, iq=4):
        self.rng = rng
        self.speed = speed
        self.fx = Fx()
        self.brain = E.Brain(iq, rng)
        self.reset()

    def reset(self):
        self.grid = E.new_grid()
        self.brain.well = E.default_well()
        self.brain.panic = False
        self.bag = E.Bag(self.rng)
        self.hold = None
        self.score = self.lines = self.pieces = self.tetrises = 0
        self.level = 1
        self.combo = -1
        self.b2b = 0
        self.t0 = time.monotonic()
        self.top3 = []
        self.plan = []
        self.kind = None
        self.move = None
        self.dead_rows = 0
        self.frame = 0
        self.state = "spawn"
        self.timer = 0
        self.clear_rows = []
        self.lock_cells = []
        self.hold_flash = 0
        self.danger = 0.0
        self.fx.log("new game")

    @property
    def elapsed(self):
        return time.monotonic() - self.t0

    @property
    def ready(self):
        return E.ready_rows(self.grid, self.brain.well)

    def cells(self):
        return E.cells_at(self.kind, self.rot, self.x, self.y)

    def ghost_y(self):
        return E.drop_y(self.grid, self.kind, self.rot, self.x, self.y)

    # -- cycle -----------------------------------------------------------
    def spawn(self):
        self.kind = self.bag.take()
        self.rot = 0
        self.x = E.spawn_x(self.kind)
        self.y = -2
        alt = self.hold if self.hold else self.bag.peek(1)[0]
        mv, top, _ = self.brain.decide(self.grid, self.kind, alt)
        self.top3 = top
        if mv is None or E.collides(self.grid, self.cells()):
            return self.die()
        self.move = mv
        self.plan = self.build_plan(mv)
        self.state = "play"
        self.timer = 0
        self.pieces += 1

    def build_plan(self, mv):
        seq = []
        if mv["hold"]:
            seq.append("hold")
            kind = mv["kind"]
            sx = E.spawn_x(kind)
        else:
            kind = self.kind
            sx = self.x
        n = len(E.ROT[kind])
        rots = ["rot"] * (mv["rot"] % n)
        dx = mv["x"] - sx
        moves = ["right" if dx > 0 else "left"] * abs(dx)
        out = list(seq)
        while rots or moves:
            if rots:
                out.append(rots.pop())
            if moves:
                out.append(moves.pop())
        return out

    def do_hold(self):
        if self.hold is None:
            self.hold = self.kind
            self.kind = self.bag.take()
        else:
            self.hold, self.kind = self.kind, self.hold
        self.rot = 0
        self.x = E.spawn_x(self.kind)
        self.hold_flash = 8

    def apply(self, tok):
        if tok == "hold":
            return self.do_hold()
        if tok == "rot":
            nr = (self.rot + 1) % len(E.ROT[self.kind])
            for kick in (0, -1, 1, -2, 2):
                if not E.collides(self.grid, E.cells_at(self.kind, nr, self.x + kick, self.y)):
                    self.rot, self.x = nr, self.x + kick
                    return
            return
        d = -1 if tok == "left" else 1
        if not E.collides(self.grid, E.cells_at(self.kind, self.rot, self.x + d, self.y)):
            self.x += d

    def lock(self):
        for cx, cy in self.cells():
            if cy >= 0:
                self.grid[cy][cx] = self.kind
        self.lock_cells = self.cells()
        rows = E.full_rows(self.grid)
        self.fx.shake = max(self.fx.shake, 0.6 + len(rows) * 1.5)
        if rows:
            self.clear_rows = rows
            self.state = "clear"
        else:
            self.combo = -1
            self.state = "lockflash"
        self.timer = 0

    def resolve_clear(self):
        n = len(self.clear_rows)
        self.grid = E.collapse(self.grid, self.clear_rows)
        self.lines += n
        self.combo += 1
        tetris = n == 4
        gain = E.SCORES[n] * self.level
        if tetris:
            self.tetrises += 1
            gain = int(gain * (1.5 if self.b2b else 1.0))
            self.b2b += 1
        else:
            self.b2b = 0
        if self.combo > 0:
            gain += 50 * self.combo * self.level
        self.score += gain
        lvl = 1 + self.lines // 10
        if lvl != self.level:
            self.level = lvl
            self.fx.log("LEVEL %d" % lvl)
        if all(v is None for row in self.grid for v in row):
            self.fx.say("PERFECT CLEAR", 48)
            self.fx.log("PERFECT CLEAR")
        elif tetris:
            self.fx.say("__TETRIS__", 42)
            self.fx.log("TETRIS +%d" % gain)
        elif self.combo >= 2:
            self.fx.say("COMBO x%d" % self.combo, 26)
        self.clear_rows = []
        self.state = "spawn"

    def die(self):
        self.state = "over"
        self.timer = 0
        self.dead_rows = 0
        self.fx.say("GAME OVER", 60)
        self.fx.log("topped out · restarting")

    def rebase(self, old, ocols, orows):
        """Board resized: keep the stack, anchored to the bottom-left corner."""
        g = E.new_grid()
        for r in range(min(E.ROWS, orows)):
            for c in range(min(E.COLS, ocols)):
                g[E.ROWS - 1 - r][c] = old[orows - 1 - r][c]
        done = E.full_rows(g)
        if done:
            g = E.collapse(g, done)
        self.grid = g
        self.brain.well = E.default_well()
        self.brain.panic = False
        self.plan = []
        self.clear_rows = []
        self.lock_cells = []
        self.fx.trails.clear()
        self.state = "spawn"
        self.timer = 0

    def update(self):
        self.frame += 1
        self.timer += 1
        if self.hold_flash:
            self.hold_flash -= 1
        tgt = max(0.0, (max(E.height_map(self.grid)) - E.ROWS * 0.6) / (E.ROWS * 0.3))
        self.danger += (min(1.0, tgt) - self.danger) * 0.12
        s = self.speed
        st = self.state
        if st == "spawn":
            self.spawn()
        elif st == "play":
            every = max(1, int(round(2 / s)))
            if self.timer % every == 0:
                if self.plan:
                    self.apply(self.plan.pop(0))
                else:
                    self.target_y = self.ghost_y()
                    self.state = "drop"
            if self.frame % max(2, int(6 / s)) == 0 and self.y < 2:
                if not E.collides(self.grid, E.cells_at(self.kind, self.rot, self.x, self.y + 1)):
                    self.y += 1
        elif st == "drop":
            step = max(2, int(3 * s))
            prev = self.y
            self.y = min(self.target_y, self.y + step)
            for cx, cy in self.cells():
                for yy in range(max(0, prev), cy):
                    self.fx.trails.append([cx, yy, 9, self.kind])
            if self.y >= self.target_y:
                self.lock()
        elif st == "lockflash":
            if self.timer >= 2:
                self.state = "spawn"
        elif st == "clear":
            if self.timer >= max(6, int(14 / s)):
                self.resolve_clear()
        elif st == "over":
            if self.timer % 2 == 0:
                self.dead_rows += 1
            if self.dead_rows > E.ROWS + 14:
                self.reset()
        self.fx.step()


# ---------------------------------------------------------------- keyboard

class Keys:
    def __init__(self):
        self.fd = sys.stdin.fileno() if sys.stdin.isatty() else None
        self.saved = None

    def __enter__(self):
        if self.fd is not None:
            self.saved = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *a):
        if self.saved is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)

    ARROWS = {"A": "up", "B": "down", "C": "right", "D": "left"}

    @classmethod
    def parse(cls, data):
        out = []
        i = 0
        while i < len(data):
            c = data[i]
            if c == "\x1b" and data[i + 1:i + 2] == "[" and data[i + 2:i + 3] in cls.ARROWS:
                out.append(cls.ARROWS[data[i + 2]])
                i += 3
            else:
                out.append(c)
                i += 1
        return out

    def read(self):
        if self.fd is None:
            return ""
        out = ""
        while select.select([self.fd], [], [], 0)[0]:
            chunk = os.read(self.fd, 32).decode("utf-8", "ignore")
            if not chunk:
                break
            out += chunk
        return out


# --------------------------------------------------------------- transitions

class Transition:
    """Reveals the new theme on top of a snapshot of the previous frame."""
    KINDS = ("wipe", "iris", "dissolve", "blocks", "curtain", "doors", "glitch", "scan")

    def __init__(self, kind, cv, rng, frames=26):
        self.kind = kind
        self.frames = frames
        self.t = 0
        self.rng = rng
        self.snap = ([r[:] for r in cv.ch], [r[:] for r in cv.fg], [r[:] for r in cv.bg])
        self.noise = [[rng.random() for _ in range(cv.w)] for _ in range(cv.h)]
        self.cols = [rng.random() * 0.45 for _ in range(cv.w + 4)]
        self.bands = [rng.random() for _ in range(cv.h + 4)]
        self.jitter = [rng.randint(-9, 9) for _ in range(cv.h + 4)]

    @property
    def done(self):
        return self.t >= self.frames

    def metric(self, x, y, w, h):
        k = self.kind
        if k == "wipe":
            return x / max(1, w - 1)
        if k == "iris":
            dx = (x - w / 2) / (w / 2)
            dy = (y - h / 2) / (h / 2)
            return min(1.0, math.hypot(dx, dy) / 1.42)
        if k == "dissolve":
            return self.noise[y][x]
        if k == "blocks":
            return min(1.0, y / max(1, h - 1) * 0.6 + self.cols[x])
        if k == "curtain":
            return 1.0 - abs(y - h / 2) / (h / 2 + 1e-6)
        if k == "doors":
            return 1.0 - abs(x - w / 2) / (w / 2 + 1e-6)
        if k == "glitch":
            return self.bands[y]
        return ((y * 7) % max(1, h)) / max(1, h)   # scan

    def compose(self, cv, th):
        p = self.t / self.frames
        ch, fg, bg = self.snap
        w, h = cv.w, cv.h
        glitch = self.kind == "glitch"
        for y in range(h):
            off = self.jitter[y] if (glitch and p < 0.75) else 0
            for x in range(w):
                v = self.metric(x, y, w, h)
                if v <= p:
                    if abs(v - p) < 0.035:            # bright leading edge
                        cv.fg[y][x] = shade(th.bg0, 0.4)
                        cv.bg[y][x] = th.accent
                    continue
                sx = min(w - 1, max(0, x + off))
                cv.ch[y][x] = ch[y][sx]
                cv.fg[y][x] = fg[y][sx]
                cv.bg[y][x] = bg[y][sx]
        self.t += 1


# --------------------------------------------------------------- rendering

class Renderer:
    def __init__(self, cv, rng):
        self.cv = cv
        self.rng = rng
        self.seed_bg()

    def seed_bg(self):
        r = self.rng
        self.rain = [[r.uniform(0, 60), r.uniform(0.3, 1.1), r.randrange(0, 400),
                      r.randrange(4, 12)] for _ in range(55)]
        self.stars = [(r.random(), r.random(), r.uniform(0, math.tau)) for _ in range(90)]
        self.gears = [(r.random(), r.random(), r.uniform(3, 7), r.choice((-1, 1)) * r.uniform(.3, .9))
                      for _ in range(5)]
        self.steam = [(r.random(), r.random(), r.uniform(.2, .6)) for _ in range(28)]

    def background(self, th, t, flash=0.0):
        cv = self.cv
        w, h = cv.w, cv.h
        kind = th.bgkind
        pulse = 0.5 + 0.5 * math.sin(t * 0.7)
        for y in range(h):
            f = y / max(1, h - 1)
            if kind == "plain":
                col = th.bg0
            elif kind == "scan":
                col = lerp(th.bg0, th.bg1, f)
                if y % 2:
                    col = shade(col, 0.55)
                col = shade(col, 0.92 + 0.12 * math.sin(t * 9.1 + y * 0.3))
            elif kind == "sun":
                col = lerp(th.bg1, th.bg0, f)
                if f < 0.45 and int(y + t * 2) % 3 == 0:
                    col = lerp(col, (255, 140, 90), 0.22)
            elif kind == "gears":
                col = lerp(th.bg0, th.bg1, f * (0.7 + 0.3 * pulse))
            else:
                col = lerp(th.bg0, th.bg1, f * (0.8 + 0.2 * pulse))
            if flash:
                col = lerp(col, th.accent, flash)
            row = cv.bg[y]
            for x in range(w):
                row[x] = col
        if kind == "stars":
            for sx, sy, ph in self.stars:
                x, y = int(sx * w), int(sy * h)
                tw = 0.5 + 0.5 * math.sin(t * 2.2 + ph)
                if tw > 0.55:
                    cv.put(x, y, "·" if tw < 0.85 else "✦", shade(th.accent2, 0.25 + tw * 0.5))
        elif kind == "rain":
            for d in self.rain:
                d[0] = (d[0] + d[1]) % (h + 24)
                x = d[2] % w
                head = int(d[0])
                for k in range(d[3]):
                    y = head - k
                    if 0 <= y < h:
                        c = shade(th.accent, max(0.04, 0.55 - k * (0.5 / d[3])))
                        if k == 0:
                            c = shade(th.accent2, 0.75)
                        g = T._GLYPHS[(x * 3 + y * 5 + int(t * 8)) % len(T._GLYPHS)]
                        cv.put(x, y, "01"[(x + y) % 2] if render.ASCII else g, c)
        elif kind == "gears":
            teeth = "+x*" if render.ASCII else "╬✳❋"
            for gx, gy, rad, spd in self.gears:
                cx, cy = gx * w, gy * h
                n = int(rad * 3)
                for i in range(n):
                    a = math.tau * i / n + t * spd
                    x = int(cx + math.cos(a) * rad * 2)
                    y = int(cy + math.sin(a) * rad)
                    cv.put(x, y, teeth[i % len(teeth)], shade(th.dim, 0.55))
                cv.put(int(cx), int(cy), "o" if render.ASCII else "◎", shade(th.dim, 0.7))
            for i, (sx, sy, sp) in enumerate(self.steam):
                y = int((sy * h - t * sp * 4) % h)
                x = int((sx * w + math.sin(t * 0.7 + i) * 2) % w)
                cv.put(x, y, "·" if render.ASCII else "°", shade(th.fg, 0.18))

    # -- small preview pieces --------------------------------------------
    def mini(self, kind, x, y, w, th, t, dim=False):
        if kind is None:
            return
        cells = E.ROT[kind][0]
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        ox = x + (w - (max(xs) - min(xs) + 1) * 2) // 2 - min(xs) * 2
        oy = y - min(ys)
        for cx, cy in cells:
            if dim:
                col = shade(th.pal[kind], 0.35)
                for i in range(2):
                    self.cv.put(ox + cx * 2 + i, oy + cy, "#" if render.ASCII else "█", col)
            else:
                draw_cell(self.cv, ox + cx * 2, oy + cy, 1, kind, th, t)

    def panel_bg(self, th):
        return shade(th.bg0, 0.94 if th.light else 1.35)

    def panels(self, g, th, L, t):
        cv = self.cv
        bc = th.boxchars()
        pb = self.panel_bg(th)
        ox, oy = L.lx, L.by
        hcol = th.accent2 if g.hold_flash else th.dim
        cv.box(ox, oy, LW, 5, hcol, bc, "HOLD", th.accent, fill=pb)
        self.mini(g.hold, ox + 2, oy + 2, LW - 4, th, t, dim=not g.hold_flash)
        cv.box(ox, oy + 5, LW, 11, th.dim, bc, "STATS", th.accent, fill=pb)
        sc = "{:,}".format(g.score).replace(",", " ")
        cv.text(ox + 2, oy + 6, "SCORE", shade(th.dim, 1.1))
        cv.text(ox + LW - 2 - len(sc), oy + 7, sc, th.accent2)
        warm = g.elapsed > 3
        rows = [("LINES", str(g.lines)), ("LEVEL", str(g.level)),
                ("PIECES", str(g.pieces)), ("TETRIS", str(g.tetrises)),
                ("PPS", "%.2f" % (g.pieces / g.elapsed) if warm else "—"),
                ("LPM", "%.0f" % (g.lines * 60 / g.elapsed) if warm else "—"),
                ("TIME", "%02d:%02d" % (int(g.elapsed) // 60, int(g.elapsed) % 60))]
        for i, (k, v) in enumerate(rows):
            cv.text(ox + 2, oy + 8 + i, k, th.dim)
            cv.text(ox + LW - 2 - len(v), oy + 8 + i, v, th.fg)
        # STACK: what the AI is doing right now
        cv.box(ox, oy + 16, LW, 6, th.dim, bc, "STACK", th.accent, fill=pb)
        mode = g.brain.mode
        mcol = (255, 90, 80) if mode == "PANIC" else (th.accent if mode == "STACKING" else th.dim)
        cv.ctext(ox + LW // 2, oy + 17, mode, mcol)
        ready = min(4, g.ready)
        cv.text(ox + 2, oy + 18, "ready", th.dim)
        for i in range(4):
            on = i < ready
            cv.put(ox + LW - 6 + i, oy + 18,
                   ("#" if on else ".") if render.ASCII else ("▰" if on else "▱"),
                   th.accent2 if on else shade(th.dim, 0.6))
        cv.text(ox + 2, oy + 19, "well", th.dim)
        cv.text(ox + LW - 2 - 6, oy + 19, "col %-2d" % (g.brain.well + 1), th.fg)
        streak = "b2b %d  combo %d" % (g.b2b, max(0, g.combo))
        cv.ctext(ox + LW // 2, oy + 20, streak, th.fg if (g.b2b or g.combo > 0) else th.dim)

    def right(self, g, th, L, t):
        cv = self.cv
        bc = th.boxchars()
        ox, oy = L.rx, L.by
        pb = self.panel_bg(th)
        cv.box(ox, oy, RW, 14, th.dim, bc, "NEXT", th.accent, fill=pb)
        for i, k in enumerate(g.bag.peek(4)):
            self.mini(k, ox + 2, oy + 2 + i * 3, RW - 4, th, t)
        cv.box(ox, oy + 14, RW, 8, th.dim, bc, "BRAIN", th.accent, fill=pb)
        cv.ctext(ox + RW // 2, oy + 15, g.brain.label, th.accent2)
        mv = g.move
        if mv:
            cv.text(ox + 2, oy + 16, "rot %d  col %-2d %s" %
                    (mv["rot"], mv["x"] + 1, "H" if mv["hold"] else " "), th.fg)
        scores = [c["score"] for c in g.top3] or [0]
        lo, hi = min(scores), max(scores)
        wbar = RW - 10
        for i, c in enumerate(g.top3[:3]):
            f = 1.0 if hi == lo else (c["score"] - lo) / (hi - lo) * 0.7 + 0.3
            n = max(1, int(wbar * f))
            col = th.accent if i == 0 else shade(th.dim, 1.5)
            for j in range(wbar):
                cv.put(ox + 2 + j, oy + 18 + i, "█" if j < n else ("." if render.ASCII else "░"),
                       col if j < n else shade(th.dim, 0.55))
            cv.text(ox + RW - 7, oy + 18 + i, "%5.0f" % c["score"], shade(th.dim, 1.2))

    def board(self, g, th, L, t):
        cv = self.cv
        s = L.s
        ox, oy = L.bx, L.by
        pulse = 0.55 + 0.45 * math.sin(t * 2.0)
        bcol = lerp(shade(th.accent, 0.45), th.accent, pulse)
        if g.danger > 0.02:
            bcol = lerp(bcol, (255, 60, 60), g.danger * (0.45 + 0.55 * pulse))
        cv.box(ox, oy, L.bw, L.bh, bcol, th.boxchars(),
               fill=shade(th.bg0, 0.88 if th.light else 1.18))
        clearing = g.state == "clear"
        cphase = g.timer / max(1, 14)
        well = g.brain.well
        for r in range(E.ROWS):
            for c in range(E.COLS):
                x, y = ox + 1 + c * 2 * s, oy + 1 + r * s
                k = g.grid[r][c]
                if k is None:
                    if c == well and g.brain.level >= 3:
                        for j in range(s):        # faint marker on the well
                            cv.put(x + 2 * s - 1, y + j, "▕" if not render.ASCII else "|",
                                   shade(th.dim, 0.35))
                    draw_empty(cv, x, y, s, th, t)
                    continue
                if g.state == "over" and r >= E.ROWS - g.dead_rows:
                    draw_cell(cv, x, y, s, k, th, t, "dead")
                elif clearing and r in g.clear_rows:
                    if cphase > abs(c - 4.5) / 5.0:
                        continue
                    draw_cell(cv, x, y, s, k, th, t, "flash")
                else:
                    draw_cell(cv, x, y, s, k, th, t)
        for tx, ty, age, kind in g.fx.trails:
            if 0 <= ty < E.ROWS:
                col = shade(th.pal[kind], 0.18 + 0.07 * age)
                ch = "|" if render.ASCII else ("│" if age < 6 else "║")
                for j in range(s):                       # only the middle of the cell
                    cv.put(ox + s + tx * 2 * s, oy + 1 + ty * s + j, ch, col)
                    cv.put(ox + s + 1 + tx * 2 * s, oy + 1 + ty * s + j, ch, shade(col, 0.6))
        if g.state in ("play", "drop") and g.kind:
            if g.state == "play":
                for cx, cy in E.cells_at(g.kind, g.rot, g.x, g.ghost_y()):
                    if cy >= 0:
                        draw_cell(cv, ox + 1 + cx * 2 * s, oy + 1 + cy * s, s, g.kind, th, t, "ghost")
            boost = 0.35 if g.state == "drop" else 0.10 + 0.10 * math.sin(t * 9)
            cells = g.cells()
            face_at = cells[len(cells) // 2]
            for cx, cy in cells:
                if cy < 0:
                    continue
                px, py = ox + 1 + cx * 2 * s, oy + 1 + cy * s
                draw_cell(cv, px, py, s, g.kind, th, t, boost=boost)
                if th.face and (cx, cy) == face_at and not render.ASCII:
                    eye = (30, 20, 40)
                    a, b = ("^", "^") if g.state == "drop" else ("•", "•")
                    cv.put(px + s - 1, py + (s - 1) // 2, a, eye)
                    cv.put(px + s, py + (s - 1) // 2, b, eye)
        if g.state == "lockflash":
            for cx, cy in g.lock_cells:
                if cy >= 0:
                    draw_cell(cv, ox + 1 + cx * 2 * s, oy + 1 + cy * s, s, g.kind, th, t, "flash")

    def overlays(self, g, th, L, t):
        cv = self.cv
        fx = g.fx
        for rx, ry, rad, life in fx.ring:
            n = max(8, int(rad * 5))
            for i in range(n):
                a = math.tau * i / n
                cv.put(int(rx + math.cos(a) * rad * 2), int(ry + math.sin(a) * rad * 0.75),
                       "·" if life < 6 else ("*" if render.ASCII else "•"),
                       shade(lerp(th.accent, th.accent2, (math.sin(a + t) + 1) / 2),
                             max(0.15, life / 14)))
        for p in fx.parts:
            cv.put(int(p.x), int(p.y), p.ch,
                   shade(p.col or th.accent, 0.25 + 0.75 * p.life / max(1, p.max)))
        if fx.banner:
            text, life, mx = fx.banner
            f = life / mx
            word = th.tetris_word if text == "__TETRIS__" else text
            inner = L.bw - 2
            word = word[:inner - 2]
            # slides in from below, rests near the top, floats away
            slide = int((1 - min(1.0, (1 - f) * 4)) * 3) - int(max(0.0, (0.35 - f) * 8))
            by = L.by + 1 + max(0, L.bh // 5) + slide
            fade = min(1.0, f * 3.5)
            bar = shade(th.bg0, 0.45 if not th.light else 1.4)
            cv.clear_rect(L.bx + 1, by, inner, 3, bar)
            edge = "─" if not render.ASCII else "-"
            for i in range(inner):
                c = lerp(th.accent, th.accent2, (math.sin(t * 3 + i * 0.25) + 1) / 2)
                cv.put(L.bx + 1 + i, by, edge, shade(c, 0.35 + 0.45 * fade), bar)
                cv.put(L.bx + 1 + i, by + 2, edge, shade(c, 0.35 + 0.45 * fade), bar)
            sx = L.bx + 1 + (inner - len(word)) // 2
            for i, c in enumerate(word):
                col = lerp(th.accent, th.accent2, (math.sin(t * 4 + i * 0.4) + 1) / 2)
                cv.put(sx + i, by + 1, c, shade(col, 0.3 + 0.7 * fade), bar)

    def help_box(self, th, app, t):
        cv = self.cv
        lines = [
            ("h / ?", "this help"),
            ("z", "zen mode - board only" + ("  [ON]" if app.zen else "")),
            ("t / T", "next / previous theme"),
            ("c", "theme auto-cycle: " + ("ON" if app.cycle else "off")),
            ("o", "follow the desktop theme: " + ("ON" if app.follow else "off")),
            ("i / I", "AI level: " + app.game.brain.label),
            ("[  ]", "speed: %.1fx" % app.game.speed),
            ("+  -", "block size: %d (max %d)" % (app.scale, app.smax)),
            ("arrows", "board size: %d x %d" % (E.COLS, E.ROWS)),
            ("f / g", "fill the window / back to 10x20"),
            ("r", "restart now"),
            ("p", "pause: " + ("yes" if app.paused else "no")),
            ("q", "quit"),
        ]
        w, h = 44, len(lines) + 4
        x, y = (cv.w - w) // 2, (cv.h - h) // 2
        cv.box(x, y, w, h, th.accent, th.boxchars(), "CONTROLS", th.accent2,
               fill=shade(th.bg0, 1.45 if not th.light else 0.92))
        for i, (k, d) in enumerate(lines):
            cv.text(x + 3, y + 2 + i, k.ljust(7), th.accent2)
            cv.text(x + 11, y + 2 + i, d[:w - 13], th.fg)
        cv.ctext(x + w // 2, y + h - 1, " %d themes · %s " % (len(app.keys), th.name), th.dim)

    def frame(self, app, t):
        cv = self.cv
        g, th, L = app.game, app.theme, app.layout
        cv.fill(th.bg0)
        self.background(th, t, g.fx.flash)
        sh = g.fx.shake
        if sh:
            L.ox += int(round(math.sin(t * 61) * sh))
            L.oy += int(round(math.cos(t * 47) * sh * 0.5))
            L.bx += int(round(math.sin(t * 61) * sh))
            L.by += int(round(math.cos(t * 47) * sh * 0.5))
            L.lx = L.ox
            L.rx = L.bx + L.bw + GAP
        if not L.zen:
            title = "A U T O T R I S"
            sx = L.ox + (L.w - len(title)) // 2
            for i, c in enumerate(title):
                cv.put(sx + i, L.oy, c,
                       lerp(th.accent, th.accent2, (math.sin(t * 1.8 + i * 0.35) + 1) / 2))
            cv.ctext(L.ox + L.w // 2, L.oy + 1, (th.name + " · " + th.tagline)[:L.w],
                     shade(th.dim, 1.15))
            self.panels(g, th, L, t)
            self.right(g, th, L, t)
        self.board(g, th, L, t)
        self.overlays(g, th, L, t)
        if not L.zen:
            line = "  ".join(x[0] for x in g.fx.ticker[-2:])
            cv.ctext(L.ox + L.w // 2, L.oy + L.h - 2, line[:L.w], shade(th.accent2, 0.9))
            foot = "%s · %s · %.1fx · %dx%d@%d · h for help" % (
                th.key.replace("om:", ""), g.brain.label, g.speed, E.COLS, E.ROWS, L.s)
            if app.cycle:
                foot = "⟳ " + foot
            cv.ctext(L.ox + L.w // 2, L.oy + L.h - 1, foot[:L.w], shade(th.dim, 0.85))
        if app.toast:
            msg = " %s " % app.toast[0]
            y = min(cv.h - 1, L.oy + L.h) if not L.zen else min(cv.h - 1, L.oy + L.h + 1)
            cv.ctext(cv.w // 2, y, msg, shade(th.bg0, 0.3), th.accent)
        if app.paused:
            cv.ctext(L.bx + L.bw // 2, L.by + L.bh // 2, "  PAUSED  ",
                     shade(th.bg0, 0.3), th.accent2)
        if app.help:
            self.help_box(th, app, t)


def emit_effects(g, th, rnd, L):
    fx = g.fx
    s = L.s
    px = lambda c: L.bx + 1 + c * 2 * s + s - 1
    py = lambda r: L.by + 1 + r * s + (s - 1) // 2
    if g.state == "lockflash" and g.timer == 1:
        cells = [c for c in g.lock_cells if c[1] >= 0]
        if cells:
            base = max(c[1] for c in cells)
            for cx, cy in cells:
                if cy != base:
                    continue
                for d in (-1, 1):
                    fx.parts.append(Particle(px(cx), py(cy), d * rnd.uniform(0.5, 1.4),
                                             -rnd.uniform(0.05, 0.3), rnd.randint(7, 13),
                                             rnd.choice(list(th.parts)), th.pal[g.kind], 0.06))
    if g.state == "clear" and g.timer == 1:
        n = len(g.clear_rows)
        for r in g.clear_rows:
            for c in range(E.COLS):
                k = g.grid[r][c] or "I"
                fx.burst(px(c), py(r), 3 if n < 4 else 5,
                         [th.pal[k], th.fg, th.accent], list(th.parts),
                         1.0 + 0.3 * n, 20, 0.04, rnd)
        cy = py(int(sum(g.clear_rows) / n))
        if n >= 3:
            fx.ring.append([L.bx + L.bw / 2, cy, 1.0, 14])
        if n == 4:
            fx.ring.append([L.bx + L.bw / 2, cy, 0.5, 20])
            fx.flash = 0.55
        elif n == 3:
            fx.flash = 0.22


# --------------------------------------------------------------------- app

class App:
    def __init__(self, args):
        self.args = args
        render.ASCII = args.ascii
        self.rng = random.Random(args.seed)
        self.rnd = random.Random(args.seed + 7)
        self.all = dict(T.THEMES)
        self.all.update(T.load_omarchy())
        self.keys = self.theme_keys(args.only)
        self.game = Game(self.rng, args.speed, args.iq)
        self.zen = args.zen
        self.help = False
        self.paused = False
        self.cycle = not args.theme
        self.follow = False
        self.toast = None
        self.trans = None
        self.scale_want = args.scale
        self.scale = max(1, args.scale or 1)
        self.autofill = args.fill
        self.smax = 1
        self.stamp = omarchy.current_stamp()
        key = self.resolve(args.theme) if args.theme else self.keys[0]
        if key == "system":
            self.follow = True
        self.theme = self.theme_by_key(key) or T.NEON
        self.ti = self.keys.index(key) if key in self.keys else 0
        self.swap_at = time.monotonic() + args.gallery

    # -- themes ----------------------------------------------------------
    def theme_keys(self, only):
        nat = [t.key for t in T.NATIVE]
        om = sorted(k for k in self.all if k.startswith("om:"))
        if only == "builtin":
            return nat
        if only == "omarchy":
            return om
        return nat + om

    def resolve(self, name):
        if not name:
            return self.keys[0]
        if name in ("system", "desktop", "omarchy"):
            return "system"
        if name in self.all:
            return name
        if "om:" + name in self.all:
            return "om:" + name
        return self.keys[0]

    def theme_by_key(self, key):
        if key == "system":
            return T.system_theme() or T.NEON
        return self.all.get(key)

    def set_theme(self, key, toast=None, kind=None):
        th = self.theme_by_key(key)
        if not th:
            return
        self.theme = th
        self.trans = Transition(kind or self.rnd.choice(Transition.KINDS),
                                self.canvas, self.rnd)
        self.say(toast or th.name)

    def say(self, msg, frames=70):
        self.toast = [msg, frames]

    # -- board size -------------------------------------------------------
    def set_grid(self, cols, rows, toast=True, fill=False):
        before = (E.COLS, E.ROWS)
        old = self.game.grid
        cols, rows = E.set_size(cols, rows)
        self.autofill = fill
        if (cols, rows) != before:
            self.game.rebase(old, before[0], before[1])
        if toast:
            self.say("board %dx%d" % (cols, rows))

    def fill_grid(self, toast=True):
        """Biggest board that fits the window at the current block size."""
        cv = self.canvas
        s = max(1, self.scale)
        extra_w = 0 if self.zen else (LW + RW + 2 * GAP)
        extra_h = 0 if self.zen else 4
        cols = (cv.w - extra_w - 2) // (2 * s)
        rows = (cv.h - extra_h - 2) // s
        self.set_grid(cols, rows, toast=False, fill=True)
        if toast:
            self.say("filled the window: %dx%d" % (E.COLS, E.ROWS))

    # -- input ------------------------------------------------------------
    def key(self, c):
        g = self.game
        if c in ("q", "\x03"):
            raise KeyboardInterrupt
        elif c in ("h", "?"):
            self.help = not self.help
        elif c == "z":
            self.zen = not self.zen
            self.say("zen mode " + ("on" if self.zen else "off"))
            if self.autofill:
                self.fill_grid(False)
        elif c == "t":
            self.cycle = False
            self.ti = (self.ti + 1) % len(self.keys)
            self.set_theme(self.keys[self.ti])
        elif c == "T":
            self.cycle = False
            self.ti = (self.ti - 1) % len(self.keys)
            self.set_theme(self.keys[self.ti])
        elif c == "c":
            self.cycle = not self.cycle
            self.swap_at = time.monotonic() + self.args.gallery
            self.say("theme auto-cycle " + ("ON" if self.cycle else "off"))
        elif c == "o":
            self.follow = not self.follow
            if self.follow:
                self.cycle = False
                self.stamp = omarchy.current_stamp()
                self.set_theme("system", "following the desktop: %s" % (self.stamp[0] or "?"))
            else:
                self.say("stopped following the desktop")
        elif c == "r":
            g.reset()
            self.say("restarted")
        elif c == "p":
            self.paused = not self.paused
        elif c == "i":
            g.brain.level = (g.brain.level + 1) % len(E.LEVELS)
            self.say("AI: " + g.brain.label)
        elif c == "I":
            g.brain.level = (g.brain.level - 1) % len(E.LEVELS)
            self.say("AI: " + g.brain.label)
        elif c in ("]", "."):
            g.speed = min(4.0, round(g.speed + 0.2, 1))
            self.say("speed %.1fx" % g.speed)
        elif c in ("[", ","):
            g.speed = max(0.2, round(g.speed - 0.2, 1))
            self.say("speed %.1fx" % g.speed)
        elif c in ("+", "="):
            self.scale_want = min(self.smax, (self.scale_want or self.scale) + 1)
            self.say("block size %d" % self.scale_want)
            if self.autofill:
                self.fill_grid(False)
        elif c in ("-", "_"):
            self.scale_want = max(1, (self.scale_want or self.scale) - 1)
            self.say("block size %d" % self.scale_want)
            if self.autofill:
                self.fill_grid(False)
        elif c == "right":
            self.set_grid(E.COLS + 1, E.ROWS)
        elif c == "left":
            self.set_grid(E.COLS - 1, E.ROWS)
        elif c == "up":
            self.set_grid(E.COLS, E.ROWS + 1)
        elif c == "down":
            self.set_grid(E.COLS, E.ROWS - 1)
        elif c == "f":
            self.fill_grid()
        elif c == "g":
            self.set_grid(10, 20)

    # -- loop -------------------------------------------------------------
    def run(self):
        a = self.args
        tty_out = sys.stdout.isatty()
        tw, th_ = term_size()
        self.canvas = cv = Canvas(tw, th_)
        r = Renderer(cv, self.rnd)
        resized = [False]
        if tty_out:
            try:
                signal.signal(signal.SIGWINCH, lambda *_: resized.__setitem__(0, True))
            except Exception:
                pass
        out = sys.stdout
        if self.autofill:
            self.fill_grid(False)
        t0 = time.monotonic()
        frames = 0
        with Keys() as keys:
            try:
                if not a.no_alt and tty_out:
                    out.write("\x1b[?1049h\x1b[?25l\x1b[2J")
                while True:
                    now = time.monotonic()
                    t = now - t0
                    for c in Keys.parse(keys.read()):
                        self.key(c)
                    if resized[0]:
                        resized[0] = False
                        tw, th_ = term_size()
                        cv.resize(tw, th_)
                        r.seed_bg()
                        self.trans = None
                        if self.autofill:
                            self.fill_grid(False)
                    self.smax = max_scale(cv.w, cv.h, self.zen)
                    self.scale = min(self.smax, self.scale_want or self.smax)
                    self.layout = Layout(cv.w, cv.h, self.scale, self.zen)
                    if self.follow and frames % 45 == 0:
                        st = omarchy.current_stamp()
                        if st != self.stamp:
                            self.stamp = st
                            self.set_theme("system", "desktop switched to %s" % (st[0] or "?"))
                    if self.cycle and now >= self.swap_at:
                        self.ti = (self.ti + 1) % len(self.keys)
                        self.swap_at = now + a.gallery
                        self.set_theme(self.keys[self.ti])
                    if not self.paused:
                        self.game.update()
                        emit_effects(self.game, self.theme, self.rnd, self.layout)
                    if self.toast:
                        self.toast[1] -= 1
                        if self.toast[1] <= 0:
                            self.toast = None
                    r.frame(self, t)
                    if self.trans:
                        self.trans.compose(cv, self.theme)
                        if self.trans.done:
                            self.trans = None
                    if not a.plain:
                        out.write(cv.render())
                        out.flush()
                    frames += 1
                    if a.frames and frames >= a.frames:
                        break
                    d = (t0 + frames / FPS) - time.monotonic()
                    if d > 0:
                        time.sleep(d)
            except KeyboardInterrupt:
                pass
            finally:
                if not a.no_alt and tty_out:
                    out.write("\x1b[0m\x1b[?25h\x1b[?1049l")
                    out.flush()
        if a.plain:
            print(cv.plain())


def main():
    p = argparse.ArgumentParser(
        description="a tetris that plays itself, for the screen you are not working on",
        epilog="press h while it is running to see every key")
    p.add_argument("-t", "--theme",
                   help="starting theme (built-in, an omarchy name, or 'system')")
    p.add_argument("-g", "--gallery", type=float, default=25.0,
                   help="seconds per theme when cycling (default 25)")
    p.add_argument("-s", "--speed", type=float, default=1.0,
                   help="speed multiplier, 0.2 to 4.0")
    p.add_argument("-i", "--iq", type=int, default=4, choices=range(5),
                   help="0 chaos · 1 rookie · 2 plain · 3 stacker · 4 master")
    p.add_argument("-S", "--scale", type=int, default=0, help="block size (0 = the biggest that fits)")
    p.add_argument("-z", "--zen", action="store_true", help="start with the HUD hidden")
    p.add_argument("-G", "--grid", metavar="CxR", help="board size, e.g. 20x24")
    p.add_argument("-F", "--fill", action="store_true",
                   help="board as large as the window (follows resizes)")
    p.add_argument("--only", choices=("builtin", "omarchy", "all"), default="all",
                   help="which themes go in the cycle")
    p.add_argument("--seed", type=int, default=random.randrange(1 << 30),
                   help="seed for the piece bag, to replay a run")
    p.add_argument("--ascii", action="store_true",
                   help="ASCII fallback for terminals without block glyphs")
    p.add_argument("--list", action="store_true", help="list every theme and exit")
    p.add_argument("--frames", type=int, default=0,
                   help="render N frames then exit (for testing)")
    p.add_argument("--plain", action="store_true",
                   help="print the last frame as plain text instead of drawing")
    p.add_argument("--no-alt", action="store_true",
                   help="do not switch to the alternate screen buffer")
    a = p.parse_args()
    if a.list:
        allt = dict(T.THEMES)
        allt.update(T.load_omarchy())
        cur = omarchy.current_name()
        print("built-in:")
        for t in T.NATIVE:
            print("  %-12s %-14s %s" % (t.key, t.name, t.tagline))
        print("\nomarchy (%s installed):" % len([k for k in allt if k.startswith("om:")]))
        for k in sorted(k for k in allt if k.startswith("om:")):
            n = k[3:]
            print("  %-12s %s%s" % (n, allt[k].tagline, "   <- in use on your desktop" if n == cur else ""))
        print("\n  system       follows your desktop theme (now: %s)" % (cur or "?"))
        return
    if a.grid:
        try:
            c, r = a.grid.lower().split("x")
            E.set_size(int(c), int(r))
        except ValueError:
            p.error("--grid expects something like 20x24")
    App(a).run()


if __name__ == "__main__":
    main()
