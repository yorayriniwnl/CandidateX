# CandidateX // Evidence OS

**Status:** Approved implementation reference
**Date:** 2026-09-23
**Branch audited:** `origin/main` at `baa559f130fcb1bc5706ce55765bd7cb6cffa0ba`

## Objective

Rebuild the CandidateX frontend as a forensic, evidence-first technical dossier. The interface should help a recruiter understand the result quickly, let an engineer trace major numbers to their evidence, and make uncertainty legible. This is a frontend redesign. The backend, acquisition limits, scoring behavior, identity boundaries, and evidence semantics remain authoritative.

The design follows the supplied CandidateX // Evidence OS brief. It replaces the current long stack of similarly weighted panels with a deliberate intake, an honest synchronous run state, and a dossier organized around decision summary, capability evidence, and provenance.

## Source-of-truth audit

- The implementation target is `origin/main` at the SHA above. The user's original checkout is 117 commits behind and has four modified frontend files; it remains untouched in a separate worktree.
- Production at `https://candidatex-smoky.vercel.app` redirects `/` to `/analyze`. The production browser check found no console, page, or HTTP errors; a 390 px viewport has no horizontal overflow.
- The existing local Playwright live-analysis flow uploads a generated PDF fixture, calls the local backend, receives a valid partial/unknown result with no public evidence, and exports it. No resume was submitted to production.
- The latest-main web build succeeds and the existing eight Playwright tests pass after building `.next` first. Desktop and mobile screenshots show that the current live view is a long, dense sequence of small boxed sections.
- Current frontend contracts are in `apps/web/lib/live-analysis.ts` and `apps/web/types/cci.ts`; synchronous acquisition and its limitations are in `services/backend/src/cci/live/service.py` and `services/backend/src/cci/live/contracts.py`.
- Open draft PR #20 adds broader claim-ledger, academic-record, and discovered-link work. These unmerged fields are not part of this design.

## Product and truth model

CandidateX is role-aware candidate capability intelligence. It analyzes declared resume information and supplied public sources to create an inspectable technical dossier. Candidate code is not executed. Evidence existence is not mastery. Repository ownership is heuristic. Public text is not independent verification. Resume identity and linked-account association are declarations. Missing evidence stays unknown.

Every display field must be one of:

1. Directly returned by the live API.
2. A transparent, deterministic presentation transform of returned data, such as counts, labels, sorting, or filtering.
3. A clearly marked synthetic research-demo fixture on `/research-demo` only.

Do not fill missing live fields from demos, browser defaults, static examples, or product copy. `null` estimates render as **UNKNOWN**, never zero. Do not turn unknown into a negative claim about a candidate.

Status colors have fixed meanings: green means observed/supporting evidence; yellow means incomplete or needs investigation; red means an actual conflict or failure; gray means unknown or not observed; the restrained violet/blue accent marks role context only. Labels and icons must carry status meaning without color. Use human-readable sans typography; reserve monospace for IDs, revisions, paths, and timestamps. Use near-black surfaces, thin borders, modest corner radii, and no general-purpose glass cards, fake terminal decoration, unsupported benchmark, or decorative visualizations. The approved evidence graph is a restrained, on-demand 3D view of the returned CEG only; it is not a decorative scene or chart.

## Current-main data contract boundaries

