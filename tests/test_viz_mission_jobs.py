"""The browser mission route returns immediately and exposes backend progress."""

import time

from viz.server import MISSION_JOBS, MISSION_JOBS_LOCK, mission_job_snapshot, start_mission_job


def test_background_mission_exposes_progress_then_a_verified_replay():
    job_id = start_mission_job({
        "planner": "baseline",
        "text": "inspect the top side, seed 200",
    })

    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        job = mission_job_snapshot(job_id)
        if job["status"] in {"complete", "failed"}:
            break
        time.sleep(0.02)
    else:
        raise AssertionError("background mission did not finish")

    assert job["status"] == "complete"
    assert job["result"]["ok"] is True
    assert job["result"]["artifact"]["final_disposition"] == "PASS"
    stages = [event["stage"] for event in job["history"]]
    assert stages[0] == "preparing"
    assert "waiting_for_planner" in stages
    assert "action_executed" in stages
    assert stages[-1] == "complete"
    assert job["frame_count"] == len(job["result"]["frames"])

    with MISSION_JOBS_LOCK:
        MISSION_JOBS.pop(job_id, None)
