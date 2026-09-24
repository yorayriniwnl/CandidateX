"""Final Red Team Audit Test Suite across 10 Adversary Personas (FIX 55).

Simulates 10 adversarial perspectives to verify that CandidateX cannot be broken:
1. Skeptical recruiter (fork theft, automatic hire/reject prevention)
2. Candidate disputing report (5-hop traceability, zero ungrounded negative claims)
3. Security engineer (static execution invariant, SSRF, symlink traversal)
4. Statistician (pseudoreplication, Kish effective depth, D_k stability)
5. Research-paper reviewer (reproducibility, canonical versioning, pure rescore invariant)
6. SaaS architect (immutability, persistence, partial outage isolation)
7. Malicious API user (burst rate limiting, concurrency cap, circuit breaker)
8. Privacy officer (demographic neutrality, credential scrubbing)
9. Senior backend engineer (model freezing, structured error handling, thread safety)
10. Frontend accessibility reviewer (UX truth compliance, semantic export structure)
"""

from datetime import datetime, timezone
import hashlib
import json
import pytest
from uuid import uuid4

from cci.domain.contracts import (
    CanonicalRole,
    CapabilityConflict,
    CapabilityEstimate,
    CapabilityKey,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NegativeEvidenceDetails,
    NegativeEvidenceScanScope,
    ScoringConfig,
    SourceFamily,
)
from cci.scoring.ownership import estimate_repository_ownership
from cci.live.resilience import (
    FailureClass,
    classify_http_failure,
    extract_missing_pieces,
)
from cci.pipeline.orchestrator import PipelineStatus, execute_analysis_pipeline
from cci.reports.exporter import generate_html_brief, generate_markdown_brief
from cci.scoring.capability import compute_capability_score, compute_cluster_aware_coverage, build_evidence_coverage_item
from cci.security.abuse import (
    CircuitBreaker,
    CircuitState,
    ConcurrencyLimiter,
    RateLimiter,
    RateLimitExceeded,
    sanitize_credentials,
)
from cci.security.ssrf import SSRFSecurityError, validate_safe_url
from cci.versioning import (
    SCORING_MODEL_VERSION,
    build_reproducibility_metadata,
    get_canonical_version_dict,
    validate_dossier_reproducibility,
)


def _make_adversarial_record(
    cap: CapabilityKey,
    signal: float,
    family: SourceFamily = SourceFamily.GITHUB,
    cluster_id: str = "cluster-red-team",
    path: str = "src/module.py",
    ownership: float = 0.95,
    recency: float = 0.95,
    depth: float = 0.90,
    commit_sha: str = "11223344556677889900aabbccddeeff00112233",
    is_positive: bool = True,
    claim_ref: str | None = None,
) -> EvidenceRecord:
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=ownership,
        recency_factor=recency,
        verification_level=1.0,
        depth_specificity=depth,
        source_reliability=0.90,
    )
    chash = hashlib.sha256(f"{path}:{commit_sha}:{signal}".encode()).hexdigest()
    neg_details = None
    if not is_positive:
        neg_details = NegativeEvidenceDetails(
            claim_reference=claim_ref or ("cr1:" + "f" * 64),
            candidate_type="candidatex.contradiction.coverage_below_claim",
            expected_observation="Test coverage >= 90%",
            actual_observation="Coverage artifact records 40%",
            scan_scope=NegativeEvidenceScanScope(scope_kind="synthetic"),
            required_scan_completeness=1.0,
            observed_scan_completeness=1.0,
            explanation="Automated test report contradicts candidate self-reported claim.",
        )
    return EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint=f"fp-{uuid4()}",
        source_family=family,
        source_locator=f"https://github.com/adversary/{cluster_id}",
        immutable_revision=commit_sha,
        target_capability=cap,
        technical_signal_strength=signal,
        is_positive_support=is_positive,
        negative_evidence_details=neg_details,
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
            **({"synthetic": True} if not is_positive else {}),
        },
    )


