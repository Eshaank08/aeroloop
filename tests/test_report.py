import json

import pytest

from sim.report import (
    ApprovalRefused,
    approve_report,
    build_report,
    check_integrity,
    load_report,
    report_digest,
    write_report,
)
from sim.run_verifier import ScenarioResult


def _results():
    return [
        ScenarioResult(1000, 1.0, 0, 33.5, 120.0),
        ScenarioResult(1001, 0.96, 0, 34.0, 120.0),
    ]


def _report(tmp_path):
    controller_path = tmp_path / "controller.py"
    controller_path.write_text("class Controller: pass\n", encoding="utf-8")
    return build_report(True, _results(), 2, 1000, controller_path)


def test_report_round_trip_has_exact_schema(tmp_path):
    report = _report(tmp_path)
    path = tmp_path / "reports" / "verification.json"

    assert write_report(report, path) == path
    assert load_report(path) == report
    assert json.loads(path.read_text(encoding="utf-8")) == report
    assert set(report) == {
        "schema_version",
        "generated_at_utc",
        "result",
        "controller",
        "run",
        "thresholds",
        "scenarios",
        "environment",
        "approval",
    }
    assert set(report["controller"]) == {
        "path",
        "sha256",
        "git_commit",
        "git_dirty",
    }
    assert set(report["run"]) == {
        "scenarios",
        "base_seed",
        "pass_rate",
        "mean_coverage",
        "total_collisions",
    }
    assert set(report["thresholds"]) == {
        "coverage",
        "scenario_pass_rate",
        "collisions",
        "time_budget_s",
    }
    assert set(report["scenarios"][0]) == {
        "seed",
        "passed",
        "coverage",
        "collisions",
        "elapsed_s",
    }
    assert set(report["environment"]) == {"python", "platform"}


def test_fail_artifact_cannot_be_approved(tmp_path):
    report = _report(tmp_path)
    report["result"] = "FAIL"

    with pytest.raises(ApprovalRefused):
        approve_report(report)
    assert report["approval"] is None


def test_approval_uses_approver_environment(monkeypatch, tmp_path):
    report = _report(tmp_path)
    monkeypatch.setenv("APPROVER", "safety-reviewer")

    approve_report(report)

    assert report["approval"]["approved"] is True
    assert report["approval"]["approver"] == "safety-reviewer"
    assert report["approval"]["approved_at_utc"].endswith("Z")
    assert report["approval"]["report_sha256"] == report_digest(report)
    assert check_integrity(report)


def test_tampering_breaks_signed_digest(tmp_path):
    report = _report(tmp_path)
    original_digest = report_digest(report)
    approve_report(report)
    assert report["approval"]["report_sha256"] == original_digest
    assert check_integrity(report)

    report["run"]["pass_rate"] = 0.5
    assert not check_integrity(report)
