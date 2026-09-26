# CandidateX strong audit — 2026-09-27

**Release decision for the audited local tree: not ready for a general multi-tenant SaaS release.** The local live workflow passes its functional checks, but fresh installation fails and public analysis lacks an enforceable backend abuse boundary. The full API additionally permits unauthenticated cross-tenant access and has deployment and state-consistency defects.

This audit covers commit `28a085290a1a60dfe2b945844bd7616927867ccf` **plus the pre-existing working-tree changes**. It does not certify that commit alone, a clean checkout, or a deployed service. No application code was changed. Existing modified and untracked application files were fingerprinted before verification and remained byte-for-byte unchanged.

**Repository divergence:** fresh remote verification found GitHub `main` at `6cdddd4702fc4c5b54f4129f153b77e8de4a848b`, with 20 commits unique to local HEAD and 122 unique to remote main. The latest remote application code was not the audit target and was not re-audited. These findings must be rechecked before applying fixes there. The report is published on a separate branch based on that remote revision, without merging, resetting, or publishing the local application changes.

The reviewed surfaces include both FastAPI entrypoints, routers and persistence, live document and public-source ingestion, SSRF and archive controls, attribution and scoring uncertainty, exports, the Next.js bridge and UI, Docker/Compose, dependency configuration, CI, and automated tests. P1 means resolve before releasing the affected surface; P2 means a confirmed correctness or reliability defect. Deployment-dependent exposure is called out explicitly.

## Confirmed findings

| ID | Priority | Finding | Affected surface |
| --- | --- | --- | --- |
| A1 | P1 | No authenticated tenant or actor boundary | Full `cci.main` API |
| A2 | P1 | Analysis bypasses the frontend rate limiter | Dedicated live API and Next.js bridge |
| A3 | P1 | Frozen dependency installation fails | Clean install, CI, frontend image |
| A4 | P1 | PostgreSQL configuration cannot start the packaged backend | Compose backend |
| A5 | P1 | Two workers cannot share pipeline, graph, and audit state | Full API Docker runtime |
| A6 | P2 | Exports overstate evidence strength and invent contradiction labels | Legacy HTML/Markdown exports |
| A7 | P2 | Database failures masquerade as successful empty results | Full API directory and retrieval routes |
| A8 | P2 | A malformed public URL fails the whole analysis | Dedicated live API |

### A1 — Bind every full-API operation to an authenticated tenant and actor

**Evidence:** `services/backend/src/cci/main.py:42` mounts the full routers without an authentication dependency. `api/routers/candidates.py:41` accepts an optional caller-supplied organization; `db/repository.py:517` only filters when that argument is supplied. Candidate detail at `api/routers/candidates.py:88` uses an ID without tenant authorization. `api/routers/overrides.py:50` accepts the purported actor and tenant from the request body.

**Reproduction:** an isolated temporary database containing two synthetic organizations returned both organizations' candidates to an unauthenticated `GET /api/v1/candidates`. Unauthenticated detail access returned the second organization's synthetic email and manifest. Supplying that organization's ID selected its candidates. An unauthenticated pipeline run and recruiter override both returned HTTP 200; the override accepted a caller-invented user ID.

**Impact:** anyone who can reach this API can read candidate data across organizations and alter results while supplying the audit actor. CORS does not provide an authorization boundary. This is a release blocker if the full API is reachable by untrusted users.

**Scope:** the dedicated Vercel entrypoint imports `cci.live_app`; its candidate directory returned 404 in the probe. Compose binds its host port to loopback, so this audit does **not** claim that candidate data is currently exposed on the internet. The Docker image nevertheless starts `cci.main` (`services/backend/Dockerfile:61`), so changing deployment topology can expose the broader surface.

**Fix and acceptance:** derive tenant and actor from authenticated server-side context, require tenant scope in repository lookups and writes, and deny cross-tenant IDs consistently. Add negative tests for list/detail/export/graph/override/run access and forged actor IDs. Keep the full API private until these checks pass.

### A2 — Enforce quotas at the expensive backend operation

**Evidence:** `apps/web/app/api/live/[operation]/route.ts:12` keeps counters in a process-local map and takes the first `x-forwarded-for` value at line 37. Entries are never deleted. `services/backend/src/cci/api/routers/live.py:53` dispatches analysis without a quota or authenticated bridge dependency; `cci.live_app` exposes it directly. `live/service.py:17` starts acquisition pools for each accepted analysis.

