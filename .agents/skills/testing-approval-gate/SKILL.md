---
name: testing-approval-gate
description: How to exercise and adversarially test the AeroLoop verification artifact + human approval gate (scripts/approve.py, sim/report.py) from the shell.
---

# Testing the AeroLoop approval gate

## Setup
- `pip install -r requirements.txt` (numpy + pytest). `python3 -m pytest -q` should be green.
- No services, no web UI. Everything is shell-only, so a screen recording adds nothing.
- A full verifier run (30 scenarios, base seed 1000) takes under 1 second, so re-running
  `python3 scripts/approve.py` for each case is cheap.

## Useful facts
- `reports/` is gitignored; artifacts land at `reports/verification_<UTC>Z.json`.
- `--dry-run` writes the artifact and skips the prompt; `--report <path>` approves an
  existing artifact without re-running the verifier.
- The prompt only accepts the exact string `yes` (no strip, no case folding).
- The signature is sha256 over `json.dumps(report, indent=2, sort_keys=False,
  ensure_ascii=False) + "\n"` with `approval` forced to `null`. To recompute a digest
  independently, mirror exactly that serialization; any indent/newline difference changes it.
- Approver comes from `$APPROVER`, else `getpass.getuser()`.

## Adversarial cases worth repeating on any change here
1. Piped negative inputs: `y`, `YES`, `Yes`, empty line, ` yes `, `no` -> exit 1,
   `approval` stays `null`.
2. `< /dev/null` (EOF): safe (exit 1, no approval) but may raise an unhandled `EOFError`
   traceback; the same is true of nonexistent path, a directory, malformed/empty JSON, and
   an artifact missing `result`. These are robustness gaps, not gate bypasses. If you are
   asked to harden them, wrap `load_report`/`input()` in try/except in `main()`.
3. FAIL artifact (`result: "FAIL"`) with `yes` on stdin: must print `failure:` lines,
   never print the prompt, exit 1.
4. Hand-written approval blocks: `check_integrity` only checks the digest, not that
   `result == "PASS"`. A self-signed FAIL artifact passes `check_integrity`, so downstream
   consumers must check `result == "PASS"` as well as integrity, not integrity alone.
5. Tamper: mutate any number under `run` or `scenarios` in an approved artifact ->
   `check_integrity` False and `--report` refuses with an integrity error.

## Devin Secrets Needed
None.
