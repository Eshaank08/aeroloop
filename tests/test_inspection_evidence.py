"""Unit tests for synthetic evidence derivation and deterministic quality scoring."""

import math

import pytest

from sim.aircraft_geometry import DEFAULT_NACELLE
from sim.limits import DEFAULT_LIMITS
from inspection.adaptive import AdaptiveRunner
from inspection.evidence import Capture, derive_captures, _hash_capture
from inspection.quality import QualityOracle, DEFAULT_THRESHOLDS
from inspection.schema import (
    CAPTURE_STATUS_GOOD,
    CAPTURE_STATUS_MARGINAL,
    CAPTURE_STATUS_MISSING,
    REASON_ANGLE,
    REASON_CLEARANCE,
    REASON_DWELL,
    REASON_MISSING,
    REASON_SPEED,
    REASON_WIND,
)
from viz.flightlab import fly
from viz.mission import Mission


def _make_trace(seed: int = 606076, wind_scale: float = 1.0):
    mission = Mission(
        kind="sweep",
        waypoints=list(DEFAULT_NACELLE.waypoints()),
        wind_seed=seed,
        wind_scale=wind_scale,
        label="sweep",
    )
    return fly(mission, nacelle=DEFAULT_NACELLE, limits=DEFAULT_LIMITS, stride=1)


def test_one_capture_per_visited_waypoint():
    trace = _make_trace()
    captures = derive_captures(trace, DEFAULT_NACELLE)
    assert len(captures) == len(DEFAULT_NACELLE.waypoints())
    for i, capture in enumerate(captures):
        assert capture.waypoint_index == i
        assert capture.synthetic is True
        assert capture.source == "synthetic_trace"


def test_capture_digest_changes_with_measurement():
    trace = _make_trace()
    captures = derive_captures(trace, DEFAULT_NACELLE)
    good = captures[0]
    mutated = Capture(**{**good.__dict__, "speed_mps": (good.speed_mps or 0.0) + 1.0})
    mutated = Capture(**{**mutated.__dict__, "sha256": _hash_capture(mutated)})
    assert good.sha256 != mutated.sha256


def test_missing_waypoint_is_missing():
    trace = {
        "frames": [],
        "waypoints": DEFAULT_NACELLE.waypoints(),
    }
    captures = derive_captures(trace, DEFAULT_NACELLE)
    for capture in captures:
        assert capture.captured_at_s is None
        assert capture.trace_frame_indexes == []


def test_missing_never_silently_good():
    oracle = QualityOracle()
    missing = Capture(capture_id="missing", source="synthetic_trace", synthetic=True)
    q = oracle.assess(missing)
    assert q.status == CAPTURE_STATUS_MISSING
    assert q.reasons == [REASON_MISSING]


def test_missing_hash_stable():
    missing = Capture(capture_id="missing", source="synthetic_trace", synthetic=True)
    missing = Capture(**{**missing.__dict__, "sha256": _hash_capture(missing)})
    missing2 = Capture(capture_id="missing", source="synthetic_trace", synthetic=True)
    missing2 = Capture(**{**missing2.__dict__, "sha256": _hash_capture(missing2)})
    assert missing.sha256 == missing2.sha256


def test_speed_boundary():
    oracle = QualityOracle()
    at = Capture(speed_mps=1.0, dwell_s=1.0, view_angle_deg=0.0, wind_mps=0.0, clearance_m=1.0, captured_at_s=0.0)
    over = Capture(speed_mps=1.001, dwell_s=1.0, view_angle_deg=0.0, wind_mps=0.0, clearance_m=1.0, captured_at_s=0.0)
    assert oracle.assess(at).status == CAPTURE_STATUS_GOOD
    assert oracle.assess(over).status == CAPTURE_STATUS_MARGINAL
    assert REASON_SPEED in oracle.assess(over).reasons


def test_view_angle_boundary():
    oracle = QualityOracle()
    at = Capture(speed_mps=0.0, dwell_s=1.0, view_angle_deg=40.0, wind_mps=0.0, clearance_m=1.0, captured_at_s=0.0)
    over = Capture(speed_mps=0.0, dwell_s=1.0, view_angle_deg=40.001, wind_mps=0.0, clearance_m=1.0, captured_at_s=0.0)
    assert oracle.assess(at).status == CAPTURE_STATUS_GOOD
    assert oracle.assess(over).status == CAPTURE_STATUS_MARGINAL
    assert REASON_ANGLE in oracle.assess(over).reasons


def test_dwell_boundary():
    oracle = QualityOracle()
    at = Capture(speed_mps=0.0, dwell_s=0.4, view_angle_deg=0.0, wind_mps=0.0, clearance_m=1.0, captured_at_s=0.0)
    under = Capture(speed_mps=0.0, dwell_s=0.399, view_angle_deg=0.0, wind_mps=0.0, clearance_m=1.0, captured_at_s=0.0)
    assert oracle.assess(at).status == CAPTURE_STATUS_GOOD
    assert oracle.assess(under).status == CAPTURE_STATUS_MARGINAL
    assert REASON_DWELL in oracle.assess(under).reasons


