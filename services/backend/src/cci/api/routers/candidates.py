"""Candidate directory and manifest API router."""

from datetime import datetime, timezone
from typing import Any, Union
from uuid import UUID, uuid4

import cci.db.repository as repo
from cci.db.session import SessionLocal
from cci.logging_config import get_logger
from fastapi import APIRouter, HTTPException, status, Depends, Response, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from cci.api.pagination import PaginatedResponse, PaginationParams
from cci.middleware.rate_limit import rate_limit
import math

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/candidates", tags=["Candidate Directory"])


class CandidateSummaryResponse(BaseModel):
    id: UUID
    display_name: str
    primary_email: str | None = None
    has_completed_dossier: bool
    rci: float | None = None
    jd_fit_score: float | None = None
    observed_capabilities: int | None = None
    coverage: float | None = None
    role: str | None = None
    has_meaningful_conflict: bool = False
    created_at: str


class CandidateDetailResponse(BaseModel):
    id: UUID
    display_name: str
    primary_email: str | None = None
    manifest_data: dict[str, Any]
    is_active: bool
    created_at: str


class SaveCandidateRequest(BaseModel):
    id: str | None = None
    display_name: str
    primary_email: str | None = None
    has_completed_dossier: bool = True
    rci: float | None = None
    jd_fit_score: float | None = None
    observed_capabilities: int | None = None
    coverage: float | None = None
    role: str | None = None
    has_meaningful_conflict: bool = False
    created_at: str | None = None
    manifest_data: dict[str, Any] | None = None


_MEMORY_CANDIDATES: dict[UUID, CandidateSummaryResponse] = {}


@router.post(
    "",
    response_model=CandidateSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a candidate profile into the HR directory",
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))]
)
def save_candidate_profile(
    req: SaveCandidateRequest,
    organization_id: UUID | None = None,
) -> CandidateSummaryResponse:
    """Saves or updates a candidate profile in the HR directory."""
    try:
        cand_id = UUID(req.id) if req.id else None
    except (ValueError, TypeError):
        cand_id = None

    try:
        with SessionLocal() as db:
            if not cand_id and req.primary_email:
                stmt = select(repo.models.Candidate).where(
                    func.lower(repo.models.Candidate.primary_email) == req.primary_email.strip().lower()
                )
                existing_c = db.execute(stmt).scalars().first()
                if existing_c:
                    cand_id = existing_c.id
            if not cand_id and req.display_name:
                stmt = select(repo.models.Candidate).where(
                    func.lower(repo.models.Candidate.display_name) == req.display_name.strip().lower()
                )
                existing_n = db.execute(stmt).scalars().first()
                if existing_n:
                    cand_id = existing_n.id
    except Exception:
        pass

    if not cand_id:
        cand_id = uuid4()

    created_at_str = req.created_at or datetime.now(timezone.utc).isoformat()
    fit_score = req.jd_fit_score if req.jd_fit_score is not None else req.rci
    summary = CandidateSummaryResponse(
        id=cand_id,
        display_name=req.display_name,
        primary_email=req.primary_email,
        has_completed_dossier=req.has_completed_dossier,
        rci=req.rci,
        jd_fit_score=fit_score,
        observed_capabilities=req.observed_capabilities,
        coverage=req.coverage,
        role=req.role,
        has_meaningful_conflict=req.has_meaningful_conflict,
        created_at=created_at_str,
    )

    # Clean any duplicate entries in memory cache with matching id, email, or name
    req_email = req.primary_email.strip().lower() if req.primary_email else None
    req_name = req.display_name.strip().lower() if req.display_name else None
    to_remove = [
        k for k, v in _MEMORY_CANDIDATES.items()
        if k == cand_id
        or (req_email and v.primary_email and v.primary_email.strip().lower() == req_email)
        or (req_name and v.display_name.strip().lower() == req_name)
    ]
    for k in to_remove:
        _MEMORY_CANDIDATES.pop(k, None)
    _MEMORY_CANDIDATES[cand_id] = summary

    try:
        with SessionLocal() as db:
            org_id = organization_id or UUID("00000000-0000-0000-0000-000000000001")
            existing_org = db.get(repo.models.Organization, org_id)
            if not existing_org:
                repo.save_organization(db, name="Default Org", slug="default", org_id=org_id)
            from cci.domain.contracts import CandidateManifest as DomainManifest
            manifest_dict = req.manifest_data or {
                "candidate_id": str(cand_id),
                "full_name": req.display_name,
                "display_name": req.display_name,
                "email": req.primary_email,
                "github_urls": [],
                "portfolio_urls": [],
                "deployment_urls": [],
                "declared_skills": [],
                "extraction_metadata": {},
            }
            manifest_obj = DomainManifest.model_validate(manifest_dict)
            repo.save_candidate(db, organization_id=org_id, manifest=manifest_obj, candidate_id=cand_id)
            db.commit()
    except Exception:
        pass

    return summary


