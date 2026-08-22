"""Adaptive runner integration tests."""

from inspection.adaptive import AdaptiveRunner
from inspection.quality import QualityOracle
from inspection.work_order import parse_work_order


def test_sector_inspection_keeps_global_indexes():
    """Selected waypoints must keep their global nacelle indexes through re-capture."""
    wo = parse_work_order("inspect top side, heavy wind seed 606076")
    runner = AdaptiveRunner(oracle=QualityOracle())
    result = runner.run(
        wo.label,
        wo.nacelle,
        wo.limits,
        seed=wo.seed,
        wind_scale=wo.wind_scale,
        selected_waypoints=wo.selected_waypoints,
        selected_waypoint_indexes=wo.selected_waypoint_indexes,
    )
    all_waypoints = list(wo.nacelle.waypoints())
    selected_indexes = set(wo.selected_waypoint_indexes)

    for capture in result.initial.captures:
        assert capture.waypoint_index in selected_indexes, "initial capture used a non-sector index"
        assert capture.synthetic is True

    for request in result.accepted:
        for idx in request.waypoint_indexes:
            assert idx in selected_indexes, "re-capture requested a non-sector global index"
            assert all_waypoints[idx] in wo.selected_waypoints, "re-capture points to the wrong nacelle waypoint"

    if result.followup_result:
        for capture in result.followup_result.captures:
            if capture.capture_id.startswith("followup-blank"):
                continue
            assert capture.waypoint_index in selected_indexes, "follow-up capture used a non-sector index"
