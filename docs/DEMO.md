# DEMO

A live judge demo of AeroLoop, minute by minute. Nothing on screen is a slide.
Everything is a command, a report, or a browser view of a real graded run.

Total: about six minutes with questions, or four minutes if you cut the engineering
loop section. Every step that touches the network has a fallback that does not.

## Pre-demo checklist

Do all of this before you walk up. None of it counts against your time.

```bash
cd aeroloop
python -m pip install -r requirements.txt
python -m pytest -q                      # must print: 151 passed
echo -n "$DEVIN_API_KEY" | wc -c         # non zero, never print the key itself
echo -n "$DEVIN_ORG_ID"  | wc -c
```

Then:

1. Export the credentials **in the shell you start the server from**, then start it and
   leave it running:

   ```bash
   export DEVIN_API_KEY=cog_...
   export DEVIN_ORG_ID=org-...
   export AEROLOOP_DEVIN_MAX_ACU=20        # cost ceiling per mission
   python -m viz.server
   ```

   The server reads the credentials from its own environment. If you start it without
   them, live missions return `DEVIN_API_KEY and DEVIN_ORG_ID are required for Devin
   mode` and refuse to run. That is the fail-closed guard doing its job, but it is an
   embarrassing way to discover it on stage, so check it before you walk up.
2. Open `http://127.0.0.1:8765/mission_view.html` in a tab and leave it loaded. It auto
   loads the last recorded Devin mission from `viz/data3/`, so the view is never empty
   even with no network at all. Confirm you can see the drone, the engine, and the
   Devin decisions panel on the right.
3. Pre-warm the fallback report so you never wait on a cold run:
   `python -m sim2.run_verifier --scenarios 30 --seed 1000 > /tmp/aeroloop_v2.txt`.
4. Have the PR #21 page open in a spare tab. That is the self-fixed controller bug and
   it is your strongest single exhibit.
5. Two terminal tabs, large font, repo root. Tab A for live commands, tab B holding the
   pre-warmed report.
6. Decide up front whether you are running a live Devin mission. If wifi is shaky,
   plan to show the recorded one and say so plainly. A recorded run described honestly
   beats a live run that hangs.

## The one thing to get right

Do not narrate scripts. Hand the keyboard over, or type what a judge asks you to type,
into the box at the bottom of the mission view. It takes plain English:

- `inspect the lower end of the engine on a random scene`
- `check the inlet, seed 1027`
- `take the drone from one corner to the other and inspect everything`
- `look at the port side`

The HUD shows what the sentence authorised before anything flies: the region, the
waypoint count, and the seed, marked random when the system picked it. Say that out
loud, because it is the point. The operator's words set the boundary, and Devin chooses
every action inside it. If a judge invents a sentence you have never tried, run it. An
unparsed sentence authorises the whole nacelle rather than nothing, so the worst case is
a full sweep, not a broken demo.

Ask a judge for a number when you want an unseen scene. Seeds 1000 to 1029 and 5000 to
5029 are the ones in the results tables, so a judge's own number is genuinely unrehearsed.

## Timing

| Minute | What | Needs network? |
| ------ | ---- | -------------- |
| 0:00 to 0:45 | Framing, the industry and the loop | no |
| 0:45 to 1:45 | Loop one: Devin writes the controller, verifiers prove it | no |
| 1:45 to 3:30 | Loop two: Devin flies the mission, live or recorded | yes if live |
| 3:30 to 4:30 | The browser mission view, Devin's reasoning on screen | no |
| 4:30 to 5:15 | The self-fixed controller bug, PR #21 | tab already open |
| 5:15 to 6:00 | The human safety gate and the close | no |

---

## 0:00 to 0:45. Framing

Nothing on screen but a clean terminal.

Say:

> Aircraft engine inspection by drone is already approved and already running. Airbus
> wrote it into the A320-family maintenance manual, Boeing into the 737 manual, and
> airlines like KLM and AAR run it today. Airbus's own number: an inspection that took up
> to a day now takes about three hours. So the industry question is settled. Ours is
> sharper: can an
> AI engineer build, verify and then actually fly that software on its own?
>
> Two loops. Devin writes the flight controller and a hidden adversarial verifier grades
> it. Then, in the second simulator, Devin is the mission agent at runtime, choosing
> every action while a safety envelope bounds it. Everything you are about to see is
> simulated, and what we verify is inspection coverage, not damage detection.

