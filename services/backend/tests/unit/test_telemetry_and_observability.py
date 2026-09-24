"""Unit tests for Production Telemetry, Observability Metrics, and Structured Errors (Fix 35)."""

import time
from uuid import uuid4
from fastapi.testclient import TestClient

from cci.domain.contracts import (
    CandidateManifest,
    Dossier,
    OwnershipAssessment,
    RepositoryAssociation,
    RepositoryContribution,
)
from cci.domain.enums import CanonicalRole
from cci.live_app import app as live_app
from cci.live.runner import AnalysisRunManager
from cci.telemetry import (
    RunTelemetry,
    StructuredAnalysisError,
    create_run_telemetry,
)


def test_telemetry_timing_and_durations():
    """Verifies that run duration, queue delay, and stage durations are recorded accurately."""
    run_id = uuid4()
    tel = create_run_telemetry(run_id, request_id="req_test_123")
    assert tel.analysis_run_id == str(run_id)
    assert tel.request_id == "req_test_123"

    time.sleep(0.01)
    tel.start_run()
    assert tel.started_at is not None
    assert tel.queue_delay_seconds >= 0.0

    # Test stage timing
    tel.start_stage("PARSING_RESUME")
    time.sleep(0.01)
    tel.complete_stage("PARSING_RESUME", artifacts_count=5)

    assert "PARSING_RESUME" in tel.stage_durations
    assert tel.stage_durations["PARSING_RESUME"] > 0.0
    assert tel.stages["PARSING_RESUME"].status == "completed"
    assert tel.stages["PARSING_RESUME"].artifacts_count == 5

    # Finalize
    time.sleep(0.01)
    tel.finalize()
    assert tel.completed_at is not None
    assert tel.analysis_run_duration_seconds > 0.0


def test_source_fetch_counts_and_failure_reasons():
    """Verifies that source fetch outcomes and sanitized failure reasons are aggregated."""
    run_id = uuid4()
    tel = create_run_telemetry(run_id)

    raw_sources = [
        {"url": "https://example.com/a", "status": "observed", "receipt": {"bytes_downloaded": 1024}},
        {"url": "https://example.com/b", "status": "observed", "receipt": {"bytes_downloaded": 2048}},
        {"url": "https://example.com/c", "status": "timeout", "detail": "Public-link time budget reached."},
        {"url": "https://example.com/d", "status": "access_restricted", "detail": "Login gate encountered HTTP 403"},
        {"url": "https://example.com/e", "status": "not_scanned", "detail": "Deferred: domain cap reached"},
        {"url": "https://example.com/f", "status": "security_blocked", "detail": "SSRF safety validation failed"},
        {"url": "https://example.com/g", "status": "not_selected", "detail": "Not selected for run"},
    ]

    tel.record_sources(raw_sources)
    counts = tel.source_fetch_counts
    assert counts["total_attempted"] == 7
    assert counts["fetched"] == 2
    assert counts["deferred"] == 1
    assert counts["blocked"] == 2
    assert counts["not_selected"] == 1
    assert counts["failed"] == 1

    reasons = tel.source_failure_reasons
    assert "timeout_expired" in reasons
    assert "access_restricted" in reasons
    assert "security_validation_blocked" in reasons

    crawl = tel.crawl_budget_usage
    assert crawl["pages_fetched"] == 2
    assert crawl["bytes_downloaded"] == 3072


