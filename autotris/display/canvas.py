"""A grid of characters, each with its own foreground and background colour."""
from __future__ import annotations

ASCII = False


def ascii_only():
    return ASCII


def set_ascii(enabled):
    global ASCII
    ASCII = enabled


class Canvas:
    def __init__(self, width, height):
        self.resize(width, height)

    def resize(self, width, height):
        self.width, self.height = max(1, width), max(1, height)
        self.fill(None)

    def fill(self, color=None):
        self.ch = [[" "] * self.width for _ in range(self.height)]
        self.fg = [[None] * self.width for _ in range(self.height)]
        self.bg = [[color] * self.width for _ in range(self.height)]

    def put(self, x, y, char, fg=None, bg=None):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.ch[y][x] = char
            if fg is not None:
                self.fg[y][x] = fg
            if bg is not None:
                self.bg[y][x] = bg

    def paint(self, x, y, bg):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.bg[y][x] = bg

    def text(self, x, y, value, fg=None, bg=None):
        for i, char in enumerate(value):
            self.put(x + i, y, char, fg, bg)

    def centered(self, x, y, value, fg=None, bg=None):
        self.text(x - len(value) // 2, y, value, fg, bg)

    def wash(self, x, y, width, height, bg=None, fg=None):
        for j in range(height):
            row = y + j
            if not 0 <= row < self.height:
                continue
            for i in range(width):
                column = x + i
                if 0 <= column < self.width:
                    self.ch[row][column] = " "
                    self.fg[row][column] = fg
                    self.bg[row][column] = bg

    def frame(self, x, y, width, height, fg, chars, title=None, title_fg=None,
              bg=None, fill=None):
        if fill is not None:
            self.wash(x, y, width, height, fill)
        top_left, top_right, bottom_left, bottom_right, horizontal, vertical = chars
        self.put(x, y, top_left, fg, bg)
        self.put(x + width - 1, y, top_right, fg, bg)
        self.put(x, y + height - 1, bottom_left, fg, bg)
        self.put(x + width - 1, y + height - 1, bottom_right, fg, bg)
        for i in range(1, width - 1):
            self.put(x + i, y, horizontal, fg, bg)
            self.put(x + i, y + height - 1, horizontal, fg, bg)
        for j in range(1, height - 1):
            self.put(x, y + j, vertical, fg, bg)
            self.put(x + width - 1, y + j, vertical, fg, bg)
        if title:
            self.text(x + 2, y, " " + title + " ", title_fg or fg, bg)

    def snapshot(self):
        return ([row[:] for row in self.ch],
                [row[:] for row in self.fg],
                [row[:] for row in self.bg])

    def restore_cell(self, snapshot, x, y, source_x=None):
        chars, fgs, bgs = snapshot
        sx = x if source_x is None else source_x
        self.ch[y][x] = chars[y][sx]
        self.fg[y][x] = fgs[y][sx]
        self.bg[y][x] = bgs[y][sx]

    def to_ansi(self):
        out = []
        for y in range(self.height):
            out.append("\x1b[%d;1H" % (y + 1))
            last_fg = last_bg = -1
            chars, fgs, bgs = self.ch[y], self.fg[y], self.bg[y]
            for x in range(self.width):
                fg, bg = fgs[x], bgs[x]
                if fg != last_fg:
                    out.append("\x1b[39m" if fg is None else "\x1b[38;2;%d;%d;%dm" % fg)
                    last_fg = fg
                if bg != last_bg:
                    out.append("\x1b[49m" if bg is None else "\x1b[48;2;%d;%d;%dm" % bg)
                    last_bg = bg
                out.append(chars[x])
            out.append("\x1b[0m")
        return "".join(out)

    def to_text(self):
        return "\n".join("".join(row).rstrip() for row in self.ch)