| Surface | Data available in the audited branch | UI boundary |
| --- | --- | --- |
| Resume intake | Parsed manifest, display name, declared skills, URL categories, project claims, document hash, warnings, preview, and resume review sections | Say detected/extracted/declared. Do not say verified. Do not invent counts or identity certainty. |
| Dossier summary | Nullable RCI, overall coverage, insufficient-evidence flag, capability estimates, role requirements, optional role weights, conflicts, probe priorities/questions, ownership assessments, limitations, versions, run ID, and timestamp | Show only returned values. Keep RCI separate from evidence coverage; define RCI as an estimated index, never hiring probability. |
| Capability estimates | Nullable estimate, observed flag, raw/effective evidence counts, optional cluster count, standard error, dispersion, optional CI bounds, and per-capability coverage | Unknown estimates remain unknown. Confidence language must not be reverse-engineered from numeric values unless the backend supplies it. |
| Evidence | Live dossier `evidence_records` use evidence fields and provenance with optional artifact hash/URL/line; fields include source family/locator, revision, capability, support, confidence, and observation metadata | Render only fields that exist for the selected evidence. Do not describe repository-file presence as skill mastery. |
| Sources | Receipt status/detail/URL; optional fetch time, commit, files inspected/omitted, evidence count, ownership; GitHub profile/inventory and repository review; public-page title/excerpt/hash/fetch metadata | Preserve backend receipt states. Distinguish not selected, inaccessible, unsupported, and observed where receipts do. State repository signals apply only to inspected files. |
| Claim corroboration | Current branch has capability-oriented `claims_corroboration` rows; resume declared skills and report-level skill explanations; quantified claims to verify | A limited skill-corroboration view may use returned rows. Do not imply a complete resume claim ledger or structured academic records. Keep experience/education self-reported. |
| Graph | Actual CEG candidate/run IDs, nodes, edges, and properties | Render only returned graph structure in the on-demand 3D view. Provide a searchable text equivalent and retain it when WebGL is unavailable. Do not promise unsupported node categories or raw source details. |
| Run state | One synchronous request; frontend proxy timeout is 55 seconds under a 60-second function ceiling. Backend returns dossier only after bounded source acquisition and scoring finish. | Show request sent, waiting, result received, or error. Do not show fictional acquisition stages, percentages, completion checkmarks, or streaming progress. |
| Persistence | Live resume/result is request-scoped; refresh clears it | Do not imply server persistence. Any added interviewer notes are local to the active browser run and are labeled as not uploaded/saved. |

The backend's `partial` result state can be triggered by non-observed receipts or by no evidence. Show the literal result state and source-level explanations; do not infer a precise cause or missed-source count unless the returned receipts support it.

## Experience architecture

### Routes and product boundaries

- `/` becomes a concise product landing page positioned around **Evidence before interviews**, with primary **Analyze candidate** CTA to `/analyze` and secondary link to the explicitly synthetic `/research-demo`.
- `/analyze` becomes the primary evaluation flow and hosts the completed dossier. The result is built from scratch around current-main live data.
- `/research-demo` stays visually and verbally marked as a controlled synthetic research demonstration. It may use demo-only scenarios and controls; these must not flow into a live dossier.
- Legacy `/workspace` and `/hr` prototypes are not promoted into the live flow or primary navigation. They remain clearly outside the live CandidateX dossier until separately scoped.

### Landing

State what CandidateX does in precise language: it turns resumes and supplied public technical sources into an inspectable, role-aware capability dossier. Explain static analysis, traceable evidence, and explicit unknowns. Do not claim LLM analysis, skill verification, employment verification, or hiring decisions.

### New evaluation flow

Present four numbered stages: Resume; Target role / job description; Public sources; Analyze. Keep one primary task visually dominant at a time and retain a visible step indicator.

1. **Resume:** large accessible PDF/DOCX drop area, accepted type/size feedback, parsed filename/type/size, candidate-declared display name, document fingerprint, warnings, and available extracted skill/project/link counts. Counts are computed from actual parsed output, and their labels say extracted or declared. After parsing, replace the empty drop area with an intake summary and provide replace/remove controls.
2. **Role:** collect the existing role and optional job description. Since live role parsing occurs inside the analysis request, this stage may show entered role and a JD preview/length, but no precomputed requirement weights unless a current endpoint actually returns them. Keep weighting graphics result-bound to `dossier.role_weights`.
3. **Sources:** show the actual resume-extracted source manifest, category, selected action, and current known limitation. Keep user selections explicit. Do not imply a source has been fetched before analysis. Unsupported, unsafe, and unselected URLs must be explained using actual client validation or returned status; preserve the app's current private-link protections and backend closed-world selection rules.
4. **Analyze:** show a concise review of selected sources and role, then begin the synchronous request. Keep the request lifecycle resilient and prevent duplicate submits.

### Run state and errors

The in-flight view reports only real frontend lifecycle facts: request prepared/submitted, waiting for the bounded live response, response received, or request failed/timed out. Show the known time limit as a limit, not as a countdown or estimated completion. A truthful skeleton may reserve the eventual summary and table layout but must not contain fake values.

