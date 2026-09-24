"""Performance, Concurrency, and Load Audit Suite (FIX 54).

Verifies system behavior under concurrent load (1, 5, 10 workers), large source sets,
external timeouts, GitHub rate-limiting/throttling (HTTP 429), partial outages,
and circuit breaker tripping/cooldown.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import time
from uuid import UUID, uuid4

import pytest

from cci.domain.contracts import (
    CanonicalRole,
    CapabilityKey,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    SourceFamily,
)
from cci.live.resilience import (
    FailureClass,
    classify_http_failure,
    extract_missing_pieces,
    is_retryable_status,
)
from cci.pipeline.orchestrator import PipelineStatus, execute_analysis_pipeline
from cci.security.abuse import CircuitBreaker, CircuitBreakerRegistry, CircuitState, ConcurrencyLimiter


def _make_perf_record(
    cap: CapabilityKey,
    signal: float,
    family: SourceFamily = SourceFamily.GITHUB,
    cluster_id: str = "cluster-perf-1",
    path: str = "src/core.py",
    ownership: float = 0.95,
    recency: float = 0.95,
    depth: float = 0.90,
) -> EvidenceRecord:
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=ownership,
        recency_factor=recency,
        verification_level=1.0,
        depth_specificity=depth,
        source_reliability=0.90,
    )
    commit_sha = "abc123def4567890123456789012345678901234"
    chash = hashlib.sha256(f"{path}:{commit_sha}:{signal}".encode()).hexdigest()
    return EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint=f"fp-{uuid4()}",
        source_family=family,
        source_locator=f"https://github.com/candidate-perf/{cluster_id}",
        immutable_revision=commit_sha,
        target_capability=cap,
        technical_signal_strength=signal,
        is_positive_support=True,
        confidence_factors=factors,
        confidence=factors.composite_confidence,
        cluster_id=cluster_id,
        created_at=datetime.now(timezone.utc),
        provenance={
            "path": path,
            "artifact_path": path,
            "commit_sha": commit_sha,
            "content_hash": chash,
            "content_sha256": chash,
            "artifact_sha256": chash,
            "fetch_timestamp": "2026-09-24T12:00:00Z",
        },
    )


def _build_standard_workload(candidate_id: UUID) -> list[EvidenceRecord]:
    """Builds a representative workload across 4 clusters and 4 capabilities."""
    records = []
    # Cluster 1: Backend service
    records.append(_make_perf_record(CapabilityKey.BACKEND_ENGINEERING, 88.0, cluster_id="cluster-repo-1", path="api/server.py"))
    records.append(_make_perf_record(CapabilityKey.BACKEND_ENGINEERING, 85.0, cluster_id="cluster-repo-1", path="api/routes.py"))
    # Cluster 2: Database layer
    records.append(_make_perf_record(CapabilityKey.DATABASE_ENGINEERING, 82.0, family=SourceFamily.DATABASE, cluster_id="cluster-repo-1", path="db/schema.sql"))
    # Cluster 3: Architecture in separate repo
    records.append(_make_perf_record(CapabilityKey.BACKEND_ENGINEERING, 84.0, cluster_id="cluster-repo-2", path="service/core.py"))
    records.append(_make_perf_record(CapabilityKey.SOFTWARE_ARCHITECTURE, 78.0, cluster_id="cluster-repo-2", path="service/bus.py"))
    # Cluster 4: Deployment
    records.append(_make_perf_record(CapabilityKey.DEVOPS_CLOUD, 80.0, family=SourceFamily.DEPLOYMENT, cluster_id="cluster-deploy", path="/health"))
    return records


# ---------------------------------------------------------------------------
# 1. Baseline Performance Test
# ---------------------------------------------------------------------------

def test_single_analysis_baseline_latency():
    """Verify single analysis execution meets latency requirements and completes all stages."""
    cid = uuid4()
    rid = uuid4()
    records = _build_standard_workload(cid)

    start = time.perf_counter()
    result = execute_analysis_pipeline(
        candidate_id=cid,
        analysis_run_id=rid,
        role=CanonicalRole.BACKEND,
        custom_evidence=records,
        evidence_mode="provided",
    )
    elapsed = time.perf_counter() - start

    assert result.status == PipelineStatus.COMPLETED
    assert result.error is None
    assert len(result.stages) == 10
    assert result.dossier is not None
    assert result.ceg_graph is not None
    # Must complete comfortably under 5 seconds (typically ~0.05 - 0.2s for in-memory synthesis)
    assert elapsed < 5.0, f"Single analysis took {elapsed:.2f}s, expected < 5.0s"


# ---------------------------------------------------------------------------
# 2. Concurrency Load Test: 5 Workers
# ---------------------------------------------------------------------------

def test_concurrent_analyses_5_workers():
    """Verify concurrent execution of 5 analyses with full memory and dossier isolation."""
    num_concurrent = 5
    workloads = [(uuid4(), uuid4()) for _ in range(num_concurrent)]

    def run_one(cid: UUID, rid: UUID) -> tuple[UUID, float, bool]:
        records = _build_standard_workload(cid)
        t0 = time.perf_counter()
        res = execute_analysis_pipeline(
            candidate_id=cid,
            analysis_run_id=rid,
            role=CanonicalRole.BACKEND,
            custom_evidence=records,
            evidence_mode="provided",
        )
        duration = time.perf_counter() - t0
        success = (
            res.status == PipelineStatus.COMPLETED
            and res.dossier is not None
            and res.dossier.candidate_id == cid
            and res.dossier.analysis_run_id == rid
        )
        return cid, duration, success

    start = time.perf_counter()
    durations: list[float] = []
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(run_one, cid, rid) for cid, rid in workloads]
        for f in as_completed(futures):
            cid, dur, success = f.result()
            assert success is True, f"Analysis for candidate {cid} failed under 5-worker concurrency"
            durations.append(dur)
    wall_clock = time.perf_counter() - start

    assert len(durations) == num_concurrent
    durations.sort()
    p50 = durations[len(durations) // 2]
    p95 = durations[int(len(durations) * 0.95)]
    assert wall_clock < 10.0
    assert p50 < 3.0
    assert p95 < 5.0


# ---------------------------------------------------------------------------
# 3. Concurrency Load Test: 10 Workers
# ---------------------------------------------------------------------------

def test_concurrent_analyses_10_workers():
    """Verify concurrent execution of 10 analyses without thread contention or score drift."""
    num_concurrent = 10
    workloads = [(uuid4(), uuid4()) for _ in range(num_concurrent)]

    def run_one(cid: UUID, rid: UUID):
        records = _build_standard_workload(cid)
        t0 = time.perf_counter()
        res = execute_analysis_pipeline(
            candidate_id=cid,
            analysis_run_id=rid,
            role=CanonicalRole.BACKEND,
            custom_evidence=records,
            evidence_mode="provided",
        )
        dur = time.perf_counter() - t0
        return cid, dur, res

    results = []
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(run_one, cid, rid) for cid, rid in workloads]
        for f in as_completed(futures):
            results.append(f.result())

    assert len(results) == num_concurrent
    backend_estimates: list[float] = []
    durations: list[float] = []

    for cid, dur, res in results:
        assert res.status == PipelineStatus.COMPLETED
        assert res.dossier is not None
        assert res.dossier.candidate_id == cid
        backend_est = res.dossier.capability_estimates.get(CapabilityKey.BACKEND_ENGINEERING)
        assert backend_est is not None
        assert backend_est.is_observed is True
        backend_estimates.append(backend_est.estimate)
        durations.append(dur)

    # Invariant: deterministic calculation across concurrent threads (all identical inputs produce identical scores)
    first_score = backend_estimates[0]
    for sc in backend_estimates:
        assert abs(sc - first_score) < 1e-6, "Concurrent execution produced non-deterministic scores"


# ---------------------------------------------------------------------------
# 4. Large Source Set Stress Test (60 Evidence Records across 10 Clusters)
# ---------------------------------------------------------------------------

def test_large_source_set_performance():
    """Verify pipeline efficiency under a larger source set with 60 evidence records across 10 clusters."""
    cid = uuid4()
    rid = uuid4()

    large_records: list[EvidenceRecord] = []
    capabilities = [
        CapabilityKey.BACKEND_ENGINEERING,
        CapabilityKey.DATABASE_ENGINEERING,
        CapabilityKey.SOFTWARE_ARCHITECTURE,
        CapabilityKey.DEVOPS_CLOUD,
        CapabilityKey.SECURITY,
        CapabilityKey.TESTING_QUALITY,
    ]

    for cluster_idx in range(10):
        c_id = f"large-cluster-{cluster_idx}"
        for cap_idx, cap in enumerate(capabilities):
            large_records.append(
                _make_perf_record(
                    cap=cap,
                    signal=75.0 + (cluster_idx % 20),
                    family=SourceFamily.GITHUB if cluster_idx < 8 else SourceFamily.DEPLOYMENT,
                    cluster_id=c_id,
                    path=f"module_{cluster_idx}/cap_{cap_idx}.py",
                    ownership=0.90,
                    recency=0.90,
                    depth=0.85,
                )
            )

    assert len(large_records) == 60

    t0 = time.perf_counter()
    res = execute_analysis_pipeline(
        candidate_id=cid,
        analysis_run_id=rid,
        role=CanonicalRole.BACKEND,
        custom_evidence=large_records,
        evidence_mode="provided",
    )
    duration = time.perf_counter() - t0

    assert res.status == PipelineStatus.COMPLETED
    assert res.dossier is not None
    assert len(res.dossier.evidence_records) == 60

    # Cluster aware coverage and Kish counts should scale without quadratic slowdown
    assert duration < 5.0, f"Large source set took {duration:.2f}s, expected < 5.0s"
    distinct_clusters = {e.cluster_id for e in res.dossier.evidence_records}
    assert len(distinct_clusters) == 10


# ---------------------------------------------------------------------------
# 5. GitHub Throttling & Rate Limit Resilience (HTTP 429)
# ---------------------------------------------------------------------------

def test_github_throttling_resilience():
    """Verify HTTP 429 rate-limiting classification, retryability, and backoff clamps."""
    # 1. 429 with explicit Retry-After header
    status, detail, retryable, backoff = classify_http_failure(
        429, headers={"retry-after": "3"}
    )
    assert status == FailureClass.RATE_LIMITED.value
    assert retryable is True
    assert backoff == 3.0

    # 2. 429 with very high Retry-After clamped to 5.0s maximum backoff
    status, detail, retryable, backoff = classify_http_failure(
        429, headers={"retry-after": "60"}
    )
    assert status == FailureClass.RATE_LIMITED.value
    assert retryable is True
    assert backoff == 5.0  # Clamped to 5.0s

    # 3. 429 without header defaults to minimum sensible backoff (0.5s)
    status, detail, retryable, backoff = classify_http_failure(429, headers={})
    assert status == FailureClass.RATE_LIMITED.value
    assert retryable is True
    assert backoff == 0.5


# ---------------------------------------------------------------------------
# 6. External Host Timeout Resilience
# ---------------------------------------------------------------------------

def test_external_host_timeout_resilience():
    """Verify timeout classification and extraction into retryable missing pieces."""
    # Source timeout failure classification
    sources = [
        {"url": "https://github.com/candidate/repo1", "status": "completed"},
        {"url": "https://slow-external-service.com/api", "status": "timeout", "detail": "Connection timed out after 5.0s"},
    ]
    missing = extract_missing_pieces(sources, time_exhausted=False)
    assert len(missing) == 1
    assert missing[0]["status"] == FailureClass.TIMEOUT.value
    assert missing[0]["is_retryable"] is True
    assert is_retryable_status(FailureClass.TIMEOUT.value) is True


# ---------------------------------------------------------------------------
# 7. Partial Outage Graceful Degradation
# ---------------------------------------------------------------------------

def test_partial_outage_graceful_degradation():
    """Verify that when 1 source is completely down (503/404), surviving sources produce a valid dossier."""
    cid = uuid4()
    rid = uuid4()

    # Surviving healthy sources: backend and database evidence
    healthy_records = [
        _make_perf_record(CapabilityKey.BACKEND_ENGINEERING, 88.0, cluster_id="cluster-healthy-1", path="api/server.py"),
        _make_perf_record(CapabilityKey.BACKEND_ENGINEERING, 86.0, cluster_id="cluster-healthy-1", path="api/routes.py"),
        _make_perf_record(CapabilityKey.DATABASE_ENGINEERING, 82.0, family=SourceFamily.DATABASE, cluster_id="cluster-healthy-2", path="db/schema.sql"),
    ]

    result = execute_analysis_pipeline(
        candidate_id=cid,
        analysis_run_id=rid,
        role=CanonicalRole.BACKEND,
        custom_evidence=healthy_records,
        evidence_mode="provided",
    )

    # Pipeline successfully produces dossier with observed evidence from surviving sources
    assert result.status == PipelineStatus.COMPLETED
    assert result.dossier is not None
    assert len(result.dossier.evidence_records) == 3

    # Document missing piece for the failed source without crashing the run
    source_status_map = [
        {"url": "https://github.com/candidate/healthy-repo-1", "status": "completed"},
        {"url": "https://github.com/candidate/healthy-repo-2", "status": "completed"},
        {"url": "https://github.com/candidate/outage-repo", "status": "unavailable", "detail": "Upstream service 503 unavailable"},
    ]
    missing = extract_missing_pieces(source_status_map)
    assert len(missing) == 1
    assert missing[0]["source"] == "https://github.com/candidate/outage-repo"
    assert missing[0]["status"] == "unavailable"


# ---------------------------------------------------------------------------
# 8. Circuit Breaker Protection under Burst Failures
# ---------------------------------------------------------------------------

def test_circuit_breaker_tripping_and_cooldown():
    """Verify circuit breaker trips to OPEN on repeated upstream failures, blocking cascading traffic."""
    registry = CircuitBreakerRegistry(failure_threshold=3, cooldown_seconds=0.1)
    breaker = registry.get_breaker("api.github.com")

    assert breaker.state == CircuitState.CLOSED
    assert breaker.can_execute() is True

    # 1. Simulate 2 consecutive failures -> stays CLOSED (< threshold 3)
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.can_execute() is True

    # 2. 3rd failure trips the breaker to OPEN
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.can_execute() is False

    # 3. Wait for cooldown period (0.1s) -> transitions to HALF_OPEN
    time.sleep(0.12)
    assert breaker.can_execute() is True  # triggers transition to HALF_OPEN
    assert breaker.state == CircuitState.HALF_OPEN

    # 4. Successful execution resets breaker to CLOSED
    breaker.record_success()
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.can_execute() is True


# ---------------------------------------------------------------------------
# 9. Concurrency Limiter Enforcement
# ---------------------------------------------------------------------------

def test_concurrency_limiter_enforcement():
    """Verify global and per-client concurrent execution limits under peak requests."""
    limiter = ConcurrencyLimiter(global_max=5, per_key_max=2)

    # Client A acquires 2 slots -> succeeds
    ok1, _ = limiter.acquire("client-a")
    ok2, _ = limiter.acquire("client-a")
    assert ok1 is True
    assert ok2 is True

    # Client A attempts 3rd slot -> rejected by per-client cap
    ok3, reason = limiter.acquire("client-a")
    assert ok3 is False
    assert "Per-client concurrency limit" in reason

    # Client B, C, D acquire slots -> reaches global maximum of 5
    ok_b, _ = limiter.acquire("client-b")
    ok_c, _ = limiter.acquire("client-c")
    ok_d, _ = limiter.acquire("client-d")
    assert ok_b is True and ok_c is True and ok_d is True
    assert limiter.active_count() == 5

    # 6th slot from any client is rejected by global cap
    ok_e, reason = limiter.acquire("client-e")
    assert ok_e is False
    assert "Global concurrency limit reached" in reason

    # Releasing Client A slot allows another client to proceed
    limiter.release("client-a")
    assert limiter.active_count() == 4
    ok_e_retry, _ = limiter.acquire("client-e")
    assert ok_e_retry is True
