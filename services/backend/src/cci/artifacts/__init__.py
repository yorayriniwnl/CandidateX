"""Artifact identity and indexing package."""

from cci.artifacts.identity import (
    compute_canonical_artifact_id,
    compute_canonical_artifact_uuid,
    normalize_artifact_path,
)

__all__ = [
    "compute_canonical_artifact_id",
    "compute_canonical_artifact_uuid",
    "normalize_artifact_path",
]