On first-run failure, retain the intake and source selections, name the operation that failed when known, and offer retry. If a prior completed result exists in memory, keep it visible with a clear banner that the latest attempt failed and the displayed dossier belongs to the earlier run. Never relabel that older result as the failed run. A response with `partial` status is a dossier state, not a generic error page.

### Dossier information hierarchy

The first viewport should answer: who is being assessed, for which role, what was observed, what capability estimate is returned, how much evidence coverage exists, and what remains unknown.

1. **Executive summary:** candidate/role/run identity; large RCI when non-null; separate evidence coverage; observed/total capabilities computed from the returned map; source/repository counts only when derivable from returned receipts; partial/insufficient status; concise RCI and coverage definitions. Never format RCI as percent chance, fit probability, or hire recommendation.
2. **Role need vs. observed evidence:** a semantic, dense capability matrix with capability, returned role emphasis (only when present), estimate/unknown, observation state, raw/effective evidence counts, capability coverage, interval where present, and conflict state. Use a qualitative “role context” view when numeric weights or targets are absent. Do not invent role-need values or subtract estimates from unlike scales.
3. **Capability inspector:** selecting a row focuses an adjacent panel/drawer with the available estimate, coverage, evidence counts, interval/uncertainty values, conflict diagnostics, role weight, and linked evidence. “Why this estimate exists” lists only records linked to that capability and shows provenance fields that exist.
4. **Evidence ledger:** searchable, sortable, filterable table over actual evidence records. Core columns are evidence/observation, capability, source, support direction/strength, ownership when returned, observed date when returned, revision/path when returned, and verification/status labels derived from contract fields. Row expansion or drawer exposes fuller provenance. Keep numeric columns aligned and technical IDs in monospace.
5. **Claims:** expose the existing skill-oriented claim corroboration rows and declared resume skills with explicit boundaries. Distinguish self-reported, observed, corroborated, partial, contradicted, and unknown only where current response fields support those states. Do not create a general claim ledger from PR #20, fabricate academic rows, or imply that a public credential page authenticates an issuer.
6. **Source coverage and receipts:** list every selected/extracted/returned source with backend/client-supported state and receipt detail. Selecting a source opens its receipt with URL, fetch/revision, inspected/omitted counts, evidence count, acquisition method, fingerprint, public excerpt, and ownership only when returned. Keep no-field states explicit rather than blank or guessed.
7. **Repository intelligence:** show technologies, dependencies, languages, file categories, engineering signals, metadata, and limitations returned by `repository_review`. Every section says it describes inspected files/metadata and does not prove candidate mastery or ownership. Clearly scope inspected/omitted counts to the receipt.
8. **Conflicts and unknowns:** surface `has_meaningful_conflict` and actual conflict diagnostics with the evidence IDs/rows behind both support directions. Unknown capability rows explain that no evidence was observed within supplied sources and scan limits, and offer the returned interview probe where present. Unknown is not a red flag or a zero score.
9. **Interview plan:** order existing returned probes/questions and show question text, rationale, verification guidance, follow-ups, and grounding evidence IDs. Optional notes live only in browser memory for the current run; label them local-only and clear them on run change/refresh. Do not call persistence endpoints or claim notes are saved. Keep any existing scorecard only where the live response and current supported flow make it truthful.
10. **Evidence graph:** load the restrained 3D view on demand from `LiveResult.graph`. Render only actual returned CEG nodes and edges, expose returned properties on selection, and link evidence and capability nodes to their dossier inspectors. Keep a searchable, keyboard-accessible node/relationship equivalent available without WebGL and when the 3D view cannot initialize.
11. **Audit and limitations:** expose generated time, analysis run ID, versions, system limitations, and source receipts. Keep deep provenance collapsed by default while making every major metric auditable.

Use a sticky desktop section rail for Overview, Capabilities, Evidence, Claims (only when returned), Sources, Interview, Graph, and Audit. The rail navigates to sections rather than hiding important content behind a tab. A compact sticky summary can show name, role, RCI/null, coverage, observed count, and meaningful conflict count while scrolling. No invented “complete” badges.

### Responsive, accessible, and performance behavior

