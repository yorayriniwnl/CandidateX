"""Tests for the backend's canonical evidence coverage state policy."""

import pytest

from cci.domain.coverage_policy import (
    classify_evidence_state,
    is_coverage_sufficient,
)
from cci.domain.enums import EvidenceState


@pytest.mark.parametrize(
    ("coverage", "expected"),
    [
        (0.0, EvidenceState.INSUFFICIENT),
        (0.3499, EvidenceState.INSUFFICIENT),
        (0.35, EvidenceState.SPARSE),
        (0.4999, EvidenceState.SPARSE),
        (0.5, EvidenceState.MODERATE),
        (0.7499, EvidenceState.MODERATE),
        (0.75, EvidenceState.SUBSTANTIAL),
        (1.0, EvidenceState.SUBSTANTIAL),
    ],
)
def test_evidence_state_uses_one_threshold_and_documented_bands(coverage, expected):
    assert classify_evidence_state(coverage, sufficiency_threshold=0.35) == expected


def test_configured_threshold_overrides_sparse_band_and_missing_is_unknown():
    assert (
        classify_evidence_state(0.55, sufficiency_threshold=0.6)
        == EvidenceState.INSUFFICIENT
    )
    assert classify_evidence_state(None, sufficiency_threshold=0.35) == EvidenceState.UNKNOWN


def test_state_uses_coverage_and_threshold_as_the_only_sufficiency_inputs():
    assert (
        classify_evidence_state(0.8, sufficiency_threshold=0.35)
        == EvidenceState.SUBSTANTIAL
    )


def test_missing_coverage_is_never_sufficient():
    assert is_coverage_sufficient(None, threshold=0.35) is False
    assert is_coverage_sufficient(0.35, threshold=0.35) is True
    assert is_coverage_sufficient(0.3499, threshold=0.35) is False
