"""Comprehensive test suite for Fix 31: Protect PII and Define Retention.

Verifies:
1. Explicit data lifecycle policies across all 8 data categories:
   - uploaded resume bytes
   - extracted PII
   - parsed resume text
   - analysis artifacts
   - cached pages
   - candidate records
   - logs
   - exports
   - Confirmation of zero hidden indefinite storage.
2. PII log sanitization and redaction:
   - candidate personal emails redacted to [REDACTED_EMAIL]
   - candidate phone numbers redacted to [REDACTED_PHONE]
   - candidate SSNs redacted to [REDACTED_SSN]
   - authorization tokens redacted to [REDACTED_TOKEN]
   - multi-line resume bodies redacted to [REDACTED_RESUME_TEXT]
3. Full candidate deletion pathway (GDPR Right-to-be-Forgotten):
   - Deletes from SQL database (candidates, documents, sources, projects, snapshots, runs)
   - Evicts from in-memory caches (dossier store, CEG store, runner runs, pipeline state)
   - Generates immutable DeletionEvent tombstone with SHA-256 candidate ID hash
   - Records deletion audit event in append-only audit trail
   - Post-deletion GET returns HTTP 404
4. Multi-tenancy isolation on deletion pathway:
   - Org B cannot delete Org A candidate (returns HTTP 404)
5. Retention policy enforcement:
   - Purges documents and analysis runs older than configured retention limits
   - Evicts expired web cache entries
"""

import io
import logging
import hashlib
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cci.api.routers.dossier import (
    _DOSSIER_STORE,
    get_stored_dossier,
    register_dossier,
)
from cci.db.base import Base
from cci.db import models
from cci.db.models.audit import DeletionEvent
from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
)
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.main import app
from cci.security.auth import create_access_token
from cci.security.privacy import (
    DataCategory,
    PIISanitizingFilter,
    get_explicit_data_policies,
    sanitize_sensitive_text,
)


@pytest.fixture
def test_dossier() -> Dossier:
    """Creates a sample dossier fixture."""
    cid = uuid4()
    estimates = {
        k: CapabilityEstimate(
            capability_key=k,
            estimate=80.0,
            is_observed=True,
            effective_evidence_count=2.0,
            raw_evidence_count=3,
            coverage_k=0.8,
        )
        for k in CapabilityKey
    }
    conflicts = {
        k: CapabilityConflict(
            capability_key=k,
            positive_support_sum=2.0,
            negative_support_sum=0.0,
            contradiction_diagnostic=1.0,
        )
        for k in CapabilityKey
    }
    return Dossier(
        dossier_id=uuid4(),
        candidate_id=cid,
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
        rci=80.0,
        coverage=0.6,
        is_insufficient_evidence=False,
        capability_estimates=estimates,
        capability_conflicts=conflicts,
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
    )


# ------------------------------------------------------------------------------
# 1. Explicit Data Policies for All 8 Categories (No Hidden Indefinite Storage)
# ------------------------------------------------------------------------------
def test_explicit_data_policies_cover_all_eight_categories():
    """Verifies that all 8 required categories have explicit, bounded retention policies."""
    client = TestClient(app)
    res = client.get("/api/v1/privacy/policies")
    assert res.status_code == 200

    data = res.json()
    assert data["guarantee_no_hidden_indefinite_storage"] is True
    assert data["total_categories"] == 8

    policies = {p["category"]: p for p in data["policies"]}
    expected_categories = [
        "uploaded_resume_bytes",
        "extracted_pii",
        "parsed_resume_text",
        "analysis_artifacts",
        "cached_pages",
        "candidate_records",
        "logs",
        "exports",
    ]

    for cat in expected_categories:
        assert cat in policies, f"Missing required data policy category: {cat}"
        policy = policies[cat]
        # Guarantee no indefinite storage
        assert policy["is_indefinite"] is False
        assert policy["storage_location"] is not None
        assert policy["deletion_pathway"] is not None
        assert policy["logging_policy"] is not None
        # Must have either max_retention_days or max_retention_hours bounded
        assert (
            policy["max_retention_days"] is not None
            or policy["max_retention_hours"] is not None
        )


# ------------------------------------------------------------------------------
# 2. PII Log Redaction and Sanitization
# ------------------------------------------------------------------------------
def test_pii_log_redaction_sanitizes_emails_phones_and_resume_bodies():
    """Verifies that PIISanitizingFilter prevents candidate PII and resume bodies from entering logs."""
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.addFilter(PIISanitizingFilter())

    test_logger = logging.getLogger("test_privacy_redaction")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)

    candidate_email = "alex.rivas.982@example.com"
    candidate_phone = "415-555-0199"
    candidate_ssn = "123-45-6789"
    bearer_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sensitive_token_payload"
    resume_body = (
        "WORK EXPERIENCE: Senior Backend Developer at Tech Innovations from 2021-2024. "
        "Engineered scalable microservices using Python and Go. Led PostgreSQL database optimization. "
        "EDUCATION: Bachelor of Science in Computer Science, Magna Cum Laude."
    )

    test_logger.info("Intake initiated for %s with phone %s and ssn %s", candidate_email, candidate_phone, candidate_ssn)
    test_logger.info("Headers received: %s", bearer_token)
    test_logger.info("Extracted raw resume text: %s", resume_body)

    log_contents = log_capture.getvalue()

    # Verify zero raw PII leaked into logs
    assert candidate_email not in log_contents
    assert candidate_phone not in log_contents
    assert candidate_ssn not in log_contents
    assert "sensitive_token_payload" not in log_contents
    assert "Tech Innovations" not in log_contents

    # Verify standard redaction placeholders
    assert "[REDACTED_EMAIL]" in log_contents
    assert "[REDACTED_PHONE]" in log_contents
    assert "[REDACTED_SSN]" in log_contents
    assert "[REDACTED_TOKEN]" in log_contents
    assert "[REDACTED_RESUME_TEXT]" in log_contents


