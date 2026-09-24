# CandidateX Synthetic-Only Public Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CandidateX’s production deployment a bounded synthetic-only public demo while keeping the live analysis workflow available only in local development.

**Architecture:** A dedicated FastAPI production app mounts only a health endpoint and a strict synthetic-demo API. Its run and rescore endpoints regenerate evidence from allowlisted simulation controls, avoiding candidate data and process-local run state. Next.js redirects production entry routes to the demo and blocks live-analysis proxies, while development continues to use the existing full local API.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, existing CCI scorer and graph builder, Next.js 16 App Router, TypeScript, Playwright, pnpm, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-23-synthetic-only-public-demo.md`

## Global Constraints

- The production backend exposes only health and bounded synthetic-demo operations.
- No deployed production route accepts resumes, candidate profiles, candidate identifiers, or arbitrary candidate-linked text.
- The real-candidate analysis app remains available only through the explicit local-development entrypoint.
- In production builds, `/`, `/analyze`, `/hr`, and `/workspace` redirect to `/research-demo`.
- The synthetic demo continues to run, inspect, export, and rescore actual backend-generated synthetic results.
- Run and rescore work without relying on process-local state surviving between serverless requests.
- Preserve the current synthetic evidence-generation and scoring math; this release does not calibrate or validate it.
- Do not add authentication, tenant isolation, candidate persistence, retention/deletion workflows, payments, or company accounts.
- Do not claim employment-law compliance, fairness validation, predictive validity, or SaaS readiness.

## Review Focus

1. A request that sneaks in `candidate_id`, resume text, profile URLs, or job-description text must receive HTTP 422. Pin this in Task 1’s strict-request tests.
2. A rescore reaching a fresh backend process must still work without a prior run in that process. Pin this in Task 1 by making any `PipelineService.rescore_run` call fail the test. A failed/incomplete pipeline must return an error, never a sample dossier.
3. Empty synthetic evidence must remain unknown (`rci is None`, coverage `0`), not turn into a zero-capability claim. Pin this in Task 1’s empty-scenario test.
4. Production aliases and `/api/live/*` must not reveal the legacy workflow or forward live requests. Pin this in Task 2’s production Playwright tests.
5. A production/Vercel build without `CCI_API_URL` must fail closed, while local development retains its loopback fallback. Pin both cases in Task 2’s backend-URL helper tests.

## Files and Boundaries

- `services/backend/src/cci/api/routers/synthetic_demo.py` defines the allowlisted synthetic request contracts and stateless run/rescore handlers.
- `services/backend/src/cci/synthetic_demo_app.py` is the production FastAPI app; `services/backend/app.py` is its Vercel entrypoint.
- `services/backend/src/cci/main.py` also mounts the strict synthetic router for the local frontend, without removing its existing local-only APIs.
- `apps/web/lib/server/cci-backend.ts` centralizes deployment-mode detection and backend URL resolution for Next route handlers.
- `apps/web/next.config.mjs` contains production-only redirects. The `/api/live/[operation]` handler blocks before reading or forwarding a request in production.
- `apps/web/playwright.config.ts` remains the local-development suite; `apps/web/playwright.production.config.ts` starts the production build and production FastAPI entrypoint for release-boundary smoke tests.
- `apps/web/app/research-demo/page.tsx` and `apps/web/lib/research-demo.ts` expose only synthetic controls and keep the existing backend-generated result/graph/export experience.
- `docs/live-resume-analysis.md` distinguishes the production synthetic demo from local live analysis.

---

### Task 1: Isolated Stateless Synthetic Backend

**Files:**
- Create: `services/backend/src/cci/api/routers/synthetic_demo.py`
- Create: `services/backend/src/cci/synthetic_demo_app.py`
- Create: `services/backend/tests/test_synthetic_demo_app.py`
- Modify: `services/backend/app.py`

**Interfaces:**
- `SyntheticDemoControls` accepts `scenario`, `role`, `excluded_sources`, `ownership_multiplier`, and `reliability_false_positives`; its Pydantic config forbids extra fields.
- `SyntheticDemoRescoreRequest` extends those controls with validated `weights: dict[CapabilityKey, float]`.
- `synthetic_demo_router` is mounted at `/api/v1/synthetic-demo`, with `POST /run` and `POST /rescore`.
- The Vercel `app.py` imports `cci.synthetic_demo_app:app`. A later web-contract task mounts the same strict router in local `cci.main:app` so the local demo uses the same API contract.

- [x] **Step 1: Write route-boundary and strict-input tests**

Create `services/backend/tests/test_synthetic_demo_app.py` and import the actual Vercel module (`from app import app`). Add these parameterized checks before implementation:

```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

@pytest.mark.parametrize(("method", "path"), [
    ("POST", "/api/v1/live/intake"),
    ("POST", "/api/v1/live/analyze"),
    ("GET", "/api/v1/candidates"),
    ("GET", "/api/v1/jobs"),
    ("GET", "/api/v1/dossier/11111111-1111-1111-1111-111111111111"),
    ("POST", "/api/v1/pipeline/run"),
    ("POST", "/api/v1/overrides/interview-feedback"),
])
def test_vercel_app_does_not_mount_live_or_persistent_apis(method, path):
    response = client.request(method, path, json={})
    assert response.status_code == 404

@pytest.mark.parametrize("extra", [
    {"candidate_id": "11111111-1111-1111-1111-111111111111"},
    {"resume_text": "Example person"},
    {"github_urls": ["https://github.com/example"]},
    {"linkedin_url": "https://linkedin.com/in/example"},
    {"jd_text": "Candidate Alice"},
])
def test_public_demo_rejects_candidate_data_fields(extra):
    response = client.post(
        "/api/v1/synthetic-demo/run", json={"scenario": "consistent", **extra}
    )
    assert response.status_code == 422
```

- [x] **Step 2: Run the new tests and confirm they fail for the current live Vercel app**

Run from `services/backend`: `pytest tests/test_synthetic_demo_app.py -q`.

Expected: failures show the existing Vercel app exposes `/api/v1/live/*`, and the synthetic-only module/routes do not yet exist.

- [x] **Step 3: Implement strict controls and a stateless synthetic run/rescore router**

In `synthetic_demo.py`, define `PUBLIC_DEMO_CANDIDATE_ID = UUID("d3333333-3333-4333-8333-333333333333")`, strict Pydantic models, and a helper that maps allowlisted controls into the existing `DemoRequest`, calls `make_scenario`, then calls `execute_analysis_pipeline` directly with `evidence_mode="synthetic"`. Do not call `pipeline_service.start_pipeline` or `pipeline_service.rescore_run`.

The run handler returns the existing `DemoResult` shape (`dossier`, `graph`, `graph_snapshot`, `input`, `evidence_digest`, `scenario_version`, `scoring_config`, `reliability`, `stages`, `benchmark_scope`, and `storage_notice`). `input` contains only allowlisted controls. Set `storage_notice` to state that the synthetic scenario is regenerated per request and no candidate data or run state is stored; do not reuse the existing process-local-registry warning. The rescore handler reconstructs the same synthetic evidence from its controls, calls `rescore_dossier` with the validated weights and the constant justification `Synthetic demonstration weight override`, then returns the updated dossier and graph. Return HTTP 500 on an incomplete pipeline state and HTTP 422 on invalid weights; never substitute a stored or fabricated result.

```python
class SyntheticDemoControls(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: Literal["consistent", "sparse", "low_ownership", "conflicting", "empty"] = "consistent"
    role: CanonicalRole = CanonicalRole.BACKEND
    excluded_sources: list[SourceFamily] = Field(default_factory=list, max_length=7)
    ownership_multiplier: float = Field(default=1, ge=0, le=1)
    reliability_false_positives: int = Field(default=0, ge=0, le=100)

class SyntheticDemoRescoreRequest(SyntheticDemoControls):
    weights: dict[CapabilityKey, float]

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, weights):
        if not weights or any(not math.isfinite(value) or value < 0 for value in weights.values()) or sum(weights.values()) <= 0:
            raise ValueError("Supply finite non-negative weights with a positive total")
        return weights
```

Use a helper signature `build_synthetic_state(controls: SyntheticDemoControls) -> tuple[PipelineExecutionState, list[EvidenceRecord], dict[SourceFamily, Any]]`. It constructs the fixed-ID internal `DemoRequest`, calls `make_scenario`, and calls `execute_analysis_pipeline` with only those generated records. The run and rescore handlers must both use this helper.

- [x] **Step 4: Test generated evidence, explicit unknowns, failure behavior, and stateless rescore**

Add a populated `consistent` run test proving generated synthetic evidence is present, the response uses the fixed candidate UUID, and the graph run ID matches the dossier. Add an `empty` run test proving `evidence_mode == "synthetic"`, the fixed candidate UUID, `rci is None`, and `coverage == 0`. Stub pipeline execution to return an incomplete state and assert HTTP 500 with no dossier/result substituted. Add a rescore test that never calls `/run` and monkeypatches `pipeline_service.rescore_run` to `pytest.fail`; assert HTTP 200 and matching `graph.analysis_run_id == dossier.analysis_run_id`. Add empty- and negative-weight tests returning HTTP 422.

- [x] **Step 5: Wire the Vercel production entrypoint and run focused regression tests**

Create `synthetic_demo_app.py` with only the synthetic router and `/health`. Change `services/backend/app.py` to import that app. Keep `cci.main` unchanged in this task so the existing local frontend remains compatible until the web contract is updated in Task 2.

Run from `services/backend`: `pytest tests/test_synthetic_demo_app.py tests/test_live_boundaries.py tests/test_research_demonstration.py -q`.

Expected: all new production-boundary/stateless tests and existing local live/research tests pass.

- [x] **Step 6: Commit and push this completed backend task**

```powershell
git add services/backend/app.py services/backend/src/cci/api/routers/synthetic_demo.py services/backend/src/cci/synthetic_demo_app.py services/backend/tests/test_synthetic_demo_app.py
git commit -m "feat: isolate synthetic production backend"
git push origin HEAD
```

### Task 2: Fail-Closed Production Web Boundary

**Files:**
- Create: `apps/web/lib/server/cci-backend.ts`
- Create: `apps/web/tests/cci-backend.spec.ts`
- Create: `apps/web/playwright.production.config.ts`
- Create: `apps/web/tests/production-demo.spec.ts`
- Modify: `apps/web/app/research-demo/page.tsx`
- Modify: `apps/web/lib/research-demo.ts`
- Modify: `apps/web/tests/research-demo.spec.ts`
- Modify: `services/backend/src/cci/main.py`
- Modify: `apps/web/app/api/live/[operation]/route.ts`
- Modify: `apps/web/app/api/demo/route.ts`
- Modify: `apps/web/next.config.mjs`
- Modify: `apps/web/playwright.config.ts`
- Modify: `apps/web/package.json`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- `isSyntheticOnlyDeployment(env = process.env): boolean` returns true for `NODE_ENV === "production"` or a nonempty Vercel deployment marker.
- `resolveCciBackendUrl(env = process.env): string | null` returns configured `CCI_API_URL`, returns `null` for an unconfigured production/Vercel environment, and uses `http://127.0.0.1:8000` only in local development.
- `DemoInput` contains only scenario, role, excluded sources, ownership multiplier, and false-positive count. Rescore sends those fields plus weights; the backend supplies identity and justification.
- The existing Playwright config tests local development (`next dev` plus `cci.main`); the production config tests `next start` plus the Vercel FastAPI entrypoint.

- [x] **Step 1: Write deployment-mode helper tests**

Create `apps/web/tests/cci-backend.spec.ts` and pin production fail-closed behavior and local compatibility:

```ts
import { expect, test } from '@playwright/test';
import { resolveCciBackendUrl } from '../lib/server/cci-backend';

test('does not invent a localhost backend for production or Vercel', () => {
  expect(resolveCciBackendUrl({ NODE_ENV: 'production' })).toBeNull();
  expect(resolveCciBackendUrl({ NODE_ENV: 'development', VERCEL: '1' })).toBeNull();
});

test('keeps the loopback fallback for local development only', () => {
  expect(resolveCciBackendUrl({ NODE_ENV: 'development' })).toBe('http://127.0.0.1:8000');
  expect(resolveCciBackendUrl({ NODE_ENV: 'production', CCI_API_URL: 'https://api.example.test/' }))
    .toBe('https://api.example.test');
});
```

Also add `public synthetic demo rejects real-data inputs and legacy routes` to `apps/web/tests/research-demo.spec.ts`. Assert there are no `Job description` or `Override justification` inputs and no `Prototype workspace` link; assert the page explicitly identifies generated observations and says results are not validated for hiring; keep the scenario, role, empty-evidence, override, and export assertions. Add production checks in `production-demo.spec.ts` for all four route aliases, blocked live API calls, synthetic-only/non-hiring copy, and a full synthetic run/rescore flow.

- [x] **Step 2: Run the helper tests and confirm they fail before the helper exists**

Run from `apps/web`:

```powershell
pnpm exec playwright test tests/cci-backend.spec.ts
pnpm exec playwright test tests/research-demo.spec.ts --grep "public synthetic demo rejects real-data inputs and legacy routes"
```

Expected: helper test module/import failure, and the browser regression fails because the existing page still exposes free-text fields and the workspace link.

- [x] **Step 3: Add the shared backend resolver and guard both API bridges**

Implement the tested helper in `apps/web/lib/server/cci-backend.ts`. Make `/api/live/[operation]` return HTTP 404 with `Cache-Control: no-store` before reading the body or calling `fetch` whenever `isSyntheticOnlyDeployment()` is true. Make `/api/demo` return HTTP 503 when `resolveCciBackendUrl()` returns `null`; otherwise proxy the allowlisted `run`/`rescore` operation to `/api/v1/synthetic-demo/{operation}`. Preserve the existing 127.0.0.1 fallback only for local development. Mount `synthetic_demo_router` in `cci.main` under its independent `/api/v1/synthetic-demo` prefix; retain the old local research-demo endpoints for local tests and users.

- [x] **Step 4: Add temporary production redirects and keep development routes intact**

Read the installed Next.js guides named in `apps/web/AGENTS.md` before editing: `apps/web/node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/redirects.md` and `apps/web/node_modules/next/dist/docs/01-app/01-getting-started/15-route-handlers.md`.

In `next.config.mjs`, return redirects only when `process.env.NODE_ENV === "production"`:

```js
async redirects() {
  if (process.env.NODE_ENV !== 'production') return [];
  return ['/', '/analyze', '/hr', '/workspace'].map(source => ({
    source,
    destination: '/research-demo',
    permanent: false,
  }));
}
```

Change the existing Playwright web server to `next dev` so its live-analysis tests continue to verify the local-only workflow. Create a production Playwright config that matches only `production-demo.spec.ts`, starts `python -m uvicorn app:app --app-dir ../../services/backend --host 127.0.0.1 --port 8018` and `pnpm exec next start --hostname 127.0.0.1 --port 3109`, with `CCI_API_URL=http://127.0.0.1:8018` for the frontend. Do not let the production config run local-only `live-analysis.spec.ts` tests.

Update `research-demo.ts` so `DemoInput` excludes `candidate_id` and `jd_text`; export the fixed public synthetic ID. In `research-demo/page.tsx`, remove the free-text JD and override-justification fields, remove the requirements view that depended on custom JD text, and remove the `/workspace` navigation link. Keep the role/scenario/source/ownership/reliability controls and the evidence/uncertainty/graph/export experience. Build rescore requests from `result.input` plus weights, without a process-local `run_id`:

```ts
const revised = await demoRequest<Pick<DemoResult, 'dossier' | 'graph' | 'graph_snapshot'>>(
  'rescore',
  { ...result.input, weights: { [overrideCap]: 1 } },
);
if (revised.dossier.candidate_id !== SYNTHETIC_CANDIDATE_ID ||
    revised.graph.analysis_run_id !== revised.dossier.analysis_run_id) {
  throw new Error('Synthetic result identity mismatch.');
}
```

Update visible copy to say observations are generated, resumes/profiles are not accepted, no real person is assessed, and the prototype is not a validated hiring predictor. Use fixed server-supplied demo wording for override history.

- [x] **Step 5: Write and run production route tests**

In `production-demo.spec.ts`, verify each of `/`, `/analyze`, `/hr`, and `/workspace` ends at `/research-demo`, and POSTs to `/api/live/intake` and `/api/live/analyze` receive HTTP 404. Confirm the demo page renders with synthetic-only/non-hiring copy, runs a synthetic scenario, then rescales it successfully using only the allowlisted controls. Assert the synthetic identity and graph/dossier run IDs match. The test must run against the built production server, not `next dev`.

Run after a web build: `pnpm --filter web exec playwright test --config=playwright.production.config.ts tests/production-demo.spec.ts`.

Expected: all route aliases resolve to the demo; live API operations remain blocked despite `CCI_API_URL` being set; synthetic run and stateless rescore succeed.

- [x] **Step 6: Add the production browser suite to package scripts and CI**

Add `"test:production": "playwright test --config=playwright.production.config.ts"` to `apps/web/package.json`. In `.github/workflows/ci.yml`, run `pnpm --filter web run test:production` after `pnpm --filter web build` and Playwright browser installation, before or alongside the local-development Playwright suite.

- [x] **Step 7: Run local and production route suites, then commit and push**

Run from the repository root:

```powershell
pnpm --filter web exec playwright test tests/cci-backend.spec.ts
pnpm --filter web build
pnpm --filter web run test:production
pnpm --filter web test
```

Expected: helper tests pass; the production build redirects and blocks live routes; local live-analysis Playwright tests continue to pass.

```powershell
git add apps/web/lib/server/cci-backend.ts apps/web/tests/cci-backend.spec.ts apps/web/playwright.production.config.ts apps/web/tests/production-demo.spec.ts apps/web/app/research-demo/page.tsx apps/web/lib/research-demo.ts apps/web/tests/research-demo.spec.ts services/backend/src/cci/main.py 'apps/web/app/api/live/[operation]/route.ts' apps/web/app/api/demo/route.ts apps/web/next.config.mjs apps/web/playwright.config.ts apps/web/package.json .github/workflows/ci.yml
git commit -m "feat: make hosted demo synthetic-only"
git push origin HEAD
```

### Task 3: Hosting Documentation

**Files:**
- Modify: `docs/live-resume-analysis.md`

**Interfaces:**
- Documentation names `services/backend/app.py` as the synthetic-only Vercel entrypoint and `cci.live_app:app` as the local live-analysis entrypoint.

- [x] **Step 1: Update the hosting guide to describe the production boundary**

In `docs/live-resume-analysis.md`, label the resume/profile workflow local-development-only. Keep the local command using `cci.live_app:app`. Replace the current hosting instructions that deploy `app.py` as live analysis with instructions that `services/backend/app.py` serves the synthetic demo and the frontend’s `/research-demo` is the only production product flow. State that the synthetic API accepts no candidate identity, resume/profile URLs, job description, or user-written override note, and that this is not a validated hiring predictor or multi-tenant SaaS.

- [x] **Step 2: Review the guide against the code and run whitespace validation**

Run `git diff --check`, then confirm each production API path, local startup command, and `CCI_API_URL` requirement in the guide matches the actual source and deployment configuration.

- [x] **Step 3: Commit and push the documentation task**

```powershell
git add docs/live-resume-analysis.md
git commit -m "docs: clarify synthetic production hosting"
git push origin HEAD
```

### Task 4: Full Verification and Release Preflight

**Files:**
- No planned source changes. If verification requires a fix, add a focused regression test and complete it in the owning task before continuing.

**Interfaces:**
- The release candidate is the pushed feature branch containing the three task commits.
- Production promotion requires a verified Vercel project/environment and must use the built production app described above; do not point production at `cci.live_app`.

- [x] **Step 1: Run complete backend verification**

From `services/backend`, run `pytest -v --durations=10`.

Expected: all backend tests pass, including the new production route boundary, strict-input, stateless rescore, empty-evidence, and existing local-live tests.

- [x] **Step 2: Run complete web verification from the repository root**

Run `pnpm --filter web lint`, `pnpm --filter web build`, `pnpm --filter web run test:production`, and `pnpm --filter web test`. Run `git diff --check` afterward.

Expected: typecheck, production build, production-route/demo browser tests, local live/demo browser tests, and whitespace checks all pass.

- [x] **Step 3: Host and inspect the local development flow**

Use the existing local-development commands from `docs/live-resume-analysis.md` and the Playwright dev-server configuration. Confirm the synthetic demo is reachable and that the local-only `/analyze` route remains functional. Do not replace or stop another process already serving port 3000; use an unused loopback port for this worktree if port 3000 is occupied.

- [x] **Step 4: Check deployment target before any production promotion**

Inspect the linked Vercel project and production environment. Confirm the frontend’s `CCI_API_URL` targets the separately deployed backend whose `services/backend/app.py` imports `cci.synthetic_demo_app:app`. If the Vercel team/project, project link, or required environment is still unavailable, stop before production promotion and report exactly what the user needs to connect. Do not invent a Vercel project, expose credentials, or claim deployment success from a local build.

- [ ] **Step 5: Verify deployed production routes after promotion is authorized and configured**

If the verified project is available, deploy the candidate using the repository’s configured Vercel project and run the production Playwright/smoke checks against the resulting production URL. Verify `/`, `/analyze`, `/hr`, and `/workspace` resolve to `/research-demo`; verify `/api/live/*` is blocked; run one synthetic scenario and a stateless rescore; inspect deployment status and error logs. If any boundary check fails, do not announce production success.

- [x] **Step 6: Report completed commits, checks, local URL, and deployment state**

List each pushed commit and test command with its actual result. State whether production was deployed or remains blocked by Vercel access/configuration. Do not describe this synthetic demo as a production hiring SaaS.
