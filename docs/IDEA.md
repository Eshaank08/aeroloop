# IDEA

## One line

Devin autonomously writes, tests, and fixes the flight-control software for a drone that
inspects an aircraft engine for damage, verified entirely in simulation, with a human
approving only the final step before it would ever fly near a real aircraft.

## The industry, and why it has a loop

Autonomous drone-based aircraft inspection is a real, already-approved, currently-scaling
practice in 2026. This is not a scenario invented for a pitch.

- **FAA Part 145 and EASA Part 145** both approve drone inspection for General and
  Detailed Visual Inspection.
- **Airbus** approved it for the A320 family. **Boeing** added it to the 737 maintenance
  manual.
- Airlines and MROs already running it: **AAR, Austrian Airlines, KLM, LATAM**, via
  providers like **Donecle** and **Mainblades**.
- The real performance bar: **99.1% inspection coverage autonomous vs 78% for a manual
  walk-around**. A full widebody scan runs under two hours; Donecle does a full fuselage
  scan in under fifteen minutes.

So the question "should drones inspect aircraft" is already settled by the industry. Our
question is sharper and harder to argue with:

> Can an AI engineer build and verify that flight software entirely on its own, the same
> way it already builds and verifies ordinary code?

**Why the loop exists here.** Flight software is the rare physical-world discipline that
already validates in simulation before it ever touches hardware. Real drone and aerospace
teams run controllers through simulated flight for weeks before a first real flight,
because crashing hardware is expensive. That means a verdict already exists, it is
already trusted by the industry, and it is already software. We are not inventing a
checker. We are handing Devin the one the industry already uses.

## Why this framing beats a generic robotics demo

A generic "AI controls a robot" demo has no external standard to be judged against. This
one has a real regulator, real named operators, and a published performance number we can
target and be measured on.

## The Cognition connection

Named Cognition customers include **GE Aerospace** (jet engines), **NASA**, the
**U.S. Army**, the **U.S. Navy**, and **Anduril**. This idea sits precisely in that
cluster, which makes the closing line honest rather than opportunistic:

> This is the industry Cognition is already in. We built the missing piece.

## Ideas considered and dropped

| Idea                                | Why dropped                                                                |
| ----------------------------------- | -------------------------------------------------------------------------- |
| Cybersecurity, patch and verify CVEs | Cognition already ships this as Devin Security Swarm                        |
| Defense / government                | Cognition already has Cognition for Government, FedRAMP High, DOE Genesis   |
| Hardware / RTL design               | Already shown as a past hackathon team project in Cognition's own deck      |
| AI builds a startup, market sim     | Same, already shown as past team projects                                   |
| Insurance and hotel pricing         | Needs real historical data that cannot be credibly obtained in 48 hours     |
| Legal redlining, tax prep           | The checker would be a rulebook we wrote ourselves, so passing proves little |
| Accounting close, payroll           | Airtight but the weakest story in the room                                  |
| Physical AI, robot manipulation     | Strong local TUM resonance, but no real Cognition evidence to point at      |
| Data centers, PyDCM / SustainDC     | Hot trend, zero Cognition connection, weakest under Q&A                     |

The inspection-drone idea is the only one with **both** a real current named-customer
anchor at Cognition **and** a real current regulator-approved industry practice.

## How the approach changed while building (for the pitch)

Track this honestly as it happens. Current record:

1. Started by ranking industries on verifier strength and ruled out anything where we
   would be grading our own homework with a rulebook we wrote the same weekend.
2. Ruled out every domain Cognition already occupies, because building in their own
   territory means losing the comparison by default.
3. Rejected a real-hardware drone, then realized simulation is not a workaround. It is
   how the industry itself validates flight software before first flight.
4. Chose to wire the verifier in as the pytest suite rather than write custom retry
   logic, so Devin's existing test-fix-rerun habit does the iteration for free.
5. **Started narrow: Devin writes a controller, a verifier grades it.** One shot. The
   agent produced `controller.py` for simulator v1, the verifier said PASS or FAIL, and
   that was the whole loop. Honest but thin, because the agent's only decision was made
   at compile time. Once the software shipped, nothing intelligent was left in the
   system.
6. **Added an adaptive evidence loop.** Instead of grading a sweep as done or not done,
   we scored evidence per waypoint and let a planner ask for targeted re-captures where
   the evidence was weak. That is where the interesting behaviour lives: reacting to
   what actually happened rather than to what was planned.
7. **Found that a clean sweep with an unreachable planner still reported PASS. Made it
   fail closed.** If the controller happened to cover everything on its own, the mission
   reported success even when the planner never answered a single call. That is exactly
   the failure the challenge warns about: a system that cannot tell a good result from a
   lucky one. Now, if the authority deciding what to inspect goes silent, the vehicle
   performs a bounded return toward home and the disposition can never be PASS, no
   matter how much evidence happens to exist.
8. **Found the planner could fly outside the authorised sector. Bounded it.** Nothing
   stopped a planner from requesting waypoints it had not been cleared for. Added
   `mission/safety.py`, an envelope that rejects out of sector waypoints, over long
   actions, excess speed, stale observation ids, replayed action ids and exhausted per
   waypoint attempts. The deliberate design choice: the envelope reports the rejection
   back to the agent and never substitutes a target of its own, because an envelope that
   quietly picks a replacement is doing the agent's job and hiding the agent's mistakes.
9. **Moved from one shot re-capture planning to Devin as the full runtime mission
   agent, on simulator v2.** The re-capture planner still assumed the flight plan was
   basically fixed. Simulator v2, a rate controlled quadrotor with a camera gate,
   removed that assumption: `mission/episode.py` turns the flight into reset, observe,
   act, verify, and Devin chooses every single action from sensed observations alone. It
   never sees the wind schedule or the verifier answer, and its claim of completion does
   not override the verifier.
10. **The runtime loop then broke the controller, and an agent fixed it.** Handing
    partial waypoint sets to `controller2.py` exposed a `ZeroDivisionError` the batch
    verifier could never have found, because the batch always passes the full nacelle. A
    separate Devin session diagnosed and fixed it in PR #21, verified identical routes
    over 2000 random cases, and lifted the mission loop from 27/30 to 29/30. No human
    edited the controller. That was the moment the project stopped being "an agent wrote
    some code we tested" and became a loop that finds its own defects.

What we would say to a judge about the shape of that change: the first version put an
agent inside a build loop, which is a thing Devin already does well. The version we
submitted puts an agent inside a runtime loop that is bounded, auditable, and able to
refuse the agent, and every one of those bounds exists because we watched the system
get it wrong first.
