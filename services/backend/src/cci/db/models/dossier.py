"""Dossier items and consolidated interviewer dossier snapshots."""

import uuid
from typing import List
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cci.db.base import Base, GUID, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class DossierSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Consolidated technical dossier snapshot for the interviewer."""
    __tablename__ = "dossier_snapshots"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_runs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    rci: Mapped[float] = mapped_column(Float, nullable=True)
    coverage: Mapped[float] = mapped_column(Float, nullable=False)
    is_insufficient_evidence: Mapped[bool] = mapped_column(nullable=False)
    summary_payload: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    limitations: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    version_metadata: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)

    items: Mapped[List["DossierItem"]] = relationship(
        "DossierItem", back_populates="dossier", cascade="all, delete-orphan"
    )


class DossierItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific section or evidence link within the interviewer dossier."""
    __tablename__ = "dossier_items"

    dossier_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("dossier_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_type: Mapped[str] = mapped_column(String(50), nullable=False)  # strong_area, uncertain_area, ownership, probe
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    referenced_evidence_ids: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    item_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    dossier: Mapped["DossierSnapshot"] = relationship("DossierSnapshot", back_populates="items")
