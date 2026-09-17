"""Interviewer dossier and interview probe API response schemas."""

from typing import List
from uuid import UUID
from pydantic import BaseModel, Field

from cci.domain.contracts import Dossier, InterviewQuestion, ProbePriority


class DossierResponse(BaseModel):
    """Complete structured dossier payload for technical interviewer UI."""
    dossier: Dossier


class InterviewProbesResponse(BaseModel):
    """Prioritized interview inquiry targets and grounded questions."""
    analysis_run_id: UUID
    probes: List[ProbePriority] = Field(default_factory=list)
    questions: List[InterviewQuestion] = Field(default_factory=list)
