# CandidateX // Evidence OS implementation plan

**Date:** 2026-09-23
**Spec:** `docs/superpowers/specs/2026-09-23-candidatex-evidence-os.md`
**Target:** audited `origin/main` worktree, branch `codex/candidatex-evidence-os`

## Goal

Implement the complete approved Evidence OS frontend across `/`, `/analyze`, and `/research-demo`, preserving current backend/API contracts and evidence semantics. The live experience must be traceable, truthful, resilient to bounded synchronous acquisition, and usable on desktop and mobile. Do not stop at a refreshed intake or a summary-only result page.

## Guardrails

- Before changing Next.js code, read the relevant Next.js 16 guides under `apps/web/node_modules/next/dist/docs/` as required by `apps/web/AGENTS.md`.
- Keep all new sample values inside explicitly labeled Playwright fixtures or the existing research demo. Live UI renders only the returned run.
- Preserve private/public URL validation, upload bounds, source selection rules, scoring, `partial` semantics, and request-only persistence.
- Do not add backend schema or scoring changes. Do not consume draft PR #20 fields.
- Add/adjust Playwright tests before their implementation (red/green); retain the existing real local upload-to-backend flow.
- Use the repo's pnpm commands. The web `lint` and `typecheck` scripts are both `tsc --noEmit`.
- Keep the original checkout's four uncommitted files untouched; all work stays in the managed worktree.

## Work sequence

### 1. Product shell, tokens, and landing page

1. Add failing Playwright assertions for `/` landing copy, primary `/analyze` CTA, secondary `/research-demo` CTA, and no unsupported AI/verification claims.
2. Read the Next.js App Router, CSS Modules/global CSS, server/client boundary, and accessibility guides relevant to the edits.
3. Establish design tokens for background/surface/text/border/status/role accent, shared type/spacing/focus rules, and restrained motion/reduced-motion behavior. Replace the app-wide one-off palette gradually as components move into the new system; do not leave a second unrelated design system on the primary flow.
4. Replace the root redirect with a concise CandidateX landing page and accurate product language. Keep the research demo visibly labeled synthetic.
5. Run the new route assertions and the existing research-demo tests; inspect desktop and mobile landing screenshots.

### 2. Staged intake and synchronous run lifecycle

1. Add failing tests for a four-stage stepper, next/back behavior, resume replacement/removal, parsed intake summary, extracted source manifest, source selection, optional role/JD, duplicate-submit prevention, and retained form state after errors.
2. Build composed analysis components for resume intake, role/JD entry, source manifest, review, and run status. Keep file extraction and backend submission tied to existing API operations.
3. Make source selection precise: show what the browser has extracted, what is selected for the request, and what is unsupported/unselected only where the current UI or API provides that fact. Do not label any source fetched before the response returns.
4. Model run lifecycle only as request prepared/submitted, waiting, response received, failed, or timed out. Use layout-matched skeletons with no fabricated numbers or acquisition-stage completion states.
5. Separate the previous completed result from the in-flight attempt. A later failure preserves both the earlier dossier (clearly identified as earlier) and current form/selections; retry resubmits the current intake.
6. Verify the user can reach the true partial, no-GitHub, inaccessible/unsupported-link, large-JD, no-JD, timeout, and first-run error states through deterministic tests while keeping the existing local backend integration test.

### 3. Dossier shell and decision summary

1. Add failing tests for the first viewport's candidate/role/run identity, nullable RCI, separate evidence coverage, observed/total capabilities, source/inspection counts when derivable, and unknowns. Assert missing values stay `UNKNOWN` and never format as zero or a percentage.
2. Replace the current stacked result panels with a responsive dossier shell: sticky desktop section rail, concise sticky summary, ordered sections, clear headings, semantic status legend, and mobile priority flow.
3. Implement the executive summary and a semantic capability matrix from `dossier.capability_estimates`, `role_weights`, `role_requirements`, `capability_conflicts`, and actual `evidence_records` only. Show numeric role emphasis only when returned; never manufacture numeric targets or calculate a gap between unlike scales.
4. Add a capability inspector connected to selected matrix rows. Show returned estimates, counts, interval/uncertainty values, role weight, conflicts, and linked evidence with only available fields.
5. Run typecheck and the focused Playwright assertions; inspect the desktop first viewport and narrow mobile result before expanding to secondary sections.

