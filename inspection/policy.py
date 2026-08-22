"""Allow-list and validation for re-capture requests."""

from __future__ import annotations

import math

from sim.limits import Limits
from viz.mission import Mission
from inspection.schema import MissionLeg, PolicyViolation, RequestedCapture

MAX_RETRY = 1
MAX_DWELL = 10.0
HOME_POSITION = (0.0, 0.0, 6.0)

ALLOWED_PRIMITIVES = frozenset(("capture_closeup", "capture_orbit", "quiet_hover", "return_home"))


class PolicyValidator:
    """Stateful validator: convert requested captures into bounded missions.

    The validator tracks retries and rejects anything outside the allow-list.
    """

    def __init__(self, max_retry: int = MAX_RETRY, home: tuple[float, float, float] = HOME_POSITION):
        self.retries: dict[int, int] = {}
        self.max_retry = max_retry
        self.home = home

    def _waypoints_for_orbit(self, request: RequestedCapture, nacelle):
        indexes = request.waypoint_indexes
        per_ring = max(nacelle.per_ring, 1)
        rings = {idx // per_ring for idx in indexes}
        if len(rings) != 1:
            raise PolicyViolation("capture_orbit must target exactly one ring")
        return [nacelle.waypoints()[idx] for idx in indexes]

    def _clone_limits(self, limits: Limits, constraint_speed: float | None, time_budget_s: float) -> Limits:
        max_speed = limits.max_speed
        if constraint_speed is not None:
            if not (0 < constraint_speed <= limits.max_speed):
                raise PolicyViolation(
                    f"max_speed constraint {constraint_speed} is outside (0, {limits.max_speed}]"
                )
            max_speed = constraint_speed
        # Never extend the budget, only shrink it for follow-up legs.
        return Limits(
            max_accel=limits.max_accel,
            max_speed=max_speed,
            time_budget_s=time_budget_s,
            dt=limits.dt,
        )

    def validate(
        self,
        request: RequestedCapture,
        nacelle,
        limits: Limits,
        start_position: tuple[float, float, float],
        wind_seed: int,
        wind_scale: float,
        remaining_time_s: float,
        collision: bool = False,
    ) -> MissionLeg:
        if collision:
            raise PolicyViolation("cannot re-capture after a collision")

        primitive = request.primitive
        if primitive not in ALLOWED_PRIMITIVES:
            raise PolicyViolation(f"unknown primitive {primitive!r}")

        if primitive != "return_home" and not request.waypoint_indexes:
            raise PolicyViolation("request must include at least one waypoint index")

        total = len(nacelle.waypoints())
        for idx in request.waypoint_indexes:
            if not (0 <= idx < total):
                raise PolicyViolation(f"waypoint index {idx} is outside [0, {total})")

        # Retry budget: one follow-up attempt per waypoint in this milestone.
        # return_home does not consume a waypoint retry.
        if primitive != "return_home":
            for idx in request.waypoint_indexes:
                if self.retries.get(idx, 0) >= self.max_retry:
                    raise PolicyViolation(f"retry limit exceeded for waypoint {idx}")

        constraints = request.constraints or {}
        constraint_speed = constraints.get("max_speed_mps")
        minimum_dwell = constraints.get("minimum_dwell_s", 2.0)
        if not (0 < minimum_dwell <= MAX_DWELL):
            raise PolicyViolation(f"minimum_dwell_s {minimum_dwell} is outside (0, {MAX_DWELL}]")

        if remaining_time_s <= 0:
            raise PolicyViolation("no remaining flight time for re-capture")

        new_limits = self._clone_limits(limits, constraint_speed, remaining_time_s)

        def hover_duration(point: tuple[float, float, float], min_dwell: float) -> float:
            distance = math.dist(start_position, point)
            travel_s = (distance / max(new_limits.max_speed, 0.01)) * 1.8
            return min(remaining_time_s, travel_s + min_dwell * 2)

        if primitive == "capture_orbit":
            selected = self._waypoints_for_orbit(request, nacelle)
            mission = Mission(
                kind="sweep",
                waypoints=selected,
                start=start_position,
                wind_seed=wind_seed,
                wind_scale=wind_scale,
                label="re-capture orbit",
                text="",
                hold_duration=minimum_dwell,
            )
        elif primitive in ("capture_closeup", "quiet_hover"):
            if len(request.waypoint_indexes) > 1 and primitive == "capture_closeup":
                raise PolicyViolation("capture_closeup targets one waypoint in this milestone")
            point = nacelle.waypoints()[request.waypoint_indexes[0]]
            hold_dur = hover_duration(point, minimum_dwell)
            mission = Mission(
                kind="hover",
                waypoints=[point],
                start=start_position,
                wind_seed=wind_seed,
                wind_scale=wind_scale,
                label="re-capture closeup",
                text="",
                hold_duration=hold_dur,
            )
        elif primitive == "return_home":
            hold_dur = hover_duration(self.home, minimum_dwell)
            mission = Mission(
                kind="home",
                waypoints=[self.home],
                start=start_position,
                wind_seed=wind_seed,
                wind_scale=wind_scale,
                label="return home",
                text="",
                hold_duration=hold_dur,
            )
        else:
            raise PolicyViolation(f"unimplemented primitive {primitive!r}")

        if primitive != "return_home":
            for idx in request.waypoint_indexes:
                self.retries[idx] = self.retries.get(idx, 0) + 1

        return MissionLeg(
            mission=mission,
            limits=new_limits,
            nacelle=nacelle,
            request=request,
        )

