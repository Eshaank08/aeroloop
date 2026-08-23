"""Construct, approve, and verify the integrity of an inspection artifact."""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from inspection.schema import (
    DISPOSITION_APPROVED,
    DISPOSITION_PASS,
    InspectionArtifact,
)
from inspection.quality import DEFAULT_THRESHOLDS
from sim.report import _controller_metadata


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _trace_digest(trace: dict) -> str:
    return hashlib.sha256(_to_canonical(trace).encode("utf-8")).hexdigest()


def _summarize_trace(trace: dict) -> dict:
    return {
        "digest": _trace_digest(trace),
        "seed": trace.get("seed"),
        "start_time": trace.get("start_time", 0.0),
        "coverage": trace.get("coverage"),
        "collisions": trace.get("collisions"),
        "elapsed_s": trace.get("elapsed_s"),
        "frames": len(trace.get("frames", [])),
    }


def build_artifact(
    result,
    controller_path: str = "controller.py",
    nacelle=None,
    limits=None,
) -> dict:
    """Turn an AdaptiveResult into a durable inspection artifact dictionary."""
    from inspection.schema import (
        capture_to_dict,
        quality_to_dict,
        request_to_dict,
    )

    initial_trace = result.initial.trace
    followup = result.followup_result.trace if result.followup_result else {"frames": []}

    nacelle = nacelle or {}
    limits = limits or {}

    nacelle_dict = {
        "axis_start": list(getattr(nacelle, "axis_start", (0.0, 0.0, 0.0))),
        "axis_end": list(getattr(nacelle, "axis_end", (4.5, 0.0, 0.0))),
        "radius": getattr(nacelle, "radius", 1.6),
        "safety_margin": getattr(nacelle, "safety_margin", 0.5),
        "inspection_radius": getattr(nacelle, "inspection_radius", 3.0),
        "rings": getattr(nacelle, "rings", 3),
        "per_ring": getattr(nacelle, "per_ring", 8),
        "waypoint_tolerance": getattr(nacelle, "waypoint_tolerance", 0.4),
    }

    limits_dict = {
        "max_accel": getattr(limits, "max_accel", 6.0),
        "max_speed": getattr(limits, "max_speed", 4.0),
        "time_budget_s": getattr(limits, "time_budget_s", 120.0),
        "dt": getattr(limits, "dt", 0.02),
    }

    controller_meta = _controller_metadata(controller_path)

    requested_dicts = [request_to_dict(r) for r in result.requested]
    accepted_dicts = [request_to_dict(r) for r in result.accepted]
    final_captures = [capture_to_dict(c) for c in result.final_captures]
    final_quality = [quality_to_dict(q) for q in result.final_quality]
    gaps = [quality_to_dict(q) for q in result.gaps]

    followup_summaries = []
    for leg in result.followup_legs:
        followup_summaries.append(_summarize_trace(leg))

    policy_decisions = []
    for request_dict, accepted in zip(requested_dicts, [r in result.accepted for r in result.requested]):
        policy_decisions.append({
            "request_id": request_dict["request_id"],
            "primitive": request_dict["primitive"],
            "waypoint_indexes": request_dict["waypoint_indexes"],
            "decision": "accepted" if accepted else "rejected",
        })
    for reason in result.policy_violations:
        policy_decisions.append({"decision": "rejected", "reason": reason})

    artifact = InspectionArtifact(
        synthetic=True,
        generated_at_utc=_utc_now(),
        work_order=result.work_order,
        seed=result.seed,
        wind_scale=result.wind_scale,
        nacelle=nacelle_dict,
        limits=limits_dict,
        controller=controller_meta,
        threshold_version=result.threshold_version,
        threshold_values=result.threshold_values or dict(DEFAULT_THRESHOLDS),
        policy_version="allow-list-v1",
        initial_trace_digest=_trace_digest(initial_trace),
        followup_trace_digest=_trace_digest(followup),
        captures=final_captures,
        quality=final_quality,
        gaps=gaps,
        requested_captures=requested_dicts,
        planner_record={
            "planner": result.planner,
            "metadata": result.planner_metadata,
            "failed": result.planner_failed,
            "input_gap_count": len(gaps),
            "raw_requests": requested_dicts,
            "validated_requests": accepted_dicts,
            "violations": result.policy_violations,
        },
        policy_decisions=policy_decisions,
        followup_results=followup_summaries,
        final_disposition=result.final_disposition,
        approval=None,
    )

    artifact_dict = artifact_to_dict(artifact)
    artifact_dict["integrity_digest"] = artifact_digest(artifact_dict)
    return artifact_dict


