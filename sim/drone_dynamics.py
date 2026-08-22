"""Point-mass drone dynamics with acceleration control and wind disturbance.

Deliberately simple: position and velocity only. Real inspection drones are stabilised
well enough that a point-mass model with clamped acceleration is a fair abstraction for
path-level control, which is what we are verifying.
"""

import math

from .limits import Limits, DEFAULT_LIMITS


def _clamp_magnitude(vec, max_mag):
    mag = math.sqrt(sum(c * c for c in vec))
    if mag <= max_mag or mag == 0.0:
        return vec
    scale = max_mag / mag
    return tuple(c * scale for c in vec)


class Drone:
    def __init__(self, position=(0.0, 0.0, 6.0), limits: Limits = DEFAULT_LIMITS):
        self.position = tuple(position)
        self.velocity = (0.0, 0.0, 0.0)
        self.limits = limits

    def step(self, accel_cmd, wind):
        """Advance one tick. `accel_cmd` from the controller, `wind` from the scenario."""
        a = _clamp_magnitude(tuple(accel_cmd), self.limits.max_accel)
        total = tuple(a[i] + wind[i] for i in range(3))
        v = tuple(self.velocity[i] + total[i] * self.limits.dt for i in range(3))
        v = _clamp_magnitude(v, self.limits.max_speed)
        p = tuple(self.position[i] + v[i] * self.limits.dt for i in range(3))
        self.velocity = v
        self.position = p
        return p, v
