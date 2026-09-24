"""Integration test for database repository persistence, seeding, and invariant preservation."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cci.db.base import Base
import cci.db.models as models
import cci.db.repository as repo
from cci.domain.contracts import (
    CandidateManifest,
    ArtifactRecency,
    CapabilityEstimate,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    ScoringConfig,
)
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.pipeline.orchestrator import execute_analysis_pipeline


@pytest.fixture
def memory_db():
    """In-memory SQLite database session for fast, isolated repository tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    repo.init_db(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_repository_organization_and_user_creation(memory_db):
    """Verifies creation and retrieval of multi-tenant Organization and User entities."""
    org = repo.save_organization(
        session=memory_db,
        name="Test Corp",
        slug="test-corp",
        settings={"env": "testing"},
    )
    assert org.id is not None
    assert org.name == "Test Corp"

    # Idempotency check: saving same slug returns existing
    org_duplicate = repo.save_organization(
        session=memory_db,
        name="Test Corp",
        slug="test-corp",
    )
    assert org_duplicate.id == org.id

    user = repo.save_user(
        session=memory_db,
        organization_id=org.id,
        email="interviewer@testcorp.com",
        full_name="Interviewer One",
    )
    assert user.id is not None
    assert user.organization_id == org.id

    # User idempotency check
    user_duplicate = repo.save_user(
        session=memory_db,
        organization_id=org.id,
        email="interviewer@testcorp.com",
        full_name="Interviewer One",
    )
    assert user_duplicate.id == user.id


def test_repository_candidate_and_job_description(memory_db):
    """Verifies candidate manifest and job description persistence."""
    org = repo.save_organization(memory_db, "Acme", "acme")

    manifest = CandidateManifest(
        display_name="Jane Doe",
        email="jane@example.com",
        github_urls=["https://github.com/janedoe/core-engine"],
        claimed_skills=["Python", "PostgreSQL", "Distributed Systems"],
    )

    candidate = repo.save_candidate(
        session=memory_db,
        organization_id=org.id,
        manifest=manifest,
    )
    assert candidate.display_name == "Jane Doe"
    assert candidate.primary_email == "jane@example.com"

    # Query candidate back
    fetched = repo.get_candidate_by_id(memory_db, candidate.id)
    assert fetched is not None
    assert fetched.display_name == "Jane Doe"

    candidates_list = repo.list_candidates(memory_db, org.id)
    assert len(candidates_list) == 1
    assert candidates_list[0].id == candidate.id

    from cci.jobs.parser import extract_requirements_from_jd
    from cci.scoring.weights import build_role_profile

    jd_text = "Requires Python, PostgreSQL, and distributed architectures."
    requirements = extract_requirements_from_jd(jd_text)
    role_profile = build_role_profile(
        requirements,
        CanonicalRole.BACKEND,
        ScoringConfig(temperature=0.5),
    )

    # Save job description and verify the exact profile temperature is retained.
    jd = repo.save_job_description(
        session=memory_db,
        organization_id=org.id,
        title="Senior Backend Engineer",
        canonical_role=CanonicalRole.BACKEND,
        raw_text=jd_text,
        role_profile=role_profile,
        requirements=requirements,
    )
    assert jd.id is not None
    assert jd.canonical_role == "backend"
    saved_profile = memory_db.query(models.RoleProfileEntity).one()
    assert saved_profile.temperature_used == 0.5

    jobs = repo.list_jobs(memory_db, org.id)
    assert len(jobs) == 1
    assert jobs[0].id == jd.id


def test_repository_dossier_persistence_and_reconstruction(memory_db):
    """Verifies full execution pipeline run persistence and Dossier reconstruction."""
    org = repo.save_organization(memory_db, "Dossier Test Org", "dossier-test-org")

    candidate_id = uuid.uuid4()
    manifest = CandidateManifest(
        display_name="Alice Engineer",
        email="alice@eng.io",
        github_urls=["https://github.com/alice/service"],
    )
    repo.save_candidate(memory_db, org.id, manifest, candidate_id=candidate_id)

    # Run analysis pipeline
    state = execute_analysis_pipeline(
        candidate_id=candidate_id,
        role=CanonicalRole.BACKEND,
        jd_text="Senior Backend Engineer with Python and PostgreSQL",
        cv_text="# Alice Engineer\nSenior backend engineer.",
    )
    assert state.dossier is not None

    # Persist dossier
    snapshot = repo.save_dossier(memory_db, state.dossier, org.id)
    memory_db.commit()

    assert snapshot.id == state.dossier.dossier_id

    # Retrieve and reconstruct Dossier from database
    loaded_dossier = repo.get_dossier_by_candidate_id(memory_db, candidate_id)
    assert loaded_dossier is not None
    assert loaded_dossier.candidate_id == candidate_id
    assert loaded_dossier.role == CanonicalRole.BACKEND
    assert loaded_dossier.dossier_id == state.dossier.dossier_id
    assert len(loaded_dossier.interview_probes) > 0


def test_repository_uses_dossier_coverage_threshold_for_uncertainty_and_gaps(memory_db):
    org = repo.save_organization(memory_db, "Coverage Policy Org", "coverage-policy")
    candidate_id = uuid.uuid4()
    run_id = uuid.uuid4()
    capability = CapabilityKey.BACKEND_ENGINEERING
    estimate = CapabilityEstimate(
        capability_key=capability,
        estimate=60.0,
        is_observed=True,
        effective_evidence_count=1.0,
        raw_evidence_count=1,
        cluster_count=1,
        coverage_k=0.4,
    )
    dossier = Dossier(
        candidate_id=candidate_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.4,
        coverage_sufficiency_threshold=0.5,
        is_insufficient_evidence=True,
        capability_estimates={capability: estimate},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
    )

    repo.save_dossier(
        memory_db,
        dossier,
        org.id,
        scoring_config=ScoringConfig(low_coverage_threshold=0.5),
    )

    uncertainty = memory_db.query(models.CapabilityUncertaintyEntity).one()
    gap = (
        memory_db.query(models.DossierItem)
        .filter_by(section_type="uncertain_area")
        .one()
    )
    assert uncertainty.is_low_coverage is True
    assert capability.value in gap.body_markdown
    assert "Low Coverage" in gap.body_markdown
    snapshot = memory_db.query(models.DossierSnapshot).one()
    assert snapshot.summary_payload["coverage_sufficiency_threshold"] == 0.5
    assert snapshot.summary_payload["evidence_state"] == "INSUFFICIENT"


def test_evidence_immutability_in_repository(memory_db):
    """Enforces that evidence records saved through the repository layer cannot be modified."""
    org = repo.save_organization(memory_db, "Audit Org", "audit-org")
    candidate_id = uuid.uuid4()
    manifest = CandidateManifest(display_name="Immutability Subject")
    repo.save_candidate(memory_db, org.id, manifest, candidate_id=candidate_id)

    run = repo.save_analysis_run(memory_db, candidate_id, CanonicalRole.BACKEND, org.id)
    memory_db.flush()

    cf = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    ev_record = EvidenceRecord(
        evidence_id=uuid.uuid4(),
        fingerprint="fp_immutability_test_001",
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/test/repo",
        immutable_revision="abc1234",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=90.0,
        confidence_factors=cf,
        confidence=1.0,
        provenance={"test": "data"},
    )

    ev_entities = repo.save_evidence_records(
        memory_db, run.id, [ev_record], ScoringConfig()
    )
    memory_db.commit()

    assert len(ev_entities) == 1
    ev_entity = ev_entities[0]

    # Attempt mutation
    ev_entity.support_score = 99.9
    with pytest.raises(ValueError, match="Immutable entity 'Evidence'.*cannot be modified"):
        memory_db.commit()


def test_repository_persists_family_metadata_weights_and_active_config(memory_db):
    org = repo.save_organization(memory_db, "Family Org", "family-org")
    candidate_id = uuid.uuid4()
    repo.save_candidate(
        memory_db,
        org.id,
        CandidateManifest(display_name="Family Candidate"),
        candidate_id=candidate_id,
    )
    family_id = "ef1:" + "a" * 64
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    records = [
        EvidenceRecord(
            evidence_id=uuid.uuid4(),
            fingerprint="a" * 64,
            source_family=SourceFamily.GITHUB,
            source_locator="https://github.com/acme/family",
            immutable_revision="b" * 40,
            target_capability=CapabilityKey.BACKEND_ENGINEERING,
            technical_signal_strength=80.0,
            confidence_factors=factors,
            confidence=0.8,
            cluster_id="https://github.com/acme/family",
            evidence_family_id=family_id,
            observation_type="dependency:manifest",
            evidence_family_basis={"schema": "ef1", "domain": "dependency"},
            artifact_recency=ArtifactRecency(
                state="known",
                last_meaningful_modification_at=datetime(2023, 6, 1, tzinfo=timezone.utc),
                last_meaningful_revision_sha="d" * 40,
                repository_last_activity=datetime(2026, 9, 22, tzinfo=timezone.utc),
            ),
            provenance={"artifact_path": "requirements.txt"},
        ),
        EvidenceRecord(
            evidence_id=uuid.uuid4(),
            fingerprint="c" * 64,
            source_family=SourceFamily.GITHUB,
            source_locator="https://github.com/acme/family",
            immutable_revision="b" * 40,
            target_capability=CapabilityKey.BACKEND_ENGINEERING,
            support_score=70.0,
            confidence_factors=factors,
            confidence=0.4,
            cluster_id="https://github.com/acme/family",
            evidence_family_id=family_id,
            observation_type="dependency:python_import",
            evidence_family_basis={"schema": "ef1", "domain": "dependency"},
            provenance={"artifact_path": "src/service.py"},
        ),
    ]
    config = ScoringConfig(evidence_family_decay=0.25)

    state = execute_analysis_pipeline(
        candidate_id=candidate_id,
        role=CanonicalRole.BACKEND,
    )
    assert state.dossier is not None
    repo.save_dossier(
        memory_db,
        state.dossier,
        org.id,
        custom_evidence=records,
        scoring_config=config,
    )
    memory_db.commit()

    config_entity = memory_db.query(models.ScoringConfigEntity).one()
    saved = memory_db.query(models.Evidence).order_by(models.Evidence.fingerprint).all()
    assert config_entity.version == config.version
    assert config_entity.evidence_family_decay == 0.25
    assert config_entity.eta_parameters == {
        "jd_max_logit_adjustment": config.jd_max_logit_adjustment,
        "jd_adjustment_saturation": config.jd_adjustment_saturation,
        "jd_requirement_group_decay": config.jd_requirement_group_decay,
        "min_role_weight": config.min_role_weight,
        "max_role_weight": config.max_role_weight,
    }
    assert config_entity.is_active is True
    assert len(saved) == 2
    assert [entity.support_score for entity in saved] == [80.0, 70.0]
    round_tripped = EvidenceRecord.model_validate({
        **records[0].model_dump(exclude={"technical_signal_strength", "support_score"}),
        "support_score": saved[0].support_score,
    })
    assert round_tripped.technical_signal_strength == round_tripped.support_score == 80.0
    assert {entity.analysis_run_id for entity in saved} == {
        state.dossier.analysis_run_id
    }
    assert {entity.evidence_family_id for entity in saved} == {family_id}
    assert {entity.observation_type for entity in saved} == {
        "dependency:manifest",
        "dependency:python_import",
    }
    assert all(
        entity.provenance["evidence_family_basis"]["schema"] == "ef1"
        for entity in saved
    )
    persisted_recency = next(
        entity.provenance["artifact_recency"]
        for entity in saved
        if entity.fingerprint == "a" * 64
    )
    assert persisted_recency["state"] == "known"
    assert persisted_recency["last_meaningful_revision_sha"] == "d" * 40
    assert persisted_recency["repository_last_activity"] == "2026-09-22T00:00:00Z"
    links = memory_db.query(models.EvidenceCapabilityLink).all()
    assert {link.evidence_id: link.effective_weight for link in links} == {
        records[0].evidence_id: 1.0,
        records[1].evidence_id: 0.25,
    }


def test_database_seeder_script_execution():
    """Validates that scripts/seed_db.py executes cleanly without errors."""
    from scripts.seed_db import seed_database
    test_db_file = "sqlite:///:memory:"
    # Run seed_database with 2 sample cohorts in-memory
    seed_database(db_url=test_db_file, reset=False, samples_count=2)


def test_qualified_negative_round_trips_through_dossier_snapshot(memory_db):
    """Verifies that qualified negative evidence preserves details and qualification through repository persistence."""
    org = repo.save_organization(memory_db, "Negative Evidence Org", "negative-evidence-org")
    candidate_id = uuid.uuid4()
    run_id = uuid.uuid4()
    claim_ref = "cr1:" + "e" * 64
    rule_id = "candidatex.contradiction.coverage_below_claim"
    details = {
        "claim_reference": claim_ref,
        "candidate_type": rule_id,
        "expected_observation": "Line coverage >= 90%",
        "actual_observation": "Line coverage 65%",
        "scan_scope": {
            "scope_kind": "artifact",
            "repository_scope": "acme/repo",
            "pinned_revision": "f" * 40,
            "artifact_paths": ["coverage.xml"],
            "category": "coverage_report",
            "scope_version": "candidatex.negative-scan-scope/1.0.0",
        },
        "required_scan_completeness": 1.0,
        "observed_scan_completeness": 1.0,
        "explanation": "Report coverage 65% is below claimed 90%.",
    }
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    negative_record = EvidenceRecord(
        evidence_id=uuid.uuid4(),
        fingerprint="f" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/acme/repo",
        immutable_revision="f" * 40,
        target_capability=CapabilityKey.TESTING_QUALITY,
        technical_signal_strength=65.0,
        is_positive_support=False,
        negative_evidence_details=details,
        confidence_factors=factors,
        confidence=1.0,
        provenance={
            "signal_rule_id": rule_id,
            "signal_rule_version": "1.0.0",
            "artifact_path": "coverage.xml",
        },
    )
    dossier = Dossier(
        candidate_id=candidate_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.8,
        coverage_sufficiency_threshold=0.5,
        is_insufficient_evidence=False,
        capability_estimates={},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
        evidence_records=[negative_record],
    )
    repo.save_dossier(
        memory_db,
        dossier,
        org.id,
        custom_evidence=[negative_record],
    )
    memory_db.commit()

    loaded = repo.get_dossier_by_candidate_id(memory_db, dossier.candidate_id)
    assert loaded is not None
    negative = next(record for record in loaded.evidence_records if not record.is_positive_support)
    assert negative.negative_evidence_qualification == "qualified"
    assert negative.negative_evidence_details is not None
    assert negative.negative_evidence_details.claim_reference == claim_ref

    # Verify relational Evidence entity provenance in DB mirrors details and qualification
    ev_entity = memory_db.query(models.Evidence).filter_by(fingerprint="f" * 64).one()
    assert ev_entity.is_positive_support is False
    assert ev_entity.provenance.get("negative_evidence_qualification") == "qualified"
    assert ev_entity.provenance.get("negative_evidence_details") is not None
    assert ev_entity.provenance["negative_evidence_details"]["claim_reference"] == claim_ref


def test_legacy_negative_record_round_trips_unqualified_in_provenance(memory_db):
    """Verifies that legacy unqualified negative evidence records mirror legacy_unqualified in provenance."""
    org = repo.save_organization(memory_db, "Legacy Neg Org", "legacy-neg-org")
    candidate_id = uuid.uuid4()
    run = repo.save_analysis_run(memory_db, candidate_id, CanonicalRole.BACKEND, org.id)
    memory_db.flush()

    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    legacy_record = EvidenceRecord(
        evidence_id=uuid.uuid4(),
        fingerprint="e" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/acme/legacy",
        immutable_revision="e" * 40,
        target_capability=CapabilityKey.TESTING_QUALITY,
        technical_signal_strength=40.0,
        is_positive_support=False,
        confidence_factors=factors,
        confidence=1.0,
    )
    repo.save_evidence_records(memory_db, run.id, [legacy_record], ScoringConfig())
    memory_db.commit()

    ev_entity = memory_db.query(models.Evidence).filter_by(fingerprint="e" * 64).one()
    assert ev_entity.is_positive_support is False
    assert ev_entity.provenance.get("negative_evidence_qualification") == "legacy_unqualified"
    assert "negative_evidence_details" not in ev_entity.provenance
