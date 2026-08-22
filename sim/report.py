"""Build, persist, approve, and verify verifier result artifacts."""

import copy
import getpass
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sim.limits import DEFAULT_LIMITS
from sim.run_verifier import COVERAGE_THRESHOLD, SCENARIO_PASS_RATE


class ApprovalRefused(Exception):
    """Raised when a verification artifact cannot be approved."""


class ReportAlreadyApproved(ApprovalRefused):
    """Raised when an artifact already contains an approval."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _controller_metadata(controller_path):
    path = Path(controller_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    git_commit = None
    git_dirty = False

    try:
        root = subprocess.check_output(
            ["git", "-C", str(path.parent or Path(".")), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        git_commit = subprocess.check_output(
            ["git", "-C", root, "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty_output = subprocess.check_output(
            ["git", "-C", root, "status", "--porcelain", "--untracked-files=all"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        git_dirty = bool(dirty_output.strip())
    except (OSError, subprocess.CalledProcessError):
        pass

    return {
        "path": str(controller_path),
        "sha256": digest,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
    }


def build_report(ok, results, count, base_seed, controller_path):
    """Turn verifier output into a durable verification artifact dictionary."""
    results = list(results)
    n_pass = sum(result.passed for result in results)
    pass_rate = n_pass / len(results) if results else 0.0
    mean_coverage = (
        sum(result.coverage for result in results) / len(results) if results else 0.0
    )

    return {
        "schema_version": 1,
        "generated_at_utc": _utc_now(),
        "result": "PASS" if ok else "FAIL",
        "controller": _controller_metadata(controller_path),
        "run": {
            "scenarios": count,
            "base_seed": base_seed,
            "pass_rate": pass_rate,
            "mean_coverage": mean_coverage,
            "total_collisions": sum(result.collisions for result in results),
        },
        "thresholds": {
            "coverage": COVERAGE_THRESHOLD,
            "scenario_pass_rate": SCENARIO_PASS_RATE,
            "collisions": 0,
            "time_budget_s": DEFAULT_LIMITS.time_budget_s,
        },
        "scenarios": [
            {
                "seed": result.seed,
                "passed": result.passed,
                "coverage": result.coverage,
                "collisions": result.collisions,
                "elapsed_s": result.elapsed_s,
            }
            for result in results
        ],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "approval": None,
    }


def _serialize_report(report, force_null_approval=False):
    payload = copy.deepcopy(report)
    if force_null_approval:
        payload["approval"] = None
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=False,
            ensure_ascii=False,
        ).encode("utf-8")
        + b"\n"
    )


def write_report(report, path):
    """Write an artifact as stable, human-readable JSON and return its path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_serialize_report(report))
    return path


def load_report(path):
    """Load an artifact dictionary from JSON."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def report_digest(report):
    """Return the signature digest over the artifact with approval set to null."""
    return hashlib.sha256(_serialize_report(report, force_null_approval=True)).hexdigest()


def approve_report(report, approver=None):
    """Add a signed approval block to a passing artifact."""
    if report.get("result") != "PASS":
        raise ApprovalRefused("Only a PASS artifact can be approved.")
    if report.get("approval") is not None:
        raise ReportAlreadyApproved("This artifact is already approved.")

    if approver is None:
        approver = os.environ.get("APPROVER") or getpass.getuser()
    report["approval"] = {
        "approved": True,
        "approver": approver,
        "approved_at_utc": _utc_now(),
        "report_sha256": report_digest(report),
    }
    return report


def check_integrity(report):
    """Return whether an approved artifact still matches its signed contents."""
    approval = report.get("approval")
    if approval is None:
        return True
    if not isinstance(approval, dict):
        return False
    expected = approval.get("report_sha256")
    return isinstance(expected, str) and expected == report_digest(report)
