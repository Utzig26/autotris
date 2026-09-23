"""autotris - a cell canvas with 24-bit colour and ANSI output."""
from __future__ import annotations

ASCII = False


def lerp(a, b, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def shade(c, f):
    return (max(0, min(255, int(c[0] * f))),
            max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))))


def mix(a, b, t):
    return lerp(a, b, t)


class Canvas:
    """A grid of characters, each with its own foreground and background."""

    def __init__(self, w, h):
        self.resize(w, h)

    def resize(self, w, h):
        self.w, self.h = max(1, w), max(1, h)
        self.fill(None)

    def fill(self, color=None):
        self.ch = [[" "] * self.w for _ in range(self.h)]
        self.fg = [[None] * self.w for _ in range(self.h)]
        self.bg = [[color] * self.w for _ in range(self.h)]

    def put(self, x, y, ch, fg=None, bg=None):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.ch[y][x] = ch
            if fg is not None:
                self.fg[y][x] = fg
            if bg is not None:
                self.bg[y][x] = bg

    def bgput(self, x, y, bg):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.bg[y][x] = bg

    def text(self, x, y, s, fg=None, bg=None):
        for i, c in enumerate(s):
            self.put(x + i, y, c, fg, bg)

    def ctext(self, cx, y, s, fg=None, bg=None):
        self.text(cx - len(s) // 2, y, s, fg, bg)

    def rect(self, x, y, w, h, bg):
        for j in range(h):
            for i in range(w):
                self.bgput(x + i, y + j, bg)

    def clear_rect(self, x, y, w, h, bg=None, fg=None):
        """Wipes characters too, not just the background."""
        for j in range(h):
            yy = y + j
            if not (0 <= yy < self.h):
                continue
            for i in range(w):
                xx = x + i
                if 0 <= xx < self.w:
                    self.ch[yy][xx] = " "
                    self.fg[yy][xx] = fg
                    self.bg[yy][xx] = bg

    def box(self, x, y, w, h, fg, chars, title=None, tfg=None, bg=None, fill=None):
        if fill is not None:
            self.clear_rect(x, y, w, h, fill)
        tl, tr, bl, br, hz, vt = chars
        self.put(x, y, tl, fg, bg)
        self.put(x + w - 1, y, tr, fg, bg)
        self.put(x, y + h - 1, bl, fg, bg)
        self.put(x + w - 1, y + h - 1, br, fg, bg)
        for i in range(1, w - 1):
            self.put(x + i, y, hz, fg, bg)
            self.put(x + i, y + h - 1, hz, fg, bg)
        for j in range(1, h - 1):
            self.put(x, y + j, vt, fg, bg)
            self.put(x + w - 1, y + j, vt, fg, bg)
        if title:
            self.text(x + 2, y, " " + title + " ", tfg or fg, bg)

    def render(self):
        """One escape-coded string for the whole frame, colours coalesced."""
        out = []
        for y in range(self.h):
            out.append("\x1b[%d;1H" % (y + 1))
            cf = cb = -1
            row = self.ch[y]
            fgr = self.fg[y]
            bgr = self.bg[y]
            for x in range(self.w):
                f = fgr[x]
                b = bgr[x]
                if f != cf:
                    out.append("\x1b[39m" if f is None else "\x1b[38;2;%d;%d;%dm" % f)
                    cf = f
                if b != cb:
                    out.append("\x1b[49m" if b is None else "\x1b[48;2;%d;%d;%dm" % b)
                    cb = b
                out.append(row[x])
            out.append("\x1b[0m")
        return "".join(out)

    def plain(self):
        return "\n".join("".join(r).rstrip() for r in self.ch)
