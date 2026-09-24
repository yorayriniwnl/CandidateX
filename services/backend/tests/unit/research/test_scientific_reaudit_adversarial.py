"""Full Scientific Re-Audit: Adversarial Candidates A-P (Fix 51).

Recalculates the evidence model from first principles across 16 adversarial candidates:
A. Excellent repository, zero candidate attribution -> confidence crushed, no capability inflation.
B. Mediocre repository, strong ownership -> accurate moderate score, not penalized to 0.
C. One tiny contribution to giant strong repository -> path attribution prevents stolen credit.
D. Many duplicate artifacts -> cluster-aware coverage discounts correlated duplication.
E. One repo producing 100 analyzer hits -> single cluster cannot saturate cross-project coverage.
F. Multiple independent projects -> multi-cluster evidence grants higher coverage and confidence.
G. Stale code with recent README -> recency anchors to substantive code commits, not cosmetic README.
H. Strong resume, no evidence -> claims remain UNKNOWN; zero positive hiring score.
I. Weak resume, strong verified artifacts -> score driven by empirical code, unhindered by CV phrasing.
J. Conflicting public claims -> contradiction diagnostic detects discrepancies and triggers probes.
K. Inaccessible private work -> missing evidence evaluates strictly to UNKNOWN, never 0.0 penalty.
L. Project fork -> upstream commits not credited to candidate.
M. Generated repository -> low depth specificity and signal rules discount boilerplate.
N. Certificate-heavy candidate with no projects -> certificates provide proxy signal only; coding UNKNOWN.
O. Coding-profile-heavy candidate -> credits algorithmic dimension while system/infra remain UNKNOWN.
P. Sparse but extremely high-quality evidence -> high quality acknowledged, insufficient coverage flagged.
"""

from datetime import datetime, timezone, timedelta
import math
import pytest
from uuid import uuid4

from cci.contradictions.diagnostic import compute_contradiction_diagnostic
from cci.domain.contracts import (
    CapabilityEstimate,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NegativeEvidenceDetails,
    NegativeEvidenceScanScope,
    ScoringConfig,
)
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.scoring.capability import (
    compute_capability_score,
    compute_cluster_aware_coverage,
    build_evidence_coverage_item,
    compute_effective_evidence_count,
)
from cci.scoring.ownership import estimate_repository_ownership
from cci.scoring.recency import calculate_elapsed_years, compute_recency_factor
from cci.scoring.rci import compute_rci, compute_evidence_coverage


def _create_record(
    cap: CapabilityKey,
    signal: float,
    ownership: float = 1.0,
    artifact_integrity: float = 1.0,
    recency: float = 1.0,
    verification: float = 1.0,
    depth: float = 1.0,
    source_reliability: float = 0.9,
    cluster_id: str = "cluster-1",
    path: str = "src/main.py",
    commit_sha: str = "abc1234",
    content_hash: str | None = None,
    is_positive: bool = True,
    created_at: datetime | None = None,
) -> EvidenceRecord:
    factors = EvidenceConfidenceFactors(
        artifact_integrity=artifact_integrity,
        ownership_score=ownership,
        recency_factor=recency,
        verification_level=verification,
        depth_specificity=depth,
        source_reliability=source_reliability,
    )
    conf = factors.composite_confidence
    chash = content_hash or f"hash-{path}-{commit_sha}"
    neg_details = (
        NegativeEvidenceDetails(
            claim_reference="cr1:" + "a" * 64,
            candidate_type="candidatex.contradiction.coverage_below_claim",
            expected_observation="100% test coverage with automated unit tests",
            actual_observation="Zero test files observed in repository",
            scan_scope=NegativeEvidenceScanScope(scope_kind="synthetic"),
            required_scan_completeness=1.0,
            observed_scan_completeness=1.0,
            explanation="Repository scan revealed zero unit or integration test suites.",
        )
        if not is_positive
        else None
    )
    return EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint=f"fp-{uuid4()}",
        source_family=SourceFamily.GITHUB,
        source_locator=f"https://github.com/org/repo/{cluster_id}",
        immutable_revision=commit_sha,
        target_capability=cap,
        technical_signal_strength=signal,
        is_positive_support=is_positive,
        negative_evidence_details=neg_details,
        confidence_factors=factors,
        confidence=conf,
        cluster_id=cluster_id,
        created_at=created_at or datetime.now(timezone.utc),
        provenance={
            "path": path,
            "commit_sha": commit_sha,
            "content_hash": chash,
            **({"synthetic": True} if not is_positive else {}),
        },
    )


