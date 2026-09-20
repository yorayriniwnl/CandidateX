from typing import Any

"""Candidate intake, digital identity, and project entities."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cci.db.base import (
    GUID,
    Base,
    JSONType,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Candidate(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Core candidate entity."""

    __tablename__ = "candidates"

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    manifest_data: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    identities: Mapped[list["Identity"]] = relationship(
        "Identity", back_populates="candidate", cascade="all, delete-orphan"
    )
    documents: Mapped[list["CandidateDocument"]] = relationship(
        "CandidateDocument", back_populates="candidate", cascade="all, delete-orphan"
    )
    sources: Mapped[list["CandidateSource"]] = relationship(
        "CandidateSource", back_populates="candidate", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="candidate", cascade="all, delete-orphan"
    )


class Identity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Candidate external identity account (GitHub, LinkedIn, Portfolio, etc.)."""

    __tablename__ = "identities"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # github, linkedin, website, leetcode
    identifier: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # username, URL, or handle
    profile_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="identities"
    )
    links: Mapped[list["IdentityLink"]] = relationship(
        "IdentityLink", back_populates="identity", cascade="all, delete-orphan"
    )


class IdentityLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Deterministic relationship link proving identity association from candidate-supplied evidence."""

    __tablename__ = "identity_links"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("candidate_documents.id", ondelete="SET NULL"), nullable=True
    )
    extraction_method: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., embedded_hyperlink, visible_url
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    link_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )

    identity: Mapped["Identity"] = relationship("Identity", back_populates="links")


class CandidateDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Uploaded or supplied candidate document (CV, resume, cover letter)."""

    __tablename__ = "candidate_documents"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # resume_pdf, resume_docx
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    parsed_content: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )

    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="documents"
    )


class CandidateSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """External evidence source discovered strictly through candidate-supplied manifest."""

    __tablename__ = "candidate_sources"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_family: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # resume, github, deployment, etc.
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    state: Mapped[str] = mapped_column(
        String(50), default="observed", nullable=False
    )  # observed, unavailable, etc.
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="sources")


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Project claimed by candidate or identified in repository/portfolio."""

    __tablename__ = "projects"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cluster_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    candidate: Mapped["Candidate"] = relationship(
        "Candidate", back_populates="projects"
    )