Say the simulated part out loud, early. Judges trust the rest more once you have named
the limit yourself.

---

## 0:45 to 1:45. Loop one: written and verified by Devin

Tab A:

```bash
python -m sim.run_verifier --scenarios 30 --seed 1000
```

Runs in about a second. Point at the summary block.

> Thirty randomized wind scenarios. Simulator one, point mass. Thirty of thirty pass,
> 100 percent mean coverage, zero collisions. Zero collisions is absolute: cover every
> waypoint and clip the nacelle once and that scenario is a fail, not a near miss.

Then the harder one:

```bash
python -m sim2.run_verifier --scenarios 30 --seed 1000
```

> Simulator two is a rate controlled quadrotor, and coverage only counts through a
> camera gate: within half a metre, aimed within 60 degrees of the surface, and steady.
> Thirty of thirty pass, 99.9 percent mean coverage, 719 of 720 waypoints. Seed 1027
> is the honest edge case: 23 of 24 views, 95.8 percent coverage at exactly 150 seconds,
> which still clears the unchanged 95 percent threshold. We show the missing view rather
> than rounding the batch to 100 percent.

If a judge offers a base seed, run it live with `--seed <their number>`. Do not promise
an outcome for a seed you have not run.

**If Python breaks on a borrowed laptop:** switch to tab B and page the pre-warmed
`/tmp/aeroloop_v2.txt`, and say it is a saved run of the command on screen.

---

## 1:45 to 3:30. Loop two: Devin flies the mission

This is the part that is new and the part to spend time on.

Say first, before running anything:

> In simulator two the Devin API is the mission agent. Each turn it gets one observation
> containing only what a drone could sense: pose, clearance, a wind estimate recovered
> from the vehicle's own motion, which waypoints still have evidence gaps and why,
> remaining budget, and the hard limits. It returns one bounded action. A safety
> envelope can reject that action and tells Devin why, but it never picks a different
> waypoint on Devin's behalf. And Devin saying it is finished decides nothing, the
> verifier runs afterwards.

Then, if the network is good:

```bash
python scripts/run_autonomous_mission.py --seed 1000 --sector all --planner devin
```

While it runs, talk. Do not stand in silence waiting on the API.

> Credentials come from the environment, `DEVIN_API_KEY` and `DEVIN_ORG_ID`. If they are
> missing this refuses to run rather than silently falling back to something local.

Expected on seed 1000: PASS, 24 of 24 waypoints, 100 percent coverage, 82.3 seconds
elapsed, six actions accepted and one rejected by the envelope.

**If the call is slow, hanging, or the network dies:** Ctrl C and say plainly that you
are switching to the recorded mission. Two fallbacks, in this order.

1. The browser tab you already have open auto loads the recorded Devin mission, session
   `0f34f963d5534c08a748e2d3eacc09eb`, the exact run whose numbers you just quoted. Move
   straight to the next section and show it there. This costs you nothing.
2. If you need something running in the terminal, use the baseline agent, which needs no
   network and no credentials:

   ```bash
   python scripts/run_autonomous_mission.py --seed 1000 --planner baseline
   ```

   Label it honestly: this is a deterministic local stand in, not Devin, and it exists
   as the comparison number. Across seeds 1000 to 1029 it scores 29 of 30 with 98.6
   percent mean coverage, and the one it fails is seed 1027 again.

---

## 3:30 to 4:30. The mission view

Switch to the browser tab at `http://127.0.0.1:8765/mission_view.html`. If you ran a
live mission, press **Start mission** with the plain-English request and planner set in the
controls, or just show the recorded one.

First point to the legend: grey is a required camera view, blue is the view being
attempted and green means the simulated pose, aim and stability gate passed. It does
not mean a defect was found. Then point to the sensor panel: wind is seeded simulator
truth shown in the replay; vision and audio are explicitly synthetic test inputs. Last,
walk down the plain-language Devin decisions on the right.

