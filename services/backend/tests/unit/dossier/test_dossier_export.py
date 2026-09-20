"""Unit and API tests for Candidate Technical Intelligence Brief export engine."""

import json
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest

from cci.api.routers.dossier import register_dossier
from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
    InterviewQuestion,
    ProbePriority,
)
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.main import app
from cci.reports.exporter import generate_html_brief, generate_markdown_brief


@pytest.fixture
def sample_dossier() -> Dossier:
    """Creates a sample Dossier fixture for export verification."""
    cand_id = uuid4()
    run_id = uuid4()

    estimates = {}
    conflicts = {}

    for key in CapabilityKey:
        if key in (CapabilityKey.BACKEND_ENGINEERING, CapabilityKey.DATABASE_ENGINEERING):
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=88.5,
                is_observed=True,
                effective_evidence_count=4.2,
                raw_evidence_count=6,
                cluster_count=2,
                standard_error=1.5,
                dispersion=3.0,
                ci_lower=85.0,
                ci_upper=92.0,
                coverage_k=0.75,
            )
            conflicts[key] = CapabilityConflict(
                capability_key=key,
                positive_support_sum=12.0,
                negative_support_sum=0.5,
                contradiction_diagnostic=0.92,
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

    probes = [
        ProbePriority(
            capability_key=CapabilityKey.SOFTWARE_ARCHITECTURE,
            rank=1,
            priority_score=0.85,
            role_weight=0.15,
            coverage_gap_term=1.0,
            uncertainty_term=0.5,
            contradiction_term=0.0,
        )
    ]

    questions = [
        InterviewQuestion(
            target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
            question_text="How do you handle event schema migrations in your messaging system?",
            rationale="Unobserved architecture boundary handling in resume",
            verification_guidance="Listen for schema registry, backward compatibility, and DLQ handling",
        )
    ]

    claims = [
        {
            "claim_text": "Built high-throughput data processing pipeline with Python",
            "status": "supported",
            "grounding_evidence_ids": [str(uuid4())],
        }
    ]

    return Dossier(
        dossier_id=uuid4(),
        candidate_id=cand_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        rci=88.5,
        coverage=0.35,
        is_insufficient_evidence=False,
        capability_estimates=estimates,
        capability_conflicts=conflicts,
        role_requirements=[],
        ownership_assessments=[],
        interview_probes=probes,
        interview_questions=questions,
        claims_corroboration=claims,
    )


def test_generate_markdown_brief_content(sample_dossier):
    """Verifies that markdown brief contains required sections and invariants."""
    md = generate_markdown_brief(sample_dossier, candidate_name="Sarah Connor")

    assert "# Candidate Technical Intelligence Brief: Sarah Connor" in md
    assert "Decision Support Only" in md
    assert "Role Capability Index (RCI)" in md
    assert "88.5 / 100" in md
    assert "35.0%" in md
    assert "Backend Engineering" in md
    assert "Contradiction Diagnostics" in md
    assert "Prioritized Technical Interview Inquiry Probes" in md
    assert "How do you handle event schema migrations" in md
    assert "Candidate Self-Claims Corroboration" in md


def test_generate_html_brief_content(sample_dossier):
    """Verifies that HTML brief contains valid HTML5, CSS print media, and scorecards."""
    html_doc = generate_html_brief(sample_dossier, candidate_name="Sarah Connor")

    assert "<!DOCTYPE html>" in html_doc
    assert "Sarah Connor" in html_doc
    assert "@media print" in html_doc
    assert "window.print()" in html_doc
    assert "88.5" in html_doc
    assert "35.0%" in html_doc
    assert "Backend Engineering" in html_doc
    assert "probe-card" in html_doc
    assert "Evaluation Guidance:" in html_doc


def test_dossier_export_api_endpoints(sample_dossier):
    """Tests the /api/v1/dossier/{candidate_id}/export endpoint across formats."""
    register_dossier(sample_dossier)
    client = TestClient(app)

    # HTML format (default)
    res_html = client.get(f"/api/v1/dossier/{sample_dossier.candidate_id}/export")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    assert "<!DOCTYPE html>" in res_html.text

    # Markdown format
    res_md = client.get(f"/api/v1/dossier/{sample_dossier.candidate_id}/export?format=markdown")
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# Candidate Technical Intelligence Brief" in res_md.text

    # JSON format
    res_json = client.get(f"/api/v1/dossier/{sample_dossier.candidate_id}/export?format=json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    parsed = res_json.json()
    assert parsed["candidate_id"] == str(sample_dossier.candidate_id)
    assert parsed["rci"] == 88.5

    # 404 on unknown candidate
    fake_id = uuid4()
    res_404 = client.get(f"/api/v1/dossier/{fake_id}/export")
    assert res_404.status_code == 404

    # 422 on invalid format
    res_invalid = client.get(f"/api/v1/dossier/{sample_dossier.candidate_id}/export?format=docx")
    assert res_invalid.status_code == 422
