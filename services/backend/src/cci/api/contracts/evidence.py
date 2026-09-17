"""Evidence retrieval, filtering, and provenance API schemas."""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from cci.domain.contracts import EvidenceRecord
from cci.domain.enums import CapabilityKey, SourceFamily


class EvidenceFilterParams(BaseModel):
    """Query filters for evidence exploration."""
    capability_key: Optional[CapabilityKey] = None
    source_family: Optional[SourceFamily] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_positive_only: Optional[bool] = None
    cluster_id: Optional[str] = None


class EvidenceDetailResponse(BaseModel):
    """Detailed evidence record response."""
    record: EvidenceRecord
    repository_name: Optional[str] = None
    file_path: Optional[str] = None
    commit_sha: Optional[str] = None
    raw_support_snippet: Optional[str] = None
