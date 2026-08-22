# AeroLoop, pitch deck

Cognition track, EHL Munich. "Find an Industry, Give it an Engineer."

Fourteen slides. Speaker notes sit under each slide as a blockquote. Two spoken scripts,
60 seconds and 3 minutes, are at the end of this file.

---

## Slide 1: AeroLoop

**Devin does not just write the flight software for a drone inspecting a jet engine
nacelle. Devin flies the mission.**

An independent verifier that existed before Devin wrote a line decides whether the
inspection was good enough. A safety envelope bounds every action. Humans keep four
authorities and nothing else.

> Open with the one line and stop talking for a beat. The claim people expect is "AI
> writes the controller". The claim we are actually making is one step past that, and the
> whole deck is the evidence for it. Say up front that everything runs in simulation, so
> nobody has to wonder when the catch is coming.

---

## Slide 2: The problem

An aircraft on the ground earns nothing, and the inspection that keeps it there is done
by a person walking around it with a torch.

- Global aviation MRO demand was **$136 billion in 2025** and is expected to approach
  **$193 billion by 2030** (Oliver Wyman, Global Fleet and MRO Market Forecast 2026-2036).
- Manual walk-around inspection averages **78% surface coverage**. Autonomous drone
  inspection reaches **99.1%**.
- Typical manual miss rate is around **15%**. Automation raises detection by about
  **27 percentage points**.
- Nacelle inspection is the awkward case. The fan cowl latches sit low on the underside,
  a zone the Aviation Safety Network timeline describes as one that "can only be
  inspected by crawling under it." Over three decades there are **45 or more** documented
  A320 family fan cowl door losses.
- Southwest Airlines Flight 1380 (2018) was a fan blade root fatigue crack that surface
  inspection could not see. NTSB report AAR-19/03.

The failure mode is not usually a bad reading. It is no reading at all. A panel that was
never covered at the right distance and angle is not clean, it is unseen.

> Do not oversell this. The point of the slide is that coverage, not cleverness, is the
> binding constraint, and that coverage is measurable. The defect research on the repo is
> a collaborator's work with real citations, and it exists to explain why coverage
> matters, not to claim we detect anything.

---

## Slide 3: Why this industry has the loop the challenge asks for

The brief says pick a domain where every attempt gets a verdict and a wrong answer
announces itself. Flight software already works that way.

- Aerospace teams validate controllers in simulation for weeks before first flight,
  because crashing hardware is expensive. The verdict already exists and the industry
  already trusts it.
- The verdict is numeric and adversarial: waypoint coverage, collision count, elapsed
  time, on seeded randomized winds. A controller cannot pass by memorising one scenario.
- Regulators already accept the practice. FAA Part 145 and EASA Part 145 approve drone
  General and Detailed Visual Inspection. Airbus approved it for the A320 family, Boeing
  added it to the 737 maintenance manual. AAR, Austrian Airlines, KLM and LATAM run it
  through providers such as Donecle and Mainblades.

So the question "should drones inspect aircraft" is settled. Our question is narrower:
can an AI engineer build, verify and then actually run that mission on its own.

> The judges called out three failure modes. No way to check the work, human in the loop,
> and one prepared example. This slide is the answer to the first. The verifier is
> external, it predates Devin's first line, and we never edited the simulator to make a
> failing controller pass.

---

## Slide 4: Where we started, and how the bar moved

**Step 1. Devin writes the controller.** A point mass drone, seeded wind, 24 inspection
waypoints in three rings of eight around the nacelle. Devin wrote `controller.py` against
the verifier, read its own failures through pytest, and fixed them. No human edited that
file. Result: **30/30 scenarios PASS, mean coverage 100.0%, zero collisions.**

**Step 2. We raised the bar on ourselves.** A point mass hides the part that makes drone
inspection hard: a quadrotor can only push along its own thrust axis, so translating means
tilting, and tilting moves the camera. Simulator v2 replaced the vehicle with a rate
controlled quadrotor with thrust limits, motor lag and drag, and replaced the coverage
rule with a camera gate. A waypoint counts only when all three hold on the same tick:

| Gate condition | Threshold |
| --- | --- |
| Distance to waypoint | at most 0.5 m |
| Camera aimed at the nacelle surface | within 60 degrees of boresight |
| Shot steady | body rate at most 1.5 rad/s and speed at most 2.5 m/s |

Devin wrote `controller2.py` for that vehicle. Result: **29/30 PASS, mean coverage 99.9%,
719 of 720 waypoints inspected.**

