"""Unit tests validating frozen domain contracts, enums, and mathematical primitives."""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from cci.domain.enums import (
    AnalysisStage,
    AnalysisStatus,
    CanonicalRole,
    CapabilityKey,
    ClaimStatus,
    EvidenceState,
    GraphEdgeType,
    GraphNodeType,
    RequirementPriority,
    RequirementStatus,
    ScanDepth,
    SourceFamily,
    SourceState,
)
from cci.domain.contracts import (
    AnalysisScore,
    CandidateManifest,
    CapabilityConflict,
    CapabilityEstimate,
    CapabilityUncertainty,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceInput,
    EvidenceRecord,
    InterviewQuestion,
    NormalizedRequirement,
    OwnershipAssessment,
    ProbePriority,
    RoleProfile,
    ScoringConfig,
    SourceReliabilitySnapshot,
)
from cci.api.contracts.analyses import AnalysisTriggerRequest
from cci.api.contracts.evidence import EvidenceDetailResponse


def test_canonical_roles_exact_six():
    """Acceptance gate: exactly 6 canonical roles must be defined."""
    expected_roles = {
        "backend",
        "frontend",
        "fullstack",
        "ml_engineer",
        "devops_cloud",
        "data_engineer",
    }
    actual_roles = {r.value for r in CanonicalRole}
    assert actual_roles == expected_roles, f"Expected 6 canonical roles, got: {actual_roles}"
    assert len(CanonicalRole) == 6


def test_capability_keys_exact_twelve():
    """Acceptance gate: exactly 12 capability keys must be defined."""
    expected_capabilities = {
        "backend_engineering",
        "frontend_engineering",
        "database_engineering",
        "devops_cloud",
        "machine_learning",
        "data_engineering",
        "algorithms_problem_solving",
        "testing_quality",
        "security",
        "software_architecture",
        "collaboration",
        "documentation_communication",
    }
    actual_capabilities = {c.value for c in CapabilityKey}
    assert actual_capabilities == expected_capabilities, f"Expected 12 capabilities, got: {actual_capabilities}"
    assert len(CapabilityKey) == 12


def test_pipeline_stages_coverage():
    """Validate pipeline stages match formal pipeline specification."""
    expected_stages = {
        "PARSING_CV",
        "INGESTING_SOURCES",
        "ANALYZING_ARTIFACTS",
        "BUILDING_EVIDENCE",
        "CALIBRATING_RELIABILITY",
        "ESTIMATING_OWNERSHIP",
        "COMPUTING_UNCERTAINTY",
        "SCORING",
        "PRIORITIZING_PROBES",
        "GENERATING_DOSSIER",
    }
    actual_stages = {s.value for s in AnalysisStage}
    assert actual_stages == expected_stages


def test_source_families_exact_seven():
    """Validate 7 source families from research design."""
    expected_families = {
        "resume",
        "github",
        "deployment",
        "database",
        "coding",
        "certificate",
        "linkedin",
    }
    actual_families = {sf.value for sf in SourceFamily}
    assert actual_families == expected_families
    assert len(SourceFamily) == 7


def test_confidence_factors_attribution_gate_formula():
    """Verify c_e,k = o * (a * t * v * x * r)^(1/5)."""
    # When all factors are 1.0, confidence is 1.0
    factors_all_one = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    assert pytest.approx(factors_all_one.composite_confidence, rel=1e-5) == 1.0

    # The five quality factors combine separately; attribution gates their mean.
    factors = EvidenceConfidenceFactors(
        artifact_integrity=0.8,
        ownership_score=0.9,
        recency_factor=0.7,
        verification_level=0.6,
        depth_specificity=0.5,
        source_reliability=0.85,
    )
    quality_product = 0.8 * 0.7 * 0.6 * 0.5 * 0.85
    expected = 0.9 * quality_product ** (1.0 / 5.0)
    assert pytest.approx(factors.composite_confidence, rel=1e-5) == expected
    assert pytest.approx(factors.evidence_quality, rel=1e-5) == quality_product ** (1.0 / 5.0)

    # Confidence must fall to 0 if any single factor is 0
    factors_zero = EvidenceConfidenceFactors(
        artifact_integrity=0.0,
        ownership_score=0.9,
        recency_factor=0.7,
        verification_level=0.6,
        depth_specificity=0.5,
        source_reliability=0.85,
    )
    assert factors_zero.composite_confidence == 0.0


