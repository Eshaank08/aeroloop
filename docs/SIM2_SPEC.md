# Simulator v2: a real quadrotor

## Why

v1 is a point mass that is commanded in acceleration. It is a fair abstraction for
path level control, but it hides the part of the problem that makes drone inspection
hard: a quadrotor can only push along its own thrust axis, so translating means
tilting, and tilting moves the camera. A controller that passes v1 has not shown it
can point a camera at a nacelle while fighting a gust.

v2 keeps the same industry task, the same nacelle, the same seeded winds and the same
verdict shape, and replaces the vehicle and the coverage rule:

- the vehicle is a rate controlled quadrotor with thrust limits, motor lag and drag
- a waypoint counts as inspected only if the camera was actually looking at the
  nacelle, steadily, from within tolerance

v1 stays exactly as it is. v2 lives in `sim2/` and is graded by `sim2/run_verifier.py`
against `controller2.py`. Nothing in `sim/`, `tests/test_controller.py` or
`controller.py` changes.

## Frames and units

SI throughout, radians for angles.

World frame is the one v1 already uses: `+x` runs along the nacelle axis, `+y` is
lateral, `+z` is up. Gravity is `(0, 0, -9.81)`.

Attitude is a body to world rotation matrix `R`, stored row major as a tuple of three
3-tuples. Body `+z` is the thrust axis. Body `+x` is the camera boresight.

## Vehicle parameters

Frozen dataclass `QuadParams` in `sim2/params.py`, with `DEFAULT_QUAD` as the instance
the verifier uses. These are the graded numbers, do not tune them to make a controller
pass.

| Parameter          | Value    | Meaning                                            |
| ------------------ | -------- | -------------------------------------------------- |
| `mass`             | 1.4      | kg                                                 |
| `gravity`          | 9.81     | m/s^2                                              |
| `thrust_to_weight` | 2.0      | so `max_thrust = 2.0 * mass * gravity` newtons     |
| `min_thrust`       | 0.0      | newtons, rotors can idle                           |
| `max_body_rate`    | 4.0      | rad/s, per axis, commands are clamped              |
| `rate_tau`         | 0.06     | s, first order lag on rate tracking                |
| `motor_tau`        | 0.05     | s, first order lag on thrust                       |
| `drag_coeff`       | 0.35     | N per m/s, linear, applied per axis                |
| `max_speed`        | 8.0      | m/s, exceeding it fails the scenario as unsafe     |
| `dt`               | 0.02     | s, 50 Hz, same tick rate as v1                     |
| `time_budget_s`    | 150.0    | s, longer than v1 because aiming costs time        |

Start state: position `(0.0, 0.0, 6.0)`, zero velocity, identity attitude, zero rates,
thrust state at hover (`mass * gravity`).

## Dynamics, one tick

`QuadDrone.step(command, wind)` where `command` is `(thrust_n, p_cmd, q_cmd, r_cmd)`
from the controller and `wind` is the same acceleration triple v1 scenarios produce.

1. Clamp `thrust_n` to `[min_thrust, max_thrust]`. Clamp each rate command to
   `[-max_body_rate, +max_body_rate]`. A non finite command is a scenario failure,
   not a crash: record it as `invalid_command` and end the episode.
2. Rates lag toward the command: `omega += (omega_cmd - omega) * (dt / rate_tau)`,
   with the step capped so `dt / rate_tau` never exceeds 1.
3. Thrust lags toward the command the same way, with `motor_tau`.
4. Integrate attitude: `R <- R @ (I + skew(omega) * dt)`, then re-orthonormalize with
   Gram-Schmidt every tick so numerical drift cannot creep in.
5. Acceleration:
   `a = (R @ (0, 0, thrust)) / mass + (0, 0, -gravity) + wind - (drag_coeff / mass) * v`
6. `v += a * dt`, then `p += v * dt`. Velocity is **not** clamped: thrust limits and
   drag are what bound it. If `|v| > max_speed` the scenario fails as unsafe.

