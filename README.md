# Candidate Capability Intelligence (CCI)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Research prototype](https://img.shields.io/badge/status-research_prototype-indigo.svg)](#research-and-validation-boundary)

**Candidate Capability Intelligence (CCI)** is an employer-facing, human-in-the-loop technical assessment prototype. It turns candidate-authorized technical evidence into a provenance-preserving Candidate Evidence Graph, role-conditioned capability estimates, Evidence Coverage, contradiction diagnostics, and evidence-linked interview probes.

**Live demo:** https://candidatex-smoky.vercel.app  
**Portfolio case study:** https://yorayriniwnl.in/projects/candidatex

> CCI is decision support for technical interviewers. It does **not** autonomously hire or reject candidates, and missing public evidence is treated as uncertainty / lower coverage rather than incapability.

---

## Why CandidateX exists

Software-engineering capability leaves evidence across repositories, deployments, database artifacts, credentials, professional profiles, resumes, and coding platforms. Traditional screening often compresses that evidence into resume keywords or one opaque score.

CCI instead asks four questions:

1. **What technical capability is supported?**
2. **Which concrete evidence supports it?**
3. **How strong, attributable, current, and complete is that evidence?**
4. **What should a human interviewer verify next?**

The system is designed around auditability rather than automated employment decisions.

---

## Core invariants

1. **Human decision support only**. No autonomous hire / reject output.
2. **Closed-world evidence boundary**. Analysis is restricted to candidate-supplied or explicitly authorized professional artifacts.
3. **No untrusted candidate-code execution**. Candidate repositories are inspected statically.
4. **Missing evidence is UNKNOWN**. Absence lowers Evidence Coverage; it is not silently mapped to zero capability.
5. **Capability and coverage are separate outputs**. RCI summarizes observed capability while Coverage communicates evidence sufficiency.
6. **Provenance is first-class**. Evidence retains source, revision, timestamp, ownership, verification, extractor version, and fingerprint information.
7. **Role-aware interpretation**. The same candidate can be interpreted differently for Backend, Frontend, Full-stack, ML Engineer, DevOps, and Data Engineer roles.
8. **Contradictions are preserved**. Conflicting evidence becomes an interviewer verification signal rather than an automatic rejection.

---

## System architecture

```text
Candidate / Job Intake
        |
        v
Authorized Evidence Sources
        |
        v
Source-specific static analyzers + verifiers
        |
        v
Candidate Evidence Graph (CEG)
        |
        v
Role-aware evidence fusion
        |
        +--> Capability estimates + confidence intervals
        +--> Evidence Coverage
        +--> Contradiction diagnostics
        +--> Evidence-linked interview probes
        |
        v
Human interviewer dossier
```

### Monorepo

```text
CandidateX/
├── apps/web/                         # Next.js recruiter workspace
├── services/backend/                 # FastAPI + SQLAlchemy backend
│   └── src/cci/
│       ├── acquisition/              # bounded evidence acquisition
│       ├── analyzers/                # static code / DB / infra / deployment analysis
│       ├── attribution/              # ownership + reliability
│       ├── graph/                    # Candidate Evidence Graph
│       ├── scoring/                  # confidence, capability, coverage, RCI
│       ├── contradictions/           # conflict diagnostics
│       ├── probes/                   # interview-probe prioritization
│       ├── pipeline/                 # staged analysis orchestration
│       └── api/                      # FastAPI routers
├── research/                         # benchmark provenance + supplementary ablation harness
├── examples/                         # reproducible candidate/JD fixtures
├── scripts/                          # CLI analysis, seed, and audit tools
└── .github/workflows/ci.yml          # backend/frontend/security verification workflow
```

---

## Formal CCI model

The repository implementation follows the submitted paper's scoring equations.

### 1. Bayesian source reliability

For source family `s`:

```text
r_s = (TP_s + alpha_s) / (TP_s + FP_s + alpha_s + beta_s)
```

### 2. Capability-dependent recency

