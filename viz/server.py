"""Local HTTP command server for the AeroLoop flight view."""

import argparse
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hmac
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
import time
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import uuid4

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

# The command endpoints run real work and can spend Devin credits. Browser POSTs
# must be same-origin (or explicitly allow-listed), and live Devin requests need
# a separate server-side demo token. The token is never shipped in this frontend.
LOCAL_ORIGINS = ("http://127.0.0.1", "http://localhost", "http://[::1]")
MAX_REQUEST_BODY_BYTES = 16_384
MAX_REQUEST_TEXT_CHARS = 500
MAX_CONCURRENT_MISSIONS = 2
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW_S = 60.0
MAX_DEVIN_ACU_PER_MISSION = 20


class RequestRejected(ValueError):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


class SlidingWindowLimiter:
    """Small in-process abuse brake for a single-replica demo deployment."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = Lock()
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_s: float) -> bool:
        now = self.clock()
        cutoff = now - window_s
        with self.lock:
            events = self.events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True

    def clear(self) -> None:
        with self.lock:
            self.events.clear()


REQUEST_LIMITER = SlidingWindowLimiter()


def _devin_max_acu() -> int:
    raw = os.environ.get("AEROLOOP_DEVIN_MAX_ACU", "").strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError("AEROLOOP_DEVIN_MAX_ACU must be an integer") from error
    if not 1 <= value <= MAX_DEVIN_ACU_PER_MISSION:
        raise ValueError(
            f"AEROLOOP_DEVIN_MAX_ACU must be between 1 and {MAX_DEVIN_ACU_PER_MISSION}"
        )
    return value


def _devin_is_configured() -> bool:
    if not (
        os.environ.get("DEVIN_API_KEY")
        and os.environ.get("DEVIN_ORG_ID")
        and os.environ.get("AEROLOOP_DEMO_TOKEN")
    ):
        return False
    try:
        _devin_max_acu()
    except ValueError:
        return False
    return True


def _inspection_planner(request: dict):
    name = str(request.get("planner") or os.environ.get("AEROLOOP_INSPECTION_PLANNER", "rule")).lower()
    if name in {"rule", "rule_engine"}:
        return None
    if name != "devin":
        raise ValueError("planner must be 'rule' or 'devin'")
    return DevinRecapturePlanner(
        DevinClient.from_env(), max_acu_limit=_devin_max_acu(),
    )


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


MISSION_JOBS: dict[str, dict] = {}
MISSION_JOBS_LOCK = Lock()
MAX_MISSION_JOBS = 20


def _mission_payload(request: dict, on_progress=None) -> dict:
    """Run one mission independently of HTTP so sync and async routes stay identical."""
    planner_name = str(request.get("planner", "baseline")).lower()
    text = str(request.get("text", "") or "").strip()
    intent = parse_mission_intent(text or "inspect the whole nacelle")
    if request.get("seed") is not None:
        intent = replace(intent, seed=int(request["seed"]), seed_was_random=False)
    if request.get("sector") in SECTORS and SECTORS[request["sector"]] is not None:
        intent = replace(intent, authorised_indexes=SECTORS[request["sector"]])
    if request.get("max_actions") is not None:
        intent = replace(intent, max_actions=int(request["max_actions"]))

    seed = intent.seed
    authorised = intent.authorised_indexes
    api_calls: list = []
    if planner_name == "devin":
        client = DevinClient.from_env(
            poll_interval_s=8.0, timeout_s=420.0, recorder=api_calls,
        )
        session = DevinMissionSession(
            client,
            ACTION_SCHEMA,
            title=f"AeroLoop autonomous mission seed {seed}",
            max_acu_limit=_devin_max_acu(),
        )
        planner = DevinMissionPlanner(session, work_order=intent.text)
    elif planner_name == "baseline":
        planner = ScriptedPilot()
    else:
        raise ValueError("planner must be 'devin' or 'baseline'")

    episode = MissionEpisode(seed=seed, authorised_indexes=authorised)
    run = run_mission(
        planner,
        seed=seed,
        authorised_indexes=authorised,
        max_actions=intent.max_actions,
        episode=episode,
        on_progress=on_progress,
    )
    return {
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
        "evidence_targets": [list(point) for point in episode.evidence_targets],
        "authorised_indexes": episode.authorised_indexes,
        "frames": episode.frames,
        "artifact": run.to_dict(),
    }


def _job_message(stage: str, planner: str, step: dict | None) -> str:
    observation_id = (step or {}).get("observation_id", "")
    labels = {
        "preparing": "Preparing the scenario and authorised evidence targets.",
        "waiting_for_planner": (
            f"Observation {observation_id} sent to "
            f"{'Devin' if planner == 'devin' else 'the local test pilot'}; waiting for a decision."
        ),
        "action_accepted": f"Decision {observation_id} passed the safety envelope.",
        "action_rejected": f"Decision {observation_id} was blocked and returned to the planner.",
        "action_executed": f"Action {observation_id} completed; evaluating the new evidence.",
        "terminal_action": "The planner stopped; the independent verifier is checking the mission.",
        "planner_failed": "The planner became unavailable; executing the bounded safe stop.",
        "complete": "Mission complete. Loading the verified replay from 0.0 seconds.",
    }
    return labels.get(stage, "Mission is running.")


def _run_mission_job(job_id: str, request: dict) -> None:
    planner = str(request.get("planner", "baseline")).lower()

    def progress(stage, run, episode, step):
        snapshot = {
            "stage": stage,
            "message": _job_message(stage, planner, step),
            "steps": deepcopy(run.steps),
            "current_step": deepcopy(step),
            "frame_count": len(episode.frames),
            "updated_at": time.time(),
        }
        with MISSION_JOBS_LOCK:
            if job_id in MISSION_JOBS:
                history = MISSION_JOBS[job_id].setdefault("history", [])
                history.append({"stage": stage, "message": snapshot["message"]})
                MISSION_JOBS[job_id].update(snapshot)

    try:
        result = _mission_payload(request, on_progress=progress)
    except Exception as error:
        with MISSION_JOBS_LOCK:
            if job_id in MISSION_JOBS:
                MISSION_JOBS[job_id].update({
                    "status": "failed",
                    "stage": "failed",
                    "message": f"Mission failed: {error}",
                    "error": str(error),
                    "updated_at": time.time(),
                })
        return

    with MISSION_JOBS_LOCK:
        if job_id not in MISSION_JOBS:
            return
        MISSION_JOBS[job_id].setdefault("history", []).append({
            "stage": "complete",
            "message": _job_message("complete", planner, None),
        })
        MISSION_JOBS[job_id].update({
            "status": "complete",
            "stage": "complete",
            "message": _job_message("complete", planner, None),
            "result": result,
            "steps": deepcopy(result["artifact"]["steps"]),
            "frame_count": len(result["frames"]),
            "updated_at": time.time(),
        })


def start_mission_job(request: dict) -> str:
    job_id = uuid4().hex
    now = time.time()
    job = {
        "ok": True,
        "job_id": job_id,
        "status": "running",
        "stage": "preparing",
        "message": _job_message("preparing", str(request.get("planner", "baseline")), None),
        "steps": [],
        "current_step": None,
        "frame_count": 0,
        "history": [{"stage": "preparing", "message": _job_message("preparing", "", None)}],
        "created_at": now,
        "updated_at": now,
    }
    with MISSION_JOBS_LOCK:
        running = sum(1 for value in MISSION_JOBS.values() if value["status"] == "running")
        if running >= MAX_CONCURRENT_MISSIONS:
            raise RuntimeError("The mission capacity is full; wait for a running mission to finish")
        if len(MISSION_JOBS) >= MAX_MISSION_JOBS:
            finished = [
                key for key, value in MISSION_JOBS.items()
                if value["status"] in {"complete", "failed"}
            ]
            if not finished:
                raise RuntimeError("Too many missions are already running")
            oldest = min(finished, key=lambda key: MISSION_JOBS[key]["created_at"])
            del MISSION_JOBS[oldest]
        MISSION_JOBS[job_id] = job
    Thread(target=_run_mission_job, args=(job_id, dict(request)), daemon=True).start()
    return job_id


def mission_job_snapshot(job_id: str) -> dict | None:
    with MISSION_JOBS_LOCK:
        job = MISSION_JOBS.get(job_id)
        return deepcopy(job) if job is not None else None


class CommandHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), geolocation=(), microphone=(self)")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
            "connect-src 'self'; media-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        super().end_headers()

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        if not self._origin_is_allowed():
            self._send_json(403, {"ok": False, "reply": "Cross-site requests are not accepted."})
            return
        origin = self.headers.get("Origin", "")
        self.send_response(204)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
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

    def _client_is_loopback(self) -> bool:
        address = str(self.client_address[0])
        return address in {"127.0.0.1", "::1"} or address.startswith("127.")

    def _request_origin(self) -> str:
        scheme = self.headers.get("X-Forwarded-Proto", "http").split(",", 1)[0].strip()
        host = self.headers.get("Host", "").strip()
        return f"{scheme}://{host}" if host else ""

    def _origin_is_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return self._client_is_loopback()
        origin = origin.rstrip("/")
        if origin == self._request_origin().rstrip("/"):
            return True
        configured = {
            value.strip().rstrip("/")
            for value in os.environ.get("AEROLOOP_ALLOWED_ORIGINS", "").split(",")
            if value.strip()
        }
        hostname = (urlsplit(origin).hostname or "").lower()
        return origin in configured or hostname in {"127.0.0.1", "localhost", "::1"}

    def _client_key(self, path: str) -> str:
        # The final X-Forwarded-For value is appended by Railway's edge. A raw
        # client cannot create unlimited limiter buckets by prepending values.
        forwarded = self.headers.get("X-Forwarded-For", "")
        address = forwarded.split(",")[-1].strip() if forwarded else str(self.client_address[0])
        return f"{address}:POST"

    def _rate_limit_ok(self, path: str) -> bool:
        return REQUEST_LIMITER.allow(
            self._client_key(path), RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_S,
        )

    def _has_devin_access(self) -> bool:
        expected = os.environ.get("AEROLOOP_DEMO_TOKEN", "")
        supplied = self.headers.get("Authorization", "")
        if not expected or not supplied.startswith("Bearer "):
            return False
        return hmac.compare_digest(supplied.removeprefix("Bearer ").strip(), expected)

    @staticmethod
    def _uses_devin(request: dict) -> bool:
        return str(request.get("planner", "")).lower() == "devin"

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/mission_view.html")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/health":
            self._send_json(200, {"status": "ok", "service": "aeroloop"})
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/api/capabilities":
            # The UI asks before offering a live mission, so a judge is never
            # given a button that can only fail.
            configured = _devin_is_configured()
            self._send_json(200, {
                "devin_available": configured,
                "devin_requires_access_code": configured,
                "reason": "" if configured else (
                    "Live Devin missions are disabled on this server. "
                    "The verified baseline and recorded Devin mission remain available."
                ),
            })
            return
        if path == "/api/mission/status":
            query = parse_qs(urlsplit(self.path).query)
            job_id = (query.get("job_id") or [""])[0]
            job = mission_job_snapshot(job_id)
            if job is None:
                self._send_json(404, {"ok": False, "reply": "Unknown mission job."})
            else:
                self._send_json(200, job)
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
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise RequestRejected("Invalid Content-Length.", 400) from error
        if length <= 0:
            raise RequestRejected("A JSON request body is required.", 400)
        if length > MAX_REQUEST_BODY_BYTES:
            raise RequestRejected("Request body is too large.", 413)
        try:
            request = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RequestRejected("Request body must be valid JSON.", 400) from error
        if not isinstance(request, dict):
            raise RequestRejected("Request body must be a JSON object.", 400)
        text = request.get("text", "")
        if not isinstance(text, str):
            raise RequestRejected("Mission text must be a string.", 400)
        if len(text) > MAX_REQUEST_TEXT_CHARS:
            raise RequestRejected("Mission text is too long.", 400)
        planner = request.get("planner")
        if planner is not None and (
            not isinstance(planner, str)
            or planner.lower() not in {"baseline", "devin", "rule", "rule_engine"}
        ):
            raise RequestRejected("Unknown planner.", 400)
        seed = request.get("seed")
        if seed is not None and (
            isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 9_999_999
        ):
            raise RequestRejected("Seed must be an integer from 0 to 9999999.", 400)
        max_actions = request.get("max_actions")
        if max_actions is not None and (
            isinstance(max_actions, bool)
            or not isinstance(max_actions, int)
            or not 1 <= max_actions <= 20
        ):
            raise RequestRejected("max_actions must be an integer from 1 to 20.", 400)
        return request

    def _fly(self, request: dict):
        try:
            text = request.get("text")
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

    def _inspect(self, request: dict):
        try:
            text = request.get("text")
            work_order = parse_work_order(text or "")
            planner = _inspection_planner(request)
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

    def _mission(self, request: dict):
        """Run one autonomous simulator v2 mission and return it for replay."""
        try:
            payload = _mission_payload(request)
        except Exception as error:
            self._send_json(500, {"ok": False, "reply": f"Mission failed: {error}"})
            return
        self._send_json(200, payload)

    def _start_mission(self, request: dict):
        try:
            job_id = start_mission_job(request)
        except Exception as error:
            self._send_json(400, {"ok": False, "reply": f"Bad mission request: {error}"})
            return
        self._send_json(202, {
            "ok": True,
            "job_id": job_id,
            "reply": "Mission accepted. Backend progress is now available.",
        })

    def do_POST(self):
        path = urlsplit(self.path).path
        if not self._origin_is_allowed():
            self._send_json(403, {
                "ok": False,
                "reply": "Cross-site requests are not accepted by the flight view.",
            })
            return
        if not self._rate_limit_ok(path):
            self._send_json(429, {
                "ok": False,
                "reply": "Too many requests. Wait before trying again.",
            })
            return
        try:
            request = self._read_json()
        except RequestRejected as error:
            self._bad(str(error), error.status)
            return
        if self._uses_devin(request):
            if not _devin_is_configured():
                self._send_json(503, {
                    "ok": False,
                    "reply": "Live Devin missions are disabled on this server.",
                })
                return
            if not self._has_devin_access():
                self._send_json(401, {
                    "ok": False,
                    "reply": "A valid judge access code is required for live Devin missions.",
                })
                return
        if path == "/api/fly":
            self._fly(request)
        elif path == "/api/inspect":
            self._inspect(request)
        elif path == "/api/mission":
            self._mission(request)
        elif path == "/api/mission/start":
            self._start_mission(request)
        else:
            self._send_json(404, {"ok": False, "reply": "Unknown API endpoint."})


def main():
    parser = argparse.ArgumentParser(description="Serve the local AeroLoop flight view.")
    default_port = int(os.environ.get("PORT", "8765"))
    default_host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    parser.add_argument("--host", default=default_host)
    parser.add_argument("--port", type=int, default=default_port)
    args = parser.parse_args()
    handler = partial(CommandHandler, directory=str(VIZ_DIR))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    display_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
    print(f"Open http://{display_host}:{args.port}/mission_view.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
