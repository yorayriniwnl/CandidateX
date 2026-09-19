"""Recruiter capability overrides and interview audit trail router."""

from datetime import datetime, timezone
import math
from cci.pipeline.orchestrator import rescore_dossier
from cci.graph.builder import build_dossier_graph
from typing import Any
from uuid import UUID, uuid4

import cci.db.repository as repo
from cci.api.routers.dossier import _DOSSIER_STORE, register_dossier
from cci.db.models.audit import AuditEvent
from cci.db.session import SessionLocal
from cci.domain.contracts import Dossier
from cci.domain.enums import CapabilityKey
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter(
    prefix="/api/v1/overrides", tags=["Recruiter Overrides & Audit Trail"]
)

# In-memory audit log store for instant fallback and fast lookup
_AUDIT_LOG_STORE: list[dict[str, Any]] = []


class AuditEventResponse(BaseModel):
    """Immutable audit event contract."""

    id: UUID
    event_type: str
    entity_type: str
    entity_id: str
    user_id: UUID | None = None
    details: dict[str, Any]
    created_at: str


class RecruiterOverrideRequest(BaseModel):
    """Payload to record an audited recruiter role weight override and trigger functional rescore."""

    candidate_id: UUID = Field(..., description="Candidate UUID to adjust")
    role_weights: dict[CapabilityKey, float] = Field(
        ..., description="Adjusted capability weights w_k"
    )
    justification: str = Field(
        ..., min_length=5, description="Mandatory audit justification for adjustment"
    )
    user_id: UUID | None = Field(None, description="Audited recruiter/interviewer UUID")
    organization_id: UUID | None = Field(
        None, description="Multi-tenant organization UUID"
    )

    @field_validator("role_weights")
    @classmethod
    def validate_weights(
        cls, weights: dict[CapabilityKey, float]
    ) -> dict[CapabilityKey, float]:
        if not weights:
            raise ValueError("Role weights dictionary cannot be empty")
        for k, v in weights.items():
            if not math.isfinite(v) or v < 0.0:
                raise ValueError(f"Weight for {k} cannot be negative; got {v}")
        return weights


class RecruiterOverrideResponse(BaseModel):
    """Audited result of recruiter weight override and pure functional rescore."""

    override_id: UUID
    candidate_id: UUID
    previous_rci: float | None
    rescored_rci: float | None
    rescored_coverage: float
    audit_event_id: UUID
    justification: str
    recorded_at: str
    dossier: Dossier
    persistence: str = "session"


class ProbeEvaluationItem(BaseModel):
    """Interviewer evaluation for an inquiry probe."""

    capability_key: CapabilityKey
    rating: int = Field(..., ge=1, le=5, description="Candidate capability rating 1-5")
    notes: str = Field(
        ..., min_length=3, description="Interviewer qualitative findings"
    )
    is_gap_resolved: bool = Field(
        default=False, description="Whether inquiry verified candidate competence"
    )


class InterviewFeedbackRequest(BaseModel):
    """Technical interviewer feedback record on candidate probe inquiries."""

    candidate_id: UUID
    interviewer_name: str = Field(..., min_length=2)
    probe_evaluations: list[ProbeEvaluationItem] = Field(default_factory=list)
    overall_recommendation: str = Field(
        ..., description="strong_hire, lean_hire, lean_no_hire, no_hire"
    )
    overall_notes: str | None = None


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
def record_recruiter_override(
    request: RecruiterOverrideRequest,
) -> RecruiterOverrideResponse:
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

    try:
        updated_dossier = rescore_dossier(dossier, request.role_weights, request.justification)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    normalized_weights = updated_dossier.role_weights
    previous_rci = dossier.rci
    new_rci = updated_dossier.rci
    new_coverage = updated_dossier.coverage
    # Persistent overrides get a separate run, avoiding duplicate per-run score rows.
    if request.organization_id:
        updated_dossier = updated_dossier.model_copy(update={"analysis_run_id": uuid4()})

    override_id = uuid4()
    audit_event_id = uuid4()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Persist audit trail and updated snapshot to database
    if request.organization_id:
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
                    "applied_weights": {
                        k.value: v for k, v in normalized_weights.items()
                    },
                },
            )
            db.add(audit)
            if request.organization_id:
                repo.save_dossier(db, updated_dossier, request.organization_id)
            db.commit()
      except Exception as error:
        raise HTTPException(503, "Override could not be persisted; the original dossier is unchanged.") from error

    register_dossier(updated_dossier, build_dossier_graph(updated_dossier))

    # Track in in-memory fallback log
    _AUDIT_LOG_STORE.append(
        {
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
        }
    )

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
        persistence="database" if request.organization_id else "session",
    )


@router.post(
    "/interview-feedback",
    response_model=InterviewFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Record technical interviewer inquiry probe feedback with immutable audit log",
)
def record_interview_feedback(
    request: InterviewFeedbackRequest,
) -> InterviewFeedbackResponse:
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
    _AUDIT_LOG_STORE.append(
        {
            "id": audit_event_id,
            "event_type": "interviewer_probe_feedback",
            "entity_type": "candidate",
            "entity_id": str(request.candidate_id),
            "user_id": None,
            "details": details,
            "created_at": now_iso,
        }
    )

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
    response_model=list[AuditEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Get immutable audit trail of recruiter overrides and interview feedback for a candidate",
)
def get_candidate_audit_trail(candidate_id: UUID) -> list[AuditEventResponse]:
    """Retrieves all immutable audit events for the given candidate ID."""
    results: list[AuditEventResponse] = []
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
