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


def test_manifest_diverse_resume_links():
    """Verify that modern and diverse resume links are correctly classified and public links captured."""
    from cci.intake.parsers import ParsedDocument
    doc = ParsedDocument(
        raw_text="""
        Jane Engineer
        Skills: Python, TypeScript
        Links:
        GitHub: github.com/jane-eng
        LinkedIn: linkedin.com/in/jane-eng,
        HuggingFace: huggingface.co/jane-eng/bert-model
        NPM: https://www.npmjs.com/package/fast-logger.
        Portfolio: jane.tech
        Demo: https://jane-app.streamlit.app
        Coding: leetcode.com/u/jane-eng
        Credential: https://udemy.com/certificate/UC-999
        General blog: https://example.com/blog/my-journey;
        Drive notes: https://drive.google.com/file/d/123/view
        """,
        embedded_urls=[],
        visible_urls=[
            "github.com/jane-eng",
            "linkedin.com/in/jane-eng,",
            "huggingface.co/jane-eng/bert-model",
            "https://www.npmjs.com/package/fast-logger.",
            "jane.tech",
            "https://jane-app.streamlit.app",
            "leetcode.com/u/jane-eng",
            "https://udemy.com/certificate/UC-999",
            "https://example.com/blog/my-journey;",
            "https://drive.google.com/file/d/123/view",
        ],
    )
    manifest = build_candidate_manifest(doc)
    assert "https://github.com/jane-eng" in manifest.github_urls
    assert "https://linkedin.com/in/jane-eng" in manifest.linkedin_urls
    assert "https://huggingface.co/jane-eng/bert-model" in manifest.project_links
    assert "https://www.npmjs.com/package/fast-logger" in manifest.project_links
    assert "https://jane.tech" in manifest.portfolio_urls
    assert "https://jane-app.streamlit.app" in manifest.deployment_urls
    assert "https://leetcode.com/u/jane-eng" in manifest.coding_profile_urls
    assert "https://udemy.com/certificate/UC-999" in manifest.credential_urls
    assert "https://drive.google.com/file/d/123/view" in manifest.shared_document_urls
    assert "https://example.com/blog/my-journey" in manifest.public_links


def test_manifest_extracts_skills_from_various_resume_formats():
    from cci.intake.parsers import ParsedDocument

    # Format 1: Key Skills header
    doc1 = ParsedDocument(raw_text="Alice Dev\nKey Skills\nPython, Docker, Kubernetes\nExperience\nDev at Google")
    m1 = build_candidate_manifest(doc1)
    assert set(m1.claimed_skills) == {"Python", "Docker", "Kubernetes"}

    # Format 2: Categories under Technical Skills
    doc2 = ParsedDocument(raw_text="Bob Dev\nTECHNICAL SKILLS:\nLanguages: Python, Go\nDatabases: Postgres\nExperience\nDev")
    m2 = build_candidate_manifest(doc2)
    assert "Python" in m2.claimed_skills
    assert "Go" in m2.claimed_skills
    assert "Postgres" in m2.claimed_skills

    # Format 3: Slash-separated skills and Core Competencies
    doc3 = ParsedDocument(raw_text="Carol Dev\nCore Competencies\nPython / FastAPI / Redis\nProjects\nMicroservices")
    m3 = build_candidate_manifest(doc3)
    assert set(m3.claimed_skills) == {"Python", "FastAPI", "Redis"}

    # Format 4: Bulleted heading and bulleted list
    doc4 = ParsedDocument(raw_text="David Dev\n• Skills\n• Python\n• Docker\nExperience\nDev")
    m4 = build_candidate_manifest(doc4)
    assert "Python" in m4.claimed_skills
    assert "Docker" in m4.claimed_skills

    # Format 5: Inline skills line
    doc5 = ParsedDocument(raw_text="Eve Dev\nTechnical Skills: Python, React, AWS, Docker\nExperience\nEngineer")
    m5 = build_candidate_manifest(doc5)
    assert "Python" in m5.claimed_skills
    assert "React" in m5.claimed_skills
    assert "AWS" in m5.claimed_skills
    assert "Docker" in m5.claimed_skills

    # Format 6: Narrative resume without any skills header (fallback extraction)
    doc6 = ParsedDocument(raw_text="Frank Dev\nSummary\nExperienced backend engineer in Python, Docker, and PostgreSQL.")
    m6 = build_candidate_manifest(doc6)
    assert "Python" in m6.claimed_skills
    assert "Docker" in m6.claimed_skills
    assert "PostgreSQL" in m6.claimed_skills


