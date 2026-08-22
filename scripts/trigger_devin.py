"""Create a Devin session against this repo and poll it to completion.

Usage:
    export DEVIN_API_KEY=cog_...
    export DEVIN_ORG_ID=org_...
    python scripts/trigger_devin.py --repo git@github.com:<you>/aeroloop.git

The API key is read from the environment only. Never hardcode it, never paste it into
a chat or a commit.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API_BASE = "https://api.devin.ai/v3"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _request(method, url, key, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def build_prompt(repo_url: str) -> str:
    brief = (REPO_ROOT / "README.md").read_text()
    return (
        f"Work in the repository {repo_url}.\n\n"
        "Your task is defined in README.md, reproduced below. Write controller.py and "
        "nothing else. Run `pytest -q` to check your work, read the failure report, fix "
        "the controller, and rerun until the verification passes. Do not modify anything "
        "under sim/ or tests/. Open a pull request when pytest passes.\n\n"
        "----- README.md -----\n"
        f"{brief}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="git URL Devin should work in")
    ap.add_argument("--title", default="AeroLoop: write the inspection flight controller")
    ap.add_argument("--poll", type=int, default=30, help="seconds between status checks")
    ap.add_argument("--no-wait", action="store_true")
    args = ap.parse_args()

    key = os.environ.get("DEVIN_API_KEY")
    org = os.environ.get("DEVIN_ORG_ID")
    if not key or not org:
        sys.exit("Set DEVIN_API_KEY and DEVIN_ORG_ID in your environment first.")

    url = f"{API_BASE}/organizations/{org}/sessions"
    session = _request("POST", url, key, {
        "prompt": build_prompt(args.repo),
        "title": args.title,
    })
    sid = session.get("session_id") or session.get("id")
    print(f"session created: {sid}")
    print(f"url: {session.get('url', '(check the Devin dashboard)')}")

    if args.no_wait:
        return

    status_url = f"{url}/{sid}"
    while True:
        time.sleep(args.poll)
        s = _request("GET", status_url, key)
        state = s.get("status") or s.get("status_enum") or "unknown"
        print(f"  [{time.strftime('%H:%M:%S')}] {state}")
        if state in {"finished", "blocked", "expired", "stopped", "errored"}:
            print(json.dumps(s, indent=2)[:2000])
            break


if __name__ == "__main__":
    main()
