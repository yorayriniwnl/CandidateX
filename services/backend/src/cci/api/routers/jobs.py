"""Job description analysis and ontology extraction API router."""

from uuid import UUID

import cci.db.repository as repo
from cci.db.session import SessionLocal
from cci.domain.contracts import NormalizedRequirement, RoleProfile
from cci.domain.enums import CanonicalRole
from cci.jobs.parser import extract_requirements_from_jd
from cci.scoring.weights import build_role_profile
from typing import Union
from fastapi import APIRouter, status, UploadFile, File, Form, HTTPException, Depends, Request, Response, Query
from pydantic import BaseModel, Field
from cci.api.pagination import PaginatedResponse, PaginationParams
from cci.middleware.rate_limit import rate_limit
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
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))]
)
async def upload_job_description(
    request: Request,
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

    content_length = request.headers.get("Content-Length")
    if content_length and int(content_length) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
        
    chunks = []
    size = 0
    while True:
        chunk = await file.read(65536)
        if not chunk:
            break
        size += len(chunk)
        if size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)
    content = b"".join(chunks)
    
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
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))]
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
    response_model=Union[PaginatedResponse[JobSummaryResponse], list[JobSummaryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List active job postings",
    dependencies=[Depends(rate_limit(max_requests=100, window_seconds=60))]
)
def list_jobs(
    response: Response = None,
    organization_id: UUID | None = None,
    paginated: bool = Query(False, description="Whether to return a paginated response envelope"),
    pagination: PaginationParams = Depends()
) -> Union[PaginatedResponse[JobSummaryResponse], list[JobSummaryResponse]]:
    """Lists saved job postings from the database."""
    try:
        with SessionLocal() as db:
            total = repo.count_jobs(db, organization_id=organization_id)
            jds = repo.list_jobs(db, organization_id=organization_id, limit=pagination.limit, offset=pagination.offset)
            items = [
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
            total_pages = (total + pagination.page_size - 1) // pagination.page_size if total > 0 else 1
            if response is not None:
                response.headers["X-Total-Count"] = str(total)
                response.headers["X-Page"] = str(pagination.page)
                response.headers["X-Page-Size"] = str(pagination.page_size)
                response.headers["X-Total-Pages"] = str(total_pages)
                
            if paginated:
                return PaginatedResponse(
                    items=items,
                    total=total,
                    page=pagination.page,
                    page_size=pagination.page_size,
                    total_pages=total_pages
                )
            return items
    except Exception as e:
        from cci.logging_config import get_logger
        logger = get_logger(__name__)
        logger.exception("Failed to list jobs from database", extra={"organization_id": str(organization_id) if organization_id else None})
        if response is not None:
            response.headers["X-Total-Count"] = "0"
            response.headers["X-Page"] = "1"
            response.headers["X-Page-Size"] = "20"
            response.headers["X-Total-Pages"] = "1"
        if paginated:
            return PaginatedResponse(
                items=[],
                total=0,
                page=1,
                page_size=20,
                total_pages=1
            )
        return []
