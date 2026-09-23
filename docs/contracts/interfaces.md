# Candidate Capability Intelligence (CCI) — Frozen Interface Specification

## 1. Architectural Overview & Invariants

Candidate Capability Intelligence (CCI) provides employer/interviewer-side technical decision support through structured, provenance-grounded evidence acquisition, statistical calibration, and multi-factor fusion.

### Core Product Invariants

1. **Employer Decision Support**: System assists technical interviewers; it never renders autonomous hire/reject decisions.
2. **CV as Candidate Manifest**: Extraction is strictly bounded by materials supplied by the candidate. No unconstrained web scraping or unsupplied identity discovery.
3. **Deep vs. Light Scanning**:
   - Explicit CV-listed repositories receive **DEEP** analysis (bounded AST, dependency graph, testing, and infra extraction).
   - Remaining repositories on the explicitly provided GitHub profile receive **LIGHT** analysis (commit counts, languages, recency, high-level metadata).
4. **Missing or insufficiently attributed evidence is UNKNOWN**: It reduces **Evidence Coverage** and withholds the candidate estimate, but never assigns zero capability by default.
5. **Separation of RCI and Coverage**:
   - **RCI** reflects estimated technical proficiency only on capabilities meeting the configured attribution-gated coverage threshold.
   - **Evidence Coverage** measures the proportion of role-critical capabilities supported by empirical evidence.
6. **No Code Execution**: Candidate code is never executed, built, or run in test runners. All extraction is deterministic static and operational inspection.
7. **Absolute Provenance & Immutability**: Every derived observation retains its cryptographic fingerprint, file/symbol locator, and analyzer version. Evidence rows are immutable in persistence.
8. **Decoupled Acquisition & Rescoring**: Evidence acquisition is expensive and cached; role re-scoring against new or updated job descriptions is purely functional and inexpensive.
9. **No Demographic or Personality Inference**: Scoring is mathematically and structurally isolated from protected demographic attributes.

---

## 2. Canonical Roles & Capabilities

### The Six Canonical Roles (`CanonicalRole`)
- `backend`: Backend Engineering & Distributed Systems
- `frontend`: Frontend Engineering & Client Architectures
- `fullstack`: Fullstack Systems & Web Applications
- `ml_engineer`: Machine Learning Systems & Modeling
- `devops_cloud`: DevOps, Cloud Infrastructure & Reliability
- `data_engineer`: Data Engineering & Pipeline Infrastructure

### The Twelve Core Capabilities (`CapabilityKey`)
1. `backend_engineering`: Server-side architecture, APIs, routing, asynchronous workflows.
2. `frontend_engineering`: UI components, state management, web performance, accessibility.
3. `database_engineering`: Schema design, ORM, migrations, transactions, indexing, SQL queries.
4. `devops_cloud`: Containerization, CI/CD pipelines, IaC, Kubernetes, environment config.
5. `machine_learning`: Model architecture, training pipelines, evaluation, inference serving.
6. `data_engineering`: ETL/ELT pipelines, streaming, distributed processing, batch compute.
7. `algorithms_problem_solving`: Algorithmic complexity, data structures, optimization.
8. `testing_quality`: Unit/integration/e2e test design, assertions, mocks, test fixtures.
9. `security`: Authentication, authorization, input validation, secrets management, SSRF guards.
10. `software_architecture`: Modular boundaries, design patterns, separation of concerns, ADRs.
11. `collaboration`: Git workflows, PR quality, code review participation, teamwork indicators.
12. `documentation_communication`: API documentation, setup instructions, architecture docs, READMEs.

---

## 3. Mathematical Framework

### 3.1. Beta-Posterior Source Reliability
For each source family $s \in \{\text{Resume}, \text{GitHub}, \text{Deployment}, \text{Database}, \text{Coding}, \text{Certificate}, \text{LinkedIn}\}$:
$$r_s = \frac{TP_s + \alpha_s}{TP_s + FP_s + \alpha_s + \beta_s}$$