def artifact_to_dict(artifact: InspectionArtifact) -> dict:
    return {
        "schema_version": artifact.schema_version,
        "synthetic": artifact.synthetic,
        "generated_at_utc": artifact.generated_at_utc,
        "work_order": artifact.work_order,
        "seed": artifact.seed,
        "wind_scale": artifact.wind_scale,
        "nacelle": artifact.nacelle,
        "limits": artifact.limits,
        "controller": artifact.controller,
        "threshold_version": artifact.threshold_version,
        "threshold_values": artifact.threshold_values,
        "policy_version": artifact.policy_version,
        "initial_trace_digest": artifact.initial_trace_digest,
        "followup_trace_digest": artifact.followup_trace_digest,
        "captures": artifact.captures,
        "quality": artifact.quality,
        "gaps": artifact.gaps,
        "requested_captures": artifact.requested_captures,
        "planner_record": artifact.planner_record,
        "policy_decisions": artifact.policy_decisions,
        "followup_results": artifact.followup_results,
        "final_disposition": artifact.final_disposition,
        "approval": artifact.approval,
        "integrity_digest": artifact.integrity_digest,
    }


def artifact_digest(artifact: dict) -> str:
    """Canonical digest of artifact content.

    The integrity_digest and the approval block's own digest are wiped so the
    digest is not self-referential. Everything else, including generated_at_utc
    and the full approval block, is covered, so any post-approval mutation is
    detectable.
    """
    payload = dict(artifact)
    payload["integrity_digest"] = ""
    approval = payload.get("approval")
    if isinstance(approval, dict):
        approval = dict(approval)
        approval["artifact_digest"] = ""
        payload["approval"] = approval
    return hashlib.sha256(_to_canonical(payload).encode("utf-8")).hexdigest()


def check_artifact_integrity(artifact: dict) -> bool:
    """Return True if the artifact has not been mutated since its digest was minted."""
    expected = artifact.get("integrity_digest")
    return isinstance(expected, str) and expected == artifact_digest(artifact)


def check_approval_integrity(artifact: dict) -> bool:
    """Return True if the approval block still matches the approved artifact."""
    approval = artifact.get("approval")
    if approval is None:
        return True
    if not isinstance(approval, dict):
        return False
    if artifact.get("final_disposition") != DISPOSITION_APPROVED:
        return False
    expected = approval.get("artifact_digest")
    return isinstance(expected, str) and expected == artifact_digest(artifact)


def approve_artifact(artifact: dict, approver: str | None = None) -> dict:
    """Add a human approval block to a passing artifact."""
    if artifact.get("final_disposition") != DISPOSITION_PASS:
        raise ValueError("Only a PASS artifact can be approved")
    if artifact.get("approval") is not None:
        raise ValueError("Artifact is already approved")
    if not check_artifact_integrity(artifact):
        raise ValueError("Artifact integrity digest mismatch; the artifact has been tampered with")

    if approver is None:
        approver = os.environ.get("APPROVER") or getpass.getuser()

    artifact["final_disposition"] = DISPOSITION_APPROVED
    artifact["approval"] = {
        "approved": True,
        "approver": approver,
        "approved_at_utc": _utc_now(),
    }
    # The digest is computed after the approval block is present, but with the
    # approval's own digest wiped so it is not self-referential.
    artifact["approval"]["artifact_digest"] = artifact_digest(artifact)
    # integrity_digest covers the same content and is updated after approval.
    artifact["integrity_digest"] = artifact_digest(artifact)
    return artifact
