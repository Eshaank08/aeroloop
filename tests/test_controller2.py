"""pytest wrappers around the simulator v2 verifier."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controller2 import Controller  # noqa: E402
from sim.aircraft_geometry import DEFAULT_NACELLE  # noqa: E402
from sim.scenarios import make_scenarios  # noqa: E402
from sim2.params import DEFAULT_QUAD  # noqa: E402
from sim2.quad_dynamics import QuadDrone  # noqa: E402
from sim2.run_verifier import verify  # noqa: E402


def test_controller2_passes_verification():
    ok, results = verify(Controller, count=30, base_seed=1000, verbose=True)
    n_pass = sum(result.passed for result in results)
    mean_cov = sum(result.coverage for result in results) / len(results)
    assert ok, (
        f"verification FAILED: {n_pass}/{len(results)} scenarios passed, "
        f"mean coverage {mean_cov * 100:.1f}%."
    )


def _trace(seed):
    scenario = make_scenarios(1, seed)[0]
    drone = QuadDrone(params=DEFAULT_QUAD)
    trace = []
    t = 0.0
    def command_at(time):
        return (
            DEFAULT_QUAD.hover_thrust * (1.0 + 0.08 * math.sin(0.37 * time)),
            0.7 * math.sin(0.41 * time),
            0.8 * math.cos(0.29 * time),
            0.6 * math.sin(0.53 * time + 0.2),
        )

    for _ in range(500):
        command = command_at(t)
        drone.step(command, scenario.at(t))
        state = drone.state
        trace.append((
            state.position,
            state.velocity,
            state.attitude,
            state.body_rates,
            state.thrust,
        ))
        t += DEFAULT_QUAD.dt
    return trace


def test_dynamics_trace_is_bit_for_bit_deterministic():
    assert _trace(1000) == _trace(1000)