### 3.2. Capability-Specific Recency Decay
Given elapsed time $\Delta t_e$ (in years) since observation:
$$t_{e,k} = \exp(-\lambda_k \cdot \Delta t_e)$$
where $\lambda_k$ is the decay rate specific to capability $k$.

For live repository evidence, $\Delta t_e$ is derived from the latest usable GitHub-reported commit touching the exact artifact path at the pinned repository revision. Git committer timestamps are repository metadata, not independent time attestations. `EvidenceRecord.artifact_recency` records the path timestamp and commit SHA, any latest commit linked to the declared GitHub account, and `repository_last_activity` as separate context. If path history is unavailable, malformed, or outside the bounded request budget, the state is `artifact_recency_unknown`; repository activity is never substituted for artifact age. The neutral recency multiplier used for an unknown value is not a freshness claim, and the explicit state and limitations must be retained.

### 3.3. Attribution-Gated Evidence Weight
Each evidence record $e$ supporting capability $k$ combines five evidence-quality factors and a direct candidate-attribution gate:
$$q_{e,k} = \left( a_e \cdot t_{e,k} \cdot v_e \cdot x_e \cdot r_s(e) \right)^{1/5}, \qquad c_{e,k} = o_e \cdot q_{e,k}$$
- $a_e, t_{e,k}, v_e, x_e, r_s(e) \in [0, 1]$: Artifact integrity, recency, verification, technical specificity, and source reliability
- $o_e \in [0, 1]$: Path-specific account contribution ratio used as a direct gate; it is not a calibrated probability

The result is bounded by attribution ($c_{e,k} \le o_e$). With five quality factors at $0.75$ and attribution at $0.03$, the old sixth-root formula gives $0.4386$, while the gated rule gives $0.0225$. No hard cutoff is applied because an empirically validated threshold is unavailable.

### 3.4. Capability Estimate & Effective Evidence Count
Scoring config `5.1.0` first applies a semantic family multiplier $\alpha_e$ to confidence. Within each evidence family, the strongest observation for each observation type and support polarity contributes; those representatives are ranked by confidence and receive geometric weights $1, \gamma, \gamma^2, \ldots$ (`evidence_family_decay = 0.5` by default). Repeated observations of the same type remain in provenance with zero contribution. Aggregates use $\tilde c_{e,k} = c_{e,k}\alpha_e$:
$$q_k = \frac{\sum_{e} \tilde c_{e,k} \cdot z_{e,k}}{\sum_{e} \tilde c_{e,k}}$$
If no usable evidence exists for capability $k$: $q_k = \text{None}$ (`UNKNOWN`).

Effective evidence count $n_{\text{eff},k}$ accounting for correlation:
$$n_{\text{eff},k} = \frac{\left(\sum_e \tilde c_{e,k}\right)^2}{\sum_e \tilde c_{e,k}^2}$$

Standard Error:
$$SE_k = \frac{s_k}{\sqrt{\max(1, n_{\text{eff},k})}}$$
where $s_k$ is the confidence-weighted sample standard deviation of $\{z_{e,k}\}$.

### 3.5. Contradiction Diagnostic
$$D_k = \frac{P_k - N_k}{P_k + N_k + \epsilon}$$
- $P_k = \sum_{e \in \text{pos}} \tilde c_{e,k}$: Total positive evidence support after family weighting
- $N_k = \sum_{e \in \text{neg}} \tilde c_{e,k}$: Total negative/contradictory evidence support after family weighting
- $\epsilon = 10^{-5}$: Numerical stabilization factor
- $D_k \in [-1, 1]$: $D_k \to 1$ indicates strong consensus; $D_k \to -1$ indicates severe contradiction.

