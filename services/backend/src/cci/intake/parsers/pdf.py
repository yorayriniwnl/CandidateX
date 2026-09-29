"""Digital PDF parser with embedded hyperlink extraction using PyMuPDF."""

import re
from dataclasses import dataclass, field

import fitz  # type: ignore  # PyMuPDF

from cci.intake.canonicalizer import COMMON_TLDS, is_false_positive_link

URL_REGEX = re.compile(
    r"(?<![@.\w])(?:"
    r"(?:https?://|www\.|git@)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    r"|"
    r"[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9](?:\.[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])*\."
    rf"(?:{COMMON_TLDS})(?![\w@])"
    r")"
    r"(?:[/?#][^\s()<>\"\'`]*)?",
    re.IGNORECASE,
)


def clean_extracted_url(raw_url: str) -> str:
    """Strips leading/trailing punctuation, quotes, and wrapping brackets."""
    u = raw_url.strip()
    u = re.sub(r'^[<(\[\'\"`]+', '', u)
    u = re.sub(r'[>)\],;:\'\"`.!?]+$', '', u)
    return u.strip()


@dataclass
class ParsedDocument:
    """Standardized output of document extraction."""

    raw_text: str
    embedded_urls: list[str] = field(default_factory=list)
    visible_urls: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    picture: str | None = None


def parse_pdf_document(pdf_bytes: bytes) -> ParsedDocument:
    """Extracts text, embedded hyperlink annotations, and picture from digital PDF.

    Strict invariant: no OCR is performed in v1, and no URLs are invented.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    text_chunks: list[str] = []
    embedded_urls: list[str] = []
    visible_urls: list[str] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_text = page.get_text("text", sort=True)
        text_chunks.append(page_text)

        # 1. Extract embedded hyperlinks (PDF URI annotations)
        links = page.get_links()
        for link in links:
            uri = link.get("uri")
            if uri and isinstance(uri, str):
                cleaned_uri = clean_extracted_url(uri)
                if cleaned_uri and not is_false_positive_link(cleaned_uri):
                    embedded_urls.append(cleaned_uri)

        # 2. Extract visible URLs from text (including joining line-wrapped URLs ending with path continuations)
        unwrapped_text = re.sub(r'(https?://\S*[-/&?=])\n\s*([a-zA-Z0-9_.-]+)', r'\1\2', page_text)
        for match in URL_REGEX.finditer(unwrapped_text):
            cleaned = clean_extracted_url(match.group(0))
            if cleaned and not is_false_positive_link(cleaned):
                visible_urls.append(cleaned)

    # 3. Comprehensive embedded URI extraction from PDF objects (widgets, form buttons, actions)
    try:
        seen_uris = set(embedded_urls)
        for xref in range(1, doc.xref_length()):
            obj_str = doc.xref_object(xref)
            if "/URI" in obj_str:
                for m in re.finditer(r'/URI\s*(?:\((.*?)\)|<([0-9a-fA-F]+)>)', obj_str):
                    uri_val = None
                    if m.group(1):
                        uri_val = m.group(1).replace(r'\(', '(').replace(r'\)', ')').replace(r'\\', '\\')
                    elif m.group(2):
                        try:
                            uri_val = bytes.fromhex(m.group(2)).decode('utf-8', errors='ignore')
                        except Exception:
                            pass
                    if uri_val and isinstance(uri_val, str):
                        cleaned_uri = clean_extracted_url(uri_val)
                        if (
                            cleaned_uri
                            and cleaned_uri not in seen_uris
                            and not is_false_positive_link(cleaned_uri)
                            and re.match(r'^(?:https?://|www\.|git@)', cleaned_uri, re.IGNORECASE)
                        ):
                            seen_uris.add(cleaned_uri)
                            embedded_urls.append(cleaned_uri)
    except Exception:
        pass

    # 4. Extract candidate picture if present
    from cci.intake.parsers.image import extract_picture_from_pdf
    picture = extract_picture_from_pdf(doc)

    doc.close()

    full_text = "\n".join(text_chunks)
    return ParsedDocument(
        raw_text=full_text,
        embedded_urls=embedded_urls,
        visible_urls=visible_urls,
        picture=picture,
    )
