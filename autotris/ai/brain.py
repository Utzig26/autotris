"""Picks the move: keeps the well, watches for danger, delegates to a strategy."""
from __future__ import annotations

from . import features, tuning
from .generator import placements
from .placement import Situation
from .strategies import Deliberation, build_levels

STACKING = "STACKING"
DIGGING = "DIGGING"
PANIC = "PANIC"
CLEARING = "CLEARING"


class Brain:
    def __init__(self, rng, level=4, columns=10):
        self.rng = rng
        self.levels = build_levels(rng)
        self.level = level
        self.well = columns - 1
        self.panic = False
        self.mode = CLEARING

    @property
    def strategy(self):
        return self.levels[self.level]

    @property
    def label(self):
        return self.strategy.label

    @property
    def stacking(self):
        return self.strategy.evaluator.stacking

    def cycle(self, step=1):
        self.level = (self.level + step) % len(self.levels)

    def reset(self, columns):
        self.well = columns - 1
        self.panic = False

    def ready_rows(self, board):
        return features.ready_rows(board.bits(), min(self.well, board.columns - 1))

    def choose(self, board, name, alternative=None):
        bits = board.bits()
        if self.well >= bits.columns:
            self.well = bits.columns - 1
        holes_before = features.holes(bits)
        if self.stacking:
            self._relocate_well(bits)
            self._update_panic(bits)
            self.mode = PANIC if self.panic else (DIGGING if holes_before else STACKING)
        else:
            self.panic = False
            self.mode = CLEARING
        situation = Situation(well=self.well, holes_before=holes_before,
                              stacking=self.stacking and not self.panic,
                              digging=holes_before > 0)
        evaluator = self.strategy.evaluator
        options = placements(bits, name, evaluator, situation)
        if alternative and alternative != name:
            for option in placements(bits, alternative, evaluator, situation):
                option.hold = True
                options.append(option)
            options.sort(key=lambda p: -p.score)
        if not options:
            return None, []
        deliberation = Deliberation(
            situation=situation,
            follow_up=alternative,
            evaluator=evaluator,
            explore=lambda after, piece: placements(
                after, piece, evaluator,
                Situation(well=self.well, holes_before=situation.holes_before,
                          stacking=self.stacking and not self._is_panicking(after),
                          digging=situation.digging)),
        )
        return self.strategy.pick(options, deliberation)

    def _relocate_well(self, bits):
        columns = features.heights(bits)
        best = min(range(bits.columns),
                   key=lambda c: (columns[c], 0 if c == self.well else 1,
                                  0 if c in (0, bits.columns - 1) else 1))
        if columns[self.well] - columns[best] >= tuning.WELL_MIGRATION:
            self.well = best

    def _update_panic(self, bits):
        height = features.stack_height(bits, self.well)
        if self.panic:
            self.panic = height > max(2, int(bits.height * tuning.CALM_FRACTION))
        else:
            self.panic = (height > max(4, int(bits.height * tuning.PANIC_FRACTION))
                          and features.ready_rows(bits, self.well) < 4)
        if height > bits.height * tuning.LAST_RESORT_FRACTION:
            self.panic = True

    def _is_panicking(self, bits):
        return features.stack_height(bits, self.well) > max(4, int(bits.height * tuning.PANIC_FRACTION))
