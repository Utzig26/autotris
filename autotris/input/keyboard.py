"""Reads keys without blocking, and names the arrows."""
from __future__ import annotations

import os
import select
import sys
import termios
import tty

ARROWS = {"A": "up", "B": "down", "C": "right", "D": "left"}


def decode(data):
    keys = []
    index = 0
    while index < len(data):
        char = data[index]
        if (char == "\x1b" and data[index + 1:index + 2] == "["
                and data[index + 2:index + 3] in ARROWS):
            keys.append(ARROWS[data[index + 2]])
            index += 3
        else:
            keys.append(char)
            index += 1
    return keys


class KeyReader:
    def __init__(self, stream=None):
        stream = stream or sys.stdin
        self.fd = stream.fileno() if stream.isatty() else None
        self.saved = None

    def __enter__(self):
        if self.fd is not None:
            self.saved = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *_):
        if self.saved is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)

    def pending(self):
        if self.fd is None:
            return []
        buffered = ""
        while select.select([self.fd], [], [], 0)[0]:
            chunk = os.read(self.fd, 32).decode("utf-8", "ignore")
            if not chunk:
                break
            buffered += chunk
        return decode(buffered)
