"""Tests for the live Devin planner boundary without external API access."""

import dataclasses

import pytest

from inspection.devin import (
    DevinAPIError,
    DevinClient,
    DevinOutputError,
    DevinRecapturePlanner,
)
from inspection.adaptive import AdaptiveRunner
from inspection.artifact import build_artifact
from inspection.quality import QualityOracle
from inspection.schema import (
    CAPTURE_STATUS_GOOD,
    CAPTURE_STATUS_MARGINAL,
    DISPOSITION_INSUFFICIENT,
    DISPOSITION_PASS,
    QualityResult,
)
from inspection.work_order import parse_work_order
from sim.aircraft_geometry import DEFAULT_NACELLE
from sim.limits import DEFAULT_LIMITS


class AllGoodOracle(QualityOracle):
    """Forces a clean initial sweep so disposition depends only on planner health."""

    def assess_all(self, captures):
        return [
            dataclasses.replace(q, status=CAPTURE_STATUS_GOOD)
            for q in super().assess_all(captures)
        ]


def _dead_transport(method, url, key, payload, timeout_s):
    raise DevinAPIError("Devin API request failed")


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, key, payload, timeout_s):
        self.calls.append({
            "method": method,
            "url": url,
            "key": key,
            "payload": payload,
            "timeout_s": timeout_s,
        })
        return self.responses.pop(0)


def _client(transport, **kwargs):
    return DevinClient(
        "secret-test-key",
        "org-test",
        transport=transport,
        poll_interval_s=0,
        sleeper=lambda _: None,
        **kwargs,
    )


def test_devin_planner_creates_structured_session_and_parses_action():
    transport = FakeTransport([
        {
            "session_id": "session-123",
            "url": "https://app.devin.ai/sessions/session-123",
            "status": "new",
        },
        {
            "session_id": "session-123",
            "url": "https://app.devin.ai/sessions/session-123",
            "status": "exit",
            "status_detail": "finished",
            "structured_output": {
                "requests": [{
                    "request_id": "devin-recap-10",
                    "waypoint_indexes": [10],
                    "primitive": "quiet_hover",
                    "reason_codes": ["view_angle_too_oblique"],
                    "constraints": {"max_speed_mps": 0.4, "minimum_dwell_s": 3.0},
                }]
            },
        },
    ])
    planner = DevinRecapturePlanner(_client(transport), max_acu_limit=4)
    requests = planner.plan(
        [QualityResult(
            capture_id="initial-wp010-42",
            status=CAPTURE_STATUS_MARGINAL,
            score=0.6,
            reasons=["view_angle_too_oblique"],
        )],
        {
            "seed": 42,
            "work_order": "inspect top side",
            "allowed_waypoint_indexes": [1, 2, 3, 9, 10, 11],
        },
    )

    assert len(requests) == 1
    assert requests[0].requested_by == "devin"
    assert requests[0].waypoint_indexes == [10]
    assert requests[0].primitive == "quiet_hover"
    assert planner.metadata["session_id"] == "session-123"

    create = transport.calls[0]
    assert create["method"] == "POST"
    assert create["payload"]["structured_output_required"] is True
    assert create["payload"]["structured_output_schema"]["required"] == ["requests"]
    assert create["payload"]["max_acu_limit"] == 4
    # Authentication stays in the HTTP boundary, never in the prompt payload.
    assert "secret-test-key" not in str(create["payload"])


def test_devin_planner_rejects_invalid_structured_output():
    transport = FakeTransport([
        {"session_id": "session-bad", "status": "new"},
        {
            "session_id": "session-bad",
            "status": "exit",
            "status_detail": "finished",
            "structured_output": {"requests": "not-an-array"},
        },
    ])
    planner = DevinRecapturePlanner(_client(transport))
    with pytest.raises(DevinOutputError, match="requests array"):
        planner.plan([], {"seed": 1, "allowed_waypoint_indexes": []})


