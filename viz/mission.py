"""Parse natural-language inspection commands into deterministic missions."""

from dataclasses import dataclass
import re

from sim.aircraft_geometry import DEFAULT_NACELLE


DEFAULT_WIND_SEED = 606076
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_NUMBER_RE = re.compile(_NUMBER)


class CommandError(ValueError):
    """Raised when a command does not match the supported grammar."""


@dataclass
class Mission:
    kind: str
    waypoints: list[tuple[float, float, float]]
    start: tuple[float, float, float] = (0.0, 0.0, 6.0)
    wind_seed: int = DEFAULT_WIND_SEED
    wind_scale: float = 1.0
    label: str = ""
    text: str = ""
    hold_duration: float = 8.0
    waypoint_indexes: list[int] | None = None


EXAMPLES = [
    "full sweep",
    "inspect ring 2 with seed 1234",
    "inspect the top side, light wind",
    "fly from 6 2 8 to 1 0 4",
    "hold at x=2 y=3 z=6, calm",
]


def help_text() -> str:
    return (
        "Commands: full sweep, inspect the engine, or inspect everything.\n"
        "Inspect ring 1, ring 1 and 3, or the top/bottom/left/right/front/aft side.\n"
        "Fly to x y z, go to x=... y=... z=..., or fly from x y z to x y z.\n"
        "Hover or hold at x y z. Add seed N, calm, no wind, light wind, or heavy wind."
    )


