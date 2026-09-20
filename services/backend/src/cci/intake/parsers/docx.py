"""DOCX parser with embedded hyperlink relationship extraction using python-docx."""

import io

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
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

    # Keep paragraph/table order, including nested tables and linked header parts.
    seen_parts, seen_cells = set(), set()

    def collect(container):
        part = container.part
        if id(part) not in seen_parts:
            seen_parts.add(id(part))
            for rel in part.rels.values():
                if rel.reltype == HYPERLINK_REL_TYPE and isinstance(rel.target_ref, str):
                    embedded_urls.append(rel.target_ref.strip())
        for block in container.iter_inner_content():
            if isinstance(block, Paragraph):
                # w:t also retains text in hyperlinks and text boxes.
                text = ''.join(block._p.xpath('.//w:t/text()'))
                if text:
                    text_chunks.append(block.text or text)
                    visible_urls.extend(m.group(0).strip() for m in URL_REGEX.finditer(text))
            elif isinstance(block, Table):
                for row in block.rows:
                    for cell in row.cells:
                        if cell._tc not in seen_cells:
                            seen_cells.add(cell._tc)
                            collect(cell)

    for section in doc.sections:
        for header in (section.header, section.first_page_header, section.even_page_header):
            if not header.is_linked_to_previous:
                collect(header)
    collect(doc)
    for section in doc.sections:
        for footer in (section.footer, section.first_page_footer, section.even_page_footer):
            if not footer.is_linked_to_previous:
                collect(footer)

    full_text = "\n".join(text_chunks)
    return ParsedDocument(
        raw_text=full_text,
        embedded_urls=embedded_urls,
        visible_urls=visible_urls,
    )
