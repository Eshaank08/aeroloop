"""The autonomous mission loop, exercised against a fake Devin transport.

These tests spend no API credits. They cover the properties that matter for the
claim we are making: Devin chooses the actions, the envelope bounds them, and the
system fails closed when Devin cannot be reached.
"""

import json

import pytest

from inspection.devin import DevinAPIError, DevinClient, DevinMissionSession
from mission.agent import (
    DISPOSITION_ABORTED,
    DISPOSITION_INSUFFICIENT,
    DISPOSITION_PASS,
    DevinMissionPlanner,
    ScriptedPilot,
    run_mission,
)
from mission.contract import ACTION_SCHEMA, SCHEMA_VERSION
from mission.episode import MissionEpisode

SECTOR = [0, 1, 2, 3]


class FakeDevin:
    """A Devin session that answers observations with scripted structured output."""

    def __init__(self, answers, fail_after=None):
        self.answers = list(answers)
        self.fail_after = fail_after
        self.messages = []
        self.calls = 0
        self.created_payload = None

    def __call__(self, method, url, key, payload, timeout_s):
        self.calls += 1
        if method == "POST" and url.endswith("/sessions"):
            self.created_payload = payload
            return {"session_id": "session-mission", "url": "https://app.devin.ai/sessions/session-mission", "status": "running"}
        if method == "POST" and url.endswith("/messages"):
            self.messages.append(payload["message"])
            return {"ok": True}
        if self.fail_after is not None and len(self.answers) <= self.fail_after:
            raise DevinAPIError("Devin API request failed")
        if not self.answers:
            raise DevinAPIError("no scripted answer left")
        return {
            "session_id": "session-mission",
            "status": "running",
            "status_detail": "working",
            "structured_output": self.answers.pop(0),
        }


def _planner(transport):
    client = DevinClient(
        "secret-test-key", "org-test",
        transport=transport, poll_interval_s=0, sleeper=lambda _: None,
    )
    session = DevinMissionSession(client, ACTION_SCHEMA, title="test mission")
    return DevinMissionPlanner(session)


def _answer(observation_id, action_id, **overrides):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "observation_id": observation_id,
        "action_id": action_id,
        "primitive": "inspect_waypoints",
        "waypoint_indexes": SECTOR,
        "constraints": {"duration_s": 40.0},
        "reason": "collect the authorised sector",
        "confidence": 0.8,
    }
    payload.update(overrides)
    return payload


def test_devin_drives_a_complete_mission_and_the_verifier_agrees():
    transport = FakeDevin([
        _answer(1, "a1"),
        _answer(2, "a2", primitive="complete", waypoint_indexes=[], claim="complete",
                reason="sector fully inspected"),
    ])
    planner = _planner(transport)

    run = run_mission(planner, seed=1000, authorised_indexes=SECTOR)

    assert run.disposition == DISPOSITION_PASS
    assert run.agent_claim == "complete"
    assert run.verification["coverage"] == 1.0
    assert run.planner_failed is False
    assert run.planner_metadata["session_id"] == "session-mission"
    # The session is resumable and structured output is mandatory.
    assert transport.created_payload["resumable"] is True
    assert transport.created_payload["structured_output_required"] is True
    # Credentials never travel inside the prompt.
    assert "secret-test-key" not in json.dumps(transport.created_payload)


def test_every_observation_reaches_the_same_session():
    transport = FakeDevin([
        _answer(1, "a1", waypoint_indexes=[0, 1]),
        _answer(2, "a2", waypoint_indexes=[2, 3]),
        _answer(3, "a3", primitive="complete", waypoint_indexes=[], claim="complete",
                reason="done"),
    ])
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    assert run.disposition == DISPOSITION_PASS
    # First observation rides the session prompt, the rest are messages.
    assert len(transport.messages) == 2
    assert all("observation_id" in message for message in transport.messages)


def test_unreachable_devin_triggers_a_safe_stop_and_never_passes():
    transport = FakeDevin([], fail_after=0)
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    assert run.planner_failed is True
    assert run.safe_stop is True
    assert run.disposition == DISPOSITION_INSUFFICIENT
    assert run.verification["coverage"] < 1.0
    assert any("safe-stop" in step.get("action", {}).get("action_id", "") for step in run.steps)


def test_devin_losing_connectivity_mid_mission_stops_safely():
    transport = FakeDevin([_answer(1, "a1", waypoint_indexes=[0])], fail_after=0)
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    assert run.planner_failed is True
    assert run.safe_stop is True
    assert run.disposition == DISPOSITION_INSUFFICIENT
    # It flew the action Devin did choose, then stopped instead of continuing alone.
    assert run.verification["inspected_count"] >= 1
    assert run.verification["coverage"] < 1.0


def test_out_of_sector_action_is_rejected_and_devin_is_told_why():
    transport = FakeDevin([
        _answer(1, "a1", waypoint_indexes=[20]),
        _answer(2, "a2"),
        _answer(3, "a3", primitive="complete", waypoint_indexes=[], claim="complete",
                reason="done"),
    ])
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    assert any("outside the authorised mission sector" in r for r in run.rejections)
    # The rejection reason is fed back to the agent, not silently swallowed.
    assert any("previous_action_rejected" in message for message in transport.messages)
    assert run.disposition == DISPOSITION_PASS


def test_repeated_unsafe_actions_end_in_a_safe_stop():
    transport = FakeDevin([_answer(i, f"a{i}", waypoint_indexes=[20]) for i in range(1, 6)])
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    assert len(run.rejections) == 3
    assert run.safe_stop is True
    assert run.disposition == DISPOSITION_INSUFFICIENT