@router.get(
    "",
    response_model=Union[PaginatedResponse[CandidateSummaryResponse], list[CandidateSummaryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List all candidates with evaluation and dossier summary",
    dependencies=[Depends(rate_limit(max_requests=100, window_seconds=60))]
)
def list_candidates(
    response: Response = None,
    organization_id: UUID | None = None,
    paginated: bool = Query(False, description="Whether to return a paginated response envelope"),
    pagination: PaginationParams = Depends()
) -> Union[PaginatedResponse[CandidateSummaryResponse], list[CandidateSummaryResponse]]:
    """Lists candidates along with their latest evaluation score summary."""
    try:
        with SessionLocal() as db:
            total = repo.count_candidates(db, organization_id=organization_id)
            cands = repo.list_candidates(db, organization_id=organization_id, limit=pagination.limit, offset=pagination.offset)
            summaries = []
            db_ids = set()
            db_emails = set()
            db_names = set()
            for c in cands:
                db_ids.add(c.id)
                if c.primary_email:
                    db_emails.add(c.primary_email.strip().lower())
                if c.display_name:
                    db_names.add(c.display_name.strip().lower())
                dossier = repo.get_dossier_by_candidate_id(db, c.id)
                has_dossier = dossier is not None
                rci = dossier.rci if dossier else None
                coverage = dossier.coverage if dossier else None
                role_val = dossier.role.value if dossier else None
                has_conflict = False
                observed_count = None
                if dossier:
                    has_conflict = any(
                        conf.has_meaningful_conflict
                        for conf in dossier.capability_conflicts.values()
                    )
                    observed_count = sum(
                        1
                        for est in dossier.capability_estimates.values()
                        if est.is_observed and est.estimate is not None
                    )

                summaries.append(
                    CandidateSummaryResponse(
                        id=c.id,
                        display_name=c.display_name,
                        primary_email=c.primary_email,
                        has_completed_dossier=has_dossier,
                        rci=rci,
                        jd_fit_score=rci,
                        observed_capabilities=observed_count,
                        coverage=coverage,
                        role=role_val,
                        has_meaningful_conflict=has_conflict,
                        created_at=c.created_at.isoformat()
                        if hasattr(c, "created_at") and c.created_at
                        else "",
                    )
                )
            for mem_cand in _MEMORY_CANDIDATES.values():
                mem_email = mem_cand.primary_email.strip().lower() if mem_cand.primary_email else None
                mem_name = mem_cand.display_name.strip().lower() if mem_cand.display_name else None
                if (
                    mem_cand.id not in db_ids
                    and (not mem_email or mem_email not in db_emails)
                    and (not mem_name or mem_name not in db_names)
                ):
                    summaries.append(mem_cand)
            total_pages = (total + pagination.page_size - 1) // pagination.page_size if total > 0 else 1
            if response is not None:
                response.headers["X-Total-Count"] = str(total)
                response.headers["X-Page"] = str(pagination.page)
                response.headers["X-Page-Size"] = str(pagination.page_size)
                response.headers["X-Total-Pages"] = str(total_pages)
                
            if paginated:
                return PaginatedResponse(
                    items=summaries,
                    total=total,
                    page=pagination.page,
                    page_size=pagination.page_size,
                    total_pages=total_pages
                )
            return summaries
    except Exception as e:
        logger.exception("Failed to list candidates from database, returning in-memory cache", extra={"organization_id": str(organization_id) if organization_id else None})
        items = list(_MEMORY_CANDIDATES.values())
        if response is not None:
            response.headers["X-Total-Count"] = str(len(items))
            response.headers["X-Page"] = "1"
            response.headers["X-Page-Size"] = str(len(items))
            response.headers["X-Total-Pages"] = "1"
        if paginated:
            return PaginatedResponse(
                items=items,
                total=len(items),
                page=1,
                page_size=len(items),
                total_pages=1
            )
        return items


@router.get(
    "/{candidate_id}",
    response_model=CandidateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed candidate manifest and intake records",
    dependencies=[Depends(rate_limit(max_requests=100, window_seconds=60))]
)
def get_candidate(candidate_id: UUID) -> CandidateDetailResponse:
    """Retrieves candidate manifest details."""
    try:
        with SessionLocal() as db:
            cand = repo.get_candidate_by_id(db, candidate_id)
            if not cand:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate {candidate_id} not found",
                )
            return CandidateDetailResponse(
                id=cand.id,
                display_name=cand.display_name,
                primary_email=cand.primary_email,
                manifest_data=cand.manifest_data,
                is_active=cand.is_active,
                created_at=cand.created_at.isoformat()
                if hasattr(cand, "created_at") and cand.created_at
                else "",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a candidate and their evaluation records",
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))]
)
def delete_candidate(candidate_id: UUID) -> None:
    """Deletes a candidate from the database and in-memory cache."""
    _MEMORY_CANDIDATES.pop(candidate_id, None)
    try:
        with SessionLocal() as db:
            repo.delete_candidate(db, candidate_id)
            db.commit()
    except Exception as e:
        logger.exception("Failed to delete candidate from database", extra={"candidate_id": str(candidate_id)})
    return None


