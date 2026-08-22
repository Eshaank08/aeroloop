"""An interactive simulator v2 episode: reset, observe, act, verify.

The one-shot verifier flies a whole sweep and grades it. A mission agent needs the
opposite: advance the world by one bounded action, hand back what the drone can
sense, and wait to be told what to do next.

The inner 50 Hz control law is always the controller Devin wrote. Nothing in this
file computes thrust or body rates. An action selects targets and bounds; the
controller flies them.
"""

from __future__ import annotations

import math

from sim.aircraft_geometry import DEFAULT_NACELLE
from sim.scenarios import make_scenario
from sim2.camera import camera_gate
from sim2.params import DEFAULT_QUAD
from sim2.quad_dynamics import QuadDrone, command_is_finite
from sim2.run_verifier import COVERAGE_THRESHOLD

from mission.contract import (
    ALLOWED_PRIMITIVES,
    GAP_NOT_AIMED,
    GAP_NOT_STEADY,
    GAP_NOT_VISITED,
    GAP_TOO_FAR,
    PRIMITIVE_HOVER,
    PRIMITIVE_INSPECT,
    PRIMITIVE_RETURN_HOME,
    Action,
    ActionOutcome,
    Observation,
    WaypointEvidence,
)
from mission.environment import (
    DRONE_GROUND_RADIUS_M,
    GROUND_Z_M,
    OBSTACLE_SAFETY_RADIUS_M,
    make_environment,
)

HOME_POSITION = (0.0, 0.0, 6.0)
GUST_EVENT_THRESHOLD = 3.0
FRAME_STRIDE = 2


def _norm(vector) -> float:
    return math.sqrt(sum(component * component for component in vector))


class EpisodeClosed(RuntimeError):
    """Raised when an action is submitted to an episode that has already ended."""


