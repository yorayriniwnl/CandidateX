"""Six-factor multiplicative evidence confidence calculation."""

from typing import Iterable, List
from cci.domain.contracts import EvidenceConfidenceFactors


def compute_evidence_confidence(
    artifact_integrity: float,
    ownership_score: float,
    recency_factor: float,
    verification_level: float,
    depth_specificity: float,
    source_reliability: float,
) -> float:
    """Computes the 6-factor multiplicative confidence:
    
        c_{e,k} = (a_e * o_e * t_{e,k} * v_e * x_e * r_s(e))^(1/6)
        
    Each factor must be in the range [0.0, 1.0].
    Returns confidence c_{e,k} in [0.0, 1.0].
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
    
    if any(f == 0.0 for f in clamped):
        return 0.0
        
    product = 1.0
    for f in clamped:
        product *= f
        
    return float(product ** (1.0 / 6.0))


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
