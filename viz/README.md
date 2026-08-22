# Flight view

A read-only replay of the graded inspection flight, meant to be legible from
across a room. Nothing here can change a PASS or a FAIL: `viz/replay.py` reruns
the same `Drone`, `Nacelle`, `Controller` and wind scenarios the verifier uses
and records them, it does not score them and it never touches `sim/` or `tests/`.

## Record a run

```bash
python -m viz.replay                      # 30 scenarios from seed 1000, trace of seed 1000
python -m viz.replay --trace-seed 1017    # trace a scenario whose gust hits mid sweep
python -m viz.replay --seed 31337 --scenarios 50
```

That writes `viz/data/`:

- `scene.json` nacelle geometry, waypoints, limits and verifier thresholds
- `batch.json` per-scenario coverage, collisions, elapsed time and pass or fail
- `trace.json` the frame by frame flight of one scenario
- `data.js` all three as a script tag, so the view opens straight off the
  filesystem (`file://` blocks `fetch`)

The committed data is seed 1017, whose gust starts at 5.5 s with a 4.9 m/s^2
peak, so the disturbance lands while the drone is still working the nacelle.

## Watch it

Open `viz/flight_view.html` in a browser. No server, no build step, no network:
Three.js is vendored under `viz/vendor/`.

The view loads `data/data.js` by default and takes the directory from the query
string, so `flight_view.html?data=data2` replays a recording written elsewhere
under `viz/` without touching the committed v1 demo data.

Left panel is the live flight: coverage, waypoints, elapsed against the 120 s
budget, speed, clearance to the keep-out shell, wind magnitude, collisions, and
the verdict. Right panel is the whole verification batch, one cell per scenario,
green for pass. Drag to orbit, scroll to zoom, and use `jump to gust` to skip
straight to the disturbance.

## The drone model and its attitude

The drone is drawn as a quadrotor: body, four arms, four spinning rotors, and the
camera cone opening along the boresight, which turns green while the camera is
within 35 degrees of the nacelle skin it is inspecting.

v1 is a point mass, so a trace carries no attitude and the pose shown is inferred
rather than simulated: thrust axis along acceleration plus gravity, which is the
attitude a real quadrotor would have had to hold to fly that path, and boresight
aimed at the radial projection onto the skin. The legend says `attitude inferred`
whenever that is what you are looking at, and the tilt readout is marked the same
way. Tilt costs aim, which is exactly the coupling the v2 task in
`docs/SIM2_SPEC.md` grades.

When a trace carries an `R` field per frame, a 3x3 body to world rotation matrix,
the view uses it verbatim and drops the inferred label. That is the hook for
replaying a v2 flight, and the camera half angle is read from `scene.camera` when
the recorder supplies it.