class MissionEpisode:
    """One seeded, resumable inspection flight driven action by action."""

    def __init__(
        self,
        seed: int,
        nacelle=DEFAULT_NACELLE,
        params=DEFAULT_QUAD,
        controller_cls=None,
        authorised_indexes: list[int] | None = None,
        mission_id: str = "",
    ):
        if controller_cls is None:
            from controller2 import Controller as controller_cls  # noqa: N813

        self.seed = seed
        self.nacelle = nacelle
        self.params = params
        self.controller_cls = controller_cls
        self.mission_id = mission_id or f"mission-{seed}"

        self.waypoints = list(nacelle.waypoints())
        every_index = list(range(len(self.waypoints)))
        self.authorised_indexes = sorted(
            set(authorised_indexes) if authorised_indexes is not None else every_index
        )

        self.scenario = make_scenario(seed)
        self.environment = make_environment(seed)
        self.drone = QuadDrone(params=params)
        self.t = 0.0
        self.inspected = {index: False for index in every_index}
        self.approached = {index: False for index in every_index}
        self.attempts = {index: 0 for index in every_index}
        self.gap_reasons = {index: [GAP_NOT_VISITED] for index in every_index}

        self.failure: str | None = None
        self.closed = False
        self.observation_id = 0
        self.actions_executed = 0
        self.frames: list[dict] = []
        self.pending_events: list[dict] = []
        self._wind_estimate = 0.0
        self._gust_reported = False
        self._visual_reported = False
        self._audio_reported = False
        self._minimum_ground_clearance = float("inf")
        self._obstacle_alerts = 0
        self._record_frame()

    # ---- sensing -------------------------------------------------------

    @property
    def time_remaining_s(self) -> float:
        return max(0.0, self.params.time_budget_s - self.t)

    def clearance_m(self) -> float:
        distance = self.nacelle.distance_to_surface(self.drone.state.position)
        return distance - self.nacelle.keep_out_radius

    def _tilt_deg(self) -> float:
        up = self.drone.state.attitude[2][2]
        return math.degrees(math.acos(max(-1.0, min(1.0, up))))

    def _estimate_wind(self, previous_velocity, previous_thrust_world) -> None:
        """Recover the disturbance the drone is fighting from its own motion.

        An accelerometer plus the vehicle model gives this in the real world, so it
        is fair to report. The seeded scenario itself is never exposed.
        """
        state = self.drone.state
        measured = tuple(
            (state.velocity[i] - previous_velocity[i]) / self.params.dt for i in range(3)
        )
        modelled = tuple(
            previous_thrust_world[i] / self.params.mass
            + (0.0, 0.0, -self.params.gravity)[i]
            - (self.params.drag_coeff / self.params.mass) * previous_velocity[i]
            for i in range(3)
        )
        residual = _norm(tuple(measured[i] - modelled[i] for i in range(3)))
        self._wind_estimate = 0.8 * self._wind_estimate + 0.2 * residual

    def _record_frame(self) -> None:
        state = self.drone.state
        sensors = self.environment.sample(self.t, state.position)
        wind = self.scenario.at(self.t)
        self._minimum_ground_clearance = min(
            self._minimum_ground_clearance, sensors["ground_clearance_m"]
        )
        self.frames.append({
            "t": round(self.t, 3),
            "p": [round(v, 4) for v in state.position],
            "v": [round(v, 4) for v in state.velocity],
            "R": [[round(v, 5) for v in row] for row in state.attitude],
            "thrust": round(state.thrust, 4),
            "wind": [round(v, 4) for v in wind],
            "sensors": sensors,
        })

    def _sense_environment(self) -> str | None:
        """Record current detections and enforce immediate onboard safety."""
        sample = self.environment.sample(self.t, self.drone.state.position)
        self._minimum_ground_clearance = min(
            self._minimum_ground_clearance, sample["ground_clearance_m"]
        )
        detections = sample["visual_detections"]
        if detections and not self._visual_reported:
            detection = detections[0]
            self.pending_events.append({
                "type": "visual_object_detected",
                "source": "synthetic_vision",
                "at_s": round(self.t, 3),
                **detection,
            })
            self._visual_reported = True
        if sample["audio"]["anomaly"] and not self._audio_reported:
            self.pending_events.append({
                "type": "acoustic_anomaly_detected",
                "source": "synthetic_audio",
                "at_s": round(self.t, 3),
                **sample["audio"],
            })
            self._audio_reported = True

        if sample["ground_clearance_m"] < 0.0:
            return "ground_contact"
        nearest = sample["nearest_object_m"]
        if nearest is not None and nearest < OBSTACLE_SAFETY_RADIUS_M:
            self._obstacle_alerts += 1
            self.pending_events.append({
                "type": "dynamic_obstacle_safety_stop",
                "source": "onboard_safety",
                "at_s": round(self.t, 3),
                "distance_m": nearest,
            })
            return "dynamic_obstacle_proximity"
        return None

    def _evidence(self) -> list[WaypointEvidence]:
        return [
            WaypointEvidence(
                index=index,
                inspected=self.inspected[index],
                approached=self.approached[index],
                attempts=self.attempts[index],
                gap_reasons=[] if self.inspected[index] else list(self.gap_reasons[index]),
            )
            for index in self.authorised_indexes
        ]

    def observe(
        self,
        previous_action_id: str = "",
        last_outcome: dict | None = None,
        actions_remaining: int = 0,
        limits: dict | None = None,
    ) -> Observation:
        self.observation_id += 1
        state = self.drone.state
        sensors = self.environment.sample(self.t, state.position)
        events = list(self.pending_events)
        self.pending_events = []
        if self._wind_estimate >= GUST_EVENT_THRESHOLD and not self._gust_reported:
            events.append({
                "type": "disturbance_detected",
                "wind_estimate_mps2": round(self._wind_estimate, 3),
            })
            self._gust_reported = True
        if self._wind_estimate < GUST_EVENT_THRESHOLD * 0.6:
            self._gust_reported = False

        return Observation(
            mission_id=self.mission_id,
            observation_id=self.observation_id,
            previous_action_id=previous_action_id,
            time_s=self.t,
            time_remaining_s=self.time_remaining_s,
            position_m=tuple(round(v, 4) for v in state.position),
            velocity_mps=tuple(round(v, 4) for v in state.velocity),
            speed_mps=_norm(state.velocity),
            tilt_deg=self._tilt_deg(),
            body_rate_rps=_norm(state.body_rates),
            clearance_m=self.clearance_m(),
            ground_clearance_m=sensors["ground_clearance_m"],
            wind_estimate_mps2=self._wind_estimate,
            perception={
                "synthetic": True,
                "visual_detections": sensors["visual_detections"],
                "audio": sensors["audio"],
            },
            evidence=self._evidence(),
            available_targets=[
                index for index in self.authorised_indexes if not self.inspected[index]
            ],
            allowed_primitives=list(ALLOWED_PRIMITIVES),
            events=events,
            actions_used=self.actions_executed,
            actions_remaining=actions_remaining,
            last_outcome=last_outcome,
            limits=dict(limits or {}),
        )

    # ---- acting --------------------------------------------------------

    def _score_gate(self, index: int) -> None:
        """Update evidence bookkeeping for one waypoint at the current tick."""
        if self.inspected[index]:
            return
        gate = camera_gate(self.waypoints[index], self.drone.state, self.nacelle)
        if gate.inspected:
            self.inspected[index] = True
            self.gap_reasons[index] = []
            return
        if gate.within_tolerance:
            self.approached[index] = True
            reasons = []
            if not gate.aimed:
                reasons.append(GAP_NOT_AIMED)
            if not gate.steady:
                reasons.append(GAP_NOT_STEADY)
            self.gap_reasons[index] = reasons or [GAP_TOO_FAR]
        elif not self.approached[index]:
            self.gap_reasons[index] = [GAP_TOO_FAR]

    def _fly(self, targets: list[int], duration_s: float, stop_when_inspected: bool) -> str | None:
        """Advance physics under Devin's controller for one bounded action."""
        try:
            controller = self.controller_cls(
                [self.waypoints[index] for index in targets],
                self.nacelle,
                self.params,
            )
        except Exception as exc:  # the controller is under test, not trusted
            return f"controller_exception: {type(exc).__name__}: {exc}"
        # Tick counting rather than float comparison, so an action can never
        # accumulate its way past the graded time budget.
        deadline = min(self.t + duration_s, self.params.time_budget_s)
        ticks_allowed = int(round((deadline - self.t) / self.params.dt))
        tick = 0
        while tick < ticks_allowed:
            try:
                command = controller.step(self.t, self.drone.state)
            except Exception as exc:  # the controller is under test, not trusted
                return f"controller_exception: {type(exc).__name__}: {exc}"
            if not command_is_finite(command):
                return "invalid_command"

            previous_velocity = self.drone.state.velocity
            previous_thrust_world = tuple(
                self.drone.state.attitude[i][2] * self.drone.state.thrust for i in range(3)
            )
            self.drone.step(command, self.scenario.at(self.t))
            self.t = round(self.t + self.params.dt, 9)
            tick += 1
            self._estimate_wind(previous_velocity, previous_thrust_world)

            environment_failure = self._sense_environment()
            if environment_failure:
                self._record_frame()
                return environment_failure

            if self.nacelle.is_collision(self.drone.state.position):
                self._record_frame()
                return "collision"
            if _norm(self.drone.state.velocity) > self.params.max_speed:
                self._record_frame()
                return "unsafe_speed"

            for index in self.authorised_indexes:
                self._score_gate(index)
            if tick % FRAME_STRIDE == 0:
                self._record_frame()
            if stop_when_inspected and all(self.inspected[index] for index in targets):
                break

        self._record_frame()
        return None

    def _home_target(self) -> list[int]:
        """The waypoint nearest home, used as the standoff for a safe return.

        Home is a position, not an inspection point, and only Devin's controller is
        allowed to fly the vehicle, so a safe return is expressed as holding the
        authorised waypoint closest to the home standoff.
        """
        return [min(
            self.authorised_indexes,
            key=lambda index: _norm(
                tuple(self.waypoints[index][i] - HOME_POSITION[i] for i in range(3))
            ),
        )]

    def act(self, action: Action, duration_s: float) -> ActionOutcome:
        if self.closed:
            raise EpisodeClosed("this episode has already ended")

        before = {index for index in self.authorised_indexes if self.inspected[index]}
        started_at = self.t

        if action.primitive == PRIMITIVE_INSPECT:
            targets = list(action.waypoint_indexes)
            stop_when_inspected = True
        elif action.primitive == PRIMITIVE_HOVER:
            targets = list(action.waypoint_indexes)
            stop_when_inspected = False
        elif action.primitive == PRIMITIVE_RETURN_HOME:
            targets = self._home_target()
            stop_when_inspected = False
        else:
            raise EpisodeClosed(f"{action.primitive} is not an executable flight primitive")

        for index in targets:
            self.attempts[index] = self.attempts.get(index, 0) + 1

        failure = self._fly(targets, duration_s, stop_when_inspected)
        self.actions_executed += 1
        if failure:
            self.failure = failure
            self.closed = True

        after = {index for index in self.authorised_indexes if self.inspected[index]}
        notes = []
        for index in targets:
            if index in self.authorised_indexes and not self.inspected[index]:
                notes.extend(
                    f"waypoint {index}: {reason}" for reason in self.gap_reasons[index]
                )
        if self.time_remaining_s <= 0.0:
            self.closed = True
            notes.append("mission time budget exhausted")

        return ActionOutcome(
            action_id=action.action_id,
            executed=True,
            duration_s=self.t - started_at,
            newly_inspected=sorted(after - before),
            still_missing=[i for i in self.authorised_indexes if not self.inspected[i]],
            failure=failure,
            end_position_m=tuple(round(v, 4) for v in self.drone.state.position),
            notes=notes,
        )

    def close(self) -> None:
        self.closed = True

    # ---- verdict -------------------------------------------------------

    def verify(self) -> dict:
        """Grade the episode independently of whatever the agent claimed.

        Thresholds come from the simulator v2 verifier and are not restated here,
        so the interactive path cannot drift into an easier bar than the batch path.
        """
        inspected = [self.inspected[index] for index in self.authorised_indexes]
        coverage = sum(inspected) / len(inspected) if inspected else 0.0
        passed = (
            coverage >= COVERAGE_THRESHOLD
            and self.failure is None
            and self.t <= self.params.time_budget_s
        )
        return {
            "verifier": "sim2-interactive-v1",
            "seed": self.seed,
            "coverage": round(coverage, 4),
            "coverage_threshold": COVERAGE_THRESHOLD,
            "inspected_count": sum(inspected),
            "waypoint_count": len(inspected),
            "authorised_indexes": list(self.authorised_indexes),
            "missing_indexes": [
                index for index in self.authorised_indexes if not self.inspected[index]
            ],
            "elapsed_s": round(self.t, 3),
            "time_budget_s": self.params.time_budget_s,
            "collision": self.failure == "collision",
            "ground_contact": self.failure == "ground_contact",
            "ground_z_m": GROUND_Z_M,
            "drone_ground_radius_m": DRONE_GROUND_RADIUS_M,
            "minimum_ground_clearance_m": round(self._minimum_ground_clearance, 3),
            "dynamic_obstacle_stop": self.failure == "dynamic_obstacle_proximity",
            "obstacle_alerts": self._obstacle_alerts,
            "failure": self.failure,
            "actions_executed": self.actions_executed,
            "passed": passed,
        }