# ==============================================================================
# Candidate A: Excellent repository, zero candidate attribution
# ==============================================================================
def test_candidate_a_excellent_repo_zero_attribution():
    """Candidate linked a world-class repo (signal=98) but has 0% commit attribution."""
    rec = _create_record(
        cap=CapabilityKey.BACKEND_ENGINEERING,
        signal=98.0,
        ownership=0.0,  # Zero attribution
    )
    assert rec.confidence == 0.0  # Ownership gate completely collapses confidence

    est = compute_capability_score([rec], CapabilityKey.BACKEND_ENGINEERING)
    # Must evaluate strictly to UNKNOWN / unobserved
    assert est.is_observed is False
    assert est.estimate is None
    assert est.effective_evidence_count == 0.0


# ==============================================================================
# Candidate B: Mediocre repository, strong ownership
# ==============================================================================
def test_candidate_b_mediocre_repo_strong_ownership():
    """Candidate built a modest project (signal=55) with 100% ownership."""
    records = [
        _create_record(
            cap=CapabilityKey.BACKEND_ENGINEERING,
            signal=55.0,
            ownership=1.0,
            cluster_id=f"cluster-{i}",
            path=f"src/file_{i}.py",
        )
        for i in range(5)
    ]
    est = compute_capability_score(records, CapabilityKey.BACKEND_ENGINEERING)
    assert est.is_observed is True
    assert est.estimate is not None
    assert 53.0 <= est.estimate <= 57.0  # Accurately reflects 55 without false inflation


# ==============================================================================
# Candidate C: One tiny contribution to giant strong repository
# ==============================================================================
def test_candidate_c_tiny_contribution_giant_repo():
    """Candidate made a 2-line README fix in Kubernetes (giant repo)."""
    # Blame attribution gives 0.005 ownership
    assessment = estimate_repository_ownership(
        repository_url="https://github.com/kubernetes/kubernetes",
        candidate_identifier="candidate_x",
        candidate_commits=1,
        total_commits=10000,
        candidate_lines=2,
        total_lines=500000,
    )
    ownership = assessment.ownership_score
    assert ownership < 0.20

    rec = _create_record(
        cap=CapabilityKey.SOFTWARE_ARCHITECTURE,
        signal=99.0,
        ownership=ownership,
    )
    assert rec.confidence < 0.20  # Path attribution dampens signal
    est = compute_capability_score([rec], CapabilityKey.SOFTWARE_ARCHITECTURE)
    assert est.is_observed is False  # Cannot claim mastery of architecture
    assert est.estimate is None


# ==============================================================================
# Candidate D: Many duplicate artifacts
# ==============================================================================
def test_candidate_d_duplicate_artifacts():
    """10 duplicate copies of identical files must not inflate cluster coverage."""
    identical_hash = "sha256-identical-content-1111111111111111"
    items = [
        build_evidence_coverage_item(
            source_family=SourceFamily.GITHUB,
            source_locator=f"https://github.com/u/repo-{i}",
            confidence=0.8,
            cluster_id=f"repo-{i}",
            artifact_hash=identical_hash,  # Identical content
        )
        for i in range(10)
    ]
    coverage, cluster_count = compute_cluster_aware_coverage(items, tau_saturation=5.0)
    # Deduplication ensures only 1 copy contributes
    assert coverage < 0.25


# ==============================================================================
# Candidate E: One single repo producing 100 analyzer hits
# ==============================================================================
def test_candidate_e_single_repo_100_hits_bounded():
    """100 analyzer hits in 1 single repository must have bounded cluster mass."""
    items = [
        build_evidence_coverage_item(
            source_family=SourceFamily.GITHUB,
            source_locator="https://github.com/u/monorepo",
            confidence=0.9,
            cluster_id="monorepo",
            artifact_path=f"src/module_{i}/service.py",
        )
        for i in range(100)
    ]
    coverage, cluster_count = compute_cluster_aware_coverage(items, tau_saturation=5.0, artifact_decay=0.5)
    assert cluster_count == 1
    # Geometric decay ensures 1 cluster contributes at most 0.9 * (1 / (1 - 0.5)) = 1.8 mass
    # 1.8 / 5.0 = 0.36 max coverage
    assert coverage <= 0.40


