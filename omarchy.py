"""Reads Omarchy themes (colors.toml) and turns them into autotris themes.

Every Omarchy theme ships a full ~20 colour palette, so the seven pieces and
the rest of the UI map straight onto it and the game matches the desktop.
The "system" theme follows whatever is active and picks up live changes.
"""
from __future__ import annotations
import os

SYS_DIR = "/usr/share/omarchy/themes"
USR_DIR = os.path.expanduser("~/.config/omarchy/themes")
STATE = os.path.expanduser("~/.local/state/omarchy/current")

try:
    import tomllib
except ImportError:
    tomllib = None


def _parse(path):
    if tomllib:
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except Exception:
            pass
    out = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.split("#")[0].strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        return {}
    return out


def _rgb(h, fallback=(128, 128, 128)):
    if not isinstance(h, str):
        return fallback
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return fallback
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return fallback


def available():
    """{name: path to colors.toml}. User themes win over system ones."""
    found = {}
    for d in (SYS_DIR, USR_DIR):
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name, "colors.toml")
            if os.path.isfile(p):
                found[name] = p
    return found


def current_name():
    try:
        with open(os.path.join(STATE, "theme.name")) as f:
            return f.read().strip()
    except OSError:
        pass
    link = os.path.join(STATE, "theme")
    if os.path.islink(link) or os.path.isdir(link):
        return os.path.basename(os.path.realpath(link))
    return None


def current_stamp():
    """Changes whenever the user switches desktop theme."""
    try:
        return (current_name(), os.stat(os.path.join(STATE, "theme")).st_mtime)
    except OSError:
        return (current_name(), 0)


def load(path):
    """colors.toml -> a dict ready to become a Theme."""
    c = _parse(path)
    g = lambda k, d=None: c.get(k, d)
    light = str(g("mode", "dark")).lower() == "light"

    def pick(*keys, fb=(128, 128, 128)):
        for k in keys:
            if c.get(k):
                return _rgb(c[k], fb)
        return fb

    bright = (lambda base: ("bright_" + base, base)) if not light else (lambda base: (base, "bright_" + base))
    pal = {
        "I": pick(*bright("cyan"), fb=(0, 200, 220)),
        "J": pick(*bright("blue"), fb=(80, 120, 240)),
        "L": pick(*bright("orange"), "yellow", fb=(235, 146, 123)),
        "O": pick(*bright("yellow"), fb=(230, 200, 90)),
        "S": pick(*bright("green"), fb=(140, 210, 100)),
        "T": pick(*bright("magenta"), fb=(180, 140, 230)),
        "Z": pick(*bright("red"), fb=(240, 110, 130)),
    }
    if light:
        bg0 = pick("lighter_background", "background", fb=(240, 238, 232))
        bg1 = pick("background", "selection", fb=(226, 224, 216))
        fg = pick("dark_foreground", "foreground", fb=(40, 40, 46))
        dim = pick("muted", "dark_foreground", fb=(150, 148, 142))
    else:
        bg0 = pick("darker_background", "dark_background", "background", fb=(12, 12, 18))
        bg1 = pick("lighter_background", "background", fb=(30, 30, 44))
        fg = pick("bright_foreground", "foreground", fb=(220, 224, 240))
        dim = pick("muted", "dark_foreground", fb=(90, 92, 110))
    return {
        "light": light,
        "pal": pal,
        "bg0": bg0,
        "bg1": bg1,
        "fg": fg,
        "dim": dim,
        "accent": pick("accent", "blue", fb=(120, 160, 250)),
        "accent2": pick("magenta", "bright_magenta", "red", fb=(200, 140, 240)),
        "accent_hex": str(g("accent", "")),
    }
