# RESULTS

Every number below came from a command run in this repository. The command is printed
above its output, and the output is pasted verbatim. Nothing here is projected,
rounded up, or copied from a slide.

## How to reproduce

```bash
git clone https://github.com/Eshaank08/aeroloop.git
cd aeroloop
python3 -m pip install -r requirements.txt
python3 -m pytest -q
python3 -m sim.run_verifier --scenarios 30 --verbose
python3 -m sim.run_verifier --scenarios 50 --seed 424242 --verbose
```

## Environment these numbers were measured on

| Item                | Value                                                |
| ------------------- | ---------------------------------------------------- |
| Commit under test   | `a4c34f4d8ae2b349e2289f332f3d346452f51e95` (master)   |
| `controller.py`     | unmodified, as merged in PR #4                        |
| Python              | 3.10.12 (`python3 --version`)                         |
| numpy               | 2.2.1                                                 |
| pytest              | 9.1.1                                                 |
| Machine             | Ubuntu Linux container, no GPU, single process        |

The repo targets Python 3.11+. These runs used the 3.10.12 interpreter that was on the
machine and the verifier ran clean on it, but 3.10 is not the supported floor and is not
a claim about 3.10 support.

Wall clock timings below are `time(1)` output for the whole process, so they include
interpreter startup. They are the cost of running the verifier, not the simulated flight
time. Simulated flight time is the `time X / 120s` column inside each report.

## 1. The test suite

Command:

```bash
python3 -m pytest -q
```

Output:

```
.                                                                        [100%]
1 passed in 0.54s

real	0m0.663s
user	0m0.638s
sys	0m0.000s
```

One test is collected, `tests/test_controller.py::test_controller_passes_verification`,
confirmed with `python3 -m pytest -q --collect-only`. That single test wraps the whole
verifier, so a green `pytest` means the full 30 scenario batch passed.

## 2. Default verification batch, 30 scenarios from base seed 1000

Command:

```bash
python3 -m sim.run_verifier --scenarios 30 --verbose
```

Output:

```

AeroLoop verification report
================================================================
  seed 1000   PASS  coverage 100.0%  collisions 0  time  33.44s / 120s
  seed 1001   PASS  coverage 100.0%  collisions 0  time  34.56s / 120s
  seed 1002   PASS  coverage 100.0%  collisions 0  time  33.48s / 120s
  seed 1003   PASS  coverage 100.0%  collisions 0  time  33.98s / 120s
  seed 1004   PASS  coverage 100.0%  collisions 0  time  33.92s / 120s
  seed 1005   PASS  coverage 100.0%  collisions 0  time  34.36s / 120s
  seed 1006   PASS  coverage 100.0%  collisions 0  time  34.20s / 120s
  seed 1007   PASS  coverage 100.0%  collisions 0  time  34.38s / 120s
  seed 1008   PASS  coverage 100.0%  collisions 0  time  33.88s / 120s
  seed 1009   PASS  coverage 100.0%  collisions 0  time  33.62s / 120s
  seed 1010   PASS  coverage 100.0%  collisions 0  time  33.60s / 120s
  seed 1011   PASS  coverage 100.0%  collisions 0  time  33.62s / 120s
  seed 1012   PASS  coverage 100.0%  collisions 0  time  33.66s / 120s
  seed 1013   PASS  coverage 100.0%  collisions 0  time  34.08s / 120s
  seed 1014   PASS  coverage 100.0%  collisions 0  time  33.56s / 120s
  seed 1015   PASS  coverage 100.0%  collisions 0  time  33.78s / 120s
  seed 1016   PASS  coverage 100.0%  collisions 0  time  33.72s / 120s
  seed 1017   PASS  coverage 100.0%  collisions 0  time  33.52s / 120s
  seed 1018   PASS  coverage 100.0%  collisions 0  time  34.02s / 120s
  seed 1019   PASS  coverage 100.0%  collisions 0  time  33.52s / 120s
  seed 1020   PASS  coverage 100.0%  collisions 0  time  33.48s / 120s
  seed 1021   PASS  coverage 100.0%  collisions 0  time  33.46s / 120s
  seed 1022   PASS  coverage 100.0%  collisions 0  time  34.46s / 120s
  seed 1023   PASS  coverage 100.0%  collisions 0  time  33.82s / 120s
  seed 1024   PASS  coverage 100.0%  collisions 0  time  34.22s / 120s
  seed 1025   PASS  coverage 100.0%  collisions 0  time  33.98s / 120s
  seed 1026   PASS  coverage 100.0%  collisions 0  time  33.50s / 120s
  seed 1027   PASS  coverage 100.0%  collisions 0  time  34.46s / 120s
  seed 1028   PASS  coverage 100.0%  collisions 0  time  33.62s / 120s
  seed 1029   PASS  coverage 100.0%  collisions 0  time  36.64s / 120s
================================================================
  scenarios passed : 30/30  (100.0%)
  mean coverage    : 100.0%
  total collisions : 0
  thresholds       : coverage >= 95%, collisions == 0, pass rate >= 90%

  RESULT: PASS


real	0m0.558s
user	0m0.556s
sys	0m0.000s
```

