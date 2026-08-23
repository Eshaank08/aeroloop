"""Rate controlled quadrotor inspection controller for simulator v2.

Strategy
--------
* Thrust only acts along body +z and the camera looks along body +x, so the two
  jobs of the airframe are coupled: the attitude that holds a position is rarely
  the attitude that aims the camera. The controller therefore treats the camera
  gate as a constraint on the thrust axis and solves for the attitude that is
  closest to the position controller's demand while still satisfying it. Rate
  control is split into a prioritized thrust-axis term and a smaller yaw term,
  so camera aiming cannot starve the attitude that provides braking and lift.

  For a target direction `d` (drone to closest nacelle surface point) the camera
  can be aimed by yaw alone, at best, to within `asin(|dot(z_body, d)|)` of `d`.
  The gate wants 60 degrees, so the whole gate reduces to the scalar condition
  `|dot(z_body, d)| <= sin(60 deg)`. The side and diagonal waypoints therefore
  need no tilt, while the top and bottom waypoints need only about 30 degrees.
  The thrust axis is rotated the minimum amount that satisfies the bound, which
  preserves most of the position controller's authority.

* The aim is held near each waypoint rather than flown as a large pass. The
  controller enters `aim` after reaching a small hold point, and leaves it for
  a fresh approach if it leaves the tolerance ball, exceeds the blur speed, or
  takes too long. Above the camera blur speed, aiming is abandoned immediately
  so the full rate budget is available for braking. The axis and boresight are
  pre-aimed on the final approach while speed is still low.

* Wind is recovered exactly from the observed acceleration (the dynamics are
  known and the state is fully observable) and fed forward, which keeps the
  inspection route stable during a gust.

The vertical channel is always solved exactly (thrust is scaled by
`1 / dot(z_body, up)`) so that altitude holds no matter how far the aim
constraint has tilted the airframe, and the residual horizontal acceleration is
whatever the tilt happens to produce.
"""

import math

from sim2.camera import (
    camera_fov_half_angle,
    inspection_tolerance,
    max_blur_rate,
    max_blur_speed,
)

FOV_HALF_ANGLE = camera_fov_half_angle
BLUR_RATE = max_blur_rate
BLUR_SPEED = max_blur_speed
TOLERANCE = inspection_tolerance


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(v):
    return math.sqrt(_dot(v, v))


def _unit(v, fallback=(0.0, 0.0, 1.0)):
    magnitude = _norm(v)
    if magnitude <= 1e-12:
        return fallback
    return _scale(v, 1.0 / magnitude)


def _clamp(value, low, high):
    return low if value < low else (high if value > high else value)


def _clamp_norm(v, limit):
    magnitude = _norm(v)
    if magnitude <= limit or magnitude <= 1e-12:
        return v
    return _scale(v, limit / magnitude)


def _body_axis(attitude, index):
    return (attitude[0][index], attitude[1][index], attitude[2][index])


def _horizontal(v):
    return (v[0], v[1], 0.0)


def _closest_surface_point(nacelle, position):
    """Radial projection of position onto the capped nacelle surface."""
    axis = _sub(nacelle.axis_end, nacelle.axis_start)
    axis_length_sq = _dot(axis, axis)
    from_start = _sub(position, nacelle.axis_start)
    if axis_length_sq <= 0.0:
        center = nacelle.axis_start
        radial = _sub(position, center)
    else:
        fraction = _clamp(_dot(from_start, axis) / axis_length_sq, 0.0, 1.0)
        center = _add(nacelle.axis_start, _scale(axis, fraction))
        radial = _sub(position, center)
        if fraction <= 0.0 or fraction >= 1.0:
            axis_direction = _scale(axis, 1.0 / math.sqrt(axis_length_sq))
            radial = _sub(radial, _scale(axis_direction, _dot(radial, axis_direction)))
    return _add(center, _scale(_unit(radial, (0.0, 1.0, 0.0)), nacelle.radius))


