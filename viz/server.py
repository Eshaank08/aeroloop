"""Local HTTP command server for the AeroLoop flight view."""

import argparse
from dataclasses import replace
from functools import partial
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from inspection.adaptive import AdaptiveRunner
from inspection.artifact import build_artifact
from inspection.devin import DevinClient, DevinRecapturePlanner
from inspection.devin import DevinMissionSession
from inspection.quality import QualityOracle
from inspection.work_order import parse_work_order
from mission.agent import DevinMissionPlanner, ScriptedPilot, run_mission
from mission.contract import ACTION_SCHEMA
from mission.episode import MissionEpisode
from mission.intent import parse_mission_intent
from viz.flightlab import fly
from viz.mission import CommandError, EXAMPLES, help_text, parse
from viz.replay import scene


VIZ_DIR = Path(__file__).resolve().parent
REPO_ROOT = VIZ_DIR.parent
# Served from the repository root rather than viz/, so the mission view can use the
# real turbofan and quadcopter models and read written mission artifacts.
ROOT_PREFIXES = ("/engine-reference/", "/artifacts/")
# Containment must be checked against these directories, not the repository root.
# Checking the root only would let "/artifacts/../.env" resolve inside the repo and
# be served, which hands out .env and .git to anything that can reach the port.
ALLOWED_ROOTS = tuple(
    (REPO_ROOT / prefix.strip("/")).resolve() for prefix in ROOT_PREFIXES
)
# Any path that matched a prefix but escaped its directory is mapped here so the
# request 404s instead of falling through to another root.
FORBIDDEN_PATH = str(REPO_ROOT / "artifacts" / ".aeroloop-forbidden")

# The command endpoints run real work and can spend Devin credits, so a POST is
# only honoured when it did not come from another website.
LOCAL_ORIGINS = ("http://127.0.0.1", "http://localhost", "http://[::1]")


def _inspection_planner(request: dict):
    name = str(request.get("planner") or os.environ.get("AEROLOOP_INSPECTION_PLANNER", "rule")).lower()
    if name in {"rule", "rule_engine"}:
        return None
    if name != "devin":
        raise ValueError("planner must be 'rule' or 'devin'")
    max_acu_text = os.environ.get("AEROLOOP_DEVIN_MAX_ACU", "").strip()
    max_acu = int(max_acu_text) if max_acu_text else None
    return DevinRecapturePlanner(DevinClient.from_env(), max_acu_limit=max_acu)


SECTORS = {
    "all": None,
    "top": [index for index in range(24) if index % 8 in (0, 1, 7)],
    "ring0": list(range(8)),
}


def _wind_label(scale: float) -> str:
    if scale == 0.0:
        return "calm"
    if scale == 0.5:
        return "light wind"
    if scale == 2.0:
        return "heavy wind"
    return f"wind x{scale:g}"


class CommandHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def translate_path(self, path):
        clean = unquote(urlsplit(path).path)
        if clean.startswith(ROOT_PREFIXES):
            candidate = (REPO_ROOT / clean.lstrip("/")).resolve()
            # resolve() has already followed any symlink, so a link that points
            # out of the served directory fails this check too.
            if any(
                candidate == root or candidate.is_relative_to(root)
                for root in ALLOWED_ROOTS
            ):
                return str(candidate)
            return FORBIDDEN_PATH
        return super().translate_path(path)

    def _origin_is_local(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin.startswith(LOCAL_ORIGINS)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/api/capabilities":
            # The UI asks before offering a live mission, so a judge is never
            # given a button that can only fail.
            has_credentials = bool(
                os.environ.get("DEVIN_API_KEY") and os.environ.get("DEVIN_ORG_ID")
            )
            self._send_json(200, {
                "devin_available": has_credentials,
                "reason": "" if has_credentials else (
                    "This server was started without DEVIN_API_KEY and DEVIN_ORG_ID, so "
                    "live missions are refused. Restart it with both exported to enable "
                    "Devin. The baseline agent works either way."
                ),
            })
            return
        if path == "/api/scene":
            payload = scene()
            payload["examples"] = EXAMPLES
            payload["help"] = help_text()
            self._send_json(200, payload)
            return
        super().do_GET()

    def _bad(self, message: str, status: int = 200):
        self._send_json(status, {"ok": False, "reply": message})

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length))

    def _fly(self):
        try:
            request = self._read_json()
            text = request.get("text") if isinstance(request, dict) else None
            mission = parse(text)
        except CommandError as error:
            self._send_json(
                200,
                {
                    "ok": False,
                    "reply": str(error) + " " + "Try " + EXAMPLES[0] + ".",
                },
            )
            return
        except Exception as error:
            self._send_json(500, {"ok": False, "reply": f"Flight command failed: {error}"})
            return

        try:
            trace = fly(mission)
            mission_data = {
                "kind": mission.kind,
                "label": mission.label,
                "wind_seed": mission.wind_seed,
                "wind_scale": mission.wind_scale,
                "start": mission.start,
                "waypoints": mission.waypoints,
            }
            reply = (
                f"Flying {mission.label}, seed {mission.wind_seed}, "
                f"{_wind_label(mission.wind_scale)}"
            )
            self._send_json(
                200,
                {"ok": True, "reply": reply, "mission": mission_data, "trace": trace},
            )
        except Exception as error:
            self._send_json(500, {"ok": False, "reply": f"Flight command failed: {error}"})

    def _inspect(self):
        try:
            request = self._read_json()
            text = request.get("text") if isinstance(request, dict) else None
            work_order = parse_work_order(text or "")
            planner = _inspection_planner(request if isinstance(request, dict) else {})
        except Exception as error:
            self._send_json(400, {"ok": False, "reply": f"Could not parse work order: {error}"})
            return

        try:
            runner = AdaptiveRunner(planner=planner, oracle=QualityOracle())
            result = runner.run(
                work_order.label,
                work_order.nacelle,
                work_order.limits,
                seed=work_order.seed,
                wind_scale=work_order.wind_scale,
                selected_waypoints=work_order.selected_waypoints,
                selected_waypoint_indexes=work_order.selected_waypoint_indexes,
            )
            artifact = build_artifact(result, nacelle=work_order.nacelle, limits=work_order.limits)
            trace = self._combine_for_display(result)
            good = sum(1 for q in result.final_quality if q.status == "good")
            disposition = result.final_disposition
            reply = (
                f"adaptive run complete with {result.planner}: {disposition}. "
                f"{good}/{len(result.final_quality)} captures good."
            )
            if result.planner_failed:
                reply += " Planner unreachable, no follow-up actions were flown."
            elif result.policy_violations:
                reply += f" {len(result.policy_violations)} request(s) rejected by policy."
            self._send_json(
                200,
                {
                    "ok": True,
                    "reply": reply,
                    "trace": trace,
                    "artifact": artifact,
                    "captures": [c.__dict__ for c in result.final_captures],
                    "quality": [q.__dict__ for q in result.final_quality],
                    "planner": {
                        "name": result.planner,
                        "metadata": result.planner_metadata,
                        "failed": result.planner_failed,
                        "violations": result.policy_violations,
                    },
                    "mission": {
                        "kind": "sweep",
                        "label": work_order.label,
                        "sector": work_order.sector,
                        "waypoints": list(work_order.selected_waypoints or work_order.nacelle.waypoints()),
                        "start": (0.0, 0.0, 6.0),
                        "wind_seed": work_order.seed,
                        "wind_scale": work_order.wind_scale,
                    },
                },
            )
        except Exception as error:
            self._send_json(500, {"ok": False, "reply": f"Inspection run failed: {error}"})

    @staticmethod
    def _combine_for_display(result):
        """Merge initial and follow-up traces into one scrubbable timeline."""
        initial = result.initial.trace
        followup = result.followup_result.trace if result.followup_result else {"frames": []}
        combined = dict(initial)
        combined["frames"] = []
        elapsed = 0.0
        for frame in initial.get("frames", []):
            new_frame = dict(frame)
            new_frame["phase"] = "initial"
            combined["frames"].append(new_frame)
        elapsed += initial.get("elapsed_s", 0.0)
        for frame in followup.get("frames", []):
            new_frame = dict(frame)
            new_frame["t"] = round(frame["t"] + elapsed, 3)
            new_frame["phase"] = "re-capture"
            combined["frames"].append(new_frame)
        combined["elapsed_s"] = round(elapsed + followup.get("elapsed_s", 0.0), 3)
        combined["waypoints"] = list(combined.get("waypoints", []))
        return combined

    def _mission(self):
        """Run one autonomous simulator v2 mission and return it for replay."""
        try:
            request = self._read_json() or {}
            planner_name = str(request.get("planner", "baseline")).lower()
            # A plain sentence is the primary interface. Seed and sector remain
            # accepted so the CLI and the tests can pin an exact scenario.
            text = str(request.get("text", "") or "").strip()
            intent = parse_mission_intent(text or "inspect the whole nacelle")
            if request.get("seed") is not None:
                intent = replace(intent, seed=int(request["seed"]), seed_was_random=False)
            if request.get("sector") in SECTORS and SECTORS[request["sector"]] is not None:
                intent = replace(intent, authorised_indexes=SECTORS[request["sector"]])
            if request.get("max_actions") is not None:
                intent = replace(intent, max_actions=int(request["max_actions"]))
        except Exception as error:
            self._send_json(400, {"ok": False, "reply": f"Bad mission request: {error}"})
            return

        seed = intent.seed
        authorised = intent.authorised_indexes
        max_actions = intent.max_actions

        api_calls: list = []
        try:
            if planner_name == "devin":
                client = DevinClient.from_env(
                    poll_interval_s=8.0, timeout_s=420.0, recorder=api_calls,
                )
                max_acu_text = os.environ.get("AEROLOOP_DEVIN_MAX_ACU", "").strip()
                session = DevinMissionSession(
                    client,
                    ACTION_SCHEMA,
                    title=f"AeroLoop autonomous mission seed {seed}",
                    max_acu_limit=int(max_acu_text) if max_acu_text else None,
                )
                planner = DevinMissionPlanner(session, work_order=intent.text)
            elif planner_name == "baseline":
                planner = ScriptedPilot()
            else:
                raise ValueError("planner must be 'devin' or 'baseline'")
        except Exception as error:
            self._send_json(400, {"ok": False, "reply": str(error)})
            return

        try:
            episode = MissionEpisode(seed=seed, authorised_indexes=authorised)
            run = run_mission(
                planner, seed=seed, authorised_indexes=authorised,
                max_actions=max_actions, episode=episode,
            )
            self._send_json(200, {
                "ok": True,
                "reply": (
                    f"{run.planner_name} inspected {run.verification['inspected_count']}"
                    f"/{run.verification['waypoint_count']} waypoints of {intent.region}"
                    f" on seed {seed}: {run.disposition}"
                ),
                "seed": seed,
                "intent": intent.to_dict(),
                "api_calls": api_calls,
                "sector": intent.region,
                "waypoints": [list(point) for point in episode.waypoints],
                "authorised_indexes": episode.authorised_indexes,
                "frames": episode.frames,
                "artifact": run.to_dict(),
            })
        except Exception as error:
            self._send_json(500, {"ok": False, "reply": f"Mission failed: {error}"})

    def do_POST(self):
        path = urlsplit(self.path).path
        if not self._origin_is_local():
            self._send_json(403, {
                "ok": False,
                "reply": "Cross-site requests are not accepted by the flight view.",
            })
            return
        if path == "/api/fly":
            self._fly()
        elif path == "/api/inspect":
            self._inspect()
        elif path == "/api/mission":
            self._mission()
        else:
            self._send_json(404, {"ok": False, "reply": "Unknown API endpoint."})


def main():
    parser = argparse.ArgumentParser(description="Serve the local AeroLoop flight view.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    handler = partial(CommandHandler, directory=str(VIZ_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Open http://127.0.0.1:{args.port}/flight_view.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