> This is the first half of the "how did your approach change" answer. We made the task
> harder after Devin had already solved the easy version, because passing a point mass
> task does not prove you can hold a camera on a nacelle in a gust. Being able to say we
> tightened the verifier rather than loosened it is the credibility of the whole project.

---

## Slide 5: The turn, Devin stops being only the engineer

Writing the controller is still a code task. The bigger move was making Devin the runtime
mission agent.

In the autonomous loop Devin receives an observation packet, chooses one bounded mission
action, and gets the measured outcome back. One resumable Devin API session answers every
observation of a mission. Every answer must name the observation it responds to.

- Devin sees only what a drone could sense right now: pose, velocity, clearance, time
  remaining, per waypoint evidence status and gap reasons, the allowed primitives and the
  current safety limits.
- Devin never sees the seeded scenario, the future gust or the verifier's answer.
- Primitives are `inspect_waypoints`, `quiet_hover`, `return_home`, `complete`, `abort`.
- If Devin is unreachable the mission cannot report PASS. It holds, then returns home.
- The deterministic rule planner still exists, but only as a labelled baseline. It is not
  the demo.

> This is the second half of the evolution answer, and it is the one the judges asked
> about. The honest reason we made the move: an engineering loop that ends at a merged
> pull request is a very good software demo, but the industry problem is a mission, not a
> file. Once the mission itself is an observation and action protocol, the same agent can
> run it.

---

## Slide 6: Architecture, two control rates

```text
seeded hidden scenario (wind, gusts)
        |
        v
 simulator v2 + camera gate  ->  observation packet (only what the drone senses)
        |
        v
 Devin mission session  ->  structured JSON action + written reason
        |
        v
 safety envelope  ->  accept, or reject and tell Devin why
        |
        v
 controller2.py at 50 Hz  ->  quadrotor dynamics
        |
        v
 outcome observation ------> back to Devin
        |
        v
 independent verifier  ->  PASS or INSUFFICIENT_EVIDENCE
        |
        v
 human final approval
```

**Mission rate.** Devin chooses which waypoints to approach, whether to hover and settle,
whether to retry, and when to stop. Seconds per decision.

**Flight rate.** `controller2.py` runs at 50 Hz to stabilise the vehicle and execute the
latest accepted action inside speed, clearance and geofence limits. It is an actuator, not
a planner. In Devin controlled mode local code never picks the next inspection target.

> One sentence to land: the fast loop keeps the aircraft safe, the slow loop decides what
> the mission does, and only the slow loop is intelligent. That separation is also why
> Milestone 5 is a swap and not a rewrite.

---

## Slide 7: Safety envelope and the four human authorities

The envelope in `mission/safety.py` checks every proposed action before it flies:

- stale observation IDs and duplicate action IDs are rejected
- unknown primitives are rejected
- waypoints outside the authorised sector are rejected
- at most 8 targets per action, at most 3 attempts per waypoint
- at most 40 s per action, commanded speed capped at the vehicle limit
- an action with no mission time remaining is rejected

The rule that matters: **a rejection is reported back to Devin with its reason. The
backend never substitutes a target of its own.** Rejections shape Devin's next choice
rather than being quietly patched over.

Humans keep exactly four authorities:

1. **Mission authorisation.** Approve the asset, procedure and operating envelope.
2. **Identity confirmation.** Required when an ambiguous asset changes which approved
   procedure applies.
3. **Safety intervention.** Pause, return home, land, emergency stop, at any time.
4. **Final disposition.** Review the evidence package and approve or reject the result.

Between trigger and artifact, no human chooses a waypoint or repairs an action.

> Pre-empt the obvious question. Yes there is a human, and the human is deliberately
> outside the loop being judged: authorisation before, intervention beside, approval
> after. Also note we publish the envelope limits inside every observation, so a rejection
> means Devin used bad judgement rather than that Devin was missing information. That fix
> came out of a real failed turn in a live run.

---

## Slide 8: Devin found and fixed a bug in its own controller

During the build, `controller2.py` crashed with a `ZeroDivisionError` whenever the mission
agent handed it fewer than three targets. The controller had been written for the full
24 waypoint, three ring nacelle and had that structure baked in. The mission layer
legitimately asks for small subsets, so the assumption was wrong the moment Devin became
the mission agent.

What happened next:

- a separate Devin session received the failure and diagnosed it
- it rewrote the retry sweep to derive the ring structure from the waypoints actually
  given, rather than assuming three rings of eight
