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
]
