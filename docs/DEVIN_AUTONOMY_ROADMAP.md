# Devin autonomy deployment roadmap

## Product statement

> **AeroLoop is Devin for autonomous physical inspection.**
>
> Devin receives live visual, acoustic and flight observations, chooses every
> mission-level drone action, reacts to unseen disturbances and evidence failures,
> and continues until an independent verifier accepts the inspection or the system
> safely stops. Humans retain mission authority and final inspection approval.

This is the next build after the adaptive-evidence milestone. It changes Devin from
the engineer that writes `controller.py` into the runtime mission agent. The existing
code-writing workflow remains useful, but it is no longer the primary product demo.

## Challenge alignment

The challenge asks for a domain with an objective feedback loop, an output expressible
as code, programmatically triggered Devin sessions and a useful verified artifact with
nobody intervening between trigger and result. AeroLoop should demonstrate both layers
without mixing their responsibilities:

### Judged engineering loop

```text
unseen work order and seed
        -> programmatically create Devin session
        -> Devin writes or improves inspection policy/controller code
        -> hidden simulator and evidence verifier run
        -> failures return automatically to the same Devin session
        -> Devin changes the code and reruns
        -> signed controller + verification + evidence artifact
```

This is the clearest answer to the challenge's write-run-test-fix requirement. No person
chooses a fix, edits code, selects a retry or approves an intermediate result. A human
may review the already-produced artifact afterward.

### Runtime autonomy loop

The controller produced by that engineering loop is then exercised in the flight view.
In Devin mission mode, the Devin API also chooses mission-level inspection actions from
live observations. This makes the autonomous layer visible, but it must not replace the
code-producing and independently verified challenge artifact.

The complete judge command should eventually trigger both loops and produce one linked
artifact containing the engineering session, code revision, runtime session, evidence
and verifier result.

## What "Devin controls the drone" means

The drone has two control rates:

1. **Devin mission loop** — Devin chooses every meaningful action: which region to
   approach, where to move next, whether to hold, capture, orbit, re-capture, avoid,
   return or stop.
2. **Local flight loop** — `Controller.step()` runs at 50 Hz to stabilise the vehicle
   and execute the latest accepted Devin command inside acceleration, speed,
   clearance and geofence limits.

The second loop is an actuator and safety mechanism, not an autonomous mission
planner. In Devin-controlled mode, local code must not select the next inspection
target or silently continue the mission when Devin is unavailable.

## Non-negotiable challenge mode

- Every autonomous mission creates a Devin API session.
- The mission cannot progress beyond safe initialisation until the session is ready.
- Devin chooses every mission primitive after receiving the current observation.
- The backend may reject an unsafe action, but it may not replace it with a locally
  selected inspection action. It reports the rejection to Devin for another choice.
- Loss of Devin connectivity causes a bounded hold followed by return-home or land.
- The hidden scenario, future gusts, obstacle paths and verifier answer are never sent
  to Devin.
- A deterministic rule planner is allowed only in tests and as an explicitly labelled
  baseline. It is not the challenge demo.
- Every Devin input, structured output, validation result and executed action is
  recorded in the inspection artifact.

## Runtime architecture

```text
seeded hidden scenario / real world
              |
              v
     simulator or sensor adapters
   visual + audio + telemetry + events
              |
              v
       observation/evidence service
              |
              v
         Devin mission session
       reason + choose next action
              |
       structured JSON command
              v
      policy and safety validator <---- human pause / abort
              |
       accepted bounded primitive
              v
      controller + drone dynamics
              |
         outcome observation
              +------------------------> repeat
              |
       independent verifier
              |
       human final approval
```

## Devin API usage

Use the organisation API as the runtime backbone, not merely as a script that asks
Devin to edit the repository.

### Mission start

Create one session per mission with:

- `structured_output_required: true`.
- A self-contained JSON Schema in `structured_output_schema`.
- An AeroLoop inspection `playbook_id` containing operating, abstention and escalation
  rules.
- Relevant approved-procedure `knowledge_ids` when available.
- A bounded `max_acu_limit`, mission title and searchable tags.
- Evidence references through `attachment_urls` only when policy permits upload.
- `resumable: false` for disposable simulator missions unless audit requirements say
  otherwise.

