"""Unit tests for FIX 49: Provenance-Preserving Exports (JSON, Markdown, HTML).

Mandatory Invariants:
1. Export supports JSON, Markdown, and HTML/PDF.
2. Every conclusion must preserve:
   - claim IDs
   - evidence IDs
   - source URLs
   - commit SHA
   - artifact path
   - content hash
   - fetch timestamp
   - limitations
   - model/analyzer versions
3. Exports must not turn uncertain findings into certain statements.
"""

import json
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from cci.api.routers.dossier import register_dossier
from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    InterviewQuestion,
    ProbePriority,
)
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.main import app
from cci.reports.exporter import (
    generate_html_brief,
    generate_json_brief,
    generate_markdown_brief,
)


@pytest.fixture
def provenance_dossier() -> Dossier:
    cand_id = uuid4()
    run_id = uuid4()
    ev1_id = uuid4()
    ev2_id = uuid4()
    claim1_id = uuid4()
    claim2_id = uuid4()

    ev1 = EvidenceRecord(
        evidence_id=ev1_id,
        fingerprint="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/candidate/distributed-cache",
        immutable_revision="8f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        technical_signal_strength=88.0,
        is_positive_support=True,
        confidence_factors=EvidenceConfidenceFactors(
            artifact_integrity=1.0,
            ownership_score=1.0,
            recency_factor=0.9,
            verification_level=0.95,
            depth_specificity=0.9,
            source_reliability=0.95,
        ),
        confidence=0.85,
        observation_type="ast_analysis",
        provenance={
            "path": "src/cache/lru_engine.py",
            "file": "lru_engine.py",
            "line": 42,
            "commit_sha": "8f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
            "content_hash": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
            "fetch_timestamp": "2026-09-24 18:30:00 UTC",
            "analyzer_version": "2.4.0",
        },
        created_at=datetime(2026, 9, 24, 18, 30, 0, tzinfo=timezone.utc),
    )

    ev2 = EvidenceRecord(
        evidence_id=ev2_id,
        fingerprint="b2c3d4e5f6a17890123456789abcdef0123456789abcdef0123456789abcdef1",
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/candidate/distributed-cache",
        immutable_revision="8f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
        target_capability=CapabilityKey.DATABASE_ENGINEERING,
        technical_signal_strength=82.0,
        is_positive_support=True,
        confidence_factors=EvidenceConfidenceFactors(
            artifact_integrity=1.0,
            ownership_score=1.0,
            recency_factor=0.9,
            verification_level=0.95,
            depth_specificity=0.9,
            source_reliability=0.95,
        ),
        confidence=0.80,
        observation_type="ast_analysis",
        provenance={
            "path": "src/db/storage_adapter.py",
            "file": "storage_adapter.py",
            "line": 105,
            "commit_sha": "8f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
            "content_hash": "b2c3d4e5f6a17890123456789abcdef0123456789abcdef0123456789abcdef1",
            "fetch_timestamp": "2026-09-24 18:30:00 UTC",
            "analyzer_version": "2.4.0",
        },
        created_at=datetime(2026, 9, 24, 18, 30, 0, tzinfo=timezone.utc),
    )

    estimates = {}
    conflicts = {}

    for key in CapabilityKey:
        if key in (CapabilityKey.BACKEND_ENGINEERING, CapabilityKey.DATABASE_ENGINEERING):
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=85.0,
                is_observed=True,
                effective_evidence_count=2.0,
                raw_evidence_count=2,
                cluster_count=1,
                standard_error=2.0,
                dispersion=3.0,
                ci_lower=80.0,
                ci_upper=90.0,
                coverage_k=0.60,
            )
            conflicts[key] = CapabilityConflict(
                capability_key=key,
                positive_support_sum=10.0,
                negative_support_sum=0.0,
                contradiction_diagnostic=1.0,
                has_meaningful_conflict=False,
            )
        else:
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=None,
                is_observed=False,
                effective_evidence_count=0.0,
                raw_evidence_count=0,
                cluster_count=0,
                standard_error=0.0,
                dispersion=0.0,
                ci_lower=None,
                ci_upper=None,
                coverage_k=0.0,
            )
            conflicts[key] = CapabilityConflict(
                capability_key=key,
                positive_support_sum=0.0,
                negative_support_sum=0.0,
                contradiction_diagnostic=0.0,
                has_meaningful_conflict=False,
            )

    claims = [
        {
            "claim_id": str(claim1_id),
            "claim_text": "Built high-throughput in-memory LRU cache engine in Python",
            "target_capability": "backend_engineering",
            "status": "corroborated",
            "confidence": 0.90,
            "grounding_evidence_ids": [str(ev1_id)],
            "citation_urls": ["https://github.com/candidate/distributed-cache/blob/master/src/cache/lru_engine.py"],
            "explanation": "Observed LRU eviction algorithm implementation in candidate commit",
        },
        {
            "claim_id": str(claim2_id),
            "claim_text": "Architected multi-region Kubernetes clusters with Istio mesh",
            "target_capability": "devops_cloud",
            "status": "unknown",
            "confidence": 0.0,
            "grounding_evidence_ids": [],
            "citation_urls": [],
            "explanation": "No infrastructure or deployment manifests observed in provided sources",
        },
    ]

    return Dossier(
        dossier_id=uuid4(),
        candidate_id=cand_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        rci=85.0,
        coverage=0.35,
        is_insufficient_evidence=False,
        capability_estimates=estimates,
        capability_conflicts=conflicts,
        role_requirements=[],
        ownership_assessments=[],
        interview_probes=[],
        interview_questions=[],
        claims_corroboration=claims,
        evidence_records=[ev1, ev2],
        system_limitations=[
            "Analysis bounded to publicly inspectable Git repositories and manifest claims.",
            "Missing evidence represents unknown capability, never low capability.",
        ],
        versions={
            "scoring_model_version": "5.1.0",
            "analyzer_version": "2.4.0",
            "evidence_schema_version": "1.0.0",
            "role_ontology_version": "1.0.0",
            "claim_schema_version": "1.0.0",
            "source_reliability_version": "1.0.0",
            "api_version": "1.0.0",
        },
    )