def test_candidate_manifest_validation():
    """Verify CandidateManifest validation and immutability."""
    manifest = CandidateManifest(
        display_name="Alice Candidate",
        email="alice@example.com",
        github_urls=["https://github.com/alice/project1"],
        project_links=["https://alice.dev/proj"],
        claimed_skills=["Python", "FastAPI", "PostgreSQL"],
    )
    assert manifest.display_name == "Alice Candidate"
    assert len(manifest.claimed_skills) == 3

    # Frozen model should reject attribute mutation
    with pytest.raises(ValidationError):
        manifest.display_name = "Bob"  # type: ignore


def test_role_profile_weights_sum_to_one():
    """RoleProfile weights w_k must sum to 1.0."""
    equal_weight = 1.0 / 12.0
    weights = {cap: equal_weight for cap in CapabilityKey}
    importances = {cap: 1.0 for cap in CapabilityKey}

    profile = RoleProfile(
        canonical_role=CanonicalRole.BACKEND,
        raw_importances=importances,
        softmax_weights=weights,
    )
    assert profile.canonical_role == CanonicalRole.BACKEND
    assert pytest.approx(sum(profile.softmax_weights.values()), rel=1e-4) == 1.0

    # Reject invalid weights that do not sum to 1.0
    bad_weights = {cap: 0.5 for cap in CapabilityKey}
    with pytest.raises(ValidationError):
        RoleProfile(
            canonical_role=CanonicalRole.BACKEND,
            raw_importances=importances,
            softmax_weights=bad_weights,
        )


def test_capability_estimate_observed_vs_missing():
    """Check CapabilityEstimate for observed vs missing capability."""
    # Missing / UNKNOWN capability has estimate=None
    missing = CapabilityEstimate(
        capability_key=CapabilityKey.MACHINE_LEARNING,
        estimate=None,
        is_observed=False,
        effective_evidence_count=0.0,
        raw_evidence_count=0,
        coverage_k=0.0,
    )
    assert missing.estimate is None
    assert not missing.is_observed

    # Observed capability
    observed = CapabilityEstimate(
        capability_key=CapabilityKey.BACKEND_ENGINEERING,
        estimate=82.5,
        is_observed=True,
        effective_evidence_count=4.8,
        raw_evidence_count=6,
        cluster_count=2,
        coverage_k=0.96,
        standard_error=3.2,
        dispersion=7.0,
        ci_lower=76.0,
        ci_upper=88.5,
    )
    assert observed.estimate == 82.5
    assert observed.is_observed
    assert observed.coverage_k == 0.96


def test_scoring_config_defaults():
    """Validate versioned scoring configuration parameters."""
    config = ScoringConfig()
    assert config.version == "5.1.0"
    assert config.temperature == 1.0
    assert config.jd_max_logit_adjustment == 1.5
    assert config.jd_adjustment_saturation == 2.0
    assert config.jd_requirement_group_decay == 0.5
    assert config.min_role_weight == 0.01
    assert config.max_role_weight == 0.40
    assert config.low_coverage_threshold == 0.35
    assert config.cluster_artifact_decay == 0.5
    assert config.evidence_family_decay == 0.5
    assert config.probe_alpha + config.probe_beta + config.probe_gamma == 1.0
    assert len(config.lambda_decay) == 12
    assert len(config.tau_saturation) == 12


def test_cluster_artifact_decay_must_be_less_than_one():
    with pytest.raises(ValueError):
        ScoringConfig(cluster_artifact_decay=1.0)


def test_evidence_family_decay_accepts_zero_but_rejects_one():
    assert ScoringConfig(evidence_family_decay=0.0).evidence_family_decay == 0.0
    with pytest.raises(ValidationError):
        ScoringConfig(evidence_family_decay=1.0)


