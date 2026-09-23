# Candidate Capability Intelligence (CCI)

[![CI Pipeline](https://github.com/yorayriniwnl/CandidateX/actions/workflows/ci.yml/badge.svg)](https://github.com/yorayriniwnl/CandidateX/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: Proprietary / Conference Submission](https://img.shields.io/badge/License-Academic_Conference_Submission-red.svg)](#)

> **CandidateX analyzes real resumes, GitHub profiles and repositories, and supplied public links live.** It extracts PDF/DOCX sections, skills, project claims, education and certificates; inspects commit-pinned source files and public page text; and produces a role-aware dossier with traceable skill matches and explicit verification gaps. Static observations and attribution remain heuristic decision support, not validated hiring accuracy.

**Start here: [Live resume analysis](docs/live-resume-analysis.md)** — supported sources, local setup, hosting, acquisition limits, ownership interpretation, privacy, and verification. The [research demonstration guide](docs/research-demonstration.md) covers synthetic teaching scenarios and experiment boundaries.

Open `/analyze` (also the default `/` route). `/research-demo` is explicitly synthetic. The earlier interface is available at `/workspace`; `/hr` remains a separate sample interface. Public portfolios, deployments, coding profiles and credential pages are inspected when accessible. Login restrictions, missing pages and scan limits are visible; certificate authenticity and employment are not automatically verified. See the [comprehensive analysis design](docs/comprehensive-live-analysis.md).

---

## Table of Contents

1. [Core Product Invariants](#core-product-invariants)
2. [System Architecture & Monorepo Structure](#system-architecture--monorepo-structure)
3. [Formal Mathematical Framework](#formal-mathematical-framework)
4. [Research Experiments & Ablation Studies](#research-experiments--ablation-studies)
5. [Quickstart & Local Development](#quickstart--local-development)
6. [Docker Deployment](#docker-deployment)
7. [Verification & Test Matrix](#verification--test-matrix)

---

## Core Product Invariants

CCI is designed under strict ethical, mathematical, and operational constraints:

1. **Employer Decision Support Only**: CCI assists human interviewers and hiring managers with structured evidence, diagnostics, and probe questions; it **never** makes autonomous hire/reject decisions.
2. **Closed-World CV Candidate Manifest**: Analysis is strictly constrained to resources explicitly supplied by the candidate (e.g. CV, linked GitHub, portfolio links). No unconstrained scraping or unsupplied identity discovery.
3. **Candidate Code is NEVER Executed**: Untrusted candidate repositories are analyzed purely via a Python AST parser and text-pattern analyzers for TypeScript/JavaScript, Go, Java, and C++, dependency manifests, and infrastructure definitions. No test runners, containers, sub-processes, or headless JS browsers are ever launched against candidate code.
4. **Missing or weakly attributed evidence is `UNKNOWN`**: A lack of sufficient candidate attribution drops **Evidence Coverage** and withholds the estimate; it never assigns an arbitrary zero capability score.
5. **Separation of RCI and Coverage**:
   - **Role Capability Index (RCI)** reflects estimates only for technical dimensions that meet the configured attribution-gated evidence threshold.
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

### 3. Attribution-Gated Evidence Weight
Each atomic evidence record $e$ supporting capability $k$ combines five evidence-quality factors and a direct attribution gate:
$$q_{e,k} = \left( a_e \cdot t_{e,k} \cdot v_e \cdot x_e \cdot r_s(e) \right)^{1/5}, \qquad c_{e,k} = o_e \cdot q_{e,k}$$
- $a_e$: Artifact validity and static parser integrity
- $o_e$: Path-specific account contribution ratio used as a direct gate, not a calibrated probability
- $t_{e,k}$: Temporal recency decay
- $v_e$: Direct verification level (e.g. verified commit vs unverified resume)
- $x_e$: Technical specificity and architectural depth
- $r_s(e)$: Bayesian posterior source reliability

Because $q_{e,k} \in [0, 1]$, the weight satisfies $c_{e,k} \le o_e$. With five quality factors at $0.75$ and attribution at $0.03$, the former sixth-root formula yields $0.4386$, while the gated rule yields $0.0225$. No hard cutoff is used because no empirically validated threshold exists.

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
For each source cluster $g$, unique artifacts contribute their strongest attribution-gated quality $q_{g,j}$ once, sorted from strongest to weakest. Further artifacts in the same cluster receive geometrically diminishing weight $\delta^{j-1}$:
$$M_{g,k} = \sum_{j=1}^{n_g} q_{g,j}\,\delta^{j-1}, \quad \mathrm{Cov}_k = \min\left(1, \frac{\sum_g M_{g,k}}{\tau_k}\right), \quad \delta=0.5$$
Clusters use source family plus normalized cluster ID (or source locator). Content-identical artifacts across repositories are credited once. Overall role coverage remains $\text{Coverage}(C, J) = \sum_{k=1}^{12} w_k \cdot \mathrm{Cov}_k$, and RCI uses only capabilities meeting the 0.35 default minimum.

---

## Research Experiments & Ablation Studies

The public runner is a **separate synthetic prototype experiment**, as disclosed in manuscript Section 2.6. It uses 16 seeds x six roles x 50 distinct candidates per role, or 4,800 candidates per ablation mode. Scoring config 5.0.0 uses source-cluster coverage, 0.5 within-cluster artifact decay, 0.5 evidence-family decay, and requires candidate attribution-gated coverage of at least 0.35. Repeated observations of one family and type are retained but only the strongest contributes; distinct observation types receive geometric decay. The manuscript headline study evaluates each candidate against all six roles for 28,800 pairs and reports rho 0.928; original per-seed outputs and exact calibration are unavailable. The repository's rho is not a reproduction of that result.

```powershell
python research/run_paper_experiments.py --output-dir reports/research-demo-verification
```

Use `--quick` for a smaller smoke experiment. Neither experiment establishes real-world hiring accuracy.

### Recorded Prototype Results ($N = 4,800$)

| Evaluation Model | Paired N | RCI MAE $\downarrow$ | RCI RMSE $\downarrow$ | Spearman's $\rho$ $\uparrow$ | Kendall's $\tau$ $\uparrow$ | Stat. Sig. ($p < 0.001$) |
|:-----------------|:--------:|:--------------------:|:---------------------:|:----------------------------:|:---------------------------:|:------------------------:|
| **FULL_CCI** | 4,796 | **1.267** | **1.643** | **0.977** | **0.872** | Baseline |
| **NO_RECENCY_DECAY** | 4,796 | 1.255 | 1.626 | 0.976 | 0.868 | p = 0.4733 |
| **NO_OWNERSHIP_DISCOUNT** | 4,796 | 2.332 | 2.996 | 0.934 | 0.780 | Yes ($^{***}$) |
| **UNIFORM_WEIGHTS** | 4,796 | 1.921 | 2.455 | 0.960 | 0.831 | Yes ($^{***}$) |
| **UNCALIBRATED_SOURCES** | 4,796 | 1.335 | 1.734 | 0.975 | 0.867 | Yes ($^{***}$) |

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

### 1. Database Seeding CLI
The earlier workspace has an optional database seeder. It is not needed by the research demonstration. CV/JD declarations alone now yield unknown capability unless observations are supplied:
```bash
# Seed default SQLite database (local_dev.db) with 7 canonical candidates
python scripts/seed_db.py --samples 7

# Reset existing database and seed a custom PostgreSQL instance
python scripts/seed_db.py --db-url "postgresql://postgres:postgres@localhost:5432/cci" --reset --samples 7
```

### 2. Turnkey Candidate Analysis CLI
The CLI parses supplied declarations and produces a dossier. Automated source acquisition is not wired into this path; without registered observations, technical capability remains unknown. For scored examples use the explicit research demonstration:
```bash
# Run 10-stage pipeline on sample CV and JD fixtures (automatically infers candidate name)
python scripts/analyze_candidate.py --cv examples/sample_backend_cv.txt --jd examples/sample_backend_jd.txt --role backend

# Demonstrate instantaneous pure functional rescore (< 1ms) with custom capability weights
python scripts/analyze_candidate.py --rescore-weights '{"backend_engineering": 0.40, "database_engineering": 0.30}'
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
Open `http://localhost:3000` for the paper demonstration. The earlier `/workspace` interface contains:
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

Legacy container configuration is provided in `docker-compose.yml`; it is not the verified research-demo startup path. Database drivers, migrations, service routing, and worker state require validation before deployment. The configuration includes security settings (`no-new-privileges:true`, dropped capabilities, healthchecks, and non-root users):

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

Use the self-contained verification commands in the [demonstration guide](docs/research-demonstration.md#verification). Backend tests use a disposable database and explicit test fixtures. Browser tests exercise the production frontend against a real backend.

- [Demonstration acceptance tests](services/backend/tests/test_research_demonstration.py): evidence integrity, deterministic scenarios, role/JD conditioning, missingness, provenance, consistent rescoring, validation and artifact alignment.
- [Browser workflow tests](apps/web/tests/research-demo.spec.ts): controls through API responses, exports, failure states and mobile layout.
- Existing suites cover mathematical properties, source parsers, database operations, and the separate simulation. Passing these tests does not independently validate real-world hiring accuracy or every production security property.
