"""Flight controller for autonomous jet engine nacelle inspection.

Strategy
--------
* Visit the inspection waypoints in a snake order (ring by ring along the nacelle,
  reversing the angular direction on every ring) so that consecutive targets are
  always neighbours on the inspection cylinder. Every chord of that path stays
  clear of the keep-out volume.
* Track the active waypoint with a cascaded position/velocity controller and a
  feed-forward estimate of the wind, recovered from the observed acceleration.
  Wind can momentarily exceed the drone's own control authority, so cancelling
  the steady part of it is what keeps the tracking error small.
* A radial barrier dominates the command whenever the drone drifts towards the
  nacelle: it pushes outward and kills the inward velocity component well before
  the keep-out surface is reached.
"""

import math


def _norm(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _clamp_mag(v, max_mag):
    mag = _norm(v)
    if mag <= max_mag or mag == 0.0:
        return v
    return _scale(v, max_mag / mag)


class Controller:
    # tracking gains
    KP = 1.6            # position error -> desired velocity
    KV = 5.0            # velocity error -> acceleration
    CRUISE_SPEED = 2.6  # m/s along the inspection path

    # radial barrier
    SOFT_CLEARANCE = 0.75   # start pushing outward this far above the keep-out radius
    HARD_CLEARANCE = 0.30   # below this, the barrier is the only thing commanded
    K_BARRIER = 24.0
    K_BARRIER_DAMP = 6.0

    WIND_FILTER = 0.25
    ARRIVAL = 0.28          # advance target inside the verifier's tolerance

    def __init__(self, waypoints, nacelle, limits):
        self.waypoints = list(waypoints)
        self.nacelle = nacelle
        self.limits = limits

        self.order = self._plan_order(self.waypoints)
        self.index = 0

        self.wind_est = (0.0, 0.0, 0.0)
        self._prev_velocity = None
        self._prev_cmd = (0.0, 0.0, 0.0)

    # ------------------------------------------------------------------ planning
    def _plan_order(self, waypoints):
        """Snake order: group waypoints into rings along the axis, alternate direction."""
        axis = _sub(self.nacelle.axis_end, self.nacelle.axis_start)
        axis_len = _norm(axis)
        axis_dir = _scale(axis, 1.0 / axis_len) if axis_len > 0 else (1.0, 0.0, 0.0)

        def along(wp):
            return _dot(_sub(wp, self.nacelle.axis_start), axis_dir)

        def angle(wp):
            radial = _sub(wp, self._closest_axis_point(wp))
            # any consistent basis perpendicular to the axis
            ref = (0.0, 1.0, 0.0)
            if abs(_dot(ref, axis_dir)) > 0.9:
                ref = (0.0, 0.0, 1.0)
            u = _sub(ref, _scale(axis_dir, _dot(ref, axis_dir)))
            u = _scale(u, 1.0 / max(_norm(u), 1e-9))
            w = (
                axis_dir[1] * u[2] - axis_dir[2] * u[1],
                axis_dir[2] * u[0] - axis_dir[0] * u[2],
                axis_dir[0] * u[1] - axis_dir[1] * u[0],
            )
            return math.atan2(_dot(radial, w), _dot(radial, u))

        rings = {}
        for i, wp in enumerate(waypoints):
            key = round(along(wp), 3)
            rings.setdefault(key, []).append(i)

        order = []
        for r, (_, members) in enumerate(sorted(rings.items())):
            members.sort(key=lambda i: angle(waypoints[i]))
            if r % 2 == 1:
                members.reverse()
            order.extend(members)
        return order

    # ------------------------------------------------------------------ geometry
    def _closest_axis_point(self, position):
        a = self.nacelle.axis_start
        b = self.nacelle.axis_end
        ab = _sub(b, a)
        ab_len_sq = _dot(ab, ab)
        if ab_len_sq == 0.0:
            return a
        s = _dot(_sub(position, a), ab) / ab_len_sq
        s = max(0.0, min(1.0, s))
        return _add(a, _scale(ab, s))

    # ------------------------------------------------------------------- control
    def _update_wind_estimate(self, velocity):
        if self._prev_velocity is None:
            self._prev_velocity = velocity
            return
        if _norm(velocity) < self.limits.max_speed - 0.1:
            measured = _scale(_sub(velocity, self._prev_velocity), 1.0 / self.limits.dt)
            residual = _sub(measured, self._prev_cmd)
            a = self.WIND_FILTER
            self.wind_est = _add(
                _scale(self.wind_est, 1.0 - a), _scale(residual, a)
            )
        self._prev_velocity = velocity

    def _target(self, position):
        while self.index < len(self.order):
            wp = self.waypoints[self.order[self.index]]
            if math.dist(position, wp) <= self.ARRIVAL:
                self.index += 1
                continue
            return wp
        return None

    def step(self, t, position, velocity):
        self._update_wind_estimate(velocity)

        keep_out = self.nacelle.keep_out_radius
        axis_pt = self._closest_axis_point(position)
        radial = _sub(position, axis_pt)
        rho = _norm(radial)
        outward = _scale(radial, 1.0 / rho) if rho > 1e-9 else (0.0, 0.0, 1.0)

        target = self._target(position)
        if target is None:
            # everything visited: hold a safe station on the inspection cylinder
            target = _add(axis_pt, _scale(outward, self.nacelle.inspection_radius))

        # ---- path tracking
        error = _sub(target, position)
        v_des = _clamp_mag(_scale(error, self.KP), self.CRUISE_SPEED)
        cmd = _sub(_scale(_sub(v_des, velocity), self.KV), self.wind_est)

        # ---- radial barrier
        soft = keep_out + self.SOFT_CLEARANCE
        hard = keep_out + self.HARD_CLEARANCE
        if rho < soft:
            depth = (soft - rho) / self.SOFT_CLEARANCE
            push = self.K_BARRIER * depth * depth
            inward_speed = -_dot(velocity, outward)
            if inward_speed > 0.0:
                push += self.K_BARRIER_DAMP * inward_speed * depth
            barrier = _add(_scale(outward, push), _scale(self.wind_est, -1.0))
            if rho < hard:
                cmd = barrier
            else:
                # keep the tangential part of the tracking command, replace the
                # inward radial part with the barrier
                radial_part = _dot(cmd, outward)
                tangential = _sub(cmd, _scale(outward, radial_part))
                blend = (soft - rho) / (soft - hard)
                tangential = _scale(tangential, max(0.0, 1.0 - blend))
                cmd = _add(tangential, barrier)

        cmd = _clamp_mag(cmd, self.limits.max_accel)
        self._prev_cmd = cmd
        return cmd
