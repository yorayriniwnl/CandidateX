"""Integration tests for CCI end-to-end pipeline orchestration (Agent 13).

Verifies:
1. 10-stage analysis lifecycle execution from intake to dossier.
2. Missing evidence produces UNKNOWN (never 0.0).
3. Pure functional rescore without re-crawling.
4. FastAPI endpoints for pipeline execution, status, and rescore.
"""

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from cci.domain.contracts import EvidenceConfidenceFactors, EvidenceRecord
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.main import app
from cci.pipeline.orchestrator import (
    AnalysisStage,
    PipelineStatus,
    execute_analysis_pipeline,
    rescore_dossier,
)
from cci.pipeline.service import pipeline_service
from cci.research.scenarios import DemoRequest, make_scenario

client = TestClient(app)


def _high_fit_thin_evidence() -> list[EvidenceRecord]:
    """Saturate two role capabilities from one cluster without estimable CIs."""
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    records: list[EvidenceRecord] = []
    for capability in (
        CapabilityKey.BACKEND_ENGINEERING,
        CapabilityKey.DATABASE_ENGINEERING,
    ):
        for index in range(5):
            records.append(
                EvidenceRecord(
                    evidence_id=uuid4(),
                    fingerprint=f"{capability.value}-{index}",
                    source_family=SourceFamily.GITHUB,
                    source_locator="https://github.com/candidate/one",
                    immutable_revision="one-revision",
                    target_capability=capability,
                    support_score=96.0,
                    confidence_factors=factors,
                    confidence=1.0,
                    cluster_id="project-one",
                    provenance={
                        "artifact_path": "src/service.py",
                        "raw_support_text": "Python and PostgreSQL implementation",
                    },
                )
            )
    return records


def test_pipeline_10_stages_execution():
    """Verify that all 10 stages execute and produce a valid Dossier."""
    cand_id = uuid4()
    state = execute_analysis_pipeline(
        candidate_id=cand_id,
        role=CanonicalRole.BACKEND,
        jd_text="Looking for Backend Engineer with Python, FastAPI, and Postgres experience.",
        cv_text="Alice Developer\nImplemented distributed key-value cache handling 10k RPS.\nBuilt database migrations.",
        repo_urls=["https://github.com/candidate/distributed-cache"],
        custom_evidence=make_scenario(DemoRequest(candidate_id=cand_id, scenario="sparse"))[0],
        evidence_mode="synthetic",
    )

    assert state.status == PipelineStatus.COMPLETED
    assert state.error is None
    assert state.dossier is not None

    # Verify all 10 stages are tracked and completed
    assert len(state.stages) == 10
    stage_enum_set = {s.stage for s in state.stages}
    for expected_stage in AnalysisStage:
        assert expected_stage in stage_enum_set

    for s in state.stages:
        assert s.status == "completed", f"Stage {s.stage} not completed: {s}"

    # Verify Dossier structure & math invariants
    dossier = state.dossier
    assert dossier.candidate_id == cand_id
    assert dossier.role == CanonicalRole.BACKEND
    assert dossier.rci is not None
    assert 0.0 <= dossier.rci <= 100.0
    assert 0.0 <= dossier.coverage <= 1.0

    # Invariant: Missing evidence must be UNKNOWN, never 0.0
    estimates = dossier.capability_estimates
    assert len(estimates) == 12

    # Observed capabilities should have non-null estimate
    assert estimates[CapabilityKey.BACKEND_ENGINEERING].is_observed is True
    assert estimates[CapabilityKey.BACKEND_ENGINEERING].estimate is not None

    # Unobserved capability must be UNKNOWN
    unobserved = estimates[CapabilityKey.MACHINE_LEARNING]
    assert unobserved.is_observed is False
    assert unobserved.estimate is None
    assert unobserved.coverage_k == 0.0

    # Interview probes must be ranked 1..12
    assert len(dossier.interview_probes) == 12
    ranks = [p.rank for p in dossier.interview_probes]
    assert sorted(ranks) == list(range(1, 13))

    # Evidence graph must be constructed
    assert state.ceg_graph is not None
    assert len(state.ceg_graph.nodes) > 0


def test_functional_rescore_without_recrawling():
    """Verify purely functional rescore without re-crawling or mutating original dossier."""
    cand_id = uuid4()
    state = execute_analysis_pipeline(
        candidate_id=cand_id,
        role=CanonicalRole.BACKEND,
        custom_evidence=make_scenario(DemoRequest(candidate_id=cand_id, scenario="sparse"))[0],
        evidence_mode="synthetic",
    )
    assert state.dossier is not None
    original_rci = state.dossier.rci

    # Apply heavy weight override to Database Engineering
    custom_weights = {
        CapabilityKey.DATABASE_ENGINEERING: 0.80,
        CapabilityKey.BACKEND_ENGINEERING: 0.10,
        CapabilityKey.TESTING_QUALITY: 0.10,
    }

    rescored = rescore_dossier(state.dossier, custom_weights)

    # Must produce new distinct dossier instance
    assert rescored.dossier_id != state.dossier.dossier_id
    assert rescored.candidate_id == state.dossier.candidate_id
    assert rescored.rci is not None
    assert (
        rescored.analysis_confidence.role_coverage
        != state.dossier.analysis_confidence.role_coverage
    )

    # Unobserved capabilities remain strictly UNKNOWN
    assert rescored.capability_estimates[CapabilityKey.FRONTEND_ENGINEERING].estimate is None
    assert rescored.capability_estimates[CapabilityKey.FRONTEND_ENGINEERING].is_observed is False


def test_pipeline_exposes_limited_confidence_for_thin_evidence():
    """A high RCI must not imply broad confidence from one evidence cluster."""
    state = execute_analysis_pipeline(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        custom_evidence=_high_fit_thin_evidence(),
        evidence_mode="synthetic",
    )

    assert state.status == PipelineStatus.COMPLETED
    assert state.dossier is not None
    assert state.dossier.rci is not None and state.dossier.rci > 90.0
    assert state.dossier.analysis_confidence.evidence_strength == "limited"
    assert "single_cluster" in state.dossier.analysis_confidence.uncertainty_flags
    assert "interval_unavailable" in state.dossier.analysis_confidence.uncertainty_flags


def test_pipeline_api_lifecycle():
    """Test full FastAPI lifecycle: run pipeline, query status, and rescore."""
    cand_id = str(uuid4())

    # 1. Trigger Run
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
    assert data["rci"] is None  # URLs and self-claims are not analyzed observations
    assert len(data["stages"]) == 10

    # 2. Query Status
    status_resp = client.get(f"/api/v1/pipeline/status/{run_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["analysis_run_id"] == run_id
    assert status_data["status"] == "completed"

    # 3. Rescore Run
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
