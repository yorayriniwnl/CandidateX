import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from cci.main import app

client = TestClient(app)


def test_candidates_endpoint_post_and_list():
    test_id = str(uuid4())
    payload = {
        "id": test_id,
        "display_name": "Dr. Sarah Connor",
        "primary_email": "sarah.connor@example.com",
        "has_completed_dossier": True,
        "rci": 94.2,
        "jd_fit_score": 94.2,
        "observed_capabilities": 10,
        "coverage": 0.88,
        "role": "backend",
        "has_meaningful_conflict": False,
        "manifest_data": {
            "candidate_id": test_id,
            "full_name": "Dr. Sarah Connor",
            "declared_skills": ["Rust", "Distributed Systems", "C++"],
        }
    }

    # Test POST /api/v1/candidates
    res = client.post("/api/v1/candidates", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == test_id
    assert data["display_name"] == "Dr. Sarah Connor"
    assert data["rci"] == 94.2
    assert data["jd_fit_score"] == 94.2
    assert data["observed_capabilities"] == 10
    assert data["role"] == "backend"

    # Test GET /api/v1/candidates includes the saved candidate
    list_res = client.get("/api/v1/candidates")
    assert list_res.status_code == 200
    candidates = list_res.json()
    matched = [c for c in candidates if c["id"] == test_id]
    assert len(matched) == 1
    assert matched[0]["display_name"] == "Dr. Sarah Connor"
    assert matched[0]["rci"] == 94.2
    assert matched[0]["jd_fit_score"] == 94.2
    assert matched[0]["observed_capabilities"] == 10
