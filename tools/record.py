#!/usr/bin/env python3
"""Renders a demo to PNG frames without involving a terminal.

Drives a normal Session through its frame hooks, painting each canvas cell with
PIL and a font cascade so blocks, symbols and half-width katakana all appear.

    python tools/record.py --out frames/ --seconds 34
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from autotris.display import canvas as canvas_module
from autotris.session import FPS, Session

FONTS = [
    "/usr/share/fonts/Adwaita/AdwaitaMono-Regular.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Black.ttc",
]

BEATS = [
    (5.0, "theme:steampunk"),
    (9.5, "theme:kawaii"),
    (13.5, "theme:matrix"),
    (17.5, "theme:om:tokyo-night"),
    (21.5, "z"),
    (23.5, "f"),
    (29.0, "g"),
    (29.6, "z"),
    (31.0, "h"),
]


class FontSet:
    def __init__(self, size):
        self.fonts = []
        for path in FONTS:
            if not os.path.exists(path):
                continue
            try:
                parsed = TTFont(path, fontNumber=0, lazy=True)
                covered = set()
                for table in parsed["cmap"].tables:
                    covered |= set(table.cmap)
                self.fonts.append((ImageFont.truetype(path, size), covered))
            except Exception:
                continue
        if not self.fonts:
            raise SystemExit("no usable font found")
        self.cache = {}

    def for_char(self, char):
        chosen = self.cache.get(char)
        if chosen is None:
            code = ord(char)
            chosen = next((f for f, covered in self.fonts if code in covered), self.fonts[0][0])
            self.cache[char] = chosen
        return chosen


class FrameWriter:
    def __init__(self, out, fonts, cell_width, cell_height, padding, fps, beats):
        self.out = out
        self.fonts = fonts
        self.cw = cell_width
        self.chh = cell_height
        self.pad = padding
        self.fps = fps
        self.beats = list(beats)
        self.fired = set()
        self.index = 0

    def before(self, session, frame):
        moment = frame / FPS
        for when, action in self.beats:
            if moment < when or when in self.fired:
                continue
            self.fired.add(when)
            if action.startswith("theme:"):
                session.set_theme(action.split(":", 1)[1])
            else:
                session.handle(action)

    def after(self, canvas, frame):
        if frame % max(1, round(FPS / self.fps)):
            return
        self.paint(canvas).save("%s/f%05d.png" % (self.out, self.index))
        self.index += 1
        if self.index % 60 == 0:
            print("  frame %d" % self.index, flush=True)

    def paint(self, canvas):
        image = Image.new("RGB", (canvas.width * self.cw + 2 * self.pad,
                                  canvas.height * self.chh + 2 * self.pad), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        for y in range(canvas.height):
            backgrounds, foregrounds, chars = canvas.bg[y], canvas.fg[y], canvas.ch[y]
            x = 0
            while x < canvas.width:
                colour = backgrounds[x]
                run = x
                while run < canvas.width and backgrounds[run] == colour:
                    run += 1
                if colour:
                    draw.rectangle([self.pad + x * self.cw, self.pad + y * self.chh,
                                    self.pad + run * self.cw - 1,
                                    self.pad + y * self.chh + self.chh - 1], fill=colour)
                x = run
            for x in range(canvas.width):
                char = chars[x]
                if char == " " or not foregrounds[x]:
                    continue
                draw.text((self.pad + x * self.cw, self.pad + y * self.chh), char,
                          font=self.fonts.for_char(char), fill=foregrounds[x])
        return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="frames")
    parser.add_argument("--seconds", type=float, default=34.0)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--cols", type=int, default=82)
    parser.add_argument("--rows", type=int, default=32)
    parser.add_argument("--size", type=int, default=15)
    parser.add_argument("--speed", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=20260923)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    os.environ["COLUMNS"], os.environ["LINES"] = str(args.cols), str(args.rows)
    fonts = FontSet(args.size)
    cell_width = max(1, round(fonts.fonts[0][0].getlength("M")))

    options = argparse.Namespace(
        theme="neon", gallery=1e9, speed=args.speed, iq=4, scale=1, zen=False,
        only="all", seed=args.seed, ascii=False, list=False,
        frames=int(args.seconds * FPS), plain=False, no_alt=True, grid=None,
        board=None, fill=False, deterministic=True, digest=False)
    canvas_module.set_ascii(False)
    writer = FrameWriter(args.out, fonts, cell_width, max(1, round(args.size * 1.30)),
                         10, args.fps, BEATS)
    Session(options).run(hooks=writer)
    print("done: %d frames" % writer.index)


if __name__ == "__main__":
    main()
