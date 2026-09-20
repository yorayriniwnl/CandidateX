# CandidateX Release Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CandidateX reproducibly runnable and verifiably shippable as a local release with a coherent public navigation flow, deliberate live-source review, reliable backend/frontend setup, and green end-to-end acceptance tests.

**Architecture:** Preserve the existing Next.js app and FastAPI domain modules. Use the existing `PlatformHeader` navigation boundary, a public command-center route, project-local Python runtime discovery, and explicit setup/verification scripts. Keep Docker and CI entrypoints compatible while correcting the internal server URL used by the Next.js bridge.

**Tech Stack:** Next.js 16, React 19, TypeScript, Playwright, FastAPI, Python 3.12, pytest, pnpm, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-21-candidatex-release-readiness-design.md`

**Execution note (2026-09-21):** The implementation was integrated as one authorized working-tree release pass. The repository already contained an in-progress `PlatformHeader`, command-center composition, deliberate source-review disclosure, and capability snapshot; those boundaries were completed and verified rather than duplicated under the plan's earlier `PublicHeader` names. The verification script also runs `next typegen` before TypeScript so a clean `.next` directory is supported. Docker was not installed on the host, so Compose was parsed and contract-checked statically while the local release gate remained independent of Docker.

## Global Constraints

- CandidateX remains technical decision support, not an autonomous hire/reject system or validated hiring-accuracy model.
- Candidate code is never executed; repository analysis remains static and bounded.
- Missing evidence remains unknown and failed live requests never substitute synthetic results.
- `/` is the command center; `/analyze` is live evidence; `/research-demo` is synthetic; `/workspace` and `/hr` are labeled prototype/sample surfaces.
- Existing FastAPI endpoints and typed dossier/provenance contracts remain backward compatible.
- Python dependencies live in `services/backend/.venv`; local environments and build artifacts remain ignored.

## Review Focus

- A clean machine without a PATH-visible Python runtime must receive a concrete setup failure or use the project virtualenv; test with `scripts/setup.ps1` and Playwright startup.
- Root navigation and the live-analysis header must expose every public surface with correct `href` and active-page state; test with `apps/web/tests/homepage.spec.ts`.
- Public source fields must remain hidden until the user intentionally reviews them, while successful intake still exposes the existing analysis action; test with `apps/web/tests/live-analysis-ui.spec.ts`.
- A failed live request must clear a previous dossier instead of leaving stale evidence visible; test with `apps/web/tests/live-analysis.spec.ts`.
- Container/server-side bridge configuration must target the Compose service name while browser-facing legacy API calls retain the host URL; test with `docker compose config` when Docker is available and the configuration assertions in the verification script.

### Task 1: Reproducible Python and frontend setup

**Files:**
- Create: `scripts/setup.ps1`
- Create: `scripts/verify.ps1`
- Modify: `apps/web/playwright.config.ts`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: installed Python 3.12 or a compatible Python executable, `pnpm`, and the existing `services/backend/pyproject.toml` / `pnpm-lock.yaml`.
- Produces: `services/backend/.venv\Scripts\python.exe` on Windows, installed backend/frontend dependencies, Chromium, and a single verification command that exits nonzero at the first failed gate.

- [x] **Step 1: Add the setup and verification script tests as executable acceptance checks**

Run the existing backend and frontend commands with the project virtualenv explicitly selected:

```powershell
$env:CCI_PYTHON = (Resolve-Path 'services/backend/.venv/Scripts/python.exe').Path
& $env:CCI_PYTHON -m pytest services/backend/tests -q
pnpm --filter web exec tsc --noEmit --incremental false
pnpm --filter web build
```

Expected: backend, typecheck, and build are green; the current browser configuration is still allowed to fail before the runtime selection change.

- [x] **Step 2: Implement `scripts/setup.ps1`**

The script must:

```powershell
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction Stop }
& $python.Source -3.12 -m venv services/backend/.venv
& services/backend/.venv/Scripts/python.exe -m pip install --upgrade pip
& services/backend/.venv/Scripts/python.exe -m pip install -e 'services/backend[dev]'
pnpm install --frozen-lockfile
pnpm --filter web exec playwright install chromium
```

Use explicit existence checks and actionable errors for missing Python or pnpm. Do not delete an existing virtualenv.

- [x] **Step 3: Implement `scripts/verify.ps1`**

Select `services/backend/.venv/Scripts/python.exe` when it exists, set `CCI_PYTHON`, then run:

```powershell
& $python -m pytest services/backend/tests -q
pnpm --filter web exec tsc --noEmit --incremental false
pnpm --filter web build
pnpm --filter web test
```

Use `$ErrorActionPreference = 'Stop'`, print the gate name before each command, and leave Playwright artifacts in `apps/web/test-results`.

- [x] **Step 4: Make Playwright discover the same interpreter**

In `apps/web/playwright.config.ts`, resolve the repository root from `process.cwd()`, prefer the platform-specific project virtualenv path, then `CCI_PYTHON`, then `python`/`python3`. Prepend the selected interpreter directory to `PATH` so test fixtures using `execFileSync('python', ...)` resolve the same environment. Use the selected executable in the backend `webServer` command.

- [x] **Step 5: Run the setup/verification smoke checks**

Run:

```powershell
./scripts/setup.ps1
./scripts/verify.ps1
```

Expected: setup is idempotent and the verification script reaches the browser gate with the project virtualenv, not a system Python without `uvicorn`.

- [x] **Step 6: Integrate the task in the final local commit**

```powershell
git add scripts/setup.ps1 scripts/verify.ps1 apps/web/playwright.config.ts .gitignore
git commit -m "chore: make local verification reproducible"
```

### Task 2: Shared public navigation and command center

**Files:**
- Create/verify: `apps/web/components/navigation/PlatformHeader.tsx`
- Create/verify: `apps/web/components/navigation/navigation.ts`
- Create/verify: `apps/web/components/navigation/SurfaceBadge.tsx`
- Create: `apps/web/app/page.module.css`
- Create: `apps/web/app/home.module.css`
- Create: `apps/web/components/home/ExperienceCard.tsx`
- Create: `apps/web/components/home/SignalConstellation.tsx`
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/analyze/page.tsx`
- Test: `apps/web/tests/homepage.spec.ts`
- Modify: `apps/web/tests/live-analysis.spec.ts`
- Modify: `apps/web/tests/research-demo.spec.ts`

