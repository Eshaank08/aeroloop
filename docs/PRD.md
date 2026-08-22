# PRD

Status of this document: it describes the repository as it stands on master, not the plan.
Everything marked BUILT was run in the checkout and its output is pasted in
`docs/RESULTS.md`. Everything marked SPECIFIED exists only as a written spec.

## System in one diagram

```
scripts/trigger_devin.py                                    [BUILT, path exercised once]
        |  POST /v3/organizations/{org}/sessions   (prompt = README task spec)
        |  credentials read from DEVIN_API_KEY and DEVIN_ORG_ID only
        v
   Devin session  ---writes--->  controller.py               [BUILT, merged in PR #4]
        |  ^                      commit author on that file is the Devin bot
        |  |  pytest -q  (wraps both verifiers)               [BUILT, prints 59 passed]
        |  +--- FAIL: coverage/collision/time report fed back automatically
        v
      PASS   30/30 default scenarios, 50/50 on unseen base seed 424242
        |
        +---> viz/replay.py --> viz/data/*.json --> viz/flight_view.html
        |     records and replays a graded run, scores nothing  [BUILT, offline, read only]
        v
scripts/approve.py   <- the single human touch, a safety gate, post-PASS   [BUILT]
        |
        v
   ARTIFACT: controller.py + verification report

sim2/run_verifier.py  rate controlled quadrotor, coverage gated on a camera view
   spec docs/SIM2_SPEC.md, controller2.py                    [BUILT, merged in PR #17]
   29/30 default scenarios, 20/20 on unseen base seed 424242, RESULT: PASS

scripts/run_devin_mission.py  live Devin session as the mission planner   [BUILT]
   fails closed without DEVIN_API_KEY and DEVIN_ORG_ID, no mission measured here
```

## Components

| File                       | Owner       | Purpose                                                       |
| -------------------------- | ----------- | ------------------------------------------------------------- |
| `sim/aircraft_geometry.py` | Claude Code | Nacelle collision surface, inspection waypoint ring layout     |
| `sim/drone_dynamics.py`    | Claude Code | Position/velocity integration, wind disturbance, accel clamp   |
| `sim/scenarios.py`         | Claude Code | Seeded randomized wind scenarios, reproducible per seed        |
| `sim/limits.py`            | Claude Code | max_accel, max_speed, time_budget_s, dt                        |
| `sim/run_verifier.py`      | Claude Code | Runs N scenarios, scores coverage/collisions/time, PASS/FAIL   |
| `sim2/`                    | Claude Code | Simulator v2: quadrotor dynamics, camera gate, its own verifier |
| `controller2.py`           | **Devin**   | The v2 flight controller for the camera gated quadrotor        |
| `inspection/`              | Claude Code | Evidence scoring, action policy, work order parsing, artifact, Devin planner |
| `scripts/run_devin_mission.py` | Claude Code | Runs a Devin planned re-capture mission, requires credentials |
| `tests/test_controller.py` | Claude Code | pytest wrapper so Devin's normal test loop triggers the verifier |
| `tests/test_controller2.py` | Claude Code | Same wrapper for the v2 batch, plus a determinism check       |
| `sim/report.py`            | Claude Code | Signed verification artifact, its schema, and the recorded approval |
| `tests/test_report.py`     | Claude Code | Tests for the artifact schema, its signature, and gate refusals |
| `controller.py`            | **Devin**   | The flight controller. The only file Devin writes.             |
| `scripts/trigger_devin.py` | Claude Code | Creates the Devin session via API, polls status                |
| `scripts/approve.py`       | Claude Code | Writes the verification artifact, prints its summary, requires one human confirmation |
| `viz/replay.py`            | Devin       | Reruns the graded scenarios and records them to `viz/data/`, scores nothing |
| `viz/flight_view.html`     | Devin       | Browser flight view of one recorded run, Three.js vendored, no server, no network |
| `viz/data/*.json`, `data.js` | generated | Committed recording of the graded batch and of the traced scenario, seed 1017 |
| `viz/replay2.py`, `viz/data2/*.json` | Devin | Recorder and committed recording for the v2 quadrotor run       |
| `viz/server.py`, `viz/mission.py`, `viz/flightlab.py` | Devin | Flight command console behind the view, chat and voice missions, served at `127.0.0.1:8765` |
| `reports/*.json`           | generated   | Verification artifacts written by the gate, gitignored           |
| `docs/REAL_WORLD_ROADMAP.md` | Claude Code | Backlog for moving from the simulator to a real hangar          |
| `docs/ADAPTIVE_EVIDENCE_BUILD.md` | Claude Code | Implementation brief for the adaptive evidence loop, now implemented in `inspection/` |
| `docs/DEMO.md`             | Claude Code | 90 second demo runbook, with an offline fallback per step       |
| `docs/RESULTS.md`          | Claude Code | Every claimed number, with the command that produced it         |
| `docs/DEVIN_AUTONOMY_ROADMAP.md` | Claude Code | Milestone where Devin is the required runtime mission agent |
| `docs/SIM2_SPEC.md`        | Claude Code | Simulator v2 spec, now implemented in `sim2/`                   |

