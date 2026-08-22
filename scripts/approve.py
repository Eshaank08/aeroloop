"""The single human touch in the pipeline: a post-PASS physical-safety gate.

Runs the verifier one final time, prints the full report, and asks a person to confirm
before the controller would ever be treated as cleared to fly near a real aircraft.

This gate is deliberately placed AFTER verification. No human is involved in writing,
testing, or fixing the controller. A drone operating near a live jet engine is a
physical-safety decision, and that is the only thing a person signs here.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controller import Controller  # noqa: E402
from sim.report import (  # noqa: E402
    ApprovalRefused,
    approve_report,
    build_report,
    check_integrity,
    load_report,
    write_report,
)
from sim.run_verifier import verify  # noqa: E402


def _display_path(path):
    path = Path(path)
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _print_summary(report, artifact_path):
    run = report["run"]
    controller = report["controller"]
    scenarios = report.get("scenarios", [])
    passed = sum(scenario["passed"] for scenario in scenarios)
    commit = controller["git_commit"] or "unknown"
    print("AeroLoop verification artifact")
    print("=" * 32)
    print(f"result           : {report['result']}")
    print(f"pass rate        : {run['pass_rate'] * 100:.1f}% ({passed}/{len(scenarios)})")
    print(f"mean coverage    : {run['mean_coverage'] * 100:.1f}%")
    print(f"total collisions : {run['total_collisions']}")
    print(f"controller sha256: {controller['sha256'][:12]}")
    print(f"git commit       : {commit}")
    print(f"git dirty        : {str(controller['git_dirty']).lower()}")
    print(f"artifact         : {_display_path(artifact_path)}")


def _print_failure_reasons(report):
    run = report["run"]
    thresholds = report["thresholds"]
    if run["pass_rate"] < thresholds["scenario_pass_rate"]:
        print(
            f"failure: pass rate {run['pass_rate'] * 100:.1f}% is below "
            f"{thresholds['scenario_pass_rate'] * 100:.1f}%"
        )
    for scenario in report.get("scenarios", []):
        reasons = []
        if scenario["coverage"] < thresholds["coverage"]:
            reasons.append(
                f"coverage {scenario['coverage'] * 100:.1f}% is below "
                f"{thresholds['coverage'] * 100:.1f}%"
            )
        if scenario["collisions"] != thresholds["collisions"]:
            reasons.append(
                f"collisions {scenario['collisions']} != {thresholds['collisions']}"
            )
        if scenario["elapsed_s"] > thresholds["time_budget_s"]:
            reasons.append(
                f"time {scenario['elapsed_s']:.2f}s exceeds "
                f"{thresholds['time_budget_s']:.1f}s"
            )
        if reasons:
            print(f"failure: seed {scenario['seed']}: {'; '.join(reasons)}")


def _new_report():
    ok, results = verify(Controller, count=30, base_seed=1000, verbose=False)
    report = build_report(ok, results, 30, 1000, "controller.py")
    timestamp = report["generated_at_utc"].replace("-", "").replace(":", "")
    artifact_path = Path("reports") / f"verification_{timestamp}.json"
    write_report(report, artifact_path)
    return report, artifact_path


def _approve_interactively(report, artifact_path):
    answer = input(
        "Type yes to record human approval for this verification artifact: "
    )
    if answer != "yes":
        print("NOT APPROVED. Controller held.")
        return 1
    try:
        approve_report(report)
    except ApprovalRefused as exc:
        print(f"Approval refused: {exc}")
        return 1
    write_report(report, artifact_path)
    print("APPROVED. Controller released for flight operations.")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.report is None:
        report, artifact_path = _new_report()
    else:
        artifact_path = args.report
        report = load_report(artifact_path)
        _print_summary(report, artifact_path)
        if report.get("approval") is not None and not check_integrity(report):
            print("Approval refused: artifact integrity check failed.")
            return 1
        if report["result"] != "PASS":
            _print_failure_reasons(report)
            print("Approval refused: verification result is FAIL.")
            return 1
        if report.get("approval") is not None:
            print("Approval refused: artifact is already approved.")
            return 1
        if args.dry_run:
            return 0
        return _approve_interactively(report, artifact_path)

    _print_summary(report, artifact_path)
    if report["result"] != "PASS":
        _print_failure_reasons(report)
        return 1
    if args.dry_run:
        return 0
    return _approve_interactively(report, artifact_path)


if __name__ == "__main__":
    sys.exit(main())
