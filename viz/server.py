"""Local HTTP command server for the AeroLoop flight view."""

import argparse
from functools import partial
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from viz.flightlab import fly
from viz.mission import CommandError, EXAMPLES, help_text, parse
from viz.replay import scene


VIZ_DIR = Path(__file__).resolve().parent


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

    def do_POST(self):
        path = urlsplit(self.path).path
        if path != "/api/fly":
            self._send_json(404, {"ok": False, "reply": "Unknown API endpoint."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
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
