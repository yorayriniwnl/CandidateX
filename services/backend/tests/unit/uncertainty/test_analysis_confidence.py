from uuid import uuid4

from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    RoleFitSummary,
)
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.uncertainty.summary import build_analysis_confidence


def _empty_capabilities() -> dict[CapabilityKey, CapabilityEstimate]:
    return {
        capability: CapabilityEstimate(
            capability_key=capability,
            estimate=None,
            is_observed=False,
            effective_evidence_count=0.0,
            raw_evidence_count=0,
            cluster_count=0,
            standard_error=0.0,
            dispersion=0.0,
            coverage_k=0.0,
        )
        for capability in CapabilityKey
    }


def _weights() -> dict[CapabilityKey, float]:
    return {
        capability: 1.0 if capability == CapabilityKey.BACKEND_ENGINEERING else 0.0
        for capability in CapabilityKey
    }


def _factors(*, confidence: float = 1.0) -> EvidenceConfidenceFactors:
    return EvidenceConfidenceFactors(
        artifact_integrity=confidence,
        ownership_score=confidence,
        recency_factor=confidence,
        verification_level=confidence,
        depth_specificity=confidence,
        source_reliability=confidence,
    )


def _evidence(
    cluster: str,
    *,
    score: float = 96.0,
    confidence: float = 1.0,
    positive: bool = True,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint=f"fingerprint-{cluster}-{score}-{confidence}",
        source_family=SourceFamily.GITHUB,
        source_locator=f"https://github.com/example/{cluster}",
        immutable_revision="a" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=score,
        is_positive_support=positive,
        confidence_factors=_factors(confidence=confidence),
        confidence=confidence,
        cluster_id=cluster,
    )


def _observed_capability(
    *,
    score: float = 96.0,
    coverage: float = 0.9,
    clusters: int = 1,
    ci: tuple[float, float] | None = None,
) -> CapabilityEstimate:
    return CapabilityEstimate(
        capability_key=CapabilityKey.BACKEND_ENGINEERING,
        estimate=score,
        is_observed=True,
        effective_evidence_count=float(clusters),
        raw_evidence_count=clusters,
        cluster_count=clusters,
        standard_error=1.0,
        dispersion=1.0,
        ci_lower=ci[0] if ci else None,
        ci_upper=ci[1] if ci else None,
        coverage_k=coverage,
    )


def _conflicts(*, meaningful: bool = False) -> dict[CapabilityKey, CapabilityConflict]:
    return {
        CapabilityKey.BACKEND_ENGINEERING: CapabilityConflict(
            capability_key=CapabilityKey.BACKEND_ENGINEERING,
            positive_support_sum=1.0,
            negative_support_sum=0.0,
            contradiction_diagnostic=1.0,
            has_meaningful_conflict=meaningful,
        )
    }


def test_one_high_score_cluster_cannot_be_well_supported():
    capabilities = _empty_capabilities()
    capabilities[CapabilityKey.BACKEND_ENGINEERING] = _observed_capability()

    result = build_analysis_confidence(
        capabilities=capabilities,
        evidence_records=[_evidence("repo-a")],
        role_weights=_weights(),
        conflicts=_conflicts(),
        role_fit=RoleFitSummary(),
    )

    assert result.evidence_strength == "limited"
    assert "single_cluster" in result.uncertainty_flags
    assert "interval_unavailable" in result.uncertainty_flags


def test_no_evidence_is_explicitly_insufficient():
    result = build_analysis_confidence(
        capabilities=_empty_capabilities(),
        evidence_records=[],
        role_weights=_weights(),
        conflicts={},
        role_fit=RoleFitSummary(),
    )

    assert result.evidence_strength == "insufficient"
    assert result.uncertainty_flags == ["no_empirical_evidence", "low_role_coverage"]
    assert result.role_coverage == 0.0


def test_independent_interval_backed_clusters_can_be_well_supported():
    capabilities = _empty_capabilities()
    capabilities[CapabilityKey.BACKEND_ENGINEERING] = _observed_capability(
        clusters=3, ci=(92.0, 98.0)
    )

    result = build_analysis_confidence(
        capabilities=capabilities,
        evidence_records=[_evidence("repo-a"), _evidence("repo-b"), _evidence("repo-c")],
        role_weights=_weights(),
        conflicts=_conflicts(),
        role_fit=RoleFitSummary(),
    )

    assert result.evidence_strength == "well_supported"
    assert result.independent_clusters == 3
    assert result.capabilities_with_intervals == 1
    assert result.interval_coverage == 1.0
    assert result.maximum_interval_width == 6.0


def test_conflict_and_mandatory_gap_keep_summary_below_well_supported():
    capabilities = _empty_capabilities()
    capabilities[CapabilityKey.BACKEND_ENGINEERING] = _observed_capability(
        clusters=3, ci=(92.0, 98.0)
    )
    role_fit = RoleFitSummary(
        mandatory_total=1,
        mandatory_unknown=1,
        critical_gaps=["PostgreSQL"],
    )

    result = build_analysis_confidence(
        capabilities=capabilities,
        evidence_records=[
            _evidence("repo-a"),
            _evidence("repo-b"),
            _evidence("repo-c", score=20.0, positive=False),
        ],
        role_weights=_weights(),
        conflicts={
            CapabilityKey.BACKEND_ENGINEERING: CapabilityConflict(
                capability_key=CapabilityKey.BACKEND_ENGINEERING,
                positive_support_sum=2.0,
                negative_support_sum=1.0,
                contradiction_diagnostic=0.33,
                has_meaningful_conflict=True,
            )
        },
        role_fit=role_fit,
    )

    assert result.evidence_strength == "limited"
    assert "meaningful_conflict" in result.uncertainty_flags
    assert "mandatory_unknown" in result.uncertainty_flags
