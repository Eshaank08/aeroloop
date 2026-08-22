"""Turn a plain-language work order into bounded aircraft/limits/seed parameters."""

from __future__ import annotations

import re

from sim.aircraft_geometry import DEFAULT_NACELLE, Nacelle
from sim.limits import DEFAULT_LIMITS, Limits


class WorkOrder:
    """Bound work-order with explicit aircraft geometry, limits, seed and wind scale."""

    def __init__(
        self,
        label: str,
        nacelle=None,
        limits=None,
        seed: int = 606076,
        wind_scale: float = 1.0,
        selected_waypoints: list[tuple[float, float, float]] | None = None,
        selected_waypoint_indexes: list[int] | None = None,
        sector: str = "",
    ):
        self.label = label
        self.nacelle = nacelle or DEFAULT_NACELLE
        self.limits = limits or DEFAULT_LIMITS
        self.seed = seed
        self.wind_scale = wind_scale
        self.selected_waypoints = selected_waypoints
        self.selected_waypoint_indexes = selected_waypoint_indexes
        self.sector = sector

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "seed": self.seed,
            "wind_scale": self.wind_scale,
            "sector": self.sector,
            "selected_waypoints": [list(wp) for wp in self.selected_waypoints] if self.selected_waypoints else [],
            "selected_waypoint_indexes": list(self.selected_waypoint_indexes) if self.selected_waypoint_indexes else [],
            "nacelle": {
                "axis_start": list(self.nacelle.axis_start),
                "axis_end": list(self.nacelle.axis_end),
                "radius": self.nacelle.radius,
                "safety_margin": self.nacelle.safety_margin,
                "inspection_radius": self.nacelle.inspection_radius,
                "rings": self.nacelle.rings,
                "per_ring": self.nacelle.per_ring,
            },
            "limits": {
                "max_accel": self.limits.max_accel,
                "max_speed": self.limits.max_speed,
                "time_budget_s": self.limits.time_budget_s,
                "dt": self.limits.dt,
            },
        }


def _parse_seed(text: str) -> int | None:
    match = re.search(r"\bseed\s*(?:is|=)?\s*(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


_WIND_TERMS_RE = re.compile(
    r"\b(?:calm|no\s+wind|light\s+wind|light|low|moderate\s+wind|moderate|medium\s+wind|medium|heavy\s+wind|heavy|strong\s+wind|strong|high\s+wind|high)\b",
    re.IGNORECASE,
)


def _parse_wind(text: str) -> float:
    lower = text.lower()
    if re.search(r"\b(?:calm|no\s+wind)\b", lower):
        return 0.3
    if re.search(r"\b(?:light)\b", lower):
        return 0.5
    if re.search(r"\b(?:strong|heavy|high)\b", lower):
        return 2.0
    if re.search(r"\b(?:moderate|medium)\b", lower):
        return 1.0
    return 1.0


def _text_for_job(text: str) -> str:
    """Strip wind modifiers so they cannot be mistaken for job keywords."""
    return _WIND_TERMS_RE.sub(" ", text)


def _without_seed(text: str) -> str:
    """Strip seed clauses so numbers like 'seed 200' are not parsed as ring/side."""
    text = re.sub(r"\bwith\s+seed\s+\d+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bseed\s+\d+", " ", text, flags=re.IGNORECASE)
    return text


def _parse_selection(text: str, nacelle: Nacelle):
    """Return (selected waypoints, selected indexes, sector label) if text targets a side or ring."""
    cleansed = _without_seed(_text_for_job(text))
    lowered = cleansed.lower()
    waypoints = nacelle.waypoints()

    ring_match = re.search(r"\brings?\b(.*)$", cleansed, re.IGNORECASE)
    if ring_match:
        ring_numbers = [int(value) for value in re.findall(r"\b\d+\b", ring_match.group(1))]
        if ring_numbers:
            invalid = [value for value in ring_numbers if not 1 <= value <= nacelle.rings]
            if invalid:
                return None, None, ""
            selected = []
            selected_indexes = []
            per_ring = nacelle.per_ring
            for ring in ring_numbers:
                begin = (ring - 1) * per_ring
                selected.extend(waypoints[begin : begin + per_ring])
                selected_indexes.extend(range(begin, begin + per_ring))
            label = "Ring " + ", ".join(str(value) for value in ring_numbers)
            return selected, selected_indexes, label

    side_match = re.search(r"\b(top|bottom|left|right|front|aft)(?:\s+side)?\b", lowered)
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
        if indexed:
            selected = [wp for i, wp in indexed]
            selected_indexes = [i for i, wp in indexed]
            return selected, selected_indexes, side.title() + " side"

    return None, None, ""


def _parse_job(text: str) -> tuple[Nacelle, Limits]:
    lower = _text_for_job(text).lower()
    if "narrowbody" in lower or "a320" in lower or re.search(r"\b2\.7\s*m\b", lower):
        nacelle = Nacelle(
            axis_start=(0.0, 0.0, 0.0),
            axis_end=(3.0, 0.0, 0.0),
            radius=2.7 / 2,
            safety_margin=0.5,
            inspection_radius=4.0,
            rings=3,
            per_ring=8,
            waypoint_tolerance=0.4,
        )
        limits = Limits(max_accel=6.0, max_speed=4.0, time_budget_s=90.0, dt=0.02)
        return nacelle, limits
    if "dense" in lower or re.search(r"\b60\s*wp\b|\b60\b", lower):
        nacelle = Nacelle(
            axis_start=(0.0, 0.0, 0.0),
            axis_end=(4.5, 0.0, 0.0),
            radius=1.6,
            safety_margin=0.5,
            inspection_radius=3.0,
            rings=5,
            per_ring=12,
            waypoint_tolerance=0.35,
        )
        limits = Limits(max_accel=6.0, max_speed=4.0, time_budget_s=120.0, dt=0.02)
        return nacelle, limits
    return DEFAULT_NACELLE, DEFAULT_LIMITS


def parse_work_order(text: str) -> WorkOrder:
    """Convert free text into a deterministic WorkOrder."""
    wind_scale = _parse_wind(text)
    nacelle, limits = _parse_job(text)
    seed = _parse_seed(text) or 606076
    selected, selected_indexes, sector = _parse_selection(text, nacelle)
    return WorkOrder(
        label=text,
        nacelle=nacelle,
        limits=limits,
        seed=seed,
        wind_scale=wind_scale,
        selected_waypoints=selected,
        selected_waypoint_indexes=selected_indexes,
        sector=sector,
    )
