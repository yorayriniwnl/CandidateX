"""Unit tests for durable AnalysisRun execution engine and state machine (Fix 26).

Verifies that synchronous single-request analysis is replaced with a persistent,
resumable, idempotent, and pollable AnalysisRun:
1. Complete 18-state lifecycle:
   * QUEUED
   * PARSING_RESUME
   * EXTRACTING_CLAIMS
   * DISCOVERING_SOURCES
   * FETCHING_SOURCES
   * ANALYZING_GITHUB
   * ANALYZING_DEPLOYMENTS
   * ANALYZING_CREDENTIALS
   * ANALYZING_ACADEMICS
   * ANALYZING_PROJECTS
   * CORROBORATING_CLAIMS
   * COMPUTING_SIGNALS
   * BUILDING_GRAPH
   * BUILDING_DOSSIER
   * COMPLETED
   * PARTIAL
   * FAILED
   * CANCELLED
2. Idempotence: re-executing stages does not duplicate work.
3. Resumability: failed or interrupted runs resume from the last incomplete stage.
4. Cancellation: runs can be cancelled cleanly.
5. Polling & API surface: POST /runs, GET /runs/{id}, POST /runs/{id}/resume, POST /runs/{id}/cancel.
"""

import time
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest

from cci.domain.enums import AnalysisRunState
from cci.live.runner import (
    AnalysisRunManager,
    DurableAnalysisRun,
    PIPELINE_STAGES,
    get_analysis_run_manager,
)
from cci.live_app import app

client = TestClient(app)


def test_analysis_run_state_all_eighteen_states_present():
    """Verify that all 18 mandated states exist in AnalysisRunState."""
    expected_states = {
        "QUEUED",
        "PARSING_RESUME",
        "EXTRACTING_CLAIMS",
        "DISCOVERING_SOURCES",
        "FETCHING_SOURCES",
        "ANALYZING_GITHUB",
        "ANALYZING_DEPLOYMENTS",
        "ANALYZING_CREDENTIALS",
        "ANALYZING_ACADEMICS",
        "ANALYZING_PROJECTS",
        "CORROBORATING_CLAIMS",
        "COMPUTING_SIGNALS",
        "BUILDING_GRAPH",
        "BUILDING_DOSSIER",
        "COMPLETED",
        "PARTIAL",
        "FAILED",
        "CANCELLED",
    }
    actual_states = {s.value for s in AnalysisRunState}
    assert expected_states.issubset(actual_states)
    assert len(expected_states) == 18

    # Terminal states
    assert AnalysisRunState.COMPLETED.is_terminal is True
    assert AnalysisRunState.PARTIAL.is_terminal is True
    assert AnalysisRunState.FAILED.is_terminal is True
    assert AnalysisRunState.CANCELLED.is_terminal is True
    assert AnalysisRunState.QUEUED.is_terminal is False
    assert AnalysisRunState.ANALYZING_GITHUB.is_terminal is False


def test_analysis_run_idempotence():
    """Verify that running a stage multiple times returns cached stage data without re-executing."""
    manager = AnalysisRunManager()
    run = manager.create_run({"role": "backend", "intake": {"manifest": {"claimed_skills": ["Python"]}}}, auto_start=False)

    # Pre-populate stage data for PARSING_RESUME
    run.stage_data[AnalysisRunState.PARSING_RESUME.value] = {"candidate_id": "test-id", "cached": True}

    output = manager._run_stage(run, AnalysisRunState.PARSING_RESUME)
    # The output is cached in run.stage_data
    assert run.stage_data[AnalysisRunState.PARSING_RESUME.value]["cached"] is True


