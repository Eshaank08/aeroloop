# AeroLoop — Five-Slide Judge Deck

This is the source copy for a deliberately simple five-slide pitch. Keep the
visible slides sparse; use the presenter notes to explain the technical detail.

## Slide 1 — AeroLoop

### Visible copy

**Give physical work a feedback loop.**

Devin for autonomous inspection.

Work order → decisions → verified artifact

### Presenter note

Software improves through a tight loop: attempt, test, fix. Physical inspection
usually breaks that loop because a person must coordinate every new flight and
review. AeroLoop puts Devin inside a bounded inspection loop that can act, check
the result, and try again before producing an auditable artifact.

## Slide 2 — The first flight is not the inspection

### Visible copy

**How it works today**

1. An inspector plans the route.
2. A pilot captures data.
3. A team reviews it later.
4. Missing evidence triggers another flight.

**The gap**

Coverage does not guarantee usable evidence. Distance, angle, motion, wind, or
an obstacle can invalidate a capture.

Human coordination sits between every attempt and verdict.

### Presenter note

Autonomous inspection drones already exist, so our claim is not that AeroLoop
invented automated flight. The problem is the fragmented feedback loop: route
planning, capture, quality review, re-capture, and reporting are often separate
steps. This slows inspections and makes repeat work expensive, especially on
large, dangerous, or remote assets.

## Slide 3 — AeroLoop closes the loop automatically

### Visible copy

1. **Authorize** — the work order defines the allowed inspection region.
2. **Decide** — Devin chooses the next bounded mission action.
3. **Guard** — an independent safety layer accepts or rejects it.
4. **Fly and observe** — the controller executes; the environment returns evidence.
5. **Verify** — independent checks issue PASS, retry, or safe stop and hash the artifact.

No human between trigger and artifact.

### Presenter note

The human remains at the correct boundaries: a person authorizes the asset and
inspection region before the run, and a qualified person decides what the final
artifact means for maintenance or return to service. Nobody has to select each
waypoint or rescue a weak capture during the autonomous run.

## Slide 4 — Devin is the mission engineer, not the motor controller

### Visible copy

**Why Devin**

- A resumable session retains mission context.
- Structured API output becomes bounded actions.
- The same agent can write and repair controller code against tests.

**What Devin does at runtime**

- Reads the current observation.
- Chooses targets, speed, standoff, and the next action.
- Responds to rejected actions and evidence gaps.

Safety, motor control, and the final verifier remain outside the model.

### Presenter note

Devin does not emit motor signals. It is the slower mission-level intelligence.
The deterministic controller closes the fast flight-control loop, while the
safety envelope can reject any unauthorized or unsafe proposal. The verifier,
not Devin, decides whether the evidence passes. If Devin is unavailable or
repeatedly proposes invalid actions, the system stops safely. Other models could
fit this interface; Devin is central here because the challenge asks us to put
Devin inside an engineering loop, and its API sessions connect build-time
engineering with runtime decisions.

## Slide 5 — The loop runs. Now judge it.

### Visible copy

**151** automated tests

**30/30** unseen seeded scenarios passed by the autonomous baseline

**5/5** recorded live-Devin missions passed *(small sample)*

**24/24** verified captures in a whole-asset example

### Primary demo

https://aeroloop-production.up.railway.app/mission_view.html

Choose **Devin live**, enter a mission, and watch decisions, safety checks,
flight, evidence, and the final verdict.

Real autonomous software loop. Simulated aircraft, sensors, and environment.

### Presenter note

Give judges Mission Control as the primary link because it demonstrates all
three challenge criteria in one place: autonomy, automatic verification, and a
usable artifact. Use the website for context and Backend View only when a judge
wants to inspect API and decision details.

Secondary links:

- Project website: https://aeroloop-production.up.railway.app/
- Backend audit: https://aeroloop-production.up.railway.app/backend_view.html

## Repository sources for claims

- Runtime architecture: `mission/agent.py`, `mission/episode.py`,
  `mission/safety.py`, `mission/contract.py`, `inspection/devin.py`
- Server and deployed views: `viz/server.py`, `viz/mission_view.html`,
  `viz/backend_view.html`
- Recorded results and limitations: `docs/RESULTS.md`
- Judge-facing positioning: `docs/JUDGE_QA.md`, `docs/REAL_WORLD_ROADMAP.md`
