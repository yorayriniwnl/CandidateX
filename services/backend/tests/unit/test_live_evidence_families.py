"""Live observation retention and run-scoped evidence identities."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from cci.domain.contracts import (
    ArtifactRecency,
    ArtifactAttribution,
    EvidenceInput,
    RepositoryAssociation,
    RepositoryContribution,
)
from cci.domain.enums import ArtifactAttributionState, CapabilityKey, SourceFamily
from cci.live.acquisition import (
    build_live_evidence_records,
    evidence_ids_for_fingerprints,
    normalized_repository_identity,
)


REPOSITORY_URL = "https://github.com/Acme/API.git"
FAMILY_ID = "ef1:" + "a" * 64


def _input() -> EvidenceInput:
    return EvidenceInput(
        source_family=SourceFamily.GITHUB,
        source_locator=REPOSITORY_URL,
        immutable_revision="b" * 40,
        artifact_path="requirements.txt",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        observed_score=72.0,
        raw_support_text="fastapi==0.115.0",
        extractor_version="python-analyzer-v2",
        evidence_family_id=FAMILY_ID,
        observation_type="dependency:manifest",
        evidence_family_basis={
            "schema": "ef1",
            "domain": "dependency",
            "subject": "fastapi",
        },
    )


def test_run_scoped_fingerprint_occurrence_ids_are_unique_and_repeatable():
    run_id = uuid4()
    fingerprints = ["same-fingerprint"] * 200

    first = evidence_ids_for_fingerprints(run_id, fingerprints)
    repeated = evidence_ids_for_fingerprints(run_id, fingerprints)
    another_run = evidence_ids_for_fingerprints(uuid4(), fingerprints)

    assert len(first) == 200
    assert len(set(first)) == 200
    assert first == repeated
    assert set(first).isdisjoint(another_run)


def test_live_conversion_retains_repeated_inputs_and_semantic_metadata():
    run_id = uuid4()
    artifact_id = uuid4()
    artifact = SimpleNamespace(artifact_id=artifact_id, content_sha256="c" * 64)
    attribution = ArtifactAttribution(
        revision_sha="b" * 40,
        state=ArtifactAttributionState.STRONG_ATTRIBUTION,
        ownership_score=0.8,
        attribution_confidence=0.9,
        candidate_commit_count=4,
        sampled_path_commit_count=5,
    )
    association = RepositoryAssociation(
        repository_url=REPOSITORY_URL,
        basis="selected_repository_url",
    )
    contribution = RepositoryContribution(
        repository_url=REPOSITORY_URL,
        sampled_commit_count=5,
        candidate_commit_count=4,
        candidate_commit_ratio=0.8,
    )
    observations = [_input(), _input()]

    records = build_live_evidence_records(
        observations,
        analysis_run_id=run_id,
        source_locator=REPOSITORY_URL,
        immutable_revision="b" * 40,
        cluster_id="https://github.com/acme/api",
        artifacts_by_path={"requirements.txt": artifact},
        snapshot_fingerprint="d" * 64,
        path_attributions={"requirements.txt": attribution},
        artifact_recencies={
            "requirements.txt": ArtifactRecency(
                state="known",
                last_meaningful_modification_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
                last_meaningful_revision_sha="e" * 40,
                repository_last_activity=datetime(2025, 1, 2, tzinfo=timezone.utc),
            )
        },
        repository_last_activity=datetime(2025, 1, 2, tzinfo=timezone.utc),
        repository_association=association,
        repository_contribution=contribution,
    )
    rebuilt = build_live_evidence_records(
        observations,
        analysis_run_id=run_id,
        source_locator=REPOSITORY_URL,
        immutable_revision="b" * 40,
        cluster_id="https://github.com/acme/api",
        artifacts_by_path={"requirements.txt": artifact},
        snapshot_fingerprint="d" * 64,
        path_attributions={"requirements.txt": attribution},
        artifact_recencies={
            "requirements.txt": ArtifactRecency(
                state="known",
                last_meaningful_modification_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
                last_meaningful_revision_sha="e" * 40,
                repository_last_activity=datetime(2025, 1, 2, tzinfo=timezone.utc),
            )
        },
        repository_last_activity=datetime(2025, 1, 2, tzinfo=timezone.utc),
        repository_association=association,
        repository_contribution=contribution,
    )

    assert len(records) == 2
    assert records[0].fingerprint == records[1].fingerprint
    assert records[0].evidence_id != records[1].evidence_id
    assert [record.evidence_id for record in records] == [
        record.evidence_id for record in rebuilt
    ]
    assert all(record.provenance["raw_support_text"] == "fastapi==0.115.0" for record in records)
    assert all(record.evidence_family_id == FAMILY_ID for record in records)
    assert all(record.observation_type == "dependency:manifest" for record in records)
    assert all(record.cluster_id == "https://github.com/acme/api" for record in records)
    assert all(record.artifact_id == artifact_id for record in records)
    assert all(
        record.provenance["evidence_family_basis"]["subject"] == "fastapi"
        for record in records
    )


def test_repository_cluster_identity_is_canonicalized():
    assert normalized_repository_identity(REPOSITORY_URL) == (
        "https://github.com/acme/api"
    )
