"""Formal paper-aligned scoring functions for CCI."""

from cci.scoring.capability import (
    compute_capability_score,
    compute_effective_evidence_count,
)
from cci.scoring.confidence import (
    compute_confidence_from_factors,
    compute_evidence_confidence,
)
from cci.scoring.ownership import (
    assemble_confidence_factors,
    estimate_repository_ownership,
)
from cci.scoring.rci import (
    compute_evidence_coverage,
    compute_rci,
    evaluate_analysis_score,
)
from cci.scoring.recency import calculate_elapsed_years, compute_recency_factor
from cci.scoring.reliability import (
    DEFAULT_PRIOR_RATIONALES,
    DEFAULT_PRIORS,
    calibrate_from_empirical_outcomes,
    calibrate_from_observations,
    compute_source_reliability,
    get_default_reliability_snapshots,
)
from cci.scoring.weights import (
    apply_expert_overrides,
    build_role_profile,
    compute_role_importances,
    compute_softmax_weights,
)

__all__ = [
    "DEFAULT_PRIOR_RATIONALES",
    "DEFAULT_PRIORS",
    "apply_expert_overrides",
    "assemble_confidence_factors",
    "build_role_profile",
    "calculate_elapsed_years",
    "calibrate_from_empirical_outcomes",
    "calibrate_from_observations",
    "compute_capability_score",
    "compute_confidence_from_factors",
    "compute_effective_evidence_count",
    "compute_evidence_confidence",
    "compute_evidence_coverage",
    "compute_rci",
    "compute_recency_factor",
    "compute_role_importances",
    "compute_softmax_weights",
    "compute_source_reliability",
    "estimate_repository_ownership",
    "evaluate_analysis_score",
    "get_default_reliability_snapshots",
]
