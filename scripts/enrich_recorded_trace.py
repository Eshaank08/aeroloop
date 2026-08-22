"""Add current seeded disturbance and synthetic sensor channels to a saved replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mission.environment import make_environment  # noqa: E402
from sim.scenarios import make_scenario  # noqa: E402


def enrich(payload: dict) -> dict:
    seed = int(payload["seed"])
    wind = make_scenario(seed)
    environment = make_environment(seed)
    for frame in payload.get("frames", []):
        time_s = float(frame["t"])
        frame["wind"] = [round(value, 4) for value in wind.at(time_s)]
        frame["sensors"] = environment.sample(time_s, frame["p"])
    payload["replay_channels"] = {
        "wind": "seeded simulator truth shown to the viewer only",
        "vision": "synthetic",
        "audio": "synthetic",
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", type=Path, nargs="?", default=Path("viz/data3/mission_trace.json")
    )
    args = parser.parse_args()
    payload = enrich(json.loads(args.path.read_text()))
    args.path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"enriched {len(payload.get('frames', []))} frames in {args.path}")


if __name__ == "__main__":
    main()
