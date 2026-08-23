"""MissionEpisode must fail closed if the controller misbehaves, at construction
time and not only while it is stepping. controller.py is Devin's file and is
explicitly untrusted (see CLAUDE.md); a bug in its __init__ must produce a
controller_exception outcome, never an unhandled crash of the mission process."""

import math

import pytest

from mission.contract import SCHEMA_VERSION, parse_action
from mission.episode import EpisodeClosed, MissionEpisode


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


class _BrokenController:
    """Stands in for a controller.py whose __init__ raises."""

    def __init__(self, waypoints, nacelle, params):
        raise ValueError("boom: bad route geometry")


class _RecordingController:
    latest = None

    def __init__(self, waypoints, nacelle, params):
        self.waypoints = waypoints
        self.params = params
        self.transit_speed = 1.8
        self.approach_speed = 1.0
        self.arrive_speed = 1.4
        self.brake_speed = 1.4
        self.standoff_radius = 2.85
        self.retry_standoff_radius = 2.85
        type(self).latest = self

    def step(self, _time, _state):
        return (self.params.hover_thrust, 0.0, 0.0, 0.0)


def test_a_controller_that_raises_in_init_fails_closed_instead_of_crashing():
    episode = MissionEpisode(
        seed=1000, authorised_indexes=[0, 1, 2, 3], controller_cls=_BrokenController,
    )
    outcome = episode.act(_action(), 10.0)

    assert outcome.failure is not None
    assert outcome.failure.startswith("controller_exception")
    assert "boom" in outcome.failure
    assert episode.closed is True

    with pytest.raises(EpisodeClosed):
        episode.act(_action(action_id="action-2"), 10.0)


def test_agent_standoff_and_speed_reach_the_real_time_controller():
    episode = MissionEpisode(
        seed=1000, authorised_indexes=[1], controller_cls=_RecordingController,
    )
    action = _action(constraints={
        "duration_s": 0.04,
        "max_speed_mps": 0.6,
        "view_distance_m": 1.0,
    })

    episode.act(action, 0.04)

    controller = _RecordingController.latest
    assert controller.transit_speed == 0.6
    assert controller.approach_speed == 0.6
    viewpoint = controller.waypoints[0]
    assert math.hypot(viewpoint[1], viewpoint[2]) == pytest.approx(
        episode.nacelle.radius + 1.0
    )
    assert episode.last_execution["flight_waypoints"][0] == list(viewpoint)


@pytest.mark.parametrize("view_distance,speed", [(1.0, 0.8), (2.0, 1.6)])
def test_real_controller_captures_evidence_from_agent_selected_viewpoints(
    view_distance, speed,
):
    episode = MissionEpisode(seed=1000, authorised_indexes=[1])
    observation = episode.observe()
    action = parse_action({
        "schema_version": SCHEMA_VERSION,
        "observation_id": observation.observation_id,
        "action_id": f"view-{view_distance}",
        "primitive": "inspect_waypoints",
        "waypoint_indexes": [1],
        "constraints": {
            "duration_s": 40.0,
            "max_speed_mps": speed,
            "view_distance_m": view_distance,
        },
        "reason": "prove the chosen view reaches the controller and camera gate",
    })

    outcome = episode.act(action, 40.0)

    assert outcome.failure is None
    assert outcome.newly_inspected == [1]
    flight_point = episode.last_execution["flight_waypoints"][0]
    assert math.hypot(flight_point[1], flight_point[2]) == pytest.approx(
        episode.nacelle.radius + view_distance
    )
