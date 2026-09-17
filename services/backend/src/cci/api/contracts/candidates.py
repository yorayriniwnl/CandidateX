"""Candidate and manifest API contracts."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from cci.domain.contracts import CandidateManifest


class CandidateCreateRequest(BaseModel):
    """Payload to initiate candidate intake from supplied files/text."""
    display_name: str = Field(..., min_length=1)
    notes: Optional[str] = None


class CandidateResponse(BaseModel):
    """Candidate summary response schema."""
    id: UUID
    organization_id: UUID
    display_name: str
    primary_email: Optional[str] = None
    manifest: Optional[CandidateManifest] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ManifestUpdateRequest(BaseModel):
    """Recruiter review payload to remove erroneous URLs from parsed manifest."""
    removed_urls: List[str] = Field(default_factory=list, description="URLs rejected during manifest review")
    notes: Optional[str] = None
