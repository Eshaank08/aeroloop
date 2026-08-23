# AGENTS.md

Guidance for coding agents working in this repository. Read this before you start.

AeroLoop is a verification harness for autonomous aircraft engine inspection. An AI
engineer writes the flight and mission software, an adversarial simulator grades it, and
a human signs off only after the verifier has already returned PASS.

## The one rule that defines this project

**Devin writes `controller.py`, `controller2.py`, and the mission planner. Nobody else
touches them.**

The entire claim of the project is that an AI engineer produced that software
unsupervised. One human edit and the submission is dishonest. If the agent cannot solve
the task, the correct response is to fix the task spec in `README.md` or tune the
verifier parameters, never to write the solution by hand.

## Verifier integrity

**Never modify `sim/`, `sim2/`, `inspection/`, `mission/` or `tests/` to make a failing
controller pass.** That is grading our own homework.

The verifier existed before the controller did, and it is adversarial by design. If a
change would make the task easier, ask whether it is a genuine spec fix or a quiet
lowering of the bar. Record every parameter change in `docs/IDEA.md` under "how the
approach changed", because the judges explicitly ask how the approach evolved.

The verifier must stay deterministic given a seed. Never introduce unseeded randomness.

## Setup commands

Python 3.11 (see `.python-version`). Dependencies are deliberately minimal: numpy and
pytest only, no physics engine, no external simulator, no drone hardware.

```bash
python -m pip install -r requirements.txt
npm ci --prefix frontend        # only if you are touching the dashboard
```

## Testing

Run the full suite before you claim anything works. It takes about a minute.

```bash
python -m pytest -q
```

That is also what CI runs. Targeted runs while iterating:

```bash
# simulator v1: point-mass drone, waypoint coverage
python -m sim.run_verifier --scenarios 30 --seed 1000 --verbose
python -m sim.run_verifier --job dense-sweep --scenarios 5 --seed 4242 --verbose

# simulator v2: rate-controlled quadrotor with a camera gate
python -m sim2.run_verifier

# the runtime mission loop, where the agent chooses every action
python scripts/run_autonomous_mission.py --seed 1000 --planner baseline
python scripts/run_autonomous_mission.py --seed 1000 --sector all --planner devin
```

Environment overrides for the v1 pytest wrapper: `AEROLOOP_JOB`, `AEROLOOP_SCENARIOS`,
`AEROLOOP_BASE_SEED`.

### CI gotcha

CI runs `git diff --exit-code -- viz/dashboard` after building the frontend. **If you
change anything under `frontend/`, you must commit the rebuilt `viz/dashboard` output
too**, or CI fails on an otherwise correct change:

```bash
npm run typecheck --prefix frontend && npm run lint --prefix frontend
npm run build --prefix frontend
git add viz/dashboard
```

## Project structure

| Path | What it is |
| --- | --- |
| `controller.py` | v1 flight controller. Agent-written only. |
| `controller2.py` | v2 controller, quadrotor with a camera gate. Agent-written only. |
| `sim/` | Simulator v1: point-mass dynamics, nacelle geometry, wind, verifier |
| `sim/jobs.py` | Inspection jobs: a plain-language request mapped to a graded spec |
| `sim2/` | Simulator v2: quadrotor dynamics, camera gate, its own verifier |
| `inspection/` | Evidence model: what counts as having inspected a surface |
| `mission/` | Runtime loop. `episode.py` is reset/observe/act/verify, `safety.py` is the envelope, `agent.py` holds the planners |
| `tests/` | The verifier wrapped as pytest, so the normal test loop grades the work |
| `scripts/` | Devin session triggers, mission runners, the human approval gate |
| `viz/` | Flight replay view and the built dashboard |
| `frontend/` | Dashboard source, Vite and React, builds into `viz/dashboard` |
| `docs/` | GOAL, IDEA, PRD, DECK, DEMO, RESULTS and the judge Q&A |

## Code style

- Plain functions and small dataclasses. No frameworks, no abstraction layers.
- numpy only for the simulator. Do not add dependencies without a reason that survives
  being questioned.
- **No em dashes anywhere**, in docs, code comments, or the deck.
- Keep the verifier's output legible on a projector. It gets read out loud.

## Evidence and claims

Any number that goes in `docs/` or the deck needs a source that survives being checked
live. We already removed one headline statistic that traced back to an SEO content farm.
If you cannot find a primary source, say so rather than quoting the figure.

## Secrets

`DEVIN_API_KEY` and `DEVIN_ORG_ID` are read from the environment only. **Never hardcode
or echo an API key.** If a key appears in a chat, a transcript, or a commit, treat it as
compromised and rotate it.
