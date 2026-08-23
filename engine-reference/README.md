# Engine reference model & defect research

Additive/visual only — nothing here touches the graded pipeline (`sim/`, `controller.py`,
`tests/`). This folder is a reference model and supporting research, not part of the
verification path.

## Contents

- `nacelle_3d.html` — interactive 3D viewer: a real turbofan engine model with a real
  quadcopter drone patrolling it, and three real, cited defect locations marked directly
  on the surface (glow brighter as the drone passes near them).
- `assets/turbofan_engine.glb` — "Turbine | Turbofan Engine" by blenderbirb (Sketchfab,
  CC Attribution 4.0). Proportioned to a CFM56-7B-class engine.
- `assets/quadcopter_drone.glb` — "Quadcopter drone" by Annelida (Sketchfab, CC
  Attribution 4.0).
- `report/defect_report.html` — research report on real, documented aircraft engine
  defects that are hard to catch with manual or standard optical drone inspection
  specifically because they depend on complete, consistent coverage — the exact thing
  the verified controller in this repo proves it holds under wind disturbance. Includes
  real NTSB investigation photos (public domain, U.S. government work product) from the
  Southwest Airlines Flight 1380 accident.

## How to view

Both HTML files fetch local assets at runtime (3D models, images), so opening them by
double-click will fail silently on `file://` due to browser CORS restrictions. Run:

```
python -m http.server 8743
```

from this folder, then open `http://localhost:8743/nacelle_3d.html` or
`http://localhost:8743/report/defect_report.html`. On Windows, `view_engine_model.bat`
does this for you (starts the server and opens the 3D viewer in one click).

## Scope note

The 3D model and report are illustrative/research material for the pitch — they do not
claim the system detects defects. AeroLoop verifies flight-path coverage, not damage
classification; see the "honest bridge" framing in `report/defect_report.html` and
`docs/IDEA.md` for how the two connect.
