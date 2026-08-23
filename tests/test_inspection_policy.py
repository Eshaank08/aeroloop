"""Policy and rule-planner tests for the adaptive evidence loop."""

import pytest

from sim.aircraft_geometry import DEFAULT_NACELLE
from sim.limits import DEFAULT_LIMITS
from inspection.adaptive import RuleBasedRecapturePlanner
from inspection.policy import PolicyValidator, PolicyViolation
from inspection.schema import RequestedCapture


def _validator():
    return PolicyValidator(max_retry=1)


def test_unknown_primitive_rejected():
    validator = _validator()
    request = RequestedCapture(
        request_id="bad",
        waypoint_indexes=[0],
        primitive="fly_loop",
    )
    with pytest.raises(PolicyViolation):
        validator.validate(
            request,
            DEFAULT_NACELLE,
            DEFAULT_LIMITS,
            (0.0, 0.0, 6.0),
            606076,
            1.0,
            60.0,
        )


def test_excessive_dwell_rejected():
    validator = _validator()
    request = RequestedCapture(
        request_id="dwell",
        waypoint_indexes=[0],
        primitive="quiet_hover",
        constraints={"minimum_dwell_s": 11.0},
    )
    with pytest.raises(PolicyViolation):
        validator.validate(
            request,
            DEFAULT_NACELLE,
            DEFAULT_LIMITS,
            (0.0, 0.0, 6.0),
            606076,
            1.0,
            60.0,
        )


def test_unknown_waypoint_index_rejected():
    validator = _validator()
    request = RequestedCapture(
        request_id="idx",
        waypoint_indexes=[100],
        primitive="capture_closeup",
    )
    with pytest.raises(PolicyViolation):
        validator.validate(
            request,
            DEFAULT_NACELLE,
            DEFAULT_LIMITS,
            (0.0, 0.0, 6.0),
            606076,
            1.0,
            60.0,
        )


def test_retry_limit_rejected():
    validator = _validator()
    request = RequestedCapture(
        request_id="retry",
        waypoint_indexes=[0],
        primitive="capture_closeup",
    )
    validator.validate(
        request,
        DEFAULT_NACELLE,
        DEFAULT_LIMITS,
        (0.0, 0.0, 6.0),
        606076,
        1.0,
        60.0,
    )
    with pytest.raises(PolicyViolation, match="retry limit"):
        validator.validate(
            request,
            DEFAULT_NACELLE,
            DEFAULT_LIMITS,
            (0.0, 0.0, 6.0),
            606076,
            1.0,
            60.0,
        )


def test_collision_prevents_capture():
    validator = _validator()
    request = RequestedCapture(
        request_id="postcrash",
        waypoint_indexes=[0],
        primitive="capture_closeup",
    )
    with pytest.raises(PolicyViolation, match="collision"):
        validator.validate(
            request,
            DEFAULT_NACELLE,
            DEFAULT_LIMITS,
            (0.0, 0.0, 6.0),
            606076,
            1.0,
            60.0,
            collision=True,
        )


def test_orbit_multiple_rings_rejected():
    validator = _validator()
    request = RequestedCapture(
        request_id="orbit",
        waypoint_indexes=[0, 8],
        primitive="capture_orbit",
    )
    with pytest.raises(PolicyViolation, match="one ring"):
        validator.validate(
            request,
            DEFAULT_NACELLE,
            DEFAULT_LIMITS,
            (0.0, 0.0, 6.0),
            606076,
            1.0,
            60.0,
        )


def test_orbit_same_ring_accepted():
    validator = _validator()
    request = RequestedCapture(
        request_id="orbit",
        waypoint_indexes=[0, 1, 2],
        primitive="capture_orbit",
    )
    leg = validator.validate(
        request,
        DEFAULT_NACELLE,
        DEFAULT_LIMITS,
        (0.0, 0.0, 6.0),
        606076,
        1.0,
        60.0,
    )
    assert leg.mission.kind == "sweep"
    assert len(leg.mission.waypoints) == 3


def test_closeup_targets_one_waypoint():
    validator = _validator()
    request = RequestedCapture(
        request_id="closeup",
        waypoint_indexes=[0, 1],
        primitive="capture_closeup",
    )
    with pytest.raises(PolicyViolation):
        validator.validate(
            request,
            DEFAULT_NACELLE,
            DEFAULT_LIMITS,
            (0.0, 0.0, 6.0),
            606076,
            1.0,
            60.0,
        )


def test_excessive_speed_constraint_rejected():
    validator = _validator()
    request = RequestedCapture(
        request_id="fast",
        waypoint_indexes=[0],
        primitive="capture_closeup",
        constraints={"max_speed_mps": 10.0},
    )
    with pytest.raises(PolicyViolation):
        validator.validate(
            request,
            DEFAULT_NACELLE,
            DEFAULT_LIMITS,
            (0.0, 0.0, 6.0),
            606076,
            1.0,
            60.0,
        )


def test_rule_planner_requests_only_failed_waypoints():
    planner = RuleBasedRecapturePlanner()
    from inspection.schema import QualityResult, CAPTURE_STATUS_MARGINAL
    gaps = [
        QualityResult(capture_id="initial-wp005-606076", status=CAPTURE_STATUS_MARGINAL, reasons=["speed_too_high"]),
    ]
    context = {"seed": 606076, "capture_to_index": {"initial-wp005-606076": 5}}
    requests = planner.plan(gaps, context)
    assert len(requests) == 1
    assert requests[0].waypoint_indexes == [5]
    assert requests[0].primitive == "capture_closeup"


def test_return_home_flies_to_home_position():
    validator = PolicyValidator(max_retry=1, home=(0.0, 0.0, 6.0))
    request = RequestedCapture(
        request_id="home",
        waypoint_indexes=[],
        primitive="return_home",
    )
    start = (1.5, 3.0, 3.0)
    leg = validator.validate(
        request,
        DEFAULT_NACELLE,
        DEFAULT_LIMITS,
        start,
        606076,
        1.0,
        60.0,
    )
    assert leg.mission.kind == "home"
    assert leg.mission.start == start
    assert leg.mission.waypoints == [(0.0, 0.0, 6.0)]
    # return_home must not consume a waypoint retry slot.
    assert validator.retries == {}
