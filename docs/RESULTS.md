# RESULTS

Every number below was measured on this repository. Each table names the exact command
that produces it. Where something fails, it is written down rather than rounded away.

Scope, stated once so nothing here is over read:

- Everything is simulated. No real drone has flown.
- The system verifies inspection **coverage**, not damage. It does not detect defects.
- The Devin API paths have had a handful of live runs. They work, they are not battle
  tested.
- Seed 1027 fails, in the simulator v2 batch and in the mission loop. Details below.

## 1. Test suite

| Metric | Result |
| ------ | ------ |
| Tests | 101 passed |

```bash
python -m pytest -q
```

The suite includes both verifiers end to end plus unit coverage of the mission
contract, the safety envelope, the mission agent, evidence scoring, the signed
artifact and the approval gate.

## 2. Simulator v1, point mass, `controller.py`

| Metric | Result |
| ------ | ------ |
| Scenarios passed | 30/30 |
| Mean coverage | 100.0% |
| Collisions | 0 |

```bash
python -m sim.run_verifier --scenarios 30 --seed 1000
```

`controller.py` was written by a Devin session against the brief in `README.md`. No
human edited it.

## 3. Simulator v2, rate controlled quadrotor with a camera gate, `controller2.py`

| Metric | Result |
| ------ | ------ |
| Scenarios passed | 29/30 |
| Mean coverage | 99.9% |
| Waypoints inspected | 719/720 |
| Failing seed | 1027 only |

```bash
python -m sim2.run_verifier --scenarios 30 --seed 1000
```

Seed 1027 fails on the 150 s time budget. It does not collide and it does not fly
outside its envelope, it simply does not finish the sweep in time under that wind
draw. The batch still reports PASS overall because the threshold is a 90% scenario
pass rate, but the single failing seed is the honest number to quote.

v1 and v2 numbers are not comparable. v2 grades a quadrotor with attitude dynamics and
only counts a waypoint when the camera is aimed and the shot is steady, so its
coverage is a strictly harder measurement.

## 4. Autonomous mission loop, deterministic baseline agent

Seeds 1000 to 1029, whole nacelle, no Devin credentials used.

| Metric | Result |
| ------ | ------ |
| Missions passed | 29/30 |
| Mean coverage | 98.6% |
| Controller exceptions | 0 |
| Failing seed | 1027 only |

```bash
python scripts/run_autonomous_mission.py --seed 1000 --planner baseline
# repeated for seeds 1001 through 1029
```

The only failing seed is 1027, the same scenario the batch verifier fails, for the
same reason. That agreement matters: the runtime loop is not introducing new failure
modes on top of the controller, it is inheriting the one that already existed.

The baseline agent is a deterministic local stand in. It exists so the loop can be
tested without spending credits and so there is a labelled comparison number. It is
explicitly not the challenge demo.

## 5. Live Devin mission, simulator v2

Seed 1000, whole nacelle, real Devin v3 API, Devin choosing every action.

| Metric | Result |
| ------ | ------ |
| Disposition | PASS |
| Waypoints inspected | 24/24 |
| Coverage | 100.0% |
| Elapsed | 82.3 s of the 150 s budget |
| Actions accepted | 6 |
| Actions rejected by the safety envelope | 1 |
| Devin session | `0f34f963d5534c08a748e2d3eacc09eb` |

```bash
export DEVIN_API_KEY=cog_...
export DEVIN_ORG_ID=org_...
python scripts/run_autonomous_mission.py --seed 1000 --sector all --planner devin
```

The recorded artifact and flight trace for this mission are in `viz/data3/`, and
`viz/mission_view.html` auto loads them.

### What Devin did unprompted

None of the following was scripted, prompted per step, or corrected by a human. It is
the sequence of actions in the recorded artifact.

1. **Batched aggressively while conditions were good.** First action inspected
   waypoints 0 to 7, the maximum eight targets allowed in one action, with the speed
   cap set below the steadiness limit. Its stated reason was that wind was calm and
   clearance was good, so bank evidence early.
2. **Read its own telemetry and chose to slow down.** After that batch it noticed body
   rate above the 1.5 rad/s steadiness limit, clearance down to 0.81 m, and the vehicle
   still descending at 1.14 m/s. It chose to hover and settle rather than push on.
3. **Was rejected, and fixed its own action.** That hover named no waypoint, so the
   safety envelope rejected it with `quiet_hover needs at least one waypoint index`.
   The envelope did not choose a replacement. Devin re-issued the hover correctly
   scoped to the next batch.
4. **Diagnosed the actual binding constraint from the evidence gaps.** It then read the
   per waypoint gap reasons, saw they were all `too_far` rather than `shot_not_steady`,
   concluded that distance and not steadiness was what was blocking coverage, and
   adjusted its approach accordingly.
5. **Finished, returned, then claimed.** It inspected the remaining waypoints, issued
   `return_home`, and only then claimed complete. The claim did not decide anything.
   The verifier ran afterwards and independently returned PASS.

Step 4 is the part worth dwelling on. Nothing in the brief tells the agent how to
interpret gap reasons. It inferred the constraint from evidence it was given and
changed strategy because of it.

## 6. An earlier live run that failed closed correctly

An earlier live mission did not pass, and it failed in the right direction.

| What happened | What the system did |
| ------------- | ------------------- |
| Devin proposed a 55 s action against the 40 s bound on a single action | Rejected by the safety envelope, reported back to Devin |
| The client wrongly treated an idle Devin session as a dead one | The mission performed a bounded safe stop and reported `INSUFFICIENT_EVIDENCE` |

It did not report PASS. That is the behaviour that matters: when the authority deciding
what to inspect stops answering, the mission cannot be called complete no matter how
much evidence happens to already exist.

Both underlying bugs are fixed. The agent is now told the hard limits in a `limits`
block on every observation, so the 40 s bound is visible before it chooses. And an idle
session is no longer read as a dead one.

## 7. Devin fixed a bug in its own controller

This is the strongest single piece of evidence in the project, because it closes the
loop twice: an agent wrote the flight software, and then an agent debugged the flight
software when the runtime loop exposed a defect in it.

**The defect.** `controller2.py` assumed it always received the full 24 waypoint, three
ring nacelle. When the mission agent handed it fewer than three targets, `per_ring`
computed to 0 and `divmod` raised `ZeroDivisionError`. The batch verifier never hit
this, because the batch verifier always passes the full nacelle. Only the runtime loop,
where the agent chooses partial waypoint sets, could trigger it.

**The fix.** A separate Devin session diagnosed the defect and fixed it in PR #21, now
merged. It derived the ring grid from the waypoints actually supplied rather than
assuming the full set, and verified that routes were identical over 2000 random cases
on the full nacelle, so the fix changed nothing about the already measured batch
behaviour.

**The effect.** The autonomous mission loop went from 27/30 to 29/30.

**The human contribution.** None. No human edited `controller2.py` at any point, before
or after this fix.

## 8. What is not measured, and must not be claimed

- No real hardware flight. Every number here comes from simulation.
- No defect detection. Coverage of the inspection sweep is what is graded.
- No long running or high volume Devin API testing. A handful of live missions have
  run end to end.
- No claim that seed 1027 is solved. It is not. It misses the time budget.