**Interfaces:**
- Consumes: Next.js `Link`, route pathname state passed by each page, and the existing page-local styles.
- Produces: `PlatformHeader({ surface, status })` with shared route links, active-page state, surface status badges, and a `Start an analysis` CTA pointing to `/analyze`.

- [x] **Step 1: Run the navigation tests to verify the current failure**

```powershell
$env:CCI_PYTHON = (Resolve-Path 'services/backend/.venv/Scripts/python.exe').Path
pnpm --filter web exec playwright test tests/homepage.spec.ts tests/live-analysis-ui.spec.ts --project=chromium
```

Expected: current `/` redirect and missing shared navigation fail the homepage assertions.

- [x] **Step 2: Complete the shared `PlatformHeader`**

Render a semantic `<header>` with a brand link, `<nav aria-label="Primary navigation">`, the shared routes, `aria-current="page"` on the active route, a mobile toggle, status badges, and a CTA link with accessible text `Start an analysis`.

- [x] **Step 3: Replace the root redirect with the command center**

Render a page that stays at `/`, has an `h1` containing `Candidate intelligence`, and presents four route cards using the exact labels tested by `homepage.spec.ts`. Include `PublicHeader` and a short statement that the four surfaces have different evidence boundaries.

- [x] **Step 4: Use `PlatformHeader` on public surfaces and align legacy route tests**

Use `PlatformHeader surface="live" status="live"` on the live page and the corresponding labeled status on research and hiring surfaces. Update the older live/research tests so they navigate to `/analyze` directly where they are testing the live flow and expect the command center at `/` where they are testing the root route.

- [x] **Step 5: Run the navigation tests**

```powershell
pnpm --filter web exec playwright test tests/homepage.spec.ts tests/live-analysis.spec.ts tests/research-demo.spec.ts --project=chromium
```

Expected: all affected navigation and existing workflow assertions pass.

- [x] **Step 6: Integrate the task in the final local commit**

```powershell
git add apps/web/app/page.tsx apps/web/app/page.module.css apps/web/app/analyze/page.tsx apps/web/components/navigation apps/web/tests
git commit -m "feat: add public command center navigation"
```

### Task 3: Deliberate source review and readable live results

**Files:**
- Modify: `apps/web/app/analyze/page.tsx`
- Modify: `apps/web/tests/live-analysis.spec.ts`
- Test: `apps/web/tests/live-analysis-ui.spec.ts`

**Interfaces:**
- Consumes: `ResumeIntake`, `LiveResult`, `CapabilitySnapshotTable`, existing `DetailedAnalysis`, and the existing live API bridge.
- Produces: an intake flow with a closed-by-default `Review public sources (optional)` disclosure and a result view headed `What the evidence shows` with the capability snapshot/audit details.

- [x] **Step 1: Run the focused UI tests to verify the current failure**

```powershell
pnpm --filter web exec playwright test tests/live-analysis-ui.spec.ts --project=chromium
```

Expected: the current initial heading, always-visible source controls, and missing capability snapshot fail.

- [x] **Step 2: Add the intentional review disclosure**

Change the initial empty-state heading to `Upload a resume to begin`. When `intake` exists, render the GitHub identity, GitHub URLs, and external URL controls inside:

```tsx
<details>
  <summary>Review public sources (optional)</summary>
  {/* existing source fields and explanatory copy */}
</details>
```

Keep the analyze button outside the disclosure so the default request remains valid with no public sources.

- [x] **Step 3: Lead results with the capability snapshot**

Immediately after the result summary, render:

```tsx
<section aria-label="Evidence summary">
  <h2>What the evidence shows</h2>
  <CapabilitySnapshotTable
    estimates={result.dossier.capability_estimates}
    selectedCapability={capability}
    onSelectCapability={setCapability}
  />
</section>
```

Keep `Technical evidence dossier` as the result summary heading for existing export/live-flow assertions, and retain the detailed analysis below it.

- [x] **Step 4: Update the live workflow test to open the source review**

In the DOCX/public-link test, click `Review public sources (optional)` before filling `Public portfolio, certificate and other links`. This asserts the new deliberate-review contract instead of bypassing it.

- [x] **Step 5: Run all live UI tests**

```powershell
pnpm --filter web exec playwright test tests/live-analysis-ui.spec.ts tests/live-analysis.spec.ts --project=chromium
```

Expected: all live UI, real upload, failure-clearing, mobile, DOCX, source receipt, and export tests pass.

- [x] **Step 6: Integrate the task in the final local commit**

```powershell
git add apps/web/app/analyze/page.tsx apps/web/tests/live-analysis.spec.ts
git commit -m "feat: make live source review deliberate and readable"
```

### Task 4: Correct deployment boundaries and image inputs

**Files:**
- Modify: `docker-compose.yml`
- Create: `.dockerignore`
- Create: `services/backend/.dockerignore`
- Modify: `README.md`
- Modify: `docs/live-resume-analysis.md`
- Modify: `docs/research-demonstration.md`

**Interfaces:**
- Consumes: the existing Compose service names, `CCI_API_URL` server-side bridge, `NEXT_PUBLIC_API_URL` browser-side legacy API base, and current Dockerfiles.
- Produces: a Compose configuration where `/research-demo` and `/api/live/*` reach the backend container internally, with local setup/verification instructions matching the scripts.

- [x] **Step 1: Add a configuration regression check**

Before changing Compose, run:

```powershell
Select-String -Path docker-compose.yml -Pattern 'CCI_API_URL|NEXT_PUBLIC_API_URL'
```

Expected: `CCI_API_URL` is absent, documenting the current deployment mismatch.

- [x] **Step 2: Fix Compose environment contracts**

Add `CCI_API_URL: http://backend:8000` to the web service, retain `NEXT_PUBLIC_API_URL: http://localhost:8000` for browser-facing legacy calls, and add a backend health dependency for web startup where Compose supports it without changing the existing public ports.

- [x] **Step 3: Add Docker ignore boundaries**

Exclude `.git`, `.venv`, `node_modules`, `.next`, test reports, research reports, local databases, and environment files from both the root web build context and backend build context. Do not exclude source, migrations, examples, or runtime configuration templates.

- [x] **Step 4: Align documentation**

Document `/` as the command center, `/analyze` as the live route, the setup/verification scripts, the two API URL roles, and the explicit limits that still cannot be called real-world validation.

- [x] **Step 5: Run static deployment checks**

```powershell
Select-String -Path docker-compose.yml -Pattern 'CCI_API_URL: http://backend:8000','NEXT_PUBLIC_API_URL: http://localhost:8000'
Get-Content .dockerignore, services/backend/.dockerignore
```

If Docker is installed, also run `docker compose config`; otherwise record Docker as environment-unverified without weakening the local release gate.

- [x] **Step 6: Integrate the task in the final local commit**

```powershell
git add docker-compose.yml .dockerignore services/backend/.dockerignore README.md docs/live-resume-analysis.md docs/research-demonstration.md
git commit -m "chore: align deployment and verification boundaries"
```

### Task 5: Full release verification and review

**Files:**
- Modify: `Makefile` if its commands do not delegate to the project virtualenv consistently.
- Modify: `.github/workflows/ci.yml` only if CI does not exercise the same setup/verification contracts.

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: a clean local release verification record and a final self-review of the complete branch.

- [x] **Step 1: Run the complete verification command**

```powershell
./scripts/verify.ps1
```

Expected: backend tests, frontend typecheck, production build, and all Playwright tests pass with zero failures.

- [x] **Step 2: Run the research and live smoke checks**

```powershell
& services/backend/.venv/Scripts/python.exe research/run_paper_experiments.py --quick --output-dir reports/research-demo-verification
& services/backend/.venv/Scripts/python.exe scripts/smoke_test.py
```

Expected: the quick research experiment completes; the smoke test either verifies running services or reports the exact missing service without claiming deployment success.

- [x] **Step 3: Run a final source/config review**

```powershell
rg -n -i 'TODO|FIXME|TBD|localhost:8000|127.0.0.1:8000|NEXT_PUBLIC_API_URL|CCI_API_URL' apps services scripts docker-compose.yml README.md docs
git diff --check
git status --short
```

Resolve new actionable placeholders and whitespace errors; keep documented localhost defaults only where they are intentional development defaults.

- [x] **Step 4: Integrate final verification documentation in the local commit**

```powershell
git add Makefile .github/workflows/ci.yml docs reports
git commit -m "chore: record release verification"
```