Store the returned session ID and URL before flight begins.

### Observation/action cycle

After every executed primitive or material event:

1. Build an observation packet containing only information available to the drone.
2. Hash the packet and add it to the audit artifact.
3. Send the packet to the same Devin session through the session-message API.
4. Poll at the documented interval for status and structured output.
5. Validate schema version, observation ID and action sequence number.
6. Send the proposed action through the local policy validator.
7. Execute an accepted action and report the measured outcome to Devin.
8. Return rejected actions and reasons to Devin; do not invent a substitute action.

### Mission completion

- Require Devin to return `complete`, `insufficient_evidence`, `needs_human` or
  `abort`.
- Run the independent verifier regardless of Devin's claimed disposition.
- Persist the final structured output, session metadata, evidence hashes, validator
  decisions and verifier result.
- Require human approval before an inspection artifact becomes operationally final.
- Archive the session according to the retention policy.

### Separate improvement loop

After the mission, a separate Devin session may receive the failed artifact and
repository, improve non-safety-critical orchestration code, run tests and open a pull
request. Runtime mission authority and code-writing authority must be separate sessions
with separate artifacts.

Official API references:

- <https://docs.devin.ai/api-reference/v3/sessions/post-organizations-sessions>
- <https://docs.devin.ai/api-reference/v3/sessions/get-organizations-session>
- <https://docs.devin.ai/api-reference/v3/sessions/post-organizations-sessions-messages>
- <https://docs.devin.ai/api-reference/v1/structured-output>

## Observation contract

Devin receives snapshots, not the simulator's hidden state:

```json
{
  "schema_version": 1,
  "mission_id": "mission-...",
  "observation_id": 12,
  "previous_action_id": "action-11",
  "time_s": 34.8,
  "pose": {"position_m": [1.2, 2.9, 3.1], "velocity_mps": [0.1, 0.0, 0.0]},
  "flight": {"battery_fraction": 0.72, "wind_estimate_mps": 2.4, "clearance_m": 0.81},
  "events": [{"type": "moving_obstacle_detected", "bearing_deg": 31, "confidence": 0.82}],
  "evidence": [{"waypoint_index": 10, "status": "marginal", "reasons": ["blur"]}],
  "available_targets": [9, 10, 11],
  "allowed_primitives": ["move_to", "capture", "quiet_hover", "capture_orbit", "return_home", "abort"]
}
```

Synthetic camera and audio adapters must remain labelled synthetic. The contract should
later accept real image, audio, thermal and depth references without changing the
mission loop.

## Devin action contract

```json
{
  "schema_version": 1,
  "mission_id": "mission-...",
  "observation_id": 12,
  "action_id": "action-12",
  "primitive": "quiet_hover",
  "waypoint_indexes": [10],
  "constraints": {"duration_s": 5, "max_speed_mps": 0.4},
  "reason": "The last capture was blurred during a gust; hold and recapture.",
  "expected_evidence": ["stable_visual_closeup"],
  "confidence": 0.86,
  "human_confirmation_required": false
}
```

The backend rejects stale observation IDs, duplicate action IDs, unknown targets,
unsupported primitives, excessive motion/dwell, exhausted budgets and actions that
violate the current safety state.

## Human authority loop

The challenge remains autonomous between start and artifact: a person does not choose
waypoints or repair Devin's actions. Humans have four explicit authorities:

1. **Mission authorisation** — approve the asset, procedure and operating envelope.
2. **Identity confirmation** — required when an unexpected or ambiguous asset changes
   which approved procedure applies.
3. **Safety intervention** — pause, return-home, land and emergency stop at any time.
4. **Final disposition** — inspect the evidence package and approve or reject the
   operational result.

For the judge demo, use a pre-confirmed synthetic asset so the autonomous loop runs
without an intermediate human decision. Still demonstrate the pause/abort control and
final approval gate.

The trigger-to-artifact challenge boundary ends before final operational approval. This
keeps the judged engineering process autonomous while preserving a real-world safety
gate outside it.

## Hidden scenario engine

The backend should generate seeded but undisclosed conditions:

- gusts and changing wind;
- moving birds, people or equipment;
- occlusions and temporary blocked approaches;
- camera blur, poor exposure and missing frames;
- acoustic noise and low signal-to-noise captures;
- unknown or substituted components;
- sensor dropouts and stale observations;
- evidence defects that require different viewpoints.

