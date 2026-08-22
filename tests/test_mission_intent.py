"""A judge types a sentence. It must resolve to a defensible authorisation."""

import random

import pytest

from mission.intent import parse_mission_intent
from sim.aircraft_geometry import DEFAULT_NACELLE

WAYPOINTS = DEFAULT_NACELLE.waypoints()
AXIS_Z = (DEFAULT_NACELLE.axis_start[2] + DEFAULT_NACELLE.axis_end[2]) / 2.0
AXIS_X = (DEFAULT_NACELLE.axis_start[0] + DEFAULT_NACELLE.axis_end[0]) / 2.0


def _fixed_rng():
    return random.Random(7)


@pytest.mark.parametrize("sentence", [
    "inspect the lower end of the engine",
    "check the underside",
    "look at the belly of the nacelle",
    "inspect beneath the engine please",
])
def test_underside_phrasings_authorise_only_lower_waypoints(sentence):
    intent = parse_mission_intent(sentence, rng=_fixed_rng())
    assert intent.authorised_indexes
    for index in intent.authorised_indexes:
        assert WAYPOINTS[index][2] < AXIS_Z, f"{sentence!r} authorised a waypoint that is not below the axis"


@pytest.mark.parametrize("sentence,predicate", [
    ("inspect the top side", lambda p: p[2] > AXIS_Z),
    ("check the inlet", lambda p: p[0] < AXIS_X),
    ("inspect the exhaust end", lambda p: p[0] > AXIS_X),
    ("look at the port side", lambda p: p[1] > 0),
    ("inspect the starboard side", lambda p: p[1] < 0),
])
def test_named_regions_map_to_the_right_geometry(sentence, predicate):
    intent = parse_mission_intent(sentence, rng=_fixed_rng())
    assert intent.authorised_indexes
    assert all(predicate(WAYPOINTS[i]) for i in intent.authorised_indexes)


@pytest.mark.parametrize("sentence", [
    "inspect the whole nacelle",
    "take the drone from one corner to the other and inspect everything",
    "fly it from front to back",
    "do a full sweep",
    "top and bottom please",
])
def test_whole_nacelle_phrasings_authorise_everything(sentence):
    intent = parse_mission_intent(sentence, rng=_fixed_rng())
    assert len(intent.authorised_indexes) == len(WAYPOINTS)


def test_an_explicit_seed_is_honoured_and_not_random():
    intent = parse_mission_intent("full sweep, seed 1027", rng=_fixed_rng())
    assert intent.seed == 1027
    assert intent.seed_was_random is False


def test_an_unspecified_scene_is_random_but_reported():
    intent = parse_mission_intent("inspect the underside", rng=_fixed_rng())
    assert intent.seed_was_random is True
    assert intent.seed >= 10_000
    # Reproducible once reported: the same seed must rebuild the same mission.
    assert parse_mission_intent(f"inspect the underside seed {intent.seed}").seed == intent.seed


def test_a_seed_number_is_not_mistaken_for_a_ring():
    intent = parse_mission_intent("inspect ring 2, seed 3", rng=_fixed_rng())
    assert intent.seed == 3
    assert len(intent.authorised_indexes) == DEFAULT_NACELLE.per_ring
    assert min(intent.authorised_indexes) == DEFAULT_NACELLE.per_ring


def test_gibberish_falls_back_to_the_whole_nacelle_rather_than_nothing():
    """An unparsed sentence must not silently authorise an empty mission."""
    intent = parse_mission_intent("qwertyuiop", rng=_fixed_rng())
    assert len(intent.authorised_indexes) == len(WAYPOINTS)


def test_the_operators_words_are_preserved_for_the_agent():
    sentence = "inspect the lower end, be careful near the pylon"
    assert parse_mission_intent(sentence, rng=_fixed_rng()).text == sentence
