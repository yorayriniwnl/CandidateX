"""Live observation retention and run-scoped evidence identities."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from cci.domain.contracts import (
    NegativeEvidenceDetails,
    NegativeEvidenceScanScope,
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
    versioned = _input().model_copy(update={
        "signal_rule_id": "candidatex.dependencies.manifest_declaration",
        "signal_rule_version": "1.0.0",
    })
    observations = [_input(), versioned]

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
    assert records[0].fingerprint == "a5b26218d19de95406db7b0d186d4bab9debfc543f0a1a7069015c3085107bb0"
    assert records[0].provenance["signal_rule_id"] == "legacy_unknown"
    assert records[0].provenance["signal_rule_version"] == "legacy_unknown"
    assert records[1].provenance["signal_rule_id"] == "candidatex.dependencies.manifest_declaration"
    assert records[1].provenance["signal_rule_version"] == "1.0.0"
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


def test_live_negative_conversion_retains_report_attribution_and_details():
    run_id = uuid4()
    artifact_id = uuid4()
    artifact = SimpleNamespace(artifact_id=artifact_id, content_sha256="c" * 64)
    attribution = ArtifactAttribution(
        revision_sha="b" * 40,
        state=ArtifactAttributionState.STRONG_ATTRIBUTION,
        ownership_score=0.85,
        attribution_confidence=0.9,
        candidate_commit_count=4,
        sampled_path_commit_count=5,
    )
    details = NegativeEvidenceDetails(
        claim_reference="cr1:" + "f" * 64,
        candidate_type="candidatex.contradiction.coverage_below_claim",
        expected_observation="line_coverage >= 95%",
        actual_observation="coverage.xml line_coverage=70%",
        scan_scope=NegativeEvidenceScanScope(
            scope_kind="artifact",
            repository_scope="acme/api",
            pinned_revision="b" * 40,
            artifact_paths=["coverage.xml"],
            category="coverage",
            scope_version="candidatex.negative-scan-scope/1.0.0",
        ),
        required_scan_completeness=1.0,
        observed_scan_completeness=1.0,
        explanation="Coverage violates threshold",
    )
    negative_input = EvidenceInput(
        source_family=SourceFamily.GITHUB,
        source_locator=REPOSITORY_URL,
        immutable_revision="b" * 40,
        artifact_path="coverage.xml",
        target_capability=CapabilityKey.TESTING_QUALITY,
        technical_signal_strength=70.0,
        signal_rule_id="candidatex.contradiction.coverage_below_claim",
        signal_rule_version="1.0.0",
        is_positive_support=False,
        raw_support_text="coverage.xml line_coverage=70%",
        extractor_version="contradiction-v1",
        negative_evidence_details=details,
    )
    association = RepositoryAssociation(repository_url=REPOSITORY_URL, basis="selected_repository_url")
    contribution = RepositoryContribution(
        repository_url=REPOSITORY_URL, sampled_commit_count=5,
        candidate_commit_count=4, candidate_commit_ratio=0.8,
    )

    records = build_live_evidence_records(
        [negative_input],
        analysis_run_id=run_id,
        source_locator=REPOSITORY_URL,
        immutable_revision="b" * 40,
        cluster_id="https://github.com/acme/api",
        artifacts_by_path={"coverage.xml": artifact},
        snapshot_fingerprint="d" * 64,
        path_attributions={"coverage.xml": attribution},
        artifact_recencies={
            "coverage.xml": ArtifactRecency(
                state="known",
                last_meaningful_modification_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
                last_meaningful_revision_sha="e" * 40,
            )
        },
        repository_last_activity=datetime(2025, 1, 2, tzinfo=timezone.utc),
        repository_association=association,
        repository_contribution=contribution,
    )

    assert len(records) == 1
    record = records[0]
    assert record.is_positive_support is False
    assert record.negative_evidence_qualification == "qualified"
    assert record.negative_evidence_details == details
    assert record.artifact_attribution == attribution
    assert record.provenance["negative_evidence_qualification"] == "qualified"
    assert record.provenance["negative_evidence_details"]["claim_reference"] == details.claim_reference
    assert record.provenance["signal_rule_id"] == "candidatex.contradiction.coverage_below_claim"


def test_live_negative_conversion_handles_repository_scope_absence():
    run_id = uuid4()
    details = NegativeEvidenceDetails(
        claim_reference="cr1:" + "a" * 64,
        candidate_type="candidatex.contradiction.framework_usage_absent",
        expected_observation="Repository source uses fastapi",
        actual_observation="No fastapi source usage in 10 eligible inspected files",
        scan_scope=NegativeEvidenceScanScope(
            scope_kind="repository",
            repository_scope="acme/api",
            pinned_revision="b" * 40,
            category="framework_usage",
            scope_version="candidatex.negative-scan-scope/1.0.0",
        ),
        required_scan_completeness=1.0,
        observed_scan_completeness=1.0,
        explanation="Complete scan found no framework usage",
    )
    absence_input = EvidenceInput(
        source_family=SourceFamily.GITHUB,
        source_locator=REPOSITORY_URL,
        immutable_revision="b" * 40,
        artifact_path=None,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        technical_signal_strength=55.0,
        signal_rule_id="candidatex.contradiction.framework_usage_absent",
        signal_rule_version="1.0.0",
        is_positive_support=False,
        raw_support_text="No fastapi source usage",
        extractor_version="contradiction-v1",
        negative_evidence_details=details,
    )
    association = RepositoryAssociation(repository_url=REPOSITORY_URL, basis="selected_repository_url")
    contribution_positive = RepositoryContribution(
        repository_url=REPOSITORY_URL, sampled_commit_count=10,
        candidate_commit_count=6, candidate_commit_ratio=0.6,
    )
    contribution_zero = RepositoryContribution(
        repository_url=REPOSITORY_URL, sampled_commit_count=10,
        candidate_commit_count=0, candidate_commit_ratio=0.0,
    )

    records = build_live_evidence_records(
        [absence_input],
        analysis_run_id=run_id,
        source_locator=REPOSITORY_URL,
        immutable_revision="b" * 40,
        cluster_id="https://github.com/acme/api",
        artifacts_by_path={},
        snapshot_fingerprint="d" * 64,
        path_attributions={},
        artifact_recencies={},
        repository_last_activity=datetime(2025, 1, 2, tzinfo=timezone.utc),
        repository_association=association,
        repository_contribution=contribution_positive,
    )

    assert len(records) == 1
    record = records[0]
    assert record.artifact_attribution is None
    assert record.artifact_recency is None
    assert record.confidence_factors.ownership_score == 0.6
    assert record.confidence > 0.0
    assert record.provenance["ownership_basis"] == "repository_candidate_commit_ratio"
    assert "Repository commit ratio" in record.provenance["ownership_limitations"][0]

    # Zero commit ratio produces zero confidence
    zero_records = build_live_evidence_records(
        [absence_input],
        analysis_run_id=run_id,
        source_locator=REPOSITORY_URL,
        immutable_revision="b" * 40,
        cluster_id="https://github.com/acme/api",
        artifacts_by_path={},
        snapshot_fingerprint="d" * 64,
        path_attributions={},
        artifact_recencies={},
        repository_last_activity=datetime(2025, 1, 2, tzinfo=timezone.utc),
        repository_association=association,
        repository_contribution=contribution_zero,
    )
    assert zero_records[0].confidence_factors.ownership_score == 0.0
    assert zero_records[0].confidence == 0.0
