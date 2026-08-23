"""Inspection jobs: a plain-language request mapped to a verifier configuration.

An inspection job is what a maintenance planner actually asks for: "give me a detailed
sweep of the left nacelle on the A320". This module turns that sentence into the
geometry, waypoint layout and flight limits the verifier will grade against.

The mapping is a deterministic keyword match, not a language model. That is on purpose.
The verifier has to produce the same verdict for the same request every time, so the
step that decides what "detailed" means cannot be allowed to drift between runs. The
job description is also handed to Devin verbatim, so the engineer reads the request in
the planner's own words while the grader reads it in fixed parameters.
"""

from dataclasses import dataclass

from .aircraft_geometry import Nacelle
from .limits import Limits


@dataclass(frozen=True)
class Job:
    name: str
    summary: str
    nacelle: Nacelle
    limits: Limits


JOBS = {
    # Widebody nacelle, 3.2 m outer diameter and 4.5 m long, which sits between a
    # LEAP-1A at 2.7 m and a Trent 7000 at 3.65 m per Safran Nacelles. Three rings of
    # eight is the routine general visual inspection pattern.
    "standard-sweep": Job(
        name="standard-sweep",
        summary=(
            "General visual inspection of a widebody engine nacelle. Three rings of "
            "eight viewpoints at 3.0 m standoff, 120 s budget."
        ),
        nacelle=Nacelle(),
        limits=Limits(),
    ),
    # Detailed visual inspection: same airframe, far denser viewpoint set. This is the
    # job that proves the controller is planning a sweep rather than replaying a path.
    "dense-sweep": Job(
        name="dense-sweep",
        summary=(
            "Detailed visual inspection of the same nacelle after a reported bird "
            "strike. Five rings of twelve viewpoints, 60 in total, 120 s budget."
        ),
        nacelle=Nacelle(rings=5, per_ring=12),
        limits=Limits(),
    ),
    # Narrowbody: a LEAP-1A class nacelle at 2.7 m outer diameter and 3.0 m long, with
    # a proportionally tighter standoff and a shorter budget.
    "narrowbody-sweep": Job(
        name="narrowbody-sweep",
        summary=(
            "General visual inspection of a narrowbody (A320 class) nacelle: 2.7 m "
            "outer diameter, 3.0 m long, 2.6 m standoff, 90 s budget."
        ),
        nacelle=Nacelle(
            axis_end=(3.0, 0.0, 0.0),
            radius=1.35,
            inspection_radius=2.6,
        ),
        limits=Limits(time_budget_s=90.0),
    ),
}

DEFAULT_JOB = "standard-sweep"

# Keyword to job mapping, checked in order. First hit wins.
_KEYWORDS = (
    (("dense", "detailed", "thorough", "bird strike", "lightning", "close"), "dense-sweep"),
    (("a320", "narrowbody", "narrow body", "single aisle", "leap"), "narrowbody-sweep"),
    (("widebody", "wide body", "general visual", "standard", "routine"), "standard-sweep"),
)


def parse_job(request: str) -> Job:
    """Map a plain-language inspection request to the job that will grade it."""
    text = request.lower()
    for words, name in _KEYWORDS:
        if any(word in text for word in words):
            return JOBS[name]
    return JOBS[DEFAULT_JOB]


def get_job(name: str) -> Job:
    if name not in JOBS:
        raise KeyError(f"unknown job {name!r}, expected one of {sorted(JOBS)}")
    return JOBS[name]