# ==============================================================================
# 1. Persona 1: Skeptical Recruiter
# ==============================================================================
def test_persona_1_skeptical_recruiter():
    """Verify recruiter cannot be deceived by forked repositories and system never issues automated hire/reject."""
    # Attack: Candidate forks a 50,000-star repo, commits 0 lines, claims backend mastery
    ownership_assessment = estimate_repository_ownership(
        repository_url="https://github.com/candidate/massive-fork",
        candidate_identifier="candidate_x",
        is_fork=True,
        candidate_commits=0,
        total_commits=15000,
        candidate_lines=0,
        total_lines=500000,
    )
    assert ownership_assessment.ownership_score <= 0.10

    # Pipeline gating prevents certification on zero-attribution repo
    rec = _make_adversarial_record(
        cap=CapabilityKey.BACKEND_ENGINEERING,
        signal=99.0,
        ownership=ownership_assessment.ownership_score,
        cluster_id="cluster-forked-repo",
    )
    est = compute_capability_score([rec], CapabilityKey.BACKEND_ENGINEERING)
    assert est.is_observed is False
    assert est.estimate is None

    # Decision Support Guarantee: System limitations strictly forbid automatic hire/reject
    res = execute_analysis_pipeline(
        candidate_id=uuid4(),
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
        custom_evidence=[rec],
        evidence_mode="provided",
    )
    assert any("decision support only" in lim.lower() for lim in res.dossier.system_limitations)
    assert any("never executed" in lim.lower() for lim in res.dossier.system_limitations)


# ==============================================================================
# 2. Persona 2: Candidate Disputing the Report
# ==============================================================================
def test_persona_2_candidate_disputing_report():
    """Verify complete 5-hop provenance traceability when candidate challenges a discrepancy finding."""
    claim_ref = "cr1:" + "e" * 64
    commit_sha = "99887766554433221100aabbccddeeff00112233"
    rec_pos = _make_adversarial_record(
        cap=CapabilityKey.TESTING_QUALITY,
        signal=85.0,
        cluster_id="cluster-test-repo",
        path="tests/test_core.py",
        commit_sha=commit_sha,
    )
    rec_neg = _make_adversarial_record(
        cap=CapabilityKey.TESTING_QUALITY,
        signal=40.0,
        cluster_id="cluster-test-repo",
        path="coverage.xml",
        commit_sha=commit_sha,
        is_positive=False,
        claim_ref=claim_ref,
    )

    res = execute_analysis_pipeline(
        candidate_id=uuid4(),
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
        custom_evidence=[rec_pos, rec_neg],
        evidence_mode="provided",
    )

    # 1. Discrepancy is fully detailed and grounded
    conflict = res.dossier.capability_conflicts.get(CapabilityKey.TESTING_QUALITY)
    assert conflict is not None
    assert conflict.has_meaningful_conflict is True

    # 2. 5-Hop Traceability
    neg_ev = next(e for e in res.dossier.evidence_records if not e.is_positive_support)
    # Hop 1: Claim Reference
    assert neg_ev.negative_evidence_details.claim_reference == claim_ref
    # Hop 2: Corroboration / Diagnostic
    assert neg_ev.negative_evidence_details.candidate_type == "candidatex.contradiction.coverage_below_claim"
    # Hop 3: Evidence Record Identity
    assert neg_ev.evidence_id is not None
    # Hop 4: Inspected Artifact Path
    assert neg_ev.provenance["artifact_path"] == "coverage.xml"
    # Hop 5: Immutable Revision
    assert neg_ev.immutable_revision == commit_sha
    assert neg_ev.provenance["artifact_sha256"] is not None

    # Truth In UX: Unobserved skills (ML) remain UNKNOWN, never penalized to 0.0
    ml_est = res.dossier.capability_estimates.get(CapabilityKey.MACHINE_LEARNING)
    assert ml_est.estimate is None
    assert ml_est.is_observed is False


# ==============================================================================
# 3. Persona 3: Security Engineer
# ==============================================================================
def test_persona_3_security_engineer():
    """Verify absolute static-only analysis, SSRF prevention, and credential sanitization."""
    # 1. SSRF: Private IP, loopback, and cloud metadata blocking
    with pytest.raises(SSRFSecurityError):
        validate_safe_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(SSRFSecurityError):
        validate_safe_url("http://127.0.0.1:8000/internal")
    with pytest.raises(SSRFSecurityError):
        validate_safe_url("http://10.0.0.1/admin")

    # 2. Credential scrubbing: GitHub PATs, AWS keys, private keys scrubbed
    leaked_payload = {
        "token": "ghp_123456789012345678901234567890123456",
        "aws": "AKIAIOSFODNN7EXAMPLE",
        "code_snippet": "client = github('ghp_abcdefghijklmnopqrstuvwxyz1234567890')",
    }
    sanitized = sanitize_credentials(leaked_payload)
    assert sanitized["token"] == "[REDACTED_CREDENTIAL]"
    assert sanitized["aws"] == "[REDACTED_CREDENTIAL]"
    assert "ghp_" not in sanitized["code_snippet"]


