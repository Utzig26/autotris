"""Every key the session responds to. The help screen is built from this list."""
from __future__ import annotations

from abc import ABC, abstractmethod


class Command(ABC):
    keys = ()
    hint = ""

    @abstractmethod
    def execute(self, session):
        ...

    def describe(self, session):
        return self.hint

    @property
    def label(self):
        return " ".join(self.keys)


class Quit(Command):
    keys = ("q",)
    hint = "quit"

    def execute(self, session):
        raise KeyboardInterrupt


class ToggleHelp(Command):
    keys = ("h", "?")
    hint = "this help"

    def execute(self, session):
        session.help_visible = not session.help_visible


class ToggleZen(Command):
    keys = ("z",)

    def describe(self, session):
        return "zen mode - board only" + ("  [ON]" if session.zen else "")

    def execute(self, session):
        session.zen = not session.zen
        session.say("zen mode " + ("on" if session.zen else "off"))
        session.refit()


class NextTheme(Command):
    keys = ("t", "T")
    hint = "next / previous theme"

    def execute(self, session, step=1):
        session.cycle = False
        session.step_theme(step)


class PreviousTheme(NextTheme):
    keys = ()

    def execute(self, session, step=-1):
        super().execute(session, step)


class ToggleCycle(Command):
    keys = ("c",)

    def describe(self, session):
        return "theme auto-cycle: " + ("ON" if session.cycle else "off")

    def execute(self, session):
        session.cycle = not session.cycle
        session.restart_cycle()
        session.say("theme auto-cycle " + ("ON" if session.cycle else "off"))


class FollowDesktop(Command):
    keys = ("o",)

    def describe(self, session):
        return "follow the desktop theme: " + ("ON" if session.follow else "off")

    def execute(self, session):
        session.follow = not session.follow
        if session.follow:
            session.cycle = False
            session.watch_desktop()
        else:
            session.say("stopped following the desktop")


class Restart(Command):
    keys = ("r",)
    hint = "restart now"

    def execute(self, session):
        session.game.start()
        session.say("restarted")


class TogglePause(Command):
    keys = ("p",)

    def describe(self, session):
        return "pause: " + ("yes" if session.paused else "no")

    def execute(self, session):
        session.paused = not session.paused


class SmarterAI(Command):
    keys = ("i", "I")

    def describe(self, session):
        return "AI level: " + session.game.brain.label

    def execute(self, session, step=1):
        session.game.brain.cycle(step)
        session.say("AI: " + session.game.brain.label)


class DumberAI(SmarterAI):
    keys = ()

    def execute(self, session, step=-1):
        super().execute(session, step)


class Faster(Command):
    keys = ("]", ".")

    def describe(self, session):
        return "speed: %.1fx" % session.game.speed

    def execute(self, session, step=0.2):
        session.game.speed = max(0.2, min(4.0, round(session.game.speed + step, 1)))
        session.say("speed %.1fx" % session.game.speed)


class Slower(Faster):
    keys = ("[", ",")

    def execute(self, session, step=-0.2):
        super().execute(session, step)


class Bigger(Command):
    keys = ("+", "=")

    def describe(self, session):
        return "block size: %d (max %d)" % (session.scale, session.max_scale)

    def execute(self, session, step=1):
        session.resize_blocks(step)


class Smaller(Bigger):
    keys = ("-", "_")

    def execute(self, session, step=-1):
        super().execute(session, step)


class WiderBoard(Command):
    keys = ("right", "left")

    def describe(self, session):
        return "board size: %d x %d" % (session.game.board.columns, session.game.board.rows)

    def execute(self, session, step=1):
        board = session.game.board
        session.set_board(board.columns + step, board.rows)


class NarrowerBoard(WiderBoard):
    keys = ()

    def execute(self, session, step=-1):
        super().execute(session, step)


class TallerBoard(WiderBoard):
    keys = ("up", "down")

    def describe(self, session):
        return ""

    def execute(self, session, step=1):
        board = session.game.board
        session.set_board(board.columns, board.rows + step)


class ShorterBoard(TallerBoard):
    keys = ()

    def execute(self, session, step=-1):
        super().execute(session, step)


class FillWindow(Command):
    keys = ("f", "g")
    hint = "fill the window / back to 10x20"

    def execute(self, session):
        session.fill_window()


class DefaultBoard(FillWindow):
    keys = ()

    def execute(self, session):
        session.set_board(10, 20)


SHOWN = (ToggleHelp, ToggleZen, NextTheme, ToggleCycle, FollowDesktop, SmarterAI,
         Faster, Bigger, WiderBoard, TallerBoard, FillWindow, Restart, TogglePause, Quit)

_PAIRS = {
    "t": NextTheme, "T": PreviousTheme,
    "i": SmarterAI, "I": DumberAI,
    "]": Faster, ".": Faster, "[": Slower, ",": Slower,
    "+": Bigger, "=": Bigger, "-": Smaller, "_": Smaller,
    "right": WiderBoard, "left": NarrowerBoard,
    "up": TallerBoard, "down": ShorterBoard,
    "f": FillWindow, "g": DefaultBoard,
}


def build():
    table = {}
    singles = (Quit, ToggleHelp, ToggleZen, ToggleCycle, FollowDesktop, Restart, TogglePause)
    for command_type in singles:
        command = command_type()
        for key in command.keys:
            table[key] = command
    for key, command_type in _PAIRS.items():
        table[key] = command_type()
    table["\x03"] = table["q"]
    return table


def help_rows(session):
    rows = []
    for command_type in SHOWN:
        command = command_type()
        description = command.describe(session)
        if description:
            rows.append((command.label, description))
    return rows
