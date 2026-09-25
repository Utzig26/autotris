"""Time, so a run can be driven by the wall clock or by the frame counter."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod


class Clock(ABC):
    def __init__(self):
        self._origin = 0.0

    def start(self):
        self._origin = self.reading()

    def elapsed(self):
        return self.reading() - self._origin

    @abstractmethod
    def reading(self):
        ...

    @abstractmethod
    def since(self, origin, frames):
        """How long something that has run `frames` frames since `origin` has lived."""

    def tick(self):
        pass

    def pace(self, frames, fps):
        pass


class RealClock(Clock):
    def reading(self):
        return time.monotonic()

    def since(self, origin, frames):
        return self.reading() - self._origin - origin

    def pace(self, frames, fps):
        delay = self._origin + frames / fps - time.monotonic()
        if delay > 0:
            time.sleep(delay)


class FixedStepClock(Clock):
    """Every frame is exactly one step, so a run is reproducible and fast."""

    def __init__(self, fps):
        super().__init__()
        self.fps = fps
        self.frames = 0

    def reading(self):
        return self.frames / self.fps

    def since(self, origin, frames):
        return frames / self.fps

    def tick(self):
        self.frames += 1
