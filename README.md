# Candidate Capability Intelligence (CCI)

**CandidateX** is a research prototype for provenance-grounded technical capability evaluation and interviewer decision support. It converts candidate-supplied artifacts into an inspectable Candidate Evidence Graph (CEG), capability estimates, evidence-coverage diagnostics, contradictions, and prioritized technical interview probes.

> **Human decision support only.** CandidateX does not autonomously hire, reject, shortlist, or rank people for employment decisions. Public demo records may be controlled synthetic/demo data when the live backend is unavailable.

## Core invariants

- Analysis is bounded to a closed-world manifest of candidate-supplied resources.
- Untrusted candidate code is statically inspected and is never executed.
- Missing evidence is `UNKNOWN`; it lowers coverage rather than becoming a zero capability score.
- RCI and Evidence Coverage are separate outputs.
- Evidence records preserve provenance and immutable locators.
- Rescoring uses previously acquired evidence and does not require re-crawling candidate sources.

## Architecture

```text
Candidate / Role Intake
        ↓
Safe Evidence Acquisition
        ↓
Static Analyzers + Provenance
        ↓
Candidate Evidence Graph (CEG)
        ↓
Capability + Uncertainty Engine
        ↓
Contradiction Diagnostics
        ↓
Interview Probe Prioritization
        ↓
Human-Reviewed Technical Dossier
```

The monorepo contains a Next.js recruiter workspace (`apps/web`), a FastAPI / SQLAlchemy analysis service (`services/backend`), deterministic research tooling (`research`), sample role fixtures (`examples`), and verification/audit tests.

## Paper-aligned mathematical core

### Evidence recency

$$t_{e,k}=\exp(-\lambda_k\Delta t_e)$$

### Six-factor evidence confidence

$$c_{e,k}=\left(a_e\,o_e\,t_{e,k}\,v_e\,x_e\,r_{s(e)}\right)^{1/6}$$

### Capability estimate and effective evidence count

$$q_k=\frac{\sum_e c_{e,k}z_{e,k}}{\sum_e c_{e,k}},\qquad
n_{\mathrm{eff},k}=\frac{(\sum_e c_{e,k})^2}{\sum_e c_{e,k}^2}$$

### Contradiction diagnostic

$$D_k=\frac{P_k-N_k}{P_k+N_k+\epsilon}$$

### Interview probe priority, paper Eq. (11)

$$I_k=w_k\left[\alpha(1-\mathrm{Cov}_k)+\beta\,\mathrm{CIwidth}_k+\gamma\,\mathrm{Conf}_k\right]$$

### Role Capability Index

$$RCI(C,J)=\frac{\sum_{k\in\mathcal O}w_kq_k}{\sum_{k\in\mathcal O}w_k}$$

Unobserved capabilities remain outside the RCI numerator/denominator and are reflected in Evidence Coverage instead.

## Canonical engineering roles

1. Backend Engineering
2. Frontend Engineering
3. Full-stack Engineering
4. Machine Learning Engineering
5. DevOps / Cloud Engineering
6. Data Engineering

The framework evaluates twelve technical capability dimensions across those role profiles.

## Research evidence: two distinct layers

### A. Submitted-paper controlled benchmark

The submitted conference paper reports a controlled synthetic mechanism-validation experiment with:

- **16 deterministic seeds**
- **300 candidate profiles per seed**
- **6 target roles per candidate profile**
- **28,800 candidate-role evaluations**

Headline paper-reported results:

| Metric | Paper result |
|---|---:|
| Spearman $\rho$ | **0.928 ± 0.013** |
| Kendall $\tau$ | **0.774 ± 0.019** |
| nDCG@20 | **0.970 ± 0.011** |

The machine-readable provenance record is `research/paper_benchmark_manifest.json`.

Additional paper-reported controls are also recorded there, including role-agnostic ranking, source dropout, candidate shuffle, and generator-regime sensitivity.

**Validation boundary:** these are synthetic controlled-experiment results. They do not establish real-world hiring accuracy, fairness, or candidate performance. External human-reviewed validation remains future work.

### B. Repository supplementary implementation ablation

The repository separately contains a deterministic **4,800 candidate-role-sample supplementary implementation ablation**. It compares the implemented Full CCI scoring architecture against recency, ownership, role-weight, and source-reliability ablations.

This harness is intentionally labelled `paper_exact_reproduction: false`. It is useful for implementation diagnostics, but **it is not an exact regeneration of the paper benchmark** and its metrics must not be substituted for the paper's 28,800-evaluation headline results.

Run it with:

```bash
python research/run_paper_experiments.py
```

or a quick smoke configuration with:

```bash
python research/run_paper_experiments.py --quick
```

Generated artifacts live under `research/results/` and carry the supplementary-evidence provenance boundary.

## Public demo behavior

The frontend contains controlled demo candidate records so the recruiter workflow remains inspectable when the FastAPI service is unavailable. The UI explicitly identifies this boundary. Demo candidates are **not** evidence that those people were analyzed by a live production backend.

When the backend is online, the frontend uses the configured API and can retrieve live candidate/dossier/research data. When it is not, supported screens degrade to bounded demo/fallback data rather than pretending that a network analysis occurred.

## REST API highlights

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service health |
| `GET` | `/api/v1/candidates` | Candidate directory |
| `GET` | `/api/v1/dossier/{candidate_id}` | Technical dossier |
| `GET` | `/api/v1/research/theorems` | Paper-aligned theorem / formula catalog |
| `GET` | `/api/v1/research/paper-benchmark` | Submitted-paper benchmark provenance and headline results |
| `GET` | `/api/v1/research/ablation-study` | Supplementary 4,800-sample implementation ablation |
| `POST` | `/api/v1/research/calculate` | Interactive supported theorem calculations |

## Local development

### Backend

```bash
cd services/backend
python -m pip install -e ".[dev]"
pytest -v
python -m uvicorn cci.main:app --reload --port 8000
```

### Frontend

```bash
pnpm install
pnpm --filter web dev
```

## Verification

The repository includes unit, scoring, theorem, API, security, database, pipeline, export, research, and paper-alignment regression tests. The CI workflow runs Python 3.11/3.12 backend checks, frontend build/type checks, security invariants, and a research smoke run.

### Current GitHub Actions infrastructure note

During the 17 September 2026 readiness pass, GitHub created all CI jobs but terminated them before assigning a runner: the Actions API reported `steps: []`, `runner_id: 0`, and an empty runner name across backend, frontend, and security jobs. Therefore those red runs are **not evidence that pytest, pnpm, or the security suite executed and failed**.

The repository does not bypass or fake-success those checks. The external Actions runner/account condition must be resolved and the unchanged workflow rerun before calling CI green. See `docs/verification/ci-external-runner-note.md`.

Vercel deployment status is tracked independently and should not be treated as a substitute for the backend test suite.

## Limitations and next validation stage

CandidateX is an engineering/research prototype, not a validated hiring instrument. Before any consequential use, the system needs consented external validation with real hiring artifacts, inter-rater studies, calibration analysis, subgroup/fairness assessment, privacy/governance review, and operational reliability measurements.

For a classroom or conference demonstration, the appropriate claim is:

> CandidateX implements a provenance-grounded technical evidence and interview-intelligence workflow and includes controlled synthetic research evidence. It does not yet claim validated real-world hiring performance.
