import hashlib
import io
import zipfile
import re
from pathlib import PurePosixPath
from uuid import UUID

import pymupdf
from cci.intake.manifest import build_candidate_manifest, segment_sections, extract_skills_from_section
from cci.intake.parsers.pdf import parse_pdf_document
from cci.intake.parsers.docx import parse_docx_document
from cci.limits import get_system_limits
from cci.live.contracts import MAX_UPLOAD, MAX_EXPANDED_BYTES, ResumeIntake, ResumeReview


def parse_resume(data: bytes, filename: str, analysis_run_id: UUID | None = None) -> ResumeIntake:
    """Parse only bounded digital documents, without disk persistence or OCR claims."""
    limits = get_system_limits()
    if len(data) > limits.max_upload_bytes.budget:
        raise ValueError(f'Resume exceeds the {limits.max_upload_bytes.budget // (1024 * 1024)} MB upload limit.')
    suffix = PurePosixPath(filename.lower()).suffix
    if suffix == '.pdf':
        with pymupdf.open(stream=data, filetype='pdf') as doc:
            if doc.is_encrypted:
                raise ValueError('Password-protected PDFs are not supported. Upload an unlocked copy.')
            if len(doc) > limits.max_resume_pages.budget:
                raise ValueError(f'Resume exceeds the {limits.max_resume_pages.budget}-page limit.')
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
    kwargs = {
        'manifest': manifest,
        'document_sha256': hashlib.sha256(data).hexdigest(),
        'filename': filename[:240],
        'text_preview': document.raw_text[:limits.max_text_chars.budget],
        'warnings': warnings,
        'resume_review': review,
    }
    if analysis_run_id is not None:
        kwargs['analysis_run_id'] = analysis_run_id
    return ResumeIntake(**kwargs)
