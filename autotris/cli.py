"""Command line entry point."""
from __future__ import annotations

import argparse
import random

from .core.board import clamp_size
from .display import canvas as canvas_module
from .theming import omarchy
from .theming.builtin import BUILTIN
from .theming.registry import OMARCHY_PREFIX, ThemeRegistry

LEVELS = "0 chaos · 1 rookie · 2 plain · 3 stacker · 4 master"


def parse_board(text, parser):
    try:
        columns, rows = text.lower().split("x")
        return clamp_size(int(columns), int(rows))
    except ValueError:
        parser.error("--grid expects something like 20x24")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="autotris",
        description="a tetris that plays itself, for the screen you are not working on",
        epilog="press h while it is running to see every key")
    parser.add_argument("-t", "--theme",
                        help="starting theme (built-in, an omarchy name, or 'system')")
    parser.add_argument("-g", "--gallery", type=float, default=25.0,
                        help="seconds per theme when cycling (default 25)")
    parser.add_argument("-s", "--speed", type=float, default=1.0,
                        help="speed multiplier, 0.2 to 4.0")
    parser.add_argument("-i", "--iq", type=int, default=4, choices=range(5), help=LEVELS)
    parser.add_argument("-S", "--scale", type=int, default=0,
                        help="block size (0 = the biggest that fits)")
    parser.add_argument("-z", "--zen", action="store_true", help="start with the HUD hidden")
    parser.add_argument("-G", "--grid", metavar="CxR", help="board size, e.g. 20x24")
    parser.add_argument("-F", "--fill", action="store_true",
                        help="board as large as the window (follows resizes)")
    parser.add_argument("--only", choices=("builtin", "omarchy", "all"), default="all",
                        help="which themes go in the cycle")
    parser.add_argument("--seed", type=int, default=random.randrange(1 << 30),
                        help="seed for the piece bag, to replay a run")
    parser.add_argument("--ascii", action="store_true",
                        help="ASCII fallback for terminals without block glyphs")
    parser.add_argument("--list", action="store_true", help="list every theme and exit")
    parser.add_argument("--frames", type=int, default=0,
                        help="render N frames then exit (for testing)")
    parser.add_argument("--plain", action="store_true",
                        help="print the last frame as plain text instead of drawing")
    parser.add_argument("--no-alt", action="store_true",
                        help="do not switch to the alternate screen buffer")
    parser.add_argument("--deterministic", action="store_true",
                        help="drive animation from the frame counter instead of the clock")
    parser.add_argument("--digest", action="store_true",
                        help="print a sha256 of every rendered frame instead of drawing")
    return parser


def list_themes():
    registry = ThemeRegistry("all")
    current = omarchy.active_name()
    print("built-in:")
    for theme in BUILTIN:
        print("  %-12s %-14s %s" % (theme.key, theme.name, theme.tagline))
    omarchy_keys = [k for k in registry.themes if k.startswith(OMARCHY_PREFIX)]
    print("\nomarchy (%d installed):" % len(omarchy_keys))
    for key in sorted(omarchy_keys):
        name = key[len(OMARCHY_PREFIX):]
        mark = "   <- in use on your desktop" if name == current else ""
        print("  %-12s %s%s" % (name, registry.themes[key].tagline, mark))
    print("\n  system       follows your desktop theme (now: %s)" % (current or "?"))


def main(argv=None):
    parser = build_parser()
    options = parser.parse_args(argv)
    if options.list:
        return list_themes()
    canvas_module.set_ascii(options.ascii)
    options.board = parse_board(options.grid, parser) if options.grid else None
    from .session import Session
    Session(options).run()
