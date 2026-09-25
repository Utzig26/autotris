"""What the game reports happening, for anything that wants to react."""
from __future__ import annotations

from dataclasses import dataclass, field


class Event:
    pass


@dataclass
class GameStarted(Event):
    pass


@dataclass
class PieceLocked(Event):
    name: str
    cells: list
    rows_cleared: int


@dataclass
class PieceSettled(Event):
    name: str
    cells: list


@dataclass
class PieceFell(Event):
    name: str
    cells: list
    from_row: int


@dataclass
class RowsIgnited(Event):
    rows: list
    names: list


@dataclass
class RowsCleared(Event):
    count: int
    gain: int
    combo: int
    back_to_back: int
    perfect: bool


@dataclass
class LevelReached(Event):
    level: int


@dataclass
class ToppedOut(Event):
    pass


@dataclass
class HoldSwapped(Event):
    name: str
