"""Cluster bootstrap confidence interval implementation."""

from collections import defaultdict
from collections.abc import Mapping
from uuid import UUID

import numpy as np

from cci.domain.contracts import EvidenceRecord, ScoringConfig
from cci.domain.enums import CapabilityKey
from cci.scoring.capability import evidence_coverage_item
from cci.scoring.evidence_families import compute_record_family_weights


def cluster_bootstrap_ci(
    evidence_records: list[EvidenceRecord],
    capability: CapabilityKey,
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int | None = 42,
    config: ScoringConfig | None = None,
    family_weights: Mapping[UUID, float] | None = None,
) -> tuple[float | None, float | None]:
    """Calculates non-parametric cluster bootstrap confidence intervals for q_k.

    When at least 2 distinct clusters exist, clusters are resampled with replacement.
    When cluster count < 2, an interval is not estimable and is returned as unknown.
    Deterministic when seed is provided.

    Returns:
        (ci_lower, ci_upper) tuple clamped to [0.0, 100.0], or (None, None) if no evidence.
    """
    cfg = config or ScoringConfig()
    relevant_records = [
        e
        for e in evidence_records
        if e.target_capability == capability and e.confidence > 0.0
    ]
    if not relevant_records:
        return None, None

    if family_weights is None:
        family_weights = compute_record_family_weights(
            relevant_records, decay=cfg.evidence_family_decay
        )

    # Preserve the historical content/artifact deduplication while letting
    # independent observation modalities and polarities contribute separately.
    strongest_by_artifact_observation = {}
    for record in relevant_records:
        effective_confidence = record.confidence * family_weights[record.evidence_id]
        if effective_confidence <= 0.0:
            continue
        coverage_item = evidence_coverage_item(record, effective_confidence)
        key = (
            coverage_item.artifact_key,
            record.observation_type,
            record.is_positive_support,
        )
        rank = (
            effective_confidence,
            coverage_item.cluster_key,
            record.fingerprint,
            str(record.evidence_id),
        )
        current = strongest_by_artifact_observation.get(key)
        if current is None or rank > current[0]:
            strongest_by_artifact_observation[key] = (
                rank,
                record,
                effective_confidence,
                coverage_item,
            )

    weighted_records = [
        (record, effective_confidence, coverage_item)
        for (
            _,
            record,
            effective_confidence,
            coverage_item,
        ) in strongest_by_artifact_observation.values()
    ]
    if not weighted_records:
        return None, None

    # Use the same source-family and cluster identity as capability coverage.
    clusters = defaultdict(list)
    for record, effective_confidence, coverage_item in weighted_records:
        clusters[coverage_item.cluster_key].append((record, effective_confidence))

    cluster_keys = sorted(clusters)
    k_clusters = len(cluster_keys)

    # Base estimate
    total_c = sum(
        effective_confidence
        for _, effective_confidence, _ in weighted_records
    )
    if total_c <= 0.0:
        return None, None

    base_q = sum(
        effective_confidence * record.technical_signal_strength
        for record, effective_confidence, _ in weighted_records
    ) / total_c

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
            for rec, effective_confidence in clusters[c_key]:
                sample_sum_cz += effective_confidence * rec.technical_signal_strength
                sample_sum_c += effective_confidence

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
