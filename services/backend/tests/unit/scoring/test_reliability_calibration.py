"""Tests for Bayesian Beta-Binomial source family reliability representation and Fix 20 invariants."""

import pytest
from cci.domain.enums import ReliabilityState, SourceFamily
from cci.scoring.reliability import (
    DEFAULT_PRIOR_RATIONALES,
    DEFAULT_PRIORS,
    calibrate_from_empirical_outcomes,
    calibrate_from_observations,
    calculate_beta_mean,
    calculate_beta_variance,
    compute_source_reliability,
    get_default_reliability_snapshots,
)


def test_default_source_family_priors():
    """Verify that default priors match conference specifications, document rationale, and are marked expert priors."""
    snapshots = get_default_reliability_snapshots()
    assert len(snapshots) == 7

    # GitHub: Beta(10, 2) -> 10/12 ≈ 0.8333
    gh = snapshots[SourceFamily.GITHUB]
    assert gh.alpha_prior == 10.0
    assert gh.beta_prior == 2.0
    assert abs(gh.posterior_mean - (10.0 / 12.0)) < 1e-4
    assert gh.state == ReliabilityState.EXPERT_PRIOR
    assert gh.state == ReliabilityState.PRIOR  # Backward compatibility alias
    assert gh.is_empirically_updated is False
    assert gh.empirically_updated is False
    assert gh.empirical_sample_size == 0
    assert gh.version == "1.0.0"
    assert gh.prior_parameters == {"alpha": 10.0, "beta": 2.0}
    assert gh.is_expert_prior is True
    assert "Expert-selected prior Beta(10, 2)" in gh.rationale

    # Resume: Beta(5, 5) -> 5/10 = 0.5000
    res = snapshots[SourceFamily.RESUME]
    assert res.alpha_prior == 5.0
    assert res.beta_prior == 5.0
    assert res.posterior_mean == 0.5000
    assert res.state == ReliabilityState.EXPERT_PRIOR
    assert res.is_empirically_updated is False
    assert res.empirical_sample_size == 0
    assert "self-report bias" in res.rationale

    # Deployment: Beta(8, 2) -> 8/10 = 0.8000
    dep = snapshots[SourceFamily.DEPLOYMENT]
    assert dep.alpha_prior == 8.0
    assert dep.beta_prior == 2.0
    assert dep.posterior_mean == 0.8000
    assert dep.state == ReliabilityState.EXPERT_PRIOR
    assert dep.is_empirically_updated is False

    # Every source family has documented prior parameters and rationale
    for sf in SourceFamily:
        snap = snapshots[sf]
        assert snap.source_family == sf
        assert snap.alpha_prior > 0.0
        assert snap.beta_prior > 0.0
        assert snap.version == "1.0.0"
        assert snap.is_empirically_updated is False
        assert snap.empirical_sample_size == 0
        assert sf in DEFAULT_PRIOR_RATIONALES
        assert len(snap.rationale) > 20


def test_bayesian_posterior_updating():
    """Verify that observations update posterior mean in accordance with Bayes' rule without claiming empirical calibration."""
    # Start with GitHub prior: 10 / 12 ≈ 0.8333
    # 1. 20 consecutive true positives (e.g. simulated unit tests)
    calibrated_high = compute_source_reliability(
        source_family=SourceFamily.GITHUB,
        true_positives=20,
        false_positives=0,
    )
    expected_mean = (20.0 + 10.0) / (20.0 + 0.0 + 10.0 + 2.0)  # 30 / 32 = 0.9375
    assert abs(calibrated_high.posterior_mean - expected_mean) < 1e-4
    assert calibrated_high.state == ReliabilityState.POSTERIOR_SIMULATED
    assert calibrated_high.state == ReliabilityState.CALIBRATED  # Backward compatibility alias
    assert calibrated_high.true_positive_count == 20
    assert calibrated_high.false_positive_count == 0
    # Crucial Fix 20 invariant: simulation observations are NOT empirically calibrated
    assert calibrated_high.is_empirically_updated is False
    assert calibrated_high.empirical_sample_size == 0

    # 2. 10 false positives
    calibrated_low = compute_source_reliability(
        source_family=SourceFamily.GITHUB,
        true_positives=0,
        false_positives=10,
    )
    expected_low = (0.0 + 10.0) / (0.0 + 10.0 + 10.0 + 2.0)  # 10 / 22 ≈ 0.4545
    assert abs(calibrated_low.posterior_mean - expected_low) < 1e-4
    assert calibrated_low.state == ReliabilityState.POSTERIOR_SIMULATED
    assert calibrated_low.is_empirically_updated is False
    assert calibrated_low.empirical_sample_size == 0


