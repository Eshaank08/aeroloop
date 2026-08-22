"""Path controller for the nacelle inspection flight."""

import math


def _norm(vector):
    return math.sqrt(sum(value * value for value in vector))


def _unit(vector):
    length = _norm(vector)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    return tuple(value / length for value in vector)


def _clamp_vector(vector, maximum):
    length = _norm(vector)
    if length <= maximum or length < 1e-9:
        return tuple(vector)
    scale = maximum / length
    return tuple(value * scale for value in vector)


def _wrap_angle(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


class Controller:
    def __init__(self, waypoints, nacelle, limits):
        self.waypoints = [tuple(point) for point in waypoints]
        self.nacelle = nacelle
        self.limits = limits
        self._order = self._make_order()
        self._next = 0
        self._previous_velocity = None
        self._previous_command = (0.0, 0.0, 0.0)
        self._wind = (0.0, 0.0, 0.0)
        self._last_angle = math.pi / 2.0

        ax, ay, az = self.nacelle.axis_start
        bx, by, bz = self.nacelle.axis_end
        self._axis_origin = (ay, az)
        self._axis_length = math.sqrt(
            (bx - ax) * (bx - ax)
            + (by - ay) * (by - ay)
            + (bz - az) * (bz - az)
        )

    def _make_order(self):
        if not self.waypoints:
            return []

        groups = {}
        for index, point in enumerate(self.waypoints):
            key = round(point[0], 6)
            groups.setdefault(key, []).append((index, point))

        ordered = []
        current_angle = math.pi / 2.0
        for ring_number, key in enumerate(sorted(groups)):
            ring = groups[key]
            angles = [
                math.atan2(point[2] - self.nacelle.axis_start[2],
                           point[1] - self.nacelle.axis_start[1])
                for _, point in ring
            ]
            start = min(
                range(len(ring)),
                key=lambda i: abs(_wrap_angle(angles[i] - current_angle)),
            )
            direction = 1 if ring_number % 2 == 0 else -1
            for offset in range(len(ring)):
                index = (start + direction * offset) % len(ring)
                ordered.append(ring[index][0])
            current_angle = angles[(start + direction * (len(ring) - 1)) % len(ring)]
        return ordered

    def _axis_projection(self, position):
        ax, ay, az = self.nacelle.axis_start
        bx, by, bz = self.nacelle.axis_end
        axis = (bx - ax, by - ay, bz - az)
        relative = (position[0] - ax, position[1] - ay, position[2] - az)
        length_sq = sum(value * value for value in axis)
        fraction = 0.0
        if length_sq > 1e-9:
            fraction = sum(axis[i] * relative[i] for i in range(3)) / length_sq
        fraction = max(0.0, min(1.0, fraction))
        closest = tuple(
            self.nacelle.axis_start[i] + fraction * axis[i] for i in range(3)
        )
        offset = tuple(position[i] - closest[i] for i in range(3))
        distance = max(_norm(offset), 1e-6)
        return closest, offset, distance

    def _carrot(self, position):
        if self._next >= len(self._order):
            return tuple(position)

        target = self.waypoints[self._order[self._next]]
        target_distance = math.dist(position, target)
        if target_distance < 0.78:
            return target

        ay, az = self._axis_origin
        angle = math.atan2(position[2] - az, position[1] - ay)
        if _norm((position[1] - ay, position[2] - az)) < 1e-6:
            angle = self._last_angle
        self._last_angle = angle
        target_angle = math.atan2(target[2] - az, target[1] - ay)
        delta = _wrap_angle(target_angle - angle)
        step = max(-0.55, min(0.55, delta))
        carrot_angle = angle + step

        shell_radius = min(
            self.nacelle.inspection_radius + 0.28,
            self.nacelle.inspection_radius + self.nacelle.waypoint_tolerance - 0.03,
        )
        x = target[0]
        return (
            x,
            ay + shell_radius * math.cos(carrot_angle),
            az + shell_radius * math.sin(carrot_angle),
        )

    def _update_wind(self, velocity):
        if self._previous_velocity is None:
            self._previous_velocity = tuple(velocity)
            return

        dt = self.limits.dt
        previous_speed = _norm(self._previous_velocity)
        current_speed = _norm(velocity)
        command_speed = _norm(self._previous_command)
        if (
            previous_speed < self.limits.max_speed - 0.18
            and current_speed < self.limits.max_speed - 0.18
            and command_speed < self.limits.max_accel * 0.82
        ):
            observed = tuple(
                (velocity[i] - self._previous_velocity[i]) / dt
                - self._previous_command[i]
                for i in range(3)
            )
            observed = tuple(max(-8.0, min(8.0, value)) for value in observed)
            alpha = 0.055
            self._wind = tuple(
                self._wind[i] + alpha * (observed[i] - self._wind[i])
                for i in range(3)
            )
        self._previous_velocity = tuple(velocity)

    def _safety(self, position, velocity, acceleration):
        _, offset, distance = self._axis_projection(position)
        normal = tuple(value / distance for value in offset)
        radial_velocity = sum(velocity[i] * normal[i] for i in range(3))
        radial_acceleration = sum(acceleration[i] * normal[i] for i in range(3))

        soft_radius = self.nacelle.keep_out_radius + 0.92
        if distance < soft_radius or radial_velocity < -0.25:
            required = 7.0 * max(0.0, soft_radius - distance)
            required += 2.8 * max(0.0, -radial_velocity)
            if required > radial_acceleration:
                acceleration = tuple(
                    acceleration[i] + normal[i] * (required - radial_acceleration)
                    for i in range(3)
                )

        if distance < self.nacelle.keep_out_radius + 0.42:
            radial_acceleration = sum(
                acceleration[i] * normal[i] for i in range(3)
            )
            tangent = tuple(
                acceleration[i] - normal[i] * radial_acceleration
                for i in range(3)
            )
            tangent_length = _norm(tangent)
            if distance < self.nacelle.keep_out_radius + 0.85:
                minimum_radial = 4.5 + 3.0 * max(
                    0.0, self.nacelle.keep_out_radius + 0.42 - distance
                )
                available = math.sqrt(
                    max(0.0, self.limits.max_accel * self.limits.max_accel
                        - tangent_length * tangent_length)
                )
                radial_acceleration = max(radial_acceleration, minimum_radial)
                radial_acceleration = min(radial_acceleration, available)
                acceleration = tuple(
                    normal[i] * radial_acceleration + tangent[i]
                    for i in range(3)
                )

        if distance < self.nacelle.keep_out_radius + 0.08:
            acceleration = tuple(
                normal[i] * self.limits.max_accel for i in range(3)
            )
        return _clamp_vector(acceleration, self.limits.max_accel)

    def step(self, t, position, velocity):
        position = tuple(float(value) for value in position)
        velocity = tuple(float(value) for value in velocity)
        self._update_wind(velocity)

        while self._next < len(self._order):
            target = self.waypoints[self._order[self._next]]
            if math.dist(position, target) <= self.nacelle.waypoint_tolerance:
                self._next += 1
            else:
                break

        if self._next >= len(self._order):
            desired = tuple(-2.2 * value for value in velocity)
        else:
            carrot = self._carrot(position)
            error = tuple(carrot[i] - position[i] for i in range(3))
            desired = tuple(
                2.8 * error[i] - 2.35 * velocity[i] - self._wind[i]
                for i in range(3)
            )

        desired = self._safety(position, velocity, desired)
        desired = _clamp_vector(desired, self.limits.max_accel)
        self._previous_command = desired
        return tuple(desired)