def test_wind_boundary():
    oracle = QualityOracle()
    at = Capture(speed_mps=0.0, dwell_s=1.0, view_angle_deg=0.0, wind_mps=5.0, clearance_m=1.0, captured_at_s=0.0)
    over = Capture(speed_mps=0.0, dwell_s=1.0, view_angle_deg=0.0, wind_mps=5.001, clearance_m=1.0, captured_at_s=0.0)
    assert oracle.assess(at).status == CAPTURE_STATUS_GOOD
    assert oracle.assess(over).status == CAPTURE_STATUS_MARGINAL
    assert REASON_WIND in oracle.assess(over).reasons


def test_clearance_boundary():
    oracle = QualityOracle()
    at = Capture(speed_mps=0.0, dwell_s=1.0, view_angle_deg=0.0, wind_mps=0.0, clearance_m=0.3, captured_at_s=0.0)
    under = Capture(speed_mps=0.0, dwell_s=1.0, view_angle_deg=0.0, wind_mps=0.0, clearance_m=0.299, captured_at_s=0.0)
    assert oracle.assess(at).status == CAPTURE_STATUS_GOOD
    assert oracle.assess(under).status == CAPTURE_STATUS_MARGINAL
    assert REASON_CLEARANCE in oracle.assess(under).reasons


def test_multiple_reasons_reduce_score():
    oracle = QualityOracle()
    capture = Capture(speed_mps=2.0, dwell_s=0.1, view_angle_deg=60.0, wind_mps=6.0, clearance_m=0.1, captured_at_s=0.0)
    q = oracle.assess(capture)
    assert q.status == CAPTURE_STATUS_MARGINAL
    assert len(q.reasons) == 5
    assert q.score < 1.0


def test_one_seeded_case_improves_after_re_capture():
    runner = AdaptiveRunner(oracle=QualityOracle())
    result = runner.run("full sweep", DEFAULT_NACELLE, DEFAULT_LIMITS, seed=606076, wind_scale=1.0)
    initial_good = sum(1 for q in result.initial.quality if q.status == CAPTURE_STATUS_GOOD)
    final_good = sum(1 for q in result.final_quality if q.status == CAPTURE_STATUS_GOOD)
    assert final_good > initial_good
    assert any(c.capture_id.startswith("followup") for c in result.final_captures)


def test_one_seeded_case_remains_insufficient():
    runner = AdaptiveRunner(oracle=QualityOracle())
    result = runner.run("full sweep", DEFAULT_NACELLE, DEFAULT_LIMITS, seed=606076, wind_scale=1.0)
    from inspection.schema import DISPOSITION_INSUFFICIENT
    assert result.final_disposition == DISPOSITION_INSUFFICIENT


def _make_frame(t, p, v, clearance):
    return {
        "t": round(t, 3),
        "p": list(p),
        "v": list(v),
        "wind": [0.0, 0.0, 0.0],
        "clearance": clearance,
        "visited": 1,
    }


def test_opposite_facing_camera_is_oblique():
    """A camera pointing directly away from the surface must not score as 0 degrees."""
    waypoint = (1.125, 3.0, 0.0)
    outward = (0.0, 5.0, 0.0)
    frames = [_make_frame(i * 0.1, waypoint, outward, 0.9) for i in range(10)]
    trace = {"frames": frames, "waypoints": [waypoint]}
    captures = derive_captures(trace, DEFAULT_NACELLE)
    assert len(captures) == 1
    cap = captures[0]
    assert cap.view_angle_deg is not None
    assert cap.view_angle_deg > 90
    q = QualityOracle().assess(cap)
    assert REASON_ANGLE in q.reasons


def test_disconnected_visits_use_longest_continuous_window():
    """Dwell and other metrics must come from a single continuous visit, not a sum."""
    waypoint = (1.125, 3.0, 0.0)
    frames = [_make_frame(i * 0.1, waypoint, (0.0, 0.0, 0.0), 0.9) for i in range(5)]
    # add far frames so frame indexes are not consecutive
    frames.extend([_make_frame(0.6 + i * 0.1, (10.0, 10.0, 10.0), (1.0, 0.0, 0.0), 8.0) for i in range(5)])
    frames.extend([_make_frame(1.2 + i * 0.1, waypoint, (0.0, 0.0, 0.0), 0.9) for i in range(3)])
    trace = {"frames": frames, "waypoints": [waypoint]}
    captures = derive_captures(trace, DEFAULT_NACELLE)
    assert len(captures) == 1
    cap = captures[0]
    # longest window is 5 frames at dt=0.1 -> 0.5 s dwell, not 8 frames total
    assert abs(cap.dwell_s - 0.5) < 1e-6
    assert cap.view_angle_deg is not None and cap.view_angle_deg < 10
    assert cap.speed_mps == 0.0