Seeds make runs reproducible for tests, but Devin receives only resulting observations.
The next action must not be precomputed by the backend.

## Deployment milestones

### Milestone 0 — repair the merged baseline

- [x] Fix sector evidence accounting so selected sectors are not scored against all 24
      nacelle waypoints.
- [x] Add integration tests for top-side and ring-only evidence sets.
- [x] Preserve the deterministic rule planner as a labelled comparison baseline.

### Milestone 1 — interactive simulator protocol

- [ ] Refactor the one-shot flight run into `reset`, `observe`, `act` and `verify`.
- [ ] Advance physics for one bounded action rather than completing an entire sweep.
- [ ] Add action IDs, observation IDs, deadlines and replay protection.
- [ ] Add hidden seeded obstacle, visual-quality and audio-noise events.
- [ ] Prove that no scenario truth leaks into the observation packet.

### Milestone 2 — Devin-required mission agent

- [x] Add `inspection/devin.py` for authenticated v3 session creation, polling,
      timeouts, structured output and a first `DevinRecapturePlanner` action boundary.
- [x] Validate Devin output locally and pass every request through the existing policy
      validator.
- [x] Add `scripts/run_devin_mission.py` as the first live mission command.
- [x] Require `DEVIN_API_KEY` and `DEVIN_ORG_ID`; fail closed when either is absent.
- [x] Keep credentials server-side and out of prompts, browser responses and artifacts.
- [x] Never report `PASS` when the planner was unreachable. An unanswered planner sets
      `planner_failed`, forces `INSUFFICIENT_EVIDENCE` and is surfaced in the artifact,
      the CLI and the browser reply, even when the initial sweep was clean.
- [x] Bound every planner action to the sector the work order authorised. The policy
      validator rejects waypoints outside the authorised set instead of only checking
      them against the full 24-waypoint nacelle.
- [ ] Extend the first one-round API slice into the complete observation/action mission
      loop from Milestone 1.
- [ ] Show the session URL, current reasoning, proposed action and validator result in
      the flight view.

### Milestone 3 — human controls and audit artifact

- [ ] Add visible pause, return-home, land and emergency-stop controls.
- [ ] Add asset-confirmation and final-approval states with separate identities.
- [ ] Hash every observation/action pair and include the Devin session ID.
- [ ] Make any post-approval mutation invalidate the artifact.
- [ ] Export one replayable mission package for judges.

### Milestone 4 — deployment

- [ ] Package the mission backend as one service with a health endpoint and persistent
      artifact directory.
- [ ] Keep the simulator and Devin credentials on the server; serve only the UI to the
      browser.
- [ ] Add a mission worker so long Devin calls do not block HTTP requests.
- [ ] Stream mission state and decisions to the UI with server-sent events or WebSocket.
- [ ] Add explicit session, action and wall-clock budgets.
- [ ] Demonstrate clean hold/return behaviour when the network or Devin fails.

### Milestone 5 — real sensor and drone adapters

- [ ] Replace synthetic evidence with camera, microphone and telemetry adapters while
      preserving the observation schema.
- [ ] Replace simulator actuation with an autopilot primitive adapter while preserving
      the action schema and policy validator.
- [ ] Test first in a cage with a stationary representative component.
- [ ] Keep a hardware emergency stop independent of Devin and the backend.

## Test strategy

### Tests without API credentials

- [x] Schema parsing and rejection tests using representative Devin responses.
- [x] A fake Devin transport that chooses actions but exercises the session adapter.
- Deterministic replay of observation/action traces.
- Policy adversarial tests: stale actions, unknown waypoints, excessive dwell, repeated
  IDs, collisions and exhausted time budgets.

### Live API tests

Run only when credentials are explicitly present:

- Create a real tagged session with the production JSON Schema.
- Send a fixed synthetic observation and obtain a valid structured action.
- Execute that action in the simulator and send its outcome back to the same session.
- Verify that session ID, structured output and policy decision appear in the artifact.
- Terminate safely on timeout, invalid output, API error or depleted budget.

### Hidden-seed evaluation

Compare the deterministic baseline and Devin on unseen seeds using:

