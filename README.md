# AeroLoop

Autonomous flight software for drone-based aircraft engine inspection, written,
verified and now flown by an AI engineer, with a human involved only in the physical
safety sign off at the end.

Built for the Cognition "Find an Industry, Give it an Engineer" track, EHL Munich,
August 2026.

Everything here is simulated. No real drone has flown, and nothing in this repository
detects defects. What is graded is inspection coverage: did the vehicle get complete,
usable photographic evidence of every waypoint without hitting the engine and inside
its time budget.

## The two loops

**1. The engineering loop (Devin writes the software).** `scripts/trigger_devin.py`
creates a Devin session over the API with the task brief below as its whole prompt.
That session writes `controller.py` for simulator v1 (point mass, acceleration
control) and `controller2.py` for simulator v2 (rate controlled quadrotor whose
coverage only counts through a camera gate). It runs the hidden adversarial verifier,
reads the failure report, fixes the controller and reruns until it passes. No human
edits either controller. A human signs `scripts/approve.py` afterwards, and only to
accept the physical risk of flying near a real engine.

**2. The runtime loop (Devin flies the mission).** In simulator v2 the Devin API is
the mission agent itself. `mission/episode.py` turns the one shot flight into
reset, observe, act, verify. Devin receives an observation containing only what a
drone could sense right now: pose, clearance, a wind estimate recovered from the
vehicle's own motion, per waypoint evidence gaps, remaining action and time budget,
and the hard limits it must respect. It returns exactly one bounded action at a time
as structured output. `mission/safety.py` rejects stale observation ids, replayed
action ids, waypoints outside the authorised sector, over long actions, excess speed
and exhausted per waypoint attempts, and reports the rejection back to Devin rather
than substituting a choice of its own. Devin's claim of completion never overrides
the verifier. If Devin becomes unreachable, the mission performs a bounded return
toward home and can never report PASS.

