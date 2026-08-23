# AeroLoop codebase guide

This is the shortest path through the repository for a judge, teammate, or new
developer. It describes the current autonomous simulator (`mission/`), not the older
one-shot and adaptive prototypes that remain for comparison.

## Start here

| Goal | Open or run |
| --- | --- |
| Judge the working product | `https://aeroloop-production.up.railway.app/mission_view.html` |
| Understand the idea first | `https://aeroloop-production.up.railway.app/` |
| Audit the backend protocol | `https://aeroloop-production.up.railway.app/backend_view.html` |
| Run locally | `python -m viz.server`, then open `/mission_view.html` |
| Run without API credits | choose **Local test pilot** in the mission menu |
| Run the live challenge path | choose **Devin (live API)** |
| Read recorded results | `docs/RESULTS.md` |
| Prepare judge answers | `docs/JUDGE_QA.md` |

The simulator should be the primary submission link. The website explains the story;
the simulator proves the loop; the backend view exposes the protocol.

## The system in one sentence

A plain-language work order becomes an authorised inspection region; Devin receives
current observations and chooses bounded mission actions; local safety may reject those
actions; a deterministic controller executes accepted actions in physics; an independent
verifier—not Devin—issues the disposition; and a hashed artifact records the run.

## Request-to-artifact path

1. **Browser:** `viz/mission_view.html` collects a mission sentence and planner choice.
2. **HTTP boundary:** `viz/server.py` accepts `POST /api/mission/start`, applies origin,
   size, concurrency, rate, token, and ACU controls, and creates an asynchronous job.
3. **Human authority:** `mission/intent.py` deterministically resolves the sentence into
   a seed and authorised waypoint set. Devin cannot expand this boundary.
4. **Planner:** `inspection/devin.py::DevinMissionSession` creates one resumable Devin
   session per mission. `mission/agent.py::DevinMissionPlanner` sends each observation
   and requires structured output matching `mission/contract.py::ACTION_SCHEMA`.
5. **Safety:** `mission/safety.py::MissionSafetyEnvelope` accepts or rejects every action.
   It enforces observation freshness, unique action IDs, authorised targets, attempt
   budgets, duration, speed, standoff, and time limits.
6. **Execution:** `mission/episode.py::MissionEpisode` converts an accepted mission
   primitive into viewpoints. `controller2.py` runs the fast control loop against
   `sim2/quad_dynamics.py`; Devin never writes raw motor commands.
7. **Environment:** `sim/scenarios.py` supplies seeded wind. `mission/environment.py`
   supplies seeded ground, moving-object, synthetic visual, and synthetic audio inputs.
   The agent receives only current detections, never the future schedule.
8. **Evidence:** `sim2/camera.py` checks distance, aim, speed, and steadiness for each
   authorised waypoint. Missing evidence returns to the next observation.
9. **Verdict:** `mission/episode.py::verify` independently checks coverage, time and
   safety failures. An agent claim cannot create a `PASS`.
10. **Artifact and replay:** `mission/agent.py::MissionRun.to_dict` hashes the mission
    record. `viz/server.py` returns the trace and artifact; `viz/mission_view.html`
    renders decisions, blocked actions, flight, evidence, and disposition.

## Folder map

```text
mission/                 Current autonomous runtime
  intent.py              Operator sentence -> authorised region + seed
  contract.py            Observation/action schema and hashes
  agent.py               Devin/baseline planners and the closed loop
  safety.py              Deterministic action envelope
  episode.py             Stepwise physics, sensing, evidence and verifier
  environment.py         Seeded objects, ground, synthetic vision/audio

inspection/
  devin.py               Devin v3 client and resumable mission session
  adaptive.py            Earlier evidence re-capture vertical slice
  artifact.py            Earlier inspection artifact format

sim2/                    Current quadrotor physics and camera verifier
controller2.py           Current flight controller
sim/ + controller.py     Original one-shot controller/verifier baseline

viz/
  server.py              Secure web/API server and asynchronous jobs
  mission_view.html      Primary standalone simulator
  backend_view.html      Protocol/audit explanation
  dashboard/             Built project website served at `/`

frontend/                Source for the explanatory project website
scripts/                 CLI entry points, Devin trigger and approval tools
tests/                   151 automated tests across control, policy and web paths
docs/                    Results, roadmaps, demo instructions and judge Q&A
```

## Which implementation is current?

- **Primary demo:** `mission/` + `sim2/` + `controller2.py` + `viz/mission_view.html`.
- **Deterministic comparison:** `ScriptedPilot` uses the same action contract and safety
  envelope without API credits. It is a test pilot, not the challenge claim.
- **Earlier adaptive slice:** `inspection/adaptive.py` performs initial capture plus
  targeted re-capture. It remains useful history but is not the main judge flow.
- **Original one-shot verifier:** `sim/` + `controller.py` proves the controller across
  batches but does not expose the stepwise Devin decision loop.

## Where Devin is used

1. **Engineering loop:** Devin wrote and later repaired controller code using automated
   verifiers. `docs/RESULTS.md` records the controller bug, fix, and unseen-seed results.
2. **Runtime loop:** one resumable Devin API session chooses each bounded mission action
   from the latest observation. Session metadata and every action/rejection are recorded.

Devin is the mission decision maker, not the motor controller and not the verifier.
This separation is the safety argument and the central technical design choice.

## Human boundary

The operator authorises the asset/region and starts the mission. No person chooses
waypoints between trigger and artifact. A qualified person remains responsible for
emergency authority, reviewing evidence, maintenance disposition, and return to service.

## Verification commands

```bash
python -m pytest -q
AEROLOOP_SCENARIOS=30 AEROLOOP_BASE_SEED=606061 python -m pytest -q
python scripts/run_autonomous_mission.py --seed 1000 --planner baseline
python -m sim2.run_verifier --scenarios 30 --seed 5000
```

For a live CLI mission, configure `DEVIN_API_KEY`, `DEVIN_ORG_ID`, and an ACU ceiling,
then run `python scripts/run_autonomous_mission.py --seed 1000 --planner devin`.

## Honest boundary

The Devin API integration, contracts, safety decisions, flight controller, verifier,
artifacts, backend, deployment, and tests are real software. Physics, wind, vision,
audio, moving objects, and evidence are simulated and explicitly marked synthetic. No
physical aircraft, camera, microphone, or maintenance approval is claimed.

## Recorded intent versus code inference

Entire is enabled, but the core mission commits inspected for this guide do not contain
Entire checkpoint trailers. The flow above is therefore verified from current source,
tests, commit history, and recorded result documents—not from checkpoint transcripts.
