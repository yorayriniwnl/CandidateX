"""Unit tests validating frozen domain contracts, enums, and mathematical primitives."""

import warnings

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

    input_values = {key: value for key, value in base.items() if key != "observed_score"}
    assert (
        EvidenceInput(**input_values, technical_signal_strength=55.0).observed_score
        == 55.0
    )
    assert (
        EvidenceInput(**input_values, observed_score=55.0).technical_signal_strength
        == 55.0
    )
    with pytest.raises(ValidationError):
        EvidenceInput(
            **input_values, technical_signal_strength=55.0, observed_score=56.0
        )


def test_evidence_input_signal_rule_pair_must_match_registry():
    base = {
        "source_family": SourceFamily.GITHUB,
        "source_locator": "https://github.com/acme/api",
        "immutable_revision": "a" * 40,
        "target_capability": CapabilityKey.BACKEND_ENGINEERING,
        "technical_signal_strength": 55.0,
        "raw_support_text": "async function",
        "extractor_version": "test-v1",
    }
    rule_id = "candidatex.code.python.async_function"
    valid = EvidenceInput(
        **base, signal_rule_id=rule_id, signal_rule_version="1.0.0"
    )
    assert valid.signal_rule_id == rule_id
    for extra in (
        {"signal_rule_id": rule_id},
        {"signal_rule_version": "1.0.0"},
        {"signal_rule_id": rule_id, "signal_rule_version": "2.0.0"},
    ):
        with pytest.raises(ValidationError):
            EvidenceInput(**base, **extra)


def test_evidence_record_score_aliases_and_legacy_provenance():
    base = {
        "fingerprint": "a" * 64,
        "source_family": SourceFamily.GITHUB,
        "source_locator": "https://github.com/acme/api",
        "immutable_revision": "a" * 40,
        "target_capability": CapabilityKey.BACKEND_ENGINEERING,
        "confidence_factors": EvidenceConfidenceFactors(
            artifact_integrity=1.0,
            ownership_score=1.0,
            recency_factor=1.0,
            verification_level=1.0,
            depth_specificity=1.0,
            source_reliability=1.0,
        ),
        "confidence": 1.0,
        "provenance": {"file": "api.py"},
    }
    for score_key in ("technical_signal_strength", "support_score"):
        record = EvidenceRecord(**base, **{score_key: 55.0})
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter("always", DeprecationWarning)
            serialized = record.model_dump(mode="json")
            assert record.support_score == 55.0
        assert not [
            warning for warning in emitted
            if issubclass(warning.category, DeprecationWarning)
        ]
        assert serialized["technical_signal_strength"] == 55.0
        assert serialized["support_score"] == 55.0
        assert serialized["provenance"] == {
            "file": "api.py",
            "signal_rule_id": "legacy_unknown",
            "signal_rule_version": "legacy_unknown",
        }
    with pytest.raises(ValidationError):
        EvidenceRecord(**base, technical_signal_strength=55.0, support_score=56.0)
    schema = EvidenceRecord.model_json_schema(mode="serialization")
    assert schema["properties"]["support_score"]["deprecated"] is True


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


def _negative_details(scope_kind="artifact", **scope_overrides):
    scope = {
        "scope_kind": scope_kind,
        "repository_scope": "acme/api",
        "pinned_revision": "a" * 40,
        "artifact_paths": ["coverage.xml"],
        "category": "coverage_report",
        "scope_version": "candidatex.negative-scan-scope/1.0.0",
    }
    scope.update(scope_overrides)
    return {
        "claim_reference": "cr1:" + "b" * 64,
        "candidate_type": "candidatex.contradiction.coverage_below_claim",
        "expected_observation": "At least 95% line coverage",
        "actual_observation": "Pinned coverage.xml reports 71% line coverage",
        "scan_scope": scope,
        "required_scan_completeness": 1.0,
        "observed_scan_completeness": 1.0,
        "explanation": "The pinned report states 71%, below the claimed 95%.",
    }


def _negative_input_base():
    return {
        "source_family": SourceFamily.GITHUB,
        "source_locator": "https://github.com/acme/api",
        "immutable_revision": "a" * 40,
        "target_capability": CapabilityKey.TESTING_QUALITY,
        "technical_signal_strength": 70.0,
        "raw_support_text": "coverage.xml line-rate=0.71",
        "extractor_version": "contradiction-v1",
    }


