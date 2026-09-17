"""Tests for Monte Carlo candidate cohort simulation."""

from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.research.simulation import generate_synthetic_cohort


def test_deterministic_seed_reproducibility():
    """Verify that using the same seed produces identical candidates and observations."""
    cohort_a = generate_synthetic_cohort(role=CanonicalRole.BACKEND, count=20, seed=42)
    cohort_b = generate_synthetic_cohort(role=CanonicalRole.BACKEND, count=20, seed=42)

    assert len(cohort_a) == len(cohort_b) == 20

    for ca, cb in zip(cohort_a, cohort_b):
        # Ground truth capabilities must match exactly
        for cap in CapabilityKey:
            assert ca.ground_truth_capabilities[cap] == cb.ground_truth_capabilities[cap]

        assert len(ca.observations) == len(cb.observations)
        for oa, ob in zip(ca.observations, cb.observations):
            assert oa.observed_score == ob.observed_score
            assert oa.ownership_score == ob.ownership_score
            assert oa.elapsed_years == ob.elapsed_years


def test_different_seeds_produce_different_cohorts():
    """Verify that different random seeds produce statistically distinct candidate profiles."""
    cohort_1 = generate_synthetic_cohort(role=CanonicalRole.BACKEND, count=10, seed=100)
    cohort_2 = generate_synthetic_cohort(role=CanonicalRole.BACKEND, count=10, seed=200)

    scores_1 = [c.ground_truth_capabilities[CapabilityKey.BACKEND_ENGINEERING] for c in cohort_1]
    scores_2 = [c.ground_truth_capabilities[CapabilityKey.BACKEND_ENGINEERING] for c in cohort_2]

    assert scores_1 != scores_2


def test_role_specific_capability_profiles():
    """Verify that role-specific capabilities are elevated for their respective roles."""
    backend_cohort = generate_synthetic_cohort(role=CanonicalRole.BACKEND, count=50, seed=1)
    frontend_cohort = generate_synthetic_cohort(role=CanonicalRole.FRONTEND, count=50, seed=1)

    avg_be_in_backend = sum(c.ground_truth_capabilities[CapabilityKey.BACKEND_ENGINEERING] for c in backend_cohort) / 50.0
    avg_be_in_frontend = sum(c.ground_truth_capabilities[CapabilityKey.BACKEND_ENGINEERING] for c in frontend_cohort) / 50.0

    avg_fe_in_backend = sum(c.ground_truth_capabilities[CapabilityKey.FRONTEND_ENGINEERING] for c in backend_cohort) / 50.0
    avg_fe_in_frontend = sum(c.ground_truth_capabilities[CapabilityKey.FRONTEND_ENGINEERING] for c in frontend_cohort) / 50.0

    # Backend engineers have higher backend scores than frontend engineers
    assert avg_be_in_backend > avg_be_in_frontend
    # Frontend engineers have higher frontend scores than backend engineers
    assert avg_fe_in_frontend > avg_fe_in_backend
