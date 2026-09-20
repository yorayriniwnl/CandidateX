"""Tests for calibration of static live-source evidence."""

from cci.scoring.live_evidence import (
    estimate_declared_commit_ownership,
    live_confidence_profile,
)


def test_small_commit_samples_are_shrunk_before_becoming_ownership():
    one_commit, one_confidence = estimate_declared_commit_ownership(
        candidate_commits=1,
        total_commits=1,
        identity_supplied=True,
        is_fork=False,
    )
    sustained, sustained_confidence = estimate_declared_commit_ownership(
        candidate_commits=30,
        total_commits=30,
        identity_supplied=True,
        is_fork=False,
    )

    assert 0.0 < one_commit < sustained
    assert one_confidence < sustained_confidence
    assert estimate_declared_commit_ownership(0, 30, True, False) == (0.0, 0.0)
    assert estimate_declared_commit_ownership(30, 30, False, False) == (0.0, 0.0)


def test_fork_ownership_remains_capped_after_sample_calibration():
    ownership, confidence = estimate_declared_commit_ownership(30, 30, True, True)

    assert ownership == 0.5
    assert confidence > 0.0


def test_correlated_live_observations_have_diminishing_confidence():
    first_verification, first_depth = live_confidence_profile("source_usage", 1)
    second_verification, second_depth = live_confidence_profile("source_usage", 2)
    dependency_verification, dependency_depth = live_confidence_profile(
        "dependency_declaration", 1
    )

    assert second_verification < first_verification
    assert second_depth < first_depth
    assert dependency_verification < first_verification
    assert dependency_depth < first_depth
