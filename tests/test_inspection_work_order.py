"""Work-order parsing tests."""

from inspection.work_order import parse_work_order
from sim.aircraft_geometry import DEFAULT_NACELLE


def test_high_wind_does_not_select_dense():
    wo = parse_work_order("inspect top side, high wind seed 1234")
    assert wo.nacelle.per_ring == DEFAULT_NACELLE.per_ring
    assert wo.wind_scale == 2.0
    assert wo.seed == 1234


def test_dense_still_selected():
    wo = parse_work_order("inspect dense, calm seed 1000")
    assert wo.nacelle.rings == 5
    assert wo.nacelle.per_ring == 12
    assert wo.wind_scale == 0.3


def test_narrowbody_and_heavy_wind_independent():
    wo = parse_work_order("inspect narrowbody, heavy wind seed 42")
    assert wo.nacelle.rings == 3
    assert wo.nacelle.axis_end[0] == 3.0
    assert wo.wind_scale == 2.0
    assert wo.seed == 42


def test_top_side_selects_top_waypoints():
    wo = parse_work_order("inspect top side, light wind seed 100")
    assert wo.sector == "Top side"
    assert wo.selected_waypoints is not None
    assert len(wo.selected_waypoints) == 9
    assert all(wp[2] > 0 for wp in wo.selected_waypoints)
    assert wo.selected_waypoint_indexes is not None
    assert len(wo.selected_waypoint_indexes) == 9
    all_waypoints = list(wo.nacelle.waypoints())
    indexes = {all_waypoints.index(wp) for wp in wo.selected_waypoints}
    assert set(wo.selected_waypoint_indexes) == indexes
    assert all(all_waypoints[i][2] > 0 for i in wo.selected_waypoint_indexes)


def test_ring_selection_selects_ring_waypoints():
    wo = parse_work_order("inspect ring 2, calm seed 200")
    assert "Ring 2" in wo.sector
    assert wo.selected_waypoints is not None
    assert len(wo.selected_waypoints) == 8
    assert wo.selected_waypoint_indexes is not None
    assert wo.selected_waypoint_indexes == list(range(8, 16))
    all_waypoints = list(wo.nacelle.waypoints())
    assert all(all_waypoints[i] == wp for i, wp in zip(wo.selected_waypoint_indexes, wo.selected_waypoints))
