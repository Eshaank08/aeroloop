"""Typed records and validation for the adaptive evidence loop."""

from dataclasses import dataclass, field
from typing import Any, Optional

CAPTURE_STATUS_GOOD = "good"
CAPTURE_STATUS_MARGINAL = "marginal"
CAPTURE_STATUS_MISSING = "missing"

REASON_SPEED = "speed_too_high"
REASON_ANGLE = "view_angle_too_oblique"
REASON_DWELL = "dwell_too_short"
REASON_WIND = "wind_too_high"
REASON_CLEARANCE = "clearance_too_low"
REASON_MISSING = "capture_missing"

DISPOSITION_PASS = "PASS"
DISPOSITION_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
DISPOSITION_ABORTED = "ABORTED"
DISPOSITION_AWAITING = "AWAITING_HUMAN_APPROVAL"
DISPOSITION_APPROVED = "APPROVED"


class InspectionError(Exception):
    """Raised when the inspection pipeline cannot continue safely."""


class PolicyViolation(Exception):
    """Raised when a requested capture is not allowed."""


@dataclass(frozen=True)
class Capture:
    schema_version: int = 1
    capture_id: str = ""
    source: str = "synthetic_trace"
    synthetic: bool = True
    waypoint_index: int = -1
    waypoint: tuple[float, float, float] = (0.0, 0.0, 0.0)
    captured_at_s: Optional[float] = None
    standoff_m: Optional[float] = None
    view_angle_deg: Optional[float] = None
    dwell_s: Optional[float] = None
    speed_mps: Optional[float] = None
    wind_mps: Optional[float] = None
    clearance_m: Optional[float] = None
    camera: tuple[float, float, float] = (0.0, 0.0, 1.0)
    trace_frame_indexes: list[int] = field(default_factory=list)
    sha256: str = ""


@dataclass(frozen=True)
class QualityResult:
    capture_id: str = ""
    status: str = CAPTURE_STATUS_MISSING
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    threshold_version: str = "synthetic-v1"


@dataclass(frozen=True)
class RequestedCapture:
    request_id: str = ""
    waypoint_indexes: list[int] = field(default_factory=list)
    primitive: str = ""
    reason_codes: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    requested_by: str = "rule_engine"


@dataclass(frozen=True)
class PlannerRecord:
    planner: str = ""
    input_gaps: list[dict] = field(default_factory=list)
    raw_output: list[dict] = field(default_factory=list)
    validated_output: list[dict] = field(default_factory=list)
    rejections: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FlightResult:
    trace: dict = field(default_factory=dict)
    captures: list[Capture] = field(default_factory=list)
    quality: list[QualityResult] = field(default_factory=list)


@dataclass(frozen=True)
class MissionLeg:
    mission: Any = None
    limits: Any = None
    nacelle: Any = None
    request: Optional[RequestedCapture] = None


@dataclass(frozen=True)
class AdaptiveResult:
    work_order: str = ""
    seed: int = 0
    wind_scale: float = 1.0
    synthetic: bool = True
    planner: str = "rule_engine"
    threshold_version: str = "synthetic-v1"
    initial: FlightResult = field(default_factory=FlightResult)
    gaps: list[QualityResult] = field(default_factory=list)
    requested: list[RequestedCapture] = field(default_factory=list)
    accepted: list[RequestedCapture] = field(default_factory=list)
    policy_violations: list[str] = field(default_factory=list)
    followup_legs: list[dict] = field(default_factory=list)
    followup_result: Optional[FlightResult] = None
    final_captures: list[Capture] = field(default_factory=list)
    final_quality: list[QualityResult] = field(default_factory=list)
    final_disposition: str = DISPOSITION_INSUFFICIENT
    collision: bool = False
    artifact_digest: str = ""
    generated_at_utc: str = ""
    run_label: str = ""
    threshold_values: dict = field(default_factory=dict)


@dataclass(frozen=True)
class InspectionArtifact:
    schema_version: int = 1
    synthetic: bool = True
    generated_at_utc: str = ""
    work_order: str = ""
    seed: int = 0
    wind_scale: float = 1.0
    nacelle: dict = field(default_factory=dict)
    limits: dict = field(default_factory=dict)
    controller: dict = field(default_factory=dict)
    threshold_version: str = "synthetic-v1"
    threshold_values: dict = field(default_factory=dict)
    policy_version: str = "allow-list-v1"
    initial_trace_digest: str = ""
    followup_trace_digest: str = ""
    captures: list[dict] = field(default_factory=list)
    quality: list[dict] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    requested_captures: list[dict] = field(default_factory=list)
    planner_record: dict = field(default_factory=dict)
    policy_decisions: list[dict] = field(default_factory=list)
    followup_results: list[dict] = field(default_factory=list)
    final_disposition: str = DISPOSITION_INSUFFICIENT
    approval: Optional[dict] = None
    integrity_digest: str = ""


def _to_plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, Capture):
        return capture_to_dict(value)
    if isinstance(value, QualityResult):
        return quality_to_dict(value)
    if isinstance(value, RequestedCapture):
        return request_to_dict(value)
    return value


def capture_to_dict(capture: Capture) -> dict:
    return _to_plain(capture.__dict__)


def quality_to_dict(quality: QualityResult) -> dict:
    return _to_plain(quality.__dict__)


def request_to_dict(request: RequestedCapture) -> dict:
    return _to_plain(request.__dict__)


def adaptive_to_dict(result: AdaptiveResult) -> dict:
    return _to_plain(result.__dict__)


def artifact_to_dict(artifact: InspectionArtifact) -> dict:
    return _to_plain(artifact.__dict__)