- it proved the new routing is identical to the old routing over **2000 random cases** on
  the full nacelle, so the v2 batch result was not quietly changed
- the autonomous loop went from **27/30 to 29/30**

No human touched `controller2.py`. The project rule is that a human edit to the controller
makes the submission dishonest, and it held.

> This is the write, run, test, fix loop doing exactly what the brief describes, except
> the bug was in code the same system had written and the trigger was a runtime mission
> failure rather than a unit test. Mention the 2000 case equivalence proof. An agent that
> fixes a bug is normal now. An agent that proves it did not break the passing case is the
> part worth a slide.

---

## Slide 9: The live mission, Devin reading its own telemetry

One live mission over the real Devin v3 API, seed 1000, the whole 24 waypoint nacelle.

1. Devin batched **8 waypoints** in one `inspect_waypoints` action, the maximum the
   envelope allows.
2. It then read its own telemetry: body rate above the steadiness limit, clearance
   **0.81 m**, still descending. Instead of pushing on it chose to **hover and settle**.
3. It read the remaining gap reasons and saw they were all `too_far`, not
   `shot_not_steady`. It concluded that distance, not steadiness, was the binding
   constraint, and adjusted accordingly.

Result: **PASS, 24/24 waypoints, coverage 100.0%, 82.3 s, 6 actions accepted, 1 rejected
by the safety envelope.**

> This is the slide to slow down on. Nobody wrote a rule that says "if body rate is high,
> hover". Devin was handed telemetry and gap reasons and worked out which constraint was
> actually binding, which is the difference between a planner executing a script and an
> agent running a mission. Point at the rejected action too, because it shows the envelope
> is live rather than decorative.

---

## Slide 10: Results, including the one that fails

| Configuration | Result | Coverage | Notes |
| --- | --- | --- | --- |
| Sim v1 + `controller.py` | 30/30 PASS | 100.0% mean | 0 collisions |
| Sim v2 + `controller2.py` | 29/30 PASS | 99.9% mean | 719/720 waypoints inspected |
| Autonomous loop, baseline agent, seeds 1000-1029 | 29/30 PASS | 98.6% mean | labelled comparison baseline |
| Live Devin mission, v3 API, seed 1000 | PASS | 100.0% | 24/24 waypoints, 82.3 s, 6 accepted, 1 rejected |

**101 automated tests.**

**Seed 1027 fails.** It fails in the batch verifier and it fails in the autonomous loop.
It is a time budget problem on one hard waypoint: the run spends too long satisfying the
camera gate at a single point and runs out of budget before the sweep closes. We have not
fixed it and we are not hiding it.

> Say the failure out loud, in the same tone as the passes. Then say what we know about
> it: the same waypoint, the same cause, in two independent code paths, which means it is
> a real property of the task rather than a flake. If a judge asks how we would fix it,
> the answer is a time aware target ordering at the mission layer, which is a Devin task,
> not a human one.

---

## Slide 11: Live demo

Two commands, both from the repository root.

```bash
# deterministic baseline, no credentials, no credits spent
python scripts/run_autonomous_mission.py --seed <judge seed> --planner baseline

# the real thing: one live Devin session flies the mission
export DEVIN_API_KEY=... DEVIN_ORG_ID=...
python scripts/run_autonomous_mission.py --seed <judge seed>
```

The browser view is `viz/mission_view.html`, served by `python -m viz.server`. It replays
the mission with measured attitude on the real scanned turbofan model, and puts Devin's
own words on screen for every step: the observation, the action chosen, the written
reason, the safety envelope's accept or reject, and which waypoints that action actually
captured. The Devin session URL is linked, so a judge can open the session and read the
reasoning first hand.

The graded keep-out volume is drawn as a wireframe cylinder next to the pretty engine
model, because that cylinder is the geometry the verifier actually checks.

> Ask the judge for a seed. If wifi or credits are a problem, run the baseline planner
> live on their seed and show the recorded live Devin mission next to it, clearly labelled
> as a recording. Do not claim a live run you did not just do. The session URL is the
> strongest single artifact in the demo, so leave time to open it.

---

## Slide 12: What is real and what is simulated

Read this slide carefully, because we would rather you trust the rest of the deck.

- **Everything runs in simulation. No drone has flown.** There is no hardware, no camera,
  no flight test.