- successful verified inspections;
- collisions and minimum clearance;
- evidence completeness and quality;
- recovery from obstacles, gusts and sensor failures;
- human interventions;
- invalid/rejected action rate;
- Devin latency, ACU use and mission cost;
- safe-stop success when connectivity is removed.

## Judge demo

1. A judge supplies an unseen seed.
2. `scripts/run_devin_mission.py` creates a visible Devin session.
3. The simulator reveals wind, obstacles and evidence problems incrementally.
4. The UI shows each observation, Devin decision, validation and executed movement.
5. At least one initial capture fails and Devin changes the mission to repair it.
6. The independent verifier—not Devin—returns PASS or `INSUFFICIENT_EVIDENCE`.
7. A human reviews and signs the exact artifact digest.
8. Replay proves what Devin saw and why the drone moved.

## How to use the first Devin API slice

### Deterministic comparison baseline

```bash
python -m viz.server
```

Open <http://127.0.0.1:8765/flight_view.html>. Inspection commands use the labelled
`RuleBasedRecapturePlanner` baseline.

### Live Devin re-capture planning

```bash
export DEVIN_API_KEY=cog_...
export DEVIN_ORG_ID=org_...
python scripts/run_devin_mission.py \
  --work-order "inspect top side, light wind seed 606076"
```

The command creates a real Devin session with required structured output, lets Devin
choose the bounded follow-up capture actions, validates and flies them, then writes a
hashed artifact under `artifacts/`.

To use the existing browser UI with Devin as its re-capture planner:

```bash
export DEVIN_API_KEY=cog_...
export DEVIN_ORG_ID=org_...
AEROLOOP_INSPECTION_PLANNER=devin python -m viz.server
```

This is a first vertical slice. The initial sweep is still produced by the existing
mission builder; Milestone 1 and the remaining Milestone 2 work convert every subsequent
mission action into the iterative Devin observation/action protocol.

### Tests without spending API credits

```bash
python -m pytest -q
python -m pytest -q tests/test_devin_planner.py tests/test_inspection_adaptive.py
```

## Commercial model

Customers pay for reduced aircraft downtime, fewer repetitive technician-hours and a
traceable inspection record—not for the presence of an AI model.

Potential pricing, to validate through paid pilots:

| Offer | Illustrative price assumption |
| --- | ---: |
| Controlled paid pilot at one component/site | $50,000–$100,000 |
| Initial deployment and workflow integration | $75,000–$250,000 |
| Annual site software/support licence | $150,000–$300,000 |
| Usage option | $250–$1,500 per completed inspection |

Illustrative revenue scenarios—not forecasts or known competitor prices:

| Stage | Assumption | Annual revenue |
| --- | --- | ---: |
| Paid validation | 3–5 pilots | $150,000–$500,000 |
| Early product | 20 sites at $150k–$250k | $3m–$5m |
| Established vendor | 100 sites at $200k–$300k | $20m–$30m |
| Category leader | 300 sites at $250k–$400k | $75m–$120m |

Market evidence supports the problem but does not prove AeroLoop's revenue. Oliver
Wyman reports global aviation MRO demand of $136 billion in 2025 and expects it to
approach $193 billion by 2030. Donecle advertises aircraft inspections up to ten times
faster and component scans measured in minutes; Mainblades reports a 75% reduction for
lightning-strike inspection time. Donecle's €10 million 2026 funding round is evidence
of investment interest, not disclosed revenue.

- <https://www.oliverwyman.com/our-expertise/insights/2026/feb/global-fleet-and-mro-market-forecast-2026-2036.html>
- <https://www.donecle.com/>
- <https://www.donecle.com/components/>
- <https://www.mainblades.com/>
- <https://www.donecle.com/wp-content/uploads/2026/04/Donecle-Press-Release-ENG-FV.pdf>

## Definition of done

This roadmap is complete when all of the following are true:

- Removing Devin credentials prevents autonomous mission progress.
- No local component chooses inspection targets in Devin-controlled mode.
- Devin controls every mission primitive on at least 30 unseen seeded scenarios.
- The independent verifier passes the required threshold with zero collisions.
- Network loss and invalid Devin output always produce a safe stop.
- The UI and artifact make Devin's contribution unmistakable.
- A human can intervene immediately and remains the final operational authority.
