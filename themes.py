"""autotris - visual themes.

A theme is a palette plus a way of drawing one cell. The seven built-ins are
hand-made; the Omarchy ones are generated from the system's colors.toml files.
"""
from __future__ import annotations
import render
from render import shade, lerp
import omarchy

BOX_ROUND = "╭╮╰╯─│"
BOX_THIN = "┌┐└┘─│"
BOX_HEAVY = "┏┓┗┛━┃"
BOX_DOUBLE = "╔╗╚╝═║"
BOX_ASCII = "++++-|"


class Theme:
    def __init__(self, key, name, tagline, pal, bg0, bg1, fg, dim, accent, accent2,
                 box=BOX_THIN, cell="bevel", ghost="shade", bgkind="grad",
                 grid=None, parts=("*", "+", "."), face=False, light=False,
                 group="builtin", clear_word="LINE CLEAR", tetris_word="T E T R I S"):
        self.key = key
        self.name = name
        self.tagline = tagline
        self.pal = pal
        self.bg0, self.bg1 = bg0, bg1
        self.fg, self.dim = fg, dim
        self.accent, self.accent2 = accent, accent2
        self.box = box
        self.cell = cell
        self.ghost = ghost
        self.bgkind = bgkind
        self.grid = grid
        self.parts = parts
        self.face = face
        self.light = light
        self.group = group
        self.clear_word = clear_word
        self.tetris_word = tetris_word

    def boxchars(self):
        return BOX_ASCII if render.ASCII else self.box

    def up(self, c, f=1.18):
        """Lighter on dark themes, darker on light ones."""
        return shade(c, (2.0 - f) if self.light else f)

    def down(self, c, f=0.72):
        return shade(c, (2.0 - f) if self.light else f)


NEON = Theme(
    "neon", "NEON GRID", "cyberpunk // truecolor // glow",
    {"I": (0, 238, 255), "J": (70, 110, 255), "L": (255, 150, 20), "O": (255, 224, 60),
     "S": (60, 255, 140), "T": (208, 90, 255), "Z": (255, 60, 120)},
    bg0=(7, 5, 18), bg1=(20, 8, 44), fg=(228, 232, 255), dim=(96, 92, 140),
    accent=(0, 238, 255), accent2=(255, 60, 160),
    box=BOX_HEAVY, cell="bevel", ghost="shade", bgkind="grad",
    grid="·", parts=("✦", "·", "✧", "*"), tetris_word="█ T E T R I S █")

ARCADE = Theme(
    "arcade", "ARCADE 1989", "NES vibes // flat colours // pure black",
    {"I": (0, 255, 255), "J": (0, 88, 248), "L": (248, 152, 0), "O": (248, 216, 0),
     "S": (0, 216, 0), "T": (184, 0, 248), "Z": (248, 56, 0)},
    bg0=(0, 0, 0), bg1=(6, 6, 16), fg=(255, 255, 255), dim=(90, 90, 110),
    accent=(255, 255, 255), accent2=(248, 216, 0),
    box=BOX_DOUBLE, cell="flat", ghost="outline", bgkind="plain",
    parts=("*", "+", "x"), tetris_word="!! TETRIS !!")

CRT = Theme(
    "crt", "PHOSPHOR", "amber monochrome // scanlines // flicker",
    {k: v for k, v in zip("IJLOSTZ", [(255, 190, 60), (255, 168, 20), (255, 205, 90),
                                      (255, 150, 0), (255, 220, 120), (255, 176, 40),
                                      (255, 140, 0)])},
    bg0=(14, 8, 0), bg1=(26, 14, 0), fg=(255, 186, 60), dim=(120, 76, 10),
    accent=(255, 208, 90), accent2=(255, 140, 0),
    box=BOX_THIN, cell="shade", ghost="dots", bgkind="scan",
    parts=("·", "'", "."), tetris_word="* TETRIS *")

KAWAII = Theme(
    "kawaii", "KAWAII POP", "pastel // little faces // hearts",
    {"I": (150, 226, 250), "J": (168, 178, 250), "L": (255, 198, 150), "O": (255, 240, 170),
     "S": (170, 244, 198), "T": (244, 176, 236), "Z": (255, 172, 186)},
    bg0=(32, 26, 44), bg1=(56, 40, 70), fg=(255, 240, 250), dim=(140, 120, 160),
    accent=(255, 176, 214), accent2=(180, 230, 255),
    box=BOX_ROUND, cell="flat", ghost="shade", bgkind="stars",
    parts=("♥", "✿", "·", "♡"), face=True,
    clear_word="YAY!", tetris_word="♥ TETRIS ♥")

MATRIX = Theme(
    "matrix", "DATASTREAM", "phosphor green // glyph rain // minimal",
    {k: v for k, v in zip("IJLOSTZ", [(0, 255, 140), (0, 210, 120), (120, 255, 160),
                                      (0, 255, 190), (60, 230, 110), (0, 190, 100),
                                      (160, 255, 190)])},
    bg0=(0, 6, 3), bg1=(0, 14, 8), fg=(140, 255, 180), dim=(0, 90, 50),
    accent=(0, 255, 140), accent2=(200, 255, 220),
    box=BOX_THIN, cell="char", ghost="dots", bgkind="rain",
    parts=("1", "0", "ﾜ", "ﾊ"), tetris_word="> TETRIS_")

