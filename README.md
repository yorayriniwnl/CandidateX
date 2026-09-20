# Candidate Capability Intelligence (CCI)

[![CI Pipeline](https://github.com/yorayriniwnl/CandidateX/actions/workflows/ci.yml/badge.svg)](https://github.com/yorayriniwnl/CandidateX/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: Proprietary / Conference Submission](https://img.shields.io/badge/License-Academic_Conference_Submission-red.svg)](#)

> **CandidateX analyzes real resumes, GitHub profiles and repositories, and supplied public links live.** It extracts PDF/DOCX sections, skills, project claims, education and certificates; inspects commit-pinned source files and public page text; and produces a role-aware dossier with traceable skill matches and explicit verification gaps. Static observations and attribution remain heuristic decision support, not validated hiring accuracy.

**Start here: [Live resume analysis](docs/live-resume-analysis.md)** — supported sources, local setup, hosting, acquisition limits, ownership interpretation, privacy, and verification. The [research demonstration guide](docs/research-demonstration.md) covers synthetic teaching scenarios and experiment boundaries.

Open `/` for the command center. `/analyze` is the live resume and public-source workflow; `/research-demo` is explicitly synthetic; `/workspace` is the earlier evaluation prototype; and `/hr` is a separate sample hiring view. Public portfolios, deployments, coding profiles and credential pages are inspected when accessible. Login restrictions, missing pages and scan limits are visible; certificate authenticity and employment are not automatically verified. See the [comprehensive analysis design](docs/comprehensive-live-analysis.md).

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
3. **Candidate Code is NEVER Executed**: Untrusted candidate repositories are analyzed purely via a Python AST parser and text-pattern analyzers for TypeScript/JavaScript, Go, Java, and C++, dependency manifests, and infrastructure definitions. No test runners, containers, sub-processes, or headless JS browsers are ever launched against candidate code.
4. **Missing Evidence is `UNKNOWN`**: A lack of evidence on a skill drops **Evidence Coverage**, but never assigns an arbitrary zero capability score.
5. **Separation of RCI and Coverage**:
   - **Role Capability Index (RCI)** reflects estimated capability strictly across *observed* technical dimensions.
   - **Evidence Coverage** reflects the fraction of job-critical capabilities backed by sufficient empirical evidence.
6. **Traceable Provenance**: Demonstration observations carry content revisions, source locators, SHA-256 fingerprints, extractor versions, confidence factors, and project clusters. These are synthetic artifacts; database-wide append-only guarantees are not claimed.
7. **Functional Rescoring**: Overrides reuse the current evidence snapshot and update scores, coverage, probes, questions, and graph together. Prior snapshots and justifications remain inspectable in the exported history.
8. **No Live Acquisition in the Demonstration**: Synthetic source locators are never fetched. The live workflow uses its separate DNS-pinned `live/public_links.py` transport for supplied public pages. Legacy deployment-inspection helpers are not used by that acquisition path and do not establish connection-level DNS pinning.

---

## System Architecture & Monorepo Structure

```
CandidateX/
├── apps/
│   └── web/                         # Next.js 16 App Router Frontend (React 19, Tailwind CSS)
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
│       │   ├── analyzers/           # Python AST and polyglot text analyzers, SQL/DB, DevOps/Cloud
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
Measures positive versus negative support balance. Meaningful conflict requires both kinds of evidence; a value near -1 means negative-support dominance, not necessarily conflicting observations.

### 6. Information-Gain Probe Prioritization
Interview probes are prioritized to maximize uncertainty reduction:
$$I_k = w_k [0.40(1-\mathrm{Cov}_k) + 0.35\,\mathrm{CIwidth}_k + 0.25\,\mathrm{Conf}_k]$$
Here interval width is normalized to [0, 1]. An unavailable interval uses a conservative maximal uncertainty term for probe prioritization.

### 7. Role Capability Index (RCI) & Evidence Coverage
$$RCI(C, J) = \frac{\sum_{k \in \text{observed}} w_k q_k}{\sum_{k \in \text{observed}} w_k}, \quad \text{Coverage}(C, J) = \sum_{k=1}^{12} w_k \cdot \min\left(1.0, \frac{\sum_e c_{e,k}}{\tau_k}\right)$$

---

## Paper Reproducibility & Ablation Studies

The public runner is a **separate executable prototype experiment**, as disclosed in manuscript Section 2.6. It uses 16 seeds x six roles x 50 distinct candidates per role, or 4,800 candidates per ablation mode. The manuscript headline study evaluates each candidate against all six roles for 28,800 pairs and reports rho 0.928; original per-seed outputs and exact calibration are unavailable. The repository's rho approximately 0.943 is not a reproduction of that result.

```powershell
& services/backend/.venv/Scripts/python.exe research/run_paper_experiments.py --output-dir reports/research-demo-verification
```

Use `--quick` for a smaller smoke experiment. Neither experiment establishes real-world hiring accuracy.

### Recorded Prototype Results ($N = 4,800$)

| Evaluation Model | RCI MAE $\downarrow$ | RCI RMSE $\downarrow$ | Spearman's $\rho$ $\uparrow$ | Kendall's $\tau$ $\uparrow$ | Stat. Sig. ($p < 0.001$) |
|:-----------------|:--------------------:|:---------------------:|:----------------------------:|:---------------------------:|:------------------------:|
| **FULL_CCI** | **1.943** | **2.469** | **0.943** | **0.794** | Baseline |
| **NO_RECENCY_DECAY** | 1.975 | 2.505 | 0.943 | 0.794 | Yes ($^{***}$, $p = 2.0 \times 10^{-72}$) |
| **NO_OWNERSHIP_DISCOUNT** | 2.219 | 2.813 | 0.933 | 0.775 | Yes ($^{***}$, $p = 0.0$) |
| **UNIFORM_WEIGHTS** | 3.172 | 3.761 | **0.939** | 0.785 | Yes ($^{***}$, $p = 0.0$) |
| **UNCALIBRATED_SOURCES** | 1.922 | 2.446 | 0.942 | 0.792 | Two-sided $p = 4.1 \times 10^{-29}$ |

The committed prototype artifacts are:
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

### 0. One-command setup and verification

From the repository root, the setup script creates `services/backend/.venv`, installs the backend and frontend dependencies, and installs Chromium for browser checks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```

The verification script runs the complete backend suite, Next.js route type generation, TypeScript checks, production build, and browser acceptance suite. Use `-SkipBrowser` during setup only when Chromium is already installed.

### 1. Database Seeding CLI
The earlier workspace has an optional database seeder. It is not needed by the research demonstration. CV/JD declarations alone now yield unknown capability unless observations are supplied:
```powershell
# Seed default SQLite database (local_dev.db) with 7 canonical candidates
& services/backend/.venv/Scripts/python.exe scripts/seed_db.py --samples 7

# Reset existing database and seed a custom PostgreSQL instance
& services/backend/.venv/Scripts/python.exe scripts/seed_db.py --db-url "postgresql://postgres:postgres@localhost:5432/cci" --reset --samples 7
```

### 2. Turnkey Candidate Analysis CLI
The CLI parses supplied declarations and produces a dossier. Automated source acquisition is not wired into this path; without registered observations, technical capability remains unknown. For scored examples use the explicit research demonstration:
```powershell
# Run 10-stage pipeline on sample CV and JD fixtures (automatically infers candidate name)
& services/backend/.venv/Scripts/python.exe scripts/analyze_candidate.py --cv examples/sample_backend_cv.txt --jd examples/sample_backend_jd.txt --role backend

# Demonstrate instantaneous pure functional rescore (< 1ms) with custom capability weights
& services/backend/.venv/Scripts/python.exe scripts/analyze_candidate.py --rescore-weights '{"backend_engineering": 0.40, "database_engineering": 0.30}'
```
Dossier Markdown and JSON reports are generated in `reports/`.

### 3. Canonical Role Fixtures (`examples/`)
The repository includes 5 sample CV and JD pairs for reproducible evaluation:
- **Backend Engineering**: [`examples/sample_backend_cv.txt`](examples/sample_backend_cv.txt) & [`examples/sample_backend_jd.txt`](examples/sample_backend_jd.txt)
- **Frontend Engineering**: [`examples/sample_frontend_cv.txt`](examples/sample_frontend_cv.txt) & [`examples/sample_frontend_jd.txt`](examples/sample_frontend_jd.txt)
- **Machine Learning**: [`examples/sample_ml_cv.txt`](examples/sample_ml_cv.txt) & [`examples/sample_ml_jd.txt`](examples/sample_ml_jd.txt)
- **DevOps & Cloud**: [`examples/sample_devops_cv.txt`](examples/sample_devops_cv.txt) & [`examples/sample_devops_jd.txt`](examples/sample_devops_jd.txt)
- **Fullstack Engineering**: [`examples/sample_fullstack_cv.txt`](examples/sample_fullstack_cv.txt) & [`examples/sample_fullstack_jd.txt`](examples/sample_fullstack_jd.txt)

### 4. Backend Service Setup
```powershell
& services/backend/.venv/Scripts/python.exe -m pytest services/backend/tests
& services/backend/.venv/Scripts/python.exe -m uvicorn cci.main:app --app-dir services/backend/src --reload --port 8000
```

### 5. Web Dashboard Setup
```powershell
pnpm --filter web dev
```
Open `http://localhost:3000/` for the command center, then choose the live workflow or a clearly labeled synthetic/prototype surface. The earlier `/workspace` interface contains:
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
| `POST` | `/api/v1/pipeline/run` | Scores registered observations; declarations alone remain unknown |
| `GET` | `/api/v1/dossier/{id}` | Retrieves generated Technical Dossier for a candidate |
| `GET` | `/api/v1/dossier/{id}/export` | Exports formatted printable brief (`html`, `markdown`, or `json`) |
| `GET` | `/api/v1/dossier/{id}/probes` | Retrieves prioritized interview probes with information-gain scores |
| `POST` | `/api/v1/overrides/recruiter` | Records recruiter capability adjustments with immutable audit trail |

---

## Docker Deployment

The containerized integration stack is provided in `docker-compose.yml`. It runs PostgreSQL 16, Redis 7, FastAPI, and the Next.js production server. The web container uses `CCI_API_URL=http://backend:8000` for service-to-service calls while the browser-facing API URL remains `http://localhost:8000`. The configuration includes security settings (`no-new-privileges:true`, dropped capabilities, healthchecks, and non-root users):

```bash
# Spin up PostgreSQL 16, Redis 7, FastAPI backend, and Next.js frontend
docker compose up --build -d

# Verify all services are responsive
& services/backend/.venv/Scripts/python.exe scripts/smoke_test.py
```

- Web Dashboard: `http://localhost:3000`
- FastAPI Documentation: `http://localhost:8000/docs`
- Healthcheck Endpoint: `http://localhost:8000/health`

---

## Verification & Test Matrix

Use `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1` for the self-contained local release gate, or the more detailed commands in the [demonstration guide](docs/research-demonstration.md#verification). Backend tests use a disposable database and explicit test fixtures. Browser tests exercise the production frontend against a real backend.

- [Demonstration acceptance tests](services/backend/tests/test_research_demonstration.py): evidence integrity, deterministic scenarios, role/JD conditioning, missingness, provenance, consistent rescoring, validation and artifact alignment.
- [Browser workflow tests](apps/web/tests/research-demo.spec.ts): controls through API responses, exports, failure states and mobile layout.
- Existing suites cover mathematical properties, source parsers, database operations, and the separate simulation. Passing these tests does not independently validate real-world hiring accuracy or every production security property.
