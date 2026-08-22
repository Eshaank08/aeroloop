"""The action contract is the enforcement point, not the JSON Schema we send."""

import pytest

from mission.contract import (
    SCHEMA_VERSION,
    ContractError,
    Observation,
    observation_to_dict,
    packet_digest,
    parse_action,
)


def _valid(**overrides):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "observation_id": 3,
        "action_id": "action-3",
        "primitive": "inspect_waypoints",
        "waypoint_indexes": [1, 2],
        "constraints": {"duration_s": 12.0},
        "reason": "two waypoints still lack a steady shot",
        "confidence": 0.7,
    }
    payload.update(overrides)
    return payload


def test_parse_action_accepts_a_well_formed_action():
    action = parse_action(_valid())
    assert action.primitive == "inspect_waypoints"
    assert action.waypoint_indexes == [1, 2]
    assert action.chosen_by == "devin"


@pytest.mark.parametrize("overrides,message", [
    ({"schema_version": 2}, "schema_version"),
    ({"observation_id": -1}, "observation_id"),
    ({"observation_id": "3"}, "observation_id"),
    ({"action_id": "  "}, "action_id"),
    ({"primitive": "fly_wherever"}, "unknown primitive"),
    ({"waypoint_indexes": [1, "2"]}, "waypoint_indexes"),
    ({"constraints": {"duration_s": -1}}, "duration_s"),
    ({"constraints": {"motor_pwm": 1200}}, "unknown constraint"),
    ({"reason": ""}, "reason"),
    ({"confidence": 3}, "between 0 and 1"),
    ({"claim": "definitely_fine"}, "unknown claim"),
    ({"primitive": "complete", "claim": ""}, "must carry a claim"),
])
def test_parse_action_rejects_malformed_actions(overrides, message):
    with pytest.raises(ContractError, match=message):
        parse_action(_valid(**overrides))


def test_observation_never_carries_scenario_truth():
    """The agent must not be able to read the wind schedule out of an observation."""
    from mission.episode import MissionEpisode

    episode = MissionEpisode(seed=1000)
    packet = observation_to_dict(episode.observe())
    text = str(packet).lower()

    for leaked in ("gust_start", "gust_peak", "gust_dir", "scenario", "seed", "base"):
        assert leaked not in text, f"observation leaked {leaked}"
    assert "wind_estimate_mps2" in str(packet)


def test_packet_digest_is_stable_and_order_independent():
    left = packet_digest({"a": 1, "b": [1, 2]})
    right = packet_digest({"b": [1, 2], "a": 1})
    assert left == right
    assert left != packet_digest({"a": 1, "b": [2, 1]})


def test_observation_dict_shape():
    packet = observation_to_dict(Observation(mission_id="mission-1", observation_id=1))
    assert packet["schema_version"] == SCHEMA_VERSION
    assert set(packet) >= {
        "pose", "flight", "perception", "evidence", "available_targets", "budget"
    }
    assert "ground_clearance_m" in packet["flight"]
