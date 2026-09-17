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
│       ├── app/                     # Unified workspace: Directory, Intake, Pipeline, Dossier
│       ├── components/              # CandidateDirectory, JobIntake, CandidateIntake, DossierViewer, CEGViewer
│       ├── lib/                     # API client layer (jobs, candidates, pipeline, dossier)
│       └── Dockerfile               # Multi-stage non-root container build
├── examples/                        # Canonical role evaluation fixtures (CVs and JDs)
│   ├── sample_backend_cv.txt / sample_backend_jd.txt
│   ├── sample_frontend_cv.txt / sample_frontend_jd.txt
│   ├── sample_ml_cv.txt / sample_ml_jd.txt
│   ├── sample_devops_cv.txt / sample_devops_jd.txt
│   └── sample_fullstack_cv.txt / sample_fullstack_jd.txt
├── services/
│   └── backend/                     # FastAPI & SQLAlchemy 2.0 Backend Service
│       ├── src/cci/
│       │   ├── domain/              # Frozen Pydantic domain contracts & 41-entity DB models
│       │   ├── db/                  # Dual-representation repository layer & ImmutableModelMixin
│       │   ├── scoring/             # Mathematical core (recency, confidence, RCI, bootstrap CI)
│       │   ├── intake/              # CV/JD parsers, hyperlink extractors, URL canonicalizers
│       │   ├── acquisition/         # Safe workspace sandbox, git indexer, GitHub client
│       │   ├── analyzers/           # Static AST parsers (5 langs), SQL/DB, DevOps/Cloud
│       │   ├── security/            # Strict SSRF guard, deployment inspectors
│       │   ├── attribution/         # Heuristic ownership discount, Beta source calibration
│       │   ├── graph/               # Heterogeneous Candidate Evidence Graph (CEG)
│       │   ├── pipeline/            # 10-stage analysis orchestrator & service
│       │   └── api/                 # FastAPI routers (dossier, jobs, candidates, overrides, health)
│       ├── tests/                   # 131 unit, golden, property, security, DB, and theorem audit tests
│       └── Dockerfile               # Hardened Python 3.11-slim container build
├── research/
│   ├── run_paper_experiments.py     # Monte Carlo simulation reproduction runner (N=4,800)
│   └── results/                     # Generated publication Markdown & LaTeX tables
├── docs/                            # Formal conference paper interfaces and schemas
├── scripts/
│   ├── analyze_candidate.py         # 10-stage CLI pipeline with auto-name extraction & functional rescore
│   ├── seed_db.py                   # Multi-tenant DB seeder for organizations, roles, and 7 candidate cohorts
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
- Node.js 20+ & pnpm 9+ (or npm)
- Docker & Docker Compose (optional for local containerized run)

### 1. Database Seeding CLI
Seed the SQLite or PostgreSQL database with multi-tenant organizations (`Acme Distributed Systems Corp`, `Apex AI Research Labs`), recruiters, 5 canonical role JDs, and 7 diverse candidate cohorts evaluated through the full 10-stage pipeline:
```bash
# Seed default SQLite database (local_dev.db) with 7 canonical candidates
python scripts/seed_db.py --samples 7

# Reset existing database and seed a custom PostgreSQL instance
python scripts/seed_db.py --db-url "postgresql://postgres:postgres@localhost:5432/cci" --reset --samples 7
```

### 2. Turnkey Candidate Analysis CLI
Analyze arbitrary candidate materials through the full 10-stage pipeline and synthesize a Technical Dossier in seconds:
```bash
# Run 10-stage pipeline on sample CV and JD fixtures (automatically infers candidate name)
python scripts/analyze_candidate.py --cv examples/sample_backend_cv.txt --jd examples/sample_backend_jd.txt --role backend

# Demonstrate instantaneous pure functional rescore (< 1ms) with custom capability weights
python scripts/analyze_candidate.py --rescore-weights '{"backend_engineering": 0.40, "database_engineering": 0.30}'
```
Dossier Markdown and JSON reports are generated in `reports/`.

### 3. Canonical Role Fixtures (`examples/`)
The repository includes 5 production-grade CV and JD pairs for reproducible evaluation:
- **Backend Engineering**: [`examples/sample_backend_cv.txt`](examples/sample_backend_cv.txt) & [`examples/sample_backend_jd.txt`](examples/sample_backend_jd.txt)
- **Frontend Engineering**: [`examples/sample_frontend_cv.txt`](examples/sample_frontend_cv.txt) & [`examples/sample_frontend_jd.txt`](examples/sample_frontend_jd.txt)
- **Machine Learning**: [`examples/sample_ml_cv.txt`](examples/sample_ml_cv.txt) & [`examples/sample_ml_jd.txt`](examples/sample_ml_jd.txt)
- **DevOps & Cloud**: [`examples/sample_devops_cv.txt`](examples/sample_devops_cv.txt) & [`examples/sample_devops_jd.txt`](examples/sample_devops_jd.txt)
- **Fullstack Engineering**: [`examples/sample_fullstack_cv.txt`](examples/sample_fullstack_cv.txt) & [`examples/sample_fullstack_jd.txt`](examples/sample_fullstack_jd.txt)

