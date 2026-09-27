import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pytest
from cci.intake.parsers import parse_docx_document, parse_pdf_document
from tests.golden.cv.fixtures import (
    create_golden_docx_with_links,
    create_golden_pdf_with_hidden_links,
)


def test_pdf_embedded_and_hidden_hyperlink_extraction():
    """Verify that PyMuPDF extracts both visible text URLs and hidden URI link annotations."""
    pdf_bytes = create_golden_pdf_with_hidden_links()
    parsed = parse_pdf_document(pdf_bytes)

    assert "Alice Developer" in parsed.raw_text
    assert "alice.dev@example.com" in parsed.raw_text

    # Verify visible URLs found in text
    assert any("github.com/alicedev" in u for u in parsed.visible_urls)
    assert any("alice-dev.vercel.app" in u for u in parsed.visible_urls)

    # CRITICAL TEST: Hidden hyperlinks behind anchor text must be extracted from annotations
    # "Distributed Cache Project" was linked to "https://github.com/alicedev/distributed-cache.git"
    assert any("distributed-cache" in u for u in parsed.embedded_urls)
    # "LinkedIn Profile" was linked to "https://www.linkedin.com/in/alicedev?ref=resume_pdf"
    assert any("linkedin.com/in/alicedev" in u for u in parsed.embedded_urls)


def test_docx_relationship_hyperlink_extraction():
    """Verify that python-docx extracts text and relationship-bound hyperlinks."""
    docx_bytes = create_golden_docx_with_links()
    parsed = parse_docx_document(docx_bytes)

    assert "Bob Engineer" in parsed.raw_text
    assert "bob.eng@example.com" in parsed.raw_text
    assert "Go, TypeScript, SQL" in parsed.raw_text

    # Verify visible URL
    assert any("github.com/bobeng" in u for u in parsed.visible_urls)

    # CRITICAL TEST: Embedded relationship hyperlink
    assert any("bob-demo.fly.dev" in u for u in parsed.embedded_urls)


def test_pdf_picture_extraction():
    """Verify that PyMuPDF extracts embedded candidate photos as base64 data URIs."""
    from tests.golden.cv.fixtures import create_golden_pdf_with_picture
    from cci.intake.manifest import build_candidate_manifest

    pdf_bytes = create_golden_pdf_with_picture()
    parsed = parse_pdf_document(pdf_bytes)

    assert "Carol Candidate" in parsed.raw_text
    assert parsed.picture is not None
    assert parsed.picture.startswith("data:image/")
    assert ";base64," in parsed.picture

    # Verify manifest reflects the extracted picture
    manifest = build_candidate_manifest(parsed)
    assert manifest.display_name == "Carol Candidate"
    assert manifest.picture == parsed.picture


def test_docx_picture_extraction():
    """Verify that DOCX parser extracts embedded media as base64 data URIs."""
    from tests.golden.cv.fixtures import create_golden_docx_with_picture
    from cci.intake.manifest import build_candidate_manifest

    docx_bytes = create_golden_docx_with_picture()
    parsed = parse_docx_document(docx_bytes)

    assert "Dave Developer" in parsed.raw_text
    assert parsed.picture is not None
    assert parsed.picture.startswith("data:image/")
    assert ";base64," in parsed.picture

    # Verify manifest reflects the extracted picture
    manifest = build_candidate_manifest(parsed)
    assert manifest.display_name == "Dave Developer"
    assert manifest.picture == parsed.picture


def test_document_without_picture_returns_none():
    """Verify that documents without pictures have picture=None."""
    pdf_bytes = create_golden_pdf_with_hidden_links()
    parsed = parse_pdf_document(pdf_bytes)
    assert parsed.picture is None
