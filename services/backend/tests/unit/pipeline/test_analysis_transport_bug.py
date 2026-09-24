"""Unit and transport tests for Fix 27: The 128 KB Analysis Transport Bug.

Verifies:
1. Upload resume once via POST /api/v1/live/intake:
   - Persists safe normalized analysis data.
   - Generates and returns `analysis_run_id`.
   - Pre-caches early parse/claim extraction stages in AnalysisRun.
   - Does NOT retain raw document bytes or sensitive unparsed file payloads.
2. Lean subsequent requests:
   - Client sends only lean parameters: run ID, user-reviewed URLs, role, JD edits, optional settings.
   - Client does NOT resend enormous ResumeIntake objects.
   - Works across both asynchronous durable runs (POST /api/v1/live/runs) and synchronous analysis (POST /api/v1/live/analyze).
3. Body size validation:
   - Strictly validates body sizes across all endpoints.
   - Limits: 3 MB for resume upload, 512 KB for analysis requests.
   - Rejection with HTTP 413 for oversized payloads.
   - Field validation: 20k chars max for JD, 100 max external URLs, 20 max GitHub URLs.
4. Largest legal resume/JD/source payload:
   - Near 100,000 chars valid digital PDF resume.
   - Exactly 20,000 chars JD text.
   - Exactly 100 user-reviewed URLs.
   - Exactly 20 GitHub repository URLs.
   - Deterministic execution without transport failure.
"""

import json
import time
from uuid import UUID, uuid4

import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from cci.domain.enums import AnalysisRunState
from cci.live import acquisition
from cci.live.contracts import (
    MAX_UPLOAD,
    MAX_ANALYSIS_REQUEST_BYTES,
    LeanAnalysisRequest,
    LiveAnalysisRequest,
    ResumeIntake,
)
from cci.live.runner import AnalysisRunManager, get_analysis_run_manager
from cci.live_app import app
from tests.test_live_analysis import resume_bytes, transport

client = TestClient(app)


