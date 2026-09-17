# Candidate Capability Intelligence (CCI) — Frozen Interface Specification

## 1. Architectural Overview & Invariants

Candidate Capability Intelligence (CCI) provides employer/interviewer-side technical decision support through structured, provenance-grounded evidence acquisition, statistical calibration, and multi-factor fusion.

### Core Product Invariants

1. **Employer Decision Support**: System assists technical interviewers; it never renders autonomous hire/reject decisions.
2. **CV as Candidate Manifest**: Extraction is strictly bounded by materials supplied by the candidate. No unconstrained web scraping or unsupplied identity discovery.
3. **Deep vs. Light Scanning**:
   - Explicit CV-listed repositories receive **DEEP** analysis (bounded AST, dependency graph, testing, and infra extraction).
   - Remaining repositories on the explicitly provided GitHub profile receive **LIGHT** analysis (commit counts, languages, recency, high-level metadata).
4. **Missing Evidence is UNKNOWN**: Lack of evidence reduces **Evidence Coverage**, but never assigns zero capability by default.
5. **Separation of RCI and Coverage**:
   - **RCI** reflects estimated technical proficiency on observed capabilities.
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

### 3.3. Six-Factor Multiplicative Evidence Confidence
Each evidence record $e$ supporting capability $k$ is evaluated across six factors:
$$c_{e,k} = \left( a_e \cdot o_e \cdot t_{e,k} \cdot v_e \cdot x_e \cdot r_s(e) \right)^{1/6}$$
- $a_e \in (0, 1]$: Artifact validity / parser integrity
- $o_e \in (0, 1]$: Authorship / ownership attribution
- $t_{e,k} \in (0, 1]$: Temporal recency decay
- $v_e \in (0, 1]$: Direct operational verification level
- $x_e \in (0, 1]$: Technical depth and specificity
- $r_s(e) \in (0, 1]$: Source family posterior reliability

### 3.4. Capability Estimate & Effective Evidence Count
$$q_k = \frac{\sum_{e} c_{e,k} \cdot z_{e,k}}{\sum_{e} c_{e,k}}$$
If no usable evidence exists for capability $k$: $q_k = \text{None}$ (`UNKNOWN`).

Effective evidence count $n_{\text{eff},k}$ accounting for correlation:
$$n_{\text{eff},k} = \frac{\left(\sum_e c_{e,k}\right)^2}{\sum_e c_{e,k}^2}$$

Standard Error:
$$SE_k = \frac{s_k}{\sqrt{\max(1, n_{\text{eff},k})}}$$
where $s_k$ is the confidence-weighted sample standard deviation of $\{z_{e,k}\}$.

### 3.5. Contradiction Diagnostic
$$D_k = \frac{P_k - N_k}{P_k + N_k + \epsilon}$$
- $P_k = \sum_{e \in \text{pos}} c_{e,k}$: Total positive evidence support
- $N_k = \sum_{e \in \text{neg}} c_{e,k}$: Total negative/contradictory evidence support
- $\epsilon = 10^{-5}$: Numerical stabilization factor
- $D_k \in [-1, 1]$: $D_k \to 1$ indicates strong consensus; $D_k \to -1$ indicates severe contradiction.

### 3.6. JD Role Importance & Softmax Role Weights
Unnormalized role importance for capability $k$:
$$u_k = \eta_1 m_k + \eta_2 p_k + \eta_3 \ln(1 + f_k) + \eta_4 s_k$$
- $m_k$: Count of mandatory requirements
- $p_k$: Count of preferred requirements
- $f_k$: Mention frequency in JD
- $s_k$: Semantic specificity rating

Normalized role weights:
$$w_k = \frac{\exp(u_k / T)}{\sum_j \exp(u_j / T)}, \quad \sum_k w_k = 1.0$$

### 3.7. Evidence Coverage & Role Capability Index (RCI)
Capability-specific coverage:
$$\text{Cov}_k = \min\left(1, \frac{\sum_e c_{e,k}}{\tau_k}\right)$$
Overall Evidence Coverage across role:
$$\text{Coverage}(C, J) = \sum_{k=1}^{12} w_k \cdot \text{Cov}_k$$

Role Capability Index (RCI) computed strictly over observed capabilities:
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
- `EvidenceConfidenceFactors`: The 6 confidence components.
- `EvidenceInput`: Analyzer observation before registration.
- `EvidenceRecord`: Immutable registered evidence with SHA-256 fingerprint.
- `SourceReliabilitySnapshot`: Beta prior/posterior state.
- `OwnershipAssessment`: Authorship estimation and feature vectors.
- `CapabilityEstimate`: $q_k, n_{\text{eff},k}, SE_k$, and bootstrap CI.
- `CapabilityUncertainty`: Epistemic uncertainty and CI bounds.
- `CapabilityConflict`: Contradiction diagnostic $D_k$.
- `RoleProfile`: Softmax weights $w_k$ summing to 1.0.
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