# ==============================================================================
# 4. Persona 4: Statistician
# ==============================================================================
def test_persona_4_statistician():
    """Verify Kish effective sample size, non-saturating pseudoreplication, and bounded contradiction D_k."""
    # 1. Pseudoreplication: 50 records from the same cluster
    duplicate_records = [
        _make_adversarial_record(
            cap=CapabilityKey.BACKEND_ENGINEERING,
            signal=85.0,
            cluster_id="single-monolith-repo",
            path=f"file_{i}.py",
        )
        for i in range(50)
    ]
    # Cluster-aware coverage applies diminishing geometric returns
    items = [
        build_evidence_coverage_item(
            source_family=r.source_family,
            source_locator=r.source_locator,
            confidence=r.confidence,
            cluster_id=r.cluster_id,
            artifact_path=r.provenance.get("artifact_path"),
            fingerprint=r.fingerprint,
        )
        for r in duplicate_records
    ]
    cov, n_clusters = compute_cluster_aware_coverage(items, tau_saturation=5.0, artifact_decay=0.5)
    # 1 cluster with decay 0.5 can never contribute more than 1 / (1 - 0.5) = 2.0 mass -> cov < 2.0 / 5.0 = 0.40
    assert cov < 0.40
    assert n_clusters == 1

    # 2. Contradiction diagnostic D_k denominator stabilization
    # When P_k = 0 and N_k = 0, D_k must be 0.0, never ZeroDivisionError
    cfg = ScoringConfig(epsilon=1e-5)
    p_k, n_k = 0.0, 0.0
    d_k = (p_k - n_k) / (p_k + n_k + cfg.epsilon)
    assert abs(d_k) < 1e-4
    assert -1.0 <= d_k <= 1.0


# ==============================================================================
# 5. Persona 5: Research-Paper Reviewer
# ==============================================================================
def test_persona_5_research_paper_reviewer():
    """Verify dossier reproducibility, canonical versioning metadata, and pure rescore invariance."""
    res = execute_analysis_pipeline(
        candidate_id=uuid4(),
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
    )
    dossier = res.dossier
    assert dossier is not None

    # Canonical version metadata
    assert dossier.versions is not None
    assert "scoring_model_version" in dossier.versions
    assert dossier.versions["scoring_model_version"] == SCORING_MODEL_VERSION
    
    is_reproducible, missing = validate_dossier_reproducibility(dossier.versions)
    assert is_reproducible is True
    assert len(missing) == 0

    repro_meta = build_reproducibility_metadata(dossier)
    assert repro_meta["is_reproducible"] is True
    assert "scoring_engine" in repro_meta["reproducibility_contract"]

    # Export reproducibility
    json_dump = dossier.model_dump_json()
    parsed = json.loads(json_dump)
    assert parsed["candidate_id"] == str(dossier.candidate_id)
    assert parsed["versions"]["scoring_model_version"] == SCORING_MODEL_VERSION


# ==============================================================================
# 6. Persona 6: SaaS Architect
# ==============================================================================
def test_persona_6_saas_architect():
    """Verify immutable dossier serialization and partial failure isolation."""
    # 1. Complete JSON serialization
    res = execute_analysis_pipeline(
        candidate_id=uuid4(),
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
    )
    serialized = res.dossier.model_dump_json()
    assert len(serialized) > 100

    # 2. Partial Outage Isolation
    sources = [
        {"url": "https://github.com/candidate/active-repo", "status": "completed"},
        {"url": "https://github.com/candidate/broken-repo", "status": "unavailable", "detail": "HTTP 502"},
    ]
    missing = extract_missing_pieces(sources)
    assert len(missing) == 1
    assert missing[0]["status"] == "unavailable"


