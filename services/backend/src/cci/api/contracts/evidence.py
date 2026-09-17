"""Evidence retrieval, filtering, and provenance API schemas."""

from cci.domain.contracts import EvidenceRecord
from cci.domain.enums import CapabilityKey, SourceFamily
from pydantic import BaseModel, Field


class EvidenceFilterParams(BaseModel):
    """Query filters for evidence exploration."""

    capability_key: CapabilityKey | None = None
    source_family: SourceFamily | None = None
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    is_positive_only: bool | None = None
    cluster_id: str | None = None


class EvidenceDetailResponse(BaseModel):
    """Detailed evidence record response."""

    record: EvidenceRecord
    repository_name: str | None = None
    file_path: str | None = None
    commit_sha: str | None = None
    raw_support_snippet: str | None = None
