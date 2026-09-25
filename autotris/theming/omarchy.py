"""Reads Omarchy's theme files so the game can match the desktop."""
from __future__ import annotations

import os

from ..display.color import from_hex

SYSTEM_DIR = "/usr/share/omarchy/themes"
USER_DIR = os.path.expanduser("~/.config/omarchy/themes")
STATE_DIR = os.path.expanduser("~/.local/state/omarchy/current")

try:
    import tomllib
except ImportError:
    tomllib = None


def _parse(path):
    if tomllib:
        try:
            with open(path, "rb") as handle:
                return tomllib.load(handle)
        except (OSError, ValueError):
            pass
    values = {}
    try:
        with open(path) as handle:
            for line in handle:
                line = line.split("#")[0].strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        return {}
    return values


def installed():
    found = {}
    for directory in (SYSTEM_DIR, USER_DIR):
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name, "colors.toml")
            if os.path.isfile(path):
                found[name] = path
    return found


def active_name():
    try:
        with open(os.path.join(STATE_DIR, "theme.name")) as handle:
            return handle.read().strip()
    except OSError:
        pass
    link = os.path.join(STATE_DIR, "theme")
    if os.path.islink(link) or os.path.isdir(link):
        return os.path.basename(os.path.realpath(link))
    return None


def active_stamp():
    try:
        return (active_name(), os.stat(os.path.join(STATE_DIR, "theme")).st_mtime)
    except OSError:
        return (active_name(), 0)


def palette(path):
    raw = _parse(path)
    light = str(raw.get("mode", "dark")).lower() == "light"

    def pick(*keys, fallback=(128, 128, 128)):
        for key in keys:
            if raw.get(key):
                return from_hex(raw[key], fallback)
        return fallback

    def variants(base):
        return (base, "bright_" + base) if light else ("bright_" + base, base)

    pieces = {
        "I": pick(*variants("cyan"), fallback=(0, 200, 220)),
        "J": pick(*variants("blue"), fallback=(80, 120, 240)),
        "L": pick(*variants("orange"), "yellow", fallback=(235, 146, 123)),
        "O": pick(*variants("yellow"), fallback=(230, 200, 90)),
        "S": pick(*variants("green"), fallback=(140, 210, 100)),
        "T": pick(*variants("magenta"), fallback=(180, 140, 230)),
        "Z": pick(*variants("red"), fallback=(240, 110, 130)),
    }
    if light:
        base = pick("lighter_background", "background", fallback=(240, 238, 232))
        horizon = pick("background", "selection", fallback=(226, 224, 216))
        text = pick("dark_foreground", "foreground", fallback=(40, 40, 46))
        dim = pick("muted", "dark_foreground", fallback=(150, 148, 142))
    else:
        base = pick("darker_background", "dark_background", "background", fallback=(12, 12, 18))
        horizon = pick("lighter_background", "background", fallback=(30, 30, 44))
        text = pick("bright_foreground", "foreground", fallback=(220, 224, 240))
        dim = pick("muted", "dark_foreground", fallback=(90, 92, 110))
    return {
        "light": light,
        "palette": pieces,
        "background_color": base,
        "horizon_color": horizon,
        "foreground": text,
        "muted": dim,
        "accent": pick("accent", "blue", fallback=(120, 160, 250)),
        "highlight": pick("magenta", "bright_magenta", "red", fallback=(200, 140, 240)),
        "accent_hex": str(raw.get("accent", "")),
    }
