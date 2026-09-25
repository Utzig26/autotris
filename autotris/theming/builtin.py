"""The hand-made themes."""
from __future__ import annotations

from . import frames
from .backdrops import Flat, Gears, GlyphRain, Gradient, Scanlines, Starfield, Sunset
from .blocks import (DottedBlocks, DottedGhost, GlyphBlocks, OutlineGhost, RivetBlocks,
                     ShadedBlocks, SolidBlocks)
from .theme import Theme


def _monochrome(shades):
    return dict(zip("IJLOSTZ", shades))


NEON = Theme(
    key="neon", name="NEON GRID", tagline="cyberpunk // truecolor // glow",
    palette={"I": (0, 238, 255), "J": (70, 110, 255), "L": (255, 150, 20),
             "O": (255, 224, 60), "S": (60, 255, 140), "T": (208, 90, 255),
             "Z": (255, 60, 120)},
    background_color=(7, 5, 18), horizon_color=(20, 8, 44),
    foreground=(228, 232, 255), muted=(96, 92, 140),
    accent=(0, 238, 255), highlight=(255, 60, 160),
    blocks=SolidBlocks(), backdrop=Gradient(), frame=frames.HEAVY,
    grid_dot="·", particles=("✦", "·", "✧", "*"), tetris_word="█ T E T R I S █")

ARCADE = Theme(
    key="arcade", name="ARCADE 1989", tagline="NES vibes // flat colours // pure black",
    palette={"I": (0, 255, 255), "J": (0, 88, 248), "L": (248, 152, 0),
             "O": (248, 216, 0), "S": (0, 216, 0), "T": (184, 0, 248),
             "Z": (248, 56, 0)},
    background_color=(0, 0, 0), horizon_color=(6, 6, 16),
    foreground=(255, 255, 255), muted=(90, 90, 110),
    accent=(255, 255, 255), highlight=(248, 216, 0),
    blocks=SolidBlocks(bevelled=False, ghost=OutlineGhost()), backdrop=Flat(),
    frame=frames.DOUBLE, particles=("*", "+", "x"), tetris_word="!! TETRIS !!")

CRT = Theme(
    key="crt", name="PHOSPHOR", tagline="amber monochrome // scanlines // flicker",
    palette=_monochrome([(255, 190, 60), (255, 168, 20), (255, 205, 90), (255, 150, 0),
                         (255, 220, 120), (255, 176, 40), (255, 140, 0)]),
    background_color=(14, 8, 0), horizon_color=(26, 14, 0),
    foreground=(255, 186, 60), muted=(120, 76, 10),
    accent=(255, 208, 90), highlight=(255, 140, 0),
    blocks=ShadedBlocks(), backdrop=Scanlines(), frame=frames.THIN,
    particles=("·", "'", "."), tetris_word="* TETRIS *")

KAWAII = Theme(
    key="kawaii", name="KAWAII POP", tagline="pastel // little faces // hearts",
    palette={"I": (150, 226, 250), "J": (168, 178, 250), "L": (255, 198, 150),
             "O": (255, 240, 170), "S": (170, 244, 198), "T": (244, 176, 236),
             "Z": (255, 172, 186)},
    background_color=(32, 26, 44), horizon_color=(56, 40, 70),
    foreground=(255, 240, 250), muted=(140, 120, 160),
    accent=(255, 176, 214), highlight=(180, 230, 255),
    blocks=SolidBlocks(bevelled=False), backdrop=Starfield(), frame=frames.ROUND,
    particles=("♥", "✿", "·", "♡"), faces=True, tetris_word="♥ TETRIS ♥")

MATRIX = Theme(
    key="matrix", name="DATASTREAM", tagline="phosphor green // glyph rain // minimal",
    palette=_monochrome([(0, 255, 140), (0, 210, 120), (120, 255, 160), (0, 255, 190),
                         (60, 230, 110), (0, 190, 100), (160, 255, 190)]),
    background_color=(0, 6, 3), horizon_color=(0, 14, 8),
    foreground=(140, 255, 180), muted=(0, 90, 50),
    accent=(0, 255, 140), highlight=(200, 255, 220),
    blocks=GlyphBlocks(), backdrop=GlyphRain(), frame=frames.THIN,
    particles=("1", "0", "ﾜ", "ﾊ"), tetris_word="> TETRIS_")

VAPOR = Theme(
    key="vapor", name="VAPORWAVE", tagline="pink/purple gradient // striped sun // soft",
    palette={"I": (140, 240, 255), "J": (150, 140, 255), "L": (255, 190, 140),
             "O": (255, 230, 160), "S": (160, 255, 220), "T": (255, 140, 230),
             "Z": (255, 120, 160)},
    background_color=(28, 10, 48), horizon_color=(90, 24, 86),
    foreground=(255, 226, 248), muted=(150, 110, 170),
    accent=(255, 120, 200), highlight=(120, 230, 255),
    blocks=DottedBlocks(), backdrop=Sunset(), frame=frames.ROUND,
    particles=("─", "·", "•"), tetris_word="~ T E T R I S ~")

STEAMPUNK = Theme(
    key="steampunk", name="STEAMPUNK", tagline="brass and copper // gears // steam",
    palette={"I": (118, 196, 186), "J": (96, 134, 156), "L": (198, 118, 48),
             "O": (222, 176, 76), "S": (150, 168, 104), "T": (192, 146, 96),
             "Z": (176, 72, 44)},
    background_color=(20, 14, 9), horizon_color=(52, 34, 20),
    foreground=(238, 214, 170), muted=(132, 102, 66),
    accent=(216, 168, 76), highlight=(198, 94, 40),
    blocks=RivetBlocks(ghost=DottedGhost()), backdrop=Gears(), frame=frames.DOUBLE,
    particles=("˙", "°", "·", "o"), tetris_word="⚙ TETRIS ⚙")

BUILTIN = (NEON, ARCADE, CRT, KAWAII, MATRIX, VAPOR, STEAMPUNK)
