"""Source snapshots, repositories, and immutable code artifacts."""

import uuid
from typing import List, Optional
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cci.db.base import Base, GUID, ImmutableModelMixin, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class SourceSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Point-in-time acquisition snapshot of an external candidate evidence source."""
    __tablename__ = "source_snapshots"

    candidate_source_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("candidate_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scan_depth: Mapped[str] = mapped_column(String(20), default="light", nullable=False)  # deep or light
    commit_sha_or_etag: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    status: Mapped[str] = mapped_column(String(50), default="observed", nullable=False)
    snapshot_metadata: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)


class Repository(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """GitHub repository associated with candidate manifest."""
    __tablename__ = "repositories"

    candidate_source_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("candidate_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repo_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    primary_language: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scan_depth: Mapped[str] = mapped_column(String(20), default="light", nullable=False)

    contributors: Mapped[List["RepositoryContributor"]] = relationship(
        "RepositoryContributor", back_populates="repository", cascade="all, delete-orphan"
    )
    repository_artifacts: Mapped[List["RepositoryArtifact"]] = relationship(
        "RepositoryArtifact", back_populates="repository", cascade="all, delete-orphan"
    )


class RepositoryContributor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Contributor statistics and blame attribution in repository."""
    __tablename__ = "repository_contributors"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    login: Mapped[str] = mapped_column(String(255), nullable=False)
    commits_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    additions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_candidate_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="contributors")


class Artifact(Base, UUIDPrimaryKeyMixin, ImmutableModelMixin, TimestampMixin):
    """Immutable technical artifact indexed from source."""
    __tablename__ = "artifacts"

    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_category: Mapped[str] = mapped_column(String(50), nullable=False)  # source, manifest, test, ci, db, infra
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_extension: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_metadata: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)


class RepositoryArtifact(Base, UUIDPrimaryKeyMixin, ImmutableModelMixin, TimestampMixin):
    """Association linking repository to indexed artifact."""
    __tablename__ = "repository_artifacts"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="repository_artifacts")
