"""Cloud HTTP boundary tests: abuse brakes must fail before mission execution."""

from functools import partial
import http.client
import json
from pathlib import Path
from threading import Thread

import pytest

import viz.server as server_module


@pytest.fixture
def http_server(monkeypatch):
    monkeypatch.delenv("AEROLOOP_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("AEROLOOP_DEMO_TOKEN", raising=False)
    monkeypatch.delenv("DEVIN_API_KEY", raising=False)
    monkeypatch.delenv("DEVIN_ORG_ID", raising=False)
    monkeypatch.delenv("AEROLOOP_DEVIN_MAX_ACU", raising=False)
    server_module.REQUEST_LIMITER.clear()

    handler = partial(server_module.CommandHandler, directory=str(server_module.VIZ_DIR))
    instance = server_module.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance.server_address
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)
        server_module.REQUEST_LIMITER.clear()


def request(address, method, path, *, payload=None, headers=None):
    connection = http.client.HTTPConnection(*address, timeout=5)
    body = None if payload is None else json.dumps(payload).encode()
    request_headers = dict(headers or {})
    if body is not None:
        request_headers.setdefault("Content-Type", "application/json")
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    content = response.read()
    result = (response.status, dict(response.getheaders()), content)
    connection.close()
    return result


def same_origin(address):
    return {"Origin": f"http://{address[0]}:{address[1]}"}


def test_root_health_and_security_headers_are_cloud_ready(http_server):
    status, headers, _ = request(http_server, "GET", "/")
    assert status == 302
    assert headers["Location"] == "/mission_view.html"

    status, headers, body = request(http_server, "GET", "/health")
    assert status == 200
    assert json.loads(body) == {"status": "ok", "service": "aeroloop"}
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "connect-src 'self' blob:" in headers["Content-Security-Policy"]
    assert "worker-src 'self' blob:" in headers["Content-Security-Policy"]
    assert "Access-Control-Allow-Origin" not in headers


def test_cross_site_post_is_rejected_before_work_runs(http_server, monkeypatch):
    called = False

    def unexpected(_request):
        nonlocal called
        called = True
        return "not-used"

    monkeypatch.setattr(server_module, "start_mission_job", unexpected)
    status, _, body = request(
        http_server,
        "POST",
        "/api/mission/start",
        payload={"planner": "baseline", "text": "inspect the top"},
        headers={"Origin": "https://attacker.example"},
    )
    assert status == 403
    assert json.loads(body)["ok"] is False
    assert called is False


def test_oversized_and_invalid_request_bodies_are_rejected(http_server):
    connection = http.client.HTTPConnection(*http_server, timeout=5)
    body = b"x" * (server_module.MAX_REQUEST_BODY_BYTES + 1)
    connection.request(
        "POST",
        "/api/mission/start",
        body=body,
        headers={**same_origin(http_server), "Content-Type": "application/json"},
    )
    response = connection.getresponse()
    assert response.status == 413
    assert json.loads(response.read())["ok"] is False
    connection.close()

    status, _, body = request(
        http_server,
        "POST",
        "/api/mission/start",
        payload={"planner": "baseline", "text": "x" * 501},
        headers=same_origin(http_server),
    )
    assert status == 400
    assert "too long" in json.loads(body)["reply"]

    status, _, body = request(
        http_server,
        "POST",
        "/api/mission/start",
        payload={"planner": "baseline", "text": "inspect", "max_actions": 1_000_000},
        headers=same_origin(http_server),
    )
    assert status == 400
    assert "max_actions" in json.loads(body)["reply"]


def test_live_devin_requires_constant_time_bearer_check(http_server, monkeypatch):
    monkeypatch.setenv("AEROLOOP_DEMO_TOKEN", "judge-secret")
    monkeypatch.setenv("DEVIN_API_KEY", "not-a-real-key")
    monkeypatch.setenv("DEVIN_ORG_ID", "not-a-real-org")
    monkeypatch.setenv("AEROLOOP_DEVIN_MAX_ACU", "5")
    monkeypatch.setattr(server_module, "start_mission_job", lambda _request: "job-123")
    payload = {"planner": "devin", "text": "inspect the top"}

    status, _, body = request(
        http_server, "POST", "/api/mission/start",
        payload=payload, headers=same_origin(http_server),
    )
    assert status == 401
    assert "access code" in json.loads(body)["reply"]

    status, _, body = request(
        http_server, "POST", "/api/mission/start", payload=payload,
        headers={**same_origin(http_server), "Authorization": "Bearer judge-secret"},
    )
    assert status == 202
    assert json.loads(body)["job_id"] == "job-123"


def test_rate_limiter_and_concurrency_limit_are_bounded(monkeypatch):
    now = [100.0]
    limiter = server_module.SlidingWindowLimiter(clock=lambda: now[0])
    assert limiter.allow("client", 2, 60)
    assert limiter.allow("client", 2, 60)
    assert not limiter.allow("client", 2, 60)
    now[0] = 161.0
    assert limiter.allow("client", 2, 60)

    with server_module.MISSION_JOBS_LOCK:
        original = dict(server_module.MISSION_JOBS)
        server_module.MISSION_JOBS.clear()
        for index in range(server_module.MAX_CONCURRENT_MISSIONS):
            server_module.MISSION_JOBS[str(index)] = {
                "status": "running", "created_at": float(index),
            }
    try:
        with pytest.raises(RuntimeError, match="capacity is full"):
            server_module.start_mission_job({"planner": "baseline", "text": "inspect"})
    finally:
        with server_module.MISSION_JOBS_LOCK:
            server_module.MISSION_JOBS.clear()
            server_module.MISSION_JOBS.update(original)


def test_railway_config_has_explicit_start_and_healthcheck():
    config = json.loads(Path("railway.json").read_text())
    assert config["build"]["builder"] == "RAILPACK"
    assert config["deploy"]["startCommand"] == "python -m viz.server"
    assert config["deploy"]["healthcheckPath"] == "/health"
