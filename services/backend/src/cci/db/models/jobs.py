from typing import Any

"""Job descriptions, role profiles, requirements, and weight overrides."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cci.db.base import (
    GUID,
    Base,
    JSONType,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class JobDescription(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Employer job description."""

    __tablename__ = "job_descriptions"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # CanonicalRole enum
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role_profiles: Mapped[list["RoleProfileEntity"]] = relationship(
        "RoleProfileEntity",
        back_populates="job_description",
        cascade="all, delete-orphan",
    )
    requirements: Mapped[list["RoleRequirement"]] = relationship(
        "RoleRequirement",
        back_populates="job_description",
        cascade="all, delete-orphan",
    )


class RoleProfileEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Role weights derived for a specific JD and canonical role."""

    __tablename__ = "role_profiles"

    job_description_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canonical_role: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_importances: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False
    )  # u_k values
    softmax_weights: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False
    )  # w_k values summing to 1.0
    temperature_used: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    job_description: Mapped["JobDescription"] = relationship(
        "JobDescription", back_populates="role_profiles"
    )
    overrides: Mapped[list["RoleWeightOverride"]] = relationship(
        "RoleWeightOverride",
        back_populates="role_profile",
        cascade="all, delete-orphan",
    )


class RoleRequirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Normalized requirement extracted from JD."""

    __tablename__ = "role_requirements"

    job_description_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    priority: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # RequirementPriority enum
    capability_mappings: Mapped[list[Any]] = mapped_column(
        JSONType, nullable=False
    )  # List[CapabilityKey]
    technology_mentions: Mapped[list[Any]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    mention_frequency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    semantic_specificity: Mapped[float] = mapped_column(
        Float, default=0.5, nullable=False
    )
    mapping_confidence: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )
    mapping_method: Mapped[str] = mapped_column(
        String(100), default="controlled_synonym_map", nullable=False
    )
    ontology_version: Mapped[str] = mapped_column(
        String(50), default="1.0.0", nullable=False
    )

    job_description: Mapped["JobDescription"] = relationship(
        "JobDescription", back_populates="requirements"
    )


class RoleWeightOverride(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit log for deterministic expert manual role weight adjustments."""

    __tablename__ = "role_weight_overrides"

    role_profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("role_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    original_weights: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    overridden_weights: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)

    role_profile: Mapped["RoleProfileEntity"] = relationship(
        "RoleProfileEntity", back_populates="overrides"
    )