### 3.6. JD Role Importance & Softmax Role Weights
Scoring config `5.1.0` starts with the canonical role-prior logit $b_{r,k}$ and adds a bounded JD adjustment. Requirement groups are keyed by case- and punctuation-normalized requirement text; capability mappings still come from the controlled technology ontology. Exact repeated requirements contribute once, using the stronger priority. Distinct requirements that share a technology keyword remain distinct groups. For each group $g$ mapped to capability $k$, $h_{g,k}$ is mapping confidence times semantic specificity times a priority multiplier (1.0 mandatory, 0.5 preferred, 0.25 nice to have, 0.0 optional). Raw keyword mention frequency is not an input.

Distinct requirement groups mapped to one capability are ordered by group strength and receive geometric diminishing returns:
$$S_k = \sum_{g=1}^{n_k} h_{g,k}\,\delta_{JD}^{g-1}, \qquad A_k = A_{max}\left(1 - e^{-S_k / \kappa}\right), \qquad u_k = b_{r,k} + A_k$$
The defaults are $\delta_{JD}=0.5$, $A_{max}=1.5$, and $\kappa=2.0$. Thus, no number of requirements can add more than 1.5 logit units to one capability. The max-adjustment setting is a policy bound, not an empirically calibrated parameter.

The automatic role profile applies temperature-scaled softmax to $u_k$, then projects the result onto a bounded probability simplex: each capability weight is at least 0.01 and at most 0.40, and the weights sum to 1.0. The temperature must be at least 0.5. Empty or unmapped JDs leave the canonical role-prior profile unchanged. The pure softmax function remains available for the mathematical invariance check; production role profiles additionally apply the explicit bounds. A separately audited expert override remains an explicit manual exception and may exceed these automatic-profile bounds.

| Adversarial JD | Role | Highest weights | Lowest weight |
| --- | --- | --- | ---: |
| One mandatory Python requirement | Backend | Backend 36.35%, database 14.16% | 1.92% |
| Python mentioned 20 times | Backend | Same as one mention: backend 36.35%, database 14.16% | 1.92% |
| Balanced backend requirements | Backend | Backend 33.03%, database 16.77%, architecture 10.17% | 1.35% |
| Security-heavy backend requirements | Backend | Database 22.96%, backend 22.52%, security 11.79% | 1.85% |
| Full-stack requirements | Full stack | Frontend 23.00%, backend 17.40%, testing 11.39% | 1.51% |
| Generic, empty, or unmapped marketing JD | Backend | Canonical backend prior: backend 26.83%, database 16.28%, algorithms 9.87% | 2.20% |

These are deterministic outputs under the default policy settings, not empirically calibrated hiring weights. The machine-readable matrix includes all 12 capability weights per scenario at `docs/audits/jd-weighting-adversarial-matrix.json`.

### 3.7. Evidence Coverage & Role Capability Index (RCI)
Within independent source cluster $g$, evidence is grouped by artifact. An artifact contributes its strongest attribution-gated confidence $q_{g,j}$ once; distinct artifacts are ordered from strongest to weakest and receive geometric diminishing returns with configured decay $\delta$ (default 0.5):
$$M_{g,k} = \sum_{j=1}^{n_g} q_{g,j}\delta^{j-1}, \qquad \text{Cov}_k = \min\left(1, \frac{\sum_g M_{g,k}}{\tau_k}\right)$$
The cluster identity combines source family and normalized cluster ID (falling back to source locator). Content-identical artifacts across clusters are credited once. Family multipliers adjust confidence before both capability estimation and coverage. This keeps semantic observation correlation, artifact depth, and source independence distinct.
Overall Evidence Coverage across role:
$$\text{Coverage}(C, J) = \sum_{k=1}^{12} w_k \cdot \text{Cov}_k$$

A candidate capability estimate is emitted only when attribution-gated coverage meets `ScoringConfig.low_coverage_threshold` (0.35 by default). Below that threshold, the estimate is `UNKNOWN` (`None`); its technical observations and nonzero coverage remain available, and no zero capability is inferred.