**Reproduction:** 11 consecutive unauthenticated requests to the dedicated live endpoint all returned 200 and invoked the stubbed expensive handler 11 times. An isolated execution of the actual TypeScript bridge showed the same forwarded IP receives 429 on request 11, while rotating the caller-supplied header produces 11 successes. Requests without that header share one `unknown` bucket.

**Impact:** calling the backend directly bypasses the application limiter. Multiple frontend instances have separate counters. Untrusted forwarded headers allow quota bypass on deployments that do not overwrite them; absent headers can throttle unrelated callers together. Unlimited retained IP keys also grow process memory. A load or exhaustion attack was not performed.

**Fix and acceptance:** enforce a shared quota and bounded concurrency at the backend or an unavoidable trusted gateway, restrict direct backend access when appropriate, and resolve client identity only from trusted proxy configuration. Expire limiter keys. Verify limits across two instances and through direct-backend requests. A provider firewall may reduce exposure, but no such deployed configuration was available to verify.

### A3 — Restore a reproducible frozen install with the pinned package manager

**Evidence:** `package.json` pins pnpm `11.15.1`; `.github/workflows/ci.yml:64` and `apps/web/Dockerfile` require `pnpm install --frozen-lockfile`. The checked-in lockfile has an override entry while the pinned manager reports a configuration mismatch. The working-tree web manifest also removed `clsx`, `framer-motion`, `tailwind-merge`, and `@types/react-dom`, while `pnpm-lock.yaml` still lists them in its importer.

**Reproduction:** using the exact pinned version, `npm exec --yes --package=pnpm@11.15.1 -- pnpm install --frozen-lockfile --lockfile-only --ignore-scripts` failed with `ERR_PNPM_LOCKFILE_CONFIG_MISMATCH`: the overrides configuration does not match the lockfile. The installed pnpm `9.15.9` independently failed with `ERR_PNPM_OUTDATED_LOCKFILE` and printed the stale importer differences. Both checks left tracked dependency files unchanged.

**Impact:** a passing build using existing `node_modules` does not establish that CI or a fresh frontend image can install the reviewed tree.

**Fix and acceptance:** normalize the override configuration for the pinned pnpm release and regenerate the lockfile with that version. Commit the intentional manifest/config/lock changes together. Verify an empty-dependency-directory frozen install, typecheck, build, and browser suite using the pinned manager.

### A4 — Package the driver required by the Compose database URL

**Evidence:** `docker-compose.yml:58` sets a `postgresql://...` URL. `services/backend/pyproject.toml:11` declares SQLAlchemy but no PostgreSQL driver. The Docker builder installs that project at `services/backend/Dockerfile:27`; `db/session.py:20` creates the engine during import.

**Reproduction:** importing `cci.main` in the project virtual environment with a synthetic PostgreSQL URL fails immediately with `ModuleNotFoundError: No module named 'psycopg2'`, before any database connection is attempted. None of `psycopg`, `psycopg2`, or `psycopg2-binary` is installed.

**Impact:** the configured backend cannot reach startup or satisfy Compose's frontend health dependency. SQLite tests do not exercise this packaging path.

**Fix and acceptance:** declare and package the chosen driver and use its matching SQLAlchemy URL. Start the real image against a fresh PostgreSQL instance, apply migrations, and verify readiness and a database round trip. Docker was unavailable here, so this is a reproduced Python import failure plus image/config inspection, not a completed container test.

### A5 — Share state before running the full API with multiple workers

**Evidence:** `services/backend/Dockerfile:61` starts two workers. `pipeline/service.py:20` keeps run state in instance dictionaries; `api/routers/dossier.py:17` keeps dossiers and graphs in process-local dictionaries. Graph retrieval at line 129 has no database reconstruction fallback. The override audit fallback is also process-local.

**Reproduction:** a pipeline created by one `PipelineService` instance is absent from another. Isolating the graph registry as it would be in a different worker changes graph retrieval to 404. This was a deterministic state-isolation probe, not a measured multi-process load test.

**Impact:** requests routed to different workers can disagree about run status, graph availability, or the current snapshot; restarts discard session state. The normal pipeline path does not persist its runs. Database fallback on some dossier routes does not solve graph or run-state consistency, and cached dossiers can become stale after another worker updates them.

**Fix and acceptance:** persist tenant-scoped run, dossier, graph inputs, and audit state in shared storage and define cache invalidation. Test run/status/graph/override flows across two workers and a restart. A single worker can be a temporary development constraint; it does not provide durable SaaS history. This finding does not treat the intentionally request-scoped live workflow as a persistence bug.

### A6 — Preserve uncertainty and conflict semantics in exported briefs

