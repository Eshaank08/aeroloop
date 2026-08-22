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
