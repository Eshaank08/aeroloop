# GOAL

## What we are entering

Cognition's track at EHL Munich: **"Find an Industry, Give it an Engineer."**

Deadline: **23 August 2026, 12:01 PM CET.**

## The brief, in Cognition's words

Software improves fast because it has a loop: write, run, test, fix. That loop is why
Devin can work unsupervised. Every attempt gets a verdict, and a wrong answer announces
itself. Most industries have the same engineering problems and no such loop.

The task: find an industry that does have the loop, and build the layer that puts Devin
inside it. Pick a domain where the output can be expressed as code. Then build a system
that triggers Devin sessions programmatically, gives them a way to check their own work,
and produces real artifacts with nobody sitting in the middle.

Three failure modes they explicitly call out:

- Pick a domain with no way to check the work, and Devin is only guessing.
- Leave a human in the loop, and you have built a copilot, not a layer.
- Wire it to one prepared example, and you have built a demo.

## How we are judged

**What you built**

| Criterion    | What it means                                            |
| ------------ | -------------------------------------------------------- |
| Autonomy     | Trigger to artifact, nobody touching it in between        |
| Verification | The system knows a good result from a bad one on its own  |
| Artifacts    | Output someone in that industry could actually use        |

**How you pitch it**

| Criterion | What it means                                        |
| --------- | ---------------------------------------------------- |
| Clarity   | If they cannot follow it, they cannot credit it       |
| Problem   | Which industry, who is stuck, why it has a loop       |
| Approach  | The strategy going in, and how it changed while building |
| Solution  | What you ended up with, and the logic behind it       |

## How this project answers each one

**Autonomy.** One command creates a Devin session. Devin writes the flight controller,
runs the verifier, reads the failure, fixes it, and reruns. No retry logic written by us,
no prompt babysitting, no human approving intermediate steps. The only human touch is a
safety gate that fires *after* the verifier already said PASS.

**Verification.** A physics simulator that scores three hard metrics: waypoint coverage,
collision count, completion time. Randomized wind means a controller cannot pass by
memorizing one scenario. Zero collisions is an absolute constraint. The verifier is
adversarial and external to the thing being graded, and it existed before Devin wrote a
line.

**Artifacts.** A working, tested flight controller plus a verification report showing
coverage percentage, collisions, and timing across every scenario. That report is the
artifact a real MRO inspection engineer signs off against.

**Not a prepared example.** The live demo runs a fresh judge-supplied random seed that
was never used during development.

## Success criteria for us, in order

1. A live Devin session, triggered by script, produces a passing `controller.py` on an
   unseen seed. Nothing else matters if this does not work.
2. The verifier report is legible in under ten seconds on a projector.
3. The pitch lands the industry evidence (Airbus wrote drone inspection into the A320
   maintenance manual, Boeing into the 737's) in the first thirty seconds.
4. The approval gate reads as obviously correct engineering, not as a hedge.
