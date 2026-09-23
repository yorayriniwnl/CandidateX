from typing import Any

"""Analysis run, stage progress, and trigger API schemas."""

from datetime import datetime
from uuid import UUID

from cci.domain.enums import AnalysisStage, AnalysisStatus, CanonicalRole
from pydantic import BaseModel, Field


class AnalysisTriggerRequest(BaseModel):
    """Request payload to initiate candidate capability evaluation."""

    candidate_id: UUID
    job_description_id: UUID | None = None
    target_role: CanonicalRole
    scoring_config_version: str | None = "4.0.0"


class StageProgressResponse(BaseModel):
    """Individual stage progress item."""

    stage_name: AnalysisStage
    status: AnalysisStatus
    sequence_order: int
    duration_seconds: float | None = None
    stage_metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class AnalysisRunResponse(BaseModel):
    """Status and progress overview for an analysis run."""

    id: UUID
    candidate_id: UUID
    job_description_id: UUID | None = None
    target_role: CanonicalRole
    status: AnalysisStatus
    stages: list[StageProgressResponse] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
