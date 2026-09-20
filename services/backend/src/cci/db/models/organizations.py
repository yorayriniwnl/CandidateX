from typing import Any

"""Organization and User entities for multi-tenant access control."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cci.db.base import GUID, Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Multi-tenant organization boundary."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )

    users: Mapped[list["User"]] = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account associated with an organization."""

    __tablename__ = "users"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="interviewer", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="users"
    )
