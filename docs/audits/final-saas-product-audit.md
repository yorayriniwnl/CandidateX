# CandidateX Frontend and SaaS Product Audit

**Audit date:** 2026-09-23
**Repository revision reviewed:** 66477ed (main)
**Scope:** Frontend product surface, backend/API contracts needed by the frontend, persisted schema, test coverage, and deployment entrypoints. No product code was changed during this audit.

## Executive findings

CandidateX already has a credible evidence-first live review flow. It accepts a resume, lets the reviewer inspect extracted links, performs bounded public-source acquisition, keeps unknown capability values null, exposes source receipts and provenance, summarizes evidence strength, and exports the request result as JSON. The current copy consistently says this supports a human technical interview rather than making the hiring decision.

The repository does not yet contain the unified SaaS application described in the master build brief. The web app has two routes: a marketing/command-center page at / and a request-scoped analysis page at /analyze. There is no dashboard, candidate workspace, persisted run page, report route, settings area, billing view, or authenticated shell.

The largest architecture gap is data lifecycle. SQLAlchemy contains a substantial multi-tenant schema, but the public Vercel entrypoint deliberately serves only the stateless live-analysis app. The live workflow returns storage=request_only and the browser clears its state on refresh. The separate pipeline service keeps runs in a process-local dictionary and executes synchronously; the analysis-run tables are not wired into that service. There is no user-facing persistent run, progress polling, or workspace API in the deployed entrypoint.

This means the next frontend design must treat the live workflow as the proven product foundation and treat the broader SaaS screens as dependent on backend lifecycle, authentication, tenant-access, and retention decisions. A dashboard built before those contracts exist would have to invent data or show empty placeholders.

## Existing product surfaces

| Surface | What exists | Readiness |
| --- | --- | --- |
| / | Responsive marketing command center with the CandidateX evidence loop and one live workflow CTA. | Usable public entry page; visual direction is more expressive than the requested restrained enterprise app. |
| /analyze | Resume intake, optional role and job-description context, source review, live analysis, evidence summary, detailed claims-adjacent review, source receipts, capability table, evidence details, interview questions, and JSON download. | Strong request-scoped foundation; not a persistent workspace or multi-step route flow. |
| /api/live/intake and /api/live/analyze | Next.js server proxy for only the two live operations. Applies body limits, no-store responses, and safe upstream errors. | Appropriate for the current stateless flow. No session or workspace client exists. |
| Other frontend routes | None. Existing browser tests explicitly expect retired /workspace, /hr, and /research-demo pages to return 404. | Not built. |

The analysis UI keeps the response in React state, so a refresh discards the resume and result. The current export action serializes the full live response into a browser download. It does not create a server-side report or durable export record.

## Backend and deployment contract audit

There are two different backend entrypoints:

- services/backend/app.py imports cci.live_app:app. That Vercel surface mounts only /api/v1/live/intake, /api/v1/live/analyze, and /health. Its stated storage mode is request_only.
- cci.main:app mounts the live router plus candidate, job, pipeline, dossier, override, research, and research-demo routers. The Playwright configuration starts this broader app locally.

The distinction matters: local API availability is not proof that a route is present in the public Vercel deployment.

| Area | Present in repository | Current product limitation |
| --- | --- | --- |
| Candidate, source, project, claim, evidence, dossier, organization, user, run, and stage models | 41 mapped SQLAlchemy entities across services/backend/src/cci/db/models. | Live intake and analysis do not persist into these tables. |
| Candidate and job APIs | Read/list routes and job-description parsing exist in cci.main. | Not mounted by the public live_app deployment; no frontend client; no authentication dependency is visible on these routes. |
| Pipeline status | A pipeline route returns stages and a run identifier. | PipelineService stores state in a process-local dictionary; start_pipeline executes synchronously before returning. It is not a durable background job or refresh-safe progress stream. |
| Dossier retrieval and exports | Local full API has dossier, graph, probes, provenance, and HTML/Markdown/JSON export routes. | Not mounted by live_app; live analysis instead returns the whole report in the POST response and the browser downloads JSON. |
| Authentication and organization membership | Organization and User database models exist. | No login/session/token, member management, role-checking, or tenant-scoped web flow was found. A database model is not an access-control implementation. |
| Billing, retention controls, integrations | No user-facing routes or complete billing model/API were found. | Do not show controls or plan status until supported by a real backend contract. |
| Candidate deletion and audit | Deletion and audit entities exist; local API includes audit-related operations. | No authenticated retention/deletion UI and no live request-result persistence lifecycle. |
| Research surfaces | Research endpoints and a research-demo router are mounted in cci.main. | The frontend research demo route is retired; public live_app does not expose those routers. Keep synthetic material outside live candidate views. |

