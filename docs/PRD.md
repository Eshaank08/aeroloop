# PRD

## System in one diagram

```
scripts/trigger_devin.py
        |  POST /v3/organizations/{org}/sessions   (prompt = README task spec)
        v
   Devin session  ---writes--->  controller.py
        |  ^
        |  |  pytest -q  (wraps sim/run_verifier.py)
        |  +--- FAIL: coverage/collision/time report fed back automatically
        v
      PASS
        |
        v
scripts/approve.py   <- the single human touch, a safety gate, post-PASS
        |
        v
   ARTIFACT: controller.py + verification report
```

## Components

| File                       | Owner       | Purpose                                                       |
| -------------------------- | ----------- | ------------------------------------------------------------- |
| `sim/aircraft_geometry.py` | Claude Code | Nacelle collision surface, inspection waypoint ring layout     |
| `sim/drone_dynamics.py`    | Claude Code | Position/velocity integration, wind disturbance, accel clamp   |
| `sim/scenarios.py`         | Claude Code | Seeded randomized wind scenarios, reproducible per seed        |
| `sim/limits.py`            | Claude Code | max_accel, max_speed, time_budget_s, dt                        |
| `sim/run_verifier.py`      | Claude Code | Runs N scenarios, scores coverage/collisions/time, PASS/FAIL   |
| `tests/test_controller.py` | Claude Code | pytest wrapper so Devin's normal test loop triggers the verifier |
| `controller.py`            | **Devin**   | The flight controller. The only file Devin writes.             |
| `scripts/trigger_devin.py` | Claude Code | Creates the Devin session via API, polls status                |
| `scripts/approve.py`       | Claude Code | Prints report, requires one human confirmation                 |

## Verifier spec

**Scenario.** One nacelle, a fixed set of inspection waypoints, one seeded wind profile.

**Per tick (dt = 0.02s, 50 Hz):**
1. Call `controller.step(t, position, velocity)` to get desired acceleration.
2. Clamp acceleration magnitude to `limits.max_accel`.
3. Add wind disturbance for this tick.
4. Integrate velocity, clamp to `limits.max_speed`, integrate position.
5. Collision check: is the drone inside `nacelle.radius + safety_margin`?
6. Coverage check: is the drone within `waypoint_tolerance` of an unvisited waypoint?

**Episode ends** on collision, on time budget exceeded, or on all waypoints visited.

**Metrics per scenario:** coverage percent, collision count, elapsed time.

**Scenario passes** if coverage >= 95% AND collisions == 0 AND elapsed <= budget.

**Run passes** if >= 90% of scenarios pass. Any collision anywhere is disqualifying for
that scenario, no partial credit.

## Default parameters

| Parameter          | Value        |
| ------------------ | ------------ |
| Nacelle radius     | 1.6 m        |
| Nacelle length     | 4.5 m        |
| Safety margin      | 0.5 m        |
| Inspection radius  | 3.0 m        |
| Waypoints          | 24 (3 rings x 8) |
| Waypoint tolerance | 0.4 m        |
| max_accel          | 6.0 m/s^2    |
| max_speed          | 4.0 m/s      |
| Time budget        | 120 s        |
| dt                 | 0.02 s       |
| Scenarios per run  | 30           |
| Wind base          | 0 to 3 m/s, random direction |
| Gust               | up to 5 m/s, random onset and duration |

Tune these only if the task turns out trivially easy or impossible for Devin. Record any
change in IDEA.md under "how the approach changed."

## Build order

1. `limits.py`, `aircraft_geometry.py`, `drone_dynamics.py`, `scenarios.py`
2. `run_verifier.py` with the PASS/FAIL report
3. `tests/test_controller.py`, then sanity-check with a deliberately broken controller
   to confirm the verifier actually fails it
4. `scripts/trigger_devin.py`, confirm a session can be created and polled
5. **First real live Devin run. Do this early, not last.** Highest-uncertainty step.
6. `scripts/approve.py`
7. Deck and demo rehearsal

**Do not start the deck until step 5 has passed once.** The deck needs real coverage
numbers and a real iteration count, not projections.

## Out of scope

- Real drone hardware, real flight, camera or image processing
- Damage detection or classification, we verify flight coverage, not defect finding
- Full 6-DOF rigid-body dynamics, point-mass with accel control is sufficient and honest
- Any human involvement in writing, testing, or fixing the controller
