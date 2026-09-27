import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pytest
from cci.intake.manifest import build_candidate_manifest
from cci.intake.parsers import parse_pdf_document
from tests.golden.cv.fixtures import create_golden_pdf_with_hidden_links


def test_build_candidate_manifest_from_pdf():
    """Verify CandidateManifest fields populated strictly from candidate document."""
    pdf_bytes = create_golden_pdf_with_hidden_links()
    doc = parse_pdf_document(pdf_bytes)

    manifest = build_candidate_manifest(doc)

    assert manifest.display_name == "Alice Developer"
    assert manifest.email == "alice.dev@example.com"

    # Verify classified URLs
    assert len(manifest.github_urls) >= 2
    assert "https://github.com/alicedev" in manifest.github_urls
    assert "https://github.com/alicedev/distributed-cache" in manifest.github_urls

    assert len(manifest.linkedin_urls) == 1
    assert "https://www.linkedin.com/in/alicedev" in manifest.linkedin_urls[0]

    assert len(manifest.deployment_urls) == 1
    assert "https://alice-dev.vercel.app" in manifest.deployment_urls[0]

    # Verify claimed skills
    assert any("python" in s.lower() for s in manifest.claimed_skills)
    assert any("fastapi" in s.lower() for s in manifest.claimed_skills)
    assert any("docker" in s.lower() for s in manifest.claimed_skills)


def test_manifest_cloud_storage_links_not_claimed_as_projects():
    from cci.intake.parsers import ParsedDocument
    doc = ParsedDocument(
        raw_text="Bob Smith\nSkills\nPython, Docker\nCertificates\nhttps://drive.google.com/file/d/abc123cert/view\nProjects\nhttps://drive.google.com/file/d/xyz789proj/view\n",
        embedded_urls=("https://drive.google.com/file/d/abc123cert/view", "https://drive.google.com/file/d/xyz789proj/view"),
        visible_urls=("https://drive.google.com/file/d/abc123cert/view", "https://drive.google.com/file/d/xyz789proj/view"),
    )
    manifest = build_candidate_manifest(doc)
    assert len(manifest.project_links) == 0
    assert len(manifest.shared_document_urls) == 2
    assert "https://drive.google.com/file/d/abc123cert/view" in manifest.shared_document_urls
    assert "https://drive.google.com/file/d/xyz789proj/view" in manifest.shared_document_urls
