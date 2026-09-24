"""Unit and integration tests for Fix 29: Authentication and Multi-Tenancy.

Verifies:
1. Token Authentication:
   - Cryptographic HMAC-SHA256 JWT access token generation and claims verification.
   - Rejection of tampered signatures, expired tokens, and malformed structures.
   - POST /api/v1/auth/token and GET /api/v1/auth/me endpoints.
2. Server-Derived Organization Identity:
   - Organization identity comes solely from authenticated session/token, never caller-supplied query parameters.
3. Multi-Tenant Scoping across All Protected Endpoints (Org A vs Org B):
   - Candidate List: Org B cannot see Org A candidates.
   - Candidate Detail: Org B cannot read Org A candidate by UUID (returns 404).
   - Dossier: Org B cannot read Org A dossier by UUID (returns 404).
   - Evidence & Provenance: Org B cannot trace Org A capability provenance (returns 404).
   - Graph: Org B cannot fetch Org A Candidate Evidence Graph (returns 404).
   - Audit Trail: Org B cannot retrieve Org A candidate audit events (returns 404).
   - Exports: Org B cannot export Org A candidate technical briefs (returns 404).
   - Interview Feedback: Org B cannot record feedback for Org A candidate (returns 404).
   - Override Actions: Org B cannot adjust recruiter weights for Org A candidate (returns 404).
   - Analysis Runs: Org B cannot trigger, poll, or rescore Org A analysis runs (returns 404).
4. Strict Authentication Enforcement:
   - HTTP 401 Unauthorized when AUTH_REQUIRED=True and token is missing or invalid.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import cci.db.repository as repo
from cci.api.routers.dossier import register_dossier
from cci.config import settings
from cci.db.models.audit import AuditEvent
from cci.db.session import SessionLocal
from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
    InterviewQuestion,
    ProbePriority,
)
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.graph.builder import build_dossier_graph
from cci.main import app
from cci.pipeline.service import pipeline_service
from cci.security.auth import (
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    verify_access_token,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def org_a_id():
    return uuid4()


@pytest.fixture
def org_b_id():
    return uuid4()


@pytest.fixture
def token_org_a(org_a_id):
    return create_access_token(organization_id=org_a_id, user_id=uuid4(), role="admin")


@pytest.fixture
def token_org_b(org_b_id):
    return create_access_token(organization_id=org_b_id, user_id=uuid4(), role="recruiter")


@pytest.fixture
def auth_headers_org_a(token_org_a):
    return {"Authorization": f"Bearer {token_org_a}"}


@pytest.fixture
def auth_headers_org_b(token_org_b):
    return {"Authorization": f"Bearer {token_org_b}"}


def make_test_dossier(candidate_id, org_id):
    """Constructs a test dossier and graph registered in DB and memory."""
    estimates = {
        key: CapabilityEstimate(
            capability_key=key,
            estimate=85.0 if key == CapabilityKey.BACKEND_ENGINEERING else None,
            is_observed=key == CapabilityKey.BACKEND_ENGINEERING,
            effective_evidence_count=4.0 if key == CapabilityKey.BACKEND_ENGINEERING else 0.0,
            raw_evidence_count=6 if key == CapabilityKey.BACKEND_ENGINEERING else 0,
            coverage_k=0.85 if key == CapabilityKey.BACKEND_ENGINEERING else 0.0,
        )
        for key in CapabilityKey
    }
    conflicts = {
        key: CapabilityConflict(
            capability_key=key,
            positive_support_sum=4.0 if key == CapabilityKey.BACKEND_ENGINEERING else 0.0,
            negative_support_sum=0.0,
            contradiction_diagnostic=0.90 if key == CapabilityKey.BACKEND_ENGINEERING else 0.0,
        )
        for key in CapabilityKey
    }
    run_id = uuid4()
    dossier = Dossier(
        dossier_id=uuid4(),
        candidate_id=candidate_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        rci=85.0,
        coverage=0.35,
        is_insufficient_evidence=False,
        capability_estimates=estimates,
        capability_conflicts=conflicts,
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[
            ProbePriority(
                probe_id=uuid4(),
                capability_key=CapabilityKey.BACKEND_ENGINEERING,
                rank=1,
                priority_score=0.92,
                role_weight=0.80,
                coverage_gap_term=0.15,
                uncertainty_term=0.10,
                contradiction_term=0.05,
                justification="Primary backend domain",
            )
        ],
        interview_questions=[
            InterviewQuestion(
                question_id=uuid4(),
                target_capability=CapabilityKey.BACKEND_ENGINEERING,
                question_text="How do you handle transactional outbox consistency?",
                rationale="Verifies distributed transaction mastery",
                verification_guidance="Candidate should explain idempotent consumers",
                grounding_evidence_ids=[],
            )
        ],
    )
    graph = build_dossier_graph(dossier)
    register_dossier(dossier, graph, organization_id=org_id)

    with SessionLocal() as db:
        repo.save_dossier(db, dossier, org_id)
        db.commit()

    return dossier, graph


# ---------------------------------------------------------------------------
# 1. Token Authentication Mechanics Tests
# ---------------------------------------------------------------------------

def test_token_creation_and_claims_verification():
    """Verify cryptographic token signing, verification, and tamper rejection."""
    org_id = uuid4()
    user_id = uuid4()
    token = create_access_token(organization_id=org_id, user_id=user_id, role="recruiter", expires_in_seconds=600)

    claims = verify_access_token(token)
    assert claims["org_id"] == str(org_id)
    assert claims["uid"] == str(user_id)
    assert claims["role"] == "recruiter"
    assert "jti" in claims
    assert claims["exp"] > claims["iat"]

    # Tampered signature rejected
    tampered_sig = token[:-4] + "zzzz"
    with pytest.raises(InvalidTokenError, match="Invalid token signature"):
        verify_access_token(tampered_sig)

    # Expired token rejected
    expired_token = create_access_token(organization_id=org_id, expires_in_seconds=-10)
    with pytest.raises(TokenExpiredError, match="expired"):
        verify_access_token(expired_token)

    # Malformed token format rejected
    with pytest.raises(InvalidTokenError, match="Malformed"):
        verify_access_token("not.a.valid.jwt.token")


def test_auth_token_issuance_and_me_endpoints():
    """Verify POST /api/v1/auth/token issues tokens and GET /api/v1/auth/me returns identity."""
    org_id = uuid4()
    user_id = uuid4()

    resp = client.post(
        "/api/v1/auth/token",
        json={"organization_id": str(org_id), "user_id": str(user_id), "role": "admin", "expires_in_seconds": 3600},
    )
    assert resp.status_code == 200
    data = resp.json()
    token = data["access_token"]
    assert data["token_type"] == "Bearer"
    assert data["organization_id"] == str(org_id)
    assert data["user_id"] == str(user_id)

    # Call /me endpoint with Bearer token
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["organization_id"] == str(org_id)
    assert me_data["user_id"] == str(user_id)
    assert me_data["role"] == "admin"
    assert me_data["is_authenticated"] is True


# ---------------------------------------------------------------------------
# 2. Server-Derived Organization Identity (Never Caller Query Param)
# ---------------------------------------------------------------------------

def test_organization_identity_server_derived_not_from_query_param(
    org_a_id, org_b_id, auth_headers_org_a, auth_headers_org_b
):
    """Verify caller cannot supply ?organization_id to access another organization's candidates."""
    # Create candidate in Org A
    cand_a_resp = client.post(
        "/api/v1/candidates",
        json={"display_name": "Org A Candidate", "primary_email": "orga@example.com"},
        headers=auth_headers_org_a,
    )
    assert cand_a_resp.status_code == 201
    cand_a_id = cand_a_resp.json()["id"]

    # Org B calls GET /candidates with ?organization_id=<org_a_id> trying to access Org A
    spoof_resp = client.get(f"/api/v1/candidates?organization_id={org_a_id}", headers=auth_headers_org_b)
    assert spoof_resp.status_code == 200
    candidates = spoof_resp.json()
    # Server derived tenant identity from Org B's token; Candidate A must NOT be visible!
    assert all(c["id"] != cand_a_id for c in candidates)