def _negative_record_base():
    return {
        "fingerprint": "a" * 64,
        "source_family": SourceFamily.GITHUB,
        "source_locator": "https://github.com/acme/api",
        "immutable_revision": "a" * 40,
        "target_capability": CapabilityKey.TESTING_QUALITY,
        "technical_signal_strength": 70.0,
        "confidence_factors": EvidenceConfidenceFactors(
            artifact_integrity=1.0,
            ownership_score=1.0,
            recency_factor=1.0,
            verification_level=1.0,
            depth_specificity=1.0,
            source_reliability=1.0,
        ),
        "confidence": 1.0,
        "is_positive_support": False,
    }


def test_new_negative_evidence_requires_details():
    with pytest.raises(ValidationError, match="negative evidence"):
        EvidenceInput(**_negative_input_base(), is_positive_support=False)


def test_qualified_negative_input_requires_matching_registered_rule():
    details = _negative_details()
    base = _negative_input_base()
    with pytest.raises(ValidationError):
        EvidenceInput(**base, is_positive_support=False, negative_evidence_details=details)
    with pytest.raises(ValidationError):
        EvidenceInput(
            **base,
            is_positive_support=False,
            negative_evidence_details=details,
            signal_rule_id="candidatex.contradiction.framework_usage_absent",
            signal_rule_version="1.0.0",
        )
    qualified = EvidenceInput(
        **base,
        is_positive_support=False,
        negative_evidence_details=details,
        signal_rule_id=details["candidate_type"],
        signal_rule_version="1.0.0",
    )
    assert qualified.model_dump(mode="json")["negative_evidence_qualification"] == "qualified"


def test_negative_detail_scope_is_strict_and_synthetic_scope_is_not_production():
    base = _negative_input_base()
    rule_id = "candidatex.contradiction.coverage_below_claim"
    for details in (
        _negative_details(extra_scope_field=True),
        _negative_details(scope_kind="synthetic"),
        {**_negative_details(), "observed_scan_completeness": 1.1},
    ):
        with pytest.raises(ValidationError):
            EvidenceInput(
                **base,
                is_positive_support=False,
                negative_evidence_details=details,
                signal_rule_id=rule_id,
                signal_rule_version="1.0.0",
            )
    with pytest.raises(ValidationError):
        EvidenceInput(**base, negative_evidence_details=_negative_details())


def test_historical_negative_record_loads_as_legacy_unqualified():
    record = EvidenceRecord(**_negative_record_base())
    assert record.negative_evidence_details is None
    assert record.negative_evidence_qualification == "legacy_unqualified"
    assert record.model_dump(mode="json")["negative_evidence_qualification"] == "legacy_unqualified"


def test_positive_record_serializes_null_negative_qualification():
    record = EvidenceRecord(**{**_negative_record_base(), "is_positive_support": True})
    assert record.model_dump(mode="json")["negative_evidence_qualification"] is None
    with pytest.raises(ValidationError):
        EvidenceRecord(
            **{**_negative_record_base(), "is_positive_support": True},
            negative_evidence_details=_negative_details(),
        )


def test_positive_input_serialization_preserves_legacy_fingerprint_payload():
    serialized = EvidenceInput(**_negative_input_base()).model_dump(
        mode="json", exclude={"observed_at", "signal_rule_id", "signal_rule_version"}
    )
    assert "negative_evidence_details" not in serialized
    assert "negative_evidence_qualification" not in serialized


def test_synthetic_negative_record_requires_synthetic_provenance():
    details = _negative_details(
        scope_kind="synthetic", repository_scope=None,
        pinned_revision=None, artifact_paths=[], category=None,
    )
    record = EvidenceRecord(
        **_negative_record_base(),
        negative_evidence_details=details,
        provenance={"synthetic": True},
    )
    assert record.negative_evidence_qualification == "qualified"
    assert record.provenance["synthetic"] is True
    with pytest.raises(ValidationError):
        EvidenceRecord(
            **_negative_record_base(),
            negative_evidence_details=details,
            provenance={},
        )


def test_production_qualified_record_requires_matching_rule_provenance():
    details = _negative_details()
    for provenance in ({}, {"signal_rule_id": "candidatex.code.python.async_function", "signal_rule_version": "1.0.0"}):
        with pytest.raises(ValidationError):
            EvidenceRecord(
                **_negative_record_base(),
                negative_evidence_details=details,
                provenance=provenance,
            )
    record = EvidenceRecord(
        **_negative_record_base(),
        negative_evidence_details=details,
        provenance={"signal_rule_id": details["candidate_type"], "signal_rule_version": "1.0.0"},
    )
    assert record.model_dump(mode="json")["negative_evidence_details"]["claim_reference"] == details["claim_reference"]