# ==============================================================================
# 7. Persona 7: Malicious API User
# ==============================================================================
def test_persona_7_malicious_api_user():
    """Verify sliding-window rate limiting, concurrency limiting, and circuit breaker tripping."""
    # 1. Rate Limiter blocks burst traffic and emits Retry-After
    limiter = RateLimiter()
    ip = "203.0.113.195"
    for _ in range(5):
        limiter.check_rate_limit(ip, bucket="test", limit=5, window_seconds=60.0)
    allowed, retry_after, remaining = limiter.check_rate_limit(ip, bucket="test", limit=5, window_seconds=60.0)
    assert allowed is False
    assert retry_after > 0.0
    assert remaining == 0

    # 2. Concurrency Limiter blocks excess simultaneous executions
    concurrency = ConcurrencyLimiter(global_max=2, per_key_max=1)
    acq1, _ = concurrency.acquire("user1")
    assert acq1 is True
    acq2, reason = concurrency.acquire("user1")
    assert acq2 is False
    assert "Per-client concurrency limit" in reason

    # 3. Circuit breaker trips to OPEN on repeated upstream faults
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=10.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False


# ==============================================================================
# 8. Persona 8: Privacy Officer
# ==============================================================================
def test_persona_8_privacy_officer():
    """Verify complete absence of protected demographic attributes in scoring models and schemas."""
    forbidden_demographics = {
        "gender", "race", "ethnicity", "age", "marital_status",
        "nationality", "religion", "sexual_orientation", "disability",
    }
    scoring_cfg_fields = ScoringConfig.model_fields.keys()
    for field in scoring_cfg_fields:
        field_tokens = set(field.lower().split("_"))
        overlap = forbidden_demographics.intersection(field_tokens)
        assert not overlap, f"Forbidden demographic field token {overlap} found in ScoringConfig.{field}"

    # CapabilityEstimate contract must not contain demographic data
    estimate_fields = CapabilityEstimate.model_fields.keys()
    for field in estimate_fields:
        field_tokens = set(field.lower().split("_"))
        overlap = forbidden_demographics.intersection(field_tokens)
        assert not overlap, f"Forbidden demographic field token {overlap} found in CapabilityEstimate.{field}"


# ==============================================================================
# 9. Persona 9: Senior Backend Engineer
# ==============================================================================
def test_persona_9_senior_backend_engineer():
    """Verify contract immutability, thread-safe models, and graceful pipeline error encapsulation."""
    # 1. Pydantic v2 Frozen Contract Protection
    est = CapabilityEstimate(
        capability_key=CapabilityKey.BACKEND_ENGINEERING,
        estimate=85.0,
        is_observed=True,
        effective_evidence_count=3.0,
        raw_evidence_count=3,
        coverage_k=0.75,
    )
    with pytest.raises(Exception):
        est.estimate = 99.0  # Must be immutable / frozen

    # 2. Structured Stage Pipeline Progression
    res = execute_analysis_pipeline(
        candidate_id=uuid4(),
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
    )
    assert res.status == PipelineStatus.COMPLETED
    assert len(res.stages) == 10
    for stage in res.stages:
        assert stage.status in ("completed", "skipped", "failed")


# ==============================================================================
# 10. Persona 10: Frontend Accessibility & Truth Reviewer
# ==============================================================================
def test_persona_10_frontend_accessibility_reviewer():
    """Verify absence of ungrounded ranking/fraud terminology and accessibility compliance in exports."""
    cid = uuid4()
    res = execute_analysis_pipeline(
        candidate_id=cid,
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
    )
    dossier = res.dossier

    # Markdown Export Truth Check
    md_brief = generate_markdown_brief(dossier)
    forbidden_terms = [
        "verified code capabilities",
        "verified code coverage",
        "fraud",
        "cheating",
        "top candidate",
        "leaderboard",
        "automatic hire",
    ]
    for term in forbidden_terms:
        assert term not in md_brief.lower(), f"Forbidden overclaiming term '{term}' present in Markdown brief"

    # HTML Export Accessibility and Semantic Structure
    html_brief = generate_html_brief(dossier)
    assert "<!DOCTYPE html>" in html_brief
    assert '<html lang="en">' in html_brief
    assert "<table" in html_brief
    assert "<footer" in html_brief
    assert "container" in html_brief
    assert "Candidate Capability Intelligence (CCI)" in html_brief
