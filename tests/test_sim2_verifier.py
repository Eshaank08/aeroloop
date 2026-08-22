"""Bookkeeping tests for the simulator v2 verifier itself."""

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controller2 import Controller  # noqa: E402
from sim.scenarios import WindScenario, make_scenario  # noqa: E402
from sim2.params import DEFAULT_QUAD  # noqa: E402
from sim2.run_verifier import run_scenario  # noqa: E402


class _HoverController:
    """A controller that hovers, so a scenario runs the full tick budget."""

    def __init__(self, waypoints, nacelle, params):
        self.params = params

    def step(self, t, state):
        return (self.params.hover_thrust, 0.0, 0.0, 0.0)


def _calm_scenario(seed):
    """A wind free scenario, so a hovering drone stays safe for the whole run."""
    return WindScenario(
        seed=seed,
        base=(0.0, 0.0, 0.0),
        gust_dir=(1.0, 0.0, 0.0),
        gust_peak=0.0,
        gust_start_s=0.0,
        gust_duration_s=1.0,
    )


def test_full_budget_run_reports_elapsed_exactly_equal_to_budget():
    result = run_scenario(_HoverController, _calm_scenario(1027))

    assert result.elapsed_s == DEFAULT_QUAD.time_budget_s
    assert result.budget_s == DEFAULT_QUAD.time_budget_s
    # a run of exactly max_ticks ticks has not overrun its budget
    assert result.elapsed_s <= result.budget_s


def test_elapsed_time_is_exact_for_a_shorter_budget():
    ticks = 1234
    params = dataclasses.replace(
        DEFAULT_QUAD, time_budget_s=round(ticks * DEFAULT_QUAD.dt, 9)
    )
    assert params.max_ticks == ticks

    result = run_scenario(_HoverController, _calm_scenario(1000), params=params)

    assert result.elapsed_s == params.time_budget_s


def test_seed_1027_is_not_failed_by_elapsed_time_drift():
    result = run_scenario(Controller, make_scenario(1027))

    assert result.elapsed_s == DEFAULT_QUAD.time_budget_s
    assert result.failure_reason is None
    assert result.passed
