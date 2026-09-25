"""Owns the terminal: alternate buffer, cursor, size and resize notifications."""
from __future__ import annotations

import os
import signal
import sys

FALLBACK_SIZE = (100, 34)


def terminal_size():
    try:
        columns, rows = os.get_terminal_size()
        if columns > 10 and rows > 6:
            return columns, rows
    except OSError:
        pass
    return (int(os.environ.get("COLUMNS", FALLBACK_SIZE[0])),
            int(os.environ.get("LINES", FALLBACK_SIZE[1])))


class Screen:
    def __init__(self, alternate=True, stream=None):
        self.stream = stream or sys.stdout
        self.interactive = self.stream.isatty()
        self.alternate = alternate and self.interactive
        self._resized = False
        self._hook_resize()

    def _hook_resize(self):
        if not self.stream.isatty():
            return
        try:
            signal.signal(signal.SIGWINCH, lambda *_: setattr(self, "_resized", True))
        except (ValueError, OSError, AttributeError):
            pass

    def take_resize(self):
        was, self._resized = self._resized, False
        return was

    def __enter__(self):
        if self.alternate:
            self.stream.write("\x1b[?1049h\x1b[?25l\x1b[2J")
        return self

    def __exit__(self, *_):
        if self.alternate:
            self.stream.write("\x1b[0m\x1b[?25h\x1b[?1049l")
            self.stream.flush()

    def present(self, canvas):
        if not self.interactive:
            return
        self.stream.write(canvas.to_ansi())
        self.stream.flush()
