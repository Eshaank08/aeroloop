"""Run one adaptive AeroLoop mission with Devin choosing the re-capture actions.

Usage:
    export DEVIN_API_KEY=cog_...
    export DEVIN_ORG_ID=org_...
    python scripts/run_devin_mission.py \
        --work-order "inspect top side, light wind seed 606076"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from inspection.adaptive import AdaptiveRunner
from inspection.artifact import build_artifact
from inspection.devin import DevinClient, DevinRecapturePlanner
from inspection.quality import QualityOracle
from inspection.work_order import parse_work_order


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Devin-controlled AeroLoop re-capture mission.")
    parser.add_argument(
        "--work-order",
        default="inspect top side, light wind seed 606076",
        help="plain-language inspection request",
    )
    parser.add_argument("--output", help="artifact JSON path")
    parser.add_argument("--poll", type=float, default=10.0, help="Devin polling interval in seconds")
    parser.add_argument("--timeout", type=float, default=180.0, help="maximum Devin wait in seconds")
    parser.add_argument("--max-acu", type=int, help="optional mission ACU limit")
    args = parser.parse_args()

    work_order = parse_work_order(args.work_order)
    try:
        client = DevinClient.from_env(poll_interval_s=args.poll, timeout_s=args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    planner = DevinRecapturePlanner(client, max_acu_limit=args.max_acu)
    result = AdaptiveRunner(planner=planner, oracle=QualityOracle()).run(
        work_order.label,
        work_order.nacelle,
        work_order.limits,
        seed=work_order.seed,
        wind_scale=work_order.wind_scale,
        selected_waypoints=work_order.selected_waypoints,
        selected_waypoint_indexes=work_order.selected_waypoint_indexes,
    )
    artifact = build_artifact(result, nacelle=work_order.nacelle, limits=work_order.limits)

    output = Path(args.output) if args.output else Path("artifacts") / f"devin-mission-{work_order.seed}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"planner: {result.planner}")
    if result.planner_metadata.get("session_url"):
        print(f"Devin session: {result.planner_metadata['session_url']}")
    if result.planner_failed:
        print("planner failed: the mission could not reach Devin, no follow-up actions were flown")
    for violation in result.policy_violations:
        print(f"rejected: {violation}")
    print(f"disposition: {result.final_disposition}")
    print(f"captures: {sum(q.status == 'good' for q in result.final_quality)}/{len(result.final_quality)} good")
    print(f"artifact: {output.resolve()}")


if __name__ == "__main__":
    main()
