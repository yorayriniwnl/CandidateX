"""Evidence Coverage, Role Capability Index (RCI), and sufficiency evaluation."""

from uuid import UUID

from cci.domain.contracts import (
    AnalysisScore,
    CapabilityEstimate,
    RoleProfile,
    ScoringConfig,
)
from cci.domain.coverage_policy import is_coverage_sufficient
from cci.domain.enums import CapabilityKey
from cci.scoring.capability import has_sufficient_candidate_evidence


def compute_evidence_coverage(
    capabilities: dict[CapabilityKey, CapabilityEstimate],
    role_weights: dict[CapabilityKey, float],
) -> float:
    """Computes Evidence Coverage across all 12 capabilities:

        Coverage(C, J) = sum_k w_k * Cov_k

    where Cov_k = min(1.0, sum(c_e,k) / tau_k).
    Returns Coverage in [0.0, 1.0].
    """
    total_coverage = 0.0
    for cap, est in capabilities.items():
        w_k = role_weights.get(cap, 0.0)
        cov_k = est.coverage_k if est is not None else 0.0
        total_coverage += w_k * cov_k

    return max(0.0, min(1.0, float(total_coverage)))


def compute_rci(
    capabilities: dict[CapabilityKey, CapabilityEstimate],
    role_weights: dict[CapabilityKey, float],
    config: ScoringConfig | None = None,
) -> float | None:
    """Computes RCI only over capabilities with sufficient attributed coverage:

        RCI(C, J) = 100 * sum_{k in observed}(w_k * q_k) / sum_{k in observed}(w_k)

    Returns:
        float in [0.0, 100.0] if at least one capability meets the configured
        evidence threshold, or None otherwise.
    """
    cfg = config or ScoringConfig()
    observed_weight_sum = 0.0
    weighted_score_sum = 0.0

    for cap, est in capabilities.items():
        if (
            est is not None
            and est.is_observed
            and est.estimate is not None
            and has_sufficient_candidate_evidence(est.coverage_k, cfg)
        ):
            w_k = role_weights.get(cap, 0.0)
            q_k = est.estimate

            weighted_score_sum += w_k * q_k
            observed_weight_sum += w_k

    if observed_weight_sum <= 0.0:
        return None

    rci_val = weighted_score_sum / observed_weight_sum
    return max(0.0, min(100.0, float(rci_val)))


def evaluate_analysis_score(
    candidate_id: UUID,
    role_profile: RoleProfile,
    capabilities: dict[CapabilityKey, CapabilityEstimate],
    config: ScoringConfig | None = None,
) -> AnalysisScore:
    """Combines RCI and Coverage into formal AnalysisScore contract."""
    cfg = config or ScoringConfig()
    weights = role_profile.softmax_weights

    coverage = compute_evidence_coverage(capabilities, weights)
    rci = compute_rci(capabilities, weights, config=cfg)

    observed_count = sum(
        1
        for est in capabilities.values()
        if est is not None and est.is_observed and est.estimate is not None
    )

    is_insufficient = not is_coverage_sufficient(
        coverage, threshold=cfg.low_coverage_threshold
    )

    return AnalysisScore(
        candidate_id=candidate_id,
        role=role_profile.canonical_role,
        rci=rci,
        coverage=coverage,
        is_insufficient_evidence=is_insufficient,
        observed_capabilities_count=observed_count,
        scoring_config_version=cfg.version,
        coverage_sufficiency_threshold=cfg.low_coverage_threshold,
    )