def test_incremental_calibration():
    """Verify calibrate_from_observations accumulates counts properly."""
    initial = compute_source_reliability(SourceFamily.RESUME)
    assert initial.true_positive_count == 0
    assert initial.false_positive_count == 0
    assert initial.state == ReliabilityState.EXPERT_PRIOR

    step1 = calibrate_from_observations(initial, new_true_positives=5, new_false_positives=1)
    assert step1.true_positive_count == 5
    assert step1.false_positive_count == 1
    # r_s = (5 + 5) / (5 + 1 + 5 + 5) = 10 / 16 = 0.625
    assert step1.posterior_mean == 0.625
    assert step1.state == ReliabilityState.POSTERIOR_SIMULATED
    assert step1.is_empirically_updated is False

    step2 = calibrate_from_observations(step1, new_true_positives=3, new_false_positives=2)
    assert step2.true_positive_count == 8
    assert step2.false_positive_count == 3
    # r_s = (8 + 5) / (8 + 3 + 5 + 5) = 13 / 21
    assert abs(step2.posterior_mean - (13.0 / 21.0)) < 1e-4


def test_calibrate_from_empirical_outcomes():
    """Verify that calibrate_from_empirical_outcomes enforces provenance and documents empirical updates."""
    snap = calibrate_from_empirical_outcomes(
        source_family=SourceFamily.GITHUB,
        true_positives=85,
        false_positives=15,
        sample_size=100,
        calibration_provenance="dataset_industry_eval_2026_q2",
    )
    # Expected mean: (85 + 10) / (85 + 15 + 10 + 2) = 95 / 112 ≈ 0.8482
    expected_mean = 95.0 / 112.0
    assert abs(snap.posterior_mean - expected_mean) < 1e-4
    assert snap.state == ReliabilityState.EMPIRICALLY_CALIBRATED
    assert snap.is_empirically_updated is True
    assert snap.empirical_sample_size == 100
    assert snap.calibration_provenance == "dataset_industry_eval_2026_q2"
    assert "Empirically calibrated against external measured truth" in snap.rationale


def test_empirical_calibration_requires_provenance_and_sample_size():
    """Verify validation guards preventing unsupported empirical calibration claims."""
    with pytest.raises(ValueError, match="explicit calibration provenance"):
        calibrate_from_empirical_outcomes(
            source_family=SourceFamily.GITHUB,
            true_positives=10,
            false_positives=2,
            sample_size=12,
            calibration_provenance="",
        )

    with pytest.raises(ValueError, match="positive sample_size"):
        calibrate_from_empirical_outcomes(
            source_family=SourceFamily.GITHUB,
            true_positives=10,
            false_positives=2,
            sample_size=0,
            calibration_provenance="test_provenance",
        )


def test_reliability_state_enum_backward_compatibility_and_aliases():
    """Verify string deserialization and legacy aliases for ReliabilityState."""
    assert ReliabilityState("prior") == ReliabilityState.EXPERT_PRIOR
    assert ReliabilityState("EXPERT_PRIOR") == ReliabilityState.EXPERT_PRIOR
    assert ReliabilityState("calibrated") == ReliabilityState.POSTERIOR_SIMULATED
    assert ReliabilityState("simulated") == ReliabilityState.POSTERIOR_SIMULATED
    assert ReliabilityState("empirically_calibrated") == ReliabilityState.EMPIRICALLY_CALIBRATED

    assert ReliabilityState.PRIOR == ReliabilityState.EXPERT_PRIOR
    assert ReliabilityState.CALIBRATED == ReliabilityState.POSTERIOR_SIMULATED
    assert ReliabilityState.SIMULATED == ReliabilityState.POSTERIOR_SIMULATED


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

