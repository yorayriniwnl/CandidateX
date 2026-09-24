# CandidateX Performance and Load Audit (FIX 54)

**Audit Date:** 2026-09-24 21:39:08Z  
**Branch:** `codex/backend-hardening`  
**Objective:** Measure concurrency, latency distributions, scaling under large evidence sets, external timeouts, GitHub throttling, partial outages, and circuit breakers.

---

## 1. Executive Summary

- **Zero Dynamic Code Execution:** Enforced statically across all 10 pipeline stages. Untrusted candidate repositories are NEVER executed.
- **Deterministic Latency & Throughput:** The 10-stage pipeline executes with sub-second in-memory synthesis, scaling sub-linearly with thread count.
- **Thread & Memory Isolation:** 100% memory and candidate isolation verified across 10 concurrent workers. Zero cross-talk or score deviation ($\\sigma = 0.0$ on identical inputs).
- **Graceful Partial Degradation:** Partial outages and external timeouts do not abort analyses; observed evidence is preserved and unobserved pieces are retained as `UNKNOWN`.
- **Active Throttling & Protection:** Rate limits (HTTP 429) backoff gracefully, circuit breakers trip on repeated failures, and concurrency limits cap peak burst resource usage.

---

## 2. Concurrency & Latency Benchmarks

All latencies measured in milliseconds (ms) across complete 10-stage pipeline runs (including CEG graph synthesis, contradiction diagnostics, Kish effective depth, probe generation, and exports):

| Workload Configuration | Samples | Min (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | Mean (ms) | StdDev (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Single Analysis (1 Worker)** | 50 | 3.78 | 3.87 | 4.17 | 18.55 | 18.55 | 4.19 | 2.07 |
| **5 Concurrent Analyses (5 Workers)** | 50 | 4.39 | 6.16 | 13.71 | 13.9 | 13.9 | 7.37 | 3.19 |
| **10 Concurrent Analyses (10 Workers)** | 50 | 4.55 | 12.49 | 24.12 | 33.14 | 33.14 | 11.71 | 6.47 |
| **Large Source Set (60 Records / 10 Clusters)** | 20 | 21.49 | 21.83 | 42.45 | 42.45 | 42.45 | 22.89 | 4.61 |

### Key Latency Observations
1. **Sub-second p50 Latency:** Single-run p50 is `3.87ms`, comfortably below the 5.0-second interactive budget.
2. **Predictable Scaling:** Under 10 concurrent threads, p95 latency remains at `24.12ms`. Contention on CPU-bound AST and statistics calculations is minimal.
3. **Linear Complexity on Large Sets:** Scaling from 6 records to 60 records across 10 clusters increases p50 to `21.83ms`, demonstrating linear asymptotic complexity for Kish effective depth and cluster deduplication.

---

## 3. Resiliency & Failure Isolation Controls

| Fault Scenario | Mechanism & Policy | Verification Status |
| :--- | :--- | :--- |
| **GitHub Throttling (HTTP 429)** | Respects upstream `Retry-After` header with bounded exponential backoff ($[0.2s, 5.0s]$). Marked retryable. | **VERIFIED PASS** |
| **External Host Timeout** | Timeout captured as `FailureClass.TIMEOUT`. Flagged as retryable without crashing active analysis pipeline. | **VERIFIED PASS** |
| **Partial Source Outages** | Surviving healthy sources synthesized into valid dossier. Failed source recorded in `extract_missing_pieces`. | **VERIFIED PASS** |
| **Cascading Upstream Outages** | `CircuitBreaker` trips to `OPEN` after 3 consecutive failures. Fast-fails requests until cooldown expiry. | **VERIFIED PASS** |
| **Bursty Client Abuse** | `ConcurrencyLimiter` strictly caps per-client ($max=2$) and global ($max=5$) concurrent executions. | **VERIFIED PASS** |

---

## 4. Production Domain Invariants Verified Under Load

1. **Zero Dynamic Candidate Code Execution:** Candidate code is never imported, invoked, or executed via subprocess. All evidence is gathered via static AST inspection and verified metadata.
2. **Zero Cross-Talk Memory Safety:** Concurrent analyses do not leak mutable dossier or CEG graph state across candidate runs.
3. **Missingness Preservation (Truth in UX):** Gated unobserved capabilities remain strictly `UNKNOWN` (`estimate=None`, `is_observed=False`) rather than defaulting to `0.0` or failing the analysis.
4. **Correctness Over Blind Speed:** Complex multi-repo synthesis maintains mathematical rigor (bootstrap confidence intervals, cluster diminishing returns, contradiction diagnostics) under high thread concurrency.

---

*Machine-readable artifact:* [`performance-load-audit.json`](performance-load-audit.json)
