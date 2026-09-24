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

    assert "Jordan Example" in parsed.raw_text
    assert "jordan@example.test" in parsed.raw_text

    # Verify visible URLs found in text
    assert any("github.com/jordan-example" in u for u in parsed.visible_urls)
    assert any("jordan-example.vercel.app" in u for u in parsed.visible_urls)

    # CRITICAL TEST: Hidden hyperlinks behind anchor text must be extracted from annotations
    # "Distributed Cache Project" was linked to "https://github.com/alicedev/distributed-cache.git"
    assert any("distributed-cache" in u for u in parsed.embedded_urls)
    # "LinkedIn Profile" was linked to "https://www.linkedin.com/in/jordan-example?ref=resume_pdf"
    assert any("linkedin.com/in/jordan-example" in u for u in parsed.embedded_urls)


def test_docx_relationship_hyperlink_extraction():
    """Verify that python-docx extracts text and relationship-bound hyperlinks."""
    docx_bytes = create_golden_docx_with_links()
    parsed = parse_docx_document(docx_bytes)

    assert "Alex Rivera" in parsed.raw_text
    assert "alex@example.test" in parsed.raw_text
    assert "Go, TypeScript, SQL" in parsed.raw_text

    # Verify visible URL
    assert any("github.com/alex-rivera" in u for u in parsed.visible_urls)

    # CRITICAL TEST: Embedded relationship hyperlink
    assert any("bob-demo.fly.dev" in u for u in parsed.embedded_urls)
