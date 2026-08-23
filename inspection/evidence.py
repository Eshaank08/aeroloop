"""Derive synthetic capture records from an AeroLoop physics trace."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Optional

from inspection.schema import Capture


def nearest_axis_point(nacelle, position: tuple[float, float, float]):
    """Closest point on the nacelle axis segment to `position`."""
    px, py, pz = position
    ax, ay, az = nacelle.axis_start
    bx, by, bz = nacelle.axis_end
    abx, aby, abz = bx - ax, by - ay, bz - az
    apx, apy, apz = px - ax, py - ay, pz - az
    ab_len_sq = abx * abx + aby * aby + abz * abz
    t = 0.0 if ab_len_sq == 0 else (apx * abx + apy * aby + apz * abz) / ab_len_sq
    t = max(0.0, min(1.0, t))
    return (ax + abx * t, ay + aby * t, az + abz * t)


def surface_normal_at_waypoint(nacelle, waypoint: tuple[float, float, float]):
    """Outward radial surface normal at the waypoint, before converting to camera frame."""
    axis_point = nearest_axis_point(nacelle, waypoint)
    dx, dy, dz = waypoint[0] - axis_point[0], waypoint[1] - axis_point[1], waypoint[2] - axis_point[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length == 0:
        return (1.0, 0.0, 0.0)
    return (dx / length, dy / length, dz / length)


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length == 0:
        return (0.0, 0.0, 1.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _camera_boresight(
    nacelle,
    frame: dict,
    waypoint: tuple[float, float, float],
    low_speed_threshold: float = 0.08,
) -> tuple[float, float, float]:
    """Synthetic camera-pose model.

    When the drone is moving, the camera is fixed forward along the velocity vector,
    as a conservative proxy for a body-fixed camera. When the drone is hovering near
    the waypoint, it yaws to face the surface, so the camera looks toward the nacelle
    axis. This is a deliberately synthetic model, not a sensor reading.
    """
    vx, vy, vz = frame["v"]
    speed = math.sqrt(vx * vx + vy * vy + vz * vz)
    position = tuple(frame["p"])
    if speed > low_speed_threshold:
        return _normalize((vx, vy, vz))
    # Hover/capture: camera looks inward, toward the nacelle surface normal direction.
    axis_point = nearest_axis_point(nacelle, position)
    inward = (axis_point[0] - position[0], axis_point[1] - position[1], axis_point[2] - position[2])
    length = math.sqrt(inward[0] ** 2 + inward[1] ** 2 + inward[2] ** 2)
    if length == 0:
        # Fallback toward the waypoint from the drone, if the drone is exactly on axis.
        to_wp = (waypoint[0] - position[0], waypoint[1] - position[1], waypoint[2] - position[2])
        to_wp_length = math.sqrt(to_wp[0] ** 2 + to_wp[1] ** 2 + to_wp[2] ** 2)
        if to_wp_length > 0:
            return (-to_wp[0] / to_wp_length, -to_wp[1] / to_wp_length, -to_wp[2] / to_wp_length)
        return (0.0, 0.0, 1.0)
    return (inward[0] / length, inward[1] / length, inward[2] / length)


def _view_angle(camera: tuple[float, float, float], inward_normal: tuple[float, float, float]) -> float:
    """Angle between the camera boresight and the inward surface normal, in degrees."""
    dot = max(-1.0, min(1.0, _dot(camera, inward_normal)))
    # A camera looking directly at the surface has dot = 1, so angle = 0.
    # A camera pointing directly away has dot = -1, so angle = 180.
    return math.degrees(math.acos(dot))


def _hash_capture(capture: Capture) -> str:
    """Stable digest of every field except the hash field itself."""
    payload = capture_to_dict(capture)
    payload.pop("sha256", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def capture_to_dict(capture: Capture) -> dict:
    """Convert a capture record to a JSON-serialisable dict."""
    return {
        "schema_version": capture.schema_version,
        "capture_id": capture.capture_id,
        "source": capture.source,
        "synthetic": capture.synthetic,
        "waypoint_index": capture.waypoint_index,
        "waypoint": list(capture.waypoint),
        "captured_at_s": capture.captured_at_s,
        "standoff_m": capture.standoff_m,
        "view_angle_deg": capture.view_angle_deg,
        "dwell_s": capture.dwell_s,
        "speed_mps": capture.speed_mps,
        "wind_mps": capture.wind_mps,
        "clearance_m": capture.clearance_m,
        "camera": list(capture.camera),
        "trace_frame_indexes": list(capture.trace_frame_indexes),
        "sha256": capture.sha256,
    }


def _infer_dt(frames: list[dict]) -> float:
    if len(frames) >= 2:
        return max(frames[1]["t"] - frames[0]["t"], 1e-6)
    return 0.02


def derive_captures(
    trace: dict,
    nacelle,
    capture_id_prefix: str = "cap",
    seed: Optional[int] = None,
) -> list[Capture]:
    """Produce one synthetic capture record for every target waypoint."""
    frames = trace.get("frames", [])
    waypoints = trace.get("waypoints", []) or nacelle.waypoints()
    if not waypoints:
        return []

    dt = _infer_dt(frames)
    tolerance = nacelle.waypoint_tolerance
    captures = []

    global_indexes = trace.get("waypoint_indexes")
    if global_indexes is None or len(global_indexes) != len(waypoints):
        global_indexes = list(range(len(waypoints)))

    for local_i, (waypoint, index) in enumerate(zip(waypoints, global_indexes)):
        frame_indexes = [
            i for i, frame in enumerate(frames)
            if math.dist(frame["p"], waypoint) <= tolerance
        ]

        if not frame_indexes:
            capture = Capture(
                capture_id=f"{capture_id_prefix}-missing-{index:03d}-{seed if seed is not None else 0}",
                waypoint_index=index,
                waypoint=waypoint,
                source="synthetic_trace",
                synthetic=True,
                trace_frame_indexes=[],
                sha256="",
            )
            capture = Capture(**{**capture.__dict__, "sha256": _hash_capture(capture)})
            captures.append(capture)
            continue

        inner_frames = [frames[i] for i in frame_indexes]
        inward_normal = tuple(-v for v in surface_normal_at_waypoint(nacelle, waypoint))

        camera_choices = [
            _camera_boresight(nacelle, f, waypoint) for f in inner_frames
        ]
        view_angles = [_view_angle(c, inward_normal) for c in camera_choices]

        speeds = [
            math.sqrt(f["v"][0] ** 2 + f["v"][1] ** 2 + f["v"][2] ** 2)
            for f in inner_frames
        ]
        wind_mags = [
            math.sqrt(f["wind"][0] ** 2 + f["wind"][1] ** 2 + f["wind"][2] ** 2)
            for f in inner_frames
        ]
        clearances = [f["clearance"] for f in inner_frames]
        standoffs = [
            nacelle.distance_to_surface(f["p"]) - nacelle.radius
            for f in inner_frames
        ]

        # A capture must be a continuous visit, not a sum of disconnected passes.
        groups = [[0]]
        for k in range(1, len(frame_indexes)):
            if frame_indexes[k] == frame_indexes[k - 1] + 1:
                groups[-1].append(k)
            else:
                groups.append([k])

        def _window_score(group):
            return (len(group), -min(view_angles[i] for i in group))

        best_group = max(groups, key=_window_score)
        best_inner = [inner_frames[i] for i in best_group]
        best_indexes = [frame_indexes[i] for i in best_group]
        first_frame = best_inner[0]
        last_frame = best_inner[-1]
        best_view_i = min(best_group, key=lambda i: view_angles[i])
        capture_camera = camera_choices[best_view_i]

        capture = Capture(
            capture_id=f"{capture_id_prefix}-wp{index:03d}-{seed if seed is not None else 0}",
            source="synthetic_trace",
            synthetic=True,
            waypoint_index=index,
            waypoint=waypoint,
            captured_at_s=first_frame["t"],
            standoff_m=sum(standoffs[i] for i in best_group) / len(best_group),
            view_angle_deg=min(view_angles[i] for i in best_group),
            dwell_s=(last_frame["t"] - first_frame["t"]) + dt,
            speed_mps=sum(speeds[i] for i in best_group) / len(best_group),
            wind_mps=max(wind_mags[i] for i in best_group),
            clearance_m=min(clearances[i] for i in best_group),
            camera=capture_camera,
            trace_frame_indexes=best_indexes,
            sha256="",
        )
        capture = Capture(**{**capture.__dict__, "sha256": _hash_capture(capture)})
        captures.append(capture)

    return captures


def capture_from_dict(data: dict) -> Capture:
    return Capture(
        schema_version=data.get("schema_version", 1),
        capture_id=data.get("capture_id", ""),
        source=data.get("source", "synthetic_trace"),
        synthetic=data.get("synthetic", True),
        waypoint_index=data.get("waypoint_index", -1),
        waypoint=tuple(data.get("waypoint", (0.0, 0.0, 0.0))),
        captured_at_s=data.get("captured_at_s"),
        standoff_m=data.get("standoff_m"),
        view_angle_deg=data.get("view_angle_deg"),
        dwell_s=data.get("dwell_s"),
        speed_mps=data.get("speed_mps"),
        wind_mps=data.get("wind_mps"),
        clearance_m=data.get("clearance_m"),
        camera=tuple(data.get("camera", (0.0, 0.0, 1.0))),
        trace_frame_indexes=data.get("trace_frame_indexes", []),
        sha256=data.get("sha256", ""),
    )
