# AeroLoop

Autonomous flight-control software for drone-based aircraft engine inspection,
written and verified by an AI engineer with no human in the loop.

Built for the Cognition "Find an Industry, Give it an Engineer" track, EHL Munich,
August 2026.

## What this repository is

A closed loop. `scripts/trigger_devin.py` creates a Devin session over the API with the
task spec below as its whole prompt. That session writes `controller.py`, runs the
verifier in `sim/`, reads the failure report, fixes the controller, and reruns until it
passes, then opens a pull request. A human sees the result only at the end, at
`scripts/approve.py`, and only to accept the physical risk of flying near a real engine.

What is on master right now, verified in this checkout and not taken on trust:

- `controller.py` was written by a Devin session and merged through pull request #4. The
  commit author on that file is the Devin bot account, not a person.
- `python3 -m pytest -q` prints `1 passed`. That one test runs the whole verifier.
- `python3 -m sim.run_verifier --scenarios 30 --verbose` reports 30/30 scenarios passed,
  100.0% mean coverage, 0 collisions.
- A 50 scenario batch on unseen base seed 424242 reports 50/50 passed, 100.0% mean
  coverage, 0 collisions.
- `viz/flight_view.html` replays a graded run in the browser with no server and no
  network.

Every one of those numbers, with the exact command that produced it and the output pasted
verbatim, is in [docs/RESULTS.md](docs/RESULTS.md). The live demo runbook, including the
fallback for each step when the network is dead, is in [docs/DEMO.md](docs/DEMO.md).

For the implementation path beyond simulation, including multimodal perception,
real-drone integration, safety boundaries, regulatory implications and the complete
engineering backlog, see [Real-world multimodal inspection roadmap](docs/REAL_WORLD_ROADMAP.md).

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

The 95% coverage bar mirrors the real industry benchmark for autonomous aircraft
inspection (99.1% autonomous vs 78% manual walk-around), so it is a credible target,
not an invented one.

### How to check your own work

```bash
pytest -q
```

That runs the full verifier. It prints a per-scenario report plus a final PASS/FAIL.
The default batch uses 30 scenarios and base seed 1000. To verify against a
judge-supplied seed, override both values with environment variables:

```bash
AEROLOOP_SCENARIOS=5 AEROLOOP_BASE_SEED=4242 pytest -q
```

You can also run it directly for more detail:

```bash
python -m sim.run_verifier --scenarios 30 --verbose
```

The equivalent judge-seed command is:

```bash
python -m sim.run_verifier --scenarios 5 --seed 4242 --verbose
```

Iterate until `pytest` passes. Collisions are the hardest constraint: a controller that
covers every waypoint but clips the nacelle once is a FAIL, not a near-miss.

---

## The task list

One task, one file. The agent writes that file and nothing else, and the verifier decides
whether it is done.

| Version | Task                                                              | File the agent writes | Status                                    |
| ------- | ----------------------------------------------------------------- | --------------------- | ----------------------------------------- |
| v1      | Fly a full inspection sweep of a nacelle under randomized wind, point mass with acceleration control | `controller.py`       | done, written by Devin, merged in PR #4    |
| v2      | Fly the same sweep on a rate controlled quadrotor whose coverage only counts when a camera is aimed at the waypoint | the v2 controller file named in `docs/SIM2_SPEC.md` | specified, not built, no v2 run measured  |

The v2 simulator and its spec are the work of a parallel effort and are not on this
branch, so the exact v2 filename and interface are whatever `docs/SIM2_SPEC.md` says and
are deliberately not restated here. Nothing in this repository has been graded under v2,
so treat every number here as a v1 number.

The section above this one is the brief handed to the agent for v1. Keep it exact. The
thresholds in it are the contract, and softening them would invalidate every number in
`docs/RESULTS.md`.

## Repo layout

```
controller.py             <- THE ONLY FILE DEVIN WRITES (starts as a failing stub)
sim/aircraft_geometry.py  Nacelle collision surface + inspection waypoints
sim/drone_dynamics.py     Drone physics: position, velocity, wind disturbance
sim/scenarios.py          Seeded randomized wind-gust scenario generator
sim/limits.py             Flight limits (accel, speed, time budget, tick rate)
sim/run_verifier.py       Runs the controller across N scenarios, prints PASS/FAIL
tests/test_controller.py  pytest wrapper so the normal test loop runs the verifier
scripts/trigger_devin.py  Creates a Devin session against this repo via the API
scripts/approve.py        Final human approval gate, run after a PASS
viz/                      Read-only replay recorder and browser flight view of a graded run
docs/                     GOAL, IDEA, PRD, DEMO, RESULTS
```

## Human in the loop

There is exactly one human touch in this pipeline, and it happens after the verifier
already returned PASS: `scripts/approve.py` prints the full report and asks a person to
confirm before the result would ever be treated as cleared to fly near a real aircraft.

That gate is a physical-safety decision, not an engineering one. Nothing about writing,
testing, or fixing the flight software involves a human at any point.
