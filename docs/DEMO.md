# DEMO

A 90 second live demo of AeroLoop, in four steps. Every step has a fallback that needs
no network, because conference wifi fails.

The rule for this runbook: nothing on screen is a slide. Everything is a command, a
report, or a browser view of a real graded run.

## Before you walk up

Do all of this while somebody else is still presenting. None of it counts against the
90 seconds.

```bash
cd aeroloop
python3 -m pip install -r requirements.txt        # pytest, numpy
python3 -m pytest -q                              # must print: 59 passed, takes about 25 s
echo "$DEVIN_API_KEY" | wc -c                     # non zero length, never print the key
echo "$DEVIN_ORG_ID"  | wc -c
```

Also do this, so the fallbacks exist:

1. Open `viz/flight_view.html` in a second browser tab and leave it loaded. The view
   vendors Three.js under `viz/vendor/` and reads `viz/data/data.js` off the filesystem,
   so once the tab is open it needs no network at all.
2. Save a screenshot or a scrollback copy of a **previous** live Devin session: the
   session URL, the created session id, and the pull request it opened. That is the
   fallback for step 1, and it is the only step where a dead network actually costs you
   something.
3. Have one terminal, font large, in the repo root. Two tabs: tab A for commands,
   tab B already holding the report from a prerecorded full run.

To produce the tab B fallback report ahead of time:

```bash
python3 -m sim.run_verifier --scenarios 30 --verbose > /tmp/aeroloop_report.txt
```

Terminal setup matters more than it sounds. The verifier report is 35 lines and the
judges have to read the last five from across a room.

## Timing

| Step | What                                   | Wall clock | Runs any network? |
| ---- | -------------------------------------- | ---------- | ----------------- |
| 0    | One sentence of framing                | 10 s       | no                |
| 1    | Trigger a live Devin session           | 20 s       | yes, Devin API    |
| 2    | Verifier report                        | 25 s       | no                |
| 3    | Flight view                            | 25 s       | no                |
| 4    | Human safety gate                      | 10 s       | no                |

Total 90 s. Steps 2, 3 and 4 are entirely offline, so the worst case for a dead network
is that step 1 becomes a screenshot and you gain time rather than lose it.

---

## Step 0. Framing, 10 seconds, nothing on screen but the terminal

Say:

> Aircraft engine inspection has a loop: fly the sweep, score coverage, count collisions,
> check the clock. So we put Devin inside it. Devin writes the flight controller, the
> simulator grades it, and no human touches the controller at any point.

Audience is looking at: a clean terminal in the repo root.

---

## Step 1. Trigger a live Devin session, 20 seconds

Command, tab A:

```bash
python3 scripts/trigger_devin.py --repo https://github.com/Eshaank08/aeroloop.git --no-wait
```

Expected wall clock: about 2 to 5 seconds to return, then you talk over the result. The
script prints the created session id and its URL, then exits because of `--no-wait`.
Without `--no-wait` it polls every 30 seconds and would eat the whole demo, so always
pass it live.

What to say while it runs:

> That is one API call. The prompt is this repo's README, which is the task spec, and
> nothing else. Nobody is in that session. It writes controller.py, runs the verifier,
> reads the failure report, fixes the controller, and reruns until it passes, then opens
> a pull request.

Audience is looking at: the two printed lines, session id and session URL. If you have a
projector tab to spare, open the session URL and let it sit there while you move on. Do
not read the session live, you do not have 20 minutes.

Point at the merged pull request as the proof this already happened once:
`https://github.com/Eshaank08/aeroloop/pull/4`, the flight controller now on master,
committed by the Devin bot account and not by a human.

**Fallback if the network or the Devin API is down:** show the saved screenshot of the
previous live session, the one with the session id, the session URL, and pull request #4.
Say plainly that the network is down, that this is a recording of the same command, and
that the artifact it produced is the `controller.py` in the repo you are about to run.
Then verify the claim offline, which is something a screenshot cannot fake:

```bash
git log -1 --format='%an %s' -- controller.py
```

That prints the Devin bot as the author of the controller commit. The autonomy claim
survives with no network.

---

## Step 2. The verifier report, 25 seconds

Command, tab A:

```bash
python3 -m sim.run_verifier --scenarios 30 --verbose
```

Expected wall clock: under 1 second on a laptop. Measured on the demo machine it was
`real 0m0.693s`, so treat it as instant and spend the 25 seconds talking, not waiting.

What to say while it runs:

> Thirty randomized wind scenarios. Every one needs 95 percent waypoint coverage, zero
> collisions, and completion inside the 120 second budget, and the batch needs 90 percent
> of scenarios to pass. Zero collisions is absolute. Cover everything and clip the nacelle
> once and that scenario is a fail, not a near miss.

Audience is looking at: the last five lines of the report, the summary block. That is
where `scenarios passed`, `mean coverage`, `total collisions`, the thresholds and the
final `RESULT: PASS` live. Scroll so those lines are on screen. The per seed lines above
are texture, the summary is the claim.

Then prove it is not memorization, with a seed nobody has trained on:

```bash
python3 -m sim.run_verifier --scenarios 50 --seed 424242 --verbose
```

Expected wall clock: under two seconds, measured `real 0m1.700s`.

> Different base seed, fifty scenarios, never used during development. Same result.

If a judge offers a number, type their number in place of `424242` and run it live. That
is the whole point of the seed argument. Do not promise a specific outcome for a seed you
have not run.

The verified numbers to quote, all with the exact commands that produced them, are in
`docs/RESULTS.md`. Quote from there and nowhere else.

