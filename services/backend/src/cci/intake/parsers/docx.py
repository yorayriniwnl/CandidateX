"""DOCX parser with embedded hyperlink relationship extraction using python-docx."""

import io

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.opc.constants import RELATIONSHIP_TYPE

import re
import zipfile

from cci.intake.canonicalizer import is_false_positive_link
from cci.intake.parsers.pdf import URL_REGEX, ParsedDocument, clean_extracted_url

HYPERLINK_REL_TYPE = RELATIONSHIP_TYPE.HYPERLINK


def parse_docx_document(docx_bytes: bytes) -> ParsedDocument:
    """Extracts text, tables, and relationship-bound hyperlinks from DOCX documents."""
    stream = io.BytesIO(docx_bytes)
    doc = docx.Document(stream)

    text_chunks: list[str] = []
    embedded_urls: list[str] = []
    visible_urls: list[str] = []

    # 1. Comprehensive direct extraction of all hyperlink relationships from the DOCX package
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
            for fname in zf.namelist():
                if fname.endswith('.rels'):
                    try:
                        content = zf.read(fname).decode('utf-8', errors='ignore')
                        for m in re.finditer(r'Type="[^"]*hyperlink"[^>]*Target="([^"]+)"', content, re.IGNORECASE):
                            cleaned = clean_extracted_url(m.group(1))
                            if cleaned and cleaned not in embedded_urls and not is_false_positive_link(cleaned):
                                embedded_urls.append(cleaned)
                        for m in re.finditer(r'Target="([^"]+)"[^>]*Type="[^"]*hyperlink"', content, re.IGNORECASE):
                            cleaned = clean_extracted_url(m.group(1))
                            if cleaned and cleaned not in embedded_urls and not is_false_positive_link(cleaned):
                                embedded_urls.append(cleaned)
                    except Exception:
                        pass
    except Exception:
        pass

    # 2. Keep paragraph/table order, including nested tables, text boxes, and linked header parts.
    seen_parts, seen_cells = set(), set()

    def collect(container):
        part = container.part
        if id(part) not in seen_parts:
            seen_parts.add(id(part))
            for rel in part.rels.values():
                if rel.reltype == HYPERLINK_REL_TYPE and isinstance(rel.target_ref, str):
                    cleaned = clean_extracted_url(rel.target_ref)
                    if cleaned and cleaned not in embedded_urls and not is_false_positive_link(cleaned):
                        embedded_urls.append(cleaned)
        for block in container.iter_inner_content():
            if isinstance(block, Paragraph):
                # w:t also retains text in hyperlinks and text boxes.
                text = ''.join(block._p.xpath('.//w:t/text()'))
                if text:
                    text_chunks.append(block.text or text)
                    visible_urls.extend(
                        clean_extracted_url(m.group(0))
                        for m in URL_REGEX.finditer(text)
                        if clean_extracted_url(m.group(0)) and not is_false_positive_link(clean_extracted_url(m.group(0)))
                    )
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

    # 3. Extract text from textboxes (w:txbxContent) in shapes / drawing elements
    try:
        textbox_texts = doc._element.xpath('.//w:drawing//w:txbxContent//w:t/text()')
        if textbox_texts:
            tb_combined = ' '.join(textbox_texts)
            if tb_combined.strip() and tb_combined.strip() not in text_chunks:
                text_chunks.append(tb_combined)
                for m in URL_REGEX.finditer(tb_combined):
                    cleaned = clean_extracted_url(m.group(0))
                    if cleaned and cleaned not in visible_urls and not is_false_positive_link(cleaned):
                        visible_urls.append(cleaned)
    except Exception:
        pass

    from cci.intake.parsers.image import extract_picture_from_docx
    picture = extract_picture_from_docx(docx_bytes)

    full_text = "\n".join(text_chunks)
    return ParsedDocument(
        raw_text=full_text,
        embedded_urls=embedded_urls,
        visible_urls=visible_urls,
        picture=picture,
    )
