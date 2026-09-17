"""Analysis run, stage progress, and trigger API schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from cci.domain.enums import AnalysisStage, AnalysisStatus, CanonicalRole


class AnalysisTriggerRequest(BaseModel):
    """Request payload to initiate candidate capability evaluation."""
    candidate_id: UUID
    job_description_id: Optional[UUID] = None
    target_role: CanonicalRole
    scoring_config_version: Optional[str] = "1.0.0"


class StageProgressResponse(BaseModel):
    """Individual stage progress item."""
    stage_name: AnalysisStage
    status: AnalysisStatus
    sequence_order: int
    duration_seconds: Optional[float] = None
    stage_metadata: dict = Field(default_factory=dict)
    error_message: Optional[str] = None


class AnalysisRunResponse(BaseModel):
    """Status and progress overview for an analysis run."""
    id: UUID
    candidate_id: UUID
    job_description_id: Optional[UUID] = None
    target_role: CanonicalRole
    status: AnalysisStatus
    stages: List[StageProgressResponse] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
