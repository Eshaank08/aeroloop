"""The simulator v2 verifier for rate controlled quadrotor inspection."""

import argparse
import math
import sys
from dataclasses import dataclass

from sim.aircraft_geometry import DEFAULT_NACELLE, Nacelle
from sim.scenarios import make_scenarios

from .camera import camera_gate
from .params import DEFAULT_QUAD, QuadParams
from .quad_dynamics import QuadDrone, command_is_finite


COVERAGE_THRESHOLD = 0.95
SCENARIO_PASS_RATE = 0.90


@dataclass
class ScenarioResult:
    seed: int
    coverage: float
    inspected_count: int
    failure_reason: object
    elapsed_s: float
    near_tolerance_never_aimed: int
    waypoint_count: int
    budget_s: float

    @property
    def passed(self) -> bool:
        return (
            self.coverage >= COVERAGE_THRESHOLD
            and self.failure_reason is None
            and self.elapsed_s <= self.budget_s
        )

    @property
    def inspected(self) -> int:
        return self.inspected_count

    def line(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"  seed {self.seed:<6} {status}  "
            f"coverage {self.coverage * 100:5.1f}%  "
            f"inspected {self.inspected_count:2}/{self.waypoint_count}  "
            f"failure {self.failure_reason}  "
            f"elapsed {self.elapsed_s:6.2f}s  "
            f"near-tolerance-never-aimed {self.near_tolerance_never_aimed}"
        )


def _result(
    scenario,
    inspected,
    failure_reason,
    elapsed_s,
    near_seen,
    budget_s,
):
    inspected_count = sum(inspected)
    never_aimed = sum(near_seen[i] and not inspected[i] for i in range(len(inspected)))
    return ScenarioResult(
        seed=scenario.seed,
        coverage=inspected_count / len(inspected),
        inspected_count=inspected_count,
        failure_reason=failure_reason,
        elapsed_s=elapsed_s,
        near_tolerance_never_aimed=never_aimed,
        waypoint_count=len(inspected),
        budget_s=budget_s,
    )


def run_scenario(controller_cls, scenario, nacelle: Nacelle = DEFAULT_NACELLE,
                 params: QuadParams = DEFAULT_QUAD) -> ScenarioResult:
    waypoints = nacelle.waypoints()
    controller = controller_cls(waypoints, nacelle, params)
    drone = QuadDrone(params=params)
    inspected = [False] * len(waypoints)
    near_seen = [False] * len(waypoints)
    t = 0.0
    ticks_exhausted = True

    for _ in range(params.max_ticks):
        try:
            command = controller.step(t, drone.state)
        except Exception as exc:
            print(f"    controller raised {type(exc).__name__}: {exc}", file=sys.stderr)
            return _result(
                scenario, inspected, "controller_exception", t, near_seen,
                params.time_budget_s,
            )

        if not command_is_finite(command):
            print("    controller returned an invalid command", file=sys.stderr)
            return _result(
                scenario, inspected, "invalid_command", t, near_seen,
                params.time_budget_s,
            )

        drone.step(command, scenario.at(t))
        t += params.dt

        if nacelle.is_collision(drone.state.position):
            return _result(
                scenario, inspected, "collision", t, near_seen,
                params.time_budget_s,
            )
        if math.sqrt(sum(value * value for value in drone.state.velocity)) > params.max_speed:
            return _result(
                scenario, inspected, "unsafe_speed", t, near_seen,
                params.time_budget_s,
            )

        for index, waypoint in enumerate(waypoints):
            if not inspected[index]:
                gate = camera_gate(waypoint, drone.state, nacelle)
                near_seen[index] = near_seen[index] or gate.within_tolerance
                if gate.inspected:
                    inspected[index] = True
        if all(inspected):
            ticks_exhausted = False
            break

    failure_reason = None
    coverage = sum(inspected) / len(inspected)
    if ticks_exhausted and coverage < COVERAGE_THRESHOLD:
        failure_reason = "timeout"
    return _result(
        scenario, inspected, failure_reason, t, near_seen, params.time_budget_s,
    )


def verify(controller_cls, count=30, base_seed=1000, nacelle=DEFAULT_NACELLE,
           params=DEFAULT_QUAD, verbose=True):
    results = [
        run_scenario(controller_cls, scenario, nacelle, params)
        for scenario in make_scenarios(count, base_seed)
    ]
    n_pass = sum(result.passed for result in results)
    rate = n_pass / len(results)
    overall = rate >= SCENARIO_PASS_RATE

    if verbose:
        print("\nAeroLoop simulator v2 verification report")
        print("=" * 112)
        for result in results:
            print(result.line())
        print("=" * 112)
        print(f"  scenarios passed : {n_pass}/{len(results)}  ({rate * 100:.1f}%)")
        print(
            f"  mean coverage    : "
            f"{sum(result.coverage for result in results) / len(results) * 100:.1f}%"
        )
        print(
            f"  inspected total  : "
            f"{sum(result.inspected_count for result in results)}/"
            f"{sum(result.waypoint_count for result in results)}"
        )
        print(
            f"  thresholds       : coverage >= {COVERAGE_THRESHOLD * 100:.0f}%, "
            f"no failure, elapsed <= {params.time_budget_s:.0f}s, "
            f"pass rate >= {SCENARIO_PASS_RATE * 100:.0f}%"
        )
        print(f"\nRESULT: {'PASS' if overall else 'FAIL'}")

    # v1 returns a tuple, so keep the same (ok, results) shape.
    return overall, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", type=int, default=30)
    ap.add_argument("--seed", type=int, default=1000, help="base seed for the batch")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    from controller2 import Controller

    ok, _ = verify(
        Controller,
        count=args.scenarios,
        base_seed=args.seed,
        verbose=True,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
