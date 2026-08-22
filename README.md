# AeroLoop

Autonomous flight-control software for drone-based aircraft engine inspection,
written and verified by an AI engineer with no human in the loop.

Built for the Cognition "Find an Industry, Give it an Engineer" track, EHL Munich,
August 2026.

---

## THE TASK (this section is Devin's brief)

Write `controller.py`. That is the only file you need to create or modify.

A small inspection drone must fly a complete visual-inspection sweep of a jet engine
nacelle. It must visit every designated inspection waypoint around the engine, never
collide with the aircraft structure, and finish inside its battery/time budget, while
being pushed around by randomized wind gusts.

Everything else in this repo already exists: the simulator, the geometry, the wind
model, and the verifier. Do not modify them. Your job is the flight controller only.

### The interface you must implement

```python
# controller.py
class Controller:
    def __init__(self, waypoints, nacelle, limits):
        """
        waypoints : list[tuple[float, float, float]]
            Inspection points that must each be visited, in any order you choose.
        nacelle : sim.aircraft_geometry.Nacelle
            The engine geometry. Read `.axis_start`, `.axis_end`, `.radius`,
            `.safety_margin` to know what you must not hit.
        limits : sim.limits.Limits
            `.max_accel`, `.max_speed`, `.time_budget_s`, `.dt`
        """

    def step(self, t, position, velocity):
        """
        Called once per simulation tick (50 Hz by default).

        t        : float, seconds since flight start
        position : (x, y, z) current position in metres
        velocity : (vx, vy, vz) current velocity in m/s

        Returns  : (ax, ay, az) desired acceleration in m/s^2.
                   Magnitude is clamped to limits.max_accel by the simulator.
        """
```

### What counts as success

The verifier runs your controller across many randomized wind scenarios and requires
all three of these, on at least 90% of scenarios:

| Metric   | Pass threshold                                            |
| -------- | --------------------------------------------------------- |
| Coverage | >= 95% of inspection waypoints visited                     |
| Safety   | zero collisions with the nacelle, in every single scenario |
| Time     | sweep completed within the time budget                     |

The 95% coverage bar is our own engineering threshold, set deliberately below the full
coverage that the inspection-planning literature targets. The verifier is here to grade
robustness under wind, not geometric completeness, and the five points of slack are
exactly where the wind is allowed to hurt you. Collisions get no such slack.

### How to check your own work

```bash
pytest -q
```

That runs the full verifier. It prints a per-scenario report plus a final PASS/FAIL.
The default batch uses 30 scenarios and base seed 1000, on the `standard-sweep` job.
To verify against a different job or a judge-supplied seed, override with environment
variables:

```bash
AEROLOOP_JOB=dense-sweep AEROLOOP_SCENARIOS=5 AEROLOOP_BASE_SEED=4242 pytest -q
```

You can also run it directly for more detail:

```bash
python -m sim.run_verifier --scenarios 30 --verbose
```

The equivalent judge-seed command is:

```bash
python -m sim.run_verifier --job dense-sweep --scenarios 5 --seed 4242 --verbose
```

### Inspection jobs

A job is one inspection request: a nacelle geometry, a viewpoint layout, and a time
budget. `sim/jobs.py` defines them, and the same `Controller` class must handle
whichever one it is given. The geometry arrives through `__init__`, so do not hardcode
anything you can read off `nacelle` and `limits`.

| Job                | Geometry                            | Waypoints | Budget |
| ------------------ | ----------------------------------- | --------- | ------ |
| `standard-sweep`   | widebody, 3.2 m diameter, 4.5 m     | 24        | 120 s  |
| `dense-sweep`      | same airframe, dense viewpoint set  | 60        | 120 s  |
| `narrowbody-sweep` | A320 class, 2.7 m diameter, 3.0 m   | 24        | 90 s   |

Iterate until `pytest` passes. Collisions are the hardest constraint: a controller that
covers every waypoint but clips the nacelle once is a FAIL, not a near-miss.

---

## Repo layout

```
controller.py             <- THE ONLY FILE DEVIN WRITES (starts as a failing stub)
sim/jobs.py               Inspection jobs: a plain-language request -> a graded spec
sim/aircraft_geometry.py  Nacelle collision surface + inspection waypoints
sim/drone_dynamics.py     Drone physics: position, velocity, wind disturbance
sim/scenarios.py          Seeded randomized wind-gust scenario generator
sim/limits.py             Flight limits (accel, speed, time budget, tick rate)
sim/run_verifier.py       Runs the controller across N scenarios, prints PASS/FAIL
tests/test_controller.py  pytest wrapper so the normal test loop runs the verifier
scripts/trigger_devin.py  Creates a Devin session against this repo via the API
scripts/approve.py        Final human approval gate, run after a PASS
docs/                     GOAL, IDEA, PRD, DEMO
```

## Human in the loop

There is exactly one human touch in this pipeline, and it happens after the verifier
already returned PASS: `scripts/approve.py` prints the full report and asks a person to
confirm before the result would ever be treated as cleared to fly near a real aircraft.

That gate is a physical-safety decision, not an engineering one. Nothing about writing,
testing, or fixing the flight software involves a human at any point.
