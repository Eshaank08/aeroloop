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

## Fly it by command

The recorded trace is enough to watch the graded flight. To fly new missions,
start the local command server and open the page from it instead of from the
filesystem:

```bash
python -m viz.server            # http://127.0.0.1:8765/flight_view.html
```

The flight command panel then accepts typed or spoken instructions. Each one is
parsed into a mission, flown through the real `Drone` and `Controller` on the
server, and the resulting trace replaces what the view is playing:

```text
full sweep
inspect ring 2 with seed 1234
inspect the top side, light wind
fly from 6 2 8 to 1 0 4
hold at x=2 y=3 z=6, calm
```

Rings are 1 to 3, sides are top, bottom, left, right, front and aft, and any
command takes `seed N` plus one of `calm`, `no wind`, `light wind` or
`heavy wind`. The mic button uses the browser's own speech recognition, so no
audio leaves the machine except through the browser vendor's usual path, and
nothing needs an API key.

Two honest caveats. The controller was written for the full sweep, so a single
`fly to` point or a heavy-wind partial mission is outside what it was verified
for, and the panel reports whatever happens, including a collision. And the
batch panel on the right always shows the recorded verification batch, not the
mission you just flew: `viz/server.py` only replays, it never scores.

## Which recording is on screen

The view reads `data/data.js` by default and takes the directory from the query
string, so `flight_view.html?data=data2` replays a simulator v2 recording
written by `viz/replay2.py` without touching the committed v1 demo data.

A v2 trace carries the airframe's own attitude, body rates and thrust, so the
pose is measured rather than reconstructed, the HUD reads out tilt from level and
how far the camera is off the nacelle, and the wedge in front of the nose is the
inspection camera's field of view at the gate's half angle, green while the shot
would count. For a v2 replay, waypoint visitation, coverage and coloring come
from the simulator's recorded inspection result rather than being re-derived
from strided frames. On a v1 trace, where the point mass simulator has no
attitude to record, the pose is still reconstructed from the recorded
acceleration and the panel says so. Traces without recorded inspection times
use the existing client-side gate fallback.
