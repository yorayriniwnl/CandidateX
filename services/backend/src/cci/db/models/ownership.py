"""Candidate repository authorship and ownership assessments."""

import uuid
from typing import Optional
from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cci.db.base import Base, GUID, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class OwnershipAssessmentEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Estimated ownership o_e with provenance and feature vectors."""
    __tablename__ = "ownership_assessments"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repository_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True
    )
    repository_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    candidate_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    ownership_score: Mapped[float] = mapped_column(Float, nullable=False)  # o_e in [0, 1]
    feature_vector: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_vendor_or_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attribution_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    limitations: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
