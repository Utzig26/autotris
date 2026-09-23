#!/usr/bin/env python3
"""Renders an autotris demo to PNG frames (no terminal involved).

Each canvas cell is painted directly with PIL, using a font cascade so block
glyphs, symbols and half-width katakana all show up. ffmpeg turns the frames
into the GIF used in the README.

    python tools/record.py --out frames/ --seconds 26
"""
from __future__ import annotations
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

import autotris as A
import engine as E
import themes as T
from render import Canvas

FONTS = [
    "/usr/share/fonts/Adwaita/AdwaitaMono-Regular.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Black.ttc",
]


class FontSet:
    """Picks, per character, the first font that actually has the glyph."""

    def __init__(self, size):
        self.fonts = []
        for path in FONTS:
            if not os.path.exists(path):
                continue
            try:
                tt = TTFont(path, fontNumber=0, lazy=True)
                cmap = set()
                for t in tt["cmap"].tables:
                    cmap |= set(t.cmap)
                self.fonts.append((ImageFont.truetype(path, size), cmap))
            except Exception:
                continue
        if not self.fonts:
            raise SystemExit("no usable font found")
        self.cache = {}

    def for_char(self, ch):
        f = self.cache.get(ch)
        if f is None:
            o = ord(ch)
            f = next((fnt for fnt, cm in self.fonts if o in cm), self.fonts[0][0])
            self.cache[ch] = f
        return f


def draw_frame(cv, fs, cw, chh, pad, ox, oy):
    img = Image.new("RGB", (cv.w * cw + 2 * pad, cv.h * chh + 2 * pad), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(cv.h):
        bgr, fgr, chr_ = cv.bg[y], cv.fg[y], cv.ch[y]
        x = 0
        while x < cv.w:                       # background in runs
            b = bgr[x]
            x2 = x
            while x2 < cv.w and bgr[x2] == b:
                x2 += 1
            if b:
                d.rectangle([pad + x * cw, pad + y * chh,
                             pad + x2 * cw - 1, pad + y * chh + chh - 1], fill=b)
            x = x2
        for x in range(cv.w):                 # glyphs one by one, exact grid
            c = chr_[x]
            if c == " " or not fgr[x]:
                continue
            d.text((pad + x * cw + ox, pad + y * chh + oy), c,
                   font=fs.for_char(c), fill=fgr[x])
    return img


def script(app, t, done):
    """Timeline of the demo: what to press and when."""
    beats = [
        (5.0, "theme:steampunk"),
        (9.5, "theme:kawaii"),
        (13.5, "theme:matrix"),
        (17.5, "theme:om:tokyo-night"),
        (21.5, "z"),                       # zen: board only
        (23.5, "f"),                       # board grows to fill the window
        (29.0, "g"),                       # back to 10x20
        (29.6, "z"),                       # HUD returns
        (31.0, "h"),                       # show the controls
    ]
    for when, action in beats:
        if t >= when and when not in done:
            done.add(when)
            if action.startswith("theme:"):
                app.set_theme(action.split(":", 1)[1])
            elif action.startswith("grid:"):
                c, r = action.split(":", 1)[1].split("x")
                app.set_grid(int(c), int(r))
            else:
                app.key(action)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="frames")
    ap.add_argument("--seconds", type=float, default=34.0)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--cols", type=int, default=82)
    ap.add_argument("--rows", type=int, default=32)
    ap.add_argument("--size", type=int, default=15)
    ap.add_argument("--speed", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=20260923)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    fs = FontSet(a.size)
    probe = fs.fonts[0][0]
    cw = max(1, round(probe.getlength("M")))
    chh = max(1, round(a.size * 1.30))
    pad = 10

    args = argparse.Namespace(theme="neon", gallery=1e9, speed=a.speed, iq=4, scale=1,
                              zen=False, only="all", seed=a.seed, ascii=False, list=False,
                              frames=0, plain=False, no_alt=True, grid=None, fill=False)
    app = A.App(args)
    app.canvas = cv = Canvas(a.cols, a.rows)
    rend = A.Renderer(cv, __import__("random").Random(a.seed + 1))
    app.smax = 1
    app.scale = 1

    total = int(a.seconds * a.fps)
    done = set()
    step = 1.0 / A.FPS                     # game logic still runs at 30 fps
    sub = max(1, round(A.FPS / a.fps))     # ticks per recorded frame
    tick = 0
    for i in range(total):
        t = i / a.fps
        script(app, t, done)
        for _ in range(sub):
            tick += 1
            app.smax = A.max_scale(cv.w, cv.h, app.zen)
            app.scale = min(app.smax, app.scale_want or app.smax)
            app.layout = A.Layout(cv.w, cv.h, app.scale, app.zen)
            app.game.update()
            A.emit_effects(app.game, app.theme, rend.rng, app.layout)
            if app.toast:
                app.toast[1] -= 1
                if app.toast[1] <= 0:
                    app.toast = None
        rend.frame(app, tick * step)
        if app.trans:
            app.trans.compose(cv, app.theme)
            if app.trans.done:
                app.trans = None
        draw_frame(cv, fs, cw, chh, pad, 0, 0).save("%s/f%05d.png" % (a.out, i))
        if i % 60 == 0:
            print("  frame %d/%d" % (i, total), flush=True)
    print("done: %d frames of %dx%d px" % (total, cv.w * cw + 2 * pad, cv.h * chh + 2 * pad))


if __name__ == "__main__":
    main()
