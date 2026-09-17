"""Repository artifact indexer categorizing files and computing cryptographic fingerprints."""

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from cci.domain.enums import ScanDepth
from cci.security.repository_workspace import SafeRepositoryWorkspace

# Path/filename matching patterns for technical artifact categories
CATEGORY_RULES = [
    (
        "manifests",
        re.compile(
            r"(^|/)(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|requirements\.txt|pyproject\.toml|setup\.py|setup\.cfg|Pipfile|go\.mod|go\.sum|pom\.xml|build\.gradle|Cargo\.toml|composer\.json|Gemfile)$",
            re.IGNORECASE,
        ),
    ),
    (
        "ci",
        re.compile(
            r"(^|/)(\.github/workflows/.*|\.gitlab-ci\.yml|Jenkinsfile|\.circleci/.*|\.travis\.yml|azure-pipelines\.yml)$",
            re.IGNORECASE,
        ),
    ),
    (
        "database",
        re.compile(
            r"(^|/)(migrations?/.*|alembic/.*|prisma/schema\.prisma|\.sql$)",
            re.IGNORECASE,
        ),
    ),
    (
        "infra",
        re.compile(
            r"(^|/)(Dockerfile.*|docker-compose.*\.ya?ml|compose\.ya?ml|.*\.tf|.*\.tfvars|kubernetes/.*|k8s/.*|helm/.*)$",
            re.IGNORECASE,
        ),
    ),
    (
        "openapi",
        re.compile(
            r"(^|/)(openapi\.(json|ya?ml)|swagger\.(json|ya?ml))$", re.IGNORECASE
        ),
    ),
    (
        "tests",
        re.compile(
            r"(^|/)(tests?/.*|__tests__/.*|.*[._-](test|spec)\.[a-zA-Z0-9]+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "docs",
        re.compile(
            r"(^|/)(README(\.[a-zA-Z0-9]+)?|CONTRIBUTING.*|ADR.*|CHANGELOG.*|docs?/.*\.md)$",
            re.IGNORECASE,
        ),
    ),
    (
        "config",
        re.compile(
            r"(^|/)(tsconfig\.json|\.eslintrc.*|babel\.config.*|vitest\.config.*|pytest\.ini|\.env\.example)$",
            re.IGNORECASE,
        ),
    ),
]

SOURCE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".scala",
    ".kt",
    ".swift",
    ".sh",
    ".bash",
    ".sql",
}


@dataclass(frozen=True)
class IndexedArtifact:
    """Indexed artifact metadata preserving exact immutable revision and content hash."""

    artifact_id: UUID
    relative_path: str
    category: (
        str  # source, manifests, tests, ci, database, infra, docs, openapi, config
    )
    byte_size: int
    content_sha256: str
    is_binary: bool
    is_too_large: bool


@dataclass(frozen=True)
class RepositorySnapshotMetadata:
    """Point-in-time immutable acquisition snapshot of a repository."""

    snapshot_id: UUID
    repo_url: str
    default_branch: str
    commit_sha: str
    scan_depth: ScanDepth
    fetched_at: datetime
    snapshot_fingerprint: str  # SHA256 of combined artifact hashes
    total_artifacts: int
    artifacts_by_category: dict[str, int]


def categorize_file(rel_path: str) -> str:
    """Categorizes a relative file path into its primary technical artifact category."""
    norm_path = rel_path.replace("\\", "/")

    for cat_name, pattern in CATEGORY_RULES:
        if pattern.search(norm_path):
            return cat_name

    ext = os.path.splitext(norm_path)[1].lower()
    if ext in SOURCE_EXTENSIONS:
        return "source"

    return "other"


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def index_repository_artifacts(
    workspace: SafeRepositoryWorkspace,
    repo_url: str,
    commit_sha: str,
    default_branch: str = "main",
    scan_depth: ScanDepth = ScanDepth.DEEP,
) -> tuple[RepositorySnapshotMetadata, list[IndexedArtifact]]:
    """Traverses workspace and produces immutable artifact index and snapshot metadata.

    INVARIANT: Never infers technical capability or executes candidate code. Only acquires facts.
    """
    inspected_files = workspace.scan_files()
    indexed_artifacts: list[IndexedArtifact] = []
    category_counts: dict[str, int] = {}
    artifact_hashes: list[str] = []

    for file_info in inspected_files:
        cat = categorize_file(file_info.relative_path)
        category_counts[cat] = category_counts.get(cat, 0) + 1

        # Calculate SHA256
        content_hash = compute_file_sha256(file_info.absolute_path)
        artifact_hashes.append(content_hash)

        indexed_artifacts.append(
            IndexedArtifact(
                artifact_id=uuid4(),
                relative_path=file_info.relative_path,
                category=cat,
                byte_size=file_info.byte_size,
                content_sha256=content_hash,
                is_binary=file_info.is_binary,
                is_too_large=file_info.is_too_large,
            )
        )

    # Sort hashes deterministically for snapshot fingerprint
    artifact_hashes.sort()
    composite_payload = (
        f"{repo_url}::{commit_sha}::{'|'.join(artifact_hashes)}".encode()
    )
    snapshot_fp = hashlib.sha256(composite_payload).hexdigest()

    metadata = RepositorySnapshotMetadata(
        snapshot_id=uuid4(),
        repo_url=repo_url,
        default_branch=default_branch,
        commit_sha=commit_sha,
        scan_depth=scan_depth,
        fetched_at=datetime.now(timezone.utc),
        snapshot_fingerprint=snapshot_fp,
        total_artifacts=len(indexed_artifacts),
        artifacts_by_category=category_counts,
    )

    return metadata, indexed_artifacts