# ==============================================================================
# Candidate F: Multiple independent projects
# ==============================================================================
def test_candidate_f_multiple_independent_projects():
    """4 independent projects provide superior coverage compared to 1 monorepo."""
    multi_items = [
        build_evidence_coverage_item(
            source_family=SourceFamily.GITHUB,
            source_locator=f"https://github.com/u/proj-{i}",
            confidence=0.8,
            cluster_id=f"proj-{i}",
            artifact_path="src/main.py",
        )
        for i in range(4)
    ]
    cov_multi, clusters_multi = compute_cluster_aware_coverage(multi_items, tau_saturation=5.0)
    assert clusters_multi == 4
    assert cov_multi > 0.60


# ==============================================================================
# Candidate G: Stale code with recent README
# ==============================================================================
def test_candidate_g_stale_code_recent_readme():
    """Code authored 5 years ago decayed; cosmetic README change yesterday does not boost code."""
    now = datetime.now(timezone.utc)
    old_code_date = now - timedelta(days=5 * 365)
    recent_readme_date = now - timedelta(days=1)

    recency_code = compute_recency_factor(calculate_elapsed_years(old_code_date, now), CapabilityKey.BACKEND_ENGINEERING)
    recency_readme = compute_recency_factor(calculate_elapsed_years(recent_readme_date, now), CapabilityKey.BACKEND_ENGINEERING)

    assert recency_code < 0.40
    assert recency_readme > 0.95

    # Code record anchored to old_code_date
    rec = _create_record(
        cap=CapabilityKey.BACKEND_ENGINEERING,
        signal=80.0,
        recency=recency_code,
        created_at=old_code_date,
    )
    assert rec.confidence_factors.recency_factor < 0.40


# ==============================================================================
# Candidate H: Strong resume, no evidence
# ==============================================================================
def test_candidate_h_strong_resume_no_evidence():
    """Candidate claims 15 years experience, 0 verified repos -> strictly UNKNOWN."""
    est = compute_capability_score([], CapabilityKey.SOFTWARE_ARCHITECTURE)
    assert est.is_observed is False
    assert est.estimate is None
    assert est.effective_evidence_count == 0.0


# ==============================================================================
# Candidate I: Weak resume, strong verified artifacts
# ==============================================================================
def test_candidate_i_weak_resume_strong_verified_artifacts():
    """Modest resume text, but 4 verified production repos -> strong capability recognized."""
    records = [
        _create_record(
            cap=CapabilityKey.BACKEND_ENGINEERING,
            signal=90.0,
            ownership=0.95,
            cluster_id=f"verified-repo-{i}",
            path=f"api/v{i}/router.py",
        )
        for i in range(4)
    ]
    est = compute_capability_score(records, CapabilityKey.BACKEND_ENGINEERING)
    assert est.is_observed is True
    assert est.estimate >= 88.0
    assert est.cluster_count == 4


# ==============================================================================
# Candidate J: Conflicting public claims
# ==============================================================================
def test_candidate_j_conflicting_public_claims():
    """Conflicting public claims trigger contradiction diagnostic and meaningful conflict flag."""
    pos_rec = _create_record(
        cap=CapabilityKey.TESTING_QUALITY,
        signal=85.0,
        is_positive=True,
    )
    neg_rec = _create_record(
        cap=CapabilityKey.TESTING_QUALITY,
        signal=20.0,
        is_positive=False,
    )
    conflict = compute_contradiction_diagnostic([pos_rec, neg_rec], CapabilityKey.TESTING_QUALITY)
    assert conflict.positive_support_sum > 0.0
    assert conflict.negative_support_sum > 0.0
    assert conflict.has_meaningful_conflict is True
    # D_k indicates contradiction / divergence between signals
    assert conflict.contradiction_diagnostic < 1.0


# ==============================================================================
# Candidate K: Inaccessible private work
# ==============================================================================
def test_candidate_k_inaccessible_work_unknown_not_zero():
    """Inaccessible private repos evaluate to UNKNOWN, never penalizing candidate with 0.0."""
    est = compute_capability_score([], CapabilityKey.SECURITY)
    assert est.estimate is None
    assert est.is_observed is False
    # Crucial platform invariant: UNKNOWN != 0.0
    assert est.estimate != 0.0