- **The system verifies inspection coverage. It does not detect defects.** It proves a
  controller can reach every required point, aimed and steady, without collision, under
  seeded wind.
- **The defect research and the 3D turbofan model are context, not a claim.** The report
  is a collaborator's work with real NTSB and Aviation Safety Network citations, and it
  exists to explain why coverage matters. The engine and drone models in the viewer are
  decoration, labelled as such, sitting beside the wireframe volume the verifier actually
  uses.
- **The Devin API integration has had a handful of live runs, not sustained production
  use.** The headline live mission is one run on seed 1000. The 30 seed sweeps are the
  labelled baseline agent, not 30 live API missions.
- **The simulator omits real effects on purpose:** no battery model, no wind torque, no
  sensor noise, no obstacle other than the nacelle, no moving people or birds yet.

What we do claim: an AI engineer wrote and fixed the flight software with no human edits,
and the same system chose every mission action against an independent verifier it could
not see.

> Do this slide slowly and without apology. Every strong claim in this deck survives it,
> and a judge who has heard six pitches today will notice that we volunteered the limits
> before being asked. If someone pushes, the honest gap between here and a real flight is
> Milestone 5 on the next slide.

---

## Slide 13: Commercial model

Customers pay for reduced aircraft downtime, fewer repetitive technician hours and a
traceable inspection record. They do not pay for the presence of an AI model.

Pricing to validate through paid pilots, illustrative:

| Offer | Illustrative price assumption |
| --- | ---: |
| Controlled paid pilot at one component or site | $50,000 to $100,000 |
| Initial deployment and workflow integration | $75,000 to $250,000 |
| Annual site software and support licence | $150,000 to $300,000 |
| Usage option | $250 to $1,500 per completed inspection |

Illustrative revenue scenarios, not forecasts:

| Stage | Assumption | Annual revenue |
| --- | --- | ---: |
| Paid validation | 3 to 5 pilots | $150,000 to $500,000 |
| Early product | 20 sites at $150k to $250k | $3m to $5m |
| Established vendor | 100 sites at $200k to $300k | $20m to $30m |
| Category leader | 300 sites at $250k to $400k | $75m to $120m |

Market evidence supports the problem, it does not prove our revenue. Oliver Wyman puts
global MRO demand at $136 billion in 2025, approaching $193 billion by 2030. Donecle
advertises inspections up to ten times faster and component scans measured in minutes.
Mainblades reports a 75% reduction in lightning strike inspection time. Donecle's
10 million euro 2026 round is evidence of investor interest, not disclosed revenue.

Sources: oliverwyman.com Global Fleet and MRO Market Forecast 2026-2036, donecle.com,
donecle.com/components, mainblades.com, Donecle press release April 2026.

> Be explicit that the price table is an assumption to be tested, not a quote and not a
> competitor's published price. The market numbers are cited and the revenue numbers are
> labelled illustrative, and saying that difference out loud costs nothing.

---

## Slide 14: What comes next

**Milestone 5 in the roadmap: replace the simulator, keep everything above it.**

- Swap `controller2.py` for a real autopilot behind a MAVLink primitive adapter.
- Swap synthetic evidence for camera, microphone and telemetry adapters, preserving the
  observation schema.
- The mission layer, the safety envelope, the observation and action contract and the
  independent verifier stay unchanged. That is the point of the two rate architecture: the
  thing being replaced is the actuator, not the intelligence.
- First tests in a cage, on a stationary representative component.
- A hardware emergency stop that is independent of Devin and of the backend.

Before that: hidden seeded obstacles and audio events, the human pause and abort controls
in the flight view, and a hashed replayable mission package per run.

**The closing line.** Cognition's named customers already include GE Aerospace, NASA, the
US Army and the US Navy. This is the industry Cognition is already in. We built the layer
that puts Devin inside the mission loop, and we can tell you exactly which parts are real.

> Land Milestone 5 as a swap, not a rebuild, because that is what makes the simulation
> defensible rather than a hedge. Then stop. Do not add a new claim in the last thirty
> seconds.

---

# Spoken scripts

## 60 second script

AeroLoop is Devin for autonomous physical inspection.

Aircraft inspection has a real problem: a manual walk around covers about 78% of the
surface, autonomous drone inspection covers 99.1%, and a panel that was never covered is
not clean, it is unseen. That is a $136 billion MRO market today.

