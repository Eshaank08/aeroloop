"""Record simulator v2 inspection flights for the browser flight view.

The recorder reruns the simulator and controller directly. It does not call
the verifier or change any graded simulator code.
"""

import argparse
import json
import math
from pathlib import Path

from controller2 import Controller
from sim.aircraft_geometry import DEFAULT_NACELLE
from sim.scenarios import make_scenarios
from sim2.camera import camera_fov_half_angle, camera_gate, closest_point_on_surface
from sim2.params import DEFAULT_QUAD
from sim2.quad_dynamics import QuadDrone, command_is_finite
from sim2.run_verifier import COVERAGE_THRESHOLD, SCENARIO_PASS_RATE


OUT_DIR = Path(__file__).resolve().parent / "data2"


def _round_vector(value):
    return [round(component, 4) for component in value]


def _round_matrix(value):
    return [[round(component, 4) for component in row] for row in value]


def _aim_degrees(state, nacelle):
    surface_point = closest_point_on_surface(nacelle, state.position)
    target = tuple(surface_point[i] - state.position[i] for i in range(3))
    target_norm = math.sqrt(sum(component * component for component in target))
    camera_dir = state.camera_dir
    camera_norm = math.sqrt(sum(component * component for component in camera_dir))
    if target_norm == 0.0 or camera_norm == 0.0:
        return 180.0
    cosine = sum(camera_dir[i] * target[i] for i in range(3))
    cosine /= camera_norm * target_norm
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def _frame(t, state, wind, nacelle, visited):
    return {
        "t": round(t, 3),
        "p": _round_vector(state.position),
        "v": _round_vector(state.velocity),
        "wind": _round_vector(wind),
        "clearance": round(
            nacelle.distance_to_surface(state.position) - nacelle.keep_out_radius,
            4,
        ),
        "visited": sum(visited),
        "R": _round_matrix(state.attitude),
        "rates": _round_vector(state.body_rates),
        "thrust": round(state.thrust, 4),
        "aim": round(_aim_degrees(state, nacelle), 4),
    }


def record(scenario, nacelle=DEFAULT_NACELLE, params=DEFAULT_QUAD, stride=2):
    """Fly one scenario and return its replay trace and summary metrics."""
    waypoints = nacelle.waypoints()
    controller = Controller(waypoints, nacelle, params)
    drone = QuadDrone(params=params)
    visited = [False] * len(waypoints)
    frames = []
    failure_reason = None
    failure_at = None
    t = 0.0

    for tick in range(params.max_ticks):
        try:
            command = controller.step(t, drone.state)
        except Exception:
            failure_reason = "controller_exception"
            failure_at = t
            break

        if not command_is_finite(command):
            failure_reason = "invalid_command"
            failure_at = t
            break

        state = drone.step(command, scenario.at(t))
        t += params.dt

        if nacelle.is_collision(state.position):
            failure_reason = "collision"
        elif math.sqrt(sum(value * value for value in state.velocity)) > params.max_speed:
            failure_reason = "unsafe_speed"

        if failure_reason is None:
            for index, waypoint in enumerate(waypoints):
                if not visited[index] and camera_gate(waypoint, state, nacelle).inspected:
                    visited[index] = True

        wind = scenario.at(t)
        if (
            tick % stride == 0
            or failure_reason is not None
            or all(visited)
            or tick == params.max_ticks - 1
        ):
            frames.append(_frame(t, state, wind, nacelle, visited))

        if failure_reason is not None or all(visited):
            failure_at = t if failure_reason is not None else None
            break

    coverage = sum(visited) / len(waypoints)
    if failure_reason is None and coverage < COVERAGE_THRESHOLD and not all(visited):
        failure_reason = "timeout"
    elapsed_s = round(t, 3)
    passed = (
        coverage >= COVERAGE_THRESHOLD
        and failure_reason is None
        and t <= params.time_budget_s
    )
    return {
        "seed": scenario.seed,
        "coverage": coverage,
        "collisions": 1 if failure_reason == "collision" else 0,
        "elapsed_s": elapsed_s,
        "passed": passed,
        "collision_at": failure_at if failure_reason == "collision" else None,
        "failure_reason": failure_reason,
        "gust": {
            "start_s": round(scenario.gust_start_s, 3),
            "duration_s": round(scenario.gust_duration_s, 3),
            "peak": round(scenario.gust_peak, 3),
        },
        "base_wind": _round_vector(scenario.base),
        "frames": frames,
    }