Role Capability Index (RCI) computed strictly over capabilities whose attribution-gated coverage meets the configured threshold:
$$\text{RCI}(C, J) = 100 \cdot \frac{\sum_{k \in \text{observed}} w_k \cdot q_k}{\sum_{k \in \text{observed}} w_k}$$

### 3.8. Probe Priority Index
Priority score directing the interviewer's focus:
$$I_k = w_k \cdot \left[ \alpha (1 - \text{Cov}_k) + \beta \cdot \text{CIwidth}_k + \gamma \cdot \text{Conf}_k \right]$$
Default hyperparameters: $\alpha = 0.40, \beta = 0.35, \gamma = 0.25$.

---

## 4. Frozen Domain Schemas (`cci.domain.contracts`)

All models are defined with Pydantic V2 and `model_config = ConfigDict(frozen=True)`.

### Summary of Contracts
- `CandidateManifest`: Digital profile and claims extracted from CV.
- `NormalizedRequirement`: Standardized requirement from JD.
- `EvidenceConfidenceFactors`: Five evidence-quality factors plus the separate attribution gate.
- `EvidenceInput`: Analyzer observation before registration.
- `EvidenceRecord`: Immutable registered evidence with SHA-256 fingerprint and explicit artifact-recency state.
- `ArtifactRecency`: Path-specific modification time and immutable revision, declared-account contribution time where available, separate repository activity, or an explicit unknown state.
- `SourceReliabilitySnapshot`: Beta prior/posterior state.
- `OwnershipAssessment`: Authorship estimation and feature vectors.
- `CapabilityEstimate`: $q_k, n_{\text{eff},k}, SE_k$, and bootstrap CI.
- `CapabilityUncertainty`: Epistemic uncertainty and CI bounds.
- `CapabilityConflict`: Contradiction diagnostic $D_k$.
- `RoleProfile`: Bounded automatic weights $w_k$ summing to 1.0, including the temperature used; explicit expert overrides remain separately identified.
- `AnalysisScore`: RCI, Coverage, and sufficiency status.
- `ProbePriority`: Ranked inquiry targets $I_k$.
- `InterviewQuestion`: Evidence-grounded probe questions.
- `Dossier`: Consolidated snapshot for interviewer UI.
- `ScoringConfig`: Complete versioned mathematical hyperparameters.

---

## 5. Persistence Schema (SQLAlchemy 2.0 / Alembic)

All 41 entities are implemented in `cci.db.models`:

1. `organizations` (Multi-tenant boundary)
2. `users` (User accounts)
3. `candidates` (Candidate record)
4. `identities` (Digital platform accounts)
5. `identity_links` (Provenance linking identity to evidence)
6. `candidate_documents` (Uploaded documents)
7. `candidate_sources` (Registered evidence sources)
8. `projects` (Candidate projects)
9. `job_descriptions` (Role requirements source)
10. `role_profiles` (Derived role weights)
11. `role_requirements` (Normalized requirements)
12. `role_weight_overrides` (Audit log for manual adjustments)
13. `analysis_runs` (Analysis lifecycle)
14. `analysis_stage_runs` (Stage execution states)
15. `source_snapshots` (Acquisition point-in-time)
16. `repositories` (GitHub repositories)
17. `repository_contributors` (Commit/blame statistics)
18. `repository_artifacts` (Repository-artifact links)
19. `artifacts` (Immutable indexed artifacts)
20. `evidence` (Immutable evidence records)
21. `evidence_capability_links` (Evidence-to-capability mappings)
22. `evidence_clusters` (Correlated evidence groupings)
23. `claims` (Candidate self-claims)
24. `claim_evidence_links` (Claim corroboration links)
25. `requirement_evidence_links` (Requirement satisfaction links)
26. `source_reliability_posteriors` (Beta posterior parameters)
27. `ownership_assessments` (Authorship estimation outputs)
28. `capability_estimates` (Estimated capability scores)
29. `capability_uncertainty` (Uncertainty diagnostics)
30. `capability_conflicts` (Contradiction diagnostics)
31. `analysis_scores` (Overall RCI and Coverage)
32. `scoring_configs` (Versioned parameter configurations)
33. `interview_probe_priorities` (Ranked probe priorities)
34. `interview_questions` (Interviewer questions)
35. `dossier_items` (Individual dossier sections)
36. `dossier_snapshots` (Consolidated dossier snapshots)
37. `analyzer_versions` (Registered code analyzer versions)
38. `model_versions` (Registered heuristic/ML model versions)
39. `audit_events` (System audit trail)
40. `correction_requests` (Data correction workflow)
41. `deletion_events` (GDPR/privacy deletion records)