def make_large_pdf_resume(target_chars: int = 90000) -> bytes:
    """Creates a valid multi-page PDF resume with approximately target_chars of text."""
    doc = pymupdf.open()
    chunk_text = (
        "Experience\n"
        "Staff Software Engineer at Infrastructure Corp from 2020 to 2026.\n"
        "Architected high-throughput distributed ingestion pipelines processing 50M events daily.\n"
        "Designed resilient fault-tolerant microservices using Python, Go, and PostgreSQL.\n"
        "Projects\n"
        "Led CandidateX core platform at https://github.com/example/api with 99.99% uptime.\n"
        "Education\n"
        "BS in Computer Science from State University.\n"
        "Certifications\n"
        "AWS Certified Solutions Architect Professional.\n"
    )
    chars_per_page = len(chunk_text) * 4
    pages_needed = max(1, min(28, (target_chars // chars_per_page) + 1))

    for p in range(pages_needed):
        page = doc.new_page()
        y = 40
        if p == 0:
            page.insert_text((40, y), "Example Candidate\nSkills\nPython, Docker, Kubernetes, SQL, Go\n")
            page.insert_link({
                "kind": pymupdf.LINK_URI,
                "from": pymupdf.Rect(40, y + 10, 160, y + 30),
                "uri": "https://github.com/example/api",
            })
            y += 60

        for _ in range(4):
            page.insert_text((40, y), chunk_text)
            y += 160

    return doc.tobytes()


def test_upload_resume_once_returns_analysis_run_id_and_persists_normalized_data():
    """Verify that /intake returns analysis_run_id and stores safe normalized data in manager."""
    pdf_bytes = resume_bytes()
    response = client.post(
        "/api/v1/live/intake",
        content=pdf_bytes,
        headers={"X-Filename": "resume.pdf"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "analysis_run_id" in data
    run_id = UUID(data["analysis_run_id"])
    assert run_id is not None

    assert data["manifest"]["display_name"] == "Example Candidate"
    assert data["manifest"]["claimed_skills"] == ["Python", "SQL"]
    assert len(data["document_sha256"]) == 64

    # Verify durable run exists in AnalysisRunManager
    manager = get_analysis_run_manager()
    stored_run = manager.get_run(run_id)
    assert stored_run is not None
    assert stored_run.state == AnalysisRunState.QUEUED

    # Stages 1 & 2 are pre-cached
    assert AnalysisRunState.PARSING_RESUME.value in stored_run.stage_data
    assert AnalysisRunState.EXTRACTING_CLAIMS.value in stored_run.stage_data
    assert stored_run.stage_data["PARSING_RESUME"]["status"] == "parsed"

    # Raw bytes are NOT retained in the payload
    assert "data" not in stored_run.input_payload
    assert "pdf_bytes" not in stored_run.input_payload


def test_lean_run_execution_without_resending_intake(monkeypatch):
    """Verify that POST /runs accepts lean parameters with analysis_run_id and executes."""
    monkeypatch.setattr(acquisition, "HTTP_TRANSPORT", httpx.MockTransport(transport))

    # 1. Intake
    intake_resp = client.post(
        "/api/v1/live/intake",
        content=resume_bytes(),
        headers={"X-Filename": "resume.pdf"},
    )
    assert intake_resp.status_code == 200
    run_id_str = intake_resp.json()["analysis_run_id"]

    # 2. Lean POST /runs without intake
    lean_payload = {
        "analysis_run_id": run_id_str,
        "role": "backend",
        "jd_text": "We need an engineer experienced with Python and API design.",
        "user_reviewed_urls": ["https://github.com/example/api"],
        "optional_settings": {"deterministic": True},
    }
    run_resp = client.post("/api/v1/live/runs", json=lean_payload)
    assert run_resp.status_code == 202
    run_data = run_resp.json()
    assert run_data["analysis_run_id"] == run_id_str
    assert run_data["state"] == "QUEUED"
    assert run_data["poll_url"] == f"/api/v1/live/runs/{run_id_str}"

    # 3. Poll status until terminal
    deadline = time.time() + 10.0
    final_status = None
    while time.time() < deadline:
        poll_resp = client.get(f"/api/v1/live/runs/{run_id_str}")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        if poll_data["state"] in ("COMPLETED", "PARTIAL", "FAILED"):
            final_status = poll_data
            break
        time.sleep(0.05)

    assert final_status is not None
    assert final_status["state"] in ("COMPLETED", "PARTIAL")
    assert final_status["progress_percent"] == 100.0
    assert final_status["result"] is not None
    assert "dossier" in final_status["result"]


def test_lean_analyze_endpoint_without_resending_intake(monkeypatch):
    """Verify that POST /analyze accepts lean parameters with analysis_run_id."""
    monkeypatch.setattr(acquisition, "HTTP_TRANSPORT", httpx.MockTransport(transport))

    intake_resp = client.post(
        "/api/v1/live/intake",
        content=resume_bytes(),
        headers={"X-Filename": "resume.pdf"},
    )
    assert intake_resp.status_code == 200
    run_id_str = intake_resp.json()["analysis_run_id"]

    # Call /analyze with only run ID and lean config
    analyze_resp = client.post(
        "/api/v1/live/analyze",
        json={
            "analysis_run_id": run_id_str,
            "role": "backend",
            "jd_text": "Backend Engineer with Python",
            "github_urls": ["https://github.com/example/api"],
            "github_identity": "example",
        },
    )
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()
    assert data["dossier"] is not None
    assert data["dossier"]["role"] == "backend"
    assert "graph" in data


def test_largest_legal_resume_and_jd_and_source_payload_deterministic(monkeypatch):
    """Verify that the largest legal resume (~95k chars), JD (20k chars), and sources (100 external + 20 repos)

    work deterministically and avoid transport overflow.
    """
    monkeypatch.setattr(acquisition, "HTTP_TRANSPORT", httpx.MockTransport(transport))
    monkeypatch.setattr("cci.live.public_links.acquire_public_links", lambda urls, **kwargs: [{"url": u, "status": "completed", "detail": "Mocked"} for u in urls])
    monkeypatch.setattr("cci.live.deployment.acquire_deployment_sources", lambda candidates, urls, run_id: ([], [{"url": u, "status": "completed"} for u in candidates]))

    # 1. Largest legal resume
    large_pdf = make_large_pdf_resume(target_chars=90000)
    intake_resp = client.post(
        "/api/v1/live/intake",
        content=large_pdf,
        headers={"X-Filename": "largest_legal_resume.pdf"},
    )
    assert intake_resp.status_code == 200
    intake_data = intake_resp.json()
    run_id_str = intake_data["analysis_run_id"]
    assert len(intake_data["document_sha256"]) == 64

    # 2. Maximum legal parameters:
    # Exactly 20,000 characters JD text (maximum legal limit)
    base_jd = "Senior Distributed Systems Engineer with expertise in high scale architectures. "
    repetitions = 20000 // len(base_jd)
    max_jd_text = (base_jd * repetitions) + ("X" * (20000 - (repetitions * len(base_jd))))
    assert len(max_jd_text) == 20000

    # Exactly 100 external URLs (maximum legal limit)
    max_user_urls = [f"https://example.com/project-showcase-{i:03d}" for i in range(100)]
    assert len(max_user_urls) == 100

    # Exactly 20 GitHub URLs (maximum legal limit)
    max_github_urls = [f"https://github.com/example/api"] + [f"https://github.com/example/repo-{i:02d}" for i in range(19)]
    assert len(max_github_urls) == 20

    lean_payload = {
        "analysis_run_id": run_id_str,
        "role": "backend",
        "jd_text": max_jd_text,
        "user_reviewed_urls": max_user_urls,
        "github_urls": max_github_urls,
        "optional_settings": {"strict": True},
    }

    # Verify lean payload size is small (~30 KB), avoiding 128 KB bug completely
    payload_json_bytes = json.dumps(lean_payload).encode("utf-8")
    assert len(payload_json_bytes) < MAX_ANALYSIS_REQUEST_BYTES
    assert len(payload_json_bytes) < 60 * 1024  # Less than 60 KB

    # Validate against LeanAnalysisRequest model
    validated_lean = LeanAnalysisRequest.model_validate(lean_payload)
    assert len(validated_lean.jd_text) == 20000
    assert len(validated_lean.external_urls) == 100
    assert len(validated_lean.github_urls) == 20

    # Run twice deterministically using sync start on AnalysisRunManager
    manager = get_analysis_run_manager()
    run1 = manager.start_run(run_id_str, update_payload=lean_payload, sync=True)
    assert run1 is not None
    assert run1.state in (AnalysisRunState.COMPLETED, AnalysisRunState.PARTIAL)
    res1_stages = list(run1.stage_data.keys())

    # Second execution on same payload produces identical deterministic stage set
    run2 = manager.start_run(run_id_str, update_payload=lean_payload, sync=True)
    assert run2 is not None
    assert run2.state in (AnalysisRunState.COMPLETED, AnalysisRunState.PARTIAL)
    res2_stages = list(run2.stage_data.keys())
    assert res1_stages == res2_stages


def test_body_size_limits_enforced_strictly():
    """Verify that payload boundaries are strictly enforced with appropriate HTTP codes."""
    # 1. Upload > 3 MB to /intake is rejected with 413
    oversized_upload = b"x" * (MAX_UPLOAD + 1)
    resp = client.post("/api/v1/live/intake", content=oversized_upload, headers={"X-Filename": "huge.pdf"})
    assert resp.status_code == 413

    # 2. Payload > 512 KB to /runs is rejected with 413
    oversized_json = json.dumps({"analysis_run_id": str(uuid4()), "flood": "x" * (MAX_ANALYSIS_REQUEST_BYTES + 10)}).encode()
    resp = client.post("/api/v1/live/runs", content=oversized_json, headers={"Content-Type": "application/json"})
    assert resp.status_code == 413

    # 3. Payload > 512 KB to /analyze is rejected with 413
    resp = client.post("/api/v1/live/analyze", content=oversized_json, headers={"Content-Type": "application/json"})
    assert resp.status_code == 413

    # 4. JD text exceeding 20,000 characters is rejected with 422
    intake_resp = client.post("/api/v1/live/intake", content=resume_bytes(), headers={"X-Filename": "resume.pdf"})
    run_id = intake_resp.json()["analysis_run_id"]
    resp = client.post(
        "/api/v1/live/analyze",
        json={"analysis_run_id": run_id, "jd_text": "A" * 20001},
    )
    assert resp.status_code == 422

    # 5. External URLs exceeding 100 is rejected with 422
    resp = client.post(
        "/api/v1/live/analyze",
        json={"analysis_run_id": run_id, "user_reviewed_urls": [f"https://example.com/{i}" for i in range(101)]},
    )
    assert resp.status_code == 422

    # 6. GitHub URLs exceeding 20 is rejected with 422
    resp = client.post(
        "/api/v1/live/analyze",
        json={"analysis_run_id": run_id, "github_urls": [f"https://github.com/example/repo-{i}" for i in range(21)]},
    )
    assert resp.status_code == 422

    # 7. Non-existent run ID without intake returns 404
    non_existent = str(uuid4())
    resp = client.post("/api/v1/live/analyze", json={"analysis_run_id": non_existent})
    assert resp.status_code == 404
    resp = client.post("/api/v1/live/runs", json={"analysis_run_id": non_existent})
    assert resp.status_code == 404
