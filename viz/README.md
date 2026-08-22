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

Left panel is the live flight: coverage, waypoints, elapsed against the 120 s
budget, speed, clearance to the keep-out shell, wind magnitude, collisions, and
the verdict. Right panel is the whole verification batch, one cell per scenario,
green for pass. Drag to orbit, scroll to zoom, and use `jump to gust` to skip
straight to the disturbance.

## What you are looking at

The drone is a quadcopter airframe with counter rotating rotors. Rotor speed
follows the thrust the trace implies, and the airframe banks along the thrust
axis reconstructed from the recorded acceleration, so the attitude you see is
the attitude the recorded flight demanded, not an animation.

The nacelle sits on cradles and pylons in a hangar bay with painted floor
markings, a directional key light and shadows, roof trusses and lamps. Wind is
drawn twice: as streaks blowing through the bay at the scenario wind vector, and
as the arrow on the drone.

The keep-out shell is inert while the drone keeps its distance. As clearance
falls the shell brightens, a hotspot flares on the surface nearest the drone,
and a proximity banner appears. A breach turns both red.

Three cameras:

- `orbit`, the free camera, drag and scroll as before
- `follow`, a chase camera that trails the airframe and smooths its aim
- `pilot view`, the nose camera on the drone, with the airframe and the waypoint
  spheres hidden and inspection targets drawn as reticles instead