def test_analysis_run_resumability():
    """Verify that a failed or interrupted run resumes from the first incomplete stage."""
    manager = AnalysisRunManager()
    run = manager.create_run({"role": "backend"}, auto_start=False)

    # Simulate completed early stages
    run.stage_data[AnalysisRunState.PARSING_RESUME.value] = {"status": "parsed"}
    run.stage_data[AnalysisRunState.EXTRACTING_CLAIMS.value] = {"claimed_skills": ["Python"]}
    run.stage_data[AnalysisRunState.DISCOVERING_SOURCES.value] = {"extracted_urls": []}
    run.stage_data[AnalysisRunState.FETCHING_SOURCES.value] = {"public_sources": []}
    run.stage_data[AnalysisRunState.ANALYZING_GITHUB.value] = {"github_sources": []}
    run.stage_data[AnalysisRunState.ANALYZING_DEPLOYMENTS.value] = {"deployment_sources": []}
    run.stage_data[AnalysisRunState.ANALYZING_CREDENTIALS.value] = {"credential_status": "evaluated"}
    run.stage_data[AnalysisRunState.ANALYZING_ACADEMICS.value] = {"academic_status": "evaluated"}
    run.stage_data[AnalysisRunState.ANALYZING_PROJECTS.value] = {"project_status": "evaluated"}
    run.stage_data[AnalysisRunState.CORROBORATING_CLAIMS.value] = {"contradictions_evaluated": True}
    run.stage_data[AnalysisRunState.COMPUTING_SIGNALS.value] = {"signals_computed": True}
    run.stage_data[AnalysisRunState.BUILDING_GRAPH.value] = {"graph_prebuilt": True}
    run.stage_data[AnalysisRunState.BUILDING_DOSSIER.value] = {"dossier": {}, "sources": [], "status": "completed"}

    run.state = AnalysisRunState.FAILED
    run.error_message = "Simulated transient failure"

    # Resume the run synchronously
    resumed = manager.resume_run(run.analysis_run_id, sync=True)
    assert resumed is not None
    assert resumed.state in (AnalysisRunState.COMPLETED, AnalysisRunState.PARTIAL)
    assert resumed.error_message is None
    assert resumed.progress_percent == 100.0


def test_analysis_run_cancellation():
    """Verify that an active or queued run can be cancelled cleanly."""
    manager = AnalysisRunManager()
    run = manager.create_run({"role": "backend"}, auto_start=False)
    assert run.state == AnalysisRunState.QUEUED

    cancelled = manager.cancel_run(run.analysis_run_id)
    assert cancelled is not None
    assert cancelled.state == AnalysisRunState.CANCELLED
    assert cancelled.completed_at is not None


def test_analysis_run_api_endpoints():
    """Verify REST API lifecycle endpoints for AnalysisRun."""
    payload = {
        "role": "backend",
        "intake": {
            "candidate_id": str(uuid4()),
            "manifest": {
                "claimed_skills": ["Python", "Docker"],
                "github_urls": ["https://github.com/example/api"],
            },
        },
    }

    # 1. Create run (POST /api/v1/live/runs) -> 202 Accepted
    response = client.post("/api/v1/live/runs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "analysis_run_id" in data
    assert data["state"] in {"QUEUED", "PARSING_RESUME"}
    assert "poll_url" in data
    run_id = data["analysis_run_id"]

    # 2. Poll run status (GET /api/v1/live/runs/{run_id}) -> 200 OK
    status_response = client.get(f"/api/v1/live/runs/{run_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["analysis_run_id"] == run_id
    assert status_data["state"] in {s.value for s in AnalysisRunState}
    assert "progress_percent" in status_data
    assert "completed_stages" in status_data

    # 3. Cancel run (POST /api/v1/live/runs/{run_id}/cancel) -> 200 OK
    cancel_response = client.post(f"/api/v1/live/runs/{run_id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["state"] == "CANCELLED"

    # 4. Resume run (POST /api/v1/live/runs/{run_id}/resume) -> 200 OK
    resume_response = client.post(f"/api/v1/live/runs/{run_id}/resume")
    assert resume_response.status_code == 200

    # 5. Non-existent run -> 404
    missing_id = str(uuid4())
    assert client.get(f"/api/v1/live/runs/{missing_id}").status_code == 404
