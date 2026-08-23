# AeroLoop judge Q&A

Use this as an answer bank, not a script. Lead with the short answer, show the live
evidence if asked, and state limitations before a judge has to discover them.

## The problem in plain English

**One sentence:** Aircraft inspection is valuable only when the right surfaces were
actually seen from a usable angle; today, collecting that evidence is slow, repetitive,
and difficult to adapt when the first pass is incomplete.

**The gap:** Inspection drones already exist. The missing layer we explored is a general
software engineer inside the operational feedback loop: it reads measured mission state,
chooses a bounded next action, sees whether that action produced usable evidence, and
keeps working until an independent verifier can produce an auditable artifact.

**What AeroLoop does:** A work order starts a simulated inspection. Devin receives only
the current observation and allowed actions, chooses what the drone should do next, and
gets the measured outcome back. A deterministic safety envelope can reject the action.
The controller executes accepted actions in physics, and a separate verifier—not Devin—
decides `PASS`, `INSUFFICIENT_EVIDENCE`, or `ABORTED`.

**What AeroLoop does not do:** It has not flown real hardware, does not detect real
damage, and is not an approved maintenance procedure. Vision, audio, obstacles, and wind
are currently synthetic and seeded. The demonstrated artifact is the autonomous,
verified software loop.

## Twenty questions judges are likely to ask

### 1. What problem are you solving?

An inspection plan can say “visit every point” and still return unusable evidence because
the camera was too far away, badly aimed, moving, or interrupted. AeroLoop closes the
loop between **planned coverage** and **verified usable evidence**. It lets an agent request
the next bounded capture based on what the previous flight actually produced.

### 2. Why aircraft and engine inspection specifically?

It combines a costly physical workflow with an unusually strong software feedback loop.
Flight controllers are already tested in simulation; coverage, collision, clearance,
camera angle, steadiness, and elapsed time can all return objective verdicts. That makes
the domain suitable for autonomous agent work instead of uncheckable guessing.

### 3. Why not keep doing the inspection manually?

Humans should keep maintenance authority, but they should not have to manually repeat
every safe, measurable capture. Automation can reach awkward surfaces consistently,
repeat the same route, preserve traceability, and send people the evidence requiring
judgment. The goal is not to remove qualified inspectors; it is to remove repetitive
piloting and evidence bookkeeping from their critical path.

### 4. What actually works today?

The deployed system accepts a plain-language mission, starts a real backend job, runs a
rate-controlled quadrotor simulation with seeded disturbances, lets either Devin or a
labelled deterministic baseline choose mission actions, applies a safety envelope, and
returns a replay plus an independent verification artifact. The repository also contains
controllers that Devin wrote and later debugged through the test loop.

### 5. What is simulated, and what is real?

The physics, camera/evidence gate, wind, moving objects, vision labels, audio labels, and
telemetry are simulated. The Devin API sessions, action contract, policy decisions,
controller execution, verifier, artifacts, web backend, and deployment are real software.
No physical drone, camera, microphone, or thermal sensor has been connected yet.

### 6. How exactly did you use Devin?

Twice. First, Devin acted as the engineer: it wrote flight controllers, ran tests, read
failures, and fixed code. Second, Devin became the runtime mission agent: one resumable
API session receives observations and returns structured actions such as inspect,
quiet-hover, return-home, complete, or abort. The artifact records the session, proposed
actions, rejections, outcomes, and final independent verdict.

### 7. Is Devin really flying, or is the frontend pretending?

The frontend only submits a work order and renders backend state. For a live Devin run,
the Python backend creates a Devin session, sends observation packets, validates each
structured response, and passes accepted mission primitives to the controller and
physics. The UI cannot manufacture a passing verdict; it displays the verifier output.
The local test pilot remains available and is explicitly labelled as a baseline.

### 8. Does Devin send raw motor commands?

No, deliberately. Devin selects intent-level, allow-listed mission actions and bounded
parameters. A deterministic controller converts accepted flight targets into actuation
inside the simulator. Putting a network language model in a fast motor-control loop would
add latency and nondeterminism where a conventional controller is stronger.

### 9. Why Devin rather than Claude, Codex, or an onboard model?

The honest answer is that no law of physics makes this exclusive to Devin. The challenge
asked us to put Devin inside an industry loop, and Devin is useful here because it can
operate a resumable software-engineering session, use repository tools, run verifiers,
repair code, and also return structured runtime decisions through an API. The safety and
action boundary is intentionally model-agnostic. Our value is the verified loop and
artifact, not a claim that other models are incapable.