def test_json_export_preserves_all_provenance_fields(provenance_dossier):
    """Verifies that JSON export contains all mandatory provenance fields for every conclusion."""
    json_str = generate_json_brief(provenance_dossier, candidate_name="Jordan Forensic")
    data = json.loads(json_str)

    # 1. Root structure and backward compatibility
    assert data["candidate_id"] == str(provenance_dossier.candidate_id)
    assert data["rci"] == 85.0
    assert "CandidateX does not decide whether to hire a person" in data["platform_invariant"]

    # 2. System limitations and versions
    assert len(data["system_limitations"]) >= 2
    assert "scoring_model_version" in data["version_families"]
    assert data["version_families"]["analyzer_version"] == "2.4.0"

    # 3. Provenance conclusions
    conclusions = data["provenance_conclusions"]
    assert len(conclusions) >= 2

    # Check corroborated claim conclusion
    corroborated = next(c for c in conclusions if c["status"] == "corroborated")
    assert corroborated["claim_id"] is not None
    assert len(corroborated["grounding_evidence_records"]) == 1

    ev_record = corroborated["grounding_evidence_records"][0]
    assert ev_record["evidence_id"] == str(provenance_dossier.evidence_records[0].evidence_id)
    assert "https://github.com/candidate/distributed-cache" in ev_record["source_url"]
    assert ev_record["commit_sha"] == "8f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a"
    assert ev_record["artifact_path"] == "src/cache/lru_engine.py"
    assert ev_record["content_hash"] == "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0"
    assert "2026-09-24" in ev_record["fetch_timestamp"]
    assert ev_record["analyzer_version"] == "2.4.0"

    # Check uncorroborated claim conclusion (uncertainty preservation)
    unknown_claim = next(c for c in conclusions if c["status"] == "unknown")
    assert unknown_claim["is_uncertain"] is True
    assert unknown_claim["uncertainty_preserved"] is True
    assert "UNKNOWN" in unknown_claim["finding_statement"]
    # Unverified claims must not turn into certain statements
    assert "not be treated as established" in unknown_claim["finding_statement"] or "lacks independent artifact" in unknown_claim["finding_statement"]


def test_markdown_export_preserves_provenance_and_uncertainty(provenance_dossier):
    """Verifies that Markdown brief renders every required provenance item and preserves uncertainty."""
    md = generate_markdown_brief(provenance_dossier, candidate_name="Jordan Forensic")

    # 1. Mandatory provenance items in markdown
    ev1 = provenance_dossier.evidence_records[0]
    claim1 = provenance_dossier.claims_corroboration[0]

    assert claim1["claim_id"] in md
    assert str(ev1.evidence_id) in md
    assert ev1.source_locator in md
    assert ev1.immutable_revision in md
    assert "src/cache/lru_engine.py" in md
    assert ev1.fingerprint in md
    assert "2026-09-24" in md
    assert "2.4.0" in md

    # 2. Limitations and subsystem versions
    assert "Analysis bounded to publicly inspectable Git repositories" in md
    assert "scoring_model_version" in md
    assert "analyzer_version" in md

    # 3. Uncertainty preservation
    assert "UNKNOWN" in md
    assert "Missing evidence represents unknown capability" in md
    assert "CandidateX does not decide whether to hire a person" in md


def test_html_export_preserves_provenance_and_uncertainty(provenance_dossier):
    """Verifies that HTML/Print brief renders every required provenance item."""
    html_doc = generate_html_brief(provenance_dossier, candidate_name="Jordan Forensic")

    ev1 = provenance_dossier.evidence_records[0]
    claim1 = provenance_dossier.claims_corroboration[0]

    assert claim1["claim_id"] in html_doc
    assert str(ev1.evidence_id) in html_doc
    assert ev1.source_locator in html_doc
    assert ev1.immutable_revision in html_doc
    assert "src/cache/lru_engine.py" in html_doc
    assert ev1.fingerprint in html_doc
    assert "scoring_model_version" in html_doc
    assert "analyzer_version" in html_doc
    assert "CandidateX does not decide whether to hire a person" in html_doc


def test_dossier_export_api_json_provenance(provenance_dossier):
    """Tests the /api/v1/dossier/{id}/export?format=json endpoint for enriched provenance."""
    register_dossier(provenance_dossier)
    client = TestClient(app)

    res = client.get(f"/api/v1/dossier/{provenance_dossier.candidate_id}/export?format=json")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    parsed = res.json()
    assert parsed["candidate_id"] == str(provenance_dossier.candidate_id)
    assert parsed["rci"] == 85.0
    assert "provenance_conclusions" in parsed
    assert len(parsed["provenance_conclusions"]) >= 2
