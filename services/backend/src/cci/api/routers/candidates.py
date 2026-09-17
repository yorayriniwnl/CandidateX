"""Candidate directory and manifest API router."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from cci.db.session import SessionLocal
import cci.db.repository as repo

router = APIRouter(prefix="/api/v1/candidates", tags=["Candidate Directory"])


class CandidateSummaryResponse(BaseModel):
    id: UUID
    display_name: str
    primary_email: Optional[str] = None
    has_completed_dossier: bool
    rci: Optional[float] = None
    coverage: Optional[float] = None
    role: Optional[str] = None
    has_meaningful_conflict: bool = False
    created_at: str


class CandidateDetailResponse(BaseModel):
    id: UUID
    display_name: str
    primary_email: Optional[str] = None
    manifest_data: Dict[str, Any]
    is_active: bool
    created_at: str


@router.get(
    "",
    response_model=List[CandidateSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all candidates with evaluation and dossier summary",
)
def list_candidates(organization_id: Optional[UUID] = None) -> List[CandidateSummaryResponse]:
    """Lists candidates along with their latest evaluation score summary."""
    try:
        with SessionLocal() as db:
            cands = repo.list_candidates(db, organization_id=organization_id)
            summaries = []
            for c in cands:
                dossier = repo.get_dossier_by_candidate_id(db, c.id)
                has_dossier = dossier is not None
                rci = dossier.rci if dossier else None
                coverage = dossier.coverage if dossier else None
                role_val = dossier.role.value if dossier else None
                has_conflict = False
                if dossier:
                    has_conflict = any(conf.has_meaningful_conflict for conf in dossier.capability_conflicts.values())

                summaries.append(
                    CandidateSummaryResponse(
                        id=c.id,
                        display_name=c.display_name,
                        primary_email=c.primary_email,
                        has_completed_dossier=has_dossier,
                        rci=rci,
                        coverage=coverage,
                        role=role_val,
                        has_meaningful_conflict=has_conflict,
                        created_at=c.created_at.isoformat() if hasattr(c, "created_at") and c.created_at else "",
                    )
                )
            return summaries
    except Exception:
        return []


@router.get(
    "/{candidate_id}",
    response_model=CandidateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed candidate manifest and intake records",
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
                created_at=cand.created_at.isoformat() if hasattr(cand, "created_at") and cand.created_at else "",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
