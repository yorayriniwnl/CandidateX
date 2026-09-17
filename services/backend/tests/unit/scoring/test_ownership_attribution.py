"""Tests for candidate ownership attribution and 6-factor confidence composition."""

import pytest
from cci.domain.contracts import EvidenceConfidenceFactors, OwnershipAssessment
from cci.scoring.ownership import (
    assemble_confidence_factors,
    estimate_repository_ownership,
)


def test_solo_repository_ownership():
    """Solo author repositories must receive full ownership attribution."""
    assessment = estimate_repository_ownership(
        repository_url="https://github.com/alice/personal-project",
        candidate_identifier="alice",
        candidate_commits=45,
        total_commits=45,
        candidate_lines=3200,
        total_lines=3200,
        is_fork=False,
        is_owner=True,
    )
    assert assessment.ownership_score >= 0.95
    assert assessment.is_fork is False
    assert assessment.attribution_confidence >= 0.90


def test_fork_with_zero_candidate_commits():
    """CRITICAL SECURITY INVARIANT: Fork with zero candidate commits must be penalized to <= 0.10."""
    assessment = estimate_repository_ownership(
        repository_url="https://github.com/alice/torvalds-linux-fork",
        candidate_identifier="alice",
        candidate_commits=0,
        total_commits=50000,
        is_fork=True,
        is_owner=True,
    )
    assert assessment.ownership_score <= 0.10
    assert assessment.is_fork is True
    assert any("zero candidate commits" in lim for lim in assessment.limitations)


def test_fork_with_candidate_commits():
    """Fork with candidate commits should receive proportional attribution capped at 0.70."""
    assessment = estimate_repository_ownership(
        repository_url="https://github.com/alice/upstream-fork",
        candidate_identifier="alice",
        candidate_commits=20,
        total_commits=100,
        is_fork=True,
        is_owner=True,
    )
    assert 0.15 <= assessment.ownership_score <= 0.70
    assert any("capped at 0.70" in lim for lim in assessment.limitations)


def test_vendor_artifact_ownership():
    """Auto-generated or vendor code must receive minimal ownership attribution."""
    assessment = estimate_repository_ownership(
        repository_url="https://github.com/alice/app",
        candidate_identifier="alice",
        is_vendor_or_generated=True,
    )
    assert assessment.ownership_score <= 0.05
    assert assessment.is_vendor_or_generated is True


def test_collaborative_multi_contributor_ownership():
    """Multi-contributor project weights commits, lines, and repository ownership."""
    assessment = estimate_repository_ownership(
        repository_url="https://github.com/team/shared-app",
        candidate_identifier="alice",
        candidate_commits=30,
        total_commits=100,      # 30% commits
        candidate_lines=4000,
        total_lines=10000,      # 40% lines
        is_fork=False,
        is_owner=False,
    )
    # Expected weighted: 0.6 * 0.3 + 0.4 * 0.4 = 0.18 + 0.16 = 0.34
    assert 0.30 <= assessment.ownership_score <= 0.40
    assert assessment.feature_vector["commit_ratio"] == 0.30
    assert assessment.feature_vector["line_ratio"] == 0.40


def test_six_factor_confidence_composition():
    """Verify formal paper formula: c_e,k = (a * o * t * v * x * r)^(1/6)."""
    factors = assemble_confidence_factors(
        artifact_integrity=1.0,     # a = 1.0
        ownership_score=0.90,       # o = 0.9
        recency_factor=0.80,        # t = 0.8
        verification_level=1.0,     # v = 1.0
        depth_specificity=0.85,     # x = 0.85
        source_reliability=0.833,   # r = 0.833
    )

    expected_product = 1.0 * 0.90 * 0.80 * 1.0 * 0.85 * 0.833
    expected_c = expected_product ** (1.0 / 6.0)

    assert abs(factors.composite_confidence - expected_c) < 1e-4
    assert 0.0 <= factors.composite_confidence <= 1.0

    # If any factor is 0, composite confidence must be 0
    zero_factors = assemble_confidence_factors(ownership_score=0.0)
    assert zero_factors.composite_confidence == 0.0
