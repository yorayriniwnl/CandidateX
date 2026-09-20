import hashlib
import io
import zipfile
from pathlib import PurePosixPath

import pymupdf
from cci.intake.manifest import build_candidate_manifest
from cci.intake.parsers.pdf import parse_pdf_document
from cci.intake.parsers.docx import parse_docx_document
from cci.live.contracts import MAX_UPLOAD, MAX_EXPANDED_BYTES, ResumeIntake


def parse_resume(data: bytes, filename: str) -> ResumeIntake:
    """Parse only bounded digital documents, without disk persistence or OCR claims."""
    if len(data) > MAX_UPLOAD:
        raise ValueError('Resume exceeds the 3 MB upload limit.')
    suffix = PurePosixPath(filename.lower()).suffix
    if suffix == '.pdf':
        with pymupdf.open(stream=data, filetype='pdf') as doc:
            if doc.is_encrypted:
                raise ValueError('Password-protected PDFs are not supported. Upload an unlocked copy.')
            if len(doc) > 30:
                raise ValueError('Resume exceeds the 30-page limit.')
        document = parse_pdf_document(data)
    elif suffix == '.docx':
        with zipfile.ZipFile(io.BytesIO(data)) as doc:
            if len(doc.infolist()) > 1500 or sum(i.file_size for i in doc.infolist()) > MAX_EXPANDED_BYTES:
                raise ValueError('DOCX exceeds the expanded document limit.')
        document = parse_docx_document(data)
    else:
        raise ValueError('Upload a digital PDF or DOCX resume.')
    if len(document.raw_text.strip()) < 15:
        raise ValueError('No readable text was found. Upload a text-based PDF or DOCX; scanned images need OCR first.')
    if len(document.raw_text) > 100000:
        raise ValueError('Resume contains too much text.')
    manifest = build_candidate_manifest(document)
    warnings = ['Extracted identity and skills are declarations, not independently verified facts.']
    if not manifest.github_urls:
        warnings.append('No GitHub link was found. You can supply a candidate-declared profile or repository before analysis.')
    return ResumeIntake(manifest=manifest, document_sha256=hashlib.sha256(data).hexdigest(),
                        filename=filename[:240], text_preview=document.raw_text[:12000], warnings=warnings)
