"""Run one autonomous inspection mission in simulator v2.

Devin receives observations and chooses every mission action. The local flight
controller executes the accepted action. The verifier grades the result and a
hashed mission artifact records what Devin saw, chose, and was allowed to do.

    export DEVIN_API_KEY=cog_...
    export DEVIN_ORG_ID=org_...
    python scripts/run_autonomous_mission.py --seed 1000

The deterministic baseline spends no credits and is explicitly not the challenge
demo:

    python scripts/run_autonomous_mission.py --seed 1000 --planner baseline
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from inspection.devin import DevinClient, DevinMissionSession  # noqa: E402
from mission.agent import (  # noqa: E402
    MAX_ACTIONS,
    DevinMissionPlanner,
    ScriptedPilot,
    run_mission,
)
from mission.contract import ACTION_SCHEMA  # noqa: E402
from mission.episode import MissionEpisode  # noqa: E402


def _sector(name: str) -> list[int] | None:
    if name == "all":
        return None
    if name == "top":
        return [index for index in range(24) if index % 8 in (0, 1, 7)]
    if name == "ring0":
        return list(range(8))
    raise argparse.ArgumentTypeError("sector must be one of: all, top, ring0")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one autonomous AeroLoop mission.")
    parser.add_argument("--seed", type=int, default=1000, help="scenario seed, judge supplied")
    parser.add_argument("--planner", choices=("devin", "baseline"), default="devin")
    parser.add_argument("--sector", default="all", help="all, top or ring0")
    parser.add_argument("--max-actions", type=int, default=MAX_ACTIONS)
    parser.add_argument("--max-acu", type=int, help="optional mission ACU limit")
    parser.add_argument("--poll", type=float, default=10.0, help="Devin poll interval, seconds")
    parser.add_argument("--timeout", type=float, default=300.0, help="per decision timeout")
    parser.add_argument("--output", help="mission artifact path")
    parser.add_argument("--trace", help="optional flight trace path for replay")
    args = parser.parse_args()

    authorised = _sector(args.sector)

    if args.planner == "devin":
        try:
            client = DevinClient.from_env(poll_interval_s=args.poll, timeout_s=args.timeout)
        except ValueError as exc:
            parser.error(str(exc))
        session = DevinMissionSession(
            client,
            ACTION_SCHEMA,
            title=f"AeroLoop autonomous mission seed {args.seed}",
            max_acu_limit=args.max_acu,
        )
        planner = DevinMissionPlanner(session)
    else:
        planner = ScriptedPilot()

    episode = MissionEpisode(seed=args.seed, authorised_indexes=authorised)
    run = run_mission(
        planner,
        seed=args.seed,
        authorised_indexes=authorised,
        max_actions=args.max_actions,
        episode=episode,
    )
    artifact = run.to_dict()

    output = Path(args.output) if args.output else (
        Path("artifacts") / f"mission-{args.planner}-{args.seed}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.trace:
        trace_path = Path(args.trace)
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(json.dumps({
            "seed": args.seed,
            "waypoints": [list(point) for point in episode.waypoints],
            "authorised_indexes": episode.authorised_indexes,
            "frames": episode.frames,
            "verification": run.verification,
        }, indent=2) + "\n", encoding="utf-8")

    verification = run.verification
    print(f"mission     : {run.mission_id}  seed {args.seed}  sector {args.sector}")
    print(f"planner     : {run.planner_name}")
    if run.planner_metadata.get("session_url"):
        print(f"session     : {run.planner_metadata['session_url']}")
    accepted = sum(
        1 for step in run.steps if step.get("decision", {}).get("decision") == "accepted"
    )
    print(f"actions     : {accepted} accepted, {len(run.rejections)} rejected")
    for rejection in run.rejections:
        print(f"  rejected  : {rejection}")
    if run.planner_failed:
        print(f"agent lost  : {run.planner_failures[-1]}")
    if run.safe_stop:
        print("safe stop   : the vehicle was returned toward home by the safety envelope")
    print(f"agent claim : {run.agent_claim or 'none'}")
    print(
        f"verifier    : {verification['inspected_count']}/{verification['waypoint_count']} "
        f"inspected, coverage {verification['coverage'] * 100:.1f}%, "
        f"elapsed {verification['elapsed_s']:.1f}s, failure {verification['failure']}"
    )
    print(f"disposition : {run.disposition}")
    print(f"artifact    : {output.resolve()}")

    sys.exit(0 if run.disposition == "PASS" else 1)


if __name__ == "__main__":
    main()