```text
t_e,k = exp(-lambda_k * Delta t_e)
```

### 3. Six-factor evidence confidence

```text
c_e,k = (a_e * o_e * t_e,k * v_e * x_e * r_s(e))^(1/6)
```

where the factors represent artifact authenticity / integrity, contributor ownership, recency, verification, extractor confidence / technical specificity, and calibrated source reliability.

### 4. Capability estimate

```text
q_k = sum(c_e,k * z_e,k) / sum(c_e,k)
```

When no usable evidence exists for capability `k`, `q_k` is UNKNOWN rather than zero.

### 5. Effective evidence count

```text
n_eff,k = (sum c_e,k)^2 / sum(c_e,k^2)
```

### 6. Contradiction diagnostic

```text
D_k = (P_k - N_k) / (P_k + N_k + epsilon)
```

### 7. Role-conditioned weighting

```text
w_k(J) = exp(u_k / T) / sum_j exp(u_j / T)
```

### 8. Evidence Coverage

```text
Coverage(C,J) = sum_k w_k(J) * min(1, sum_e c_e,k / tau_k)
```

### 9. Role Capability Index

```text
RCI(C,J) = 100 * [sum_(k in O_C) w_k(J) q_k] / [sum_(k in O_C) w_k(J)]
```

### 10. Interview-probe priority, paper Eq. (11)

```text
I_k = w_k(J) * [alpha * (1 - Cov_k) + beta * CIwidth_k + gamma * Conf_k]
```

The implementation in `services/backend/src/cci/probes/priority.py` uses this structure so interviewer attention is directed toward role-important capability gaps, uncertainty, and contradictions.

---

## Canonical roles and evidence families

### Six target roles

- Backend
- Frontend
- Full-stack
- ML Engineer
- DevOps / Cloud
- Data Engineer

### Seven paper evidence families

- Resume
- GitHub
- Deployment / website
- Database artifacts
- Coding platforms
- Certificates
- LinkedIn / professional-profile claims

Not every current connector has identical runtime depth; the research paper and the implementation intentionally preserve source-family provenance so unavailable sources can be represented explicitly rather than fabricated.

---

## Research and validation boundary

There are **two separate evidence layers** in this repository. They must not be conflated.

### A. Submitted-paper controlled synthetic benchmark

The submitted paper reports:

- **16 random seeds**
- **300 synthetic candidates per seed**
- **6 target roles**
- **12 capability dimensions**
- **7 evidence families**
- **28,800 candidate-role evaluations**

Primary paper-reported results:

| Metric | Paper-reported result |
|---|---:|
| Spearman `rho` | **0.928 ± 0.013** |
| Kendall `tau` | **0.774 ± 0.019** |
| nDCG@20 | **0.970 ± 0.011** |
| Role-agnostic fusion Spearman `rho` | **0.849** |
| 60% source-dropout Spearman `rho` | **0.716** |
| Candidate-shuffle control Spearman `rho` | **-0.006 ± 0.057** |

The paper also reports **40 randomized generator regimes** comprising **288,000 additional evaluations**, with mean regime-level Spearman `rho = 0.919 ± 0.010`.

These are **synthetic mechanism-validation results, not real-world hiring accuracy**. The paper explicitly requires external validation with consented candidates and blinded interviewers before any real hiring-validity claim.

Machine-readable provenance is stored in:

```text
research/paper_benchmark_manifest.json
```

### B. Repository supplementary implementation ablation

`research/run_paper_experiments.py` is a **supplementary implementation ablation harness**. At its default settings it evaluates:

```text
16 seeds x 6 role-specific cohorts x 50 samples = 4,800 candidate-role samples
```

It is **not an exact regeneration of the paper benchmark**. It uses the current repository simulator to exercise implementation behavior under recency, ownership, role-weight, and source-calibration ablations.

The existing `research/results/ablation_results.json` values therefore remain valid as repository implementation diagnostics, but they are not relabeled as the paper's headline 28,800-evaluation results.

