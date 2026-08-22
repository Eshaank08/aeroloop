"""Seeded randomized wind scenarios. Same seed always yields the same wind profile."""

import math
import random
from dataclasses import dataclass


@dataclass
class WindScenario:
    seed: int
    base: tuple            # steady wind acceleration, m/s^2
    gust_dir: tuple        # unit direction of the gust
    gust_peak: float       # peak gust acceleration, m/s^2
    gust_start_s: float
    gust_duration_s: float

    def at(self, t: float) -> tuple:
        """Wind acceleration at time t: steady base plus a smooth gust envelope."""
        if self.gust_start_s <= t <= self.gust_start_s + self.gust_duration_s:
            phase = (t - self.gust_start_s) / self.gust_duration_s
            envelope = math.sin(math.pi * phase)  # 0 -> 1 -> 0
            g = self.gust_peak * envelope
        else:
            g = 0.0
        return tuple(self.base[i] + self.gust_dir[i] * g for i in range(3))


def _random_unit(rng) -> tuple:
    while True:
        v = (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))
        mag = math.sqrt(sum(c * c for c in v))
        if mag > 1e-6:
            return tuple(c / mag for c in v)


def make_scenario(seed: int) -> WindScenario:
    rng = random.Random(seed)
    base_dir = _random_unit(rng)
    base_mag = rng.uniform(0.0, 3.0)
    return WindScenario(
        seed=seed,
        base=tuple(c * base_mag for c in base_dir),
        gust_dir=_random_unit(rng),
        gust_peak=rng.uniform(2.0, 5.0),
        gust_start_s=rng.uniform(5.0, 60.0),
        gust_duration_s=rng.uniform(2.0, 8.0),
    )


def make_scenarios(count: int, base_seed: int = 1000) -> list:
    return [make_scenario(base_seed + i) for i in range(count)]
