"""Integration tests for CCI end-to-end pipeline orchestration.

Verifies:
1. 10-stage analysis lifecycle execution from intake to dossier.
2. Missing extracted evidence produces UNKNOWN (never invented scores).
3. Pure functional rescore without re-crawling.
4. FastAPI endpoints for pipeline execution, status, and rescore.
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.main import app
from cci.pipeline.orchestrator import (
    AnalysisStage,
    PipelineStatus,
    execute_analysis_pipeline,
    rescore_dossier,
)

client = TestClient(app)


def test_pipeline_10_stages_execution_without_extracted_evidence():
    """Declared text/URLs alone must not become capability evidence."""
    cand_id = uuid4()
    state = execute_analysis_pipeline(
        candidate_id=cand_id,
        role=CanonicalRole.BACKEND,
        jd_text="Looking for Backend Engineer with Python, FastAPI, and Postgres experience.",
        cv_text="Alice Developer\nImplemented distributed key-value cache handling 10k RPS.\nBuilt database migrations.",
        repo_urls=["https://github.com/candidate/distributed-cache"],
    )

    assert state.status == PipelineStatus.COMPLETED
    assert state.error is None
    assert state.dossier is not None

    assert len(state.stages) == 10
    stage_enum_set = {s.stage for s in state.stages}
    for expected_stage in AnalysisStage:
        assert expected_stage in stage_enum_set

    for stage in state.stages:
        assert stage.status == "completed", f"Stage {stage.stage} not completed: {stage}"

    dossier = state.dossier
    assert dossier.candidate_id == cand_id
    assert dossier.role == CanonicalRole.BACKEND
    assert dossier.rci is None
    assert dossier.coverage == 0.0
    assert dossier.is_insufficient_evidence is True
    assert dossier.ownership_assessments == []

    estimates = dossier.capability_estimates
    assert len(estimates) == len(CapabilityKey)
    assert all(est.is_observed is False for est in estimates.values())
    assert all(est.estimate is None for est in estimates.values())
    assert all(est.coverage_k == 0.0 for est in estimates.values())

    assert len(dossier.interview_probes) == len(CapabilityKey)
    ranks = [probe.rank for probe in dossier.interview_probes]
    assert sorted(ranks) == list(range(1, len(CapabilityKey) + 1))

    assert state.ceg_graph is not None
    assert len(state.ceg_graph.nodes) == len(CapabilityKey)


def test_functional_rescore_without_recrawling_preserves_unknowns():
    """Rescoring cannot turn missing evidence into a score."""
    state = execute_analysis_pipeline(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
    )
    assert state.dossier is not None
    assert state.dossier.rci is None

    custom_weights = {
        CapabilityKey.DATABASE_ENGINEERING: 0.80,
        CapabilityKey.BACKEND_ENGINEERING: 0.10,
        CapabilityKey.TESTING_QUALITY: 0.10,
    }

    rescored = rescore_dossier(state.dossier, custom_weights)

    assert rescored.dossier_id != state.dossier.dossier_id
    assert rescored.candidate_id == state.dossier.candidate_id
    assert rescored.rci is None
    assert rescored.coverage == 0.0
    assert all(est.estimate is None for est in rescored.capability_estimates.values())
    assert all(est.is_observed is False for est in rescored.capability_estimates.values())


def test_pipeline_api_lifecycle_is_honest_without_analyzer_evidence():
    """The API may complete intake, but must return no RCI until evidence exists."""
    cand_id = str(uuid4())

    payload = {
        "candidate_id": cand_id,
        "role": "backend",
        "jd_text": "Need senior backend engineer with asyncio and database skills.",
        "cv_text": "Experienced Python and SQL developer.",
        "repo_urls": ["https://github.com/alice/repo-test"],
        "declared_claims": ["Designed fast SQL indexing strategy"],
    }
    response = client.post("/api/v1/pipeline/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    run_id = data["analysis_run_id"]
    assert data["status"] == "completed"
    assert data["dossier_id"] is not None
    assert data["rci"] is None
    assert data["coverage"] == 0.0
    assert len(data["stages"]) == 10

    status_resp = client.get(f"/api/v1/pipeline/status/{run_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["analysis_run_id"] == run_id
    assert status_data["status"] == "completed"
    assert status_data["rci"] is None
    assert status_data["coverage"] == 0.0

    rescore_payload = {
        "run_id": run_id,
        "weights": {
            "backend_engineering": 0.50,
            "database_engineering": 0.50,
        },
    }
    rescore_resp = client.post("/api/v1/pipeline/rescore", json=rescore_payload)
    assert rescore_resp.status_code == 200
    rescored_data = rescore_resp.json()
    assert rescored_data["rci"] is None
    assert rescored_data["coverage"] == 0.0


def test_pipeline_api_404_not_found():
    """Verify proper 404 handling for invalid run IDs."""
    fake_id = str(uuid4())
    status_resp = client.get(f"/api/v1/pipeline/status/{fake_id}")
    assert status_resp.status_code == 404

    rescore_resp = client.post(
        "/api/v1/pipeline/rescore",
        json={"run_id": fake_id, "weights": {"backend_engineering": 1.0}},
    )
    assert rescore_resp.status_code == 404
