"""Intake module exports for Candidate Capability Intelligence."""

from cci.intake.canonicalizer import (
    classify_url,
    deduplicate_urls,
    normalize_url,
)
from cci.intake.manifest import build_candidate_manifest
from cci.intake.parsers import (
    ParsedDocument,
    parse_docx_document,
    parse_pdf_document,
)

__all__ = [
    "ParsedDocument",
    "build_candidate_manifest",
    "classify_url",
    "deduplicate_urls",
    "normalize_url",
    "parse_docx_document",
    "parse_pdf_document",
]
