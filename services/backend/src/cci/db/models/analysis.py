"""Analysis run and execution stage tracking entities."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cci.db.base import Base, GUID, JSONType, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AnalysisRun(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Execution lifecycle of an end-to-end Candidate Capability Intelligence evaluation."""
    __tablename__ = "analysis_runs"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_description_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_role: Mapped[str] = mapped_column(String(50), nullable=False)  # CanonicalRole enum
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    stages: Mapped[List["AnalysisStageRun"]] = relationship(
        "AnalysisStageRun", back_populates="analysis_run", cascade="all, delete-orphan"
    )


class AnalysisStageRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Detailed execution status of an individual pipeline stage."""
    __tablename__ = "analysis_stage_runs"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(50), nullable=False)  # AnalysisStage enum
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stage_metadata: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="stages")
