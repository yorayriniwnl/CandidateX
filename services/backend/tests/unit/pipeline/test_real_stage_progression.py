"""Unit tests for Real Analysis Stage Progression (Fix 47).

Verifies:
1. Progress is strictly backend-derived with real metric counts.
2. Invariant: No fake progress bar; stages reflect verifiable execution checkpoints:
   - Resume parsed
   - N claims extracted
   - N explicit sources, N sources discovered
   - N sources fetched
   - N repositories inventoried, N repositories deeply scanned
   - N deployments inspected
   - N credentials reviewed
   - claim corroboration complete
   - dossier finalized
3. Integration with DurableAnalysisRun.to_status_dict() and execute_analysis_pipeline().
"""

from __future__ import annotations

from uuid import uuid4
import pytest

from cci.domain.contracts import CandidateManifest, EvidenceConfidenceFactors, EvidenceRecord
from cci.domain.enums import AnalysisRunState, CanonicalRole, CapabilityKey, SourceFamily
from cci.live.runner import DurableAnalysisRun
from cci.pipeline.orchestrator import execute_analysis_pipeline


def test_durable_run_real_stage_progression():
    """Verify DurableAnalysisRun generates real backend-derived stage progression."""
    run_id = uuid4()
    manifest = CandidateManifest(
        display_name="Dev Candidate",
        claimed_skills=["Rust", "Distributed Systems", "Raft", "Python"],
        project_claims=[{"title": "Distributed KV Engine", "claimed_role": "Author"}],
        experience_claims=[{"company": "Cloud Systems", "role": "Senior Engineer"}],
        github_urls=["https://github.com/dev/kv-engine", "https://github.com/dev/raft-core"],
        deployment_urls=["https://demo-kv.dev.io"],
        portfolio_urls=["https://candidate.dev"],
        credential_urls=["https://credly.com/badges/aws-architect"],
    )

    run = DurableAnalysisRun(
        analysis_run_id=run_id,
        target_role="backend",
        input_payload={
            "intake": {"manifest": manifest.model_dump()},
            "candidate_id": str(run_id),
        },
    )

    # Populate realistic stage data as execution proceeds
    run.stage_data[AnalysisRunState.PARSING_RESUME.value] = {
        "candidate_id": str(run_id),
        "status": "parsed",
    }
    run.stage_data[AnalysisRunState.EXTRACTING_CLAIMS.value] = {
        "claimed_skills": list(manifest.claimed_skills),
        "project_claims": list(manifest.project_claims),
        "experience_claims": list(manifest.experience_claims),
    }
    run.stage_data[AnalysisRunState.DISCOVERING_SOURCES.value] = {
        "selected_urls": ["https://github.com/dev/kv-engine", "https://candidate.dev"],
        "extracted_urls": ["https://github.com/dev/kv-engine", "https://candidate.dev", "https://demo-kv.dev.io"],
    }
    run.stage_data[AnalysisRunState.FETCHING_SOURCES.value] = {
        "public_sources": [
            {"url": "https://github.com/dev/kv-engine", "status": "fetched"},
            {"url": "https://candidate.dev", "status": "fetched"},
        ]
    }
    run.stage_data[AnalysisRunState.ANALYZING_GITHUB.value] = {
        "github_sources": [
            {"url": "https://github.com/dev/kv-engine", "files_inspected": 24, "deep_scan": True},
            {"url": "https://github.com/dev/raft-core", "files_inspected": 18, "deep_scan": True},
        ]
    }
    run.stage_data[AnalysisRunState.ANALYZING_DEPLOYMENTS.value] = {
        "deployment_sources": [
            {"url": "https://demo-kv.dev.io", "status": "observed"}
        ]
    }
    run.stage_data[AnalysisRunState.ANALYZING_CREDENTIALS.value] = {
        "count": 1,
        "verified_credentials": [{"title": "AWS Certified Solutions Architect", "status": "verified"}],
    }
    run.stage_data[AnalysisRunState.CORROBORATING_CLAIMS.value] = {"status": "corroborated"}
    run.stage_data[AnalysisRunState.BUILDING_DOSSIER.value] = {"status": "finalized"}
    run.state = AnalysisRunState.COMPLETED

    stages = run.get_real_stage_progression()
    assert len(stages) >= 9

    # Verify discrete checkpoint metrics
    metrics = {s["stage"]: s["metric_label"] for s in stages}
    assert metrics[AnalysisRunState.PARSING_RESUME.value] == "Resume parsed"
    assert "6 claims extracted" in metrics[AnalysisRunState.EXTRACTING_CLAIMS.value]  # 4 skills + 1 proj + 1 exp
    assert "2 explicit sources" in metrics[AnalysisRunState.DISCOVERING_SOURCES.value]
    assert "2 sources fetched" in metrics[AnalysisRunState.FETCHING_SOURCES.value]
    assert "2 repositories inventoried, 2 repositories deeply scanned" in metrics[AnalysisRunState.ANALYZING_GITHUB.value]
    assert "1 deployments inspected" in metrics[AnalysisRunState.ANALYZING_DEPLOYMENTS.value]
    assert "1 credentials reviewed" in metrics[AnalysisRunState.ANALYZING_CREDENTIALS.value]
    assert metrics[AnalysisRunState.CORROBORATING_CLAIMS.value] == "claim corroboration complete"
    assert metrics[AnalysisRunState.BUILDING_DOSSIER.value] == "dossier finalized"

    # Verify status dict integration
    status_dict = run.to_status_dict()
    assert "real_stage_progression" in status_dict
    assert len(status_dict["real_stage_progression"]) == len(stages)


def test_orchestrator_pipeline_stage_progression_in_dossier():
    """Verify execute_analysis_pipeline stamps discrete stage progression in Dossier."""
    cand_id = uuid4()
    run_id = uuid4()

    factors = EvidenceConfidenceFactors(
        artifact_integrity=0.9,
        recency_factor=0.9,
        verification_level=0.9,
        depth_specificity=0.9,
        source_reliability=0.9,
        ownership_score=0.9,
    )

    evidence = [
        EvidenceRecord(
            evidence_id=uuid4(),
            fingerprint="a" * 64,
            candidate_id=cand_id,
            analysis_run_id=run_id,
            source_family=SourceFamily.GITHUB,
            source_locator="https://github.com/cand/repo",
            immutable_revision="b" * 40,
            target_capability=CapabilityKey.BACKEND_ENGINEERING,
            observation_type="test_suite",
            claim="Has automated tests",
            technical_signal_strength=0.85,
            confidence_factors=factors,
            confidence=0.85,
            provenance={"artifact_path": "tests/test_kv.py"},
        )
    ]

    pipeline_state = execute_analysis_pipeline(
        candidate_id=cand_id,
        role=CanonicalRole.BACKEND,
        custom_evidence=evidence,
        declared_claims=["Experienced distributed systems engineer"],
        repo_urls=["https://github.com/cand/repo"],
        analysis_run_id=run_id,
    )

    dossier = pipeline_state.dossier
    assert dossier is not None
    assert hasattr(dossier, "pipeline_stage_progression")
    assert len(dossier.pipeline_stage_progression) == 10

    # Verify discrete checkpoint metrics in the dossier
    stages = dossier.pipeline_stage_progression
    assert stages[0]["stage"] == "PARSING_CV"
    assert stages[0]["status"] == "completed"
    assert stages[-1]["stage"] == "GENERATING_DOSSIER"
    assert stages[-1]["status"] == "completed"
