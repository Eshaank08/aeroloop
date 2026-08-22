"""The safety envelope rejects unsafe actions and never substitutes its own."""

import pytest

from mission.contract import SCHEMA_VERSION, parse_action
from mission.episode import MissionEpisode
from mission.safety import (
    MAX_ATTEMPTS_PER_WAYPOINT,
    MissionPolicyViolation,
    MissionSafetyEnvelope,
)


def _action(**overrides):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "observation_id": 1,
        "action_id": "action-1",
        "primitive": "inspect_waypoints",
        "waypoint_indexes": [1],
        "constraints": {"duration_s": 10.0},
        "reason": "collect the missing shot",
    }
    payload.update(overrides)
    return parse_action(payload)


@pytest.fixture
def setup():
    episode = MissionEpisode(seed=1000, authorised_indexes=[0, 1, 2, 3])
    observation = episode.observe()
    envelope = MissionSafetyEnvelope(
        authorised_indexes=episode.authorised_indexes,
        max_speed_mps=episode.params.max_speed,
    )
    return episode, observation, envelope


def test_accepts_an_action_inside_the_envelope(setup):
    episode, observation, envelope = setup
    decision = envelope.validate(_action(), observation, episode.time_remaining_s)
    assert decision.accepted
    assert decision.duration_s == 10.0


def test_rejects_a_stale_action(setup):
    episode, observation, envelope = setup
    with pytest.raises(MissionPolicyViolation, match="stale action"):
        envelope.validate(
            _action(observation_id=observation.observation_id - 1),
            observation,
            episode.time_remaining_s,
        )


def test_rejects_a_replayed_action_id(setup):
    episode, observation, envelope = setup
    envelope.validate(_action(), observation, episode.time_remaining_s)
    with pytest.raises(MissionPolicyViolation, match="duplicate action_id"):
        envelope.validate(_action(), observation, episode.time_remaining_s)


def test_rejects_a_waypoint_outside_the_authorised_sector(setup):
    episode, observation, envelope = setup
    with pytest.raises(MissionPolicyViolation, match="outside the authorised mission sector"):
        envelope.validate(
            _action(waypoint_indexes=[20]), observation, episode.time_remaining_s
        )


def test_rejects_an_over_long_action(setup):
    episode, observation, envelope = setup
    with pytest.raises(MissionPolicyViolation, match="exceeds"):
        envelope.validate(
            _action(constraints={"duration_s": 600.0}),
            observation,
            episode.time_remaining_s,
        )


def test_rejects_a_speed_above_the_vehicle_limit(setup):
    episode, observation, envelope = setup
    with pytest.raises(MissionPolicyViolation, match="exceeds the vehicle limit"):
        envelope.validate(
            _action(constraints={"max_speed_mps": 99.0}),
            observation,
            episode.time_remaining_s,
        )


def test_rejects_too_many_targets_in_one_action(setup):
    episode, observation, envelope = setup
    envelope.authorised = set(range(24))
    with pytest.raises(MissionPolicyViolation, match="exceeds"):
        envelope.validate(
            _action(waypoint_indexes=list(range(12))),
            observation,
            episode.time_remaining_s,
        )


def test_rejects_duplicate_waypoint_indexes_in_one_action(setup):
    """A repeated index must not be able to burn its attempt budget in one shot:
    parse_action does not dedupe, and attempts are only committed after validation,
    so each repetition would otherwise be checked against the same pre-mutation
    count and then increment the counter once per repetition."""
    episode, observation, envelope = setup
    with pytest.raises(MissionPolicyViolation, match="duplicates"):
        envelope.validate(
            _action(waypoint_indexes=[1, 1, 1]), observation, episode.time_remaining_s
        )
    assert envelope.attempts.get(1, 0) == 0


def test_enforces_the_per_waypoint_attempt_limit(setup):
    episode, observation, envelope = setup
    for attempt in range(MAX_ATTEMPTS_PER_WAYPOINT):
        envelope.validate(
            _action(action_id=f"action-{attempt}"), observation, episode.time_remaining_s
        )
    with pytest.raises(MissionPolicyViolation, match="attempts"):
        envelope.validate(_action(action_id="one-too-many"), observation, episode.time_remaining_s)


def test_rejects_any_action_once_time_is_gone(setup):
    _, observation, envelope = setup
    with pytest.raises(MissionPolicyViolation, match="no mission time remains"):
        envelope.validate(_action(), observation, 0.0)


def test_truncates_a_long_action_to_the_remaining_budget(setup):
    _, observation, envelope = setup
    decision = envelope.validate(
        _action(constraints={"duration_s": 30.0}), observation, 4.0
    )
    assert decision.accepted
    assert decision.duration_s == 4.0