The strongest evidence for the challenge is in the second loop: during this build
`controller2.py` crashed with `ZeroDivisionError` whenever the mission agent handed
it fewer than three waypoints, and a separate Devin session diagnosed it, fixed it
(PR #21, merged), proved the routes were identical over 2000 random cases on the full
nacelle, and lifted the mission loop from 27/30 to 29/30. No human edited that file.
Full narrative and numbers in [docs/RESULTS.md](docs/RESULTS.md).

## Run it in five minutes

```bash
python -m pip install -r requirements.txt
python -m pytest -q                                   # 101 passed, about 20 s
```

Verifier for simulator v1, the point mass sweep:

```bash
python -m sim.run_verifier --scenarios 30 --seed 1000
```

Verifier for simulator v2, the quadrotor with the camera gate:

```bash
python -m sim2.run_verifier --scenarios 30 --seed 1000
```

One autonomous mission, Devin choosing every action over the live API:

```bash
export DEVIN_API_KEY=cog_...
export DEVIN_ORG_ID=org_...
python scripts/run_autonomous_mission.py --seed 1000 --sector all --planner devin
```

The same mission with the deterministic local baseline agent, no credentials and no
API credits. This is the comparison number, not the challenge demo:

```bash
python scripts/run_autonomous_mission.py --seed 1000 --planner baseline
```

Watch a mission in the browser, on the scanned turbofan and quadcopter models:

```bash
python -m viz.server
# then open http://127.0.0.1:8765/mission_view.html
```

The page auto loads the last recorded mission from `viz/data3/` so it is never empty,
and the **Fly mission** button runs a fresh one with the seed, sector and planner
picked in the controls.

The human safety gate, run after a PASS:

```bash
python scripts/approve.py
```

It reruns verification, writes a signed artifact under `reports/` pinning the
controller hash and the git commit, then blocks on one typed answer. Anything other
than `yes` holds the controller. If verification failed it refuses to even ask.
`python scripts/approve.py --dry-run` writes the artifact and skips the prompt.

### Credentials

`DEVIN_API_KEY` and `DEVIN_ORG_ID` are read from the environment only. They are never
entered in the browser and never committed. Every Devin path fails closed without
them: `scripts/run_autonomous_mission.py --planner devin` exits with an argument
error, `scripts/trigger_devin.py` exits immediately, and the browser backend returns
an error rather than quietly running the baseline. The Devin API path has had a
handful of live runs, not a soak test. Treat it as demonstrated, not battle tested.

### Measured results, in one line each

| What | Result | Command |
| ---- | ------ | ------- |
| Test suite | 101 passed | `python -m pytest -q` |
| Sim v1 batch | 30/30 PASS, 100.0% mean coverage, 0 collisions | `python -m sim.run_verifier --scenarios 30 --seed 1000` |
| Sim v2 batch | 29/30 PASS, 99.9% mean coverage, 719/720 waypoints | `python -m sim2.run_verifier --scenarios 30 --seed 1000` |
| Mission loop, baseline agent, seeds 1000 to 1029 | 29/30 PASS, 98.6% mean coverage | `python scripts/run_autonomous_mission.py --seed <n> --planner baseline` |
| Live Devin mission, seed 1000 | PASS, 24/24 waypoints, 100.0% coverage, 82.3 s | `python scripts/run_autonomous_mission.py --seed 1000 --planner devin` |

Seed 1027 fails, in the v2 batch and in the mission loop alike. It is the same
scenario both times, and it misses the 150 s time budget rather than colliding. It is
written down here rather than rounded away. Full tables, exact commands and the live
mission narrative are in [docs/RESULTS.md](docs/RESULTS.md). The live demo runbook,
with a fallback for every step that touches the network, is in
[docs/DEMO.md](docs/DEMO.md).

---

## THE TASK (this section is Devin's brief)

`scripts/trigger_devin.py` sends this whole file to a Devin session as the task
prompt. Everything above this line is orientation for a human reader. The contract
below is the part that must stay exact, because softening it would invalidate every
number in `docs/RESULTS.md`.

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

## Repo layout

```
controller.py             <- v1 controller, written by Devin, never by a human
controller2.py            <- v2 controller, quadrotor with a camera gate, same rule
sim/aircraft_geometry.py  Nacelle collision surface + inspection waypoints
sim/drone_dynamics.py     Drone physics: position, velocity, wind disturbance
sim/scenarios.py          Seeded randomized wind-gust scenario generator
sim/limits.py             Flight limits (accel, speed, time budget, tick rate)
sim/run_verifier.py       Runs the controller across N scenarios, prints PASS/FAIL
sim/report.py             Signed verification artifact and the approval recorded on it
sim2/                     Simulator v2: quadrotor dynamics, camera gate, its verifier
mission/contract.py       Observation and action packets exchanged with the agent
mission/episode.py        Reset, observe, act, verify around one v2 flight
mission/safety.py         The safety envelope that may reject an action, never replace it
mission/agent.py          The mission loop, the Devin planner and the baseline agent
inspection/               Evidence scoring, action policy, artifact, Devin API client
tests/                    pytest wrappers for both verifiers plus the unit suites
scripts/trigger_devin.py  Creates a Devin session against this repo via the API
scripts/run_autonomous_mission.py  One runtime mission, Devin or baseline agent
scripts/approve.py        Final human approval gate, run after a PASS
viz/                      Replay recorders, browser flight and mission views, backend
docs/                     GOAL, IDEA, PRD, DEMO, RESULTS, SIM2_SPEC, the roadmaps
```

Further reading: [Real-world multimodal inspection roadmap](docs/REAL_WORLD_ROADMAP.md)
for the path beyond simulation, [Devin autonomy deployment roadmap](docs/DEVIN_AUTONOMY_ROADMAP.md)
for how the runtime loop is meant to deploy, [Adaptive evidence loop](docs/ADAPTIVE_EVIDENCE_BUILD.md)
for the evidence scoring build, and [Simulator v2 spec](docs/SIM2_SPEC.md) for the
quadrotor and camera contract.

## Human in the loop

There is exactly one human touch in this pipeline, and it happens after the verifier
already returned PASS: `scripts/approve.py` prints the full report and asks a person to
confirm before the result would ever be treated as cleared to fly near a real aircraft.

That gate is a physical-safety decision, not an engineering one. Nothing about writing,
testing, fixing or flying the software involves a human at any point.