OFFICIAL_TEAM_EMAILS = {
    "2329027@kiit.ac.in",
    "2329100@kiit.ac.in",
    "2329179@kiit.ac.in",
    "2329065@kiit.ac.in",
    "2329064@kiit.ac.in",
    "2329195@kiit.ac.in",
}
OFFICIAL_TEAM_IDS = {
    UUID("11111111-1111-1111-1111-111111111111"),
    UUID("22222222-2222-2222-2222-222222222222"),
    UUID("33333333-3333-3333-3333-333333333333"),
    UUID("44444444-4444-4444-4444-444444444444"),
    UUID("55555555-5555-5555-5555-555555555555"),
    UUID("77777777-7777-7777-7777-777777777777"),
}


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    summary="Purge or clean candidates, optionally preserving those with completed dossiers or official team members",
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))]
)
def purge_candidates(keep_team_only: bool = False) -> dict[str, Any]:
    """Purges candidates, optionally keeping official team members and completed dossiers."""
    deleted_count = 0
    try:
        with SessionLocal() as db:
            cands = repo.list_candidates(db)
            for c in cands:
                if keep_team_only:
                    is_team = c.id in OFFICIAL_TEAM_IDS or (
                        c.primary_email and c.primary_email.strip().lower() in OFFICIAL_TEAM_EMAILS
                    )
                    dossier = repo.get_dossier_by_candidate_id(db, c.id)
                    if is_team or dossier is not None:
                        continue
                repo.delete_candidate(db, c.id)
                deleted_count += 1
            db.commit()
    except Exception as e:
        logger.exception("Failed to purge candidates from database", extra={"keep_team_only": keep_team_only})

    to_delete = [
        cid for cid, item in _MEMORY_CANDIDATES.items()
        if not (
            keep_team_only
            and (
                cid in OFFICIAL_TEAM_IDS
                or (item.primary_email and item.primary_email.strip().lower() in OFFICIAL_TEAM_EMAILS)
                or item.has_completed_dossier
            )
        )
    ]
    for cid in to_delete:
        _MEMORY_CANDIDATES.pop(cid, None)
        deleted_count += 1

    return {"deleted": deleted_count, "keep_team_only": keep_team_only}


