"""DOCX parser with embedded hyperlink relationship extraction using python-docx."""

import io

import docx
from docx.opc.constants import RELATIONSHIP_TYPE

from cci.intake.parsers.pdf import URL_REGEX, ParsedDocument

HYPERLINK_REL_TYPE = RELATIONSHIP_TYPE.HYPERLINK


def parse_docx_document(docx_bytes: bytes) -> ParsedDocument:
    """Extracts text, tables, and relationship-bound hyperlinks from DOCX documents."""
    stream = io.BytesIO(docx_bytes)
    doc = docx.Document(stream)

    text_chunks: list[str] = []
    embedded_urls: list[str] = []
    visible_urls: list[str] = []

    # 1. Extract embedded relationship hyperlinks from document part
    for rel_id, rel in doc.part.rels.items():
        if rel.reltype == HYPERLINK_REL_TYPE:
            target = rel.target_ref
            if target and isinstance(target, str):
                embedded_urls.append(target.strip())

    # 2. Extract paragraph texts
    for para in doc.paragraphs:
        p_text = para.text
        if p_text:
            text_chunks.append(p_text)
            for match in URL_REGEX.finditer(p_text):
                visible_urls.append(match.group(0).strip())

    # 3. Extract table cell texts
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                c_text = cell.text
                if c_text:
                    text_chunks.append(c_text)
                    for match in URL_REGEX.finditer(c_text):
                        visible_urls.append(match.group(0).strip())

    full_text = "\n".join(text_chunks)
    return ParsedDocument(
        raw_text=full_text,
        embedded_urls=embedded_urls,
        visible_urls=visible_urls,
    )
