"""Tests for Bayesian Beta-Binomial source family reliability calibration."""

import pytest
from cci.domain.enums import ReliabilityState, SourceFamily
from cci.scoring.reliability import (
    calibrate_from_observations,
    calculate_beta_mean,
    calculate_beta_variance,
    compute_source_reliability,
    get_default_reliability_snapshots,
)


def test_default_source_family_priors():
    """Verify that default priors match the conference paper specifications."""
    snapshots = get_default_reliability_snapshots()
    assert len(snapshots) == 7

    # GitHub: Beta(10, 2) -> 10/12 ≈ 0.8333
    gh = snapshots[SourceFamily.GITHUB]
    assert gh.alpha_prior == 10.0
    assert gh.beta_prior == 2.0
    assert abs(gh.posterior_mean - (10.0 / 12.0)) < 1e-4
    assert gh.state == ReliabilityState.PRIOR

    # Resume: Beta(5, 5) -> 5/10 = 0.5000
    res = snapshots[SourceFamily.RESUME]
    assert res.alpha_prior == 5.0
    assert res.beta_prior == 5.0
    assert res.posterior_mean == 0.5000
    assert res.state == ReliabilityState.PRIOR

    # Deployment: Beta(8, 2) -> 8/10 = 0.8000
    dep = snapshots[SourceFamily.DEPLOYMENT]
    assert dep.alpha_prior == 8.0
    assert dep.beta_prior == 2.0
    assert dep.posterior_mean == 0.8000


def test_bayesian_posterior_updating():
    """Verify that observations update posterior mean in accordance with Bayes' rule."""
    # Start with GitHub prior: 10 / 12 ≈ 0.8333
    # 1. 20 consecutive true positives (e.g. verified unit tests in code)
    calibrated_high = compute_source_reliability(
        source_family=SourceFamily.GITHUB,
        true_positives=20,
        false_positives=0,
    )
    expected_mean = (20.0 + 10.0) / (20.0 + 0.0 + 10.0 + 2.0)  # 30 / 32 = 0.9375
    assert abs(calibrated_high.posterior_mean - expected_mean) < 1e-4
    assert calibrated_high.state == ReliabilityState.CALIBRATED
    assert calibrated_high.true_positive_count == 20
    assert calibrated_high.false_positive_count == 0

    # 2. 10 false positives (e.g. uncompilable or plagiarized artifacts)
    calibrated_low = compute_source_reliability(
        source_family=SourceFamily.GITHUB,
        true_positives=0,
        false_positives=10,
    )
    expected_low = (0.0 + 10.0) / (0.0 + 10.0 + 10.0 + 2.0)  # 10 / 22 ≈ 0.4545
    assert abs(calibrated_low.posterior_mean - expected_low) < 1e-4
    assert calibrated_low.state == ReliabilityState.CALIBRATED


def test_incremental_calibration():
    """Verify calibrate_from_observations accumulates counts properly."""
    initial = compute_source_reliability(SourceFamily.RESUME)
    assert initial.true_positive_count == 0
    assert initial.false_positive_count == 0

    step1 = calibrate_from_observations(initial, new_true_positives=5, new_false_positives=1)
    assert step1.true_positive_count == 5
    assert step1.false_positive_count == 1
    # r_s = (5 + 5) / (5 + 1 + 5 + 5) = 10 / 16 = 0.625
    assert step1.posterior_mean == 0.625

    step2 = calibrate_from_observations(step1, new_true_positives=3, new_false_positives=2)
    assert step2.true_positive_count == 8
    assert step2.false_positive_count == 3
    # r_s = (8 + 5) / (8 + 3 + 5 + 5) = 13 / 21
    assert abs(step2.posterior_mean - (13.0 / 21.0)) < 1e-4


def test_beta_variance_reduction():
    """Verify that collecting more observations monotonically reduces posterior uncertainty/variance."""
    var_prior = calculate_beta_variance(0, 0, 10.0, 2.0)
    var_5 = calculate_beta_variance(5, 0, 10.0, 2.0)
    var_50 = calculate_beta_variance(50, 0, 10.0, 2.0)

    assert var_prior > var_5 > var_50
    assert var_50 > 0.0


def test_invalid_calibration_inputs():
    with pytest.raises(ValueError, match="non-negative"):
        compute_source_reliability(SourceFamily.GITHUB, true_positives=-1)

    with pytest.raises(ValueError, match="strictly positive"):
        compute_source_reliability(SourceFamily.GITHUB, alpha_prior=0.0)
