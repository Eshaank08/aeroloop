"""Jet engine nacelle geometry: the collision surface and the inspection waypoints.

The nacelle is modelled as a capped cylinder lying along the x axis. The drone must
visit waypoints arranged in rings around it without entering the keep-out volume
(cylinder radius plus safety margin).
"""

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Nacelle:
    axis_start: tuple = (0.0, 0.0, 0.0)
    axis_end: tuple = (4.5, 0.0, 0.0)
    radius: float = 1.6
    safety_margin: float = 0.5
    inspection_radius: float = 3.0
    rings: int = 3
    per_ring: int = 8
    waypoint_tolerance: float = 0.4

    @property
    def keep_out_radius(self) -> float:
        return self.radius + self.safety_margin

    def distance_to_surface(self, position) -> float:
        """Signed distance from `position` to the nacelle axis segment.

        Returns the perpendicular distance to the axis when alongside the nacelle, and
        the distance to the nearer cap centre when beyond either end.
        """
        px, py, pz = position
        ax, ay, az = self.axis_start
        bx, by, bz = self.axis_end
        abx, aby, abz = bx - ax, by - ay, bz - az
        apx, apy, apz = px - ax, py - ay, pz - az
        ab_len_sq = abx * abx + aby * aby + abz * abz
        t = 0.0 if ab_len_sq == 0 else (apx * abx + apy * aby + apz * abz) / ab_len_sq
        t = max(0.0, min(1.0, t))
        cx, cy, cz = ax + abx * t, ay + aby * t, az + abz * t
        return math.dist((px, py, pz), (cx, cy, cz))

    def is_collision(self, position) -> bool:
        return self.distance_to_surface(position) < self.keep_out_radius

    def waypoints(self) -> list:
        """Inspection points: `rings` rings along the nacelle, `per_ring` points each."""
        ax, _, _ = self.axis_start
        bx, _, _ = self.axis_end
        pts = []
        for i in range(self.rings):
            # rings spaced evenly along the nacelle, inset from the caps
            frac = (i + 1) / (self.rings + 1)
            x = ax + (bx - ax) * frac
            for j in range(self.per_ring):
                theta = 2 * math.pi * j / self.per_ring
                y = self.inspection_radius * math.cos(theta)
                z = self.inspection_radius * math.sin(theta)
                pts.append((x, y, z))
        return pts


DEFAULT_NACELLE = Nacelle()
