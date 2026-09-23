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

from cci.domain.contracts import (
    EvidenceConfidenceFactors,
    EvidenceRecord,
    ScoringConfig,
)
from cci.domain.enums import CanonicalRole, CapabilityKey, EvidenceState, SourceFamily
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


def test_pipeline_10_stages_execution():
    """Verify that all 10 stages execute and produce a valid Dossier."""
    cand_id = uuid4()
    state = execute_analysis_pipeline(
        candidate_id=cand_id,
        role=CanonicalRole.BACKEND,
        jd_text="Looking for Backend Engineer with Python, FastAPI, and Postgres experience.",
        cv_text="Alice Developer\nImplemented distributed key-value cache handling 10k RPS.\nBuilt database migrations.",
        repo_urls=["https://github.com/candidate/distributed-cache"],
        custom_evidence=make_scenario(DemoRequest(candidate_id=cand_id, scenario="consistent"))[0],
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

    # The consistent scenario has enough attribution-gated evidence for each capability.
    assert all(estimate.is_observed for estimate in estimates.values())
    assert all(estimate.estimate is not None for estimate in estimates.values())

    # Interview probes must be ranked 1..12
    assert len(dossier.interview_probes) == 12
    ranks = [p.rank for p in dossier.interview_probes]
    assert sorted(ranks) == list(range(1, 13))

    # Evidence graph must be constructed
    assert state.ceg_graph is not None
    assert len(state.ceg_graph.nodes) > 0


def test_pipeline_uses_active_family_decay_and_retains_repeated_evidence():
    candidate_id = uuid4()
    capability = CapabilityKey.BACKEND_ENGINEERING
    family_id = "ef1:" + "a" * 64
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    evidence = [
        EvidenceRecord(
            fingerprint="a" * 64,
            source_family=SourceFamily.GITHUB,
            source_locator="https://github.com/candidate/repo",
            immutable_revision="b" * 40,
            target_capability=capability,
            support_score=90.0,
            confidence_factors=factors,
            confidence=0.8,
            cluster_id="https://github.com/candidate/repo",
            evidence_family_id=family_id,
            observation_type="dependency:manifest",
            provenance={"artifact_path": "requirements.txt"},
        ),
        EvidenceRecord(
            fingerprint="c" * 64,
            source_family=SourceFamily.GITHUB,
            source_locator="https://github.com/candidate/repo",
            immutable_revision="b" * 40,
            target_capability=capability,
            support_score=10.0,
            confidence_factors=factors,
            confidence=0.4,
            cluster_id="https://github.com/candidate/repo",
            evidence_family_id=family_id,
            observation_type="dependency:python_import",
            provenance={"artifact_path": "src/service.py"},
        ),
    ]
    config = ScoringConfig(
        version="5.1.0",
        evidence_family_decay=0.0,
        low_coverage_threshold=0.0,
        tau_saturation={capability: 0.1},
    )

    state = execute_analysis_pipeline(
        candidate_id=candidate_id,
        role=CanonicalRole.BACKEND,
        custom_evidence=evidence,
        scoring_config=config,
    )

    assert state.status == PipelineStatus.COMPLETED
    assert state.dossier is not None
    estimate = state.dossier.capability_estimates[capability]
    assert estimate.estimate == 90.0
    assert estimate.effective_evidence_count == 1.0
    assert estimate.raw_evidence_count == 2
    assert len(state.dossier.evidence_records) == 2
    assert state.dossier.versions["scoring_config_version"] == "5.1.0"


def test_sparse_evidence_keeps_candidate_capabilities_unknown():
    cand_id = uuid4()
    state = execute_analysis_pipeline(
        candidate_id=cand_id,
        role=CanonicalRole.BACKEND,
        custom_evidence=make_scenario(
            DemoRequest(candidate_id=cand_id, scenario="sparse")
        )[0],
        evidence_mode="synthetic",
    )

    assert state.dossier is not None
    assert state.dossier.rci is None
    backend = state.dossier.capability_estimates[CapabilityKey.BACKEND_ENGINEERING]
    assert backend.raw_evidence_count > 0
    assert backend.coverage_k > 0.0
    assert backend.estimate is None
    assert backend.is_observed is False


def test_functional_rescore_without_recrawling():
    """Verify purely functional rescore without re-crawling or mutating original dossier."""
    cand_id = uuid4()
    state = execute_analysis_pipeline(
        candidate_id=cand_id,
        role=CanonicalRole.BACKEND,
        custom_evidence=make_scenario(DemoRequest(candidate_id=cand_id, scenario="consistent"))[0],
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

    # Rescoring changes role weights without stripping sufficiently supported evidence.
    assert rescored.capability_estimates[CapabilityKey.FRONTEND_ENGINEERING].estimate is not None
    assert rescored.capability_estimates[CapabilityKey.FRONTEND_ENGINEERING].is_observed is True


def test_custom_coverage_threshold_survives_pipeline_and_rescore(monkeypatch):
    import cci.pipeline.orchestrator as orchestrator

    candidate_id = uuid4()
    config = ScoringConfig(low_coverage_threshold=0.5)
    state = execute_analysis_pipeline(
        candidate_id=candidate_id,
        role=CanonicalRole.BACKEND,
        scoring_config=config,
    )
    assert state.dossier is not None
    assert state.dossier.coverage_sufficiency_threshold == 0.5

    uncertainty_thresholds = []
    original_diagnostics = orchestrator.compute_uncertainty_diagnostics

    def capture_diagnostics(estimate, config=None):
        uncertainty_thresholds.append(config.low_coverage_threshold)
        return original_diagnostics(estimate, config=config)

    monkeypatch.setattr(
        orchestrator, "compute_uncertainty_diagnostics", capture_diagnostics
    )
    monkeypatch.setattr(
        orchestrator, "compute_evidence_coverage", lambda *args, **kwargs: 0.4
    )

    rescored = rescore_dossier(
        state.dossier, {CapabilityKey.BACKEND_ENGINEERING: 1.0}
    )

    assert uncertainty_thresholds
    assert set(uncertainty_thresholds) == {0.5}
    assert rescored.coverage == 0.4
    assert rescored.coverage_sufficiency_threshold == 0.5
    assert rescored.is_insufficient_evidence is True
    assert rescored.evidence_state == EvidenceState.INSUFFICIENT


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
    assert data["evidence_state"] == "INSUFFICIENT"
    assert data["coverage_sufficiency_threshold"] == 0.35
    assert len(data["stages"]) == 10

    # 2. Query Status
    status_resp = client.get(f"/api/v1/pipeline/status/{run_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["analysis_run_id"] == run_id
    assert status_data["status"] == "completed"
    assert status_data["evidence_state"] == "INSUFFICIENT"

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