### 10. Where is the human in the loop?

Outside the autonomous trigger-to-artifact boundary. A qualified person authorizes the
asset and procedure before a mission, can intervene for safety at any time, and reviews
the finished evidence before operational disposition or return to service. Between
trigger and artifact, a human does not choose waypoints or repair agent actions.

### 11. How does the system know whether the result is good?

The verifier independently checks required evidence coverage, collisions, floor contact,
engine clearance, camera distance and aim, steadiness, time budget, safe return, and
planner availability. Devin claiming “complete” is only a request to end; it does not
set the result.

### 12. What stops Devin from doing something unsafe?

Every action must match a versioned schema and an allow-list. The safety envelope rejects
stale observations, replayed action IDs, unauthorized waypoints, excessive speed or
duration, invalid hover requests, exhausted attempts, and unsafe geometry. Rejections go
back to Devin with reasons; the backend does not silently substitute its own target.

### 13. What happens if Devin is slow, wrong, or unavailable?

The mission fails closed. Invalid actions are rejected, time and attempts are bounded,
and an unavailable planner cannot produce `PASS`. The system performs a bounded safe
stop/return behavior and reports insufficient evidence or aborted. The deterministic
baseline allows testing without network access but is never represented as Devin.

### 14. How do wind, birds, obstacles, vision, and audio work?

Today they are deterministic scenario inputs generated from a seed, so a failure can be
reproduced. The mission observation exposes only what the simulated sensors report, not
future disturbance schedules. The next real-world step is replacing each synthetic
adapter with timestamped, calibrated camera, thermal, microphone, perception, and
autopilot data while keeping the same observation/action/artifact contract.

### 15. Is this just one prepared animation?

No. A judge can enter a new sentence and random or explicit seed. The backend generates
the authorized region and scenario, runs a fresh job, streams progress, and creates a new
result. Recorded evidence is labelled as recorded; the live simulator is a separate
working path. Unseen-seed tests are documented in `docs/RESULTS.md`.

### 16. How are you different from Donecle, Skydio, Flyability, or Percepto?

Those companies prove that autonomous inspection is real, and they are far ahead in
hardware, deployments, sensor quality, and approvals. Donecle already offers automated
aircraft scanning and image analysis; Skydio and Percepto offer autonomous inspection
platforms; Flyability pairs inspection drones with analysis software. AeroLoop is not
claiming to replace them. Our experiment is the **general software-engineering agent**
inside a bounded, independently verified mission-and-code loop, with every decision and
artifact exposed for audit.

### 17. If competitors already automate inspections, what is the remaining gap?

Productized autonomy normally executes capabilities its vendor engineered in advance.
Our layer asks whether a general agent can both improve the software through tests and
adapt runtime evidence collection through the same explicit verifier. The gap is not
“make a drone fly”; it is “make changing conditions announce failure in a form an agent
can act on, while keeping safety and disposition outside the model.”

### 18. Why have others not already solved your exact version?

We should not say they cannot. Established vendors may have internal adaptive planners
that are not public. The hard integration problem is aligning five things at once:
machine-readable procedures, calibrated observations, a constrained action language,
an independent verifier, and regulator/auditor-friendly artifacts. A language model alone
does not solve any of those. AeroLoop demonstrates their software shape, not commercial
or regulatory completion.

### 19. What useful artifact comes out?

A controller revision and test record from the engineering loop, plus a mission artifact
containing the work order, seed/scenario, observation-action history, policy rejections,
flight trace, evidence coverage, final disposition, hashes, and Devin session metadata.
That is the beginning of an inspection evidence package an engineer can review, rather
than a chat transcript or a video with no provenance.

### 20. What must happen before this can touch a real aircraft?

Integrate a real autopilot in hardware-in-the-loop, calibrate and timestamp sensors,
validate perception against representative data, add redundant obstacle avoidance and
communications-loss behavior, bind missions to approved maintenance data, secure and
sign the full chain, test on noncritical assets, collect reliability evidence, and work
with operators, OEMs, authorities, insurers, and qualified maintenance personnel. The
first field role should be evidence collection and decision support, not autonomous
return-to-service approval.

## Competitor comparison: the honest version

