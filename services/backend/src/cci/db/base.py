"""SQLAlchemy 2.0 Base declarative class, mixins, and immutability handlers."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from sqlalchemy.types import CHAR, JSON, TypeDecorator


class GUID(TypeDecorator[Any]):
    """Platform-independent GUID/UUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class JSONType(TypeDecorator[Any]):
    """Platform-independent JSON type using JSONB on Postgres and JSON on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())


class Base(DeclarativeBase):
    """Base declarative class for all CCI entities."""


class TimestampMixin:
    """Standard timestamp tracking mixin."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Standard UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class TenantMixin:
    """Multi-tenancy organization scoping."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class ImmutableModelMixin:
    """Marker mixin for entities whose rows must never be mutated once written."""

    __is_immutable__ = True


@event.listens_for(Base, "before_update", propagate=True)
def guard_immutable_entities(_mapper: Any, _connection: Any, target: Any) -> None:
    """Enforces database-layer immutability for marked models."""
    if getattr(target, "__is_immutable__", False):
        raise ValueError(
            f"Immutable entity '{target.__class__.__name__}' (id={getattr(target, 'id', 'unknown')}) "
            "cannot be modified after creation."
        )