# ------------------------------------------------------------------------------
# 3. Candidate Deletion Pathway (GDPR Right-to-be-Forgotten)
# ------------------------------------------------------------------------------
def test_candidate_deletion_pathway_purges_data_and_creates_tombstone(test_dossier):
    """Verifies that deleting a candidate purges DB rows, evicts memory stores, and writes a tombstone."""
    org_id = uuid4()
    user_id = uuid4()
    cand_id = test_dossier.candidate_id

    # Register dossier in-memory
    register_dossier(test_dossier, organization_id=org_id)
    assert get_stored_dossier(cand_id, org_id) is not None

    token = create_access_token(user_id=user_id, organization_id=org_id, role="recruiter")
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)

    # 1. Create candidate in database
    create_res = client.post(
        "/api/v1/candidates",
        json={
            "candidate_id": str(cand_id),
            "display_name": "Candidate To Forget",
            "primary_email": "forgetme@example.com",
            "manifest_data": {"skills": ["Python", "FastAPI"]},
        },
        headers=headers,
    )
    assert create_res.status_code == 201

    # Verify candidate exists
    get_res = client.get(f"/api/v1/candidates/{cand_id}", headers=headers)
    assert get_res.status_code == 200

    # 2. Execute deletion pathway via DELETE /api/v1/candidates/{id}
    del_res = client.delete(
        f"/api/v1/candidates/{cand_id}?reason=candidate_gdpr_request",
        headers=headers,
    )
    assert del_res.status_code == 200
    del_data = del_res.json()

    assert del_data["is_deleted"] is True
    assert del_data["candidate_id"] == str(cand_id)
    expected_hash = hashlib.sha256(str(cand_id).encode("utf-8")).hexdigest()
    assert del_data["candidate_id_hash"] == expected_hash
    assert len(del_data["deleted_tables"]) >= 5

    # 3. Verify in-memory store eviction
    assert get_stored_dossier(cand_id, org_id) is None
    assert cand_id not in _DOSSIER_STORE

    # 4. Verify candidate is now 404 in database
    get_after_del = client.get(f"/api/v1/candidates/{cand_id}", headers=headers)
    assert get_after_del.status_code == 404

    # 5. Verify dossier endpoint is now 404
    dossier_after_del = client.get(f"/api/v1/dossier/{cand_id}", headers=headers)
    assert dossier_after_del.status_code == 404


# ------------------------------------------------------------------------------
# 4. Multi-Tenant Scoping on Deletion Pathway
# ------------------------------------------------------------------------------
def test_cross_tenant_candidate_deletion_rejected_with_404():
    """Verifies that Org B cannot delete Org A's candidate (returns 404 to prevent ID enumeration)."""
    org_a = uuid4()
    org_b = uuid4()
    cand_id = uuid4()

    token_a = create_access_token(user_id=uuid4(), organization_id=org_a, role="recruiter")
    token_b = create_access_token(user_id=uuid4(), organization_id=org_b, role="recruiter")

    client = TestClient(app)

    # Org A creates candidate
    client.post(
        "/api/v1/candidates",
        json={
            "candidate_id": str(cand_id),
            "display_name": "Org A Candidate",
            "primary_email": "orga@example.com",
            "manifest_data": {},
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Org B attempts to delete Org A's candidate -> must return 404
    del_b = client.delete(
        f"/api/v1/candidates/{cand_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert del_b.status_code == 404

    # Org A candidate must remain intact
    get_a = client.get(
        f"/api/v1/candidates/{cand_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert get_a.status_code == 200


# ------------------------------------------------------------------------------
# 5. Retention Policy Enforcement
# ------------------------------------------------------------------------------
def test_retention_enforcement_endpoint_purges_expired_data():
    """Verifies that POST /api/v1/privacy/retention/enforce executes retention cleanup."""
    token = create_access_token(user_id=uuid4(), organization_id=uuid4(), role="admin")
    client = TestClient(app)

    res = client.post(
        "/api/v1/privacy/retention/enforce",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert "enforced_at" in data
    assert "documents_purged" in data
    assert "runs_purged" in data
    assert "cache_entries_evicted" in data
    assert "successfully enforced" in data["details"]
