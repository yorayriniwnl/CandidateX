"""Tests for Report and Full Audit Export features."""

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from cci.main import app

client = TestClient(app)


def _setup_candidate_dossier():
    """Triggers research demo to register a candidate dossier in _DOSSIER_STORE."""
    payload = {
        "candidate_id": str(uuid4()),
        "scenario": "consistent",
        "role": "backend",
    }
    response = client.post("/api/v1/research-demo/run", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    candidate_id = data["dossier"]["candidate_id"]

    # Also submit a recruiter override to create an audit event
    client.post(
        "/api/v1/overrides/recruiter",
        json={
            "candidate_id": candidate_id,
            "role_weights": {"backend_engineering": 0.35, "database_engineering": 0.25},
            "justification": "Candidate has extensive distributed systems experience.",
        },
    )

    # And submit interviewer feedback to create an interviewer audit event
    fb_res = client.post(
        "/api/v1/overrides/interview-feedback",
        json={
            "candidate_id": candidate_id,
            "interviewer_name": "Senior Staff Architect",
            "overall_recommendation": "strong_hire",
            "overall_notes": "Demonstrated deep mastery of database sharding and concurrency.",
            "probe_evaluations": [
                {
                    "capability_key": "backend_engineering",
                    "rating": 5,
                    "notes": "Excellent answers on thread safety.",
                    "is_gap_resolved": True,
                }
            ],
        },
    )
    assert fb_res.status_code == 200, fb_res.text

    return candidate_id


def test_export_report_formats():
    candidate_id = _setup_candidate_dossier()

    # 1. HTML Report
    res_html = client.get(f"/api/v1/dossier/{candidate_id}/export?format=html&scope=report")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    assert "Technical Intelligence Brief" in res_html.text
    assert "Core Capabilities" in res_html.text

    # 2. Markdown Report
    res_md = client.get(f"/api/v1/dossier/{candidate_id}/export?format=markdown&scope=report")
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# Candidate Technical Intelligence Brief" in res_md.text

    # 3. JSON Report
    res_json = client.get(f"/api/v1/dossier/{candidate_id}/export?format=json&scope=report")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    data = res_json.json()
    assert data["candidate_id"] == candidate_id
    assert "capability_estimates" in data


def test_export_full_audit_formats():
    candidate_id = _setup_candidate_dossier()

    # 1. HTML Audit
    res_html = client.get(f"/api/v1/dossier/{candidate_id}/export?format=html&scope=audit")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    assert "Full Audit &amp; Governance Log" in res_html.text or "Full Audit & Governance Log" in res_html.text
    assert "Grounding Evidence Ledger" in res_html.text
    assert "Immutable Governance Audit Trail" in res_html.text

    # 2. Markdown Audit
    res_md = client.get(f"/api/v1/dossier/{candidate_id}/export?format=markdown&scope=audit")
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# Candidate Full Audit & Governance Log" in res_md.text
    assert "## 2. Immutable Governance Audit Trail" in res_md.text
    assert "Candidate has extensive distributed systems experience" in res_md.text
    assert "Senior Staff Architect" in res_md.text
    assert "## 3. Grounding Evidence Ledger" in res_md.text

    # 3. JSON Audit
    res_json = client.get(f"/api/v1/dossier/{candidate_id}/export?format=json&scope=audit")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    audit_data = res_json.json()
    assert audit_data["candidate_id"] == candidate_id
    assert "audit_events" in audit_data
    assert len(audit_data["audit_events"]) >= 2
    assert "evidence_records" in audit_data
    assert "versions" in audit_data

    # 4. CSV Audit
    res_csv = client.get(f"/api/v1/dossier/{candidate_id}/export?format=csv&scope=audit")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "# CANDIDATE GOVERNANCE AUDIT TRAIL" in res_csv.text
    assert "# GROUNDING EVIDENCE LEDGER" in res_csv.text


def test_export_combined_report_and_audit():
    candidate_id = _setup_candidate_dossier()

    # 1. Combined Markdown
    res_md = client.get(f"/api/v1/dossier/{candidate_id}/export?format=markdown&scope=full")
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# Candidate Technical Intelligence Brief" in res_md.text
    assert "PART II: COMPLETE GOVERNANCE & PROVENANCE AUDIT" in res_md.text
    assert "# Candidate Full Audit & Governance Log" in res_md.text

    # 2. Combined HTML
    res_html = client.get(f"/api/v1/dossier/{candidate_id}/export?format=html&scope=full")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    assert "Technical Intelligence Brief" in res_html.text
    assert "PART II: FULL AUDIT &amp; GOVERNANCE LOG" in res_html.text or "PART II: FULL AUDIT & GOVERNANCE LOG" in res_html.text

    # 3. Combined JSON
    res_json = client.get(f"/api/v1/dossier/{candidate_id}/export?format=json&scope=full")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    bundle = res_json.json()
    assert "report" in bundle
    assert "full_audit" in bundle
    assert bundle["candidate_id"] == candidate_id
    assert len(bundle["full_audit"]["audit_events"]) >= 2


def test_export_audit_dedicated_endpoints():
    candidate_id = _setup_candidate_dossier()

    # /export-audit endpoint
    res_audit_ep = client.get(f"/api/v1/dossier/{candidate_id}/export-audit?format=markdown")
    assert res_audit_ep.status_code == 200
    assert "# Candidate Full Audit & Governance Log" in res_audit_ep.text

    # /overrides/audit/{candidate_id}/export endpoint
    res_overrides_csv = client.get(f"/api/v1/overrides/audit/{candidate_id}/export?format=csv")
    assert res_overrides_csv.status_code == 200
    assert "# CANDIDATE GOVERNANCE AUDIT TRAIL" in res_overrides_csv.text

    res_overrides_md = client.get(f"/api/v1/overrides/audit/{candidate_id}/export?format=markdown")
    assert res_overrides_md.status_code == 200
    assert "# Candidate Full Audit & Governance Log" in res_overrides_md.text
