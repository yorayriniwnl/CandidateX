# CandidateX Synthetic-Only Public Demo

**Status:** Proposed for user review
**Scope:** Production release boundary for the public CandidateX deployment

## Understanding and success criteria

The approved release is a public, interactive demonstration using only generated synthetic observations. It is not a customer workspace, candidate assessment service, or multi-tenant SaaS release.

Success means:

- the production backend exposes only health and bounded synthetic-demo operations;
- no deployed production route accepts resumes, candidate profiles, candidate identifiers, or arbitrary candidate-linked text;
- the real-candidate analysis app remains available only through the explicit local-development entrypoint;
- `/`, `/analyze`, `/hr`, and `/workspace` lead to the synthetic demonstration in production, while local development retains its existing routes;
- the synthetic demo continues to run, inspect, export, and rescore actual backend-generated synthetic results;
- run and rescore work without relying on process-local state surviving between serverless requests;
- interface and documentation accurately state that the data are simulated, the system is a research prototype, and its output is not validated for hiring decisions.

## Current code context

The Vercel FastAPI entrypoint is `services/backend/app.py`, which currently imports `cci.live_app:app`. That app mounts the request-scoped resume intake and live profile-analysis routes plus the synthetic research-demo router. It deliberately omits the larger database-backed candidate directory, but its live routes still process real resumes and user-supplied public profile URLs.

The Next.js app currently links its landing page to `/analyze`, exposes a legacy `/hr` dashboard and `/workspace`, and provides `/research-demo`. The research demo generates synthetic evidence through the actual CCI scorer, but currently accepts a caller-supplied candidate UUID, free-text job description, and free-text override justification. Its rescore endpoint retrieves a prior run from `pipeline_service`, a process-local registry that is not a reliable cross-request store in a serverless deployment.

## Production application boundary

Add a dedicated production demo FastAPI app and make `services/backend/app.py` import it. The app mounts only:

- a liveness endpoint;
- synthetic demonstration run and rescore endpoints.

It must not mount the live intake/analyze router, database-backed candidate/job/dossier/pipeline/override APIs, or research APIs beyond those required by the synthetic demonstration. Preserve `cci.live_app:app` and `cci.main:app` as explicit local-development/test entrypoints; do not weaken their existing local functionality as a side effect of the production boundary.

Use strict request contracts for the public demo. Accept only the preset scenario, canonical role, source-family toggles, and bounded numeric simulation controls required by the existing interface. Assign a fixed synthetic candidate identity on the server. Do not accept resume bytes, profile URLs, arbitrary candidate identifiers, free-text job descriptions, or free-text rescore justifications. Reject unexpected request fields rather than silently ignoring them. The public rescore operation uses a fixed demonstration justification.

Keep rescore stateless: reconstruct the dossier from the bounded synthetic controls on each rescore request, apply the requested valid role weights, and return the rescored dossier and graph. Do not use or require `PipelineService` run-cache state for production demo requests. This prevents a normal run/rescore pair from failing merely because separate serverless invocations reach different instances.

## Web routes and public copy

In production builds, redirect `/`, `/analyze`, `/hr`, and `/workspace` to `/research-demo`. Keep their existing local-development behavior. Remove the research-demo navigation link to the prototype workspace so the public demo has no route back into the legacy hiring UI.

The demo controls remain interactive for synthetic scenarios, role selection, source-family inclusion, ownership simulation, and reliability false-positive simulation. Remove free-text job-description and rescore-justification controls. Keep visible copy explaining that all candidate observations are generated, no resume or profile is processed, no real person is assessed, and the output is not a hiring recommendation or validated predictor. Update hosting documentation to distinguish the production demo entrypoint from local live analysis.

The Next.js live-analysis proxy must fail closed in production even if `CCI_API_URL` points to a backend that has live-analysis routes. The synthetic-demo bridge must also fail closed when a production `CCI_API_URL` is missing; it must not fall back to localhost. Local development may continue to use the existing proxies. The production FastAPI app remains the independent server-side boundary; a frontend-only redirect is not considered sufficient.

## Compatibility and non-goals

- Preserve the current synthetic evidence-generation and scoring math; this release does not calibrate or validate it.
- Preserve local live resume/profile analysis for development and tests, but never use that entrypoint for the production deployment.
- Do not add authentication, tenant isolation, candidate persistence, retention/deletion workflows, payments, or company accounts.
- Do not claim employment-law compliance, fairness validation, predictive validity, or SaaS readiness.
- Do not add a database, Redis, or another shared-state dependency for demo rescoring.
- Do not rewrite Git history or remove prior public repository commits as part of this change.

## Acceptance criteria

### Backend

- Importing the production Vercel entrypoint exposes health and synthetic-demo routes, and returns not-found for `/api/v1/live/intake`, `/api/v1/live/analyze`, `/api/v1/candidates`, `/api/v1/jobs`, `/api/v1/dossier`, `/api/v1/pipeline`, and `/api/v1/overrides`.
- A valid synthetic run returns `evidence_mode=synthetic`, the fixed synthetic candidate identity, and a graph associated with the returned run.
- A public run request containing a candidate UUID, resume/profile fields, or custom JD text is rejected with a client error.
- A valid rescore succeeds without a preceding run in the same process and returns a graph whose run identity matches the rescored dossier.
- Invalid rescore weights and unexpected personal-data fields are rejected; failed operations never substitute sample output.
- Existing local live-analysis and backend regression tests continue to pass.

### Web and documentation

- A production build routes `/`, `/analyze`, `/hr`, and `/workspace` to `/research-demo`; local development still serves the existing local pages.
- Production `/api/live/intake` and `/api/live/analyze` return a clear unavailable/disabled response without forwarding the request upstream; the demo bridge does not silently fall back to localhost in a Vercel deployment.
- The research demo submits only bounded synthetic controls, removes user-entered candidate-linked text, and has no link to the legacy workspace.
- Browser tests verify the public synthetic flow, explicit synthetic labeling, live-route blocking, route redirects, and no regressions in run/rescore/export behavior.
- Documentation states the production demo boundary and keeps local live-analysis instructions explicitly local-only.

## Release caveats

This work makes the public hosted surface a synthetic-data demonstration; it does not make CandidateX a production hiring product or a secure multi-tenant SaaS. Keep the commercial-readiness no-go statement for real hiring use. A Vercel production target and project connection are still required before promotion; no deployment should be claimed until the actual production deployment and its routes are verified.