def _rotation_vector(matrix):
    """Axis times angle of a rotation matrix, in the frame the matrix acts on."""
    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    cosine = _clamp(0.5 * (trace - 1.0), -1.0, 1.0)
    angle = math.acos(cosine)
    if angle < 1e-9:
        return (0.0, 0.0, 0.0)
    sine = math.sin(angle)
    if sine > 1e-6:
        axis = _scale(
            (
                matrix[2][1] - matrix[1][2],
                matrix[0][2] - matrix[2][0],
                matrix[1][0] - matrix[0][1],
            ),
            1.0 / (2.0 * sine),
        )
        return _scale(axis, angle)
    # Half turn: recover the axis from the symmetric part.
    candidates = [
        (matrix[0][0] + 1.0, matrix[1][0], matrix[2][0]),
        (matrix[0][1], matrix[1][1] + 1.0, matrix[2][1]),
        (matrix[0][2], matrix[1][2], matrix[2][2] + 1.0),
    ]
    best = max(candidates, key=_norm)
    return _scale(_unit(best), angle)


class Controller:
    """Waypoint inspection controller for the v2 quadrotor."""

    # position and attitude loop gains
    position_gain = 2.0
    velocity_gain = 4.0
    attitude_gain = 8.5
    transit_speed = 1.8
    approach_speed = 1.0

    # aim constraint shaping
    aim_margin = math.radians(6.0)
    retry_aim_margin = math.radians(8.0)
    late_retry_aim_margin = math.radians(7.0)
    hold_offset = 0.10
    vertical_hold_offset = 0.50
    retry_near_factor = 0.2
    retry_far_factor = 1.0
    arrive_radius = 0.70
    arrive_speed = 1.40
    pass_timeout = 3.0
    waypoint_timeout = 13.0
    max_attempts = 4
    max_retry_sweeps = 5

    # safety envelope
    standoff_radius = 2.85
    barrier_radius = 2.45
    brake_speed = 1.4
    brake_gain = 7.0
    barrier_gain = 10.0
    barrier_damping = 5.0
    retry_barrier_gain = 10.0
    retry_barrier_damping = 5.0
    retry_standoff_radius = 2.85

    # prioritized body-rate control
    axis_rate_limit = 3.5
    yaw_gain = 4.0
    yaw_rate_limit = 2.0
    settled_axis_rate_limit = 1.0
    settled_rate_budget = BLUR_RATE
    settled_rate_damping = 3.0
    recovery_duration = 0.8
    aim_vertical_fraction = 0.90
    aim_cosine_min = 0.80
    preaim_distance = 0.8
    yaw_distance = 2.5

    def __init__(self, waypoints, nacelle, params):
        self.waypoints = [tuple(point) for point in waypoints]
        self.nacelle = nacelle
        self.params = params
        self.gravity = (0.0, 0.0, -params.gravity)
        self.max_thrust = params.max_thrust
        self.drag_per_mass = params.drag_coeff / params.mass

        self.route = self._plan_route()
        self.ring_grid = self._ring_grid()
        self.route_index = 0
        self.inspected = [False] * len(self.waypoints)
        self.attempts = {}
        self.mode = "transit"
        self.waypoint_start_t = 0.0
        self.pass_start_t = 0.0
        self.retried = False
        self.retry_sweeps = 0
        self.recovery_until = 0.0

        self.wind_estimate = (0.0, 0.0, 0.0)
        self.previous_state = None

    # ------------------------------------------------------------------ route

    def _plan_route(self):
        """Snake through all waypoints, ring by ring along the axis."""
        rings = {}
        for index, waypoint in enumerate(self.waypoints):
            rings.setdefault(round(waypoint[0], 6), []).append(index)

        route = []
        for ring_number, axis_position in enumerate(
            sorted(rings, reverse=True)
        ):
            members = sorted(
                rings[axis_position],
                key=lambda index: math.atan2(
                    self.waypoints[index][2], self.waypoints[index][1]
                ),
            )
            if ring_number % 2 == 1:
                members.reverse()
            route.extend(members)
        return route

    def _ring_grid(self):
        """Ring and slot structure of the waypoints this controller was given.

        The full nacelle is a regular grid: every ring sits at its own axial
        position and carries the same angular slots. A bounded mission target set
        is usually not, and can even be a single waypoint, so the grid is derived
        from the waypoints rather than assumed. Returns None when the waypoints do
        not form a regular grid, which tells the retry sweep to order the missed
        waypoints geometrically instead.
        """
        rings = {}
        for index, waypoint in enumerate(self.waypoints):
            rings.setdefault(round(waypoint[0], 6), []).append(index)
        axis_positions = sorted(rings)
        if len(axis_positions) < 2:
            return None
        per_ring = len(rings[axis_positions[0]])
        if per_ring < 3 or any(
            len(rings[axis]) != per_ring for axis in axis_positions
        ):
            return None

        def slot_angle(index):
            """Angle around the nacelle axis, measured from the +y side."""
            waypoint = self.waypoints[index]
            return math.atan2(waypoint[2], waypoint[1]) % (2.0 * math.pi)

        ring_of = {}
        slot_of = {}
        index_at = {}
        reference = None
        for ring_number, axis_position in enumerate(axis_positions):
            members = sorted(rings[axis_position], key=slot_angle)
            angles = [slot_angle(index) for index in members]
            if reference is None:
                reference = angles
            elif any(
                abs(angle - expected) > 1e-6
                for angle, expected in zip(angles, reference)
            ):
                # rings that do not share their slot angles are not a grid
                return None
            for slot, index in enumerate(members):
                ring_of[index] = ring_number
                slot_of[index] = slot
                index_at[(ring_number, slot)] = index
        return {
            "rings": len(axis_positions),
            "per_ring": per_ring,
            "ring_of": ring_of,
            "slot_of": slot_of,
            "index_at": index_at,
        }

    def _travel_direction(self, position_in_route):
        """Horizontal direction of travel out of the waypoint at this route slot."""
        index = self.route[position_in_route]
        if position_in_route + 1 < len(self.route):
            following = self.waypoints[self.route[position_in_route + 1]]
            direction = _horizontal(_sub(following, self.waypoints[index]))
            if _norm(direction) > 1e-6:
                return _unit(direction)
        waypoint = self.waypoints[index]
        tangent = (0.0, -waypoint[2], waypoint[1])
        return _unit(_horizontal(tangent), (0.0, 1.0, 0.0))

    # ------------------------------------------------------------- geometry

    def _target_direction(self, position):
        surface_point = _closest_surface_point(self.nacelle, position)
        return _unit(_sub(surface_point, position), (0.0, 0.0, -1.0))

    def _axis_distance(self, position):
        return self.nacelle.distance_to_surface(position)

    def _hold_point(self, position_in_route):
        """Where to sit for this waypoint, offset against the expected drift."""
        waypoint = self.waypoints[self.route[position_in_route]]
        base = waypoint
        direction = self._target_direction(base)
        margin = self.aim_margin
        if self.retried:
            margin = (
                self.late_retry_aim_margin
                if self.retry_sweeps >= 2
                else self.retry_aim_margin
            )
        if abs(_dot(direction, (0.0, 0.0, 1.0))) <= math.sin(
            FOV_HALF_ANGLE - margin
        ):
            return base
        drift = _unit(_horizontal(direction), self._travel_direction(position_in_route))
        if _norm(_horizontal(direction)) <= 0.2:
            drift = self._travel_direction(position_in_route)
        offset = self.hold_offset
        if abs(_dot(direction, (0.0, 0.0, 1.0))) > 0.85:
            offset = self.vertical_hold_offset
            if self.retried:
                phase = (self.retry_sweeps - 1) % 3
                if phase == 1:
                    offset *= self.retry_near_factor
                elif phase == 2:
                    offset *= self.retry_far_factor
        return _sub(base, _scale(drift, offset))

    def _gate(self, state, waypoint):
        """The verifier's camera gate, recomputed on the state we were handed."""
        if _norm(_sub(state.position, waypoint)) > TOLERANCE:
            return False
        if _norm(state.body_rates) > BLUR_RATE or _norm(state.velocity) > BLUR_SPEED:
            return False
        direction = self._target_direction(state.position)
        camera = _unit(state.camera_dir)
        return math.acos(_clamp(_dot(camera, direction), -1.0, 1.0)) <= FOV_HALF_ANGLE

    # ------------------------------------------------------------------ wind

    def _update_wind(self, state):
        previous = self.previous_state
        self.previous_state = state
        if previous is None:
            return
        dt = self.params.dt
        measured = _scale(_sub(state.velocity, previous.velocity), 1.0 / dt)
        thrust_world = _scale(_body_axis(state.attitude, 2), state.thrust)
        modelled = _add(
            _add(_scale(thrust_world, 1.0 / self.params.mass), self.gravity),
            _scale(previous.velocity, -self.drag_per_mass),
        )
        residual = _sub(measured, modelled)
        if not all(math.isfinite(component) for component in residual):
            return
        self.wind_estimate = _add(
            _scale(self.wind_estimate, 0.35), _scale(residual, 0.65)
        )

    # -------------------------------------------------------------- sequence

    def _advance(self, t, state):
        if self.route_index >= len(self.route):
            self._requeue_missed(t, state)
            return
        index = self.route[self.route_index]
        waypoint = self.waypoints[index]

        if self._gate(state, waypoint):
            self.inspected[index] = True
            self._next_waypoint(t, state)
            return

        offset = _norm(_sub(state.position, waypoint))
        speed = _norm(state.velocity)
        if self.mode == "transit":
            hold = self._hold_point(self.route_index)
            if (
                _norm(_sub(state.position, hold)) <= self.arrive_radius
                and speed <= self.arrive_speed
            ):
                self.mode = "aim"
                self.pass_start_t = t
        elif self.mode == "aim":
            expired = t - self.pass_start_t > self.pass_timeout
            if offset > 1.10 or speed > BLUR_SPEED or expired:
                self.mode = "transit"
                self.attempts[index] = self.attempts.get(index, 0) + 1
                self.recovery_until = t + self.recovery_duration

        if (
            t - self.waypoint_start_t > self.waypoint_timeout
            or self.attempts.get(index, 0) > self.max_attempts
        ):
            self._next_waypoint(t, state)

    def _next_waypoint(self, t, state=None):
        self.route_index += 1
        self.mode = "transit"
        self.waypoint_start_t = t
        if self.route_index >= len(self.route):
            self._requeue_missed(t, state)

    def _requeue_missed(self, t, state):
        """One retry sweep over anything the first pass failed to inspect."""
        if self.retry_sweeps >= self.max_retry_sweeps:
            return
        self.retried = True
        self.retry_sweeps += 1
        missed = [
            index
            for index in range(len(self.waypoints))
            if not self.inspected[index]
        ]
        if not missed:
            return
        grid = self.ring_grid
        if grid is None:
            retry_route = self._nearest_first_route(missed, state)
        else:
            retry_route = self._sweep_route(missed, grid)
        if not retry_route:
            return
        self.route = self.route + retry_route
        self.attempts = {}
        self.mode = "transit"
        self.waypoint_start_t = t

    def _sweep_route(self, missed, grid):
        """Walk the ring grid slot by slot, picking up every missed waypoint."""
        per_ring = grid["per_ring"]
        ring_of = grid["ring_of"]
        slot_of = grid["slot_of"]
        index_at = grid["index_at"]
        retry_route = []
        current = self.route[-1]
        remaining = set(missed)

        while remaining:
            current_ring = ring_of[current]
            current_slot = slot_of[current]

            def path_length(index):
                slot_delta = abs(slot_of[index] - current_slot)
                slot_delta = min(slot_delta, per_ring - slot_delta)
                return slot_delta + abs(ring_of[index] - current_ring)

            target = min(remaining, key=path_length)
            target_ring = ring_of[target]
            target_slot = slot_of[target]
            step = 1 if target_slot >= current_slot else -1
            if abs(target_slot - current_slot) > per_ring / 2:
                step = -step
            while current_slot != target_slot:
                current_slot = (current_slot + step) % per_ring
                current = index_at[(current_ring, current_slot)]
                retry_route.append(current)
            while current_ring != target_ring:
                current_ring += 1 if target_ring > current_ring else -1
                current = index_at[(current_ring, current_slot)]
                retry_route.append(current)
            if not retry_route or retry_route[-1] != target:
                retry_route.append(target)
            remaining.discard(target)
        return retry_route

    def _nearest_first_route(self, missed, state):
        """Retry order for a waypoint set too small or too sparse to form rings.

        There is no ring to sweep, so the recovery that saves the shot is simply
        another approach to the missed waypoints, nearest one first. With a single
        target this re-approaches that waypoint, which is what a retry sweep means
        for a one waypoint mission.
        """
        if state is not None:
            origin = state.position
        else:
            origin = self.waypoints[self.route[-1]] if self.route else (0.0, 0.0, 0.0)
        retry_route = []
        remaining = set(missed)
        while remaining:
            target = min(
                remaining,
                key=lambda index: _norm(_sub(self.waypoints[index], origin)),
            )
            retry_route.append(target)
            origin = self.waypoints[target]
            remaining.discard(target)
        return retry_route

    # --------------------------------------------------------------- control

    def _desired_acceleration(self, t, state, target, speed_limit):
        error = _sub(target, state.position)
        desired_velocity = _clamp_norm(_scale(error, self.position_gain), speed_limit)
        command = _scale(_sub(desired_velocity, state.velocity), self.velocity_gain)

        # radial barrier around the keep-out volume
        position = state.position
        radial = _unit((0.0, position[1], position[2]), (0.0, 1.0, 0.0))
        distance = self._axis_distance(position)
        standoff_radius = (
            self.retry_standoff_radius if self.retried else self.standoff_radius
        )
        if distance < standoff_radius:
            barrier_gain = (
                self.retry_barrier_gain if self.retried else self.barrier_gain
            )
            barrier_damping = (
                self.retry_barrier_damping
                if self.retried
                else self.barrier_damping
            )
            push = barrier_gain * (standoff_radius - distance)
            inward = _dot(state.velocity, radial)
            if inward < 0.0:
                push -= barrier_damping * inward
            command = _add(command, _scale(radial, push))

        speed = _norm(state.velocity)
        if speed > self.brake_speed:
            command = _add(command, _scale(state.velocity, -self.brake_gain))
        return _clamp_norm(command, 11.0)

    def _constrain_thrust_axis(self, desired_axis, target_direction, tie_break, cosine_min):
        """Rotate the thrust axis the least amount that satisfies the aim bound."""
        margin = self.aim_margin
        if self.retried:
            margin = (
                self.late_retry_aim_margin
                if self.retry_sweeps >= 2
                else self.retry_aim_margin
            )
        bound = math.sin(FOV_HALF_ANGLE - margin)
        projection = _dot(desired_axis, target_direction)
        if abs(projection) > bound:
            wanted = bound if projection > 0.0 else -bound
            perpendicular = _sub(desired_axis, _scale(target_direction, projection))
            if (
                _norm(perpendicular) <= 1e-6
                or abs(_dot(target_direction, (0.0, 0.0, 1.0))) > 0.85
            ):
                perpendicular = _sub(
                    tie_break, _scale(target_direction, _dot(tie_break, target_direction))
                )
            perpendicular = _unit(perpendicular, (0.0, 0.0, 1.0))
            desired_axis = _unit(
                _add(
                    _scale(target_direction, wanted),
                    _scale(perpendicular, math.sqrt(max(0.0, 1.0 - wanted * wanted))),
                )
            )
        return self._limit_tilt(desired_axis, cosine_min)

    def _limit_tilt(self, axis, cosine_min):
        """Keep the thrust axis upright enough that hover thrust stays available."""
        vertical = _dot(axis, (0.0, 0.0, 1.0))
        if vertical >= cosine_min:
            return axis
        horizontal = _unit(_horizontal(axis), (1.0, 0.0, 0.0))
        sine = math.sqrt(max(0.0, 1.0 - cosine_min * cosine_min))
        return _unit(
            _add(_scale(horizontal, sine), (0.0, 0.0, cosine_min))
        )

    def _thrust_axis_rate(self, state, desired_axis, limit):
        """Return the body rate that aligns body +z with the desired axis."""
        body_x = _body_axis(state.attitude, 0)
        body_y = _body_axis(state.attitude, 1)
        body_z = _body_axis(state.attitude, 2)
        cross_world = _cross(body_z, desired_axis)
        sine = _norm(cross_world)
        cosine = _clamp(_dot(body_z, desired_axis), -1.0, 1.0)
        if sine <= 1e-9:
            return (0.0, 0.0, 0.0)
        angle = math.atan2(sine, cosine)
        axis_world = _scale(cross_world, 1.0 / sine)
        error_body = (
            _dot(axis_world, body_x),
            _dot(axis_world, body_y),
            _dot(axis_world, body_z),
        )
        return _clamp_norm(_scale(error_body, self.attitude_gain * angle), limit)

    def _yaw_rate(self, state, target_direction):
        """Return the signed body-z rate that turns the boresight to target."""
        body_x = _body_axis(state.attitude, 0)
        body_z = _body_axis(state.attitude, 2)
        target_projection = _sub(
            target_direction, _scale(body_z, _dot(target_direction, body_z))
        )
        if _norm(target_projection) <= 1e-9:
            return 0.0
        target_projection = _unit(target_projection)
        sine = _dot(body_z, _cross(body_x, target_projection))
        cosine = _clamp(_dot(body_x, target_projection), -1.0, 1.0)
        error = math.atan2(sine, cosine)
        return _clamp(
            self.yaw_gain * error,
            -self.yaw_rate_limit,
            self.yaw_rate_limit,
        )

    def step(self, t, state):
        self._update_wind(state)
        self._advance(t, state)

        aiming = self.mode == "aim" and self.route_index < len(self.route)
        if self.route_index < len(self.route):
            target = self._hold_point(self.route_index)
            speed_limit = self.approach_speed if aiming else self.transit_speed
            if not aiming:
                distance = _norm(_sub(state.position, target))
                if distance < 2.4:
                    speed_limit = min(
                        self.transit_speed,
                        self.approach_speed + 0.55 * distance,
                    )
        else:
            target = state.position
            speed_limit = 0.0

        want = self._desired_acceleration(t, state, target, speed_limit)
        thrust_vector = _sub(
            _add(_add(want, _scale(self.gravity, -1.0)), _scale(state.velocity, self.drag_per_mass)),
            self.wind_estimate,
        )
        vertical_demand = max(thrust_vector[2], 0.4 * self.params.gravity)
        cosine_min = _clamp(
            self.params.mass * vertical_demand / (0.95 * self.max_thrust), 0.5, 0.95
        )

        desired_axis = _unit(thrust_vector, (0.0, 0.0, 1.0))
        target_direction = self._target_direction(state.position)
        speed = _norm(state.velocity)
        emergency = self._axis_distance(state.position) < self.barrier_radius
        preaim = (
            not aiming
            and self.route_index < len(self.route)
            and speed <= 1.8
            and _norm(_sub(state.position, target)) <= self.preaim_distance
            and t >= self.recovery_until
        )
        aim_constraint = (
            (aiming or preaim)
            and speed <= BLUR_SPEED
            and t >= self.recovery_until
            and not emergency
        )
        yaw_constraint = (
            self.route_index < len(self.route)
            and speed <= BLUR_SPEED
            and t >= self.recovery_until
            and not emergency
            and _norm(_sub(state.position, target)) <= self.yaw_distance
        )
        if (
            aim_constraint
            and abs(_dot(target_direction, (0.0, 0.0, 1.0))) > 0.85
        ):
            vertical_demand = self.aim_vertical_fraction * self.params.gravity
            cosine_min = self.aim_cosine_min
        if aim_constraint:
            tie_break = self._travel_direction(self.route_index)
            desired_axis = self._constrain_thrust_axis(
                desired_axis,
                target_direction,
                tie_break,
                cosine_min,
            )
        else:
            desired_axis = self._limit_tilt(desired_axis, max(cosine_min, 0.72))

        body_z = _body_axis(state.attitude, 2)
        axis_limit = self.axis_rate_limit
        camera = _unit(_body_axis(state.attitude, 0))
        aim_error = math.acos(_clamp(_dot(camera, target_direction), -1.0, 1.0))
        if aim_constraint and aim_error <= FOV_HALF_ANGLE:
            axis_limit = self.settled_axis_rate_limit
        axis_rate = self._thrust_axis_rate(state, desired_axis, axis_limit)
        if aim_constraint and aim_error <= FOV_HALF_ANGLE:
            axis_rate = _clamp_norm(
                _sub(
                    axis_rate,
                    _scale(
                        (state.body_rates[0], state.body_rates[1], 0.0),
                        self.settled_rate_damping,
                    ),
                ),
                axis_limit,
            )

        yaw_rate = 0.0
        if yaw_constraint:
            rate_budget = self.params.max_body_rate
            if aim_constraint and aim_error <= FOV_HALF_ANGLE:
                rate_budget = self.settled_rate_budget
            remaining = math.sqrt(
                max(0.0, rate_budget**2 - _norm(axis_rate) ** 2)
            )
            yaw_command = self._yaw_rate(state, target_direction)
            if aim_constraint and aim_error <= FOV_HALF_ANGLE:
                yaw_command -= self.settled_rate_damping * state.body_rates[2]
            yaw_rate = _clamp(
                yaw_command,
                -min(self.yaw_rate_limit, remaining),
                min(self.yaw_rate_limit, remaining),
            )
        rates = (
            _clamp(axis_rate[0], -self.params.max_body_rate, self.params.max_body_rate),
            _clamp(axis_rate[1], -self.params.max_body_rate, self.params.max_body_rate),
            _clamp(axis_rate[2] + yaw_rate, -self.params.max_body_rate, self.params.max_body_rate),
        )
        thrust = self.params.mass * vertical_demand / max(
            _dot(body_z, (0.0, 0.0, 1.0)), 0.35
        )
        thrust = _clamp(thrust, 0.0, self.max_thrust)

        command = (thrust, rates[0], rates[1], rates[2])
        if not all(math.isfinite(value) for value in command):
            return (self.params.hover_thrust, 0.0, 0.0, 0.0)
        return command
