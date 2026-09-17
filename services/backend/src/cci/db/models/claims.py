"""Candidate self-claims, corroboration links, and requirement evidence associations."""

import uuid
from typing import List, Optional
from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cci.db.base import Base, GUID, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class Claim(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Verbatim or structured claim extracted from candidate CV or manifest."""
    __tablename__ = "claims"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)  # skill, project, experience, metric
    corroboration_status: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)  # ClaimStatus enum
    positive_evidence_count: Mapped[int] = mapped_column(default=0, nullable=False)
    contradictory_evidence_count: Mapped[int] = mapped_column(default=0, nullable=False)
    claim_metadata: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)

    evidence_links: Mapped[List["ClaimEvidenceLink"]] = relationship(
        "ClaimEvidenceLink", back_populates="claim", cascade="all, delete-orphan"
    )


class ClaimEvidenceLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Link between candidate self-claim and corroborating/contradictory evidence."""
    __tablename__ = "claim_evidence_links"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_corroborating: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alignment_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    claim: Mapped["Claim"] = relationship("Claim", back_populates="evidence_links")


class RequirementEvidenceLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Link proving how JD requirement is satisfied/contradicted by candidate evidence."""
    __tablename__ = "requirement_evidence_links"

    requirement_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("role_requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_supportive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
