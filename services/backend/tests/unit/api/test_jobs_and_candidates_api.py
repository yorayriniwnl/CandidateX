"""Unit tests for Job Description parser and Candidate Directory API routers."""

import uuid
from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi.testclient import TestClient
import pytest

from cci.main import app
import cci.db.repository as repo
from cci.domain.contracts import CandidateManifest, ObservedIndexContext
from cci.domain.enums import CanonicalRole, EvidenceState
from cci.api.routers import candidates as candidates_router
from cci.api.routers.candidates import CandidateSummaryResponse

client = TestClient(app)


def test_job_parse_endpoint():
    """Verify POST /api/v1/jobs/parse extracts requirements and role weights."""
    sample_jd = """
    # Senior Backend Engineer
    Mandatory Requirements:
    - 5+ years of experience with Python, FastAPI, and PostgreSQL.
    - Deep expertise in relational schema design and query optimization.
    - Strong unit and integration testing habits (pytest/mocks).
    Preferred:
    - Experience with Docker, Kubernetes, and automated CI/CD.
    - Knowledge of Kafka and distributed event streaming.
    """
    response = client.post(
        "/api/v1/jobs/parse",
        json={"jd_text": sample_jd, "role": "backend"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "backend"
    assert data["requirements_count"] > 0
    assert len(data["requirements"]) > 0

    # Role profile checks
    profile = data["role_profile"]
    assert profile["canonical_role"] == "backend"
    softmax_weights = profile["softmax_weights"]
    assert len(softmax_weights) == 12
    total_weights = sum(softmax_weights.values())
    assert pytest.approx(total_weights, abs=1e-3) == 1.0


def test_list_jobs_endpoint():
    """Verify GET /api/v1/jobs returns status 200."""
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_candidates_endpoint():
    """Verify GET /api/v1/candidates returns status 200."""
    response = client.get("/api/v1/candidates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_candidate_summary_contract_exposes_observed_index_context():
    assert "observed_capability_index" in CandidateSummaryResponse.model_fields
    assert "observed_index_context" in CandidateSummaryResponse.model_fields
    assert "evidence_state" in CandidateSummaryResponse.model_fields
    assert "coverage_sufficiency_threshold" in CandidateSummaryResponse.model_fields


def test_candidate_summary_api_returns_context_for_partial_index(monkeypatch):
    candidate_id = uuid.uuid4()
    context = ObservedIndexContext(
        role_weighted_evidence_coverage=0.2,
        observed_role_dimensions=1,
        coverage_sufficiency_threshold=0.35,
        is_insufficient_evidence=True,
        evidence_state=EvidenceState.INSUFFICIENT,
        standalone_presentation_allowed=False,
        unique_independent_source_cluster_count=2,
        independent_source_cluster_counts_by_capability={},
    )
    candidate = SimpleNamespace(
        id=candidate_id,
        display_name="Test Candidate",
        primary_email=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    dossier = SimpleNamespace(
        rci=76.5,
        observed_capability_index=76.5,
        observed_index_context=context,
        coverage=0.2,
        coverage_sufficiency_threshold=0.35,
        evidence_state=EvidenceState.INSUFFICIENT,
        role=CanonicalRole.BACKEND,
        capability_conflicts={},
    )
    monkeypatch.setattr(
        candidates_router, "SessionLocal", lambda: nullcontext(object())
    )
    monkeypatch.setattr(
        candidates_router.repo, "list_candidates", lambda db, **kwargs: [candidate]
    )
    monkeypatch.setattr(
        candidates_router.repo,
        "get_dossier_by_candidate_id",
        lambda db, _candidate_id: dossier,
    )

    response = client.get("/api/v1/candidates")

    assert response.status_code == 200
    summary = response.json()[0]
    assert summary["rci"] == 76.5
    assert summary["observed_capability_index"] == 76.5
    assert summary["coverage_sufficiency_threshold"] == 0.35
    assert summary["evidence_state"] == "INSUFFICIENT"
    assert summary["observed_index_context"]["standalone_presentation_allowed"] is False
    assert summary["observed_index_context"]["metric_label"] == "Observed Capability Index"


def test_candidate_without_dossier_is_unknown_not_robust(monkeypatch):
    candidate = SimpleNamespace(
        id=uuid.uuid4(),
        display_name="No Dossier",
        primary_email=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        candidates_router, "SessionLocal", lambda: nullcontext(object())
    )
    monkeypatch.setattr(
        candidates_router.repo, "list_candidates", lambda db, **kwargs: [candidate]
    )
    monkeypatch.setattr(
        candidates_router.repo,
        "get_dossier_by_candidate_id",
        lambda db, _candidate_id: None,
    )

    response = client.get("/api/v1/candidates")

    assert response.status_code == 200
    summary = response.json()[0]
    assert summary["coverage"] is None
    assert summary["coverage_sufficiency_threshold"] is None
    assert summary["evidence_state"] == "UNKNOWN"


def test_get_candidate_not_found():
    """Verify GET /api/v1/candidates/{id} returns 404 for unknown candidate."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/candidates/{random_id}")
    assert response.status_code == 404
