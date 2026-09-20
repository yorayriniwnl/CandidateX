"""Unit tests for Job Description parser and Candidate Directory API routers."""

import uuid
from fastapi.testclient import TestClient
import pytest

from cci.main import app
import cci.db.repository as repo
from cci.domain.contracts import CandidateManifest
from cci.domain.enums import CanonicalRole

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


def test_get_candidate_not_found():
    """Verify GET /api/v1/candidates/{id} returns 404 for unknown candidate."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/candidates/{random_id}")
    assert response.status_code == 404
