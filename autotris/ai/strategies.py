"""How a level turns scored placements into the move it actually plays."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from . import tuning
from .evaluator import ElTetrisEvaluator, StackingEvaluator


@dataclass
class Deliberation:
    situation: object
    follow_up: str
    evaluator: object
    explore: object


class Strategy(ABC):
    """Chooses one placement out of the scored options."""

    label = "?"

    def __init__(self, rng, evaluator):
        self.rng = rng
        self.evaluator = evaluator

    @abstractmethod
    def pick(self, options, deliberation):
        ...

    def ranked(self, chosen, options):
        return [chosen] + [o for o in options[:3] if o is not chosen][:2]


class ChaosStrategy(Strategy):
    label = "CHAOS"

    def pick(self, options, deliberation):
        chosen = self.rng.choice(options)
        return chosen, [chosen] + options[:2]


class RookieStrategy(Strategy):
    label = "ROOKIE"
    sloppiness = 0.55

    def pick(self, options, deliberation):
        if self.rng.random() < self.sloppiness:
            chosen = self.rng.choice(options[:max(3, len(options) // 2)])
            return chosen, [chosen] + options[:2]
        return options[0], options[:3]


class GreedyStrategy(Strategy):
    label = "PLAIN"

    def pick(self, options, deliberation):
        return options[0], options[:3]


class StackingStrategy(GreedyStrategy):
    label = "STACKER"


class LookaheadStrategy(Strategy):
    """Scores each shortlisted move by what the next piece could do after it."""

    label = "MASTER"
    budget = 2400

    def pick(self, options, deliberation):
        if not deliberation.follow_up:
            return options[0], options[:3]
        bits = options[0].bits
        width = max(2, min(8, self.budget // max(1, bits.columns * bits.height)))
        best = None
        best_value = None
        for option in options[:width]:
            follow = deliberation.explore(option.bits, deliberation.follow_up)
            value = option.score + tuning.LOOKAHEAD_WEIGHT * (follow[0].score if follow else -500)
            if best_value is None or value > best_value:
                best, best_value = option, value
        if best is None:
            return options[0], options[:3]
        return best, self.ranked(best, options)


def build_levels(rng):
    el_tetris = ElTetrisEvaluator()
    stacking = StackingEvaluator()
    return (ChaosStrategy(rng, el_tetris),
            RookieStrategy(rng, el_tetris),
            GreedyStrategy(rng, el_tetris),
            StackingStrategy(rng, stacking),
            LookaheadStrategy(rng, stacking))
