"""The safety envelope between the agent and the vehicle.

Every action the agent proposes passes through here. This layer may reject an
action, and it reports the rejection back to the agent so the agent can choose
again. It never substitutes an inspection target of its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mission.contract import (
    FLIGHT_PRIMITIVES,
    PRIMITIVE_HOVER,
    PRIMITIVE_INSPECT,
    PRIMITIVE_RETURN_HOME,
    TERMINAL_PRIMITIVES,
    Action,
)

POLICY_VERSION = "mission-envelope-v1"

DEFAULT_DURATION_S = 20.0
MAX_DURATION_S = 40.0
MAX_TARGETS_PER_ACTION = 8
MAX_ATTEMPTS_PER_WAYPOINT = 3


class MissionPolicyViolation(Exception):
    """Raised when a proposed action is outside the safety envelope."""


@dataclass
class Decision:
    accepted: bool = False
    duration_s: float = 0.0
    reason: str = ""
    action_id: str = ""
    primitive: str = ""
    waypoint_indexes: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "primitive": self.primitive,
            "waypoint_indexes": list(self.waypoint_indexes),
            "decision": "accepted" if self.accepted else "rejected",
            "duration_s": round(self.duration_s, 3),
            "reason": self.reason,
            "policy_version": POLICY_VERSION,
        }


class MissionSafetyEnvelope:
    """Stateful validator for one mission."""

    def __init__(
        self,
        authorised_indexes: list[int],
        max_speed_mps: float,
        max_attempts_per_waypoint: int = MAX_ATTEMPTS_PER_WAYPOINT,
        max_targets_per_action: int = MAX_TARGETS_PER_ACTION,
        max_duration_s: float = MAX_DURATION_S,
    ):
        self.authorised = set(authorised_indexes)
        self.max_speed_mps = max_speed_mps
        self.max_attempts_per_waypoint = max_attempts_per_waypoint
        self.max_targets_per_action = max_targets_per_action
        self.max_duration_s = max_duration_s
        self.seen_action_ids: set[str] = set()
        self.attempts: dict[int, int] = {}

    def limits(self, time_remaining_s: float) -> dict:
        """The bounds an action must satisfy, published to the agent every turn."""
        return {
            "policy_version": POLICY_VERSION,
            "max_action_duration_s": self.max_duration_s,
            "default_action_duration_s": DEFAULT_DURATION_S,
            "max_targets_per_action": self.max_targets_per_action,
            "max_attempts_per_waypoint": self.max_attempts_per_waypoint,
            "max_speed_mps": self.max_speed_mps,
            "mission_time_remaining_s": round(time_remaining_s, 3),
            "attempts_used": dict(sorted(self.attempts.items())),
        }

    def validate(self, action: Action, observation, time_remaining_s: float) -> Decision:
        decision = Decision(
            action_id=action.action_id,
            primitive=action.primitive,
            waypoint_indexes=list(action.waypoint_indexes),
        )

        if action.observation_id != observation.observation_id:
            raise MissionPolicyViolation(
                f"stale action: answers observation {action.observation_id}, "
                f"current observation is {observation.observation_id}"
            )
        if action.action_id in self.seen_action_ids:
            raise MissionPolicyViolation(f"duplicate action_id {action.action_id!r}")

        if action.primitive in TERMINAL_PRIMITIVES:
            self.seen_action_ids.add(action.action_id)
            decision.accepted = True
            decision.reason = f"terminal action, claim {action.claim}"
            return decision

        if action.primitive not in FLIGHT_PRIMITIVES:
            raise MissionPolicyViolation(f"unknown primitive {action.primitive!r}")

        if action.primitive in (PRIMITIVE_INSPECT, PRIMITIVE_HOVER):
            if not action.waypoint_indexes:
                raise MissionPolicyViolation(
                    f"{action.primitive} needs at least one waypoint index"
                )
            if len(action.waypoint_indexes) > self.max_targets_per_action:
                raise MissionPolicyViolation(
                    f"{len(action.waypoint_indexes)} targets exceeds the "
                    f"{self.max_targets_per_action} allowed in one action"
                )
            for index in action.waypoint_indexes:
                if index not in self.authorised:
                    raise MissionPolicyViolation(
                        f"waypoint {index} is outside the authorised mission sector"
                    )
                if self.attempts.get(index, 0) >= self.max_attempts_per_waypoint:
                    raise MissionPolicyViolation(
                        f"waypoint {index} has used its "
                        f"{self.max_attempts_per_waypoint} attempts"
                    )
        elif action.primitive == PRIMITIVE_RETURN_HOME and action.waypoint_indexes:
            raise MissionPolicyViolation("return_home does not take waypoint indexes")

        speed = action.constraints.get("max_speed_mps")
        if speed is not None and speed > self.max_speed_mps:
            raise MissionPolicyViolation(
                f"max_speed_mps {speed} exceeds the vehicle limit {self.max_speed_mps}"
            )

        duration = float(action.constraints.get("duration_s", DEFAULT_DURATION_S))
        if duration > self.max_duration_s:
            raise MissionPolicyViolation(
                f"duration_s {duration} exceeds the {self.max_duration_s}s bound "
                "on a single action"
            )
        if time_remaining_s <= 0.0:
            raise MissionPolicyViolation("no mission time remains")
        duration = min(duration, time_remaining_s)

        self.seen_action_ids.add(action.action_id)
        for index in action.waypoint_indexes:
            self.attempts[index] = self.attempts.get(index, 0) + 1

        decision.accepted = True
        decision.duration_s = duration
        decision.reason = "within envelope"
        return decision