The live-analysis implementation is deliberately bounded: PDF/DOCX upload up to 3 MB, finite analysis body size, bounded repository selection and file inspection, bounded public-page acquisition, and no execution of candidate code. It returns explicit limitations. GitHub account association and credential/experience validation remain claims or heuristics rather than identity or issuer authentication.

## Frontend contract quality

The current UI consumes useful, high-value fields: role and JD-derived requirements, nullable capability estimates, capability coverage, evidence counts, independent clusters, uncertainty intervals, conflict flags, source-health counts, repository inspection summaries, claim/skill matches, credential page text matches, and interview questions.

Several frontend types are looser or duplicated relative to the backend:

- types/cci.ts defines a CandidateManifest shape using full_name, primary_email, github_usernames, and github_repositories. The current backend manifest uses display_name, email, github_urls, project_links, and other URL lists. The active live workflow avoids this type by defining a second inline manifest shape in lib/live-analysis.ts.
- ResumeIntake and SourceReceipt are local TypeScript interfaces. Several backend fields are omitted, and receipt/report statuses are plain strings rather than a single shared enum.
- The live receipt vocabulary includes states such as observed, partial, not_selected, not_scanned, access_restricted, unsupported_content, and acquisition errors. The persisted SourceState enum uses a different set. UI status labels must be mapped from the actual endpoint, not inferred from the persisted enum.
- Dossier.claims_corroboration is exposed as a flexible list of dictionaries by the Python contract, while the TypeScript side assumes a fixed ClaimCorroboration shape. This should be validated with response fixtures before it powers a claims matrix.
- The backend has both RequirementStatus values and role-fit match states. Current role-fit matches use observed, related, unknown, and unresolved. The report should use the live role-fit contract rather than assuming the other enum applies.
- Research, persistence, and manual interview-feedback interfaces remain in the frontend type file even though the live screens do not consume those routes.

The full API response does not expose one global “artifacts inspected” number. Per-repository receipts can expose files_inspected, files_omitted, and evidence_count; these are distinct units and must not be renamed into one artifact metric without a documented calculation. Similarly, a client-side elapsed timer would not be a backend analysis-duration field.

## Product and information-architecture gaps

The current result page is a useful technical review but not the flagship report in the prompt:

- The top summary has three metrics, not the requested compact 8–10 KPI strip.
- Role requirements are shown as a secondary disclosure/list, not the primary Expected vs Observed table.
- Claims do not have a dedicated claim-verification matrix. Skills, project links, education, experience, achievements, and credential page matches are present with different levels of support.
- Projects, repositories, sources, and evidence do not have dedicated workspace routes or inspectors. Some details are inline or expandable.
- There is no sticky report navigation, filterable candidate table, report history/diff, or URL-addressable report state.
- Progress is a generic busy message for the live request. The user cannot return to a live run or see server-reported counts while it runs.
- There is no workspace dashboard with real counts. The repository has schemas for several needed entities, but those schemas are not connected to the deployed live route.
- The current intake is a compact single-page form with optional role/JD and links; it does not implement the brief’s reviewed role-requirement and source-selection steps.

Some requested entities are not first-class persisted models in this codebase. Academic and credential entries, for example, are derived from request-scoped resume/public-page analysis rather than stored as dedicated database entities. Live credential matches are explicitly only public text matches; experience and education are labeled self-reported.

## Visual, responsive, and accessibility audit

The current application is dark-first and readable, with visible focus styles, labeled upload and text fields, semantic headings, named tables, expandable audit detail, reduced-motion handling for smooth scrolling, and a mobile navigation toggle. Existing browser checks cover the 390 px mobile width and an 880 px tablet width for the current routes.

The visual system differs from the requested calm, dense product shell. I reviewed the desktop full-page result and the mobile upload/review screenshot generated by the current Playwright suite:

