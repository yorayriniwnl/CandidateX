"""Interview probe priority ranking from paper-aligned formulation."""

from typing import Any

from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    CapabilityUncertainty,
    ProbePriority,
    RoleProfile,
    ScoringConfig,
)
from cci.domain.enums import CapabilityKey


def probe_priority_score(weight: float, coverage_gap: float, normalized_ci_width: float,
                         conflict: float, config: ScoringConfig | None = None) -> float:
    """Equation 8; q and CI width use the prototype's documented 0..100 scale."""
    cfg = config or ScoringConfig()
    return weight * (cfg.probe_alpha * coverage_gap + cfg.probe_beta * normalized_ci_width + cfg.probe_gamma * conflict)


def compute_probe_priorities(
    role_profile: RoleProfile,
    capabilities: dict[CapabilityKey, CapabilityEstimate],
    uncertainties: dict[CapabilityKey, CapabilityUncertainty],
    conflicts: dict[CapabilityKey, CapabilityConflict],
    config: ScoringConfig | None = None,
) -> list[ProbePriority]:
    """Computes ranked interview inquiry targets:

        I_k = w_k * [alpha * (1 - Cov_k) + beta * CIwidth_k + gamma * Conf_k]

    Returns list of ProbePriority sorted descending by priority_score I_k,
    with rank assigned from 1 to 12.
    """
    cfg = config or ScoringConfig()
    alpha = cfg.probe_alpha
    beta = cfg.probe_beta
    gamma = cfg.probe_gamma

    weights = role_profile.softmax_weights
    unranked_probes: list[dict[str, Any]] = []

    for cap in CapabilityKey:
        w_k = weights.get(cap, 0.0)

        est = capabilities.get(cap)
        cov_k = est.coverage_k if est is not None else 0.0
        coverage_gap = max(0.0, 1.0 - cov_k)

        unc = uncertainties.get(cap)
        raw_ci_width = unc.ci_width if unc is not None else 100.0
        # Normalize CI width from [0, 100] to [0, 1]
        norm_ci_width = max(0.0, min(1.0, raw_ci_width / 100.0))

        conf = conflicts.get(cap)
        if conf is not None:
            total_support = conf.positive_support_sum + conf.negative_support_sum
            # Conflict severity peaks when D_k is near 0 and total support exists
            support_scaler = min(1.0, total_support / 2.0)
            conf_term = (1.0 - abs(conf.contradiction_diagnostic)) * support_scaler
        else:
            conf_term = 0.0

        # Composite probe priority I_k
        inner_bracket = (
            (alpha * coverage_gap) + (beta * norm_ci_width) + (gamma * conf_term)
        )
        I_k = probe_priority_score(w_k, coverage_gap, norm_ci_width, conf_term, cfg)

        unranked_probes.append(
            {
                "capability_key": cap,
                "priority_score": I_k,
                "role_weight": w_k,
                "coverage_gap_term": coverage_gap,
                "uncertainty_term": norm_ci_width,
                "contradiction_term": conf_term,
            }
        )

    # Sort descending by priority score
    unranked_probes.sort(key=lambda x: x["priority_score"], reverse=True)

    ranked_probes: list[ProbePriority] = []
    for rank_idx, item in enumerate(unranked_probes, start=1):
        ranked_probes.append(
            ProbePriority(
                capability_key=item["capability_key"],
                rank=rank_idx,
                priority_score=item["priority_score"],
                role_weight=item["role_weight"],
                coverage_gap_term=item["coverage_gap_term"],
                uncertainty_term=item["uncertainty_term"],
                contradiction_term=item["contradiction_term"],
            )
        )

    return ranked_probes