| System | What their own materials show | What AeroLoop adds in this challenge | Where they are stronger |
| --- | --- | --- | --- |
| [Donecle Iris](https://www.donecle.com/iris-gvi/) | Automated aircraft visual inspection, image analysis, reports, nacelle/component use cases, and aviation approvals | A visible general-agent code-and-runtime loop with an independent verifier and action rejection history | Real aircraft, sensors, operations, analysis, and approvals |
| [Skydio](https://www.skydio.com/) | Autonomous asset inspection, remote flight, sensor capture, and mapping | A model-facing observation/action contract designed for software-agent iteration | Mature autonomous hardware and scaled drone platform |
| [Flyability Elios + Inspector](https://www.flyability.com/inspector) | Confined-space capture plus inspection-data localization, analysis, and reporting | An agent that decides the next bounded evidence action from verifier gaps | Collision-tolerant hardware, LiDAR/imagery, and field workflow |
| [Percepto AIM](https://percepto.co/remote-operations/) | Remote autonomous inspections and monitoring with drone-in-a-box operations | A transparent engineering-agent loop that can also repair controller code | Persistent remote operations, fleet management, and deployments |

The defensible positioning is: **we did not invent autonomous inspection; we built the
challenge’s missing software-engineer layer inside a verifiable version of it.**

## Devil's advocate: strongest attacks and honest responses

| Attack from a skeptical judge | Our best defense | What we must concede |
| --- | --- | --- |
| “This is a toy simulator.” | It is executable, seeded, adversarial, and produces repeatable numeric verdicts; simulation is the correct pre-hardware validation layer. | It is not high-fidelity certification evidence or a hardware-in-the-loop test. |
| “Donecle already solved aircraft inspection.” | Donecle validates the market. Our submission targets a different layer: a general agent that writes/fixes software and chooses bounded runtime actions under an independent verifier. | Donecle has the real product, data, approvals, and customers. We do not. |
| “The LLM is unnecessary; a rule planner works.” | The baseline proves that rules are strong. Devin earns its place when the observation is ambiguous, constraints interact, procedures vary, or the software itself must be repaired. Recorded runs show it adapting to gap reasons and safety rejections. | For fixed geometry and known failures, deterministic planning is cheaper and often preferable. |
| “Your verifier grades rules you wrote yourselves.” | The verifier is separate from the planner and controller, pins hard invariants, tests unseen seeds, and can reject a model’s completion claim. | Thresholds are still our simulation specification; real thresholds must come from approved procedures and validation data. |
| “You left a human in the loop, so autonomy fails.” | No human touches trigger-to-artifact. Authorization, emergency authority, and post-artifact approval are outside that challenge boundary and are necessary in safety-critical work. | A real maintenance workflow will remain human-accountable. |
| “Vision and audio are fake.” | They are explicitly labelled seeded sensor adapters used to test control flow and failure handling. The contract is ready for real timestamped sources. | We have not demonstrated real perception quality. |
| “Devin is just a remote planner, not a pilot.” | Correct at the motor-loop level by design. Devin is the mission authority choosing bounded actions; deterministic control closes the fast physical loop. | The phrase “Devin flies” must always be explained at this mission-control level. |
| “Another model could copy this.” | Yes. The safety/verifier architecture is model-agnostic. For this challenge, the proof is that Devin sessions actually wrote, debugged, and ran the loop. | The foundation model is not the moat; validated integrations, data, procedures, and approvals would be. |
| “A public live API is unsafe and expensive.” | Server-side credentials, same-origin requests, strict input bounds, one concurrent public Devin mission, per-client/global hourly limits, and an ACU ceiling constrain the demo. | This in-memory demo limiter is not production billing or identity infrastructure. |
| “A PASS could be lucky.” | The suite runs batches and unseen seeds; planner failure blocks PASS; the artifact records every accepted/rejected action and evidence target. | Five recorded live Devin missions are a small sample, not a reliability study. |

## A 30-second explanation

“Inspection drones already exist. The unsolved part we chose is what happens when the
first pass does not produce usable evidence. AeroLoop gives Devin the current telemetry,
evidence gaps, and a small set of safe actions. Devin chooses the next capture, a
deterministic safety layer may reject it, physics executes it, and an independent
verifier—not Devin—decides whether the inspection is complete. The same project also
shows Devin writing and repairing the controller through tests. Everything today is
simulation, but the trigger-to-artifact loop is real, deployed, and auditable.”

## A one-line close

**Existing systems automate a route. AeroLoop demonstrates an engineer that can improve
the route-making software, adapt the mission from evidence, and still be overruled by
safety and verification.**