- The global layout draws animated background orbs on every route. The landing and intake styles use large violet/cyan gradients, glows, grid textures, rounded panels, and decorative diagrams.
- Global CSS retains a large glass/glow utility system and old surface styles although the old product pages were retired.
- Several table headers, metadata labels, and status hints are 10–12 px; the prompt targets at least 12 px metadata and 13–14 px table text.
- The current report uses nested panels and cards; the requested information density and table-first hierarchy are not yet present.
- At the suite's default 1280 px desktop width, the report summary sits below the live workflow and extracted-resume panels. The result has no separate compact report landing view, so the target report KPIs and Expected vs Observed table are not available in the first viewport.
- There is no sidebar, organization switcher, user/account control, or contextual evidence drawer.
- No automated accessibility suite, keyboard-only report review, screen-reader review, contrast audit, or real visual screenshot review is wired as a maintained acceptance gate.

The existing responsiveness is useful groundwork. The mobile screenshot covers upload/review rather than a completed report; the report has not been visually reviewed on mobile. Existing checks use 390 px and 880 px, not the full requested width set. The current run produced apps/web/test-results/live-analysis-desktop.png, live-analysis-ui-result.png, and live-analysis-mobile.png. These results are not evidence for dashboard, report drawer, settings, or billing layouts because those screens do not exist.

## Language, demo, and human-decision boundaries

The live UI is generally careful: it says unknown stays unknown, public matches do not establish mastery, and the system does not make hiring decisions. The current backend also states that GitHub attribution is repository-level and does not prove authorship of each inspected line.

Two items need explicit separation in future screens:

- The frontend contains a HiringRecommendation type with strong_hire / lean_hire / lean_no_hire / no_hire. It corresponds to human-entered interview feedback in the full API, not an automated dossier output. Keep it in a clearly human-authored feedback area only.
- The capability table uses readiness-named CSS classes internally. The visible label is “Observed score,” but the old terminology should be removed when that table is redesigned.

Test fixtures use clearly synthetic labels such as “Example Candidate.” No personal-looking demo candidate is shown on the live public page. The current UI tests use both a local backend and mocked responses; mocked values are test-only.

## Test and release-gate inventory

- Frontend: three Playwright spec files cover homepage navigation, upload/analyze/export behavior, errors, responsive width, and selected evidence-strength disclosures. The UI-specific spec mocks the live API. There are no component-test or accessibility-test suites.
- Backend: unit, integration, property, security, and golden tests are present. CI runs backend tests and frontend typecheck/build/Playwright checks.
- The web lint command is TypeScript typechecking; no separate ESLint script is configured.
- Baseline frontend typecheck, production build, and Playwright suite were run: all passed; Playwright reported 18 passing cases.
- The backend pytest suite was run and exited successfully. It emitted two dependency deprecation warnings from Starlette/httpx/AnyIO.
- The Playwright desktop full-page result and mobile upload/review screenshots were inspected. No screenshot was taken at 1440 px or for the mobile completed-report state.
- No source implementation changed. The live flow was exercised only through the existing suite's empty-source PDF/DOCX fixtures and mocked partial-evidence responses; a full public-source QA candidate fixture is not present.

## Readiness summary

**Ready to preserve:** request-scoped resume intake; candidate review before public fetching; bounded static evidence acquisition; explicit partial/error states; nullable unknown capability estimates; source receipts; evidence provenance; deterministic evidence-strength summary; interview questions; browser JSON export; human-led product language.

**Present as schema or local API only:** candidates, roles/jobs, run/stage records, dossiers, source and artifact entities, team/user entities, audit events, exports, and research endpoints. These are not the public live product surface and should not be presented as working SaaS capabilities until the deployed API, authorization, lifecycle, and frontend are connected.

**Missing for SaaS readiness:** authentication, verified tenant isolation, durable analysis execution and retrieval, run listing and progress, persisted report/history semantics, report-level evidence navigation, an audited metric lineage sheet, explicit retention/deletion UX tied to real storage, team and billing contracts, and end-to-end verification across these routes.

The safest first implementation slice after this audit is a data-truthful report shell and Expected vs Observed requirements view built only from the existing live response. Dashboard, history, team, and billing screens should follow only when their deployed API and access-control contracts are available.
