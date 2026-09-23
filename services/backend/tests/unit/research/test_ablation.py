"""Unit tests for paper ablation study engine."""

from uuid import NAMESPACE_URL, uuid4, uuid5

from cci.domain.contracts import ScoringConfig
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
from cci.scoring.evidence_families import (
    EvidenceFamilyWeightInput,
    compute_evidence_family_weights,
)


def _synthetic_observation(
    name: str,
    *,
    capability: CapabilityKey,
    score: float,
    family_id: str,
    observation_type: str,
    cluster_id: str,
    artifact_id: str,
    ownership_score: float = 1.0,
    artifact_hash: str | None = None,
) -> SimulatedObservation:
    fingerprint = name.ljust(64, "0")[:64]
    return SimulatedObservation(
        capability_key=capability,
        observed_score=score,
        ownership_score=ownership_score,
        elapsed_years=0.0,
        artifact_integrity=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_family=SourceFamily.GITHUB,
        evidence_id=uuid5(NAMESPACE_URL, f"evidence:{name}"),
        evidence_family_id=family_id,
        observation_type=observation_type,
        fingerprint=fingerprint,
        semantic_subject="service-api",
        evidence_family_basis={
            "schema": "ef1",
            "domain": "simulation",
            "subject": "service-api",
        },
        cluster_id=cluster_id,
        source_locator=f"https://github.com/example/{cluster_id}",
        artifact_id=artifact_id,
        artifact_hash=artifact_hash,
    )


def test_ablation_does_not_score_weakly_attributed_capability():
    capability = CapabilityKey.BACKEND_ENGINEERING

    def candidate_with_attribution(ownership: float) -> SimulatedCandidate:
        observations = [
            _synthetic_observation(
                f"ownership-{index}",
                capability=capability,
                score=90.0,
                family_id=f"ownership-family-{index}",
                observation_type="simulation:capability_score",
                cluster_id=f"repo-{index}",
                artifact_id=f"repo-{index}:src/service.py",
                ownership_score=ownership,
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
        _synthetic_observation(
            f"duplicate-{index}",
            capability=capability,
            score=90.0,
            family_id="duplicate-family",
            observation_type="simulation:capability_score",
            cluster_id="repo-a",
            artifact_id="repo-a:src/service.py",
        )
        for index in range(20)
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
        _synthetic_observation(
            f"copy-{index}",
            capability=capability,
            score=90.0,
            family_id=f"copy-family-{index}",
            observation_type="simulation:capability_score",
            cluster_id=f"repo-{index}",
            artifact_hash="same-content-hash",
            artifact_id=f"artifact-{index}",
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


def test_ablation_applies_the_same_family_weights_as_live_scoring():
    capability = CapabilityKey.BACKEND_ENGINEERING
    family_id = "ef1:" + "a" * 64
    cluster_id = "example-repo"
    observations = [
        _synthetic_observation(
            "manifest-a",
            capability=capability,
            score=90.0,
            family_id=family_id,
            observation_type="simulation:manifest",
            cluster_id=cluster_id,
            artifact_id="artifact-a",
        ),
        _synthetic_observation(
            "manifest-z",
            capability=capability,
            score=50.0,
            family_id=family_id,
            observation_type="simulation:manifest",
            cluster_id=cluster_id,
            artifact_id="artifact-z",
        ),
        _synthetic_observation(
            "route-r",
            capability=capability,
            score=100.0,
            family_id=family_id,
            observation_type="simulation:route",
            cluster_id=cluster_id,
            artifact_id="artifact-r",
        ),
    ]
    config = ScoringConfig(
        evidence_family_decay=0.25,
        tau_saturation={capability: 1.0},
    )
    family_weights = compute_evidence_family_weights(
        [
            EvidenceFamilyWeightInput(
                evidence_id=observation.evidence_id,
                evidence_family_id=observation.evidence_family_id,
                observation_type=observation.observation_type,
                is_positive_support=True,
                confidence=0.8,
                fingerprint=observation.fingerprint,
            )
            for observation in observations
        ],
        decay=config.evidence_family_decay,
    )
    expected = sum(
        family_weights[observation.evidence_id] * observation.observed_score
        for observation in observations
    ) / sum(family_weights.values())
    candidate = SimulatedCandidate(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        ground_truth_capabilities={capability: expected},
        observations=observations,
        seed=42,
    )

    _, _, estimates = evaluate_candidate_ablation(
        candidate,
        AblationMode.FULL_CCI,
        {capability: 1.0},
        config=config,
    )

    assert family_weights[observations[0].evidence_id] == 0.0
    assert family_weights[observations[1].evidence_id] == 1.0
    assert family_weights[observations[2].evidence_id] == 0.25
    assert estimates[capability] == expected


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
