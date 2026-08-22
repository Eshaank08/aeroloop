"""Dispatch inspection jobs to Devin and collect verified flight software.

One plain-language inspection request goes in. For each request, this script derives
the job spec, creates a Devin session against the repo, and waits. Devin writes the
controller, runs the verifier, reads the failure, fixes it, and reruns, on its own.
Nothing here retries for it and nothing here answers questions for it.

Usage:
    export DEVIN_API_KEY=cog_...
    export DEVIN_ORG_ID=org_...

    # the three jobs of the standing demo
    python scripts/trigger_devin.py --repo git@github.com:<you>/aeroloop.git

    # or dispatch whatever a planner actually asked for
    python scripts/trigger_devin.py --repo <url> \
        --request "detailed sweep of the left nacelle after a bird strike"

The API key is read from the environment only. Never hardcode it, never paste it into
a chat or a commit.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.devin.ai/v3"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sim.jobs import JOBS, parse_job  # noqa: E402

DEFAULT_SCENARIOS = 30
DEFAULT_BASE_SEED = 1000

# Devin reports its own verdict against this schema, so the dispatcher never has to
# read a chat transcript to find out what happened. The schema is a self-report, so
# the dispatcher re-runs the verifier itself before believing any of it.
OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["verdict", "scenarios_passed", "scenarios_total", "total_collisions"],
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
        "scenarios_passed": {"type": "integer"},
        "scenarios_total": {"type": "integer"},
        "mean_coverage_percent": {"type": "number"},
        "total_collisions": {"type": "integer"},
        "iterations": {
            "type": "integer",
            "description": "How many times you ran the verifier before it passed.",
        },
        "summary": {"type": "string"},
    },
}

# v3 session states. Anything in TERMINAL means stop polling.
TERMINAL = {"exit", "error", "suspended"}
# These two mean the session is asking a human for something, which is precisely the
# thing this pipeline claims never happens. Surface them loudly rather than hanging.
NEEDS_HUMAN = {"waiting_for_user", "waiting_for_approval"}


def _request(method, url, key, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:800]
        raise SystemExit(f"{method} {url} failed with HTTP {exc.code}:\n{body}") from exc


def build_prompt(repo_url, job, scenarios, seed):
    brief = (REPO_ROOT / "README.md").read_text()
    return (
        f"Work in the repository {repo_url}.\n\n"
        f"INSPECTION JOB: {job.name}\n{job.summary}\n\n"
        "Your task is defined in README.md, reproduced below. Write controller.py and "
        "nothing else. Run the verifier to check your work, read the failure report, "
        "fix the controller, and rerun until verification passes. Do not modify "
        "anything under sim/ or tests/. Open a pull request when it passes.\n\n"
        f"Grade against the {job.name} job, {scenarios} scenarios, base seed {seed}:\n"
        f"AEROLOOP_JOB={job.name} AEROLOOP_SCENARIOS={scenarios} "
        f"AEROLOOP_BASE_SEED={seed} python -m pytest -q\n"
        "The equivalent direct verifier command is:\n"
        f"python -m sim.run_verifier --job {job.name} --scenarios {scenarios} "
        f"--seed {seed} --verbose\n\n"
        "When you are done, report your final result through structured output: the "
        "verdict, how many scenarios passed, total collisions, and how many times you "
        "had to run the verifier before it passed.\n\n"
        "----- README.md -----\n"
        f"{brief}"
    )


def create_session(key, org, repo_url, job, scenarios, seed, run_tag, acu_limit):
    payload = {
        "prompt": build_prompt(repo_url, job, scenarios, seed),
        "title": f"AeroLoop: {job.name}",
        "tags": ["aeroloop", run_tag, f"job-{job.name}"],
        "structured_output_schema": OUTPUT_SCHEMA,
    }
    if acu_limit:
        payload["max_acu_limit"] = acu_limit
    session = _request("POST", f"{API_BASE}/organizations/{org}/sessions", key, payload)
    return {
        "job": job,
        "id": session.get("session_id") or session.get("id"),
        "url": session.get("url", "(check the Devin dashboard)"),
        "state": "new",
        "detail": None,
        "output": None,
        "prs": [],
        "asked_for_human": False,
    }


def poll(key, org, sessions, interval):
    """Poll every session until each reaches a terminal state."""
    pending = {s["id"] for s in sessions}
    while pending:
        time.sleep(interval)
        for s in sessions:
            if s["id"] not in pending:
                continue
            data = _request(
                "GET", f"{API_BASE}/organizations/{org}/sessions/{s['id']}", key
            )
            s["state"] = data.get("status", "unknown")
            s["detail"] = data.get("status_detail")
            s["output"] = data.get("structured_output") or s["output"]
            s["prs"] = data.get("pull_requests") or s["prs"]
            acus = data.get("acus_consumed")

            if s["detail"] in NEEDS_HUMAN:
                s["asked_for_human"] = True

            stamp = time.strftime("%H:%M:%S")
            detail = f"/{s['detail']}" if s["detail"] else ""
            acu = f"  {acus} ACU" if acus is not None else ""
            print(f"  [{stamp}] {s['job'].name:<18} {s['state']}{detail}{acu}")

            done = s["state"] in TERMINAL or (
                s["state"] == "running" and s["detail"] == "finished"
            )
            if done:
                pending.discard(s["id"])


def reverify(job, scenarios, seed):
    """Re-run the verifier here, on this machine, against what Devin actually wrote.

    Devin's structured output is a self-report. This is the part that decides.
    """
    import importlib

    import controller as controller_module
    from sim.run_verifier import verify

    importlib.reload(controller_module)
    ok, results = verify(
        controller_module.Controller,
        count=scenarios,
        base_seed=seed,
        nacelle=job.nacelle,
        limits=job.limits,
        verbose=False,
    )
    return ok, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="git URL Devin should work in")
    ap.add_argument("--request", action="append", default=None,
                    help="plain-language inspection request, repeatable")
    ap.add_argument("--poll", type=int, default=30, help="seconds between status checks")
    ap.add_argument("--seed", type=int, default=DEFAULT_BASE_SEED)
    ap.add_argument("--scenarios", type=int, default=DEFAULT_SCENARIOS)
    ap.add_argument("--max-acu", type=int, default=None, help="per-session ACU cap")
    ap.add_argument("--no-wait", action="store_true")
    ap.add_argument("--no-reverify", action="store_true",
                    help="skip the local re-run of the verifier")
    args = ap.parse_args()

    key = os.environ.get("DEVIN_API_KEY")
    org = os.environ.get("DEVIN_ORG_ID")
    if not key or not org:
        sys.exit("Set DEVIN_API_KEY and DEVIN_ORG_ID in your environment first.")

    requests = args.request or [job.summary for job in JOBS.values()]
    jobs = [parse_job(r) for r in requests]
    run_tag = f"run-{int(time.time())}"

    print(f"dispatching {len(jobs)} inspection job(s), tag {run_tag}, "
          f"seed {args.seed}, {args.scenarios} scenarios each\n")
    sessions = []
    for request, job in zip(requests, jobs):
        s = create_session(key, org, args.repo, job, args.scenarios, args.seed,
                           run_tag, args.max_acu)
        sessions.append(s)
        print(f'  "{request[:58]}"')
        print(f"    -> {job.name}  session {s['id']}\n       {s['url']}")

    if args.no_wait:
        return

    print("\nwaiting. nobody touches these until they come back.\n")
    poll(key, org, sessions, args.poll)

    print("\n" + "=" * 68)
    print("AeroLoop dispatch report")
    print("=" * 68)
    exit_code = 0
    for s in sessions:
        out = s["output"] or {}
        claimed = out.get("verdict", "no structured output")
        iterations = out.get("iterations")
        print(f"\n  job        : {s['job'].name}")
        print(f"  session    : {s['url']}")
        print(f"  end state  : {s['state']}"
              + (f"/{s['detail']}" if s["detail"] else ""))
        print(f"  Devin says : {claimed}"
              + (f", {iterations} verifier runs" if iterations is not None else ""))
        if s["prs"]:
            for pr in s["prs"]:
                print(f"  pull request: {pr.get('url', pr)}")
        if s["asked_for_human"]:
            print("  AUTONOMY BREAK: this session asked a human for something.")
            exit_code = 1

        if args.no_reverify:
            continue
        ok, results = reverify(s["job"], args.scenarios, args.seed)
        n_pass = sum(r.passed for r in results)
        collisions = sum(r.collisions for r in results)
        coverage = sum(r.coverage for r in results) / len(results)
        print(f"  we verify  : {'PASS' if ok else 'FAIL'}  {n_pass}/{len(results)} "
              f"scenarios, mean coverage {coverage * 100:.1f}%, "
              f"{collisions} collisions")
        if claimed == "PASS" and not ok:
            print("  DISAGREEMENT: Devin reported PASS, our verifier does not agree.")
        if not ok:
            exit_code = 1

    print("\n" + "=" * 68)
    print(f"  RESULT: {'ALL JOBS VERIFIED' if exit_code == 0 else 'NOT CLEARED'}")
    print("=" * 68 + "\n")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
