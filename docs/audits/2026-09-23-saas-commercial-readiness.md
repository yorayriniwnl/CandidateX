# CandidateX SaaS commercial readiness audit

**Review date:** 2026-09-23  
**Reviewed branch:** codex/candidatex-saas-readiness  
**Reviewed commit:** ab4230a, based on origin/main baa559f  
**Verdict:** Not ready for a commercial multi-tenant launch or customer applicant data.

## Scope

This review covered the merged backend-hardening and Evidence OS branches, backend and frontend API wiring, candidate and dossier persistence paths, deployment configuration, demo data, current public pages, and the available automated checks. The public production source commit was not confirmed, so production behavior is reported separately from the branch under review.

## Branch currency

The pushed Evidence OS tip `a456eb8ff24f5d762fc6be22bb53b254ccce0794` is included in the reviewed merge. The pushed backend-hardening tip `4c012cf9f884b21cd930f5f4ce8ca721a10fbd87` adds only `docs/superpowers/specs/2026-09-23-negative-evidence-design.md` on top of backend code commit `b3b1ead1a8c5c80be9543266d831b91f52c923b4`, which is already included in the reviewed merge. It does not change the audited backend implementation. Any unpublished backend-task changes are outside this review and need a follow-up audit if pushed.

## Verification completed

- Backend test suite: full suite passed.
- Web TypeScript check through the lint script: passed.
- Next.js production build: passed.
- Playwright browser suite: 23 of 23 passed.
- Production JavaScript dependency audit: no known vulnerabilities reported.
- The branch contains the backend-hardening commits and the merged Evidence OS work. The combined candidate branch was pushed to origin.

Node commands printed a warning that the configured Kaspersky root certificate file could not be loaded. The Python suite also printed upstream deprecation warnings for the HTTP test client and Alembic path configuration.

## Launch blockers

### Critical: no authenticated user or server-verified tenant boundary

The full FastAPI application has no authentication dependency or authorization middleware. Candidate and job listing endpoints accept organization IDs supplied by the caller; candidate listing leaves the organization filter optional. Candidate detail, dossier, graph, provenance, and audit endpoints take candidate IDs without a verified user-to-organization check. Recruiter override requests also accept a caller-supplied organization ID. The generated OpenAPI schema confirms the gap: it defines no security schemes or global security, and its operations have no security declarations.

The current `User` row stores one organization ID and a password hash; the schema has no organization-membership join table. Override requests also accept caller-supplied `user_id` and optional `organization_id`. Dossier and graph routers keep process-global caches keyed only by candidate ID, the override audit trail has a process-global fallback, and pipeline run state is held in process memory. Adding token validation alone would therefore be insufficient: object access must be scoped to the verified membership, actor IDs must come from the token context, and company state must not depend on one worker's memory.

Relevant code: services/backend/src/cci/main.py, services/backend/src/cci/db/models/organizations.py, services/backend/src/cci/api/routers/candidates.py, services/backend/src/cci/api/routers/jobs.py, services/backend/src/cci/api/routers/dossier.py, services/backend/src/cci/api/routers/overrides.py, and services/backend/src/cci/pipeline/service.py.

**Impact:** a multi-company deployment cannot safely expose applicant, job, dossier, or override data. A random identifier is not an authorization boundary. Add verified identity, organization membership, role permissions, and tenant scoping in server-derived request context before accepting company data.

### Critical: the deployed backend entrypoint does not serve the company workspace API

The Vercel backend entrypoint in services/backend/app.py imports cci.live_app. That app mounts request-scoped live analysis and the synthetic research demo. It does not mount cci.main, which contains the database-backed candidates, jobs, pipelines, dossiers, and overrides APIs. The production site exposes /hr and /workspace pages, but those pages are not backed by the full company API through this Vercel entrypoint.

The live analysis page describes uploaded documents and results as request-scoped and not saved. The synthetic research registry is process-local and its response asks operators to use one backend worker and export JSON for retention.

**Impact:** the running public deployment is a demo/live-analysis surface, not a durable employer workspace. Choose and verify one production topology that serves the intended APIs, persistent storage, background jobs, and tenant controls.

### Critical: no demonstrated hiring validity or fairness evidence

