"""Tests for Recruiter Overrides and Interview Feedback API."""

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


@pytest.fixture
def candidate_dossier() -> Dossier:
    """Fixture creating a test dossier with known scores for functional rescore verification."""
    cand_id = uuid4()
    estimates = {}
    conflicts = {}

    for key in CapabilityKey:
        if key == CapabilityKey.BACKEND_ENGINEERING:
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=90.0,
                is_observed=True,
                effective_evidence_count=5.0,
                raw_evidence_count=8,
                coverage_k=0.90,
            )
        elif key == CapabilityKey.DATABASE_ENGINEERING:
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=70.0,
                is_observed=True,
                effective_evidence_count=4.0,
                raw_evidence_count=6,
                coverage_k=0.70,
            )
        else:
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=None,
                is_observed=False,
                effective_evidence_count=0.0,
                raw_evidence_count=0,
                coverage_k=0.0,
            )

        conflicts[key] = CapabilityConflict(
            capability_key=key,
            positive_support_sum=5.0 if key == CapabilityKey.BACKEND_ENGINEERING else 0.0,
            negative_support_sum=0.0,
            contradiction_diagnostic=0.95 if key == CapabilityKey.BACKEND_ENGINEERING else 0.0,
        )

    # Initial RCI with equal weights 0.5 Backend (90.0) and 0.5 Database (70.0) -> 80.0
    return Dossier(
        dossier_id=uuid4(),
        candidate_id=cand_id,
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
        rci=80.0,
        coverage=0.40,
        is_insufficient_evidence=False,
        capability_estimates=estimates,
        capability_conflicts=conflicts,
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
    )


def test_recruiter_override_functional_rescore(candidate_dossier):
    """Verifies that recruiter weight adjustment accurately rescores RCI and emits audit log."""
    register_dossier(candidate_dossier)
    client = TestClient(app)

    # Shift weights heavily to Backend Engineering (0.80) vs Database (0.20)
    # Expected RCI = 0.8 * 90.0 + 0.2 * 70.0 = 72.0 + 14.0 = 86.0
    weights_payload = {
        CapabilityKey.BACKEND_ENGINEERING.value: 0.80,
        CapabilityKey.DATABASE_ENGINEERING.value: 0.20,
    }

    req_body = {
        "candidate_id": str(candidate_dossier.candidate_id),
        "role_weights": weights_payload,
        "justification": "Candidate is applying for a pure distributed backend role with minimal SQL demands.",
    }

    res = client.post("/api/v1/overrides/recruiter", json=req_body)
    assert res.status_code == 200

    data = res.json()
    assert data["candidate_id"] == str(candidate_dossier.candidate_id)
    assert data["previous_rci"] == 80.0
    assert abs(data["rescored_rci"] - 86.0) < 1e-3
    assert data["audit_event_id"] is not None
    assert "pure distributed backend" in data["justification"]
    assert data["dossier"]["rci"] == data["rescored_rci"]


def test_recruiter_override_validation():
    """Verifies error handling for missing candidates and invalid weights."""
    client = TestClient(app)

    # 404 for unknown candidate
    res_404 = client.post(
        "/api/v1/overrides/recruiter",
        json={
            "candidate_id": str(uuid4()),
            "role_weights": {CapabilityKey.BACKEND_ENGINEERING.value: 1.0},
            "justification": "Valid justification string",
        },
    )
    assert res_404.status_code == 404

    # 422 for negative weights
    res_invalid = client.post(
        "/api/v1/overrides/recruiter",
        json={
            "candidate_id": str(uuid4()),
            "role_weights": {CapabilityKey.BACKEND_ENGINEERING.value: -0.5},
            "justification": "Short",
        },
    )
    assert res_invalid.status_code == 422


def test_interview_feedback_recording():
    """Verifies that interview probe inquiry evaluations are recorded to the audit trail."""
    client = TestClient(app)
    cand_id = uuid4()

    feedback_body = {
        "candidate_id": str(cand_id),
        "interviewer_name": "Dr. Sarah Jenkins",
        "probe_evaluations": [
            {
                "capability_key": CapabilityKey.SOFTWARE_ARCHITECTURE.value,
                "rating": 5,
                "notes": "Candidate clearly articulated saga pattern and outbox delivery semantics.",
                "is_gap_resolved": True,
            }
        ],
        "overall_recommendation": "strong_hire",
        "overall_notes": "Exceeded senior engineering expectations during technical design round.",
    }

    res = client.post("/api/v1/overrides/interview-feedback", json=feedback_body)
    assert res.status_code == 200

    data = res.json()
    assert data["candidate_id"] == str(cand_id)
    assert data["interviewer_name"] == "Dr. Sarah Jenkins"
    assert data["evaluations_count"] == 1
    assert data["audit_event_id"] is not None


def test_candidate_audit_trail_retrieval(candidate_dossier):
    """Verifies that GET /api/v1/overrides/audit/{candidate_id} returns all recorded events."""
    register_dossier(candidate_dossier)
    client = TestClient(app)
    cand_id = candidate_dossier.candidate_id

    # 1. Submit weight override
    client.post(
        "/api/v1/overrides/recruiter",
        json={
            "candidate_id": str(cand_id),
            "role_weights": {CapabilityKey.BACKEND_ENGINEERING.value: 1.0},
            "justification": "Candidate audit history test justification",
        },
    )

    # 2. Submit interview feedback
    client.post(
        "/api/v1/overrides/interview-feedback",
        json={
            "candidate_id": str(cand_id),
            "interviewer_name": "Marcus Aurelius",
            "probe_evaluations": [],
            "overall_recommendation": "lean_hire",
            "overall_notes": "Solid fundamentals.",
        },
    )

    # 3. Retrieve audit trail
    res = client.get(f"/api/v1/overrides/audit/{cand_id}")
    assert res.status_code == 200

    events = res.json()
    assert len(events) >= 2
    types = [e["event_type"] for e in events]
    assert "recruiter_weight_override" in types
    assert "interviewer_probe_feedback" in types

