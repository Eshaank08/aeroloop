# AeroLoop — Project Website

AeroLoop is a Vite + React + TypeScript project website for the working Python/Three.js
inspection simulator. The website explains the problem, autonomous loop, running proof,
and honest simulation boundary. It deliberately does not embed or imitate the simulator:
its launch links open `/mission_view.html` as the dedicated technical workspace.

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

- `src/components/aeroloop/AeroLoopShell.tsx` — website composition and navigation
- `src/components/aeroloop/ProjectStory.tsx` — problem, loop, proof, and demo narrative
- `src/components/aeroloop/HeroFlightRecorder.tsx` — landing hero and simulator CTA
- `src/components/ui/` — shadcn Radix primitives used by the UI
- `src/hooks/useFlightMotion.ts` — aircraft flight loop and scroll influence
- `src/index.css` — AeroLoop design tokens, responsive rules, and custom visual utilities
- `components.json` — shadcn configuration
