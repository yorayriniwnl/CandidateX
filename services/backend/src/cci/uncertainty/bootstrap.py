"""Cluster bootstrap confidence interval implementation."""

from collections import defaultdict

import numpy as np

from cci.domain.contracts import EvidenceRecord
from cci.domain.enums import CapabilityKey
from cci.scoring.capability import (
    deduplicate_records_by_artifact,
    evidence_coverage_item,
)


def cluster_bootstrap_ci(
    evidence_records: list[EvidenceRecord],
    capability: CapabilityKey,
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int | None = 42,
) -> tuple[float | None, float | None]:
    """Calculates non-parametric cluster bootstrap confidence intervals for q_k.

    When at least 2 distinct clusters exist, clusters are resampled with replacement.
    When cluster count < 2, an interval is not estimable and is returned as unknown.
    Deterministic when seed is provided.

    Returns:
        (ci_lower, ci_upper) tuple clamped to [0.0, 100.0], or (None, None) if no evidence.
    """
    relevant = [
        e
        for e in evidence_records
        if e.target_capability == capability and e.confidence > 0.0
    ]
    relevant = deduplicate_records_by_artifact(relevant)
    if not relevant:
        return None, None

    # Use the same source-family and cluster identity as capability coverage.
    clusters = defaultdict(list)
    for e in relevant:
        clusters[evidence_coverage_item(e).cluster_key].append(e)

    cluster_keys = list(clusters.keys())
    k_clusters = len(cluster_keys)

    # Base estimate
    total_c = sum(e.confidence for e in relevant)
    if total_c <= 0.0:
        return None, None

    base_q = sum(e.confidence * e.support_score for e in relevant) / total_c

    # One project cannot establish sampling uncertainty across projects.
    if k_clusters < 2:
        return None, None

    # Non-parametric cluster bootstrap
    rng = np.random.RandomState(seed)
    boot_estimates = []

    for _ in range(n_resamples):
        sampled_cluster_indices = rng.choice(k_clusters, size=k_clusters, replace=True)

        sample_sum_cz = 0.0
        sample_sum_c = 0.0

        for idx in sampled_cluster_indices:
            c_key = cluster_keys[idx]
            for rec in clusters[c_key]:
                sample_sum_cz += rec.confidence * rec.support_score
                sample_sum_c += rec.confidence

        if sample_sum_c > 0.0:
            boot_estimates.append(sample_sum_cz / sample_sum_c)
        else:
            boot_estimates.append(base_q)

    alpha = 1.0 - confidence_level
    lower_pct = 100.0 * (alpha / 2.0)
    upper_pct = 100.0 * (1.0 - (alpha / 2.0))

    ci_lower = float(np.percentile(boot_estimates, lower_pct))
    ci_upper = float(np.percentile(boot_estimates, upper_pct))

    return max(0.0, min(100.0, ci_lower)), max(0.0, min(100.0, ci_upper))