This separation is deliberate: publication provenance is stronger than forcing two different experimental designs into one number.

---

## Recruiter workflow

The web application exposes:

- Candidate directory
- Candidate intake
- Job / role intake
- Multi-stage analysis progress
- Candidate technical dossier
- Candidate Evidence Graph
- RCI and Evidence Coverage
- Contradiction diagnostics
- Evidence-linked interview probes
- Candidate comparison
- Methodology & math explorer
- Dossier export / print flows

When a live backend is unavailable, the public UI may fall back to controlled demonstration data. Demo-mode status should be treated as a product demonstration, not evidence that a real candidate was analyzed live.

---

## Backend API surface

Representative endpoints include:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | service health |
| `POST` | `/api/v1/jobs/parse` | parse job requirements / role profile |
| `GET` | `/api/v1/candidates` | candidate directory |
| `POST` | `/api/v1/pipeline/run` | run staged analysis |
| `GET` | `/api/v1/pipeline/status/{run_id}` | pipeline status |
| `GET` | `/api/v1/dossier/{candidate_id}` | technical dossier |
| `GET` | `/api/v1/dossier/{candidate_id}/graph` | Candidate Evidence Graph |
| `POST` | `/api/v1/pipeline/rescore` | functional role-weight rescore |
| `GET` | `/api/v1/research/theorems` | formal methodology catalog |
| `GET` | `/api/v1/research/ablation-study` | supplementary implementation ablation |

---

## Quickstart

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

### Seed controlled demo candidates

```bash
python scripts/seed_db.py --samples 7
```

### Run one candidate through the CLI

```bash
python scripts/analyze_candidate.py \
  --cv examples/sample_backend_cv.txt \
  --jd examples/sample_backend_jd.txt \
  --role backend
```

### Run the supplementary implementation ablation

```bash
python research/run_paper_experiments.py
```

Fast sanity run:

```bash
python research/run_paper_experiments.py --quick
```

---

## Verification

The repository includes tests for scoring mathematics, paper invariants, SSRF / safe-workspace behavior, database seeding, research utilities, pipeline behavior, and frontend build/type checks.

The paper-alignment regression contract lives at:

```text
services/backend/tests/test_paper_alignment_contract.py
```

It protects the project against three easy-to-miss regressions:

1. stale probe-priority equations appearing in UI/docs,
2. a non-paper role such as Mobile replacing Data Engineer in research defaults,
3. the 4,800-sample implementation harness being mislabeled as the paper's 28,800-evaluation benchmark.

### CI note

The GitHub Actions workflow is configured in `.github/workflows/ci.yml`. If GitHub reports jobs with **zero steps and `runner_id = 0`**, the job never reached a runner, so that event is an Actions account/runner-availability failure rather than a test failure. Do not interpret such a run as evidence that the backend or frontend tests executed.

---

## Security and governance

- Static analysis only for untrusted candidate repositories
- SSRF / private-network / cloud-metadata protections for bounded deployment inspection
- Source allowlists and explicit source states
- Immutable / auditable evidence lineage
- Correction / appeal design for mistaken identity or attribution
- Sensitive / protected attributes excluded from technical scoring
- Candidate notice, consent, retention, and external fairness validation required before serious hiring use

---

## Limitations

CandidateX is a research prototype. Public technical artifacts reveal only part of a person's capability. Private work, NDAs, team context, unequal access to public platforms, accessibility needs, and many other factors affect observability.

A strong-looking dossier is therefore not a hiring verdict. A low-coverage dossier is not evidence of low capability. The intended endpoint is a transparent technical brief that helps a human interviewer spend limited interview time on the most important unresolved technical questions.

---

## Authors / research context

**Ayush Roy · Archi Srivastava**  
School of Computer Engineering, KIIT Deemed to be University, Bhubaneswar, Odisha, India

Associated paper: **Role-Aware Candidate Capability Intelligence for Pre-Interview Technical Assessment Using Multi-Source Evidence Fusion**.
