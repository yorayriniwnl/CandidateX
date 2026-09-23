"""Unit tests for paper ablation study engine."""

from uuid import uuid4

from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.research.ablation import (
    AblationMode,
    evaluate_candidate_ablation,
    run_ablation_evaluation,
)
from cci.research.simulation import (
    SimulatedCandidate,
    SimulatedObservation,
    generate_synthetic_cohort,
)


def test_ablation_does_not_score_weakly_attributed_capability():
    capability = CapabilityKey.BACKEND_ENGINEERING

    def candidate_with_attribution(ownership: float) -> SimulatedCandidate:
        observations = [
            SimulatedObservation(
                capability_key=capability,
                observed_score=90.0,
                ownership_score=ownership,
                elapsed_years=0.0,
                artifact_integrity=1.0,
                verification_level=1.0,
                depth_specificity=1.0,
                source_family=SourceFamily.GITHUB,
                cluster_id=f"repo-{index}",
                source_locator=f"https://github.com/example/repo-{index}",
                artifact_id=f"repo-{index}:src/service.py",
            )
            for index in range(3)
        ]
        return SimulatedCandidate(
            candidate_id=uuid4(),
            role=CanonicalRole.BACKEND,
            ground_truth_capabilities={capability: 90.0},
            observations=observations,
            seed=1,
        )

    role_weights = {capability: 1.0}
    strong_rci, _, strong_estimates = evaluate_candidate_ablation(
        candidate_with_attribution(1.0),
        AblationMode.FULL_CCI,
        role_weights,
    )
    weak_rci, _, weak_estimates = evaluate_candidate_ablation(
        candidate_with_attribution(0.03),
        AblationMode.FULL_CCI,
        role_weights,
    )

    assert strong_rci == 90.0
    assert strong_estimates[capability] == 90.0
    assert weak_rci is None
    assert weak_estimates == {}


def test_ablation_does_not_count_duplicate_hits_in_one_artifact_as_coverage():
    capability = CapabilityKey.BACKEND_ENGINEERING
    observations = [
        SimulatedObservation(
            capability_key=capability,
            observed_score=90.0,
            ownership_score=1.0,
            elapsed_years=0.0,
            artifact_integrity=1.0,
            verification_level=1.0,
            depth_specificity=1.0,
            source_family=SourceFamily.GITHUB,
            cluster_id="repo-a",
            source_locator="https://github.com/example/repo-a",
            artifact_id="repo-a:src/service.py",
        )
        for _ in range(20)
    ]
    candidate = SimulatedCandidate(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        ground_truth_capabilities={capability: 90.0},
        observations=observations,
        seed=1,
    )

    rci, _, estimates = evaluate_candidate_ablation(
        candidate, AblationMode.FULL_CCI, {capability: 1.0}
    )

    assert rci is None
    assert estimates == {}


def test_ablation_does_not_count_identical_artifact_copies_as_independent():
    capability = CapabilityKey.BACKEND_ENGINEERING
    observations = [
        SimulatedObservation(
            capability_key=capability,
            observed_score=90.0,
            ownership_score=1.0,
            elapsed_years=0.0,
            artifact_integrity=1.0,
            verification_level=1.0,
            depth_specificity=1.0,
            source_family=SourceFamily.GITHUB,
            cluster_id=f"repo-{index}",
            source_locator=f"https://github.com/example/repo-{index}",
            artifact_hash="same-content-hash",
        )
        for index in range(2)
    ]
    candidate = SimulatedCandidate(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        ground_truth_capabilities={capability: 90.0},
        observations=observations,
        seed=1,
    )

    rci, _, estimates = evaluate_candidate_ablation(
        candidate, AblationMode.FULL_CCI, {capability: 1.0}
    )

    assert rci is None
    assert estimates == {}


def test_ablation_evaluations_run_cleanly():
    """Verify all 5 paper ablation modes execute and compute metrics on simulated cohort."""
    cohort = generate_synthetic_cohort(role=CanonicalRole.BACKEND, count=40, seed=42)

    results = {}
    for mode in AblationMode:
        metrics = run_ablation_evaluation(cohort=cohort, mode=mode, role=CanonicalRole.BACKEND)
        results[mode] = metrics
        assert "rci_mae" in metrics
        assert "rci_rmse" in metrics
        assert "spearman_rho" in metrics
        assert "kendall_tau" in metrics
        assert metrics["sample_count"] > 0
        assert 0.0 <= metrics["rci_mae"] <= 100.0

    # Full CCI ranking correlation is positive and substantial
    full_metrics = results[AblationMode.FULL_CCI]
    assert full_metrics["spearman_rho"] > 0.40
    assert full_metrics["kendall_tau"] > 0.30
