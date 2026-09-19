"""Capability estimate, effective evidence count, dispersion, and coverage."""

import math

from cci.domain.contracts import CapabilityEstimate, EvidenceRecord, ScoringConfig
from cci.domain.enums import CapabilityKey


def compute_effective_evidence_count(confidences: list[float]) -> float:
    """Computes effective evidence count:

        n_eff,k = (sum c_e,k)^2 / sum(c_e,k^2)

    Satisfies Kish's design effect formula. When all weights are identical,
    n_eff,k equals the raw count. For unequal positive weights, n_eff,k <= n_raw.
    """
    valid = [float(c) for c in confidences if c > 0.0]
    if not valid:
        return 0.0

    sum_c = sum(valid)
    sum_c_sq = sum(c * c for c in valid)

    if sum_c_sq <= 0.0:
        return 0.0

    return float((sum_c * sum_c) / sum_c_sq)


def compute_capability_score(
    evidence_records: list[EvidenceRecord],
    capability: CapabilityKey,
    config: ScoringConfig | None = None,
    ci_bounds: tuple[float | None, float | None] | None = None,
) -> CapabilityEstimate:
    """Computes capability estimate q_k, effective count, standard error, and coverage.

    If no positive confidence evidence exists:
        q_k = None (UNKNOWN)
        is_observed = False
        n_eff,k = 0.0
        coverage_k = 0.0
    """
    cfg = config or ScoringConfig()
    tau_k = cfg.tau_saturation.get(capability, 5.0)

    # Filter to evidence relevant to this capability
    relevant = [
        e
        for e in evidence_records
        if e.target_capability == capability and e.confidence > 0.0
    ]

    if not relevant:
        return CapabilityEstimate(
            capability_key=capability,
            estimate=None,
            is_observed=False,
            effective_evidence_count=0.0,
            raw_evidence_count=0,
            cluster_count=0,
            standard_error=0.0,
            dispersion=0.0,
            ci_lower=None,
            ci_upper=None,
            coverage_k=0.0,
        )

    confidences = [e.confidence for e in relevant]
    scores = [e.support_score for e in relevant]

    sum_c = sum(confidences)
    if sum_c <= 0.0:
        return CapabilityEstimate(
            capability_key=capability,
            estimate=None,
            is_observed=False,
            effective_evidence_count=0.0,
            raw_evidence_count=len(relevant),
            cluster_count=0,
            standard_error=0.0,
            dispersion=0.0,
            ci_lower=None,
            ci_upper=None,
            coverage_k=0.0,
        )

    # Capability score q_k = sum(c_e,k * z_e,k) / sum(c_e,k)
    weighted_sum = sum(c * z for c, z in zip(confidences, scores))
    q_k = float(weighted_sum / sum_c)

    # Bound to valid [0, 100]
    q_k = max(0.0, min(100.0, q_k))

    # Effective evidence count
    n_eff = compute_effective_evidence_count(confidences)

    # Weighted dispersion s_k = sqrt( sum(c * (z - q)^2) / sum(c) )
    weighted_var = (
        sum(c * ((z - q_k) ** 2) for c, z in zip(confidences, scores)) / sum_c
    )
    dispersion = math.sqrt(max(0.0, weighted_var))

    # Standard Error: SE_k = s_k / sqrt(max(1, n_eff))
    standard_error = dispersion / math.sqrt(max(1.0, n_eff))

    # Capability Coverage: Cov_k = min(1.0, sum(c) / tau_k)
    coverage_k = min(1.0, max(0.0, sum_c / tau_k))

    # Distinct clusters
    clusters = {e.cluster_id or e.source_locator for e in relevant}
    cluster_count = len(clusters)

    ci_lower = None
    ci_upper = None
    if ci_bounds is not None:
        ci_lower, ci_upper = ci_bounds

    return CapabilityEstimate(
        capability_key=capability,
        estimate=q_k,
        is_observed=True,
        effective_evidence_count=n_eff,
        raw_evidence_count=len(relevant),
        cluster_count=cluster_count,
        standard_error=standard_error,
        dispersion=dispersion,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        coverage_k=coverage_k,
    )