VAPOR = Theme(
    "vapor", "VAPORWAVE", "pink/purple gradient // striped sun // soft",
    {"I": (140, 240, 255), "J": (150, 140, 255), "L": (255, 190, 140), "O": (255, 230, 160),
     "S": (160, 255, 220), "T": (255, 140, 230), "Z": (255, 120, 160)},
    bg0=(28, 10, 48), bg1=(90, 24, 86), fg=(255, 226, 248), dim=(150, 110, 170),
    accent=(255, 120, 200), accent2=(120, 230, 255),
    box=BOX_ROUND, cell="dot", ghost="shade", bgkind="sun",
    parts=("─", "·", "•"), tetris_word="~ T E T R I S ~")

STEAMPUNK = Theme(
    "steampunk", "STEAMPUNK", "brass and copper // gears // steam",
    {"I": (118, 196, 186), "J": (96, 134, 156), "L": (198, 118, 48), "O": (222, 176, 76),
     "S": (150, 168, 104), "T": (192, 146, 96), "Z": (176, 72, 44)},
    bg0=(20, 14, 9), bg1=(52, 34, 20), fg=(238, 214, 170), dim=(132, 102, 66),
    accent=(216, 168, 76), accent2=(198, 94, 40),
    box=BOX_DOUBLE, cell="rivet", ghost="dots", bgkind="gears",
    parts=("˙", "°", "·", "o"), tetris_word="⚙ TETRIS ⚙")

NATIVE = (NEON, ARCADE, CRT, KAWAII, MATRIX, VAPOR, STEAMPUNK)
THEMES = {t.key: t for t in NATIVE}


# ------------------------------------------------------------ omarchy

def _from_omarchy(key, data, name=None):
    pretty = (name or key).replace("-", " ").upper()
    box = BOX_THIN if not data["light"] else BOX_ROUND
    return Theme("om:" + key, pretty,
                 "omarchy // %s // %s" % ("light" if data["light"] else "dark",
                                          data["accent_hex"] or "—"),
                 data["pal"], data["bg0"], data["bg1"], data["fg"], data["dim"],
                 data["accent"], data["accent2"],
                 box=box, cell="bevel", ghost="shade", bgkind="grad",
                 grid="·", parts=("·", "•", "+"), light=data["light"],
                 group="omarchy", tetris_word="T E T R I S")


def load_omarchy():
    """Every theme installed in Omarchy, already converted."""
    out = {}
    for name, path in omarchy.available().items():
        try:
            out["om:" + name] = _from_omarchy(name, omarchy.load(path))
        except Exception:
            continue
    return out


def system_theme():
    """Whatever theme the desktop is using right now (or None)."""
    cur = omarchy.current_name()
    if not cur:
        return None
    av = omarchy.available()
    path = av.get(cur)
    if not path:
        cur2 = cur.lower().replace(" ", "-")
        path = av.get(cur2)
        cur = cur2
    if not path:
        return None
    th = _from_omarchy(cur, omarchy.load(path))
    th.key = "system"
    th.name = cur.replace("-", " ").upper()
    th.tagline = "following your desktop theme"
    th.group = "system"
    return th


# ------------------------------------------------------------ cells

_GLYPHS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽﾊﾋﾜ01"


def _glyph(th, x, y, t):
    if render.ASCII:
        return "#"
    c = th.cell
    if c == "shade":
        return "▓"
    if c == "dot":
        return "▒"
    if c == "char":
        return _GLYPHS[(x * 7 + y * 13 + int(t * 6)) % len(_GLYPHS)]
    return "█"


def draw_cell(cv, px, py, s, kind, th, t, mode="solid", boost=0.0):
    """Draws one cell, (2*s) by s characters, at (px, py)."""
    col = th.pal[kind]
    w, h = 2 * s, s
    if mode == "ghost":
        if th.ghost == "outline":
            for j in range(h):
                for i in range(w):
                    edge = i == 0 or i == w - 1 or j == 0 or j == h - 1
                    if edge:
                        cv.put(px + i, py + j,
                               "+" if render.ASCII else ("▏" if i == 0 else "▕" if i == w - 1 else "▁"),
                               shade(col, 0.55))
            return
        ch = ":" if render.ASCII else ("░" if th.ghost == "dots" else _glyph(th, px, py, t))
        f = 0.45 if th.ghost == "dots" else 0.30
        for j in range(h):
            for i in range(w):
                cv.put(px + i, py + j, ch, shade(col, f))
        return
    if mode == "flash":
        col = (255, 255, 255) if not th.light else (40, 40, 48)
    elif mode == "dead":
        g = shade(col, 0.30)
        col = (int(g[0] * .5 + 70), int(g[1] * .5 + 70), int(g[2] * .5 + 75))
    elif boost:
        col = lerp(col, (255, 255, 255) if not th.light else (255, 255, 255), boost)
    flat = th.cell == "flat" or mode in ("flash", "dead")
    for j in range(h):
        for i in range(w):
            ch = _glyph(th, px + i, py + j, t)
            if flat:
                c = col
            else:
                f = 1.0
                if j == 0:
                    f *= 1.20
                if i == 0:
                    f *= 1.10
                if j == h - 1:
                    f *= 0.74
                if i == w - 1:
                    f *= 0.86
                c = th.up(col, f) if f >= 1.0 else th.down(col, f)
            cv.put(px + i, py + j, ch, c,
                   shade(col, 0.22) if th.cell == "char" and mode == "solid" else None)
    # steampunk rivet in the middle of the block
    if th.cell == "rivet" and s >= 2 and mode == "solid" and not render.ASCII:
        cv.put(px + w // 2 - 1, py + h // 2, "•", th.up(col, 1.45))


def draw_empty(cv, px, py, s, th, t):
    if not th.grid:
        return
    ch = "." if render.ASCII else th.grid
    cv.put(px + s - 1, py + (s - 1) // 2, ch, shade(th.dim, 0.42))
