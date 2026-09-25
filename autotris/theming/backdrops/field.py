"""Shared ambient state (rain drops, stars, gears) reseeded on resize."""
from __future__ import annotations

import math


class AmbientField:
    def __init__(self, rng, drops=55, stars=90, gears=5, puffs=28):
        self.sizes = (drops, stars, gears, puffs)
        self.reseed(rng)

    def reseed(self, rng):
        drops, stars, gears, puffs = self.sizes
        self.rain = [[rng.uniform(0, 60), rng.uniform(0.3, 1.1), rng.randrange(0, 400),
                      rng.randrange(4, 12)] for _ in range(drops)]
        self.stars = [(rng.random(), rng.random(), rng.uniform(0, math.tau))
                      for _ in range(stars)]
        self.gears = [(rng.random(), rng.random(), rng.uniform(3, 7),
                       rng.choice((-1, 1)) * rng.uniform(.3, .9)) for _ in range(gears)]
        self.steam = [(rng.random(), rng.random(), rng.uniform(.2, .6)) for _ in range(puffs)]