The repository describes all static signal strengths as uncalibrated policy heuristics and says they do not establish proficiency or predict job performance. I found no independent job-related validity study, disparate-impact analysis, or documented acceptance criteria for using these outputs in candidate selection.

**Impact:** do not market the score as validated hiring accuracy or use it as an automated screen or rejection rule. Keep a trained human decision-maker responsible for decisions and obtain independent employment-validity, fairness, and legal review for the intended use.

The European Commission lists AI used for employment and recruitment, including CV sorting, among high-risk use cases. Its current AI Act page says the rules for Annex III high-risk use cases apply from 2 December 2027 following the AI Omnibus. Product classification depends on the intended use; have counsel assess the actual product and customer workflow. Source: https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai

### High: candidate-data lifecycle is incomplete

The live request path intentionally avoids server-side retention, which is useful for a demo. The separate full backend persists candidate and dossier records, but the reviewed API has no candidate deletion flow or retention/purge job. I found no customer-facing access, correction, export, retention, or deletion policy for a shared company workspace.

**Impact:** before storing real applicant data, define the controller/processor roles, purpose and legal basis, retention periods, deletion propagation to evidence and exports, access/correction handling, data location, subprocessors, and incident notification process. Implement and verify those controls.

### High: demo fixtures contain plausible personal identities and live service URLs

scripts/seed_db.py, the five examples/sample_*_cv.txt files, and the legacy dossier UI contain named candidate profiles, university or company email addresses, and github.com accounts. The test suite also includes an identity named AYUSH ROY. These values could be mistaken for real candidates or resolve to real accounts.

**Impact:** replace all demo identities with clearly synthetic labels and reserved .invalid email and URL domains. Keep an obvious synthetic-data notice with the sample documents and UI.

### High: production hardening and operating evidence are incomplete

The public production page returned HTTP 200 for /, /analyze, /hr, and /workspace when checked. Those responses included Access-Control-Allow-Origin: * and did not include Content-Security-Policy or X-Frame-Options. The web config does not set these headers. The local development Compose file has a fixed default Postgres password and publishes database, Redis, backend, and web ports to the host. Backend Settings also defaults DEBUG to true and defines a development secret.

The Compose file labels itself a development/integration stack; these are release risks if those defaults or that stack are reused in production. I found no repository evidence of a production secret-management policy, backup/restore drill, customer SLO, incident runbook, or monitoring/alerting ownership.

**Impact:** establish a production-only configuration with strong secret management, least-privilege network exposure, explicit allowed origins, suitable browser security headers, and tested operational recovery before launch.

### High: public analysis compute has no per-user throttling or tenant quotas

The public live and demo routes cap individual payload sizes and request timeouts, but I found no application-level per-user or per-IP rate limiter, tenant usage quota, or request-concurrency policy in the backend or Next API handlers. The GitHub client handles upstream provider rate limits only.

**Impact:** unauthenticated callers can repeatedly consume analysis and network capacity. Add edge/API throttling, concurrency limits, per-tenant quotas, cost monitoring, and burst tests before exposing the endpoints to company traffic.

### High: Python dependencies are not locked or included in the vulnerability audit

The frontend has a pnpm lockfile and its production dependency audit found no known advisories. The Python runtime dependencies in services/backend/pyproject.toml use minimum-version ranges and the repository has no Python lockfile or Python advisory scan in the verified release workflow.

**Impact:** generate a reproducible Python dependency lock, scan the runtime and container dependencies, and add the scan to CI.

## Recommended launch order

1. Select an identity provider and implement verified authentication, organization membership, and role-based authorization across every company API.
2. Decide the production topology and connect the intended UI to the durable, tenant-scoped API.
3. Define and implement candidate-data lifecycle, retention, deletion, correction, and customer privacy documentation.
4. Keep scoring advisory until independent validity and fairness work supports the stated use; review employment-law obligations with counsel.
5. Remove plausible personal identities from all demo fixtures and legacy UI samples.
6. Complete production security, Python supply-chain, backup/restore, monitoring, and incident-response controls.
7. Run an end-to-end security and tenant-isolation review against the deployed environment.

## Release recommendation

Treat the current public site as a supervised demonstration using synthetic data. Do not onboard companies with real applicant data or sell the current deployment as a secure multi-tenant SaaS product. The code quality checks are useful, but they do not establish tenant isolation, employment validity, legal compliance, or production operations.