Determinism is a hard requirement: same seed, same controller, same trace, bit for
bit. No randomness inside the dynamics.

## Failure conditions

Any of these ends the episode and fails the scenario:

- **collision**: inside the nacelle keep-out radius, exactly as v1 judges it, reusing
  `sim.aircraft_geometry`
- **unsafe speed**: `|v| > max_speed`
- **invalid command**: any non finite value out of the controller
- **timeout**: elapsed exceeds `time_budget_s`

## The camera gate

This is the part that makes v2 a navigation problem rather than a waypoint problem.
It lives in `sim2/camera.py`.

A waypoint `wp` flips from pending to inspected on a tick where **all** of these hold:

1. `distance(position, wp) <= 0.5` m (`inspection_tolerance`)
2. the camera is on target: the angle between the boresight `R @ (1, 0, 0)` and the
   vector from the drone to the closest point on the nacelle **surface** is at most
   `60` degrees (`camera_fov_half_angle`)
3. the shot is steady: `|omega| <= 1.5` rad/s (`max_blur_rate`) and
   `|v| <= 2.5` m/s (`max_blur_speed`)

The gate uses 60 degrees because 35 degrees demanded 55 degrees of tilt at the top and
bottom waypoints and was not flyable.
There is no ground plane because the nacelle geometry is shared with v1 and half its
waypoints are below the axis.

Closest point on the surface is the radial projection used by v1's
`Nacelle.distance_to_surface`, so points beyond the nacelle ends project onto the end
cap rim rather than off into space. Put that helper in `sim2/camera.py`, do not modify
`sim/aircraft_geometry.py` to expose it.

Waypoints themselves are `Nacelle.waypoints()` from v1, unchanged: 24 points, three
rings of eight at the inspection radius.

## Controller interface

`controller2.py` at the repo root, the only file the agent writes for v2:

```python
class Controller:
    def __init__(self, waypoints, nacelle, params):
        ...

    def step(self, t: float, state: DroneState) -> tuple[float, float, float, float]:
        """Return (thrust_newtons, roll_rate, pitch_rate, yaw_rate)."""
```

`DroneState` is a frozen dataclass in `sim2/quad_dynamics.py` exposing `position`,
`velocity`, `attitude` (the 3x3 body to world rows), `body_rates`, `thrust` (the
current lagged thrust, not the command) and `camera_dir` (a convenience property,
`attitude @ (1, 0, 0)`).

Ship `controller2.py` as a bare hover stub that holds `mass * gravity` and zero rates.
It must be a legal controller that fails the verifier, so the agent loop has a real
starting point. Do not write a working v2 controller: that is the demo.

## Verifier

`sim2/run_verifier.py`, same shape and same CLI as `sim/run_verifier.py`
(`--scenarios`, `--seed`, `--verbose`), reusing `sim.scenarios.make_scenarios` so the
winds are the same deterministic family.

Per scenario report: coverage fraction, inspected count, failure reason or `None`,
elapsed seconds, and the per-waypoint reason coverage was missed where cheap to
provide (near miss on distance versus never aimed is the single most useful piece of
feedback for the agent, so include a count of waypoints that were within tolerance but
never satisfied the camera gate).

Thresholds, identical in spirit to v1:

- scenario passes if `coverage >= 0.95` and no failure condition fired and
  `elapsed <= time_budget_s`
- run passes if at least `90%` of scenarios pass
- default run is 30 scenarios from base seed 1000

Print a legible report ending in `RESULT: PASS` or `RESULT: FAIL`, and expose
`verify(...)` returning the same dict shape v1 returns so any report consumer works
for both.

`tests/test_controller2.py` wraps it for pytest exactly the way
`tests/test_controller.py` wraps v1, and asserts on the standard 30 scenario run.

## Out of scope

No battery model, no wind torque, no sensor noise, no obstacle other than the
nacelle. Those are v3 material; adding them now buys realism the demo cannot show in
90 seconds.
