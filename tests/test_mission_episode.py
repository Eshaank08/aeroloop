"""MissionEpisode must fail closed if the controller misbehaves, at construction
time and not only while it is stepping. controller.py is Devin's file and is
explicitly untrusted (see CLAUDE.md); a bug in its __init__ must produce a
controller_exception outcome, never an unhandled crash of the mission process."""

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