def _without_modifiers(text: str) -> str:
    text = re.sub(r"\bwith\s+seed\s+" + _NUMBER, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bseed\s+" + _NUMBER, " ", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(?:calm|no\s+wind|light\s+wind|heavy\s+wind|strong\s+wind|double\s+wind)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _wind_options(text: str) -> tuple[int, float]:
    seed = DEFAULT_WIND_SEED
    seed_match = re.search(r"\b(?:with\s+)?seed\s+(-?\d+)\b", text, re.IGNORECASE)
    if seed_match:
        seed = int(seed_match.group(1))

    lowered = text.lower()
    if re.search(r"\b(?:calm|no\s+wind)\b", lowered):
        scale = 0.0
    elif re.search(r"\blight\s+wind\b", lowered):
        scale = 0.5
    elif re.search(r"\b(?:heavy|strong|double)\s+wind\b", lowered):
        scale = 2.0
    else:
        scale = 1.0
    return seed, scale


def _coordinate(segment: str) -> tuple[float, float, float]:
    named = re.search(
        r"\bx\s*=\s*(" + _NUMBER + r").*?"
        r"\by\s*=\s*(" + _NUMBER + r").*?"
        r"\bz\s*=\s*(" + _NUMBER + r")",
        segment,
        re.IGNORECASE,
    )
    if named:
        return tuple(float(named.group(i)) for i in range(1, 4))

    values = _NUMBER_RE.findall(segment)
    if len(values) < 3:
        raise CommandError("I need three coordinates, such as x=2 y=3 z=5.")
    return tuple(float(value) for value in values[:3])


def _format_number(value: float) -> str:
    return f"{value:g}"


def _parse_goto(text: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    command = _without_modifiers(text)
    from_match = re.search(r"\bfrom\b(.*?)(?:\bto\b|$)", command, re.IGNORECASE)
    if from_match:
        start = _coordinate(from_match.group(1))
        to_match = re.search(r"\bto\b(.*)$", command, re.IGNORECASE)
        if not to_match:
            raise CommandError("A from command needs a destination after 'to'.")
        return start, _coordinate(to_match.group(1))

    to_match = re.search(r"\bto\b(.*)$", command, re.IGNORECASE)
    if not to_match:
        raise CommandError("A goto command needs a destination after 'to'.")
    return (0.0, 0.0, 6.0), _coordinate(to_match.group(1))


def parse(text: str, nacelle=DEFAULT_NACELLE) -> Mission:
    if not isinstance(text, str) or not text.strip():
        raise CommandError("Please enter a flight command. " + help_text().splitlines()[0])

    raw = text
    lowered = text.lower()
    seed, wind_scale = _wind_options(text)
    waypoints = nacelle.waypoints()
    start = (0.0, 0.0, 6.0)

    if re.search(r"\b(?:hover|hold)\b", lowered):
        if re.search(r"\bhold\s+at\b", lowered):
            hold_match = re.search(r"\bhold\s+at\b(.*)$", _without_modifiers(text), re.IGNORECASE)
            point = _coordinate(hold_match.group(1)) if hold_match else start
        else:
            point = start
        return Mission("hover", [point], start, seed, wind_scale, "Hover", raw)

    if re.search(r"\b(?:fly|go)\s+to\b|\bfly\s+from\b", lowered):
        start, point = _parse_goto(text)
        label = "Go to (" + ", ".join(_format_number(value) for value in point) + ")"
        return Mission("goto", [point], start, seed, wind_scale, label, raw)

    ring_match = re.search(r"\brings?\b(.*)$", _without_modifiers(text), re.IGNORECASE)
    if ring_match:
        ring_numbers = [int(value) for value in re.findall(r"\b\d+\b", ring_match.group(1))]
        if not ring_numbers:
            raise CommandError("Please name at least one ring from 1 to " + str(nacelle.rings) + ".")
        invalid = [value for value in ring_numbers if not 1 <= value <= nacelle.rings]
        if invalid:
            raise CommandError(
                f"Ring {invalid[0]} is out of range. Choose rings 1 through {nacelle.rings}."
            )
        selected = []
        selected_indexes = []
        for ring in ring_numbers:
            begin = (ring - 1) * nacelle.per_ring
            selected.extend(waypoints[begin : begin + nacelle.per_ring])
            selected_indexes.extend(range(begin, begin + nacelle.per_ring))
        ring_label = "Ring" if len(ring_numbers) == 1 else "Rings"
        label = ring_label + " " + ", ".join(str(value) for value in ring_numbers)
        return Mission("ring", selected, start, seed, wind_scale, label, raw, waypoint_indexes=selected_indexes)

    side_match = re.search(
        r"\b(top|bottom|left|right|front|aft)(?:\s+side)?\b", lowered
    )
    if side_match and re.search(r"\binspect\b", lowered):
        side = side_match.group(1)
        axis_z = (nacelle.axis_start[2] + nacelle.axis_end[2]) / 2.0
        axis_x = (nacelle.axis_start[0] + nacelle.axis_end[0]) / 2.0
        epsilon = 1e-9
        indexed = []
        if side == "top":
            indexed = [(i, wp) for i, wp in enumerate(waypoints) if wp[2] > axis_z + epsilon]
        elif side == "bottom":
            indexed = [(i, wp) for i, wp in enumerate(waypoints) if wp[2] < axis_z - epsilon]
        elif side == "left":
            indexed = [(i, wp) for i, wp in enumerate(waypoints) if wp[1] > epsilon]
        elif side == "right":
            indexed = [(i, wp) for i, wp in enumerate(waypoints) if wp[1] < -epsilon]
        elif side == "front":
            indexed = [(i, wp) for i, wp in enumerate(waypoints) if wp[0] < axis_x - epsilon]
        else:
            indexed = [(i, wp) for i, wp in enumerate(waypoints) if wp[0] > axis_x + epsilon]
        if not indexed:
            raise CommandError(f"The {side} side has no waypoints.")
        selected = [wp for i, wp in indexed]
        selected_indexes = [i for i, wp in indexed]
        return Mission("sector", selected, start, seed, wind_scale, side.title() + " side", raw, waypoint_indexes=selected_indexes)

    if re.search(
        r"\bfull\s+sweep\b|\binspect\s+(?:the\s+)?engine\b|"
        r"\brun\s+the\s+inspection\b|\binspect\s+everything\b",
        lowered,
    ):
        return Mission("sweep", waypoints, start, seed, wind_scale, "Full sweep", raw)

    raise CommandError(
        "I could not parse that command. Try 'full sweep', 'inspect ring 2', "
        "'fly to 2 3 5', or 'hover'."
    )