We started by having Devin write the flight controller for a nacelle inspection drone,
against a verifier that existed before it wrote a line. Thirty out of thirty, 100%
coverage, no collisions. Then we made the task harder: a real quadrotor and a camera gate
where a waypoint counts only if the drone is within half a metre, aimed within sixty
degrees, and steady. Devin passed that too, 29 out of 30.

Then the actual move. Devin stopped being the engineer and became the mission agent. It
receives observations and chooses every action, one at a time, through one API session,
inside a safety envelope that reports rejections back to it instead of overriding it.

Live mission, seed 1000: pass, 24 of 24 waypoints, 100% coverage, 82 seconds. Mid mission
it read its own telemetry, saw it was unsteady and still descending, and chose to hover
and settle before continuing.

Everything is simulated and no drone has flown. Every number I just gave you is measured.

## 3 minute script

**The problem, 30 seconds.** An aircraft on the ground earns nothing, and the inspection
keeping it there is a person walking around it with a torch. Manual walk around coverage
averages 78%. Autonomous drone inspection reaches 99.1%. The miss rate on manual is around
15%. And the failure mode is not a bad reading, it is no reading: a nacelle panel that was
never covered at the right distance and angle is not clean, it is unseen. That is where
things like the Southwest 1380 fan blade crack and forty five A320 fan cowl door losses
live. Global MRO demand was $136 billion in 2025, heading for $193 billion by 2030.

**Why this domain, 20 seconds.** The brief asked for an industry with a real feedback
loop. Flight software has one already. The industry validates controllers in simulation
for weeks before first flight, because crashing hardware is expensive. So the verdict
already exists, it is already trusted, and it is already code. We did not invent a checker.

**What we built, and how it changed, 60 seconds.** First, Devin wrote the flight
controller against an adversarial verifier that predates it. Point mass drone, seeded
winds, 24 waypoints. Thirty out of thirty, 100% coverage, zero collisions, no human edits.

Then we raised our own bar, because a point mass hides the hard part: a quadrotor tilts to
translate, and tilting moves the camera. Simulator v2 is a rate controlled quadrotor with
a camera gate. A waypoint counts only when the drone is within 0.5 metres, aimed within 60
degrees of the surface, and steady at 1.5 radians per second and 2.5 metres per second.
Devin wrote controller2.py for that. 29 out of 30, 99.9% coverage.

Then the real change. Devin stopped being only the engineer and became the runtime mission
agent. It gets an observation packet with only what a drone could sense, and it chooses
one bounded action, over one resumable session, for the whole mission. A safety envelope
checks every action and, when it rejects one, tells Devin why instead of substituting a
choice of its own. Humans keep four authorities: authorise the mission, confirm identity,
intervene for safety, approve the result. Nothing else.

**The two moments that matter, 45 seconds.** During the build, controller2 crashed with a
divide by zero whenever the mission agent handed it fewer than three waypoints, because it
had the full 24 waypoint nacelle baked into it. A separate Devin session diagnosed it,
derived the ring structure from the waypoints actually given, proved the routing was
identical over 2000 random cases on the full nacelle, and lifted the autonomous loop from
27 out of 30 to 29 out of 30. No human touched that file.

And in the live mission over the real API, seed 1000: Devin batched eight waypoints, then
read its own telemetry, body rate over the steadiness limit, clearance 0.81 metres, still
descending, and chose to hover and settle rather than push on. Then it read the remaining
gap reasons, saw they were all "too far" rather than "shot not steady", concluded distance
and not steadiness was binding, and adjusted. Pass, 24 of 24, 100% coverage, 82.3 seconds,
six actions accepted, one rejected by the envelope.

**Results and the failure, 20 seconds.** 30 out of 30 on v1. 29 out of 30 on v2. 29 out of
30 on the autonomous loop across seeds 1000 to 1029, 98.6% mean coverage. 101 automated
tests. Seed 1027 fails, in both the batch verifier and the autonomous loop, a time budget
problem on one hard waypoint. Same cause in two independent paths, so it is a property of
the task, and we have not fixed it.

**Honesty, 15 seconds.** Everything is simulated, no drone has flown. The system verifies
inspection coverage, it does not detect defects. The defect research and the turbofan
model are cited context, not a detection claim. The Devin API integration has had a
handful of live runs, not sustained production use.

**Next, 10 seconds.** Milestone 5 swaps controller2.py for a real autopilot over MAVLink.
The mission layer, the safety envelope and the verifier do not change, because the thing
being replaced is the actuator, not the intelligence. This is the industry Cognition is
already in. We built the layer that puts Devin inside the mission loop.
