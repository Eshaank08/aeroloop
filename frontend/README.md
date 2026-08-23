# AeroLoop — Flight Record

AeroLoop is a Vite + React + TypeScript command center wrapped around the working
Python/Three.js inspection simulator. The polished flight record, engine cutaway,
telemetry, and evidence archive are clearly labelled recorded examples. The live
simulator and command drawer communicate with `viz/mission_view.html` through a
same-origin message bridge, so backend progress and verifier outcomes remain the
source of truth.

## Run locally

Requirements: Node.js 20.19+.

```bash
npm ci
npm run dev
```

Open the local URL printed by Vite.

## Validate a production build

```bash
npm run typecheck
npm run lint
npm run build
```

The production build is written to `../viz/dashboard/` and committed because the
Railway service runs the Python server without a Node build step. GitHub CI rebuilds
it and fails if the committed output is stale.

## Main files

- `src/components/aeroloop/` — reusable AeroLoop sections and command drawer
- `src/components/ui/` — shadcn Radix primitives used by the UI
- `src/data/aeroloop.ts` — typed, explicitly labelled recorded sample data
- `src/hooks/useCommandRunner.ts` — live simulator command/progress state
- `src/components/aeroloop/LiveSimulator.tsx` — embedded working 3D simulator
- `src/hooks/useFlightMotion.ts` — aircraft flight loop and scroll influence
- `src/index.css` — AeroLoop design tokens, responsive rules, and custom visual utilities
- `components.json` — shadcn configuration
