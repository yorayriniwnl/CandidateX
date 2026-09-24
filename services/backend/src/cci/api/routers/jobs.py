"""Job description analysis and ontology extraction API router with multi-tenancy (Fix 29)."""

from uuid import UUID, uuid4

import cci.db.repository as repo
from cci.db.session import SessionLocal
from cci.domain.contracts import NormalizedRequirement, RoleProfile
from cci.domain.enums import CanonicalRole
from cci.jobs.parser import extract_requirements_from_jd
from cci.scoring.weights import build_role_profile
from cci.security.auth import TenantContext, get_current_tenant
from fastapi import APIRouter, Depends, Query, status
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


class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=2)
    canonical_role: CanonicalRole = Field(default=CanonicalRole.BACKEND)
    raw_text: str = Field(..., min_length=10)
    job_id: UUID | None = None


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


@router.post(
    "",
    response_model=JobSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job description entity scoped to the authenticated tenant",
)
def create_job(
    request: JobCreateRequest,
    tenant: TenantContext = Depends(get_current_tenant),
) -> JobSummaryResponse:
    """Creates a job posting strictly bound to the authenticated organization."""
    with SessionLocal() as db:
        requirements = extract_requirements_from_jd(request.raw_text)
        profile = build_role_profile(requirements, request.canonical_role)
        jd = repo.save_job_description(
            db,
            organization_id=tenant.organization_id,
            title=request.title,
            canonical_role=request.canonical_role,
            raw_text=request.raw_text,
            job_id=request.job_id or uuid4(),
            role_profile=profile,
            requirements=requirements,
        )
        db.commit()
        db.refresh(jd)
        return JobSummaryResponse(
            id=jd.id,
            title=jd.title,
            canonical_role=jd.canonical_role,
            is_active=jd.is_active,
            created_at=jd.created_at.isoformat() if hasattr(jd, "created_at") and jd.created_at else "",
        )


@router.get(
    "",
    response_model=list[JobSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List active job postings",
)
def list_jobs(
    organization_id: UUID | None = Query(None, description="Deprecated; organization identity is derived server-side"),
    tenant: TenantContext = Depends(get_current_tenant),
) -> list[JobSummaryResponse]:
    """Lists saved job postings from the database strictly scoped to the authenticated organization."""
    effective_org_id = tenant.organization_id
    try:
        with SessionLocal() as db:
            jds = repo.list_jobs(db, organization_id=effective_org_id)
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
