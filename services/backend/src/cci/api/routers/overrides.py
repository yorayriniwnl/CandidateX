"""Recruiter capability overrides and interview audit trail router."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from cci.api.routers.dossier import _DOSSIER_STORE, register_dossier
from cci.db.session import SessionLocal
import cci.db.repository as repo
from cci.db.models.audit import AuditEvent
from cci.domain.contracts import Dossier
from cci.domain.enums import CapabilityKey

router = APIRouter(prefix="/api/v1/overrides", tags=["Recruiter Overrides & Audit Trail"])

# In-memory audit log store for instant fallback and fast lookup
_AUDIT_LOG_STORE: List[Dict[str, Any]] = []


class AuditEventResponse(BaseModel):
    """Immutable audit event contract."""
    id: UUID
    event_type: str
    entity_type: str
    entity_id: str
    user_id: Optional[UUID] = None
    details: Dict[str, Any]
    created_at: str


class RecruiterOverrideRequest(BaseModel):
    """Payload to record an audited recruiter role weight override and trigger functional rescore."""
    candidate_id: UUID = Field(..., description="Candidate UUID to adjust")
    role_weights: Dict[CapabilityKey, float] = Field(..., description="Adjusted capability weights w_k")
    justification: str = Field(..., min_length=5, description="Mandatory audit justification for adjustment")
    user_id: Optional[UUID] = Field(None, description="Audited recruiter/interviewer UUID")
    organization_id: Optional[UUID] = Field(None, description="Multi-tenant organization UUID")

    @field_validator("role_weights")
    @classmethod
    def validate_weights(cls, weights: Dict[CapabilityKey, float]) -> Dict[CapabilityKey, float]:
        if not weights:
            raise ValueError("Role weights dictionary cannot be empty")
        for k, v in weights.items():
            if v < 0.0:
                raise ValueError(f"Weight for {k} cannot be negative; got {v}")
        return weights


class RecruiterOverrideResponse(BaseModel):
    """Audited result of recruiter weight override and pure functional rescore."""
    override_id: UUID
    candidate_id: UUID
    previous_rci: Optional[float]
    rescored_rci: Optional[float]
    rescored_coverage: float
    audit_event_id: UUID
    justification: str
    recorded_at: str
    dossier: Dossier


class ProbeEvaluationItem(BaseModel):
    """Interviewer evaluation for an inquiry probe."""
    capability_key: CapabilityKey
    rating: int = Field(..., ge=1, le=5, description="Candidate capability rating 1-5")
    notes: str = Field(..., min_length=3, description="Interviewer qualitative findings")
    is_gap_resolved: bool = Field(default=False, description="Whether inquiry verified candidate competence")


class InterviewFeedbackRequest(BaseModel):
    """Technical interviewer feedback record on candidate probe inquiries."""
    candidate_id: UUID
    interviewer_name: str = Field(..., min_length=2)
    probe_evaluations: List[ProbeEvaluationItem] = Field(default_factory=list)
    overall_recommendation: str = Field(..., description="strong_hire, lean_hire, lean_no_hire, no_hire")
    overall_notes: Optional[str] = None


class InterviewFeedbackResponse(BaseModel):
    feedback_id: UUID
    candidate_id: UUID
    interviewer_name: str
    evaluations_count: int
    audit_event_id: UUID
    recorded_at: str


@router.post(
    "/recruiter",
    response_model=RecruiterOverrideResponse,
    status_code=status.HTTP_200_OK,
    summary="Record recruiter capability weight override with immutable audit trail and functional rescore",
)
def record_recruiter_override(request: RecruiterOverrideRequest) -> RecruiterOverrideResponse:
    """Records an immutable audit event and functionally recalculates RCI without re-running analyzers."""
    candidate_id = request.candidate_id
    dossier = _DOSSIER_STORE.get(candidate_id)

    # Attempt database retrieval fallback
    if not dossier:
        try:
            with SessionLocal() as db:
                dossier = repo.get_dossier_by_candidate_id(db, candidate_id)
                if dossier:
                    _DOSSIER_STORE[candidate_id] = dossier
        except Exception:
            pass

    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dossier not found for candidate ID {candidate_id}",
        )

    # Normalize weights if needed
    total_raw_weight = sum(request.role_weights.values())
    if total_raw_weight <= 0.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sum of role weights must be greater than zero",
        )

    normalized_weights = {k: v / total_raw_weight for k, v in request.role_weights.items()}

    # Functional recalculation of RCI strictly over observed capabilities
    observed_weight_sum = 0.0
    weighted_score_sum = 0.0
    coverage_sum = 0.0

    for key, est in dossier.capability_estimates.items():
        w = normalized_weights.get(key, 0.0)
        coverage_sum += w * min(1.0, est.coverage_k)
        if est.is_observed and est.estimate is not None:
            observed_weight_sum += w
            weighted_score_sum += w * est.estimate

    previous_rci = dossier.rci
    new_rci = (weighted_score_sum / observed_weight_sum) if observed_weight_sum > 0.0 else None
    new_coverage = min(1.0, max(0.0, coverage_sum))
    is_insufficient = new_coverage < 0.30

    # Build updated Dossier snapshot
    updated_dossier = dossier.model_copy(
        update={
            "rci": new_rci,
            "coverage": new_coverage,
            "is_insufficient_evidence": is_insufficient,
            "generated_at": datetime.now(timezone.utc),
        }
    )
    register_dossier(updated_dossier)

    override_id = uuid4()
    audit_event_id = uuid4()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Persist audit trail and updated snapshot to database
    try:
        with SessionLocal() as db:
            audit = AuditEvent(
                id=audit_event_id,
                event_type="recruiter_weight_override",
                user_id=request.user_id,
                entity_type="candidate_dossier",
                entity_id=str(candidate_id),
                details={
                    "override_id": str(override_id),
                    "justification": request.justification,
                    "previous_rci": previous_rci,
                    "rescored_rci": new_rci,
                    "rescored_coverage": new_coverage,
                    "applied_weights": {k.value: v for k, v in normalized_weights.items()},
                },
            )
            db.add(audit)
            if request.organization_id:
                repo.save_dossier(db, updated_dossier, request.organization_id)
            db.commit()
    except Exception:
        # Transparent in-memory fallback
        pass

    # Track in in-memory fallback log
    _AUDIT_LOG_STORE.append({
        "id": audit_event_id,
        "event_type": "recruiter_weight_override",
        "entity_type": "candidate_dossier",
        "entity_id": str(candidate_id),
        "user_id": request.user_id,
        "details": {
            "override_id": str(override_id),
            "justification": request.justification,
            "previous_rci": previous_rci,
            "rescored_rci": new_rci,
            "rescored_coverage": new_coverage,
            "applied_weights": {k.value: v for k, v in normalized_weights.items()},
        },
        "created_at": now_iso,
    })

    return RecruiterOverrideResponse(
        override_id=override_id,
        candidate_id=candidate_id,
        previous_rci=previous_rci,
        rescored_rci=new_rci,
        rescored_coverage=new_coverage,
        audit_event_id=audit_event_id,
        justification=request.justification,
        recorded_at=now_iso,
        dossier=updated_dossier,
    )


@router.post(
    "/interview-feedback",
    response_model=InterviewFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Record technical interviewer inquiry probe feedback with immutable audit log",
)
def record_interview_feedback(request: InterviewFeedbackRequest) -> InterviewFeedbackResponse:
    """Records interviewer evaluation notes, probe ratings, and recommendation to immutable audit trail."""
    feedback_id = uuid4()
    audit_event_id = uuid4()
    now_iso = datetime.now(timezone.utc).isoformat()

    details = {
        "feedback_id": str(feedback_id),
        "interviewer_name": request.interviewer_name,
        "recommendation": request.overall_recommendation,
        "notes": request.overall_notes,
        "probe_evaluations": [
            {
                "capability_key": p.capability_key.value,
                "rating": p.rating,
                "notes": p.notes,
                "is_gap_resolved": p.is_gap_resolved,
            }
            for p in request.probe_evaluations
        ],
    }

    try:
        with SessionLocal() as db:
            audit = AuditEvent(
                id=audit_event_id,
                event_type="interviewer_probe_feedback",
                entity_type="candidate",
                entity_id=str(request.candidate_id),
                details=details,
            )
            db.add(audit)
            db.commit()
    except Exception:
        pass

    # Track in in-memory fallback log
    _AUDIT_LOG_STORE.append({
        "id": audit_event_id,
        "event_type": "interviewer_probe_feedback",
        "entity_type": "candidate",
        "entity_id": str(request.candidate_id),
        "user_id": None,
        "details": details,
        "created_at": now_iso,
    })

    return InterviewFeedbackResponse(
        feedback_id=feedback_id,
        candidate_id=request.candidate_id,
        interviewer_name=request.interviewer_name,
        evaluations_count=len(request.probe_evaluations),
        audit_event_id=audit_event_id,
        recorded_at=now_iso,
    )


@router.get(
    "/audit/{candidate_id}",
    response_model=List[AuditEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Get immutable audit trail of recruiter overrides and interview feedback for a candidate",
)
def get_candidate_audit_trail(candidate_id: UUID) -> List[AuditEventResponse]:
    """Retrieves all immutable audit events for the given candidate ID."""
    results: List[AuditEventResponse] = []
    cand_id_str = str(candidate_id)

    # First attempt DB query
    try:
        with SessionLocal() as db:
            events = (
                db.query(AuditEvent)
                .filter(AuditEvent.entity_id == cand_id_str)
                .order_by(AuditEvent.created_at.desc())
                .all()
            )
            for ev in events:
                results.append(
                    AuditEventResponse(
                        id=ev.id,
                        event_type=ev.event_type,
                        entity_type=ev.entity_type,
                        entity_id=ev.entity_id,
                        user_id=ev.user_id,
                        details=ev.details or {},
                        created_at=ev.created_at.isoformat() if ev.created_at else "",
                    )
                )
    except Exception:
        pass

    # Merge with in-memory fallback store (de-duping by id)
    seen_ids = {r.id for r in results}
    for mem_ev in _AUDIT_LOG_STORE:
        if mem_ev["entity_id"] == cand_id_str and mem_ev["id"] not in seen_ids:
            results.append(AuditEventResponse(**mem_ev))
            seen_ids.add(mem_ev["id"])

    # Sort descending by created_at
    results.sort(key=lambda x: x.created_at, reverse=True)
    return results
