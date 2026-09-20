"""Candidate and manifest API contracts."""

from datetime import datetime
from uuid import UUID

from cci.domain.contracts import CandidateManifest
from pydantic import BaseModel, Field


class CandidateCreateRequest(BaseModel):
    """Payload to initiate candidate intake from supplied files/text."""

    display_name: str = Field(..., min_length=1)
    notes: str | None = None


class CandidateResponse(BaseModel):
    """Candidate summary response schema."""

    id: UUID
    organization_id: UUID
    display_name: str
    primary_email: str | None = None
    manifest: CandidateManifest | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ManifestUpdateRequest(BaseModel):
    """Recruiter review payload to remove erroneous URLs from parsed manifest."""

    removed_urls: list[str] = Field(
        default_factory=list, description="URLs rejected during manifest review"
    )
    notes: str | None = None