Derived from the 30 `time` values in that report, computed over the pasted numbers:

| Quantity                       | Value    |
| ------------------------------ | -------- |
| Fastest simulated sweep        | 33.44 s  |
| Slowest simulated sweep        | 36.64 s  |
| Mean simulated sweep           | 33.95 s  |
| Time budget                    | 120 s    |
| Slowest sweep as share of budget | 30.5 %  |

## 3. Unseen seed batch, 50 scenarios from base seed 424242

This base seed was picked for this document and does not appear anywhere in `sim/`,
`tests/`, `viz/` or `controller.py`, so no part of the controller was tuned against it.

Command:

```bash
python3 -m sim.run_verifier --scenarios 50 --seed 424242 --verbose
```

Full per scenario lines for the first 28 scenarios, then the summary block, verbatim:

```

AeroLoop verification report
================================================================
  seed 424242 PASS  coverage 100.0%  collisions 0  time  33.96s / 120s
  seed 424243 PASS  coverage 100.0%  collisions 0  time  33.58s / 120s
  seed 424244 PASS  coverage 100.0%  collisions 0  time  33.62s / 120s
  seed 424245 PASS  coverage 100.0%  collisions 0  time  33.50s / 120s
  seed 424246 PASS  coverage 100.0%  collisions 0  time  33.50s / 120s
  seed 424247 PASS  coverage 100.0%  collisions 0  time  33.74s / 120s
  seed 424248 PASS  coverage 100.0%  collisions 0  time  34.04s / 120s
  seed 424249 PASS  coverage 100.0%  collisions 0  time  33.90s / 120s
  seed 424250 PASS  coverage 100.0%  collisions 0  time  33.72s / 120s
  seed 424251 PASS  coverage 100.0%  collisions 0  time  34.44s / 120s
  seed 424252 PASS  coverage 100.0%  collisions 0  time  33.92s / 120s
  seed 424253 PASS  coverage 100.0%  collisions 0  time  33.76s / 120s
  seed 424254 PASS  coverage 100.0%  collisions 0  time  35.28s / 120s
  seed 424255 PASS  coverage 100.0%  collisions 0  time  33.58s / 120s
  seed 424256 PASS  coverage 100.0%  collisions 0  time  33.50s / 120s
  seed 424257 PASS  coverage 100.0%  collisions 0  time  34.28s / 120s
  seed 424258 PASS  coverage 100.0%  collisions 0  time  33.40s / 120s
  seed 424259 PASS  coverage 100.0%  collisions 0  time  34.28s / 120s
  seed 424260 PASS  coverage 100.0%  collisions 0  time  33.88s / 120s
  seed 424261 PASS  coverage 100.0%  collisions 0  time  33.46s / 120s
  seed 424262 PASS  coverage 100.0%  collisions 0  time  33.78s / 120s
  seed 424263 PASS  coverage 100.0%  collisions 0  time  33.44s / 120s
  seed 424264 PASS  coverage 100.0%  collisions 0  time  34.14s / 120s
  seed 424265 PASS  coverage 100.0%  collisions 0  time  34.86s / 120s
  seed 424266 PASS  coverage 100.0%  collisions 0  time  33.56s / 120s
  seed 424267 PASS  coverage 100.0%  collisions 0  time  34.58s / 120s
  seed 424268 PASS  coverage 100.0%  collisions 0  time  33.40s / 120s
================================================================
  scenarios passed : 50/50  (100.0%)
  mean coverage    : 100.0%
  total collisions : 0
  thresholds       : coverage >= 95%, collisions == 0, pass rate >= 90%

  RESULT: PASS


real	0m0.920s
user	0m0.912s
sys	0m0.004s
```

