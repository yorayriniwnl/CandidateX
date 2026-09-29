import hashlib
import io
import zipfile
import re
from pathlib import PurePosixPath
from typing import Any

import pymupdf
from cci.intake.manifest import build_candidate_manifest, segment_sections, extract_skills_from_section
from cci.intake.parsers.pdf import parse_pdf_document
from cci.intake.parsers.docx import parse_docx_document
from cci.live.contracts import MAX_UPLOAD, MAX_EXPANDED_BYTES, ResumeIntake, ResumeReview


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
    sections = segment_sections(document.raw_text)
    learning = extract_skills_from_section([line for line in sections['skills'] if re.match(
        r'^(?:currently\s+)?(?:learning|expanding|familiarizing|exploring)\b', line, re.I)])
    observations = []
    if manifest.display_name == 'Unknown Candidate':
        observations.append('A reliable name header was not found. Review the extracted text.')
    for section in ('projects', 'experience', 'education', 'certifications'):
        if not sections[section]:
            observations.append(f'No distinct {section} section was detected; this does not establish absence.')
    if sections['certifications'] and not manifest.credential_urls:
        observations.append('Certificates are mentioned without recognized verification links. Add public credential URLs before analysis.')
    review = ResumeReview(sections={k: [line[:1500] for line in v[:60]] for k, v in sections.items() if v},
                          learning_skills=learning, observations=observations)
    warnings = ['Extracted identity and skills are declarations, not independently verified facts.']
    if not manifest.github_urls:
        warnings.append('No GitHub link was found. You can supply a candidate-declared profile or repository before analysis.')
    return ResumeIntake(manifest=manifest, picture=manifest.picture, document_sha256=hashlib.sha256(data).hexdigest(),
                        filename=filename[:240], text_preview=document.raw_text[:12000], warnings=warnings, resume_review=review)


def parse_jd_document(data: bytes, filename: str) -> dict[str, Any]:
    """Parse a job description, hiring rubric, or recruitment standards document (PDF, DOCX, DOC, TXT)."""
    if len(data) > MAX_UPLOAD:
        raise ValueError('Document exceeds the 3 MB upload limit.')

    suffix = PurePosixPath(filename.lower()).suffix
    if suffix == '.pdf':
        with pymupdf.open(stream=data, filetype='pdf') as doc:
            if doc.is_encrypted:
                raise ValueError('Password-protected PDFs are not supported. Upload an unlocked copy.')
            if len(doc) > 30:
                raise ValueError('Document exceeds the 30-page limit.')
        document = parse_pdf_document(data)
        raw_text = document.raw_text
    elif suffix == '.docx':
        with zipfile.ZipFile(io.BytesIO(data)) as doc:
            if len(doc.infolist()) > 1500 or sum(i.file_size for i in doc.infolist()) > MAX_EXPANDED_BYTES:
                raise ValueError('DOCX exceeds the expanded document limit.')
        document = parse_docx_document(data)
        raw_text = document.raw_text
    elif suffix == '.doc':
        try:
            document = parse_docx_document(data)
            raw_text = document.raw_text
        except Exception:
            try:
                decoded = data.decode('utf-8', errors='ignore')
                printable = ''.join(c for c in decoded if c.isprintable() or c in '\n\r\t')
                if len(printable.strip()) >= 20:
                    raw_text = printable
                else:
                    raise ValueError()
            except Exception:
                raise ValueError('Legacy binary .doc format could not be decoded. Please save or export as .docx or .pdf.')
    elif suffix in ('.txt', '.md'):
        try:
            raw_text = data.decode('utf-8')
        except UnicodeDecodeError:
            raw_text = data.decode('latin-1', errors='replace')
    else:
        raise ValueError('Upload a PDF, DOCX, DOC, or TXT document.')

    clean_text = raw_text.strip()
    if len(clean_text) < 10:
        raise ValueError('No readable text was found in the document. Ensure it is not a scanned image.')

    truncated = len(clean_text) > 20000
    text = clean_text[:20000]
    warnings: list[str] = []
    if truncated:
        warnings.append('Document text was truncated to 20,000 characters to fit the analysis limit.')

    return {
        'text': text,
        'filename': filename[:240],
        'char_count': len(text),
        'raw_char_count': len(clean_text),
        'truncated': truncated,
        'warnings': warnings,
    }