- On narrow screens prioritize executive summary, capabilities, unknowns, and interview probes. Convert evidence rows to expandable records/drawers; allow horizontal scrolling only for genuinely tabular comparison with an announced scroll affordance.
- Use correct heading structure, semantic tables, explicit labels, visible keyboard focus, keyboard-operable sorting/filtering/row inspection, accessible dialogs and disclosures, and text alternatives for every chart/graph.
- Honor reduced-motion preferences. Motion supports state changes and focus, with short restrained transitions; no perpetual decoration.
- Lazy-load the 3D graph and other optional heavy views. Bound DOM size, memoize derived views, and progressively reveal deep provenance. Limit WebGL rendering to a bounded number of actual nodes and edges; keep the text equivalent available and honor reduced-motion preferences.
- Loading skeletons follow actual summary/table geometry; empty, partial, unsupported, inaccessible, timeout, and unknown states have distinct explanatory copy and keyboard-readable status announcements.

## Implementation scope and sequencing

This is one integrated product experience delivered in reviewable layers:

1. **Foundation and landing:** semantic design tokens, typography/surface rules, navigation/section shell, and `/` landing.
2. **Evaluation and request resilience:** four-stage intake/source manifest, role/JD honesty, request lifecycle, partial/failure/retry/previous-result handling.
3. **Dossier core:** executive hierarchy, capability matrix/inspector, evidence ledger/provenance, source receipts, claims boundaries, repository intelligence, conflicts, unknowns, and interview plan.
4. **Graph, audit, and polish:** lazy real CEG view, limitations/audit surface, mobile behavior, accessibility, performance and visual/data-integrity audit.

No backend/scoring/acquisition change is in scope. No unmerged PR dependency, database persistence for live resumes/notes, benchmark claim, model claim, decorative 3D scene/chart, or fabricated seed data is in scope. The approved 3D view visualizes only the returned CEG. If a UI requirement needs an unavailable field, omit it or label it unavailable instead of modifying the backend silently.

## Acceptance criteria

- `/` describes the current product accurately and routes cleanly to live analysis or the labeled research demo.
- Live intake is staged; source candidates/selections are inspectable before submission; parsed values are labeled as declared/extracted.
- The loading view never claims backend stages or numerical progress that the synchronous endpoint does not expose.
- Timeout/error does not erase intake or a previous successful dossier; partial responses remain inspectable.
- Summary, role context, matrix, inspector, ledger, source receipts, repository signals, claims, conflicts, interview prompts, graph, and audit use current-main response fields only.
- A null capability estimate is visibly unknown; no role target, confidence label, claim status, or authenticity is invented.
- Evidence is traceable to provenance when the source returns it; omitted provenance fields are not synthesized.
- Demo data never enters the live dossier. No live product copy asserts mastery, verified identity, issuer authentication, or successful employment performance.
- Mobile presents the priority summary and lets users inspect details without whole-page horizontal overflow.
- All interactions are keyboard accessible; graph information is available in a text equivalent; reduced motion is respected.
- Existing route/API boundaries and backend contracts remain unchanged.
- The implementation receives full build, type, Playwright, browser-console, mobile, visual, accessibility, and data-integrity review. Test execution is planned because the user requested extensive verification.

## Risks and mitigations

- **Current evidence fields vary by source:** use field-presence rendering and receipt-level omissions; test empty and partial payloads.
- **Synchronous timeout near one minute:** keep copy factual, support retry, retain prior in-memory result, and avoid fake progress.
- **Large evidence/graph payloads:** lazy-load graph, paginate or virtualize long lists only if real response sizes warrant it, and preserve search/filter semantics.
- **Existing demo/legacy assumptions:** visually isolate the controlled demo and do not reuse its scenario labels, graph assumptions, or candidate fixture in live routes.
- **Dense design can harm mobile/accessibility:** review narrow screenshots and keyboard/semantic behavior alongside the desktop visual audit.
- **Frontend redesign may exceed one implementation turn:** retain the four reviewable layers above while carrying the entire accepted scope through completion.

## Approved implementation decisions

1. `/` is the product landing page, `/analyze` is the live evaluator and dossier, and `/research-demo` remains the labeled synthetic research surface. Legacy `/workspace` and `/hr` stay outside primary navigation.
2. Interviewer notes remain browser-local and run-scoped under the request-only live storage contract.
3. Backend, scoring, and acquisition semantics remain unchanged. The 3D visualization is approved only for the actual returned CEG, with a searchable text equivalent and a WebGL-unavailable fallback.
