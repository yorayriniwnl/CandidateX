"""Unit test for asynchronous pipeline execution."""

from uuid import uuid4
from fastapi.testclient import TestClient
from cci.main import app

client = TestClient(app)


def test_async_pipeline_execution():
    """Verify that POST /api/v1/pipeline/run?run_async=true returns immediately with RUNNING state."""
    cand_id = str(uuid4())
    res = client.post(
        "/api/v1/pipeline/run?run_async=true",
        json={
            "candidate_id": cand_id,
            "role": "backend",
            "declared_claims": ["FastAPI", "Python", "Docker"],
            "repo_urls": ["https://github.com/torvalds/linux"],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "running"
    assert "analysis_run_id" in data
    assert data["candidate_id"] == cand_id

    # Verify run ID can be queried immediately via status endpoint
    run_id = data["analysis_run_id"]
    status_res = client.get(f"/api/v1/pipeline/status/{run_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["analysis_run_id"] == run_id
