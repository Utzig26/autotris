"""A candidate move and the board it would produce."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Placement:
    name: str
    rotation: int
    column: int
    row: int
    cleared: int
    bits: object
    landing_depth: float
    size: int
    covers_well: bool
    hold: bool = False
    score: float = 0.0


@dataclass
class Situation:
    """What the evaluator needs to know beyond the board itself."""
    well: int
    holes_before: int
    stacking: bool
    digging: bool