### 4. Evidence, source, claim, repository, conflict, and interview tools

1. Add failing tests for ledger search/filter/sort/row expansion, capability/source filtering, positive/negative support, source receipt drilldown, repository inspection scope, claims boundaries, conflict evidence links, and interview question grounding.
2. Build an evidence ledger over live `evidence_records`, with semantic table markup, aligned numeric columns, keyboard operation, responsive detail disclosure, and provenance drawer/expansion. Search/filter results must be deterministic and instant at current payload sizes.
3. Build source inventory and receipts over actual `sources`: render returned receipt fields, distinguish statuses using backend values, and keep missing metadata explicit. Link a receipt's evidence rows into the ledger.
4. Build repository intelligence from returned repository review data and repeat the inspected-files limitation next to signals/technology lists.
5. Add the bounded skill-corroboration view using current `claims_corroboration`, declared skills, and report output. Do not synthesize a general resume claim ledger, academic records, or unsupported statuses from PR #20.
6. Present meaningful conflict diagnostics with their triggering evidence and an unknown-state explanation for unobserved capabilities.
7. Build the interview plan from returned probes/questions. Add optional run-scoped notes in browser memory only, visibly labeled local-only and discarded on run change/refresh; do not imply persistence or call unrelated storage endpoints.
8. Preserve existing dossier export and supported scorecard controls only where their live request flow remains valid.

### 5. Real graph, audit, accessibility, and performance

1. Add failing tests that graph nodes/edges are from the active `LiveResult.graph`, selecting a real evidence node opens its inspector, and a textual equivalent is present without relying on hover.
2. Replace or bypass the prototype graph layout that assumes fixed node types. Lazy-load a light 2D/SVG view from actual nodes/edges and provide keyboard-accessible search/list/detail interaction. Empty or unknown node types must remain visible and readable.
3. Add an audit/limitations view for the returned run ID, generated time, versions, system limitations, and source-level receipts.
4. Test the full dossier at narrow mobile widths, keyboard-only, reduced motion, and accessible names/focus/dialog behavior. Fix horizontal overflow and dense table interactions, not merely hide content.
5. Bound rendering for large evidence lists; lazy-load graph, progressively disclose raw provenance, and memoize only meaningful transforms. Avoid adding visualization dependencies unless native SVG cannot meet the actual graph needs.

### 6. End-to-end validation, visual audit, and screenshots

1. Keep at least one real local backend upload-to-analysis run using a synthetic software-engineer resume fixture, with no personal resume submitted to production. Exercise a normal populated intake, sparse/no GitHub, inaccessible LinkedIn, several repository receipts, unsupported public page, partial acquisition, no JD, and a large JD using controlled fixtures where an external service would make a test unstable.
2. Extend Playwright for upload/extraction, source selection, run success/partial/timeout/error, retained prior result, capability navigation, evidence inspection, claim inspection, source receipt, interview plan, graph, keyboard flow, and mobile result. Assertions must check data provenance and truth labels as well as visible controls.
3. Run `pnpm --filter web typecheck`, `pnpm --filter web build`, and `pnpm --filter web test`; run relevant backend/API contract tests without changing backend behavior.
4. Inspect screenshots for intake, running state, result overview, capability inspector, evidence ledger, source receipt, interview plan, graph, and mobile result. Review browser console/page errors and HTTP failures, desktop hierarchy, actual unknown/partial result, color semantics, keyboard focus, text alternative, reduced motion, and scroll width. Fix issues and capture the final set.
5. Review the final diff against the spec and ensure legacy sample routes remain identified as such, research demo remains isolated, and the original checkout remains unchanged.

## Completion evidence

- Green web typecheck/build and full Playwright suite; relevant backend/API compatibility checks green.
- Screenshots for all nine requested states saved under the existing Playwright artifact directory and visually inspected.
- Runtime browser review confirms no page/console/HTTP errors, no mobile horizontal overflow, and accurate rendering of a real partial/unknown local backend response.
- Final source audit finds no fake production metrics, fake progress stages, PR-only fields, unsupported verification language, or changed backend/scoring contracts.
- Report names UX findings, visual/IA/component changes, data tables/graph, responsive/accessibility/performance work, test/build results, remaining limits, and screenshot paths.
