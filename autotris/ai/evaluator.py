"""How good is a placement."""
from __future__ import annotations

from abc import ABC, abstractmethod

from . import features, tuning


class Evaluator(ABC):
    """Scores a placement. Higher is better."""

    stacking = False

    @abstractmethod
    def score(self, placement, situation):
        ...


class ElTetrisEvaluator(Evaluator):
    """The published El-Tetris heuristic: survives forever, clears one row at a time."""

    def score(self, placement, situation):
        bits = placement.bits
        weights = tuning.EL_TETRIS
        landing = bits.height - placement.landing_depth
        return (weights[0] * landing
                + weights[1] * placement.cleared
                + weights[2] * features.row_transitions(bits)
                + weights[3] * features.column_transitions(bits)
                + weights[4] * features.holes(bits)
                + weights[5] * features.wells(bits))


class StackingEvaluator(Evaluator):
    """Builds towards tetrises, but digs a buried hole out before anything else."""

    stacking = True

    def score(self, placement, situation):
        bits = placement.bits
        weights = tuning.EL_TETRIS
        holes_after = features.holes(bits)
        landing = bits.height - placement.landing_depth
        skip = situation.well if situation.stacking else None
        total = (weights[0] * landing
                 + weights[1] * placement.cleared
                 + weights[2] * features.row_transitions(bits)
                 + weights[3] * features.column_transitions(bits)
                 + weights[4] * holes_after
                 + weights[5] * features.wells(bits, skip))
        if not situation.stacking:
            return total
        cleared = placement.cleared
        if cleared == 4:
            total += tuning.TETRIS_BONUS
        elif cleared:
            total += (tuning.DIG_CLEAR_BONUS * cleared if situation.digging
                      else -tuning.PARTIAL_CLEAR_PENALTY * cleared)
        total += tuning.READY_ROW_BONUS * features.ready_rows(bits, situation.well)
        flat = int(bits.height * tuning.FLAT_FRACTION)
        total -= tuning.HEIGHT_PENALTY * max(0, features.stack_height(bits, situation.well) - flat)
        total += tuning.DIG_WEIGHT * (situation.holes_before - holes_after)
        if placement.covers_well and cleared < 4:
            total -= tuning.WELL_COVER_PENALTY * (0.3 if situation.digging else 1.0)
        return total
