# CandidateX SaaS commercial readiness audit

**Review date:** 2026-09-24
**Reviewed branch:** codex/candidatex-saas-readiness
**Reviewed code snapshot:** 048990f47269750ff9daef7c11a4bc262faafc3a, containing backend-hardening tip 7773d6f30e6ee1a0485d873e238e9d96958f3e77 and Evidence OS tip 2dce46cde56211bd688659fa9505f66209b4561c; based on origin/main baa559f
**Verdict:** Not ready for a commercial multi-tenant launch or customer applicant data.

## Scope

This review covers the combined backend-hardening and Evidence OS process branches, their API wiring and persistence paths, deployment configuration, demo data, and automated checks. I also inspected the current origin/main head and the changes that postdate the reviewed branch. The deployed production source commit was not confirmed, so this review does not certify the running deployment.

## Branch currency

The published Evidence OS tip 2dce46c and backend-hardening tip 7773d6f are represented in the reviewed candidate branch at 048990f. The frontend branch adds a mobile navigation fix. The backend adds explicit claim scope and polarity parsing plus a versioned scan inventory that counts eligible, inspected, and skipped files by category for archive and bounded Git blob acquisition.

The candidate branch is based on common ancestor baa559f, while origin/main advanced to 50556ac during this review. Current main includes PR #22, the production UI branch, and commit 2a98033, which hardens local development defaults (DEBUG=false, no built-in secret, required Compose database password, and loopback-only port bindings). Those main changes are not included in the reviewed candidate branch. An exploratory sync encountered conflicts across the README, application layout and home page, Evidence OS components, tests, and lockfile; it was aborted before any merge was committed. Select and reconcile the release branch, then rerun verification on that exact tree.

The latest main defaults improve local configuration but do not add authentication, tenant authorization, candidate lifecycle controls, or production operations. The current shared checkout is also a separate line at aebee8e with user changes; do not treat it as the same source tree as origin/main or this candidate branch.

## Verification completed

- Backend suite on published backend-hardening tip 7773d6f: 490 passed, 1 skipped, 5 warnings. The skipped test is tests/unit/test_signal_rule_catalog.py:153; it requires the absent contradiction evaluator.
- Frontend TypeScript check: passed.
- Next.js production build: passed.
- Playwright browser suite on the combined candidate branch: 23 of 23 passed in 1.8 minutes. The local Playwright configuration starts cci.main and Next.js; it does not exercise the Vercel services/backend/app.py entrypoint or certify the deployed company API.
- Production JavaScript dependency audit: no known vulnerabilities reported.
- Python pip check: no broken requirements found. This is not a Python vulnerability audit and does not replace a lockfile.
- Node emitted a warning that the configured Kaspersky root certificate could not be loaded. Python reported upstream HTTP test-client and Alembic path deprecation warnings.

### Separate shared-checkout and current-main state

The shared checkout at aebee8e has its own history and uncommitted changes. Its prior local verification passed 246 backend tests, the web typecheck/build, and 22 Playwright cases; those results do not apply to the reviewed candidate branch or certify origin/main at 50556ac. The local aebee8e privacy commit sanitizes sample CV and seeder identities, but that change is absent from both the reviewed candidate branch and current origin/main. Current main still contains named candidate examples, university email addresses, and live GitHub URLs.

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

### High: negative-evidence qualification is not enforced end to end

The latest backend adds NegativeEvidenceDetails, registered contradiction rule IDs, deterministic claim-expectation parsing, and a versioned repository scan inventory. The inventory now counts eligible, inspected, and skipped files by category and records skip reasons. However, RepositoryScanCompleteness remains local to acquisition: acquire_repository uses it only to reject a missing or truncated inventory, and the successful repository receipt does not serialize the category completeness values. No live evaluator consumes those values or compares them with NegativeEvidenceDetails.required_scan_completeness.

The cci/contradictions/candidates.py evaluator referenced by the rule-catalog test is absent, so its test remains skipped. The expectation parser is imported by cci.live.claims but has no live-service call site. EvidenceRecord labels any negative record with details as qualified without enforcing observed_scan_completeness >= required_scan_completeness or recomputing the claim reference from the claim and scope. The scan-scope model is frozen but contains a mutable artifact_paths list.

Evidence-family scoring, contradiction diagnostics, claim corroboration, graph construction, and uncertainty calculations still branch on is_positive_support and can therefore consume legacy unqualified negatives. The database Evidence row and repository mapping do not persist the typed negative-evidence details or qualification. The new scan inventory is a useful measurement substrate, but it is not yet an end-to-end qualification control.

**Impact:** contradiction and negative-support outputs are not ready to influence company hiring decisions. Implement claim-scoped candidate generation, enforce completeness and immutable scope, persist and return qualification details, and make every scoring, graph, and claim consumer ignore unqualified legacy negatives. Add end-to-end tests for incomplete, missing, malformed, and cross-claim evidence before relying on these results.

### High: demo fixtures contain plausible personal identities and live service URLs

The reviewed candidate branch and current origin/main still contain named candidate profiles, university email addresses, and live GitHub accounts in scripts/seed_db.py, examples/sample_*_cv.txt, and the legacy dossier UI. Current origin/main still includes an Ayush Roy sample and a university email. The separate local aebee8e commit replaces the known sample CV and seeder identities with synthetic labels and reserved .invalid contacts and URLs, but it is not included in either pushed branch.

**Impact:** replace all demo identities with clearly synthetic labels and reserved .invalid email and URL domains across seed data, sample files, mocks, and UI defaults. Keep a visible synthetic-data notice with samples and demo screens.

### High: production hardening and operating evidence are incomplete

The reviewed candidate branch predates current main's commit 2a98033, which improves the local Compose and settings defaults: DEBUG is false, the built-in secret is removed, Compose requires an ignored .env password, and service ports bind to loopback. Those fixes are not in the reviewed candidate snapshot. Even on current main, local-development defaults do not prove production configuration or deployment safety.

An earlier public-page check found Access-Control-Allow-Origin: * and no Content-Security-Policy or X-Frame-Options. Because the deployed source commit is unconfirmed and main moved during this audit, recheck the live headers against the selected release deployment. I found no repository evidence of a production secret-management policy, backup/restore drill, customer SLO, incident runbook, or monitoring/alerting ownership.

**Impact:** choose and verify the production source and topology, establish explicit browser security headers and allowed origins at the deployed edge, and document tested recovery and operating ownership before launch.

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
