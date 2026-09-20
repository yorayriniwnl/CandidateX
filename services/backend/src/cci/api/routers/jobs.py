"""Job description analysis and ontology extraction API router."""

from uuid import UUID

import cci.db.repository as repo
from cci.db.session import SessionLocal
from cci.domain.contracts import NormalizedRequirement, RoleProfile
from cci.domain.enums import CanonicalRole
from cci.jobs.parser import extract_requirements_from_jd
from cci.scoring.weights import build_role_profile
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

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