### Immutability Invariant
`evidence`, `artifacts`, `audit_events`, and `deletion_events` inherit `ImmutableModelMixin`. The SQLAlchemy ORM listener `guard_immutable_entities` automatically raises a `ValueError` on any attempt to update a persisted row.

---

## 6. Agent Ownership Boundaries

| Agent | Exclusive File Ownership | Shared Interfaces Consumed |
| :--- | :--- | :--- |
| **Agent 00** | `/`, `package.json`, `Makefile`, `.env.example`, `apps/web/` scaffold, `services/backend/src/cci/main.py`, `config.py`, `domain/`, `db/`, `api/contracts/`, `alembic/`, `docs/contracts/` | Foundation definitions |
| **Agent 01** | `services/backend/src/cci/scoring/`, `uncertainty/`, `contradictions/`, `probes/priority.py` | `ScoringConfig`, `EvidenceRecord`, `OwnershipAssessment`, `SourceReliabilitySnapshot` |
| **Agent 02** | `services/backend/src/cci/intake/`, `jobs/`, `identity/` | `CandidateManifest`, `NormalizedRequirement`, `IdentityLink` |
| **Agent 03** | `services/backend/src/cci/github/`, `sources/`, `analyzers/repository/`, `security/repository_workspace.py` | `SourceSnapshot`, `Repository`, `Artifact` |
| **Agent 04** | `services/backend/src/cci/analyzers/code/`, `analyzers/documentation/` | `Artifact`, `EvidenceInput` |
| **Agent 05** | `services/backend/src/cci/analyzers/database/`, `analyzers/testing/`, `analyzers/infra/` | `Artifact`, `EvidenceInput` |
| **Agent 06** | `services/backend/src/cci/analyzers/deployment/`, `security/network.py` | `SourceState`, `EvidenceInput` |
| **Agent 07** | `services/backend/src/cci/ownership/`, `reliability/` | `OwnershipAssessment`, `SourceReliabilitySnapshot` |
| **Agent 08** | `services/backend/src/cci/evidence/`, `claims/`, `dossier/`, `api/routes/evidence.py`, `graph.py`, `dossier.py` | `EvidenceRecord`, `Dossier`, `CEGGraphResponse` |
| **Agent 09** | `research/` | `ScoringConfig`, formal scoring functions |
| **Agent 10** | `apps/web/app/(auth)/`, `dashboard/`, `analyses/new/`, `analyses/[id]/manifest/`, `progress/`, `features/analyses/`, `features/candidates/intake/` | `CandidateResponse`, `AnalysisRunResponse`, `StageProgressResponse` |
| **Agent 11** | `apps/web/app/analyses/[id]/overview/`, `capabilities/`, `requirements/`, `repositories/`, `evidence/`, `contradictions/`, `dossier/` | `DossierResponse`, `ScoringOverviewResponse`, `InterviewProbesResponse` |
| **Agent 12** | `infra/`, `.github/workflows/`, `Dockerfile`, `docker-compose.yml` | Backend & Web runtime contracts |
| **Agent 13** | `services/backend/src/cci/workers/`, `api/routes/analyses.py`, `candidates.py`, `services/orchestration/`, `apps/web/lib/api/` | All Wave 1 modules |
| **Agent 14** | `docs/verification/`, audit test suites | Full system verification |
| **Agent 15** | Deployment scripts, production staging verification | Verified container artifacts |
