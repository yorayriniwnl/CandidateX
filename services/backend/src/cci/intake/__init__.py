"""Intake module exports for Candidate Capability Intelligence."""

from cci.intake.canonicalizer import (
    classify_url,
    deduplicate_urls,
    normalize_url,
)
from cci.intake.parsers import (
    ParsedDocument,
    parse_docx_document,
    parse_pdf_document,
)
from cci.intake.manifest import build_candidate_manifest

__all__ = [
    "classify_url",
    "deduplicate_urls",
    "normalize_url",
    "ParsedDocument",
    "parse_docx_document",
    "parse_pdf_document",
    "build_candidate_manifest",
]
