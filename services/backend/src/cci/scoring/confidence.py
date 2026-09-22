"""Attribution-gated evidence weight calculation."""

from cci.domain.contracts import EvidenceConfidenceFactors


def compute_evidence_confidence(
    artifact_integrity: float,
    ownership_score: float,
    recency_factor: float,
    verification_level: float,
    depth_specificity: float,
    source_reliability: float,
) -> float:
    """Computes an attribution-gated evidence weight:

        q_{e,k} = (a_e * t_{e,k} * v_e * x_e * r_s(e))^(1/5)
        c_{e,k} = o_e * q_{e,k}

    Attribution is a direct gate; the five evidence-quality factors cannot
    compensate for weak attribution. The result is a relative evidence weight,
    not a calibrated probability. Each factor is clamped to [0.0, 1.0].
    """
    factors = [
        artifact_integrity,
        ownership_score,
        recency_factor,
        verification_level,
        depth_specificity,
        source_reliability,
    ]

    # Range validation & clamping
    clamped = [max(0.0, min(1.0, float(f))) for f in factors]

    attribution_gate = clamped[1]
    quality_factors = clamped[:1] + clamped[2:]
    if attribution_gate == 0.0 or any(f == 0.0 for f in quality_factors):
        return 0.0

    product = 1.0
    for f in quality_factors:
        product *= f

    evidence_quality = product ** (1.0 / 5.0)
    return float(attribution_gate * evidence_quality)


def compute_confidence_from_factors(factors: EvidenceConfidenceFactors) -> float:
    """Convenience wrapper for EvidenceConfidenceFactors domain object."""
    return compute_evidence_confidence(
        artifact_integrity=factors.artifact_integrity,
        ownership_score=factors.ownership_score,
        recency_factor=factors.recency_factor,
        verification_level=factors.verification_level,
        depth_specificity=factors.depth_specificity,
        source_reliability=factors.source_reliability,
    )
