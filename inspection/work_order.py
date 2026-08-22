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
    ):
        self.label = label
        self.nacelle = nacelle or DEFAULT_NACELLE
        self.limits = limits or DEFAULT_LIMITS
        self.seed = seed
        self.wind_scale = wind_scale

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "seed": self.seed,
            "wind_scale": self.wind_scale,
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


def _parse_wind(text: str) -> float:
    lower = text.lower()
    if any(term in lower for term in ("calm", "light", "low")):
        return 0.3
    if any(term in lower for term in ("strong", "heavy", "high")):
        return 2.0
    if any(term in lower for term in ("moderate", "medium")):
        return 1.0
    return 1.0


def _parse_job(text: str) -> tuple[Nacelle, Limits]:
    lower = text.lower()
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
    if "dense" in lower or re.search(r"\b60\s*wp\b|\b60\b", lower) or "high" in lower:
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
    nacelle, limits = _parse_job(text)
    seed = _parse_seed(text) or 606076
    wind_scale = _parse_wind(text)
    return WorkOrder(label=text, nacelle=nacelle, limits=limits, seed=seed, wind_scale=wind_scale)
