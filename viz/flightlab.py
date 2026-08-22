"""Run parsed missions through the real AeroLoop simulator and controller."""

import math

from controller import Controller
from sim.aircraft_geometry import DEFAULT_NACELLE
from sim.drone_dynamics import Drone
from sim.limits import DEFAULT_LIMITS
from sim.run_verifier import COVERAGE_THRESHOLD
from sim.scenarios import WindScenario, make_scenario


def fly(mission, nacelle=DEFAULT_NACELLE, limits=DEFAULT_LIMITS, stride=2, start_time=0.0) -> dict:
    waypoints = list(mission.waypoints)
    controller = Controller(waypoints, nacelle, limits)
    base_scenario = make_scenario(mission.wind_seed)
    scenario = WindScenario(
        seed=base_scenario.seed,
        base=tuple(value * mission.wind_scale for value in base_scenario.base),
        gust_dir=base_scenario.gust_dir,
        gust_peak=base_scenario.gust_peak * mission.wind_scale,
        gust_start_s=base_scenario.gust_start_s,
        gust_duration_s=base_scenario.gust_duration_s,
    )
    drone = Drone(position=mission.start, limits=limits)
    visited = [False] * len(waypoints)
    frames = []
    collision_at = None
    t = float(start_time)
    frame_t = 0.0
    hold_ticks = max(1, math.ceil(mission.hold_duration / limits.dt))

    for tick in range(limits.max_ticks):
        accel = controller.step(t, drone.position, drone.velocity)
        drone.step(accel, scenario.at(t))
        t += limits.dt
        frame_t += limits.dt

        if nacelle.is_collision(drone.position):
            collision_at = round(frame_t, 3)

        for i, waypoint in enumerate(waypoints):
            if not visited[i] and math.dist(drone.position, waypoint) <= nacelle.waypoint_tolerance:
                visited[i] = True

        hold_complete = mission.kind == "hover" and tick + 1 >= hold_ticks
        mission_complete = hold_complete if mission.kind == "hover" else all(visited)
        if tick % stride == 0 or collision_at is not None or mission_complete:
            wind = scenario.at(t)
            frames.append(
                {
                    "t": round(frame_t, 3),
                    "p": [round(value, 4) for value in drone.position],
                    "v": [round(value, 4) for value in drone.velocity],
                    "wind": [round(value, 4) for value in wind],
                    "clearance": round(
                        nacelle.distance_to_surface(drone.position)
                        - nacelle.keep_out_radius,
                        4,
                    ),
                    "visited": sum(visited),
                }
            )

        if collision_at is not None or mission_complete:
            break

    coverage = sum(visited) / len(waypoints) if waypoints else 1.0
    result = {
        "seed": scenario.seed,
        "start_time": round(start_time, 3),
        "coverage": coverage,
        "collisions": 1 if collision_at is not None else 0,
        "elapsed_s": round(frame_t, 3),
        "passed": coverage >= COVERAGE_THRESHOLD
        and collision_at is None
        and frame_t <= limits.time_budget_s,
        "collision_at": collision_at,
        "gust": {
            "start_s": round(scenario.gust_start_s, 3),
            "duration_s": round(scenario.gust_duration_s, 3),
            "peak": round(scenario.gust_peak, 3),
        },
        "base_wind": [round(value, 4) for value in scenario.base],
        "frames": frames,
        "waypoints": list(waypoints),
        "label": mission.label,
        "kind": mission.kind,
        "wind_scale": mission.wind_scale,
    }
    return result