### 4. Backend Service Setup
```bash
cd services/backend
pip install -e ".[dev]"
python -m pytest
python -m uvicorn cci.main:app --reload --port 8000
```

### 5. Web Dashboard Setup
```bash
cd apps/web
pnpm install
pnpm dev
```
Open `http://localhost:3000` to access the interactive recruitment platform:
- **Candidate Directory**: Real-time search, role filtering, evidence status badges (`Robust`, `Sparse`, `Conflict Flagged`), and 1-click dossier navigation.
- **Job Intake Form**: Role template presets with live backend requirement extraction (`POST /api/v1/jobs/parse`).
- **Candidate Intake Form**: 1-click preset selector for the 7 canonical candidate cohorts mapped to seeded database UUIDs.
- **Dossier & CEG Viewer**: Comprehensive capability breakdown, confidence factors, claims matrix, interview probes, and interactive graph viewer.
- **Export & Print**: 1-click "Export Brief" generating standalone printable HTML documents (optimized `@media print`), downloadable Markdown, or raw JSON snapshots.
- **Multi-Candidate Comparison**: Side-by-side comparative capability matrix comparing up to 3 candidates simultaneously across RCI, Coverage, 12 Core Capabilities, and contradiction alerts.

---

## REST API Specification

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/health` / `/healthz` | System health and service availability check |
| `POST` | `/api/v1/jobs/parse` | Parses raw JD text into normalized requirements and softmax role weights $w_k$ |
| `GET` | `/api/v1/jobs` | Lists active job descriptions from the database |
| `GET` | `/api/v1/candidates` | Lists all candidates with RCI, Coverage, and conflict indicators |
| `GET` | `/api/v1/candidates/{id}` | Retrieves full candidate manifest data and intake records |
| `POST` | `/api/v1/pipeline/analyze` | Executes 10-stage evaluation pipeline against submitted CV and JD |
| `GET` | `/api/v1/dossier/{id}` | Retrieves generated Technical Dossier for a candidate |
| `GET` | `/api/v1/dossier/{id}/export` | Exports formatted printable brief (`html`, `markdown`, or `json`) |
| `GET` | `/api/v1/dossier/{id}/probes` | Retrieves prioritized interview probes with information-gain scores |
| `POST` | `/api/v1/overrides/recruiter` | Records recruiter capability adjustments with immutable audit trail |

---

## Docker Deployment

The entire stack is configured via `docker-compose.yml` with hardened security settings (`no-new-privileges:true`, dropped capabilities, healthchecks, and non-root users):

```bash
# Spin up PostgreSQL 16, Redis 7, FastAPI backend, and Next.js frontend
docker-compose up --build -d

# Verify all services are responsive
python scripts/smoke_test.py
```

- Web Dashboard: `http://localhost:3000`
- FastAPI Documentation: `http://localhost:8000/docs`
- Healthcheck Endpoint: `http://localhost:8000/health`

---

## Verification & Test Matrix

The test suite contains **134 passed tests** verifying all theorems, database persistence invariants, and end-to-end pipeline stages:

- **Mathematical Theorems (Theorems 1–10)**: Strict adherence to conference paper proofs in [`test_paper_theorems_audit.py`](services/backend/tests/test_paper_theorems_audit.py).
- **Security & SSRF Defense**: Link-local, loopback, RFC 1918 private IP, and IMDS protection in [`test_ssrf.py`](services/backend/tests/security/test_ssrf.py) and [`test_safe_workspace.py`](services/backend/tests/security/repositories/test_safe_workspace.py).
- **Database Repository & Invariants**: ORM persistence, dual-representation conversions, and evidence immutability checks in [`test_db_seeding.py`](services/backend/tests/integration/test_db_seeding.py) and [`test_db_migration.py`](services/backend/tests/integration/test_db_migration.py).
- **Static Multi-Language AST Parsers**: Deterministic code intelligence across Python, TypeScript/JavaScript, Go, Java, and C++ in [`test_code_analyzers.py`](services/backend/tests/golden/code_intel/test_code_analyzers.py).
- **Database & DevOps Infrastructure**: Schema, migration, Docker, and CI/CD parsing in [`test_db_test_infra_analyzers.py`](services/backend/tests/golden/db_infra_golden/test_db_test_infra_analyzers.py).
- **Job & Candidate APIs**: Endpoint contracts, request validation, and database fallbacks in [`test_jobs_and_candidates_api.py`](services/backend/tests/unit/api/test_jobs_and_candidates_api.py).
- **End-to-End Orchestration**: 10-stage execution pipeline and functional rescore in [`test_pipeline_orchestration.py`](services/backend/tests/test_pipeline_orchestration.py).
- **Research Reproducibility**: Monte Carlo simulation and statistical significance in [`test_run_paper_experiments.py`](services/backend/tests/unit/research/test_run_paper_experiments.py).
