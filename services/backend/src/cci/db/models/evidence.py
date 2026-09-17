"""Immutable evidence rows, capability links, and clustering entities."""

import uuid
from typing import List, Optional
from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cci.db.base import Base, GUID, ImmutableModelMixin, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class Evidence(Base, UUIDPrimaryKeyMixin, ImmutableModelMixin, TimestampMixin):
    """Immutable evidence row with 6-factor confidence parameters and provenance.
    
    Protected against SQL-level updates via ImmutableModelMixin.
    """
    __tablename__ = "evidence"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    source_family: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_locator: Mapped[str] = mapped_column(String(1024), nullable=False)
    immutable_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    target_capability: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # CapabilityKey enum
    support_score: Mapped[float] = mapped_column(Float, nullable=False)  # z_e,k in [0, 100]
    is_positive_support: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Six-factor confidence decomposition: c_e,k = (a * o * t * v * x * r)^(1/6)
    factor_artifact_integrity: Mapped[float] = mapped_column(Float, nullable=False)  # a_e
    factor_ownership_score: Mapped[float] = mapped_column(Float, nullable=False)     # o_e
    factor_recency: Mapped[float] = mapped_column(Float, nullable=False)             # t_e,k
    factor_verification_level: Mapped[float] = mapped_column(Float, nullable=False)  # v_e
    factor_depth_specificity: Mapped[float] = mapped_column(Float, nullable=False)   # x_e
    factor_source_reliability: Mapped[float] = mapped_column(Float, nullable=False)  # r_s
    computed_confidence: Mapped[float] = mapped_column(Float, nullable=False)        # c_e,k

    cluster_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    provenance: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    analyzer_version: Mapped[str] = mapped_column(String(50), nullable=False)

    capability_links: Mapped[List["EvidenceCapabilityLink"]] = relationship(
        "EvidenceCapabilityLink", back_populates="evidence", cascade="all, delete-orphan"
    )


class EvidenceCapabilityLink(Base, UUIDPrimaryKeyMixin, ImmutableModelMixin, TimestampMixin):
    """Many-to-many link between evidence and evaluated technical capability."""
    __tablename__ = "evidence_capability_links"

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    capability_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    effective_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    evidence: Mapped["Evidence"] = relationship("Evidence", back_populates="capability_links")


class EvidenceCluster(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Grouping of correlated evidence (e.g. within single repository/project) for effective count calculation."""
    __tablename__ = "evidence_clusters"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cluster_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    cluster_type: Mapped[str] = mapped_column(String(50), nullable=False)  # project, repository, document
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sum_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
