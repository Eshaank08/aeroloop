"""Deterministic test environment and clearly-labelled synthetic sensors.

This is not a camera, microphone, or bird detector.  It is a repeatable source of
real-world-like disturbances for the autonomous mission loop: a ground boundary,
one moving object, and an acoustic anomaly.  The seed makes every run reproducible,
while the mission agent receives only detections made at the current time.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random


GROUND_Z_M = -4.5
DRONE_GROUND_RADIUS_M = 0.25
OBSTACLE_SAFETY_RADIUS_M = 0.9


def _distance(left, right) -> float:
    return math.sqrt(sum((left[i] - right[i]) ** 2 for i in range(3)))


@dataclass(frozen=True)
class EnvironmentScenario:
    """One seeded moving-object and acoustic test scenario."""

    seed: int
    object_label: str
    object_start_s: float
    object_duration_s: float
    object_x_m: float
    object_z_m: float
    object_direction: int
    audio_peak_s: float
    audio_peak_db: float

    def object_position(self, time_s: float) -> tuple[float, float, float] | None:
        if not self.object_start_s <= time_s <= self.object_start_s + self.object_duration_s:
            return None
        progress = (time_s - self.object_start_s) / self.object_duration_s
        across = (-8.0 + 16.0 * progress) * self.object_direction
        bob = 0.2 * math.sin(progress * math.pi * 4.0)
        return (self.object_x_m, across, self.object_z_m + bob)

    def sample(self, time_s: float, vehicle_position) -> dict:
        """Return current simulated sensor readings, never the future schedule."""
        position = self.object_position(time_s)
        visual = []
        nearest = None
        if position is not None:
            nearest = _distance(position, vehicle_position)
            if nearest <= 12.0:
                confidence = max(0.55, min(0.98, 1.02 - nearest / 24.0))
                visual.append({
                    "label": self.object_label,
                    "confidence": round(confidence, 3),
                    "distance_m": round(nearest, 3),
                    "position_m": [round(value, 3) for value in position],
                    "synthetic": True,
                })

        audio_bump = math.exp(-((time_s - self.audio_peak_s) / 3.0) ** 2)
        level_db = 42.0 + (self.audio_peak_db - 42.0) * audio_bump
        return {
            "synthetic": True,
            "visual_detections": visual,
            "nearest_object_m": None if nearest is None else round(nearest, 3),
            "audio": {
                "level_db": round(level_db, 1),
                "anomaly": level_db >= 56.0,
                "label": "unexpected broadband noise" if level_db >= 56.0 else "normal rotor noise",
                "synthetic": True,
            },
            "ground_clearance_m": round(
                vehicle_position[2] - GROUND_Z_M - DRONE_GROUND_RADIUS_M, 3
            ),
        }


def make_environment(seed: int) -> EnvironmentScenario:
    """Build an unrehearsed but reproducible environment from a mission seed."""
    rng = random.Random(seed ^ 0xA3E0100)
    start = rng.uniform(8.0, 18.0)
    duration = rng.uniform(16.0, 24.0)
    return EnvironmentScenario(
        seed=seed,
        object_label=rng.choice(("bird", "loose inspection cover", "service drone")),
        object_start_s=start,
        object_duration_s=duration,
        object_x_m=rng.uniform(0.7, 3.8),
        object_z_m=rng.uniform(3.7, 5.1),
        object_direction=rng.choice((-1, 1)),
        audio_peak_s=start + duration * rng.uniform(0.35, 0.75),
        audio_peak_db=rng.uniform(59.0, 70.0),
    )