def test_pipeline_metrics_deduplication_and_attribution():
    """Verifies coverage, deduplication, and attribution quality metrics."""
    run_id = uuid4()
    cand_id = uuid4()
    tel = create_run_telemetry(run_id)

    ownerships = [
        OwnershipAssessment(
            repository_url="https://github.com/example/repo1",
            candidate_identifier="cand_1",
            ownership_score=0.92,
        ),
        OwnershipAssessment(
            repository_url="https://github.com/example/repo2",
            candidate_identifier="cand_1",
            ownership_score=0.60,
        ),
    ]

    dossier = Dossier(
        candidate_id=cand_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.78,
        is_insufficient_evidence=False,
        capability_estimates={},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=ownerships,
        repository_associations=[],
        claims_corroboration=[],
        interview_probes=[],
        interview_questions=[],
        evidence_records=[],
    )

    # 10 raw evidence records generated, 4 deduplicated/retained -> 6 discarded
    tel.record_pipeline_metrics(dossier, raw_evidence_count=10, artifacts_scanned=25)
    assert tel.coverage == 0.78
    assert tel.artifacts_scanned == 25
    assert tel.evidence_generated == 10
    assert tel.evidence_discarded == 10  # 10 raw - 0 final records = 10 discarded

    attr = tel.attribution_quality
    assert attr["attributed_count"] == 1  # >= 0.70
    assert attr["ambiguous_count"] == 1   # < 0.70
    assert attr["mean_confidence"] == round((0.92 + 0.60) / 2, 4)


def test_structured_error_and_candidate_privacy():
    """Verifies that structured errors redact candidate PII and auth credentials."""
    run_id = uuid4()
    tel = create_run_telemetry(run_id, request_id="req_999")

    sensitive_error = (
        "Failed fetching candidate John Doe john.doe@example.com +1-555-123-4567 "
        "using bearer secret_token_abc123456789xyz"
    )

    err = tel.fail_stage("ANALYZING_GITHUB", sensitive_error, error_code="FETCH_ERROR")
    assert err.error_id.startswith("err_")
    assert err.analysis_run_id == str(run_id)
    assert err.stage == "ANALYZING_GITHUB"
    assert err.error_code == "FETCH_ERROR"
    assert tel.failure_stage == "ANALYZING_GITHUB"

    # Must NOT contain raw PII or secret credentials
    assert "john.doe@example.com" not in err.message
    assert "+1-555-123-4567" not in err.message
    assert "secret_token_abc123456789xyz" not in err.message
    assert "[REDACTED_CREDENTIAL]" in err.message or "[REDACTED" in err.message

    snap = tel.to_dict()
    assert snap["failure_stage"] == "ANALYZING_GITHUB"
    assert snap["structured_error"]["error_code"] == "FETCH_ERROR"


def test_analysis_run_manager_records_telemetry():
    """Verifies that durable execution through AnalysisRunManager records telemetry and exposes it via API."""
    manager = AnalysisRunManager(max_workers=1)
    run_id = uuid4()
    manifest = CandidateManifest(
        display_name="Jordan Example",
        claimed_skills=["Python", "FastAPI"],
        github_urls=["https://github.com/jordan-example/backend-api"],
    )

    payload = {
        "candidate_id": str(uuid4()),
        "analysis_run_id": str(run_id),
        "role": "backend",
        "intake": {
            "analysis_run_id": str(run_id),
            "candidate_id": str(uuid4()),
            "manifest": manifest.model_dump(mode="json"),
            "document_sha256": "a" * 64,
            "filename": "resume.pdf",
            "text_preview": "Python engineer with backend API experience",
        },
    }

    run = manager.create_run(payload, analysis_run_id=run_id, auto_start=False)
    assert run.telemetry is not None
    assert run.telemetry.analysis_run_id == str(run_id)

    status_dict = run.to_status_dict()
    assert "telemetry" in status_dict
    assert status_dict["telemetry"]["analysis_run_id"] == str(run_id)


def test_telemetry_api_endpoint(monkeypatch):
    """Verifies the GET /api/v1/live/runs/{run_id}/telemetry API endpoint."""
    from cci.live.runner import get_analysis_run_manager

    manager = get_analysis_run_manager()
    run_id = uuid4()
    run = manager.create_run(
        {"role": "backend"},
        analysis_run_id=run_id,
        auto_start=False,
    )

    client = TestClient(live_app)
    resp = client.get(f"/api/v1/live/runs/{run_id}/telemetry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_run_id"] == str(run_id)
    assert "source_fetch_counts" in data
    assert "crawl_budget_usage" in data
    assert "github_api_utilization" in data
    assert "stage_durations" in data