def test_devin_client_fails_closed_on_remote_error():
    transport = FakeTransport([
        {"session_id": "session-error", "status": "new"},
        {
            "session_id": "session-error",
            "status": "suspended",
            "status_detail": "out_of_credits",
        },
    ])
    with pytest.raises(DevinAPIError, match="out_of_credits"):
        _client(transport).run_structured(
            "prompt",
            {"type": "object"},
            title="test",
        )


def test_devin_client_times_out_on_a_stuck_session():
    """A session that never errors and never finishes -- just hangs -- must still
    produce a safe stop. This is the realistic network-failure shape (a dropped
    connection or a stalled agent), not just an immediate API error, and it was
    previously untested: every other test's fake transport reaches a terminal
    status within one or two calls."""
    transport = FakeTransport([
        {"session_id": "session-stuck", "status": "running"},
    ])
    clock_values = iter([0.0, 999.0])
    client = DevinClient(
        "secret-test-key",
        "org-test",
        transport=transport,
        poll_interval_s=0,
        sleeper=lambda _: None,
        clock=lambda: next(clock_values),
        timeout_s=150.0,
    )
    with pytest.raises(DevinAPIError, match="timed out"):
        client.run_structured("prompt", {"type": "object"}, title="test")


def test_stuck_session_never_reports_pass_on_a_clean_sweep():
    """The timeout path must flow through the same fail-closed rule as a hard
    connection error: a hung planner cannot let an otherwise-clean sweep pass."""
    def _stuck_transport(method, url, key, payload, timeout_s):
        return {"session_id": "session-stuck", "status": "running"}

    clock_values = iter([0.0] + [999.0] * 10)
    client = DevinClient(
        "secret-test-key",
        "org-test",
        transport=_stuck_transport,
        poll_interval_s=0,
        sleeper=lambda _: None,
        clock=lambda: next(clock_values),
        timeout_s=150.0,
    )
    planner = DevinRecapturePlanner(client)
    work_order = parse_work_order("inspect top side, light wind seed 606076")
    result = AdaptiveRunner(planner=planner, oracle=AllGoodOracle()).run(
        work_order.label,
        work_order.nacelle,
        work_order.limits,
        seed=work_order.seed,
        wind_scale=work_order.wind_scale,
        selected_waypoints=work_order.selected_waypoints,
        selected_waypoint_indexes=work_order.selected_waypoint_indexes,
    )

    assert result.planner_failed is True
    assert result.final_disposition == DISPOSITION_INSUFFICIENT

    artifact = build_artifact(result, nacelle=work_order.nacelle, limits=work_order.limits)
    assert artifact["final_disposition"] == DISPOSITION_INSUFFICIENT
    assert artifact["planner_record"]["failed"] is True


def test_devin_client_requires_credentials(monkeypatch):
    monkeypatch.delenv("DEVIN_API_KEY", raising=False)
    monkeypatch.delenv("DEVIN_ORG_ID", raising=False)
    with pytest.raises(ValueError, match="DEVIN_API_KEY"):
        DevinClient.from_env()


def test_devin_planner_drives_adaptive_leg_and_artifact_metadata():
    transport = FakeTransport([
        {"session_id": "session-live", "url": "https://app.devin.ai/sessions/session-live", "status": "new"},
        {
            "session_id": "session-live",
            "url": "https://app.devin.ai/sessions/session-live",
            "status": "exit",
            "status_detail": "finished",
            "structured_output": {
                "requests": [{
                    "request_id": "devin-closeup-0",
                    "waypoint_indexes": [0],
                    "primitive": "capture_closeup",
                    "reason_codes": ["speed_too_high"],
                    "constraints": {"max_speed_mps": 0.5, "minimum_dwell_s": 2.0},
                }]
            },
        },
    ])
    planner = DevinRecapturePlanner(_client(transport))
    result = AdaptiveRunner(planner=planner, oracle=QualityOracle()).run(
        "full sweep",
        DEFAULT_NACELLE,
        DEFAULT_LIMITS,
        seed=606076,
        wind_scale=1.0,
    )

    assert result.accepted
    assert result.accepted[0].requested_by == "devin"
    assert result.followup_legs[0]["waypoints"] == [DEFAULT_NACELLE.waypoints()[0]]
    artifact = build_artifact(result, nacelle=DEFAULT_NACELLE, limits=DEFAULT_LIMITS)
    assert artifact["planner_record"]["planner"] == "DevinRecapturePlanner"
    assert artifact["planner_record"]["metadata"]["session_id"] == "session-live"
    assert artifact["planner_record"]["failed"] is False