# ---------------------------------------------------------------------------
# 3. Multi-Tenant Scoping across All Protected Endpoints
# ---------------------------------------------------------------------------

def test_org_a_candidate_cannot_be_read_by_org_b(
    org_a_id, org_b_id, auth_headers_org_a, auth_headers_org_b
):
    """Comprehensive test: Org A candidate cannot be accessed by Org B across any endpoint."""
    # Step 1: Create candidate under Org A
    create_resp = client.post(
        "/api/v1/candidates",
        json={
            "display_name": "Alice Backend Lead",
            "primary_email": "alice@orga.com",
            "manifest_data": {"skills": ["Python", "FastAPI", "PostgreSQL"]},
        },
        headers=auth_headers_org_a,
    )
    assert create_resp.status_code == 201
    candidate_a_id = create_resp.json()["id"]

    # Step 2: Register completed dossier and graph for Candidate A
    dossier, graph = make_test_dossier(candidate_a_id, org_a_id)

    # -----------------------------------------------------------------------
    # Endpoint 1: Candidate List
    # -----------------------------------------------------------------------
    # Org A sees Candidate A
    list_a = client.get("/api/v1/candidates", headers=auth_headers_org_a).json()
    assert any(c["id"] == candidate_a_id for c in list_a)
    # Org B does NOT see Candidate A
    list_b = client.get("/api/v1/candidates", headers=auth_headers_org_b).json()
    assert all(c["id"] != candidate_a_id for c in list_b)

    # -----------------------------------------------------------------------
    # Endpoint 2: Candidate Detail
    # -----------------------------------------------------------------------
    # Org A reads Candidate A -> 200
    detail_a = client.get(f"/api/v1/candidates/{candidate_a_id}", headers=auth_headers_org_a)
    assert detail_a.status_code == 200
    assert detail_a.json()["display_name"] == "Alice Backend Lead"
    # Org B attempts to read Candidate A -> 404 (Object IDs alone never authorize access)
    detail_b = client.get(f"/api/v1/candidates/{candidate_a_id}", headers=auth_headers_org_b)
    assert detail_b.status_code == 404

    # -----------------------------------------------------------------------
    # Endpoint 3: Candidate Dossier
    # -----------------------------------------------------------------------
    # Org A reads dossier -> 200
    dossier_a = client.get(f"/api/v1/dossier/{candidate_a_id}", headers=auth_headers_org_a)
    assert dossier_a.status_code == 200
    # Org B attempts to read dossier -> 404
    dossier_b = client.get(f"/api/v1/dossier/{candidate_a_id}", headers=auth_headers_org_b)
    assert dossier_b.status_code == 404

    # -----------------------------------------------------------------------
    # Endpoint 4: Evidence & Capability Provenance Trace
    # -----------------------------------------------------------------------
    # Org A traces provenance -> 200
    prov_a = client.get(
        f"/api/v1/dossier/{candidate_a_id}/provenance/{CapabilityKey.BACKEND_ENGINEERING.value}",
        headers=auth_headers_org_a,
    )
    assert prov_a.status_code == 200
    # Org B attempts to trace provenance -> 404
    prov_b = client.get(
        f"/api/v1/dossier/{candidate_a_id}/provenance/{CapabilityKey.BACKEND_ENGINEERING.value}",
        headers=auth_headers_org_b,
    )
    assert prov_b.status_code == 404

    # -----------------------------------------------------------------------
    # Endpoint 5: Candidate Evidence Graph (CEG)
    # -----------------------------------------------------------------------
    # Org A reads graph -> 200
    graph_a = client.get(f"/api/v1/dossier/{candidate_a_id}/graph", headers=auth_headers_org_a)
    assert graph_a.status_code == 200
    # Org B attempts to read graph -> 404
    graph_b = client.get(f"/api/v1/dossier/{candidate_a_id}/graph", headers=auth_headers_org_b)
    assert graph_b.status_code == 404

    # -----------------------------------------------------------------------
    # Endpoint 6: Interview Inquiry Probes
    # -----------------------------------------------------------------------
    # Org A reads probes -> 200
    probes_a = client.get(f"/api/v1/dossier/{candidate_a_id}/probes", headers=auth_headers_org_a)
    assert probes_a.status_code == 200
    # Org B attempts to read probes -> 404
    probes_b = client.get(f"/api/v1/dossier/{candidate_a_id}/probes", headers=auth_headers_org_b)
    assert probes_b.status_code == 404

    # -----------------------------------------------------------------------
    # Endpoint 7: Candidate Intelligence Export
    # -----------------------------------------------------------------------
    # Org A exports brief -> 200
    export_a = client.get(
        f"/api/v1/dossier/{candidate_a_id}/export?format=markdown",
        headers=auth_headers_org_a,
    )
    assert export_a.status_code == 200
    # Org B attempts to export brief -> 404
    export_b = client.get(
        f"/api/v1/dossier/{candidate_a_id}/export?format=markdown",
        headers=auth_headers_org_b,
    )
    assert export_b.status_code == 404

    # -----------------------------------------------------------------------
    # Endpoint 8: Interview Feedback Submission
    # -----------------------------------------------------------------------
    feedback_payload = {
        "candidate_id": str(candidate_a_id),
        "interviewer_name": "Bob Reviewer",
        "probe_evaluations": [],
        "overall_recommendation": "strong_hire",
        "overall_notes": "Great system design",
    }
    # Org B attempts to record interview feedback on Candidate A -> 404
    fb_b = client.post(
        "/api/v1/overrides/interview-feedback",
        json=feedback_payload,
        headers=auth_headers_org_b,
    )
    assert fb_b.status_code == 404
    # Org A records interview feedback -> 200
    fb_a = client.post(
        "/api/v1/overrides/interview-feedback",
        json=feedback_payload,
        headers=auth_headers_org_a,
    )
    assert fb_a.status_code == 200

    # -----------------------------------------------------------------------
    # Endpoint 9: Recruiter Weight Override
    # -----------------------------------------------------------------------
    override_payload = {
        "candidate_id": str(candidate_a_id),
        "role_weights": {CapabilityKey.BACKEND_ENGINEERING.value: 1.0},
        "justification": "Candidate has specialized backend domain experience",
    }
    # Org B attempts to override Candidate A -> 404
    ov_b = client.post(
        "/api/v1/overrides/recruiter",
        json=override_payload,
        headers=auth_headers_org_b,
    )
    assert ov_b.status_code == 404
    # Org A overrides Candidate A -> 200
    ov_a = client.post(
        "/api/v1/overrides/recruiter",
        json=override_payload,
        headers=auth_headers_org_a,
    )
    assert ov_a.status_code == 200

    # -----------------------------------------------------------------------
    # Endpoint 10: Audit Trail Retrieval
    # -----------------------------------------------------------------------
    # Org A retrieves audit trail -> 200
    audit_a = client.get(f"/api/v1/overrides/audit/{candidate_a_id}", headers=auth_headers_org_a)
    assert audit_a.status_code == 200
    assert len(audit_a.json()) >= 1
    # Org B attempts to retrieve audit trail -> 404
    audit_b = client.get(f"/api/v1/overrides/audit/{candidate_a_id}", headers=auth_headers_org_b)
    assert audit_b.status_code == 404

    # -----------------------------------------------------------------------
    # Endpoint 11: Pipeline Execution & Status
    # -----------------------------------------------------------------------
    # Org B attempts to trigger pipeline on Candidate A -> 404
    pipe_b = client.post(
        "/api/v1/pipeline/run",
        json={"candidate_id": str(candidate_a_id), "role": "backend"},
        headers=auth_headers_org_b,
    )
    assert pipe_b.status_code == 404

    # Org A triggers pipeline -> 200
    pipe_a = client.post(
        "/api/v1/pipeline/run",
        json={"candidate_id": str(candidate_a_id), "role": "backend"},
        headers=auth_headers_org_a,
    )
    assert pipe_a.status_code == 200
    run_a_id = pipe_a.json()["analysis_run_id"]

    # Org B attempts to check status of Org A's run -> 404
    status_b = client.get(f"/api/v1/pipeline/status/{run_a_id}", headers=auth_headers_org_b)
    assert status_b.status_code == 404

    # Org A checks status -> 200
    status_a = client.get(f"/api/v1/pipeline/status/{run_a_id}", headers=auth_headers_org_a)
    assert status_a.status_code == 200

    # Org B attempts to rescore Org A's run -> 404
    rescore_b = client.post(
        "/api/v1/pipeline/rescore",
        json={"run_id": run_a_id, "weights": {CapabilityKey.BACKEND_ENGINEERING.value: 1.0}},
        headers=auth_headers_org_b,
    )
    assert rescore_b.status_code == 404


# ---------------------------------------------------------------------------
# 4. Strict Authentication Enforcement Tests
# ---------------------------------------------------------------------------

def test_strict_authentication_enforcement(monkeypatch):
    """Verify HTTP 401 Unauthorized when AUTH_REQUIRED=True and token is missing or invalid."""
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)

    # 1. Missing Authorization header -> 401
    resp_unauth = client.get("/api/v1/candidates")
    assert resp_unauth.status_code == 401
    assert "WWW-Authenticate" in resp_unauth.headers
    assert "Authentication required" in resp_unauth.json()["detail"]

    # 2. Invalid Bearer token -> 401
    resp_bad = client.get("/api/v1/candidates", headers={"Authorization": "Bearer bad.token.signature"})
    assert resp_bad.status_code == 401

    # 3. Valid Bearer token succeeds -> 200
    valid_token = create_access_token(organization_id=uuid4())
    resp_good = client.get("/api/v1/candidates", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp_good.status_code == 200
