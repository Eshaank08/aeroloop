"""Local HTTP command server for the AeroLoop flight view."""

import argparse
from functools import partial
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from inspection.adaptive import AdaptiveRunner
from inspection.artifact import build_artifact
from inspection.devin import DevinClient, DevinRecapturePlanner
from inspection.quality import QualityOracle
from inspection.work_order import parse_work_order
from viz.flightlab import fly
from viz.mission import CommandError, EXAMPLES, help_text, parse
from viz.replay import scene


VIZ_DIR = Path(__file__).resolve().parent


def _inspection_planner(request: dict):
    name = str(request.get("planner") or os.environ.get("AEROLOOP_INSPECTION_PLANNER", "rule")).lower()
    if name in {"rule", "rule_engine"}:
        return None
    if name != "devin":
        raise ValueError("planner must be 'rule' or 'devin'")
    max_acu_text = os.environ.get("AEROLOOP_DEVIN_MAX_ACU", "").strip()
    max_acu = int(max_acu_text) if max_acu_text else None
    return DevinRecapturePlanner(DevinClient.from_env(), max_acu_limit=max_acu)


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

    def do_GET(self):
        path = urlsplit(self.path).path
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

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/api/fly":
            self._fly()
        elif path == "/api/inspect":
            self._inspect()
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
