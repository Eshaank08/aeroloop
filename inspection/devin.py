"""Devin API client and structured re-capture planner.

The client is deliberately small and standard-library only. Tests inject a fake
transport; live missions read credentials from the server environment.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
from typing import Any, Callable
import urllib.error
import urllib.request

from inspection.schema import QualityResult, RequestedCapture


API_BASE = "https://api.devin.ai/v3"

TERMINAL_FAILURE_DETAILS = {
    "error",
    "inactivity",
    "no_quota_allocation",
    "org_usage_limit_exceeded",
    "out_of_credits",
    "out_of_quota",
    "payment_declined",
    "total_session_limit_exceeded",
    "usage_limit_exceeded",
    "user_request",
    "user_usage_limit_exceeded",
    "waiting_for_approval",
    "waiting_for_user",
}

RECAPTURE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["requests"],
    "properties": {
        "requests": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["request_id", "waypoint_indexes", "primitive", "reason_codes", "constraints"],
                "properties": {
                    "request_id": {"type": "string", "minLength": 1},
                    "waypoint_indexes": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0},
                    },
                    "primitive": {
                        "type": "string",
                        "enum": ["capture_closeup", "capture_orbit", "quiet_hover", "return_home"],
                    },
                    "reason_codes": {"type": "array", "items": {"type": "string"}},
                    "constraints": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "max_speed_mps": {"type": "number", "exclusiveMinimum": 0},
                            "minimum_dwell_s": {"type": "number", "exclusiveMinimum": 0},
                        },
                    },
                },
            },
        }
    },
}


class DevinError(RuntimeError):
    """Base error for fail-closed Devin mission planning."""


class DevinAPIError(DevinError):
    """The remote session could not be created or completed."""


class DevinOutputError(DevinError):
    """Devin returned structured output that does not match the local contract."""


def _http_json(method: str, url: str, key: str, payload: dict | None, timeout_s: float) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {key}")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise DevinAPIError(f"Devin API returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DevinAPIError("Devin API request failed") from exc
    except json.JSONDecodeError as exc:
        raise DevinAPIError("Devin API returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise DevinAPIError("Devin API returned a non-object response")
    return result


@dataclass(frozen=True)
class DevinRun:
    session_id: str
    url: str
    status: str
    structured_output: dict


class DevinClient:
    """Create and poll a Devin v3 session for one structured decision."""

    def __init__(
        self,
        api_key: str,
        org_id: str,
        *,
        api_base: str = API_BASE,
        poll_interval_s: float = 10.0,
        timeout_s: float = 180.0,
        request_timeout_s: float = 30.0,
        transport: Callable[[str, str, str, dict | None, float], dict] = _http_json,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not api_key or not org_id:
            raise ValueError("DEVIN_API_KEY and DEVIN_ORG_ID are required for Devin mode")
        self.api_key = api_key
        self.org_id = org_id
        self.api_base = api_base.rstrip("/")
        self.poll_interval_s = poll_interval_s
        self.timeout_s = timeout_s
        self.request_timeout_s = request_timeout_s
        self.transport = transport
        self.sleeper = sleeper
        self.clock = clock

    @classmethod
    def from_env(cls, **kwargs) -> "DevinClient":
        return cls(
            os.environ.get("DEVIN_API_KEY", ""),
            os.environ.get("DEVIN_ORG_ID", ""),
            **kwargs,
        )

    @property
    def sessions_url(self) -> str:
        return f"{self.api_base}/organizations/{self.org_id}/sessions"

    def run_structured(
        self,
        prompt: str,
        schema: dict,
        *,
        title: str,
        tags: list[str] | None = None,
        max_acu_limit: int | None = None,
    ) -> DevinRun:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "title": title,
            "resumable": False,
            "structured_output_required": True,
            "structured_output_schema": schema,
            "tags": tags or ["aeroloop", "inspection-runtime"],
        }
        if max_acu_limit is not None:
            payload["max_acu_limit"] = max_acu_limit

        session = self.transport("POST", self.sessions_url, self.api_key, payload, self.request_timeout_s)
        session_id = session.get("session_id") or session.get("id")
        if not isinstance(session_id, str) or not session_id:
            raise DevinAPIError("Devin did not return a session ID")

        session_url = session.get("url") if isinstance(session.get("url"), str) else ""
        status_url = f"{self.sessions_url}/{session_id}"
        deadline = self.clock() + self.timeout_s

        while True:
            status = str(session.get("status") or "unknown")
            detail = str(session.get("status_detail") or "")
            output = session.get("structured_output")
            if status == "exit" or detail == "finished":
                if isinstance(output, dict):
                    return DevinRun(session_id, session_url, status, output)
                raise DevinAPIError("Devin session finished without structured output")
            if status in {"error", "suspended"} or detail in TERMINAL_FAILURE_DETAILS:
                raise DevinAPIError(f"Devin session stopped without valid output ({detail or status})")
            if self.clock() >= deadline:
                raise DevinAPIError("Devin session timed out")
            self.sleeper(self.poll_interval_s)
            session = self.transport("GET", status_url, self.api_key, None, self.request_timeout_s)


def _quality_to_dict(result: QualityResult) -> dict:
    return {
        "capture_id": result.capture_id,
        "status": result.status,
        "score": result.score,
        "reasons": list(result.reasons),
        "threshold_version": result.threshold_version,
    }


class DevinRecapturePlanner:
    """Ask Devin to choose follow-up primitives from structured evidence gaps."""

    def __init__(self, client: DevinClient, *, max_acu_limit: int | None = None):
        self.client = client
        self.max_acu_limit = max_acu_limit
        self.metadata: dict = {"provider": "devin", "mode": "structured_output"}

    def plan(self, gaps: list[QualityResult], context: dict) -> list[RequestedCapture]:
        evidence = [_quality_to_dict(gap) for gap in gaps]
        allowed_indexes = list(context.get("allowed_waypoint_indexes", []))
        prompt_payload = {
            "role": "AeroLoop autonomous inspection mission planner",
            "instruction": (
                "Choose only the minimum safe follow-up captures needed to address the evidence gaps. "
                "Use only allowed waypoint indexes and primitives. Return no requests when evidence is complete. "
                "Do not output coordinates, motor commands, or prose outside structured output."
            ),
            "work_order": context.get("work_order", ""),
            "seed": context.get("seed", 0),
            "allowed_waypoint_indexes": allowed_indexes,
            "allowed_primitives": ["capture_closeup", "capture_orbit", "quiet_hover", "return_home"],
            "evidence_gaps": evidence,
        }
        run = self.client.run_structured(
            json.dumps(prompt_payload, sort_keys=True),
            RECAPTURE_SCHEMA,
            title=f"AeroLoop inspection decision seed {context.get('seed', 0)}",
            max_acu_limit=self.max_acu_limit,
        )
        self.metadata = {
            "provider": "devin",
            "mode": "structured_output",
            "session_id": run.session_id,
            "session_url": run.url,
            "status": run.status,
        }
        return self._parse_requests(run.structured_output)

    @staticmethod
    def _parse_requests(output: dict) -> list[RequestedCapture]:
        raw_requests = output.get("requests")
        if not isinstance(raw_requests, list):
            raise DevinOutputError("structured output must contain a requests array")
        requests = []
        for raw in raw_requests:
            if not isinstance(raw, dict):
                raise DevinOutputError("each Devin request must be an object")
            request_id = raw.get("request_id")
            indexes = raw.get("waypoint_indexes")
            primitive = raw.get("primitive")
            reasons = raw.get("reason_codes")
            constraints = raw.get("constraints")
            if not isinstance(request_id, str) or not request_id:
                raise DevinOutputError("request_id must be a non-empty string")
            if not isinstance(indexes, list) or not all(type(index) is int for index in indexes):
                raise DevinOutputError("waypoint_indexes must be an integer array")
            if not isinstance(primitive, str):
                raise DevinOutputError("primitive must be a string")
            if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
                raise DevinOutputError("reason_codes must be a string array")
            if not isinstance(constraints, dict):
                raise DevinOutputError("constraints must be an object")
            requests.append(RequestedCapture(
                request_id=request_id,
                waypoint_indexes=indexes,
                primitive=primitive,
                reason_codes=reasons,
                constraints=constraints,
                requested_by="devin",
            ))
        return requests