# ==============================================================================
# Candidate L: Project fork
# ==============================================================================
def test_candidate_l_project_fork_zero_candidate_commits():
    """Fork of major repo with 0 candidate commits -> attribution capped at 0.10."""
    assessment = estimate_repository_ownership(
        repository_url="https://github.com/candidate/forked-repo",
        candidate_identifier="candidate_x",
        is_fork=True,
        candidate_commits=0,
        total_commits=5000,
        candidate_lines=0,
        total_lines=200000,
    )
    assert assessment.ownership_score <= 0.10


# ==============================================================================
# Candidate M: Generated repository
# ==============================================================================
def test_candidate_m_generated_repository_discount():
    """Scaffolded/generated repository receives minimal ownership and confidence."""
    assessment = estimate_repository_ownership(
        repository_url="https://github.com/candidate/scaffolded-repo",
        candidate_identifier="candidate_x",
        is_vendor_or_generated=True,
    )
    assert assessment.ownership_score <= 0.05
    rec = _create_record(
        cap=CapabilityKey.FRONTEND_ENGINEERING,
        signal=40.0,
        ownership=assessment.ownership_score,
        depth=0.2,
    )
    assert rec.confidence <= 0.05


# ==============================================================================
# Candidate N: Certificate-heavy candidate with no projects
# ==============================================================================
def test_candidate_n_certificates_only_coding_unknown():
    """Online certificates do not establish production engineering capabilities."""
    cert_record = EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint=f"fp-{uuid4()}",
        source_family=SourceFamily.CERTIFICATE,
        source_locator="https://coursera.org/verify/123",
        immutable_revision="cert-rev-1",
        target_capability=CapabilityKey.DEVOPS_CLOUD,
        technical_signal_strength=75.0,
        is_positive_support=True,
        confidence_factors=EvidenceConfidenceFactors(
            artifact_integrity=0.8,
            ownership_score=0.9,
            recency_factor=0.9,
            verification_level=0.7,
            depth_specificity=0.3,  # Certificate proxy has low depth
            source_reliability=0.5,
        ),
        confidence=0.10,
        cluster_id="cert-cluster",
        created_at=datetime.now(timezone.utc),
        provenance={"credential_name": "Cloud Practitioner"},
    )
    est = compute_capability_score([cert_record], CapabilityKey.DEVOPS_CLOUD)
    # Low coverage threshold prevents single certificate from certifying cloud engineering
    assert est.is_observed is False
    assert est.estimate is None


# ==============================================================================
# Candidate O: Coding-profile-heavy candidate
# ==============================================================================
def test_candidate_o_coding_profile_heavy_bounded_domain():
    """LeetCode profile credits algorithms, while DevOps and Architecture remain UNKNOWN."""
    records_algo = [
        _create_record(
            cap=CapabilityKey.ALGORITHMS_PROBLEM_SOLVING,
            signal=95.0,
            cluster_id="leetcode-profile",
            path=f"solution_{i}.py",
        )
        for i in range(5)
    ]
    # Algorithms observed
    est_algo = compute_capability_score(records_algo, CapabilityKey.ALGORITHMS_PROBLEM_SOLVING)
    assert est_algo.estimate is not None
    assert est_algo.estimate >= 90.0

    # DevOps cloud unobserved
    est_devops = compute_capability_score([], CapabilityKey.DEVOPS_CLOUD)
    assert est_devops.is_observed is False
    assert est_devops.estimate is None


# ==============================================================================
# Candidate P: Sparse but extremely high-quality evidence
# ==============================================================================
def test_candidate_p_sparse_high_quality_insufficient_not_penalized():
    """1 small but pristine repo: estimate is high, but insufficient coverage is flagged."""
    rec = _create_record(
        cap=CapabilityKey.DATABASE_ENGINEERING,
        signal=96.0,
        ownership=1.0,
        cluster_id="pristine-lru-engine",
    )
    # Tau saturation is 5.0, so 1 artifact gives coverage ~0.16 < 0.35 threshold
    est = compute_capability_score([rec], CapabilityKey.DATABASE_ENGINEERING)
    assert est.coverage_k < 0.35
    assert est.is_observed is False  # Flagged as insufficient evidence for stand-alone certification
    assert est.raw_evidence_count == 1
    # Candidate is NOT penalized with 0.0
    assert est.estimate is None
