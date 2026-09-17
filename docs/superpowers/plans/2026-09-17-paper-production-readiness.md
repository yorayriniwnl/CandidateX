# CandidateX Paper + Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CandidateX safe to demonstrate as the implementation companion to the submitted CCI paper without false paper-reproduction claims, paper/UI formula drift, canonical-role drift, or hidden demo-mode ambiguity.

**Architecture:** Treat the submitted paper as the publication source of truth for equations, canonical roles, and reported benchmark numbers. Keep the repository's existing 4,800-sample ablation harness as a supplementary implementation validation harness rather than relabeling it as the paper's 28,800 candidate-role benchmark. Add explicit provenance metadata so the two experimental layers cannot be confused.

**Tech Stack:** Python 3.11/3.12, FastAPI/Pydantic, Next.js 15/React/TypeScript, GitHub Actions, Vercel.

**Spec:** `Candidate_Capability_Intelligence_Conference_Paper_Submission_Ready_Final(5).docx` (publication source of truth supplied in the project review)

## Global Constraints

- Paper Eq. (11) is the canonical interview-probe formula: `I_k = w_k[alpha(1-Cov_k) + beta*CIwidth_k + gamma*Conf_k]`.
- Canonical roles are Backend, Frontend, Full-stack, ML Engineer, DevOps, and Data Engineer.
- Paper headline benchmark is synthetic mechanism validation: 16 seeds x 300 candidates x 6 roles = 28,800 candidate-role evaluations; it is not real-world hiring accuracy.
- Repository 4,800-sample ablation output must be labeled supplementary implementation evidence, not exact paper reproduction.
- Missing evidence remains UNKNOWN / lower coverage, never zero capability.
- CandidateX remains decision support only; no autonomous hire/reject claim.

---

### Task 1: Add paper-alignment contract tests

**Files:**
- Create: `services/backend/tests/test_paper_alignment_contract.py`
- Create: `research/paper_benchmark_manifest.json`

**Interfaces:**
- Consumes: submitted paper values and repository text/data files.
- Produces: regression checks for canonical roles, Eq. (11), paper benchmark provenance, and supplementary-ablation labeling.

- [ ] Write failing tests that detect `mobile` in research role defaults, old probe formulas, and ambiguous `paper reproduction` wording.
- [ ] Add a machine-readable paper benchmark manifest with the paper-reported metrics and explicit `reported_not_regenerated` provenance.
- [ ] Re-run the focused contract test and confirm green when CI execution is available.

### Task 2: Synchronize formulas and canonical roles

**Files:**
- Modify: `README.md`
- Modify: `services/backend/src/cci/api/routers/research.py`
- Modify: `apps/web/components/ResearchTheoremsExplorer.tsx`
- Modify: `apps/web/components/dossier/InterviewProbesPanel.tsx`
- Modify: `scripts/analyze_candidate.py`
- Modify: `services/backend/src/cci/reports/exporter.py`

**Interfaces:**
- Consumes: paper Eq. (11) and `CanonicalRole` enum.
- Produces: one displayed probe-priority formula and one six-role vocabulary across API, UI, CLI, exports, and documentation.

- [ ] Replace all stale displayed probe formulas with Eq. (11).
- [ ] Replace the research fallback `mobile` row with `data_engineer`.
- [ ] Keep backend computational implementation unchanged where it already matches Eq. (11).
- [ ] Verify repository search returns no stale formula or research-role `mobile` occurrence.

### Task 3: Separate publication benchmark from implementation ablation harness

**Files:**
- Modify: `README.md`
- Modify: `research/run_paper_experiments.py`
- Modify: `services/backend/src/cci/research/simulation.py`
- Modify: `services/backend/src/cci/api/routers/research.py`
- Modify: `apps/web/components/ResearchTheoremsExplorer.tsx`

**Interfaces:**
- Consumes: `research/paper_benchmark_manifest.json` and current `research/results/ablation_results.json`.
- Produces: two explicitly named evidence layers: Paper Reported Synthetic Benchmark and Repository Supplementary Ablation Harness.

- [ ] Stop calling the existing 4,800-sample harness an exact paper reproduction.
- [ ] Describe its unit correctly as candidate-role samples from role-specific cohorts.
- [ ] Surface the paper-reported 28,800-evaluation benchmark separately with the paper caveat that it validates mechanism behavior only.
- [ ] Preserve the existing ablation numbers as implementation diagnostics instead of overwriting them with paper numbers.

### Task 4: Make demo mode explicit

**Files:**
- Modify: `apps/web/components/SystemNotice.tsx`
- Modify: `apps/web/app/page.tsx` only if needed for status copy.

**Interfaces:**
- Consumes: `isBackendOnline` already computed by the app.
- Produces: unambiguous live-backend vs controlled-demo labeling.

- [ ] Ensure an offline backend is visibly labeled controlled demo data, not silently presented as live candidate analysis.
- [ ] Keep the decision-support and missing-evidence notices visible.

### Task 5: Fix portfolio evidence claims

**Repository:** `yorayriniwnl/Portfolio-Ayush-Roy`

**Files:**
- Modify: `src/content/candidatex.ts`
- Modify: `src/content/claims.ts`
- Add/update tests protecting the distinction between 4,800 supplementary samples and 28,800 paper candidate-role evaluations.

- [ ] Change `Research cohort: 4,800` from a publication claim to a supplementary implementation-harness claim.
- [ ] Add the paper-reported 28,800 candidate-role evaluation claim with synthetic-mechanism caveat.
- [ ] Update case-study wording so it never says the current ablation runner reproduces the paper tables exactly.

### Task 6: CI and deployment verification

**Files:**
- Modify `.github/workflows/ci.yml` only if root-cause evidence points to workflow configuration.

- [ ] Confirm whether jobs reach a runner.
- [ ] If jobs still finish with `runner_id=0` and zero steps, classify as GitHub Actions account/runner availability rather than code failure; do not paper over it with workflow edits.
- [ ] Confirm Vercel deployment succeeds for the final merge commit.
- [ ] Check the public project page and CandidateX deployment after merge.

### Task 7: Final verification

- [ ] Search for stale formulas, `Mobile Engineering` in research defaults, and ambiguous exact-reproduction claims.
- [ ] Review PR diff for scope creep.
- [ ] Merge only after verification evidence is collected.
