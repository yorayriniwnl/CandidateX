"""Uncertainty diagnostics and low-coverage detection."""

from typing import Optional
from cci.domain.contracts import CapabilityEstimate, CapabilityUncertainty, ScoringConfig


def compute_uncertainty_diagnostics(
    estimate: CapabilityEstimate,
    config: Optional[ScoringConfig] = None,
) -> CapabilityUncertainty:
    """Evaluates epistemic uncertainty and coverage sufficiency for a capability."""
    cfg = config or ScoringConfig()
    
    if not estimate.is_observed or estimate.estimate is None:
        return CapabilityUncertainty(
            capability_key=estimate.capability_key,
            epistemic_uncertainty=100.0,
            ci_width=100.0,
            is_low_coverage=True,
        )

    # Calculate CI width
    if estimate.ci_lower is not None and estimate.ci_upper is not None:
        ci_width = max(0.0, float(estimate.ci_upper - estimate.ci_lower))
    else:
        # Fallback based on asymptotic SE
        ci_width = max(0.0, float(2.0 * 1.96 * estimate.standard_error))

    # Epistemic uncertainty: composite of coverage gap and CI width
    coverage_gap = 1.0 - estimate.coverage_k
    epistemic = (coverage_gap * 50.0) + min(50.0, ci_width / 2.0)
    
    is_low_cov = estimate.coverage_k < cfg.low_coverage_threshold

    return CapabilityUncertainty(
        capability_key=estimate.capability_key,
        epistemic_uncertainty=float(epistemic),
        ci_width=float(ci_width),
        is_low_coverage=is_low_cov,
    )
