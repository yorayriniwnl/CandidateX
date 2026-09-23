"""Database migration and entity smoke tests."""

import hashlib
import uuid
from pathlib import Path
import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
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
    assert "evidence_family_decay" in columns


def _migration_config(connection):
    config_path = Path(__file__).parents[2] / "alembic.ini"
    config = Config(str(config_path))
    config.attributes["connection"] = connection
    return config


def test_fresh_alembic_upgrade_skips_columns_created_by_initial_schema():
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.connect() as connection:
            alembic_command.upgrade(_migration_config(connection), "head")
            inspector = inspect(connection)

            evidence_columns = {
                column["name"] for column in inspector.get_columns("evidence")
            }
            scoring_columns = {
                column["name"]
                for column in inspector.get_columns("scoring_configs")
            }
            cluster_column = next(
                column
                for column in inspector.get_columns("evidence")
                if column["name"] == "cluster_id"
            )

            assert "evidence_family_id" in evidence_columns
            assert "observation_type" in evidence_columns
            assert "evidence_family_decay" in scoring_columns
            assert cluster_column["type"].length == 255
    finally:
        engine.dispose()


def test_revision_0002_upgrade_backfills_unique_legacy_family_ids():
    engine = create_engine("sqlite:///:memory:")
    evidence_ids = [uuid.uuid4(), uuid.uuid4()]
    duplicate_fingerprint = "f" * 64
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "CREATE TABLE evidence (id CHAR(36) PRIMARY KEY, "
                    "fingerprint VARCHAR(64) NOT NULL, "
                    "cluster_id VARCHAR(100) NULL)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE scoring_configs (id CHAR(36) PRIMARY KEY, "
                    "version VARCHAR(50) NOT NULL, "
                    "cluster_artifact_decay FLOAT NOT NULL DEFAULT 0.5)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO evidence (id, fingerprint) VALUES "
                    "(:first_id, :fingerprint), (:second_id, :fingerprint)"
                ),
                {
                    "first_id": str(evidence_ids[0]),
                    "second_id": str(evidence_ids[1]),
                    "fingerprint": duplicate_fingerprint,
                },
            )
            connection.commit()

            config = _migration_config(connection)
            alembic_command.stamp(config, "0002_cluster_artifact_decay")
            alembic_command.upgrade(config, "head")

            rows = connection.execute(
                text(
                    "SELECT id, fingerprint, evidence_family_id, observation_type "
                    "FROM evidence ORDER BY id"
                )
            ).all()
            family_ids = {row.evidence_family_id for row in rows}
            assert len(rows) == 2
            assert len(family_ids) == 2
            assert {
                row.evidence_family_id
                for row in rows
            } == {
                "ef0:" + hashlib.sha256(str(evidence_id).encode()).hexdigest()
                for evidence_id in evidence_ids
            }
            assert {row.observation_type for row in rows} == {"legacy_unknown"}
            scoring_columns = {
                column["name"]
                for column in inspect(connection).get_columns("scoring_configs")
            }
            assert "evidence_family_decay" in scoring_columns
            cluster_column = next(
                column
                for column in inspect(connection).get_columns("evidence")
                if column["name"] == "cluster_id"
            )
            assert cluster_column["type"].length == 255

            connection.execute(
                text("INSERT INTO scoring_configs (id, version) VALUES (:id, :version)"),
                {"id": str(uuid.uuid4()), "version": "5.0.0"},
            )
            decay = connection.execute(
                text("SELECT evidence_family_decay FROM scoring_configs")
            ).scalar_one()
            assert decay == pytest.approx(0.5)
    finally:
        engine.dispose()


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
            evidence_family_id="ef0:" + "a" * 64,
            observation_type="legacy_unknown",
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
