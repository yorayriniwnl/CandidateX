"""Uncertainty diagnostics and low-coverage detection."""

from cci.domain.contracts import (
    CapabilityEstimate,
    CapabilityUncertainty,
    ScoringConfig,
)
from cci.domain.coverage_policy import is_coverage_sufficient


def compute_uncertainty_diagnostics(
    estimate: CapabilityEstimate,
    config: ScoringConfig | None = None,
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
        # Conservative probe priority when the interval is not estimable.
        ci_width = 100.0

    # Epistemic uncertainty: composite of coverage gap and CI width
    coverage_gap = 1.0 - estimate.coverage_k
    epistemic = (coverage_gap * 50.0) + min(50.0, ci_width / 2.0)

    is_low_cov = not is_coverage_sufficient(
        estimate.coverage_k, threshold=cfg.low_coverage_threshold
    )

    return CapabilityUncertainty(
        capability_key=estimate.capability_key,
        epistemic_uncertainty=float(epistemic),
        ci_width=float(ci_width),
        is_low_coverage=is_low_cov,
    )
