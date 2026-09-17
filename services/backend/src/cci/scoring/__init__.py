"""Formal paper-aligned scoring functions for CCI."""

from cci.scoring.recency import calculate_elapsed_years, compute_recency_factor
from cci.scoring.confidence import (
    compute_confidence_from_factors,
    compute_evidence_confidence,
)
from cci.scoring.capability import (
    compute_capability_score,
    compute_effective_evidence_count,
)
from cci.scoring.weights import (
    apply_expert_overrides,
    build_role_profile,
    compute_role_importances,
    compute_softmax_weights,
)
from cci.scoring.rci import (
    compute_evidence_coverage,
    compute_rci,
    evaluate_analysis_score,
)

from cci.scoring.reliability import (
    calibrate_from_observations,
    compute_source_reliability,
    get_default_reliability_snapshots,
)
from cci.scoring.ownership import (
    assemble_confidence_factors,
    estimate_repository_ownership,
)

__all__ = [
    "calculate_elapsed_years",
    "compute_recency_factor",
    "compute_confidence_from_factors",
    "compute_evidence_confidence",
    "compute_capability_score",
    "compute_effective_evidence_count",
    "compute_role_importances",
    "compute_softmax_weights",
    "build_role_profile",
    "apply_expert_overrides",
    "compute_evidence_coverage",
    "compute_rci",
    "evaluate_analysis_score",
    "compute_source_reliability",
    "calibrate_from_observations",
    "get_default_reliability_snapshots",
    "estimate_repository_ownership",
    "assemble_confidence_factors",
]