def test_malformed_structured_output_is_rejected_not_executed():
    transport = FakeDevin([
        {"schema_version": 1, "observation_id": 1, "action_id": "bad",
         "primitive": "drop_the_payload", "reason": "nope"},
        _answer(2, "a2"),
        _answer(3, "a3", primitive="complete", waypoint_indexes=[], claim="complete",
                reason="done"),
    ])
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    assert any("unknown primitive" in r for r in run.rejections)
    assert run.disposition == DISPOSITION_PASS


def test_agent_abort_is_honoured_and_recorded():
    transport = FakeDevin([
        _answer(1, "a1", primitive="abort", waypoint_indexes=[], claim="abort",
                reason="clearance looks unsafe"),
    ])
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    assert run.agent_claim == "abort"
    assert run.disposition == DISPOSITION_ABORTED
    assert run.safe_stop is True


def test_agent_claiming_complete_cannot_override_the_verifier():
    """The agent says complete with one waypoint untouched. The verifier decides."""
    transport = FakeDevin([
        _answer(1, "a1", waypoint_indexes=[0]),
        _answer(2, "a2", primitive="complete", waypoint_indexes=[], claim="complete",
                reason="I believe this is enough"),
    ])
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    assert run.agent_claim == "complete"
    assert run.verification["coverage"] < 1.0
    assert run.disposition == DISPOSITION_INSUFFICIENT


class IdleThenAnswer:
    """A session that goes idle holding stale output before answering.

    This is what the real API does between turns of a resumable session:
    `waiting_for_user` means "your turn", and `structured_output` can still hold
    the previous turn's answer for a poll or two. Reading either as failure aborts
    a healthy mission, which is exactly what happened on the first live run.
    """

    def __init__(self):
        self.polls = 0
        self.messages = []

    def __call__(self, method, url, key, payload, timeout_s):
        if method == "POST" and url.endswith("/sessions"):
            return {"session_id": "session-idle", "url": "u", "status": "running"}
        if method == "POST" and url.endswith("/messages"):
            self.messages.append(payload["message"])
            return {"ok": True}
        self.polls += 1
        if self.polls <= 3:
            return {
                "status": "running",
                "status_detail": "waiting_for_user",
                "structured_output": _answer(0, "stale"),
            }
        return {
            "status": "running",
            "status_detail": "waiting_for_user",
            "structured_output": _answer(
                1, "a1", primitive="complete", waypoint_indexes=[], claim="complete",
                reason="done",
            ),
        }


def test_idle_session_is_nudged_not_abandoned():
    transport = IdleThenAnswer()
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    assert run.planner_failed is False
    assert run.agent_claim == "complete"
    # It nudged rather than declaring the agent dead, and never executed the stale action.
    assert any("Structured output only" in message for message in transport.messages)
    assert all(
        step.get("action", {}).get("action_id") != "stale" for step in run.steps
    )


def test_observation_publishes_the_limits_the_agent_must_respect():
    transport = FakeDevin([
        _answer(1, "a1", primitive="complete", waypoint_indexes=[], claim="complete",
                reason="done"),
    ])
    run = run_mission(_planner(transport), seed=1000, authorised_indexes=SECTOR)

    limits = run.steps[0]["observation"]["limits"]
    assert limits["max_action_duration_s"] > 0
    assert limits["max_targets_per_action"] > 0
    assert limits["max_attempts_per_waypoint"] > 0
    assert limits["max_speed_mps"] > 0


def test_scripted_baseline_completes_the_full_nacelle():
    run = run_mission(ScriptedPilot(), seed=1000)

    assert run.disposition == DISPOSITION_PASS
    assert run.verification["inspected_count"] == 24
    assert run.planner_name == "scripted_baseline"


def test_mission_progress_reports_waiting_actions_and_completion():
    stages = []

    def record(stage, _run, _episode, step):
        stages.append((stage, None if step is None else step["observation_id"]))

    run = run_mission(
        ScriptedPilot(),
        seed=1000,
        authorised_indexes=SECTOR,
        on_progress=record,
    )

    assert run.disposition == DISPOSITION_PASS
    assert stages[0] == ("waiting_for_planner", 1)
    assert ("action_accepted", 1) in stages
    assert ("action_executed", 1) in stages
    assert stages[-1] == ("complete", None)


def test_broken_progress_sink_cannot_change_the_mission_result():
    def broken(*_args):
        raise RuntimeError("browser disconnected")

    run = run_mission(
        ScriptedPilot(),
        seed=1000,
        authorised_indexes=SECTOR,
        on_progress=broken,
    )

    assert run.disposition == DISPOSITION_PASS


def test_mission_artifact_hashes_every_observation_and_action():
    run = run_mission(ScriptedPilot(), seed=1000, authorised_indexes=SECTOR)
    payload = run.to_dict()

    assert payload["integrity_digest"]
    flown = [step for step in payload["steps"] if step.get("outcome")]
    assert flown
    for step in flown:
        assert step["observation_digest"]
        assert step["action_digest"]


def test_episode_is_deterministic_for_a_seed():
    first = run_mission(ScriptedPilot(), seed=1007, authorised_indexes=SECTOR).verification
    second = run_mission(ScriptedPilot(), seed=1007, authorised_indexes=SECTOR).verification
    assert first == second


def test_actions_cannot_run_past_the_mission_time_budget():
    episode = MissionEpisode(seed=1000, authorised_indexes=SECTOR)
    episode.t = episode.params.time_budget_s - 1.0
    run = run_mission(ScriptedPilot(), seed=1000, authorised_indexes=SECTOR, episode=episode)

    assert episode.t <= episode.params.time_budget_s
    assert run.disposition != DISPOSITION_PASS
