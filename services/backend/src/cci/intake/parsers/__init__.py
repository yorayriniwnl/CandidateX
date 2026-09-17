"""Intake document parsers package."""

from cci.intake.parsers.pdf import ParsedDocument, parse_pdf_document
from cci.intake.parsers.docx import parse_docx_document

__all__ = [
    "ParsedDocument",
    "parse_pdf_document",
    "parse_docx_document",
]
