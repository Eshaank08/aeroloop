"""The verifier. Runs a controller across randomized wind scenarios and scores it.

Never modify this to make a failing controller pass.
"""

import argparse
import math
import sys

from .aircraft_geometry import DEFAULT_NACELLE, Nacelle
from .drone_dynamics import Drone
from .jobs import DEFAULT_JOB, JOBS, get_job
from .limits import DEFAULT_LIMITS, Limits
from .scenarios import make_scenarios

COVERAGE_THRESHOLD = 0.95      # >= 95% of waypoints visited
SCENARIO_PASS_RATE = 0.90      # >= 90% of scenarios must pass


class ScenarioResult:
    def __init__(self, seed, coverage, collisions, elapsed_s, budget_s):
        self.seed = seed
        self.coverage = coverage
        self.collisions = collisions
        self.elapsed_s = elapsed_s
        self.budget_s = budget_s

    @property
    def passed(self) -> bool:
        return (
            self.coverage >= COVERAGE_THRESHOLD
            and self.collisions == 0
            and self.elapsed_s <= self.budget_s
        )

    def line(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"  seed {self.seed:<6} {status}  "
            f"coverage {self.coverage * 100:5.1f}%  "
            f"collisions {self.collisions}  "
            f"time {self.elapsed_s:6.2f}s / {self.budget_s:.0f}s"
        )


def run_scenario(controller_cls, scenario, nacelle: Nacelle, limits: Limits) -> ScenarioResult:
    waypoints = nacelle.waypoints()
    controller = controller_cls(waypoints, nacelle, limits)
    drone = Drone(limits=limits)
    visited = [False] * len(waypoints)
    collisions = 0
    t = 0.0

    for _ in range(limits.max_ticks):
        try:
            accel = controller.step(t, drone.position, drone.velocity)
        except Exception as exc:  # a crashing controller is a failing controller
            print(f"    controller raised {type(exc).__name__}: {exc}", file=sys.stderr)
            return ScenarioResult(scenario.seed, 0.0, 1, t, limits.time_budget_s)

        if accel is None or len(accel) != 3 or any(math.isnan(c) or math.isinf(c) for c in accel):
            print("    controller returned an invalid acceleration", file=sys.stderr)
            return ScenarioResult(scenario.seed, 0.0, 1, t, limits.time_budget_s)

        drone.step(accel, scenario.at(t))
        t += limits.dt

        if nacelle.is_collision(drone.position):
            collisions += 1
            break

        for i, wp in enumerate(waypoints):
            if not visited[i] and math.dist(drone.position, wp) <= nacelle.waypoint_tolerance:
                visited[i] = True

        if all(visited):
            break

    coverage = sum(visited) / len(waypoints)
    return ScenarioResult(scenario.seed, coverage, collisions, t, limits.time_budget_s)


def verify(controller_cls, count=30, base_seed=1000, nacelle=DEFAULT_NACELLE,
           limits=DEFAULT_LIMITS, verbose=True):
    results = [
        run_scenario(controller_cls, sc, nacelle, limits)
        for sc in make_scenarios(count, base_seed)
    ]
    n_pass = sum(r.passed for r in results)
    rate = n_pass / len(results)
    overall = rate >= SCENARIO_PASS_RATE

    if verbose:
        print("\nAeroLoop verification report")
        print("=" * 64)
        for r in results:
            print(r.line())
        print("=" * 64)
        print(f"  scenarios passed : {n_pass}/{len(results)}  ({rate * 100:.1f}%)")
        print(f"  mean coverage    : {sum(r.coverage for r in results) / len(results) * 100:.1f}%")
        print(f"  total collisions : {sum(r.collisions for r in results)}")
        print(f"  thresholds       : coverage >= {COVERAGE_THRESHOLD * 100:.0f}%, "
              f"collisions == 0, pass rate >= {SCENARIO_PASS_RATE * 100:.0f}%")
        print(f"\n  RESULT: {'PASS' if overall else 'FAIL'}\n")

    return overall, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", type=int, default=30)
    ap.add_argument("--seed", type=int, default=1000, help="base seed for the batch")
    ap.add_argument("--job", default=DEFAULT_JOB, choices=sorted(JOBS),
                    help="which inspection job to grade against")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    from controller import Controller  # noqa: E402

    job = get_job(args.job)
    print(f"job: {job.name}\n  {job.summary}")
    ok, _ = verify(Controller, count=args.scenarios, base_seed=args.seed,
                   nacelle=job.nacelle, limits=job.limits, verbose=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