def test_role_weight_bounds_and_temperature_are_validated():
    with pytest.raises(ValidationError):
        ScoringConfig(temperature=0.49)
    with pytest.raises(ValidationError):
        ScoringConfig(min_role_weight=0.10)
    with pytest.raises(ValidationError):
        ScoringConfig(max_role_weight=0.08)


def test_analysis_and_dossier_versions_default_to_scoring_v5_1():
    request = AnalysisTriggerRequest(
        candidate_id=uuid4(),
        target_role=CanonicalRole.BACKEND,
    )
    dossier = Dossier(
        candidate_id=uuid4(),
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
        coverage=0.0,
        is_insufficient_evidence=True,
        capability_estimates={},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
    )

    assert request.scoring_config_version == "5.1.0"
    assert dossier.versions["scoring_config_version"] == "5.1.0"
    assert dossier.observed_capability_index is None
    assert dossier.evidence_state == EvidenceState.INSUFFICIENT
    assert dossier.observed_index_context.evidence_state == EvidenceState.INSUFFICIENT
    assert dossier.observed_index_context.unique_independent_source_cluster_count is None
    assert dossier.observed_index_context.mean_path_attribution_confidence is None
    assert dossier.observed_index_context.path_attribution_sample_count == 0
    assert dossier.observed_index_context.standalone_presentation_allowed is False


def test_evidence_family_fields_default_for_existing_constructors():
    evidence_input = EvidenceInput(
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/acme/api",
        immutable_revision="a" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        observed_score=55.0,
        raw_support_text="dependency declared",
        extractor_version="test-v1",
    )
    confidence_factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    evidence_record = EvidenceRecord(
        fingerprint="a" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/acme/api",
        immutable_revision="a" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=55.0,
        confidence_factors=confidence_factors,
        confidence=1.0,
    )

    assert evidence_input.evidence_family_id is None
    assert evidence_input.observation_type == "legacy_unknown"
    assert evidence_input.evidence_family_basis == {}
    assert evidence_record.evidence_family_id is None
    assert evidence_record.observation_type == "legacy_unknown"
    assert evidence_record.evidence_family_basis == {}


def test_evidence_family_contracts_reject_values_outside_storage_limits():
    base = {
        "source_family": SourceFamily.GITHUB,
        "source_locator": "https://github.com/acme/api",
        "immutable_revision": "a" * 40,
        "target_capability": CapabilityKey.BACKEND_ENGINEERING,
        "observed_score": 55.0,
        "raw_support_text": "dependency declared",
        "extractor_version": "test-v1",
    }

    with pytest.raises(ValidationError):
        EvidenceInput(**base, observation_type="x" * 101)
    with pytest.raises(ValidationError):
        EvidenceInput(**base, evidence_family_id="ef1:" + "a" * 65)


def test_evidence_detail_response_serializes_family_and_scope_metadata():
    record = EvidenceRecord(
        fingerprint="a" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/acme/api",
        immutable_revision="b" * 40,
        artifact_id=uuid4(),
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=75.0,
        confidence_factors=EvidenceConfidenceFactors(
            artifact_integrity=1.0,
            ownership_score=1.0,
            recency_factor=1.0,
            verification_level=1.0,
            depth_specificity=1.0,
            source_reliability=1.0,
        ),
        confidence=0.8,
        cluster_id="https://github.com/acme/api",
        evidence_family_id="ef1:" + "c" * 64,
        observation_type="route:python_decorator",
        evidence_family_basis={"schema": "ef1", "domain": "route"},
    )

    serialized = EvidenceDetailResponse(record=record).model_dump(mode="json")[
        "record"
    ]

    assert serialized["evidence_family_id"] == record.evidence_family_id
    assert serialized["observation_type"] == "route:python_decorator"
    assert serialized["cluster_id"] == "https://github.com/acme/api"
    assert serialized["artifact_id"] == str(record.artifact_id)
