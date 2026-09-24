from typing import Any

"""Audit events, model versioning, correction requests, and deletion tracking."""

import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, synonym

from cci.db.base import (
    GUID,
    Base,
    ImmutableModelMixin,
    JSONType,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

DEFAULT_SYSTEM_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class AnalyzerVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registered version of static code or metadata analyzers."""

    __tablename__ = "analyzer_versions"

    analyzer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    capabilities_covered: Mapped[list[Any]] = mapped_column(JSONType, nullable=False)
    git_commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ModelVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registered version of ML or statistical heuristic models (e.g. HeuristicOwnershipEstimator)."""

    __tablename__ = "model_versions"

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    hyperparameters: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )
    training_data_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditEvent(Base, UUIDPrimaryKeyMixin, ImmutableModelMixin, TimestampMixin):
    """Tamper-evident append-only audit trail of decisions, overrides, and security events (Fix 30)."""

    __tablename__ = "audit_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        default=DEFAULT_SYSTEM_ORG_ID,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(
        BigInteger, default=1, nullable=False, index=True
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id = synonym("actor_id")

    action: Mapped[str] = mapped_column(
        String(100), nullable=False, default="unknown", index=True
    )
    event_type = synonym("action")

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), nullable=True, index=True
    )
    request_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )

    previous_event_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    details: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)


class CorrectionRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Candidate or recruiter correction request to remove/modify incorrectly parsed data."""

    __tablename__ = "correction_requests"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    target_field: Mapped[str] = mapped_column(String(100), nullable=False)
    original_value: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    corrected_value: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, applied, rejected
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DeletionEvent(Base, UUIDPrimaryKeyMixin, ImmutableModelMixin, TimestampMixin):
    """GDPR / right-to-be-forgotten deletion tombstone."""

    __tablename__ = "deletion_events"

    candidate_id_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    deleted_tables: Mapped[list[Any]] = mapped_column(JSONType, nullable=False)
    reason: Mapped[str] = mapped_column(
        String(255), default="candidate_request", nullable=False
    )
