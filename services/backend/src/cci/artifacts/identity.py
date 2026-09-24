"""Canonical artifact identity derivation.

INVARIANTS:
1. Canonical artifact identity derives from:
   (repo + immutable revision + normalized path + content hash).
2. Multiple observations/evidence records from the same physical file point to ONE artifact node.
3. Artifact identity remains deterministic and stable within an immutable snapshot.
"""

from hashlib import sha256
from uuid import UUID, uuid5, NAMESPACE_URL


def normalize_artifact_path(path: str | None) -> str:
    """Normalizes file path across operating systems and leading/trailing separators."""
    if not path:
        return ""
    norm = path.replace("\\", "/").strip().strip("/")
    while "//" in norm:
        norm = norm.replace("//", "/")
    return norm


def compute_canonical_artifact_id(
    repo_url: str | None,
    immutable_revision: str | None,
    artifact_path: str | None,
    content_hash: str | None = None,
) -> str:
    """Derives a canonical deterministic artifact string ID for CEG graph nodes.

    Formula: sha256(repo + immutable revision + normalized path + content hash)
    """
    repo_norm = (repo_url or "").strip().lower()
    rev_norm = (immutable_revision or "").strip()
    path_norm = normalize_artifact_path(artifact_path)
    hash_norm = (content_hash or "").strip().lower()

    composite = f"{repo_norm}::{rev_norm}::{path_norm}::{hash_norm}"
    digest = sha256(composite.encode("utf-8")).hexdigest()
    return f"artifact_{digest[:24]}"


def compute_canonical_artifact_uuid(
    repo_url: str | None,
    immutable_revision: str | None,
    artifact_path: str | None,
    content_hash: str | None = None,
) -> UUID:
    """Derives a deterministic UUIDv5 for an artifact."""
    art_id_str = compute_canonical_artifact_id(
        repo_url, immutable_revision, artifact_path, content_hash
    )
    return uuid5(NAMESPACE_URL, f"urn:candidatex:artifact:{art_id_str}")
