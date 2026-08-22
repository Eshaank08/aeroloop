"""pytest wrapper around the verifier.

This exists so that Devin's normal habit of running the test suite automatically
exercises the full simulation verifier, with no custom retry logic needed.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controller import Controller  # noqa: E402
from sim.run_verifier import verify  # noqa: E402


def _env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def test_controller_passes_verification():
    scenarios = _env_int("AEROLOOP_SCENARIOS", 30)
    base_seed = _env_int("AEROLOOP_BASE_SEED", 1000)
    ok, results = verify(
        Controller,
        count=scenarios,
        base_seed=base_seed,
        verbose=True,
    )
    n_pass = sum(r.passed for r in results)
    collisions = sum(r.collisions for r in results)
    mean_cov = sum(r.coverage for r in results) / len(results)
    assert ok, (
        f"verification FAILED: {n_pass}/{len(results)} scenarios passed, "
        f"mean coverage {mean_cov * 100:.1f}%, total collisions {collisions}, "
        f"scenarios={scenarios}, base_seed={base_seed}. "
        "Every scenario needs coverage >= 95%, zero collisions, and completion "
        "inside the time budget."
    )
