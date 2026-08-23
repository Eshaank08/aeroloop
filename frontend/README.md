# AeroLoop — Flight Record

AeroLoop is a Vite + React + TypeScript inspection command center for aircraft-engine simulation. The UI is exported from the focused AeroLoop canvas design and includes the responsive flight record, axial engine cutaway, telemetry traces, evidence archive, command drawer, and inspection drone workflow.

## Run locally

Requirements: Node.js 20.19+.

```bash
npm install
npm run dev
```

Open the local URL printed by Vite.

## Validate a production build

```bash
npm run build
npm run preview
```

## Push to GitHub

From this `aeroloop` folder:

```bash
git init
git add .
git commit -m "Add AeroLoop inspection command center"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

If your GitHub repository already contains an app, copy the contents of this folder into the repository root instead of creating a nested folder. Keep `package.json`, `src/`, `public/`, `index.html`, `vite.config.ts`, and the TypeScript config files together.

## Main files

- `src/components/aeroloop/` — reusable AeroLoop sections and command drawer
- `src/components/ui/` — shadcn Radix primitives used by the UI
- `src/data/aeroloop.ts` — typed simulation mock data
- `src/hooks/useCommandRunner.ts` — command start/stop state and log entries
- `src/hooks/useFlightMotion.ts` — aircraft flight loop and scroll influence
- `src/index.css` — AeroLoop design tokens, responsive rules, and custom visual utilities
- `components.json` — shadcn configuration