`docs/SIM2_SPEC.md` is the contract for `sim2/` and is not restated here.

### Built or specified

| Part                                                               | State                                   |
| ------------------------------------------------------------------ | --------------------------------------- |
| Simulator v1: geometry, wind, limits, verifier                      | BUILT, a 30 scenario batch runs in under a second |
| `tests/`                                                           | BUILT, 59 tests, two of them wrapping the v1 and v2 verifiers |
| `controller.py`                                                    | BUILT by a Devin session, merged in PR #4 |
| `scripts/trigger_devin.py`                                         | BUILT, and the trigger to artifact path has been exercised end to end once, producing PR #4 |
| `scripts/approve.py` and `sim/report.py`                            | BUILT, reruns the verifier, writes a signed artifact under `reports/`, then blocks on one typed answer |
| `viz/` replay recorder and flight view                              | BUILT, read only, the view itself works with no network |
| `viz/` flight command console                                       | BUILT, needs the local `viz/server.py` process, so it is not part of the offline path |
| Real hardware roadmap in `docs/REAL_WORLD_ROADMAP.md`               | SPECIFIED, backlog only, nothing in it is implemented |
| Devin autonomy milestone in `docs/DEVIN_AUTONOMY_ROADMAP.md`         | SPECIFIED, deployment plan only |
| Adaptive evidence loop: `inspection/` evidence scoring, action policy, artifact | BUILT, unit tested, but no live Devin planned mission is measured |
| Simulator v2: rate controlled quadrotor with camera gated coverage  | BUILT in `sim2/`, 29/30 default scenarios and 20/20 on unseen base seed 424242, both `RESULT: PASS` |
| `controller2.py`                                                   | BUILT by a Devin session, merged in PR #17 |
| `scripts/run_devin_mission.py`                                     | BUILT, fails closed without credentials, no live mission measured |
| Real drone hardware, real flight, image processing                  | OUT OF SCOPE, see the last section       |

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

The section above is the v1 verifier in `sim/`. Simulator v2 in `sim2/` grades against
its own thresholds, printed by its report as `coverage >= 95%, no failure, elapsed <=
150s, pass rate >= 90%`, and a waypoint only counts when the camera is aimed at it, so v1
and v2 numbers are not comparable.

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

Steps 1 to 6 are done. Step 5, the highest uncertainty step, is the one that mattered: a
scripted session wrote the controller and opened PR #4, which is on master.


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

Coverage numbers now exist and live in `docs/RESULTS.md`, for v1 and for v2. The
iteration count of the live session is not recorded in this repository, so it is not
measured and must not be quoted.

## Out of scope

- Real drone hardware, real flight, camera or image processing
- Damage detection or classification, we verify flight coverage, not defect finding
- Full 6-DOF rigid-body dynamics, point-mass with accel control is sufficient and honest
- Any human involvement in writing, testing, or fixing the controller
