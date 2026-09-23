"""Production boundary tests for the public synthetic-only demonstration."""
import sys
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app import app
from cci.domain.enums import CanonicalRole
from cci.pipeline.orchestrator import PipelineExecutionState, PipelineStatus
from cci.pipeline.service import pipeline_service

client = TestClient(app)
PUBLIC_CANDIDATE_ID = "d3333333-3333-4333-8333-333333333333"
CONTROLS = {
    "scenario": "consistent",
    "role": "backend",
    "excluded_sources": [],
    "ownership_multiplier": 1,
    "reliability_false_positives": 0,
}


@pytest.mark.parametrize(("method", "path"), [
    ("POST", "/api/v1/live/intake"),
    ("POST", "/api/v1/live/analyze"),
    ("GET", "/api/v1/candidates"),
    ("GET", "/api/v1/jobs"),
    ("GET", "/api/v1/dossier/11111111-1111-1111-1111-111111111111"),
    ("POST", "/api/v1/pipeline/run"),
    ("POST", "/api/v1/overrides/interview-feedback"),
])
def test_vercel_app_does_not_mount_live_or_persistent_apis(method, path):
    response = client.request(method, path, json={})
    assert response.status_code == 404


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_public_backend_does_not_expose_automatic_api_docs(path):
    response = client.get(path)
    assert response.status_code == 404


@pytest.mark.parametrize("extra", [
    {"candidate_id": "11111111-1111-1111-1111-111111111111"},
    {"resume_text": "Example person"},
    {"github_urls": ["https://github.com/example"]},
    {"linkedin_url": "https://linkedin.com/in/example"},
    {"profile_url": "https://example.test/profile"},
    {"jd_text": "Candidate Alice"},
])
def test_public_demo_rejects_candidate_data_fields(extra):
    response = client.post(
        "/api/v1/synthetic-demo/run", json={"scenario": "consistent", **extra}
    )
    assert response.status_code == 422


def test_populated_run_returns_generated_evidence_with_fixed_identity():
    response = client.post("/api/v1/synthetic-demo/run", json=CONTROLS)
    assert response.status_code == 200, response.text
    result = response.json()
    dossier = result["dossier"]
    assert dossier["evidence_mode"] == "synthetic"
    assert dossier["candidate_id"] == PUBLIC_CANDIDATE_ID
    assert dossier["evidence_records"]
    assert result["graph"]["analysis_run_id"] == dossier["analysis_run_id"]
    notice = result["storage_notice"].lower()
    assert "no candidate data" in notice
    assert "no run state" in notice


def test_empty_scenario_keeps_capability_unknown():
    response = client.post(
        "/api/v1/synthetic-demo/run", json={**CONTROLS, "scenario": "empty"}
    )
    assert response.status_code == 200, response.text
    dossier = response.json()["dossier"]
    assert dossier["evidence_mode"] == "synthetic"
    assert dossier["candidate_id"] == PUBLIC_CANDIDATE_ID
    assert dossier["rci"] is None
    assert dossier["coverage"] == 0
    assert all(
        estimate["estimate"] is None
        for estimate in dossier["capability_estimates"].values()
    )


def test_incomplete_pipeline_returns_error_without_substituting_a_result(monkeypatch):
    module = sys.modules.get("cci.api.routers.synthetic_demo")
    if module is not None:
        failed_state = PipelineExecutionState(
            analysis_run_id=uuid4(),
            candidate_id=UUID(PUBLIC_CANDIDATE_ID),
            role=CanonicalRole.BACKEND,
            status=PipelineStatus.FAILED,
        )
        monkeypatch.setattr(
            module, "execute_analysis_pipeline", lambda *_args, **_kwargs: failed_state
        )

    response = client.post("/api/v1/synthetic-demo/run", json=CONTROLS)
    assert response.status_code == 500
    assert "dossier" not in response.json()


def test_rescore_works_without_a_prior_run_or_process_local_cache(monkeypatch):
    def fail_if_cache_is_used(*_args, **_kwargs):
        pytest.fail("synthetic rescore must not consult process-local run state")

    monkeypatch.setattr(pipeline_service, "rescore_run", fail_if_cache_is_used)
    response = client.post(
        "/api/v1/synthetic-demo/rescore",
        json={**CONTROLS, "weights": {"backend_engineering": 1}},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["dossier"]["candidate_id"] == PUBLIC_CANDIDATE_ID
    assert result["graph"]["analysis_run_id"] == result["dossier"]["analysis_run_id"]


@pytest.mark.parametrize("weights", [{}, {"backend_engineering": -1}])
def test_invalid_synthetic_rescore_weights_are_rejected(weights):
    response = client.post(
        "/api/v1/synthetic-demo/rescore", json={**CONTROLS, "weights": weights}
    )
    assert response.status_code == 422
