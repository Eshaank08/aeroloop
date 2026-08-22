"""Turn an operator's plain sentence into an authorised mission.

The split here is deliberate. Two different things live in one sentence:

1. What the drone is allowed to touch. That is the operator's authority and it is
   resolved here, locally and deterministically, so the boundary is set by the
   human and is auditable before anything flies.
2. What to do inside that boundary. That is the agent's job. The raw sentence is
   handed to Devin unedited so it can decide order, batching, when to settle and
   when to re-capture.

Parsing the second half here would put a regex in charge of the mission, which is
the opposite of the point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import random
import re

from sim.aircraft_geometry import DEFAULT_NACELLE

# Seeds a judge has not seen. Missions default into this space so a random scene
# is genuinely unrehearsed, and the chosen seed is always reported back so any
# run can be reproduced exactly.
RANDOM_SEED_FLOOR = 10_000
RANDOM_SEED_CEILING = 999_999


@dataclass(frozen=True)
class MissionIntent:
    text: str = ""
    seed: int = 0
    seed_was_random: bool = False
    authorised_indexes: list[int] = field(default_factory=list)
    region: str = "the whole nacelle"
    max_actions: int = 12

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "seed": self.seed,
            "seed_was_random": self.seed_was_random,
            "authorised_indexes": list(self.authorised_indexes),
            "region": self.region,
            "waypoint_count": len(self.authorised_indexes),
            "max_actions": self.max_actions,
        }


def _seed_from(text: str, rng: random.Random) -> tuple[int, bool]:
    match = re.search(r"\bseeds?\s*(?:is|=|:)?\s*(\d{1,7})\b", text, re.IGNORECASE)
    if match:
        return int(match.group(1)), False
    match = re.search(r"\bscenario\s*(\d{1,7})\b", text, re.IGNORECASE)
    if match:
        return int(match.group(1)), False
    return rng.randint(RANDOM_SEED_FLOOR, RANDOM_SEED_CEILING), True


# Words an inspector would actually use, mapped onto the nacelle geometry.
_REGIONS = (
    ("bottom", ("bottom", "lower", "underside", "under side", "beneath", "belly")),
    ("top", ("top", "upper", "crown", "over the top")),
    ("left", ("left", "port")),
    ("right", ("right", "starboard")),
    ("front", ("front", "forward", "inlet", "intake", "lip", "nose")),
    ("aft", ("aft", "rear", "back", "exhaust", "nozzle", "tail")),
)


def _region_indexes(name: str, nacelle) -> list[int]:
    waypoints = nacelle.waypoints()
    axis_z = (nacelle.axis_start[2] + nacelle.axis_end[2]) / 2.0
    axis_x = (nacelle.axis_start[0] + nacelle.axis_end[0]) / 2.0
    eps = 1e-9
    tests = {
        "top": lambda p: p[2] > axis_z + eps,
        "bottom": lambda p: p[2] < axis_z - eps,
        "left": lambda p: p[1] > eps,
        "right": lambda p: p[1] < -eps,
        "front": lambda p: p[0] < axis_x - eps,
        "aft": lambda p: p[0] > axis_x + eps,
    }
    test = tests[name]
    return [index for index, point in enumerate(waypoints) if test(point)]


def _ring_indexes(text: str, nacelle) -> tuple[list[int], str] | None:
    match = re.search(r"\brings?\s*([0-9 ,and]+)", text, re.IGNORECASE)
    if not match:
        return None
    numbers = [int(value) for value in re.findall(r"\d+", match.group(1))]
    numbers = [value for value in numbers if 1 <= value <= nacelle.rings]
    if not numbers:
        return None
    indexes: list[int] = []
    for ring in sorted(set(numbers)):
        begin = (ring - 1) * nacelle.per_ring
        indexes.extend(range(begin, begin + nacelle.per_ring))
    label = "ring " + " and ".join(str(value) for value in sorted(set(numbers)))
    return indexes, label


def parse_mission_intent(
    text: str,
    nacelle=DEFAULT_NACELLE,
    rng: random.Random | None = None,
) -> MissionIntent:
    """Resolve the operator's sentence into a seed and an authorised waypoint set."""
    rng = rng or random.Random()
    cleaned = (text or "").strip()
    seed, was_random = _seed_from(cleaned, rng)

    # Strip the seed clause so "seed 1027" cannot be read as a ring number.
    without_seed = re.sub(r"\b(?:seeds?|scenario)\s*(?:is|=|:)?\s*\d{1,7}\b", " ", cleaned, flags=re.IGNORECASE)
    lowered = without_seed.lower()

    ring = _ring_indexes(without_seed, nacelle)
    if ring:
        indexes, label = ring
    else:
        matched = [
            name for name, words in _REGIONS
            if any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in words)
        ]
        # "front to back" or "one corner to the other" names the whole sweep, not a
        # region, so anything naming two opposed regions authorises everything.
        opposed = {"top", "bottom"} <= set(matched) or {"front", "aft"} <= set(matched) \
            or {"left", "right"} <= set(matched)
        if len(matched) == 1 and not opposed:
            name = matched[0]
            indexes = _region_indexes(name, nacelle)
            label = f"the {name} side" if name in ("top", "bottom", "left", "right") \
                else f"the {name} of the nacelle"
        else:
            indexes = list(range(len(nacelle.waypoints())))
            label = "the whole nacelle"

    if not indexes:
        indexes = list(range(len(nacelle.waypoints())))
        label = "the whole nacelle"

    # Longer jobs get more turns, because each action is bounded in time.
    max_actions = 8 if len(indexes) <= 9 else 14

    return MissionIntent(
        text=cleaned,
        seed=seed,
        seed_was_random=was_random,
        authorised_indexes=sorted(indexes),
        region=label,
        max_actions=max_actions,
    )
