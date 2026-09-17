"""Audit events, model versioning, correction requests, and deletion tracking."""

import uuid
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cci.db.base import Base, GUID, ImmutableModelMixin, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class AnalyzerVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registered version of static code or metadata analyzers."""
    __tablename__ = "analyzer_versions"

    analyzer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    capabilities_covered: Mapped[list] = mapped_column(JSONType, nullable=False)
    git_commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ModelVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registered version of ML or statistical heuristic models (e.g. HeuristicOwnershipEstimator)."""
    __tablename__ = "model_versions"

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    hyperparameters: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    training_data_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditEvent(Base, UUIDPrimaryKeyMixin, ImmutableModelMixin, TimestampMixin):
    """Immutable system audit trail of decisions, overrides, and security events."""
    __tablename__ = "audit_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)


class CorrectionRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Candidate or recruiter correction request to remove/modify incorrectly parsed data."""
    __tablename__ = "correction_requests"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    target_field: Mapped[str] = mapped_column(String(100), nullable=False)
    original_value: Mapped[dict] = mapped_column(JSONType, nullable=False)
    corrected_value: Mapped[dict] = mapped_column(JSONType, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, applied, rejected
    decision_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DeletionEvent(Base, UUIDPrimaryKeyMixin, ImmutableModelMixin, TimestampMixin):
    """GDPR / right-to-be-forgotten deletion tombstone."""
    __tablename__ = "deletion_events"

    candidate_id_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    deleted_tables: Mapped[list] = mapped_column(JSONType, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="candidate_request", nullable=False)