**Evidence:** `services/backend/src/cci/reports/exporter.py:44` and line 778 choose `ROBUST` solely from `is_insufficient_evidence`, ignoring `analysis_confidence`. Lines 95 and 240 label a nonpositive diagnostic as a contradiction without requiring positive and negative support or `has_meaningful_conflict`.

**Reproduction:** an actual pipeline dossier with full coverage from one synthetic cluster returned `evidence_strength=limited`, with `single_cluster` and `interval_unavailable` flags. Its Markdown export called the evidence `ROBUST`. A separate zero-evidence dossier had zero meaningful conflicts, yet its HTML export rendered `+0.00 Contradiction`.

**Impact:** the shareable report strengthens unsupported conclusions and can turn absence of evidence into a negative interpretation. This affects legacy HTML/Markdown exports; the tested live JSON download preserves the dossier's uncertainty fields.

**Fix and acceptance:** render the dossier's evidence-strength summary and flags in every export; use the actual meaningful-conflict predicate and explicit unknown/no-support states. Cover single-cluster, no-evidence, negative-only, and genuine mixed-support cases in exporter tests.

### A7 — Return database failures as failures

**Evidence:** `services/backend/src/cci/api/routers/candidates.py:78` and `jobs.py:81` catch all exceptions and return `[]`. Dossier retrieval catches database failures and can return 404 (`dossier.py:58`). Candidate detail also sends `str(e)` to callers at `candidates.py:113`. The full API's health endpoint only reports process liveness.

**Reproduction:** forcing candidate listing to raise a synthetic database outage still returned HTTP 200 with an empty array.

**Impact:** outages or schema failures resemble an empty workspace or a missing candidate, preventing callers and monitoring from distinguishing data absence from failure. Raw database exception strings can disclose implementation details.

**Fix and acceptance:** log safe diagnostics with request IDs; return explicit 503/500 errors without SQL or connection detail; reserve empty lists and 404 for successful queries. Add database readiness appropriate to the full API. Verify outage responses separately from empty-database responses.

### A8 — Contain malformed public URLs to validation or a source receipt

**Evidence:** `services/backend/src/cci/live/contracts.py:59` bounds external URL strings but does not validate their URL syntax. `live/public_links.py:82` calls `classify_url` before entering its exception handler; `intake/canonicalizer.py:126` parses the URL and can raise. The future propagates through `live/service.py:21` to the whole request.

**Reproduction:** an otherwise valid analysis request with `external_urls: ["http://["]` returned HTTP 500, `The analysis failed. No sample result was substituted.` GitHub acquisition was stubbed and no external request was made.

**Impact:** one malformed source can prevent a dossier and discard other acquired results. The browser's URL check reduces ordinary UI exposure, but the backend accepts direct clients and must enforce its own contract.

**Fix and acceptance:** validate URL syntax at the boundary and keep classification inside per-source exception handling, including omitted-source receipt construction. Return 422 or an explicit failed/blocked receipt; verify a malformed source cannot destroy a mixed-source result.

## Fresh verification

| Check | Result and limits |
| --- | --- |
| Backend suite | **246 passed**, exit 0; includes scoring, uncertainty, intake, exports, API, database, SSRF, archive traversal, and repository safety tests. Fresh collection confirms 246 tests. |
| Frontend route generation and TypeScript | Passed `next typegen` and `tsc --noEmit --incremental false`. The `lint` script is another TypeScript check, not a separate lint engine. |
| Production build | Passed with installed dependencies, Next.js 16.3.5 / Node 24.19.0. This does not overcome A3. |
| Browser acceptance suite | **22 passed** in 51.5 seconds against the production build and local full backend. Covers upload, extraction, UNKNOWN, failed reruns, source review, export, graph interaction, and mobile/tablet layouts. Most populated dossier scenarios use fixtures. |
| Real-source dedicated backend smoke | Synthetic PDF intake and analysis returned 200. Public `psf/requests` commit `611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60`: 75 files inspected, 51 evidence records, 11.26 seconds total. No declared identity: RCI remained null and evidence strength insufficient. `Cache-Control: no-store` and request ID were present. |
| Frozen install | Failed with both installed pnpm 9.15.9 and pinned pnpm 11.15.1; see A3. |
| PostgreSQL import | Failed before connection because the driver is missing; see A4. |
| Isolated adversarial probes | Reproduced A1, A2, A5, A6, A7, A8 with synthetic data and temporary state. No production data or load attack used. |
| Python dependency integrity | `pip check` passed. |
| Python advisory scan | `pip-audit` found no known vulnerabilities in 41 installed third-party packages. Local `cci` was skipped as a non-PyPI package. These are the installed versions, not a fresh resolution of the open dependency ranges. |
| JavaScript advisory scan | `pnpm audit --prod --json` reported zero advisories across 68 dependencies in the audited dependency metadata. The stale lockfile limits its relationship to a clean installation. |
| Python static security scan | Bandit scanned 12,340 lines and produced 16 alerts: 15 low and one high. The high alert is SHA-1 calculation for matching a Git blob object ID (`live/acquisition.py:254`), not a new password/signature weakness; evidence also uses SHA-256 fingerprints. Broad exception handling was reviewed rather than treating every alert as a vulnerability. |
| Selected credential checks | No tracked credential-file candidates or matches for the selected GitHub token, AWS access-key, and private-key patterns. This was not a full historical secret scan. |
| Diff and preservation | `git diff --check` passed. Original application-file hashes, including `next-env.d.ts`, were unchanged. |

