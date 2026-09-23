"""Tests for Monte Carlo candidate cohort simulation."""

from uuid import NAMESPACE_URL, uuid5

from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.research.scenarios import DemoRequest, evidence_digest, make_scenario
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
            assert oa.evidence_id == ob.evidence_id
            assert oa.evidence_family_id == ob.evidence_family_id
            assert oa.observation_type == ob.observation_type
            assert oa.fingerprint == ob.fingerprint
            assert oa.semantic_subject == ob.semantic_subject
            assert oa.cluster_id == ob.cluster_id
            assert oa.artifact_id == ob.artifact_id


def test_interactive_scenarios_emit_repeatable_family_metadata():
    request = DemoRequest(
        candidate_id=uuid5(NAMESPACE_URL, "scenario-candidate"),
        scenario="consistent",
    )

    first, _ = make_scenario(request)
    repeated, _ = make_scenario(request)

    assert first
    assert [record.evidence_id for record in first] == [
        record.evidence_id for record in repeated
    ]
    assert [record.evidence_family_id for record in first] == [
        record.evidence_family_id for record in repeated
    ]
    assert evidence_digest(first) == evidence_digest(repeated)
    assert all(record.evidence_family_id.startswith("ef1:") for record in first)
    assert all(record.observation_type.startswith("simulation:") for record in first)
    assert all(record.cluster_id and record.artifact_id for record in first)
    assert all(
        record.provenance["evidence_family_basis"]["domain"] == "simulation"
        for record in first
    )
    changed_identity = first[0].model_copy(
        update={"evidence_family_id": "ef1:" + "b" * 64}
    )
    assert evidence_digest([changed_identity, *first[1:]]) != evidence_digest(first)


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
