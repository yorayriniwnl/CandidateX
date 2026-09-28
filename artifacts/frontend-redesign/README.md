# CandidateX frontend verification

The homepage's warm dark surfaces and lavender accents extend through analysis, candidate management, the prototype workspace, research, and sign-in. The finishing pass fixes narrow-screen controls, candidate role selection, modal labels and focus restoration, comparison empty states, and reduced-motion behavior.

Research benchmark caveats and deterministic evidence-quality details from the current main branch are preserved. Missing evidence remains unknown; report metrics still come from the analysis response.

## Verified on September 28, 2026

The production build, lint, and all 57 browser workflow tests passed. The visual checks covered 35 page or workflow widths from 320px to 1440px with no page overflow or browser runtime errors. The dossier capture was refreshed after fixing the mobile score dial, and its 390px screenshot was visually inspected.

Regression coverage includes keyboard comparison selection, clearing a selection while a dossier response is pending, retained candidate roles, dialog focus restoration, and workspace controls at 320px. HR sample-data checks explicitly select the sample fallback so a developer's saved candidates cannot change the expected rows.

## Run the checks

From the repository root, with the workspace and backend dependencies installed:

```powershell
pnpm --filter web lint
pnpm --filter web build
pnpm --filter web test
pnpm --filter web exec playwright test --config playwright.visual.config.ts
```

The browser harness starts and stops its own local web and backend servers. Set `PLAYWRIGHT_WEB_PORT` and `PLAYWRIGHT_API_PORT` before testing if their defaults (3108 and 8017) are occupied. CI's software WebGL renderer settings remain enabled.

For a build independent of another development session, set `CANDIDATEX_DIST_DIR=.next-studio` before both the build and browser checks. The default remains `.next`.

## Local captures

The visual harness saves screenshots and JSON reports in this directory, outside version control:

- `analyze`, `hr`, `workspace`, `research-demo`, and `login`: desktop and 390px screenshots, plus overflow checks at 1440, 1024, 768, 390, and 320px.
- `add-candidate` and `workspace-evaluation`, `workspace-compare`, `workspace-methodology`: supporting controls.
- `layout-report.json`: page widths and browser runtime errors. Wide tables may scroll within their own containers; the page must remain within the viewport.

The optional dossier capture needs a locally saved analysis response (`live-result.json`, including its `intake`) and the corresponding `resume.pdf`. Use a synthetic resume and set `VISUAL_FIXTURE_DIR` to that directory before running the visual harness. Without it, only the dossier replay is skipped. The regular workflow tests have their own fixtures and do not require these files.

The dossier script saves the guided role/source/review steps, pending request, desktop and mobile dossier, evidence inspector, and `flow-report.json`. It replays the supplied response; it does not claim a fresh repository scan. Research results are computed by the running backend using its explicitly synthetic demonstration.

The legacy prototype workspace uses its configured `NEXT_PUBLIC_API_URL` and allowed browser origin. Capturing its empty or sample states does not verify a deployed database. Demo sign-in and missing OAuth configuration are covered by browser tests; live provider sign-in is outside this local check.
