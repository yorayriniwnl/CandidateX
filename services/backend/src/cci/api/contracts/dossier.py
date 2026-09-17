"""Interviewer dossier and interview probe API response schemas."""

from uuid import UUID

from cci.domain.contracts import Dossier, InterviewQuestion, ProbePriority
from pydantic import BaseModel, Field


class DossierResponse(BaseModel):
    """Complete structured dossier payload for technical interviewer UI."""

    dossier: Dossier


class InterviewProbesResponse(BaseModel):
    """Prioritized interview inquiry targets and grounded questions."""

    analysis_run_id: UUID
    probes: list[ProbePriority] = Field(default_factory=list)
    questions: list[InterviewQuestion] = Field(default_factory=list)
