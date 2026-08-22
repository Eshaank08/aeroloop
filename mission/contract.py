"""The observation and action contract between the simulator and the mission agent.

Two rules govern this file. The observation packet carries only what a drone could
sense right now, never the seeded scenario, the future gust or the verifier answer.
The action packet carries only bounded mission primitives, never motor commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any

SCHEMA_VERSION = 1

PRIMITIVE_INSPECT = "inspect_waypoints"
PRIMITIVE_HOVER = "quiet_hover"
PRIMITIVE_RETURN_HOME = "return_home"
PRIMITIVE_COMPLETE = "complete"
PRIMITIVE_ABORT = "abort"

FLIGHT_PRIMITIVES = (PRIMITIVE_INSPECT, PRIMITIVE_HOVER, PRIMITIVE_RETURN_HOME)
TERMINAL_PRIMITIVES = (PRIMITIVE_COMPLETE, PRIMITIVE_ABORT)
ALLOWED_PRIMITIVES = FLIGHT_PRIMITIVES + TERMINAL_PRIMITIVES

# Dispositions the agent may claim. The independent verifier still runs afterwards
# and its answer, not this one, decides whether the inspection is acceptable.
CLAIM_COMPLETE = "complete"
CLAIM_INSUFFICIENT = "insufficient_evidence"
CLAIM_NEEDS_HUMAN = "needs_human"
CLAIM_ABORT = "abort"
CLAIMS = (CLAIM_COMPLETE, CLAIM_INSUFFICIENT, CLAIM_NEEDS_HUMAN, CLAIM_ABORT)

# Reasons an evidence gap exists, reported per waypoint from the camera gate.
GAP_NOT_VISITED = "not_visited"
GAP_TOO_FAR = "too_far"
GAP_NOT_AIMED = "camera_not_aimed"
GAP_NOT_STEADY = "shot_not_steady"

ACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "observation_id", "action_id", "primitive", "reason"],
    "properties": {
        "schema_version": {"type": "integer", "minimum": 1},
        "observation_id": {"type": "integer", "minimum": 0},
        "action_id": {"type": "string", "minLength": 1},
        "primitive": {"type": "string", "enum": list(ALLOWED_PRIMITIVES)},
        "waypoint_indexes": {"type": "array", "items": {"type": "integer", "minimum": 0}},
        "constraints": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "duration_s": {"type": "number", "exclusiveMinimum": 0},
                "max_speed_mps": {"type": "number", "exclusiveMinimum": 0},
            },
        },
        "reason": {"type": "string", "minLength": 1},
        "expected_evidence": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "claim": {"type": "string", "enum": list(CLAIMS)},
    },
}


class ContractError(ValueError):
    """Raised when a packet does not satisfy the local contract."""


@dataclass(frozen=True)
class WaypointEvidence:
    index: int
    inspected: bool = False
    approached: bool = False
    attempts: int = 0
    gap_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Observation:
    """What the drone can sense at one decision point."""

    schema_version: int = SCHEMA_VERSION
    mission_id: str = ""
    observation_id: int = 0
    previous_action_id: str = ""
    time_s: float = 0.0
    time_remaining_s: float = 0.0
    position_m: tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity_mps: tuple[float, float, float] = (0.0, 0.0, 0.0)
    speed_mps: float = 0.0
    tilt_deg: float = 0.0
    body_rate_rps: float = 0.0
    clearance_m: float = 0.0
    wind_estimate_mps2: float = 0.0
    evidence: list[WaypointEvidence] = field(default_factory=list)
    available_targets: list[int] = field(default_factory=list)
    allowed_primitives: list[str] = field(default_factory=lambda: list(ALLOWED_PRIMITIVES))
    events: list[dict] = field(default_factory=list)
    actions_used: int = 0
    actions_remaining: int = 0
    last_outcome: dict | None = None
    limits: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """One bounded mission primitive chosen by the agent."""

    schema_version: int = SCHEMA_VERSION
    observation_id: int = 0
    action_id: str = ""
    primitive: str = ""
    waypoint_indexes: list[int] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    expected_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    claim: str = ""
    chosen_by: str = "devin"


@dataclass(frozen=True)
class ActionOutcome:
    """What actually happened when an accepted action was executed."""

    action_id: str = ""
    executed: bool = False
    duration_s: float = 0.0
    newly_inspected: list[int] = field(default_factory=list)
    still_missing: list[int] = field(default_factory=list)
    failure: str | None = None
    end_position_m: tuple[float, float, float] = (0.0, 0.0, 0.0)
    notes: list[str] = field(default_factory=list)


def observation_to_dict(observation: Observation) -> dict:
    return {
        "schema_version": observation.schema_version,
        "mission_id": observation.mission_id,
        "observation_id": observation.observation_id,
        "previous_action_id": observation.previous_action_id,
        "time_s": round(observation.time_s, 3),
        "time_remaining_s": round(observation.time_remaining_s, 3),
        "pose": {
            "position_m": [round(v, 4) for v in observation.position_m],
            "velocity_mps": [round(v, 4) for v in observation.velocity_mps],
            "speed_mps": round(observation.speed_mps, 4),
            "tilt_deg": round(observation.tilt_deg, 2),
            "body_rate_rps": round(observation.body_rate_rps, 4),
        },
        "flight": {
            "clearance_m": round(observation.clearance_m, 4),
            "wind_estimate_mps2": round(observation.wind_estimate_mps2, 4),
        },
        "evidence": [
            {
                "waypoint_index": item.index,
                "inspected": item.inspected,
                "approached": item.approached,
                "attempts": item.attempts,
                "gap_reasons": list(item.gap_reasons),
            }
            for item in observation.evidence
        ],
        "available_targets": list(observation.available_targets),
        "allowed_primitives": list(observation.allowed_primitives),
        "events": [dict(event) for event in observation.events],
        "budget": {
            "actions_used": observation.actions_used,
            "actions_remaining": observation.actions_remaining,
        },
        "limits": dict(observation.limits),
        "last_outcome": observation.last_outcome,
    }


def action_to_dict(action: Action) -> dict:
    return {
        "schema_version": action.schema_version,
        "observation_id": action.observation_id,
        "action_id": action.action_id,
        "primitive": action.primitive,
        "waypoint_indexes": list(action.waypoint_indexes),
        "constraints": dict(action.constraints),
        "reason": action.reason,
        "expected_evidence": list(action.expected_evidence),
        "confidence": action.confidence,
        "claim": action.claim,
        "chosen_by": action.chosen_by,
    }


def outcome_to_dict(outcome: ActionOutcome) -> dict:
    return {
        "action_id": outcome.action_id,
        "executed": outcome.executed,
        "duration_s": round(outcome.duration_s, 3),
        "newly_inspected": list(outcome.newly_inspected),
        "still_missing": list(outcome.still_missing),
        "failure": outcome.failure,
        "end_position_m": [round(v, 4) for v in outcome.end_position_m],
        "notes": list(outcome.notes),
    }


def packet_digest(payload: dict) -> str:
    """Stable hash of one observation or action, for the audit trail."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_action(payload: dict, *, chosen_by: str = "devin") -> Action:
    """Validate a structured action from the agent against the local contract.

    This is deliberately stricter than the JSON Schema sent to the model. The
    schema is a request; this function is the enforcement.
    """
    if not isinstance(payload, dict):
        raise ContractError("action must be a JSON object")

    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ContractError(f"unsupported action schema_version {version!r}")

    observation_id = payload.get("observation_id")
    if type(observation_id) is not int or observation_id < 0:
        raise ContractError("observation_id must be a non-negative integer")

    action_id = payload.get("action_id")
    if not isinstance(action_id, str) or not action_id.strip():
        raise ContractError("action_id must be a non-empty string")

    primitive = payload.get("primitive")
    if primitive not in ALLOWED_PRIMITIVES:
        raise ContractError(f"unknown primitive {primitive!r}")

    indexes = payload.get("waypoint_indexes", [])
    if not isinstance(indexes, list) or not all(type(i) is int and i >= 0 for i in indexes):
        raise ContractError("waypoint_indexes must be an array of non-negative integers")

    constraints = payload.get("constraints", {})
    if not isinstance(constraints, dict):
        raise ContractError("constraints must be an object")
    for key, value in constraints.items():
        if key not in ("duration_s", "max_speed_mps"):
            raise ContractError(f"unknown constraint {key!r}")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise ContractError(f"constraint {key} must be a positive number")

    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ContractError("reason must be a non-empty string")

    expected = payload.get("expected_evidence", [])
    if not isinstance(expected, list) or not all(isinstance(e, str) for e in expected):
        raise ContractError("expected_evidence must be an array of strings")

    confidence = payload.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ContractError("confidence must be a number")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ContractError("confidence must be between 0 and 1")

    claim = payload.get("claim", "")
    if claim and claim not in CLAIMS:
        raise ContractError(f"unknown claim {claim!r}")
    if primitive in TERMINAL_PRIMITIVES and not claim:
        raise ContractError(f"{primitive} must carry a claim")

    return Action(
        schema_version=SCHEMA_VERSION,
        observation_id=observation_id,
        action_id=action_id.strip(),
        primitive=primitive,
        waypoint_indexes=list(indexes),
        constraints=dict(constraints),
        reason=reason.strip(),
        expected_evidence=list(expected),
        confidence=float(confidence),
        claim=claim,
        chosen_by=chosen_by,
    )