Derived over all 50 `time` values in that run:

| Quantity                | Value   |
| ----------------------- | ------- |
| Fastest simulated sweep | 33.36 s |
| Slowest simulated sweep | 36.96 s |
| Mean simulated sweep    | 33.94 s |
| Scenarios with a collision | 0    |
| Scenarios below 95 % coverage | 0 |

## 4. Second unseen seed batch, 50 scenarios from base seed 20260823

A second unseen base seed, run to check that the first one was not a lucky draw.

Command:

```bash
python3 -m sim.run_verifier --scenarios 50 --seed 20260823 --verbose
```

Summary block, verbatim:

```
================================================================
  scenarios passed : 50/50  (100.0%)
  mean coverage    : 100.0%
  total collisions : 0
  thresholds       : coverage >= 95%, collisions == 0, pass rate >= 90%

  RESULT: PASS


real	0m0.903s
user	0m0.898s
sys	0m0.000s
```

Derived over all 50 `time` values in that run: fastest 33.36 s, slowest 37.58 s,
mean 33.96 s.

## 5. The human safety gate

`scripts/approve.py` reruns the verifier and then blocks on one typed answer. Run with
`no` on stdin, the tail of the output is:

```
  thresholds       : coverage >= 95%, collisions == 0, pass rate >= 90%

  RESULT: PASS

Verification PASSED across all scenarios.
Artifact: controller.py, written entirely by Devin with no human edits.

This is the only human decision in the pipeline.
Approving means: cleared for inspection flight near a real aircraft.

Approve for real-aircraft inspection flight? [yes/no] 
NOT APPROVED. Controller held.
```

Command used:

```bash
printf 'no\n' | python3 scripts/approve.py
```

Answering `yes` prints `APPROVED. Controller released for flight operations.` and exits 0.
Held and approved are the only two outcomes, and the gate refuses to ask at all if the
verifier did not pass.

## 6. The trigger path requires environment credentials and nothing else

Command:

```bash
env -u DEVIN_API_KEY -u DEVIN_ORG_ID python3 scripts/trigger_devin.py --repo https://github.com/Eshaank08/aeroloop.git
```

Output, and the shell exit status:

```
Set DEVIN_API_KEY and DEVIN_ORG_ID in your environment first.
exit=1
```

The key lives only in the environment. No credential is stored in the repository.

## 7. What the artifact is, checked against git

`controller.py` on master was authored by the Devin session, not by a human. Checked with:

```bash
git log -1 --format='%an %ae %s' f62456d
```

Output:

```
Devin AI 158243242+devin-ai-integration[bot]@users.noreply.github.com Implement nacelle inspection flight controller
```

That commit reached master through the merge commit `e069577`, `Merge pull request #4
from Eshaank08/devin/1787422507-flight-controller`, confirmed with `git log --oneline
master`. There is no later commit touching `controller.py`.

## Not measured

State these as unmeasured rather than guessing at them:

- **Number of iterations the Devin session needed.** The session history is not in the
  repository, so the write, run, fix count is not something this document can prove.
- **Wall clock length of the live Devin session.** Not recorded here.
- **Verifier behaviour under simulator v2.** The v2 camera gated coverage model is not
  merged, so no v2 number exists yet. Every number above is simulator v1.
- **Anything about real hardware.** No drone flew. The artifact is verified flight
  software, not a flight test.
