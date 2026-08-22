"""Record inspection flights as JSON traces for the flight view.

Read only with respect to the graded path: this reruns the same Drone, Nacelle,
Controller and wind scenarios the verifier uses, and never imports or alters the
verifier's scoring. Nothing here can change a PASS or a FAIL.

Usage:
    python -m viz.replay                      # seed 1000 batch, trace of the first seed
    python -m viz.replay --seed 7000 --scenarios 30
    python -m viz.replay --trace-seed 1017    # trace one specific scenario
"""

import argparse
import json
import math
from pathlib import Path

from controller import Controller
from sim.aircraft_geometry import DEFAULT_NACELLE
from sim.drone_dynamics import Drone
from sim.limits import DEFAULT_LIMITS
from sim.run_verifier import COVERAGE_THRESHOLD, SCENARIO_PASS_RATE, make_scenarios

OUT_DIR = Path(__file__).resolve().parent / "data"


def record(scenario, nacelle=DEFAULT_NACELLE, limits=DEFAULT_LIMITS, stride=2):
    """Fly one scenario and return the trace plus the same metrics the verifier scores."""
    waypoints = nacelle.waypoints()
    controller = Controller(waypoints, nacelle, limits)
    drone = Drone(limits=limits)
    visited = [False] * len(waypoints)
    frames = []
    collision_at = None
    t = 0.0

    for tick in range(limits.max_ticks):
        accel = controller.step(t, drone.position, drone.velocity)
        drone.step(accel, scenario.at(t))
        t += limits.dt

        if nacelle.is_collision(drone.position):
            collision_at = t

        for i, wp in enumerate(waypoints):
            if not visited[i] and math.dist(drone.position, wp) <= nacelle.waypoint_tolerance:
                visited[i] = True

        if tick % stride == 0 or collision_at is not None or all(visited):
            wind = scenario.at(t)
            frames.append({
                "t": round(t, 3),
                "p": [round(c, 4) for c in drone.position],
                "v": [round(c, 4) for c in drone.velocity],
                "wind": [round(c, 4) for c in wind],
                "clearance": round(
                    nacelle.distance_to_surface(drone.position) - nacelle.keep_out_radius, 4
                ),
                "visited": sum(visited),
            })

        if collision_at is not None or all(visited):
            break

    coverage = sum(visited) / len(waypoints)
    return {
        "seed": scenario.seed,
        "coverage": coverage,
        "collisions": 1 if collision_at is not None else 0,
        "elapsed_s": round(t, 3),
        "passed": coverage >= COVERAGE_THRESHOLD and collision_at is None
        and t <= limits.time_budget_s,
        "collision_at": collision_at,
        "gust": {
            "start_s": round(scenario.gust_start_s, 3),
            "duration_s": round(scenario.gust_duration_s, 3),
            "peak": round(scenario.gust_peak, 3),
        },
        "base_wind": [round(c, 4) for c in scenario.base],
        "frames": frames,
    }


def scene(nacelle=DEFAULT_NACELLE, limits=DEFAULT_LIMITS):
    """Static geometry and limits the view needs to draw the world."""
    return {
        "nacelle": {
            "axis_start": list(nacelle.axis_start),
            "axis_end": list(nacelle.axis_end),
            "radius": nacelle.radius,
            "safety_margin": nacelle.safety_margin,
            "keep_out_radius": nacelle.keep_out_radius,
            "inspection_radius": nacelle.inspection_radius,
            "waypoint_tolerance": nacelle.waypoint_tolerance,
        },
        "waypoints": [list(wp) for wp in nacelle.waypoints()],
        "limits": {
            "max_accel": limits.max_accel,
            "max_speed": limits.max_speed,
            "time_budget_s": limits.time_budget_s,
            "dt": limits.dt,
        },
        "thresholds": {
            "coverage": COVERAGE_THRESHOLD,
            "scenario_pass_rate": SCENARIO_PASS_RATE,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1000, help="base seed of the batch")
    ap.add_argument("--scenarios", type=int, default=30)
    ap.add_argument("--trace-seed", type=int, default=None,
                    help="seed to record frame by frame, defaults to the batch base seed")
    ap.add_argument("--stride", type=int, default=2, help="record every Nth tick")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    scenarios = make_scenarios(args.scenarios, args.seed)
    trace_seed = args.trace_seed if args.trace_seed is not None else args.seed

    runs = []
    trace = None
    for sc in scenarios:
        result = record(sc, stride=args.stride)
        if sc.seed == trace_seed:
            trace = result
        runs.append({k: v for k, v in result.items() if k != "frames"})

    if trace is None:
        trace = record(make_scenarios(1, trace_seed)[0], stride=args.stride)

    n_pass = sum(r["passed"] for r in runs)
    batch = {
        "base_seed": args.seed,
        "scenarios": len(runs),
        "passed": n_pass,
        "pass_rate": n_pass / len(runs),
        "mean_coverage": sum(r["coverage"] for r in runs) / len(runs),
        "total_collisions": sum(r["collisions"] for r in runs),
        "result": "PASS" if n_pass / len(runs) >= SCENARIO_PASS_RATE else "FAIL",
        "runs": runs,
    }

    scene_data = scene()
    (out / "scene.json").write_text(json.dumps(scene_data))
    (out / "batch.json").write_text(json.dumps(batch))
    (out / "trace.json").write_text(json.dumps(trace))
    # also as a script, so flight_view.html opens straight off the filesystem
    # without a local web server (file:// blocks fetch)
    (out / "data.js").write_text(
        "window.AEROLOOP = "
        + json.dumps({"scene": scene_data, "batch": batch, "trace": trace})
        + ";\n"
    )

    print(f"batch  {batch['result']}  {n_pass}/{len(runs)} passed  "
          f"mean coverage {batch['mean_coverage'] * 100:.1f}%  "
          f"collisions {batch['total_collisions']}")
    print(f"trace  seed {trace['seed']}  {len(trace['frames'])} frames  "
          f"{trace['elapsed_s']:.2f}s  coverage {trace['coverage'] * 100:.1f}%")
    print(f"written to {out}")


if __name__ == "__main__":
    main()
