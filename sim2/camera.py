"""Camera inspection gate for simulator v2."""

import math
from dataclasses import dataclass


inspection_tolerance = 0.5
camera_fov_half_angle = math.radians(60.0)
max_blur_rate = 1.5
max_blur_speed = 2.5


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _norm(value):
    return math.sqrt(_dot(value, value))


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def _scale(value, scalar):
    return tuple(component * scalar for component in value)


def closest_point_on_surface(nacelle, position):
    """Return the radial projection of position onto the capped nacelle surface."""
    axis = _sub(nacelle.axis_end, nacelle.axis_start)
    axis_length_sq = _dot(axis, axis)
    from_start = _sub(position, nacelle.axis_start)
    axis_direction = None
    if axis_length_sq == 0.0:
        center = nacelle.axis_start
    else:
        axis_direction = _scale(axis, 1.0 / math.sqrt(axis_length_sq))
        projection = max(0.0, min(1.0, _dot(from_start, axis) / axis_length_sq))
        center = _add(nacelle.axis_start, _scale(axis, projection))

    radial = _sub(position, center)
    if axis_direction is not None and (projection <= 0.0 or projection >= 1.0):
        axial_component = _scale(axis_direction, _dot(radial, axis_direction))
        radial = _sub(radial, axial_component)
    radial_length = _norm(radial)
    if radial_length <= 1e-15:
        if axis_length_sq == 0.0:
            radial_direction = (0.0, 1.0, 0.0)
        else:
            basis = (1.0, 0.0, 0.0)
            if abs(_dot(axis_direction, basis)) > 0.9:
                basis = (0.0, 1.0, 0.0)
            radial_direction = _cross(axis_direction, basis)
            radial_direction = _scale(radial_direction, 1.0 / _norm(radial_direction))
    else:
        radial_direction = _scale(radial, 1.0 / radial_length)
    return _add(center, _scale(radial_direction, nacelle.radius))


@dataclass(frozen=True)
class CameraGateResult:
    """Individual camera gate conditions for one waypoint and one tick."""

    inspected: bool
    within_tolerance: bool
    aimed: bool
    steady: bool


def camera_gate(waypoint, state, nacelle):
    """Evaluate distance, aim, and steadiness for one waypoint."""
    within_tolerance = _norm(_sub(state.position, waypoint)) <= inspection_tolerance
    surface_point = closest_point_on_surface(nacelle, state.position)
    target = _sub(surface_point, state.position)
    camera_dir = state.camera_dir
    target_norm = _norm(target)
    camera_norm = _norm(camera_dir)
    if target_norm == 0.0 or camera_norm == 0.0:
        aimed = False
    else:
        cosine = _dot(camera_dir, target) / (camera_norm * target_norm)
        cosine = max(-1.0, min(1.0, cosine))
        aimed = math.acos(cosine) <= camera_fov_half_angle
    steady = (
        _norm(state.body_rates) <= max_blur_rate
        and _norm(state.velocity) <= max_blur_speed
    )
    return CameraGateResult(
        inspected=within_tolerance and aimed and steady,
        within_tolerance=within_tolerance,
        aimed=aimed,
        steady=steady,
    )
