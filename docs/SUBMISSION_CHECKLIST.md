# Submission checklist

This is the final gate before submitting AeroLoop. Do not call the project ready until
every checkbox below is true on the exact commit being submitted.

## Entire session record — required

> This challenge requires an Entire session record, but your repository has no
> recognized Entire checkpoint branch or ref. Install Entire
> ([https://entire.io](https://entire.io)), run `entire enable --agent <your-tool>`,
> commit your AI session, push (including the checkpoint data), then resubmit. If your
> repo is private, make sure `ehl-gg` has access so we can read it.

This repository is configured for Codex with project settings and checkpoint refs:

```bash
entire status
# expected: Enabled, Agents: Codex, Checkpoints sync to: origin
```

Before submission:

- [ ] The code commit is pushed to `origin/master`.
- [ ] `entire status` reports Enabled on the submitted branch.
- [ ] The current session has a recognized Entire checkpoint ref.
- [ ] `git push origin master` has also pushed the Entire checkpoint data.
- [ ] The GitHub repository is public, or the GitHub user `ehl-gg` has read access.
- [ ] The submitted GitHub URL and commit SHA match the tested commit.

Never commit Devin credentials. Entire records the development session; it does not
replace the run artifact or the Devin session URL produced by AeroLoop.

## Product proof

- [ ] The GitHub Actions `Python tests` check passes on the submitted commit.
- [ ] `python -m pytest -q` passes.
- [ ] `python -m sim.run_verifier --scenarios 30 --seed 1000` passes.
- [ ] `python -m sim2.run_verifier --scenarios 30 --seed 1000` produces the recorded
      expected result, including the honestly documented seed 1027 miss.
- [ ] A local baseline mission completes from the browser without credentials.
- [ ] A live Devin mission is tested with credentials, or the recorded live Devin
      artifact is explicitly labelled as the network fallback.
- [ ] The mission view explains the dots, wind, synthetic vision/audio, safety stops,
      and final verifier verdict without requiring source-code knowledge.
- [ ] The backend view shows the Devin API calls, accepted/blocked decisions, hashes,
      and independent verdict.
- [ ] Floor contact, engine collision, unsafe speed and moving-object proximity cannot
      produce PASS.

## Honest scope

- [ ] Say that the flight, camera, object detections and acoustic readings are simulated.
- [ ] Say that green dots mean usable simulated capture geometry, not defect detection.
- [ ] Say that Devin chooses bounded mission actions; the onboard controller and safety
      layer handle real-time stabilization and emergency stops.
- [ ] Do not claim return-to-service authority. A qualified person owns physical release.

The stage runbook is [DEMO.md](DEMO.md), and the real-world path is
[REAL_WORLD_ROADMAP.md](REAL_WORLD_ROADMAP.md).
