# Candidate Capability Intelligence (CCI)

[![CI Pipeline](https://github.com/CandidateX/CandidateX/actions/workflows/ci.yml/badge.svg)](https://github.com/CandidateX/CandidateX/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: Proprietary / Conference Submission](https://img.shields.io/badge/License-Academic_Conference_Submission-red.svg)](#)

> **Candidate Capability Intelligence (CCI)** is a formal, provenance-grounded technical capability evaluation and interview intelligence platform. Built strictly in alignment with the Max-Technical conference paper specification, CCI transforms messy, heterogeneous candidate artifacts (CVs, git commits, codebases, schemas, CI/CD configs, live deployments) into an interpretable **Candidate Evidence Graph (CEG)**, statistically rigorous capability estimates, contradiction diagnostics, and prioritized interview probes.

---

## Table of Contents

1. [Core Product Invariants](#core-product-invariants)
2. [System Architecture & Monorepo Structure](#system-architecture--monorepo-structure)
3. [Formal Mathematical Framework](#formal-mathematical-framework)
4. [Paper Reproducibility & Ablation Studies](#paper-reproducibility--ablation-studies)
5. [Quickstart & Local Development](#quickstart--local-development)
6. [Docker Deployment](#docker-deployment)
7. [Verification & Test Matrix](#verification--test-matrix)

---

## Core Product Invariants

CCI is designed under strict ethical, mathematical, and operational constraints:

1. **Employer Decision Support Only**: CCI assists human interviewers and hiring managers with structured evidence, diagnostics, and probe questions; it **never** makes autonomous hire/reject decisions.
2. **Closed-World CV Candidate Manifest**: Analysis is strictly constrained to resources explicitly supplied by the candidate (e.g. CV, linked GitHub, portfolio links). No unconstrained scraping or unsupplied identity discovery.
3. **Candidate Code is NEVER Executed**: Untrusted candidate repositories are analyzed purely via static deterministic AST parsers (Python, TypeScript/JavaScript, Go, Java, C++), dependency manifests, and infrastructure definitions. No test runners, containers, sub-processes, or headless JS browsers are ever launched against candidate code.
4. **Missing Evidence is `UNKNOWN`**: A lack of evidence on a skill drops **Evidence Coverage**, but never assigns an arbitrary zero capability score.
5. **Separation of RCI and Coverage**:
   - **Role Capability Index (RCI)** reflects estimated capability strictly across *observed* technical dimensions.
   - **Evidence Coverage** reflects the fraction of job-critical capabilities backed by sufficient empirical evidence.
6. **Immutable Provenance**: Every evidence record is immutable and cryptographically fingerprinted with commit hash, file locator, and AST symbol path.
7. **Purely Functional Rescoring**: Evidence acquisition is cached; re-evaluating a candidate against a revised Job Description or customized role weights is instantaneous and purely functional.
8. **Strict SSRF Security**: Live deployment inspection enforces multi-layered SSRF guards: DNS pinning, RFC 1918 private IP blocking, loopback blocking, redirect hop validation, and cloud metadata defense (blocking `169.254.169.254`).

---

## System Architecture & Monorepo Structure

```
CandidateX/
├── apps/
│   └── web/                         # Next.js 15 App Router Frontend (React 19, Tailwind CSS)
│       ├── src/
│       │   ├── app/                 # Dashboard pages, dossier view, intake flow
│       │   ├── components/          # CapabilityTable, ClaimsMatrix, GraphViewer, ProbesPanel
│       │   └── types/               # Type definitions aligning with backend domain contracts
│       └── Dockerfile               # Multi-stage non-root container build
├── services/
│   └── backend/                     # FastAPI & SQLAlchemy 2.0 Backend Service
│       ├── src/cci/
│       │   ├── domain/              # Frozen Pydantic domain contracts & 41-entity DB models
│       │   ├── scoring/             # Mathematical core (recency, confidence, RCI, bootstrap CI)
│       │   ├── intake/              # CV/JD parsers, hyperlink extractors, URL canonicalizers
│       │   ├── acquisition/         # Safe workspace sandbox, git indexer, GitHub client
│       │   ├── analyzers/           # Static AST parsers (5 langs), SQL/DB, DevOps/Cloud
│       │   ├── security/            # Strict SSRF guard, deployment inspectors
│       │   ├── attribution/         # Heuristic ownership discount, Beta source calibration
│       │   ├── graph/               # Heterogeneous Candidate Evidence Graph (CEG)
│       │   ├── pipeline/            # 10-stage analysis orchestrator & service
│       │   └── api/                 # FastAPI routers (dossier, pipeline, overrides, health)
│       ├── tests/                   # 120 unit, property, security, and paper audit tests
│       └── Dockerfile               # Hardened Python 3.11-slim container build
├── research/
│   ├── run_paper_experiments.py     # Monte Carlo simulation reproduction runner (N=4,800)
│   └── results/                     # Generated publication Markdown & LaTeX tables
├── docs/                            # Formal conference paper interfaces and schemas
├── scripts/
│   └── smoke_test.py                # Operational health & connectivity verification script
├── docker-compose.yml               # Production & integration stack (Postgres 16, Redis 7, Backend, Web)
└── .github/workflows/ci.yml         # GitHub Actions multi-stage CI matrix
```

---

## Formal Mathematical Framework

The CCI evaluation engine implements the exact mathematical formulations defined in the conference paper:

### 1. Bayesian Source Family Reliability Posterior
For each source family $s \in \{\text{Resume}, \text{GitHub}, \text{Deployment}, \text{Database}, \text{Coding}, \text{Certificate}, \text{LinkedIn}\}$:
$$r_s = \frac{TP_s + \alpha_s}{TP_s + FP_s + \alpha_s + \beta_s}, \quad \operatorname{Var}(r_s) = \frac{(\alpha + TP)(\beta + FP)}{(T + \alpha + \beta)^2 (T + \alpha + \beta + 1)}$$

### 2. Temporal Recency Decay
$$t_{e,k} = \exp(-\lambda_k \cdot \Delta t_e)$$
where $\lambda_k$ is the capability-specific half-life decay rate and $\Delta t_e$ is the elapsed time in years.

### 3. Six-Factor Multiplicative Confidence
Each atomic evidence record $e$ supporting capability $k$ receives a confidence weight:
$$c_{e,k} = \left( a_e \cdot o_e \cdot t_{e,k} \cdot v_e \cdot x_e \cdot r_s(e) \right)^{1/6}$$
- $a_e$: Artifact validity and static parser integrity
- $o_e$: Authorship attribution (penalizing forks $\le 0.18$, rewarding solo code $\ge 0.95$)
- $t_{e,k}$: Temporal recency decay
- $v_e$: Direct verification level (e.g. verified commit vs unverified resume)
- $x_e$: Technical specificity and architectural depth
- $r_s(e)$: Bayesian posterior source reliability

### 4. Capability Estimation & Kish Effective Sample Size
$$q_k = \frac{\sum_{e} c_{e,k} \cdot z_{e,k}}{\sum_{e} c_{e,k}}, \quad n_{\text{eff},k} = \frac{\left(\sum_e c_{e,k}\right)^2}{\sum_e c_{e,k}^2}$$
Confidence intervals are estimated via **Cluster Bootstrap Resampling** grouped by source repository to prevent intra-cluster correlation bias.

### 5. Contradiction Diagnostics
$$D_k = \frac{P_k - N_k}{P_k + N_k + \epsilon} \in [-1, 1]$$
Quantifies consensus ($D_k \to 1$) vs. severe contradiction ($D_k \to -1$) between resume claims and observed codebase realities.

### 6. Information-Gain Probe Prioritization
Interview probes are prioritized to maximize uncertainty reduction:
$$I_k = w_k \cdot \sigma_k \cdot (1 + \gamma |D_k|)$$

### 7. Role Capability Index (RCI) & Evidence Coverage
$$RCI(C, J) = \frac{\sum_{k \in \text{observed}} w_k q_k}{\sum_{k \in \text{observed}} w_k}, \quad \text{Coverage}(C, J) = \sum_{k=1}^{12} w_k \cdot \min\left(1.0, \frac{\sum_e c_{e,k}}{\tau_k}\right)$$

---

## Paper Reproducibility & Ablation Studies

The platform includes a research engine replicating the conference paper's Monte Carlo candidate cohort evaluation across **16 deterministic seeds** $\times$ **300 candidates** across the **6 canonical roles** ($N = 4,800$ simulated candidates total).

To reproduce the publication tables:
```bash
python research/run_paper_experiments.py
```
*(Or use `--quick` for a fast verification run across 120 candidates)*.

### Publication Results ($N = 4,800$)

| Evaluation Model | RCI MAE $\downarrow$ | RCI RMSE $\downarrow$ | Spearman's $\rho$ $\uparrow$ | Kendall's $\tau$ $\uparrow$ | Stat. Sig. ($p < 0.001$) |
|:-----------------|:--------------------:|:---------------------:|:----------------------------:|:---------------------------:|:------------------------:|
| **FULL_CCI** | **1.943** | **2.469** | **0.943** | **0.794** | Baseline |
| **NO_RECENCY_DECAY** | 1.975 | 2.505 | 0.943 | 0.794 | Yes ($^{***}$, $p = 2.0 \times 10^{-72}$) |
| **NO_OWNERSHIP_DISCOUNT** | 2.219 | 2.813 | 0.933 | 0.775 | Yes ($^{***}$, $p = 0.0$) |
| **UNIFORM_WEIGHTS** | 3.172 | 3.761 | 0.939 | 0.785 | Yes ($^{***}$, $p = 0.0$) |
| **UNCALIBRATED_SOURCES** | 1.922 | 2.446 | 0.942 | 0.792 | Two-sided $p = 4.1 \times 10^{-29}$ |

Publication artifacts are automatically emitted to:
- [`research/results/table_ablation_study.md`](research/results/table_ablation_study.md)
- [`research/results/table_ablation_study.tex`](research/results/table_ablation_study.tex)
- [`research/results/role_breakdown.md`](research/results/role_breakdown.md)
- [`research/results/ablation_results.json`](research/results/ablation_results.json)

---

## Quickstart & Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+ & pnpm 9+
- Docker & Docker Compose (optional for local containerized run)

### Backend Setup
```bash
cd services/backend
pip install -r requirements.txt
python -m pytest
```

### Frontend Setup
```bash
pnpm install
pnpm --filter web lint
pnpm --filter web build
```

---

## Docker Deployment

The entire stack is configured via `docker-compose.yml` with hardened security settings (`no-new-privileges:true`, dropped capabilities, healthchecks, and non-root users):

```bash
# Spin up PostgreSQL, Redis, FastAPI backend, and Next.js frontend
docker-compose up --build -d

# Verify all services are responsive
python scripts/smoke_test.py
```

- Web Dashboard: `http://localhost:3000`
- FastAPI Documentation: `http://localhost:8000/docs`
- Healthcheck Endpoint: `http://localhost:8000/health`

---

## Verification & Test Matrix

The codebase is covered by **120 tests** verifying all theorems, safety boundaries, and end-to-end pipeline stages:

- **Mathematical Theorems (Theorems 1–10)**: Strict adherence to conference paper proofs in [`test_paper_theorems_audit.py`](services/backend/tests/test_paper_theorems_audit.py).
- **Security & SSRF Defense**: Link-local, loopback, private IP, and IMDS protection in [`test_ssrf_guard.py`](services/backend/tests/security/test_ssrf_guard.py).
- **End-to-End Orchestration**: 10-stage execution pipeline and functional rescore in [`test_pipeline_orchestration.py`](services/backend/tests/test_pipeline_orchestration.py).
- **Research Reproducibility**: Monte Carlo simulation and statistical significance in [`test_run_paper_experiments.py`](services/backend/tests/unit/research/test_run_paper_experiments.py).
