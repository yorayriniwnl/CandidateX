"""Database migration and entity smoke tests."""

import uuid
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from cci.db.base import Base
import cci.db.models as models


EXPECTED_TABLES = {
    "organizations",
    "users",
    "candidates",
    "identities",
    "identity_links",
    "candidate_documents",
    "candidate_sources",
    "projects",
    "job_descriptions",
    "role_profiles",
    "role_requirements",
    "role_weight_overrides",
    "analysis_runs",
    "analysis_stage_runs",
    "source_snapshots",
    "repositories",
    "repository_contributors",
    "repository_artifacts",
    "artifacts",
    "evidence",
    "evidence_capability_links",
    "evidence_clusters",
    "claims",
    "claim_evidence_links",
    "requirement_evidence_links",
    "source_reliability_posteriors",
    "ownership_assessments",
    "capability_estimates",
    "capability_uncertainty",
    "capability_conflicts",
    "analysis_scores",
    "scoring_configs",
    "interview_probe_priorities",
    "interview_questions",
    "dossier_items",
    "dossier_snapshots",
    "analyzer_versions",
    "model_versions",
    "audit_events",
    "correction_requests",
    "deletion_events",
}


@pytest.fixture(scope="module")
def test_engine():
    """Create in-memory SQLite engine for migration smoke testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_all_paper_aligned_tables_exist(test_engine):
    """Acceptance gate: Alembic/SQLAlchemy creates all 38+ required paper-aligned tables."""
    inspector = inspect(test_engine)
    existing_tables = set(inspector.get_table_names())

    missing_tables = EXPECTED_TABLES - existing_tables
    assert not missing_tables, f"Missing required database tables: {missing_tables}"
    assert EXPECTED_TABLES.issubset(existing_tables)


def test_scoring_config_persists_cluster_artifact_decay(test_engine):
    columns = {column["name"] for column in inspect(test_engine).get_columns("scoring_configs")}
    assert "cluster_artifact_decay" in columns


def test_evidence_immutability_enforcement(test_engine):
    """Verify that Evidence rows cannot be updated once inserted."""
    Session = sessionmaker(bind=test_engine)
    session = Session()

    try:
        # Create minimal required parent entities
        org = models.Organization(name="Acme Corp", slug="acme")
        session.add(org)
        session.flush()

        candidate = models.Candidate(
            organization_id=org.id,
            display_name="Test Candidate",
            primary_email="cand@test.com",
            manifest_data={},
        )
        session.add(candidate)
        session.flush()

        analysis = models.AnalysisRun(
            organization_id=org.id,
            candidate_id=candidate.id,
            target_role="backend",
            status="running",
        )
        session.add(analysis)
        session.flush()

        # Insert immutable Evidence record
        evidence = models.Evidence(
            analysis_run_id=analysis.id,
            fingerprint="sha256_dummy_fingerprint_for_testing",
            source_family="github",
            source_locator="https://github.com/test/repo",
            immutable_revision="abc1234",
            target_capability="backend_engineering",
            support_score=85.0,
            is_positive_support=True,
            factor_artifact_integrity=1.0,
            factor_ownership_score=0.9,
            factor_recency=0.8,
            factor_verification_level=1.0,
            factor_depth_specificity=0.7,
            factor_source_reliability=0.9,
            computed_confidence=0.87,
            analyzer_version="1.0.0",
        )
        session.add(evidence)
        session.commit()

        # Attempting to mutate evidence must raise ValueError
        evidence.support_score = 99.0
        with pytest.raises(ValueError, match="Immutable entity 'Evidence'.*cannot be modified"):
            session.commit()

    finally:
        session.rollback()
        session.close()
