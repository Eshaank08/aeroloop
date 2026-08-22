"""Rate controlled quadrotor dynamics for simulator v2."""

import math
from dataclasses import dataclass

from .params import DEFAULT_QUAD, QuadParams


def command_is_finite(command) -> bool:
    """Return whether a controller command has four finite values."""
    try:
        values = tuple(command)
        return len(values) == 4 and all(math.isfinite(value) for value in values)
    except (TypeError, ValueError, OverflowError):
        return False


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


def _mat_vec(matrix, vector):
    return tuple(_dot(row, vector) for row in matrix)


def _mat_mul(left, right):
    return tuple(
        tuple(sum(left[i][k] * right[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def _normalize(value):
    magnitude = _norm(value)
    if magnitude == 0.0:
        raise ValueError("cannot normalize a zero vector")
    return tuple(component / magnitude for component in value)


def _orthonormalize(matrix):
    """Orthonormalize the body axes with Gram-Schmidt."""
    columns = [
        tuple(matrix[row][column] for row in range(3))
        for column in range(3)
    ]
    first = _normalize(columns[0])
    second_residual = tuple(
        columns[1][i] - _dot(columns[1], first) * first[i]
        for i in range(3)
    )
    if _norm(second_residual) <= 1e-15:
        second_candidate = _cross(first, (1.0, 0.0, 0.0))
        if _norm(second_candidate) <= 1e-15:
            second_candidate = _cross(first, (0.0, 1.0, 0.0))
        second = _normalize(second_candidate)
    else:
        second = _normalize(second_residual)
    third_residual = tuple(
        columns[2][i]
        - _dot(columns[2], first) * first[i]
        - _dot(columns[2], second) * second[i]
        for i in range(3)
    )
    if _norm(third_residual) <= 1e-15:
        third = _cross(first, second)
    else:
        third = _normalize(third_residual)
    return tuple(
        tuple((first, second, third)[column][row] for column in range(3))
        for row in range(3)
    )


@dataclass(frozen=True)
class DroneState:
    """Immutable snapshot of the quadrotor state."""

    position: tuple
    velocity: tuple
    attitude: tuple
    body_rates: tuple
    thrust: float

    @property
    def camera_dir(self):
        return _mat_vec(self.attitude, (1.0, 0.0, 0.0))


class QuadDrone:
    """A deterministic rate controlled quadrotor."""

    def __init__(self, params: QuadParams = DEFAULT_QUAD, position=(0.0, 0.0, 6.0)):
        self.params = params
        self._position = tuple(position)
        self._velocity = (0.0, 0.0, 0.0)
        self._attitude = (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        )
        self._body_rates = (0.0, 0.0, 0.0)
        self._thrust = params.hover_thrust

    @property
    def state(self):
        return DroneState(
            position=self._position,
            velocity=self._velocity,
            attitude=self._attitude,
            body_rates=self._body_rates,
            thrust=self._thrust,
        )

    def step(self, command, wind):
        """Advance one tick using the specified thrust and body rates."""
        thrust_command, p_command, q_command, r_command = command
        p = max(-self.params.max_body_rate, min(self.params.max_body_rate, p_command))
        q = max(-self.params.max_body_rate, min(self.params.max_body_rate, q_command))
        r = max(-self.params.max_body_rate, min(self.params.max_body_rate, r_command))
        thrust_command = max(
            self.params.min_thrust,
            min(self.params.max_thrust, thrust_command),
        )

        rate_alpha = min(1.0, self.params.dt / self.params.rate_tau)
        omega_command = (p, q, r)
        omega = tuple(
            self._body_rates[i]
            + (omega_command[i] - self._body_rates[i]) * rate_alpha
            for i in range(3)
        )
        motor_alpha = min(1.0, self.params.dt / self.params.motor_tau)
        thrust = self._thrust + (thrust_command - self._thrust) * motor_alpha

        wx, wy, wz = omega
        skew = (
            (0.0, -wz, wy),
            (wz, 0.0, -wx),
            (-wy, wx, 0.0),
        )
        rotation_step = tuple(
            tuple(
                (1.0 if i == j else 0.0) + skew[i][j] * self.params.dt
                for j in range(3)
            )
            for i in range(3)
        )
        attitude = _orthonormalize(_mat_mul(self._attitude, rotation_step))

        thrust_world = _mat_vec(attitude, (0.0, 0.0, thrust))
        acceleration = tuple(
            thrust_world[i] / self.params.mass
            + ((0.0, 0.0, -self.params.gravity)[i])
            + wind[i]
            - (self.params.drag_coeff / self.params.mass) * self._velocity[i]
            for i in range(3)
        )
        velocity = tuple(
            self._velocity[i] + acceleration[i] * self.params.dt
            for i in range(3)
        )
        position = tuple(
            self._position[i] + velocity[i] * self.params.dt
            for i in range(3)
        )

        self._body_rates = omega
        self._thrust = thrust
        self._attitude = attitude
        self._velocity = velocity
        self._position = position
        return self.state
