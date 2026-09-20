"""Digital PDF parser with embedded hyperlink extraction using PyMuPDF."""

import re
from dataclasses import dataclass, field

import fitz  # type: ignore  # PyMuPDF

URL_REGEX = re.compile(
    r"(?<![@.\w])(?:(?:https?://|www\.|git@)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:[/?#][^\s()<>]+)?|[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.(?:com|org|net|io|dev|app|in|me|ai|edu)(?:[/?#][^\s()<>]+)?)(?![@\w])",
    re.IGNORECASE,
)


@dataclass
class ParsedDocument:
    """Standardized output of document extraction."""

    raw_text: str
    embedded_urls: list[str] = field(default_factory=list)
    visible_urls: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


def parse_pdf_document(pdf_bytes: bytes) -> ParsedDocument:
    """Extracts text and embedded hyperlink annotations from digital PDF.

    Strict invariant: no OCR is performed in v1, and no URLs are invented.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    text_chunks: list[str] = []
    embedded_urls: list[str] = []
    visible_urls: list[str] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_text = page.get_text("text")
        text_chunks.append(page_text)

        # 1. Extract embedded hyperlinks (PDF URI annotations)
        links = page.get_links()
        for link in links:
            uri = link.get("uri")
            if uri and isinstance(uri, str):
                embedded_urls.append(uri.strip())

        # 2. Extract visible URLs from text
        for match in URL_REGEX.finditer(page_text):
            visible_urls.append(match.group(0).strip())

    doc.close()

    full_text = "\n".join(text_chunks)
    return ParsedDocument(
        raw_text=full_text,
        embedded_urls=embedded_urls,
        visible_urls=visible_urls,
    )