> Every entry is one decision. Action one: batch the maximum eight waypoints, because
> wind is calm and clearance is good. Then it reads its own telemetry, sees body rate
> above the steadiness limit, clearance down to 0.81 metres, still descending, and it
> chooses to hover and settle instead of pushing on. Nobody told it to do that.
>
> That hover names no waypoint, so the envelope rejects it. Red entry. The envelope does
> not pick something else, it just says why. Devin re-issues the hover correctly scoped.
>
> Then the good part. It reads the remaining gap reasons, sees they all say "too far"
> rather than "shot not steady", concludes distance and not steadiness is the binding
> constraint, and changes approach. Finishes the waypoints, returns home, claims
> complete. And the claim decides nothing. The verifier says PASS independently.

**If the graphics stack will not cooperate:** read the same sequence out of the recorded
artifact in the terminal.

```bash
python -c "import json; d=json.load(open('viz/data3/mission_artifact.json')); [print(s.get('decision',{}).get('decision'), s.get('action',{}).get('primitive'), (s.get('action',{}).get('reason') or '')[:110]) for s in d['steps']]"
```

---

## 4:30 to 5:15. The bug Devin found in its own controller

Switch to the PR #21 tab.

> During this build the runtime loop broke the controller. `controller2.py` assumed it
> always got the full 24 waypoint, three ring nacelle. When the mission agent handed it
> fewer than three targets, the ring size computed to zero and it raised a
> ZeroDivisionError. The batch verifier could never find this, because the batch verifier
> always passes the full set. Only an agent choosing partial waypoint sets could trigger
> it.
>
> A separate Devin session diagnosed it, fixed it by deriving the ring grid from the
> waypoints actually supplied, and verified the routes were identical over 2000 random
> cases on the full nacelle so nothing already measured moved. That is PR #21, merged.
> The mission loop went from 27 of 30 to 29 of 30. No human edited that file, before or
> after.

If you only get one point across in the whole demo, make it this one.

---

## 5:15 to 6:00. The human gate, and the close

Tab A:

```bash
python scripts/approve.py
```

> One human touch in this pipeline, and it is here, after the verifier already said
> PASS. It is not an engineering review. It is a person accepting that a drone is about
> to fly next to a real jet engine. And it is not signing a screenshot: it signs an
> artifact under `reports/` that pins the controller hash, the git commit and every
> scenario result.

Type `yes`. Anything else holds the controller. If verification had failed the script
refuses to ask at all.

Close on:

> Trigger to artifact, and now trigger to flight, with nobody in the middle. The
> verifier decides, not the agent. And when the agent could not be reached, the mission
> came home and reported insufficient evidence rather than claiming a pass.

---

## Questions you will get, and the honest answer

| Question | Answer |
| -------- | ------ |
| Does it detect damage? | No. It verifies inspection coverage. Defect detection is out of scope. |
| Has a real drone flown this? | No. Everything is simulated, which is how the industry validates flight software before first flight. |
| Is the Devin API path reliable? | It has had a handful of live runs end to end. It works, it is not battle tested. |
| What about the failing seed? | Seed 1027 misses the 150 second budget in simulator two. It is unsolved and it is in `docs/RESULTS.md`. |
| Could the agent fly somewhere unsafe? | It can propose it. The envelope rejects out of sector waypoints, over long actions, excess speed, stale observations and replayed action ids, and tells the agent why. |
| What if Devin goes down mid mission? | Bounded return toward home, and the disposition can never be PASS. That happened in an earlier live run and is written up in `docs/RESULTS.md`. |

## Failure drill, memorize this

| It broke | Do this |
| -------- | ------- |
| Live Devin mission hangs | Ctrl C, use the recorded mission in the browser tab, say so plainly |
| No network at all | Skip the live mission, run `--planner baseline`, show the recorded mission view |
| Browser view will not render | Print the recorded artifact decisions with the one liner above |
| A verifier will not run | Tab B, page the pre-warmed report |
| `viz.server` is not running | `python -m viz.server` in a spare tab, then reload the page |
| Out of time | Cut loop one, keep the mission view and PR #21 |
