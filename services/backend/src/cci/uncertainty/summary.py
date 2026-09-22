"""Conservative, deterministic evidence-strength summaries."""

from collections import Counter
from collections.abc import Mapping, Sequence

from cci.domain.contracts import (
    AnalysisConfidenceSummary,
    CapabilityConflict,
    CapabilityEstimate,
    EvidenceRecord,
    RoleFitSummary,
    ScoringConfig,
)
from cci.domain.enums import CapabilityKey

LIMITED_COVERAGE = 0.60
WELL_SUPPORTED_COVERAGE = 0.80
WELL_SUPPORTED_INTERVAL_COVERAGE = 0.80
WELL_SUPPORTED_MAX_INTERVAL_WIDTH = 25.0
WELL_SUPPORTED_MIN_CLUSTERS = 3


def _bounded_nonnegative_int(value: int) -> int:
    return max(0, int(value))


def _flag_explanation(flags: list[str], band: str, clusters: int) -> str:
    if band == "insufficient":
        return "No positive-confidence empirical evidence supports a broad assessment."
    if band == "well_supported":
        return (
            "Evidence is well supported across the supplied artifacts and independent "
            f"clusters ({clusters}); this is not a probability or hiring recommendation."
        )

    labels = {
        "low_role_coverage": "role coverage is low",
        "single_cluster": "evidence comes from fewer than two independent clusters",
        "interval_unavailable": "some observed capabilities do not have estimable intervals",
        "wide_intervals": "available intervals are wide",
        "mandatory_unknown": "mandatory requirements remain unknown",
        "mandatory_unresolved": "mandatory requirements remain unmapped",
        "source_failures": "one or more supplied sources failed",
        "source_unscanned": "one or more supplied sources were not scanned",
        "meaningful_conflict": "positive and negative evidence conflict",
        "unusable_evidence": "some retained evidence has zero usable confidence",
    }
    reasons = [labels.get(flag, flag.replace("_", " ")) for flag in flags]
    if not reasons:
        reasons = [
            "the selected coverage and support gates are not all met"
        ]
    return f"Evidence strength is {band}; limiting factors: " + "; ".join(reasons) + "."


def build_analysis_confidence(
    *,
    capabilities: Mapping[CapabilityKey, CapabilityEstimate],
    evidence_records: Sequence[EvidenceRecord],
    role_weights: Mapping[CapabilityKey, float],
    conflicts: Mapping[CapabilityKey, CapabilityConflict],
    role_fit: RoleFitSummary,
    config: ScoringConfig | None = None,
    source_failures: int = 0,
    source_unscanned: int = 0,
) -> AnalysisConfidenceSummary:
    """Derive bounded evidence-strength metadata; never return a probability."""

    cfg = config or ScoringConfig()
    observed = {
        capability: estimate
        for capability, estimate in capabilities.items()
        if estimate.is_observed and estimate.estimate is not None
    }
    role_coverage = sum(
        role_weights.get(capability, 0.0) * estimate.coverage_k
        for capability, estimate in capabilities.items()
    )
    role_coverage = max(0.0, min(1.0, float(role_coverage)))

    observed_role_weight = sum(
        max(0.0, role_weights.get(capability, 0.0))
        for capability in observed
    )
    interval_capabilities = {
        capability: estimate
        for capability, estimate in observed.items()
        if estimate.ci_lower is not None and estimate.ci_upper is not None
    }
    interval_role_weight = sum(
        max(0.0, role_weights.get(capability, 0.0))
        for capability in interval_capabilities
    )
    interval_coverage = (
        interval_role_weight / observed_role_weight
        if observed_role_weight > 0.0
        else 0.0
    )
    interval_coverage = max(0.0, min(1.0, float(interval_coverage)))
    interval_widths = [
        float(estimate.ci_upper - estimate.ci_lower)
        for estimate in interval_capabilities.values()
    ]
    maximum_interval_width = max(interval_widths) if interval_widths else None

    usable_records = [record for record in evidence_records if record.confidence > 0.0]
    independent_clusters = len(
        {record.cluster_id or record.source_locator for record in usable_records}
    )
    unusable_records = [
        record for record in evidence_records if record.confidence <= 0.0
    ]
    usable_by_capability = Counter(record.target_capability for record in usable_records)
    unusable_by_capability = Counter(
        record.target_capability for record in unusable_records
    )
    material_unusable = any(
        role_weights.get(capability, 0.0) > 0.0
        and unusable_by_capability[capability] > 0
        and (
            usable_by_capability[capability] == 0
            or unusable_by_capability[capability]
            >= usable_by_capability[capability]
        )
        for capability in set(usable_by_capability) | set(unusable_by_capability)
    )

    meaningful_conflicts = sum(
        1 for conflict in conflicts.values() if conflict.has_meaningful_conflict
    )
    source_failures = _bounded_nonnegative_int(source_failures)
    source_unscanned = _bounded_nonnegative_int(source_unscanned)
    flags: list[str] = []

    if not observed:
        flags.append("no_empirical_evidence")
    if role_coverage < cfg.low_coverage_threshold:
        flags.append("low_role_coverage")
    if observed and independent_clusters < 2:
        flags.append("single_cluster")
    if observed and interval_coverage < 1.0:
        flags.append("interval_unavailable")
    if (
        maximum_interval_width is not None
        and maximum_interval_width > WELL_SUPPORTED_MAX_INTERVAL_WIDTH
    ):
        flags.append("wide_intervals")
    if role_fit.mandatory_unknown > 0:
        flags.append("mandatory_unknown")
    if role_fit.mandatory_unresolved > 0:
        flags.append("mandatory_unresolved")
    if source_failures > 0:
        flags.append("source_failures")
    if source_unscanned > 0:
        flags.append("source_unscanned")
    if meaningful_conflicts > 0:
        flags.append("meaningful_conflict")
    if material_unusable:
        flags.append("unusable_evidence")

    limited_flags = {
        "single_cluster",
        "interval_unavailable",
        "mandatory_unknown",
        "mandatory_unresolved",
        "source_failures",
        "source_unscanned",
        "unusable_evidence",
    }
    if not observed or role_coverage < cfg.low_coverage_threshold:
        band = "insufficient"
    elif (
        role_coverage < LIMITED_COVERAGE
        or any(flag in limited_flags for flag in flags)
    ):
        band = "limited"
    elif (
        role_coverage < WELL_SUPPORTED_COVERAGE
        or independent_clusters < WELL_SUPPORTED_MIN_CLUSTERS
        or interval_coverage < WELL_SUPPORTED_INTERVAL_COVERAGE
        or maximum_interval_width is None
        or maximum_interval_width > WELL_SUPPORTED_MAX_INTERVAL_WIDTH
        or meaningful_conflicts > 0
    ):
        band = "moderate"
    else:
        band = "well_supported"

    return AnalysisConfidenceSummary(
        evidence_strength=band,
        explanation=_flag_explanation(flags, band, independent_clusters),
        uncertainty_flags=flags,
        role_coverage=role_coverage,
        observed_capabilities=len(observed),
        independent_clusters=independent_clusters,
        capabilities_with_intervals=len(interval_capabilities),
        interval_coverage=interval_coverage,
        maximum_interval_width=maximum_interval_width,
        meaningful_conflicts=meaningful_conflicts,
        mandatory_unknown=max(0, role_fit.mandatory_unknown),
        mandatory_unresolved=max(0, role_fit.mandatory_unresolved),
        source_failures=source_failures,
        source_unscanned=source_unscanned,
        unusable_evidence_records=len(unusable_records),
    )
