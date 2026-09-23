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

    # Save job description
    jd = repo.save_job_description(
        session=memory_db,
        organization_id=org.id,
        title="Senior Backend Engineer",
        canonical_role=CanonicalRole.BACKEND,
        raw_text="Requires Python, PostgreSQL, and distributed architectures.",
    )
    assert jd.id is not None
    assert jd.canonical_role == "backend"

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
            support_score=80.0,
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
    assert config_entity.is_active is True
    assert len(saved) == 2
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
