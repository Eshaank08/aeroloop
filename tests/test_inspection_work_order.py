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
