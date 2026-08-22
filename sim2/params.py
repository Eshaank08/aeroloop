"""Quadrotor parameters and simulation constants for v2.

These are the graded numbers. Do not tune them to make a controller pass.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class QuadParams:
    mass: float = 1.4                 # kg
    gravity: float = 9.81             # m/s^2
    thrust_to_weight: float = 2.0     # max_thrust = thrust_to_weight * mass * gravity
    min_thrust: float = 0.0           # N, rotors can idle
    max_body_rate: float = 4.0        # rad/s per axis, commands are clamped
    rate_tau: float = 0.06            # s, first order lag on rate tracking
    motor_tau: float = 0.05           # s, first order lag on thrust
    drag_coeff: float = 0.35          # N per m/s, linear, per axis
    max_speed: float = 8.0            # m/s, exceeding it fails the scenario
    dt: float = 0.02                  # s, 50 Hz
    time_budget_s: float = 150.0      # s

    @property
    def max_thrust(self) -> float:
        return self.thrust_to_weight * self.mass * self.gravity

    @property
    def hover_thrust(self) -> float:
        return self.mass * self.gravity

    @property
    def max_ticks(self) -> int:
        return int(self.time_budget_s / self.dt)


DEFAULT_QUAD = QuadParams()
