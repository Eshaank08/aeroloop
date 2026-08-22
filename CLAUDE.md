# CLAUDE.md

Project: **AeroLoop**, Cognition track, EHL Munich hackathon.
Deadline: **23 Aug 2026, 12:01 PM CET.** Time is the binding constraint on every decision.

Read `docs/GOAL.md`, `docs/IDEA.md`, `docs/PRD.md` before doing anything substantive.

## The one rule that defines this project

**Devin writes `controller.py`. Nobody else touches it.**

Do not write, patch, hint at, or "just fix quickly" the flight controller. The entire
claim of the project is that an AI engineer produced it unsupervised. One human edit to
that file and the submission is dishonest. If Devin cannot solve it, the correct response
is to fix the task spec in README.md or tune the verifier parameters, never to write the
solution.

## Division of labour

- **Claude Code (you):** simulator, verifier, tests, trigger script, approval gate, docs,
  deck.
- **Devin:** `controller.py`, via its own write-test-fix loop.

## Conventions

- Python 3.11+, numpy only. No physics engine, no external sim, no drone hardware.
- Plain functions and small dataclasses. No frameworks, no abstraction layers.
- The verifier must stay deterministic given a seed. Never introduce unseeded randomness.
- Never modify `sim/` to make a failing controller pass. That is grading our own homework.

## Verifier integrity

The verifier existed before Devin wrote a line, and it is adversarial by design. If a
change to `sim/` would make the task easier, ask whether it is a genuine spec fix or a
quiet lowering of the bar. Record every parameter change in `docs/IDEA.md` under "how the
approach changed", because the judges explicitly ask how the approach evolved.

## Devin API

Base: `https://api.devin.ai/v3/organizations/{org_id}/sessions`
Auth: `Authorization: Bearer $DEVIN_API_KEY`

**Never hardcode or echo the API key.** Read it from the environment only. If a key ever
appears in chat, a transcript, or a commit, treat it as compromised and rotate it at
Settings > Service users.

## Writing style

No em dashes anywhere, in docs, code comments, or the deck.
