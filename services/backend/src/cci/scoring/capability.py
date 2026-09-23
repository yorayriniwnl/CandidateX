"""Capability estimate, effective evidence count, dispersion, and coverage."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from cci.domain.contracts import CapabilityEstimate, EvidenceRecord, ScoringConfig
from cci.domain.coverage_policy import is_coverage_sufficient
from cci.domain.evidence_families import normalize_source_cluster
from cci.domain.enums import CapabilityKey
from cci.scoring.evidence_families import compute_record_family_weights


@dataclass(frozen=True)
class EvidenceCoverageItem:
    """One artifact's strongest evidence quality inside an independence cluster."""

    cluster_key: str
    artifact_key: str
    evidence_quality: float


def build_evidence_coverage_item(
    *,
    source_family: object,
    source_locator: str,
    confidence: float,
    cluster_id: str | None = None,
    artifact_id: object | None = None,
    artifact_hash: str | None = None,
    artifact_path: str | None = None,
    fingerprint: str | None = None,
) -> EvidenceCoverageItem:
    """Builds stable source and artifact identities for coverage calculations."""
    cluster_key = normalize_source_cluster(source_family, cluster_id or source_locator)
    content_hash = (artifact_hash or "").strip().casefold()
    if content_hash:
        artifact_key = f"content:{content_hash}"
    elif artifact_path:
        normalized_path = artifact_path.replace("\\", "/").strip("/")
        artifact_key = f"path:{cluster_key}:{normalized_path}"
    elif artifact_id is not None:
        artifact_key = f"id:{cluster_key}:{artifact_id}"
    elif fingerprint:
        artifact_key = f"evidence:{cluster_key}:{fingerprint}"
    else:
        artifact_key = f"source:{cluster_key}"

    return EvidenceCoverageItem(
        cluster_key=cluster_key,
        artifact_key=artifact_key,
        evidence_quality=max(0.0, min(1.0, float(confidence))),
    )


def evidence_coverage_item(
    record: EvidenceRecord,
    confidence: float | None = None,
) -> EvidenceCoverageItem:
    """Extracts a coverage identity from a persisted evidence record."""
    provenance = record.provenance
    return build_evidence_coverage_item(
        source_family=record.source_family,
        source_locator=record.source_locator,
        confidence=record.confidence if confidence is None else confidence,
        cluster_id=record.cluster_id,
        artifact_id=record.artifact_id,
        artifact_hash=provenance.get("artifact_sha256")
        or provenance.get("content_sha256"),
        artifact_path=provenance.get("artifact_path"),
        fingerprint=record.fingerprint,
    )


def _deduplicate_coverage_items(
    items: Iterable[EvidenceCoverageItem],
) -> list[EvidenceCoverageItem]:
    """Keeps the strongest instance of each artifact across all source clusters."""
    strongest: dict[str, EvidenceCoverageItem] = {}
    for item in items:
        if item.evidence_quality <= 0.0:
            continue
        current = strongest.get(item.artifact_key)
        if current is None or (item.evidence_quality, item.cluster_key) > (
            current.evidence_quality,
            current.cluster_key,
        ):
            strongest[item.artifact_key] = item
    return [strongest[key] for key in sorted(strongest)]


def deduplicate_records_by_artifact(
    records: Iterable[EvidenceRecord],
) -> list[EvidenceRecord]:
    """Returns deterministic strongest representatives for independent artifacts."""
    by_artifact: dict[str, tuple[EvidenceCoverageItem, EvidenceRecord]] = {}
    for record in records:
        item = evidence_coverage_item(record)
        if item.evidence_quality <= 0.0:
            continue
        current = by_artifact.get(item.artifact_key)
        rank = (item.evidence_quality, item.cluster_key, record.fingerprint)
        if current is None or rank > (
            current[0].evidence_quality,
            current[0].cluster_key,
            current[1].fingerprint,
        ):
            by_artifact[item.artifact_key] = (item, record)
    return [by_artifact[key][1] for key in sorted(by_artifact)]


def compute_cluster_aware_coverage(
    items: Iterable[EvidenceCoverageItem],
    tau_saturation: float,
    artifact_decay: float = 0.5,
) -> tuple[float, int]:
    """Computes coverage from independent clusters and unique artifacts.

    Within each cluster, each artifact contributes its strongest attribution-gated
    evidence quality once. Distinct artifacts are sorted by quality and receive
    geometrically diminishing weight, so one cluster contributes less than
    ``1 / (1 - artifact_decay)`` units. Content-identical artifacts across
    clusters are credited only to the strongest deterministic representative.
    """
    unique_items = _deduplicate_coverage_items(items)
    qualities_by_cluster: dict[str, list[float]] = {}
    for item in unique_items:
        qualities_by_cluster.setdefault(item.cluster_key, []).append(
            item.evidence_quality
        )

    total_cluster_mass = 0.0
    for qualities in qualities_by_cluster.values():
        for rank, quality in enumerate(sorted(qualities, reverse=True)):
            total_cluster_mass += quality * (artifact_decay**rank)

    if tau_saturation <= 0.0:
        return 0.0, len(qualities_by_cluster)

    coverage = min(1.0, max(0.0, total_cluster_mass / tau_saturation))
    return coverage, len(qualities_by_cluster)


def has_sufficient_candidate_evidence(
    coverage_k: float,
    config: ScoringConfig | None = None,
) -> bool:
    """Whether attribution-gated evidence is sufficient to emit a candidate score."""
    cfg = config or ScoringConfig()
    return is_coverage_sufficient(
        coverage_k, threshold=cfg.low_coverage_threshold
    )


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
    family_weights: Mapping[UUID, float] | None = None,
) -> CapabilityEstimate:
    """Computes capability estimate q_k, effective count, standard error, and coverage.

    If no positive confidence evidence exists, or attribution-gated coverage is
    below the configured minimum:
        q_k = None (UNKNOWN)
        is_observed = False
        The evidence count and coverage remain visible when evidence exists.
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

    if family_weights is None:
        family_weights = compute_record_family_weights(
            relevant, decay=cfg.evidence_family_decay
        )
    confidences = [
        e.confidence * family_weights[e.evidence_id] for e in relevant
    ]
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

    coverage_k, cluster_count = compute_cluster_aware_coverage(
        (
            evidence_coverage_item(record, confidence)
            for record, confidence in zip(relevant, confidences)
        ),
        tau_k,
        cfg.cluster_artifact_decay,
    )
    has_sufficient_evidence = has_sufficient_candidate_evidence(coverage_k, cfg)

    ci_lower = None
    ci_upper = None
    if ci_bounds is not None:
        ci_lower, ci_upper = ci_bounds

    return CapabilityEstimate(
        capability_key=capability,
        estimate=q_k if has_sufficient_evidence else None,
        is_observed=has_sufficient_evidence,
        effective_evidence_count=n_eff,
        raw_evidence_count=len(relevant),
        cluster_count=cluster_count,
        standard_error=standard_error,
        dispersion=dispersion,
        ci_lower=ci_lower if has_sufficient_evidence else None,
        ci_upper=ci_upper if has_sufficient_evidence else None,
        coverage_k=coverage_k,
    )