def test_unreachable_devin_never_reports_pass_on_a_clean_sweep():
    """A mission whose planner never answered cannot claim a disposition of PASS."""
    planner = DevinRecapturePlanner(_client(_dead_transport))
    work_order = parse_work_order("inspect top side, light wind seed 606076")
    result = AdaptiveRunner(planner=planner, oracle=AllGoodOracle()).run(
        work_order.label,
        work_order.nacelle,
        work_order.limits,
        seed=work_order.seed,
        wind_scale=work_order.wind_scale,
        selected_waypoints=work_order.selected_waypoints,
        selected_waypoint_indexes=work_order.selected_waypoint_indexes,
    )

    assert all(q.status == CAPTURE_STATUS_GOOD for q in result.final_quality)
    assert result.planner_failed is True
    assert result.final_disposition == DISPOSITION_INSUFFICIENT
    assert any("planner failure" in v for v in result.policy_violations)

    artifact = build_artifact(result, nacelle=work_order.nacelle, limits=work_order.limits)
    assert artifact["final_disposition"] == DISPOSITION_INSUFFICIENT
    assert artifact["planner_record"]["failed"] is True


def test_healthy_planner_on_a_clean_sweep_still_passes():
    """The fail-closed rule must not block a mission whose planner did answer."""
    transport = FakeTransport([
        {"session_id": "session-clean", "status": "new"},
        {
            "session_id": "session-clean",
            "status": "exit",
            "status_detail": "finished",
            "structured_output": {"requests": []},
        },
    ])
    planner = DevinRecapturePlanner(_client(transport))
    work_order = parse_work_order("inspect top side, light wind seed 606076")
    result = AdaptiveRunner(planner=planner, oracle=AllGoodOracle()).run(
        work_order.label,
        work_order.nacelle,
        work_order.limits,
        seed=work_order.seed,
        wind_scale=work_order.wind_scale,
        selected_waypoints=work_order.selected_waypoints,
        selected_waypoint_indexes=work_order.selected_waypoint_indexes,
    )

    assert result.planner_failed is False
    assert result.final_disposition == DISPOSITION_PASS


def test_devin_cannot_fly_outside_the_authorised_sector():
    """Mission authority is the human's: a top-side work order bounds every action."""
    transport = FakeTransport([
        {"session_id": "session-escape", "status": "new"},
        {
            "session_id": "session-escape",
            "status": "exit",
            "status_detail": "finished",
            "structured_output": {
                "requests": [{
                    "request_id": "devin-escape-20",
                    "waypoint_indexes": [20],
                    "primitive": "capture_closeup",
                    "reason_codes": ["view_angle_too_oblique"],
                    "constraints": {"max_speed_mps": 0.5, "minimum_dwell_s": 2.0},
                }]
            },
        },
    ])
    planner = DevinRecapturePlanner(_client(transport))
    work_order = parse_work_order("inspect top side, light wind seed 606076")
    authorised = set(work_order.selected_waypoint_indexes or [])
    assert 20 not in authorised

    result = AdaptiveRunner(planner=planner, oracle=QualityOracle()).run(
        work_order.label,
        work_order.nacelle,
        work_order.limits,
        seed=work_order.seed,
        wind_scale=work_order.wind_scale,
        selected_waypoints=work_order.selected_waypoints,
        selected_waypoint_indexes=work_order.selected_waypoint_indexes,
    )

    assert result.requested and result.requested[0].waypoint_indexes == [20]
    assert result.accepted == []
    assert result.followup_legs == []
    assert any("authorised mission sector" in v for v in result.policy_violations)
