"""Flight limits and simulation constants. Do not modify to make a controller pass."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    max_accel: float = 6.0      # m/s^2, controller output is clamped to this
    max_speed: float = 4.0      # m/s
    time_budget_s: float = 120.0
    dt: float = 0.02            # 50 Hz

    @property
    def max_ticks(self) -> int:
        return int(self.time_budget_s / self.dt)


DEFAULT_LIMITS = Limits()
