"""Enumerates and scores every legal placement for a piece."""
from __future__ import annotations

from ..core.tetromino import PIECES
from .placement import Placement


def placements(bits, name, evaluator, situation):
    piece = PIECES[name]
    well_bit = 1 << situation.well
    found = []
    for index, rotation in enumerate(piece.rotations):
        for absolute in range(bits.columns - rotation.width + 1):
            row = bits.landing_row(rotation, absolute)
            if row < 0:
                continue
            after, cleared = bits.after(rotation, absolute, row)
            covers = any((mask << absolute) & well_bit for _, mask in rotation.masks)
            candidate = Placement(
                name=name,
                rotation=index,
                column=absolute - rotation.left,
                row=row,
                cleared=cleared,
                bits=after,
                landing_depth=(rotation.size * row + rotation.depth_sum) / rotation.size,
                size=rotation.size,
                covers_well=covers,
            )
            candidate.score = evaluator.score(candidate, situation)
            found.append(candidate)
    found.sort(key=lambda p: -p.score)
    return found
