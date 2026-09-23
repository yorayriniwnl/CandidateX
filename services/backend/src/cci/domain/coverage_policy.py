"""Canonical evidence coverage sufficiency and descriptive state policy."""

from cci.domain.enums import EvidenceState

DEFAULT_COVERAGE_SUFFICIENCY_THRESHOLD = 0.35


def is_coverage_sufficient(
    coverage: float | None,
    *,
    threshold: float,
) -> bool:
    """Returns False for missing coverage and otherwise applies the configured gate."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Coverage threshold must be in the range [0, 1]")
    if coverage is None:
        return False
    if not 0.0 <= coverage <= 1.0:
        raise ValueError("Coverage must be in the range [0, 1]")
    return coverage >= threshold


def classify_evidence_state(
    coverage: float | None,
    *,
    sufficiency_threshold: float,
) -> EvidenceState:
    """Classifies coverage without treating missing values as sufficient.

    The configured sufficiency threshold is the only boundary for insufficient
    evidence. Above it, fixed descriptive bands distinguish sparse, moderate,
    and substantial coverage; those labels are not candidate-quality ratings.
    """
    if not 0.0 <= sufficiency_threshold <= 1.0:
        raise ValueError("Coverage threshold must be in the range [0, 1]")
    if coverage is None:
        return EvidenceState.UNKNOWN
    if not is_coverage_sufficient(coverage, threshold=sufficiency_threshold):
        return EvidenceState.INSUFFICIENT
    if coverage < 0.50:
        return EvidenceState.SPARSE
    if coverage < 0.75:
        return EvidenceState.MODERATE
    return EvidenceState.SUBSTANTIAL