def scene(nacelle=DEFAULT_NACELLE, params=DEFAULT_QUAD):
    """Return static geometry and limits needed by the flight view."""
    return {
        "trace_version": "v2",
        "version": 2,
        "nacelle": {
            "axis_start": list(nacelle.axis_start),
            "axis_end": list(nacelle.axis_end),
            "radius": nacelle.radius,
            "safety_margin": nacelle.safety_margin,
            "keep_out_radius": nacelle.keep_out_radius,
            "inspection_radius": nacelle.inspection_radius,
            "waypoint_tolerance": nacelle.waypoint_tolerance,
        },
        "waypoints": [list(waypoint) for waypoint in nacelle.waypoints()],
        "limits": {
            "max_speed": params.max_speed,
            "time_budget_s": params.time_budget_s,
            "dt": params.dt,
            "max_body_rate": params.max_body_rate,
            "max_thrust": params.max_thrust,
        },
        "camera": {
            "fov_half_deg": round(math.degrees(camera_fov_half_angle), 4),
        },
        "thresholds": {
            "coverage": COVERAGE_THRESHOLD,
            "scenario_pass_rate": SCENARIO_PASS_RATE,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1000, help="base seed of the batch")
    parser.add_argument("--scenarios", type=int, default=30)
    parser.add_argument(
        "--trace-seed",
        type=int,
        default=None,
        help="seed to record frame by frame, defaults to the batch base seed",
    )
    parser.add_argument("--stride", type=int, default=2, help="record every Nth tick")
    parser.add_argument("--out", default=str(OUT_DIR))
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    scenarios = make_scenarios(args.scenarios, args.seed)
    trace_seed = args.trace_seed if args.trace_seed is not None else args.seed

    runs = []
    trace = None
    for scenario in scenarios:
        result = record(scenario, stride=args.stride)
        if scenario.seed == trace_seed:
            trace = result
        runs.append({key: value for key, value in result.items() if key != "frames"})

    if trace is None:
        trace = record(make_scenarios(1, trace_seed)[0], stride=args.stride)

    n_pass = sum(run["passed"] for run in runs)
    batch = {
        "base_seed": args.seed,
        "scenarios": len(runs),
        "passed": n_pass,
        "pass_rate": n_pass / len(runs),
        "mean_coverage": sum(run["coverage"] for run in runs) / len(runs),
        "total_collisions": sum(run["collisions"] for run in runs),
        "result": "PASS" if n_pass / len(runs) >= SCENARIO_PASS_RATE else "FAIL",
        "runs": runs,
    }

    scene_data = scene()
    (out / "scene.json").write_text(json.dumps(scene_data))
    (out / "batch.json").write_text(json.dumps(batch))
    (out / "trace.json").write_text(json.dumps(trace))
    (out / "data.js").write_text(
        "window.AEROLOOP = "
        + json.dumps({"scene": scene_data, "batch": batch, "trace": trace})
        + ";\n"
    )

    print(
        f"batch  {batch['result']}  {n_pass}/{len(runs)} passed  "
        f"mean coverage {batch['mean_coverage'] * 100:.1f}%  "
        f"collisions {batch['total_collisions']}"
    )
    print(
        f"trace  seed {trace['seed']}  {len(trace['frames'])} frames  "
        f"{trace['elapsed_s']:.2f}s  coverage {trace['coverage'] * 100:.1f}%"
    )
    print(f"written to {out}")


if __name__ == "__main__":
    main()
