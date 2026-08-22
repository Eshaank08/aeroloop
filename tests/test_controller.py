"""pytest wrapper around the verifier.

This exists so that Devin's normal habit of running the test suite automatically
exercises the full simulation verifier, with no custom retry logic needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controller import Controller  # noqa: E402
from sim.run_verifier import verify  # noqa: E402


def test_controller_passes_verification():
    ok, results = verify(Controller, count=30, base_seed=1000, verbose=True)
    n_pass = sum(r.passed for r in results)
    collisions = sum(r.collisions for r in results)
    mean_cov = sum(r.coverage for r in results) / len(results)
    assert ok, (
        f"verification FAILED: {n_pass}/{len(results)} scenarios passed, "
        f"mean coverage {mean_cov * 100:.1f}%, total collisions {collisions}. "
        "Every scenario needs coverage >= 95%, zero collisions, and completion "
        "inside the time budget."
    )
