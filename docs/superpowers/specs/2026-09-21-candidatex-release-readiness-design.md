# CandidateX Release Readiness Design

## Goal

Make CandidateX reproducibly runnable and verifiably shippable as a local release, while preserving its ethical boundary: it is technical decision support based on supplied evidence, not an autonomous hiring decision-maker or a validated predictor of job performance.

## Current contract

CandidateX has two distinct product surfaces:

- `/` is the public command center that routes people to Live Evidence, the prototype Evaluation Workspace, the Hiring View, and the Research Lab.
- `/analyze` is the request-scoped live resume workflow. It accepts a PDF or DOCX, lets the user review extracted public sources, performs bounded static acquisition, and shows traceable evidence, unknowns, limits, and exports.
- `/research-demo` is the synthetic paper demonstration. It must never substitute a synthetic result for a failed live request.
- `/workspace` and `/hr` remain available as explicitly labeled prototype/sample surfaces.

The backend exposes the existing FastAPI contracts and keeps candidate code static-only. Missing evidence remains unknown, provenance remains visible, and public-link access does not itself increase capability scores.

## Architecture and folder boundaries

Keep the existing domain-oriented backend and app/service split. Tighten the boundaries that are currently scattered:

```
apps/web/
  app/                         Next.js routes and route-local styles
  components/navigation/      Shared public navigation and command-center links
  components/                 Product components grouped by feature
  lib/                         Browser/server API clients and typed workflow helpers
  tests/                       Playwright acceptance tests
services/backend/
  src/cci/                     FastAPI app and domain modules
  tests/                       Backend unit, integration, security, and research tests
scripts/                       Reproducible setup, verification, and operational helpers
docs/                          Product, contract, deployment, and verification guides
research/                      Separate executable experiments and committed artifacts
examples/                      Deterministic CV/JD fixtures
```

Do not move backend domain modules or duplicate TypeScript/Python contracts merely to make the tree look different. The structural change is focused on shared navigation and explicit operational tooling; root Docker and CI entrypoints remain compatibility entrypoints.

## Operational design

1. `scripts/setup.ps1` discovers the installed Python 3.12 interpreter, creates `services/backend/.venv`, installs the backend editable package with development extras, installs the locked pnpm workspace, and installs Chromium for Playwright.
2. `scripts/verify.ps1` selects the project virtualenv, runs the full backend suite, frontend typecheck, production build, and browser acceptance suite in that order, stopping on the first failure.
3. Playwright automatically prefers the project virtualenv when it exists and otherwise uses the CI/system Python. This removes the current mismatch where the web server finds a Python interpreter without `uvicorn`.
4. Docker configuration uses separate internal and browser-facing URLs: the Next.js server-side bridge reaches `http://backend:8000`, while browser-side legacy API calls retain the host-facing URL.
5. Docker ignore files exclude local environments, dependency trees, build output, reports, and test artifacts from images.

## UI design

- A shared `PlatformHeader` owns the public route links, active-page state, mobile navigation, and surface status badge.
- The command center uses plain route cards with explicit labels and a heading containing “Candidate intelligence”.
- The live intake begins with “Upload a resume to begin”. After intake, public source fields are hidden inside a “Review public sources (optional)” disclosure so the user deliberately reviews what will be fetched.
- Completed live results lead with “What the evidence shows” and a capability snapshot table. “Readiness” and “Next step” are visible actions; confidence intervals and observation counts remain behind “Show audit details”.
- Existing detailed analysis, source receipts, provenance, export, mobile layout, and ethical limitation copy remain intact.

## Error handling and safety

- Setup scripts fail with an actionable message when Python, pnpm, or the virtualenv cannot be created.
- Verification reports the exact failing stage and preserves Playwright artifacts.
- Backend and frontend bridges keep request-scoped failure behavior; no stale dossier or synthetic fallback is shown after a failed request.
- No new endpoint broadens identity discovery, storage, or candidate-code execution.

## Verification gates

The release gate is:

```text
backend pytest suite = green
frontend TypeScript check = green
Next.js production build = green
Playwright browser suite = green
```

Container execution is an additional environment-dependent gate. If Docker is unavailable, local process verification must still pass and the limitation must be recorded rather than hidden. Real-world hiring accuracy, issuer authentication, and independently validated ownership remain explicitly out of scope.