**Fallback if anything goes wrong here:** this step needs no network at all, it is local
Python and numpy. The only realistic failure is a broken interpreter or a missing
dependency on a borrowed laptop. In that case switch to terminal tab B and page through
the prerecorded `/tmp/aeroloop_report.txt` from the same command, and say it is a saved
run of the command on screen.

---

## Step 3. The flight view, 25 seconds

Command, or just switch to the tab you already opened:

```bash
open viz/flight_view.html          # macOS
xdg-open viz/flight_view.html      # Linux
```

Expected wall clock: 1 to 2 seconds to render. No server, no build step, no network.

What to say while it renders:

> This is the same controller, the same nacelle, the same wind, replayed. It is read only,
> it cannot change a pass into a fail. Left panel is the flight: coverage, elapsed against
> the budget, clearance to the keep out shell. Right panel is the whole batch, one cell
> per scenario.

Audience is looking at: the drone working its way around the nacelle while the coverage
counter climbs, and the clearance number staying positive. Then click **jump to gust**.
The committed trace is seed 606076, a 39.82 s sweep at 100 percent coverage and zero
collisions, whose gust starts at 21.5 s and peaks at 4.27, so the disturbance lands while
the drone is still working the nacelle. Check those numbers before the demo with the one
liner in the fallback below, because rerecording the trace changes them.

The view also has `orbit`, `follow` and `pilot view` cameras. Pick one before you walk up
and leave it there. Do not fiddle with cameras on stage.

> That is the wind hitting mid sweep. Watch the clearance number. It does not go to zero.

Then sweep a hand across the right panel: every cell green is the batch you just ran in
step 2.

**Fallback if the browser will not cooperate:** the view is already offline, so a dead
network cannot break it. If the graphics stack refuses, the data behind the view is plain
JSON and readable in the terminal:

```bash
python3 -c "import json; d=json.load(open('viz/data/trace.json')); print(d['seed'], d['coverage'], d['collisions'], d['elapsed_s'], d['gust'])"
```

That prints the traced seed, its coverage, its collision count, its elapsed time and the
gust profile. Say you are reading the recorded flight straight out of the trace file, and
move on. Do not spend demo time debugging a browser.

Never run `python3 -m viz.replay` during the demo. It rewrites `viz/data/`, and the
committed trace is the one this runbook and the talk track describe.

The flight command console, typed or spoken missions, is a different thing: it needs
`python3 -m viz.server` running and the page opened from `http://127.0.0.1:8765/flight_view.html`
rather than off the filesystem. It is local only, so no conference wifi is involved, but
it is a live flight rather than the graded one and the controller was verified for the
full sweep only. Keep it out of the 90 seconds and save it for questions.

---

## Step 4. The human safety gate, 10 seconds

Command, tab A:

```bash
python3 scripts/approve.py
```

Expected wall clock: about 1 second to rerun the verifier and write the artifact, then it
blocks on input and waits for you.

What to say while it prints:

> One human touch in this entire pipeline, and it is here, after the verifier already
> said PASS. It is not an engineering review. It is a person accepting that a drone is
> about to fly next to a real jet engine.

Type `yes` and press enter. It prints that the controller is released for flight
operations. Anything other than the exact string `yes` holds the controller instead. If
verification had failed, the script refuses to ask at all and exits non zero.

Audience is looking at: the artifact summary, then the prompt line, then the release
line. The summary is worth one sentence, because it is what makes the approval mean
something:

> It is not signing a screenshot. It is signing an artifact under `reports/` that pins
> the controller hash, the git commit, whether the tree was dirty, and every scenario
> result. Change one byte of the controller and the digest no longer matches.

Close on:

> Trigger to artifact, nobody in the middle. The only human decision is the physical
> safety one.

**Fallback:** none needed, this step is local and offline. If the terminal is wedged,
read the gate out of `docs/RESULTS.md`, which has the pasted output of the same script
and the head of the artifact it wrote. `python3 scripts/approve.py --dry-run` writes the
artifact and skips the prompt, which is the safer thing to run if you are rehearsing and
do not want to record an approval.

---

## What is not in this demo, and say so if asked

- **Simulator v2**, the rate controlled quadrotor with a camera gate on coverage, is on
  master in `sim2/` and its controller was written by a Devin session in PR #17, but the
  90 second script above shows v1 only, because a v2 batch takes about 26 s of wall clock
  on its own. If asked, the honest one liner is 29 of 30 default scenarios and 20 of 20 on
  unseen base seed 424242, both `RESULT: PASS`, with the numbers in `docs/RESULTS.md`
  section 9. Never quote a v1 number as a v2 number.
- **A live Devin planned mission.** `scripts/run_devin_mission.py` exists and fails closed
  without credentials, but no mission was measured, so do not claim one ran.
- **Real hardware.** No drone flies. The artifact is verified flight software, and the
  verification report is what an inspection engineer would sign against.
- **Damage detection.** Coverage of the inspection sweep is graded, defect finding is not
  in scope.

## Failure drill, memorize this

| It broke                          | Do this                                             |
| --------------------------------- | --------------------------------------------------- |
| Devin API call fails or hangs     | Ctrl C, show the saved session screenshot, then `git log -1 --format='%an %s' -- controller.py` |
| No network at all                 | Skip the live trigger, run steps 2, 3 and 4, all offline |
| `pytest` or the verifier will not run | Terminal tab B, page the prerecorded report      |
| Asked for v2 live and there is time | `python3 -m sim2.run_verifier --scenarios 5 --verbose`, and say the full batch is in `docs/RESULTS.md` |
| Browser view will not render      | Print the trace JSON one liner from step 3           |
| Projector loses the terminal      | Steps 2 and 4 are readable out loud, the summary block is five lines |
| You are out of time               | Cut step 3, keep the verifier report and the safety gate |
