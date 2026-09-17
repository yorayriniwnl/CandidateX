"""Property tests verifying invariants, pure rescoring, and deterministic reproducibility."""

import copy
import random
from uuid import uuid4
import pytest

from cci.domain.contracts import (
    EvidenceConfidenceFactors,
    EvidenceRecord,
    ScoringConfig,
)
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.scoring.capability import compute_capability_score
from cci.scoring.weights import build_role_profile
from cci.scoring.rci import (
    compute_evidence_coverage,
    compute_rci,
    evaluate_analysis_score,
)
from cci.uncertainty.bootstrap import cluster_bootstrap_ci
from cci.contradictions.diagnostic import compute_contradiction_diagnostic


def _generate_random_evidence(seed: int, count: int = 30) -> list[EvidenceRecord]:
    rng = random.Random(seed)
    capabilities = list(CapabilityKey)
    families = list(SourceFamily)

    records = []
    for _ in range(count):
        cap = rng.choice(capabilities)
        fam = rng.choice(families)
        score = rng.uniform(0.0, 100.0)
        is_pos = rng.choice([True, True, False])  # 2:1 positive bias
        conf = rng.uniform(0.05, 0.98)
        cluster = f"cluster_{rng.randint(1, 5)}"

        factors = EvidenceConfidenceFactors(
            artifact_integrity=rng.uniform(0.1, 1.0),
            ownership_score=rng.uniform(0.1, 1.0),
            recency_factor=rng.uniform(0.1, 1.0),
            verification_level=rng.uniform(0.1, 1.0),
            depth_specificity=rng.uniform(0.1, 1.0),
            source_reliability=rng.uniform(0.1, 1.0),
        )

        records.append(
            EvidenceRecord(
                fingerprint=str(uuid4()),
                source_family=fam,
                source_locator=f"https://github.com/test/{cluster}",
                immutable_revision=f"sha_{rng.randint(1000, 9999)}",
                target_capability=cap,
                support_score=score,
                is_positive_support=is_pos,
                confidence_factors=factors,
                confidence=conf,
                cluster_id=cluster,
                analyzer_version="1.0.0",
            )
        )
    return records


@pytest.mark.parametrize("seed", [101, 202, 303, 404, 505])
def test_rci_and_coverage_bounds_property(seed: int):
    """Property: RCI is in [0, 100], Coverage is in [0, 1] across arbitrary evidence distributions."""
    records = _generate_random_evidence(seed)
    profile = build_role_profile([], CanonicalRole.BACKEND)
    weights = profile.softmax_weights

    capabilities = {}
    for cap in CapabilityKey:
        capabilities[cap] = compute_capability_score(records, cap)

    cov = compute_evidence_coverage(capabilities, weights)
    assert 0.0 <= cov <= 1.0

    rci = compute_rci(capabilities, weights)
    if rci is not None:
        assert 0.0 <= rci <= 100.0


@pytest.mark.parametrize("seed", [11, 22, 33, 44, 55])
def test_contradiction_diagnostic_bounds_property(seed: int):
    """Property: D_k strictly bounded in [-1.0, 1.0] across arbitrary distributions."""
    records = _generate_random_evidence(seed)
    for cap in CapabilityKey:
        conflict = compute_contradiction_diagnostic(records, cap)
        assert -1.0 <= conflict.contradiction_diagnostic <= 1.0


def test_deterministic_bootstrap_under_seed():
    """Property: Under identical seed, cluster bootstrap CI produces identical numerical bounds."""
    records = _generate_random_evidence(seed=777, count=40)
    target_cap = CapabilityKey.BACKEND_ENGINEERING

    lower1, upper1 = cluster_bootstrap_ci(records, target_cap, n_resamples=500, seed=42)
    lower2, upper2 = cluster_bootstrap_ci(records, target_cap, n_resamples=500, seed=42)

    assert lower1 is not None and upper1 is not None
    assert lower1 == lower2
    assert upper1 == upper2
    assert lower1 <= upper1


def test_pure_rescore_no_mutation():
    """Property: Rescoring against multiple role profiles is pure and leaves evidence untouched."""
    records = _generate_random_evidence(seed=999, count=25)
    records_backup = copy.deepcopy(records)

    profile_backend = build_role_profile([], CanonicalRole.BACKEND)
    profile_ml = build_role_profile([], CanonicalRole.ML_ENGINEER)
    profile_devops = build_role_profile([], CanonicalRole.DEVOPS_CLOUD)

    cap_estimates = {cap: compute_capability_score(records, cap) for cap in CapabilityKey}

    score1 = evaluate_analysis_score(uuid4(), profile_backend, cap_estimates)
    score2 = evaluate_analysis_score(uuid4(), profile_ml, cap_estimates)
    score3 = evaluate_analysis_score(uuid4(), profile_devops, cap_estimates)

    # Re-evaluating backend must produce exact same score
    score1_repeat = evaluate_analysis_score(score1.candidate_id, profile_backend, cap_estimates)
    assert score1.rci == score1_repeat.rci
    assert score1.coverage == score1_repeat.coverage

    # Evidence records must remain identical to backup
    assert records == records_backup
