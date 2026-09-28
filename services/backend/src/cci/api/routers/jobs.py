"""Job description analysis and ontology extraction API router."""

from uuid import UUID

import cci.db.repository as repo
from cci.db.session import SessionLocal
from cci.domain.contracts import NormalizedRequirement, RoleProfile
from cci.domain.enums import CanonicalRole
from cci.jobs.parser import extract_requirements_from_jd
from cci.scoring.weights import build_role_profile
from fastapi import APIRouter, status, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field
from cci.intake.parsers.pdf import parse_pdf_document
from cci.intake.parsers.docx import parse_docx_document

router = APIRouter(prefix="/api/v1/jobs", tags=["Job Description Intelligence"])


class JobParseRequest(BaseModel):
    jd_text: str = Field(..., min_length=10, description="Raw job description text")
    role: CanonicalRole = Field(
        default=CanonicalRole.BACKEND, description="Target canonical role"
    )


class JobParseResponse(BaseModel):
    role: CanonicalRole
    requirements_count: int
    requirements: list[NormalizedRequirement]
    role_profile: RoleProfile


class JobSummaryResponse(BaseModel):
    id: UUID
    title: str
    canonical_role: str
    is_active: bool
    created_at: str

class JobUploadResponse(BaseModel):
    id: UUID
    title: str
    canonical_role: str
    is_active: bool
    created_at: str
    file_name: str | None
    requirements_count: int

@router.post(
    "/upload",
    response_model=JobUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse JD document",
)
async def upload_job_description(
    file: UploadFile = File(...),
    title: str = Form(...),
    role: CanonicalRole = Form(default=CanonicalRole.BACKEND),
    organization_id: UUID | None = Form(default=None),
) -> JobUploadResponse:
    """Uploads a PDF or DOCX job description, parses it, and stores it in DB."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing."
        )

    is_pdf = file.filename.lower().endswith(".pdf")
    is_docx = file.filename.lower().endswith(".docx")

    if not (is_pdf or is_docx):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported."
        )

    content = await file.read()

    if is_pdf:
        parsed = parse_pdf_document(content)
    else:
        parsed = parse_docx_document(content)

    requirements = extract_requirements_from_jd(parsed.raw_text)
    profile = build_role_profile(requirements, role)

    org_id = organization_id or UUID('00000000-0000-0000-0000-000000000001')

    with SessionLocal() as db:
        jd = repo.save_job_description(
            session=db,
            organization_id=org_id,
            title=title,
            canonical_role=role,
            raw_text=parsed.raw_text,
            role_profile=profile,
            requirements=requirements,
            file_name=file.filename,
        )
        db.commit()

        return JobUploadResponse(
            id=jd.id,
            title=jd.title,
            canonical_role=jd.canonical_role,
            is_active=jd.is_active,
            created_at=jd.created_at.isoformat() if jd.created_at else "",
            file_name=jd.file_name,
            requirements_count=len(requirements)
        )


@router.post(
    "/parse",
    response_model=JobParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract normalized requirements and compute softmax role weights from JD",
)
def parse_job_description(request: JobParseRequest) -> JobParseResponse:
    """Parses raw job description text into paper-aligned normalized requirements and role profile."""
    requirements = extract_requirements_from_jd(request.jd_text)
    profile = build_role_profile(requirements, request.role)

    return JobParseResponse(
        role=request.role,
        requirements_count=len(requirements),
        requirements=requirements,
        role_profile=profile,
    )


@router.get(
    "",
    response_model=list[JobSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List active job postings",
)
def list_jobs(organization_id: UUID | None = None) -> list[JobSummaryResponse]:
    """Lists saved job postings from the database."""
    try:
        with SessionLocal() as db:
            jds = repo.list_jobs(db, organization_id=organization_id)
            return [
                JobSummaryResponse(
                    id=j.id,
                    title=j.title,
                    canonical_role=j.canonical_role,
                    is_active=j.is_active,
                    created_at=j.created_at.isoformat()
                    if hasattr(j, "created_at") and j.created_at
                    else "",
                )
                for j in jds
            ]
    except Exception:
        return []