The shell initially supplied `DEBUG=release`, which Pydantic correctly rejected as a boolean. Tests and local backend processes were rerun with process-local `DEBUG=false`; no environment file was changed. Tests use isolated temporary databases. Audit scanners were installed in an ignored tools environment rather than changing application dependencies.

## Controls that held up

- The dedicated live entrypoint excludes candidate directory and stored dossier routes.
- Supplied public-page connections pin a validated public IP while preserving TLS SNI; redirects are revalidated, credentials and nonstandard ports are blocked, and proxy environment settings are ignored.
- GitHub acquisition restricts destinations, pins revisions, caps archives/files and scan budgets, rejects traversal, and omits symlinks. The reviewed acquisition path treats candidate files as data; it does not run candidate programs, tests, installers, or hooks.
- Document intake applies upload, page, expanded-DOCX, and extracted-text bounds. These are useful bounds; native parser CPU/memory isolation was not stress-tested.
- Live attribution, source-health failures, missing intervals, and UNKNOWN behavior are covered by tests. The real-source smoke preserved zero attribution and null capability scores.
- The browser suite confirmed responsive layouts, explicit failure handling, retained prior-run identification, and usable evidence inspection in its covered scenarios.

## Verification limits and remaining release work

No deployed URLs or provider configuration were supplied. Production authentication, gateway quotas, TLS/headers, CORS, deployment revision, real-provider acquisition through the deployed frontend, observability, and rollback remain unverified. A request for deployment URLs was left open while local work continued. An attempt to start an additional local frontend server was rejected by automatic approval review with only `blocked by policy`; the real-source smoke therefore used the dedicated backend. The completed browser suite still exercised the existing frontend bridge with local backend requests, but it is not a deployed real-source smoke test.

Docker was unavailable. Actual image builds, PostgreSQL migrations/readiness, and cross-process failover were not executed. This audit did not establish sustained capacity, cancellation under disconnects, parser isolation under hostile resource loads, or historical secret absence. Dependency advisories are a point-in-time check, not proof of security. Python dependency ranges are unpinned, and CI does not currently reproduce these advisory/static scans. Only Python 3.12.10 was executed locally; the other CI Python version was not rerun here.

The public live product explicitly provides request-scoped results and manual JSON export. That design is coherent for a limited analysis tool. Authenticated workspaces, durable tenant history, retention/deletion administration, and trusted actor audit trails remain additional requirements if the intended product is a general company SaaS. This report makes no legal-compliance or validated hiring-accuracy claim.

Resolve A1 before exposing the full API, and A2/A3 before an unrestricted live release. Repair and exercise the container path for A4/A5 if it is a supported deployment. Resolve A6–A8, then run a clean installation and the appropriate deployment-specific release gates. Passing the existing suites alone does not cover these reproduced gaps.

## Local evidence and reproduction

Ignored artifacts are under `reports/audit-2026-09-27/`: `backend-tests.log`, `backend-collection.log`, `browser-tests.log`, `frozen-install.log`, `pip-audit.json`, `pnpm-audit.json`, `bandit.json`, `runtime-probes.log`, `limiter-probe.json`, `export-probe.json`, `live-smoke-summary.json`, and `live-smoke-result.json`. The latter contains only the synthetic audit intake and public-source observations. Artifacts are local, not bundled into the report commit.

The disposable `runtime_probes.py`, `limiter_probe.cjs`, and `export_probe.py` files in that directory reproduce the security and correctness findings without a deployed service. The first uses a temporary SQLite database and stubs expensive acquisition where appropriate. Run them from the repository root with the project virtual-environment Python or Node respectively. `live_smoke.py` needs the dedicated backend on loopback port 18147 and intentionally fetches one public repository. The audit-only backend was stopped after verification.
