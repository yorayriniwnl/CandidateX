# CandidateX frontend studio

The homepage visual language now extends through the guided analysis, candidate dashboard, prototype workspace, research demo, and shared sign-in navigation.

Preview: http://127.0.0.1:3109

## Design

- Warm black and plum surfaces, lavender primary actions, consistent typography, spacing, navigation, and footers.
- A still edition of the homepage sculpture accompanies analysis steps and research. It renders on demand and has an inline SVG fallback.
- Layered document upload, visual role selection, orbital request indicator, redesigned dossier summary, evidence panels, and inspector.
- Candidate monograms, quieter metric cards, a responsive workspace tool rail, and clearer empty states.
- Modal labeling, focus restoration, keyboard role selection, and reduced-motion support in shared controls.

## Review captures

- `analyze-1440.png` / `analyze-390.png`: first-run intake.
- `analysis-role-1440.png`, `analysis-sources-1440.png`, `analysis-review-1440.png`: guided steps; mobile counterparts use `390`.
- `analysis-running.png`: a pending request, without simulated progress percentages.
- `dossier-1440.png` / `dossier-390.png`: report overview.
- `dossier-capabilities.png` / `evidence-inspector.png`: evidence drill-down.
- `hr-1440.png` / `hr-390.png` / `add-candidate.png`: candidate workspace and dialog.
- `workspace-1440.png` / `workspace-390.png`: prototype shell; additional captures show evaluation, comparison, and methodology.
- `research-demo-1440.png` / `research-demo-390.png` / `research-result.png`: experiment inputs and calculated results.
- `login-1440.png` / `login-390.png`: shared navigation on sign-in.

The dossier captures reuse the existing local test fixture. Research captures use the backend's explicitly synthetic demonstration. Candidate and prototype views retain their existing live, empty, or labeled sample states. The legacy workspace API still depends on its configured browser API URL and allowed origin.

## Reproduce in PowerShell

From `apps/web`:

```powershell
$env:CANDIDATEX_DIST_DIR = '.next-studio'
pnpm build
pnpm exec playwright test --reporter=line
pnpm exec next start --hostname 127.0.0.1 --port 3109
```

The optional build directory keeps this review independent of another development session using `.next`. Default builds continue to use `.next`.

With the preview and backend available, run the visual checks in a separate terminal:

```powershell
$env:VISUAL_BASE_URL = 'http://127.0.0.1:3109'
node visual-frontend.cjs
node visual-frontend-flow.cjs
```

The scripts save viewport and runtime-error reports beside the images. Initial source copies and before images are retained in this directory.
