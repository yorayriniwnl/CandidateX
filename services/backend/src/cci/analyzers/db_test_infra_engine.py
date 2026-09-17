"""Unified Operational Engine for Database, Testing, and DevOps Intelligence.

INVARIANTS:
1. Candidate code, databases, tests, and CI/CD pipelines are NEVER executed.
2. All analysis is purely static file inspection.
3. Strict provenance is recorded for every EvidenceInput.
"""

import os

from cci.analyzers.database.schema_analyzer import (
    analyze_alembic_migration,
    analyze_prisma_schema,
    analyze_sql_content,
)
from cci.analyzers.infra.devops_analyzer import (
    analyze_ci_workflow,
    analyze_docker_compose,
    analyze_dockerfile,
    analyze_kubernetes_manifest,
    analyze_terraform_hcl,
)
from cci.analyzers.repository.indexer import IndexedArtifact
from cci.analyzers.testing.test_analyzer import (
    analyze_go_test_file,
    analyze_js_ts_test_file,
    analyze_python_test_file,
)
from cci.domain.contracts import EvidenceInput

EXTRACTOR_VERSION = "1.0.0"


def run_db_test_infra_intelligence(
    workspace_root: str,
    repo_url: str,
    commit_sha: str,
    artifacts: list[IndexedArtifact],
) -> list[EvidenceInput]:
    """Runs static database, testing, and devops analysis across indexed artifacts."""
    evidence_results: list[EvidenceInput] = []

    for artifact in artifacts:
        if artifact.is_binary or artifact.is_too_large:
            continue

        abs_path = os.path.join(workspace_root, artifact.relative_path)
        if not os.path.exists(abs_path):
            continue

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue

        rel_lower = artifact.relative_path.lower().replace("\\", "/")

        # 1. Database & Migrations
        if (
            artifact.category == "database"
            or "migration" in rel_lower
            or "alembic" in rel_lower
        ):
            if rel_lower.endswith(".sql"):
                evidence_results.extend(
                    analyze_sql_content(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )
            elif rel_lower.endswith(".py"):
                evidence_results.extend(
                    analyze_alembic_migration(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )
            elif rel_lower.endswith("schema.prisma"):
                evidence_results.extend(
                    analyze_prisma_schema(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )

        # 2. Testing
        elif (
            artifact.category == "tests"
            or "/test" in rel_lower
            or rel_lower.startswith("test")
        ):
            if rel_lower.endswith(".py"):
                evidence_results.extend(
                    analyze_python_test_file(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )
            elif rel_lower.endswith((".ts", ".tsx", ".js", ".jsx")):
                evidence_results.extend(
                    analyze_js_ts_test_file(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )
            elif rel_lower.endswith(".go"):
                evidence_results.extend(
                    analyze_go_test_file(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )

        # 3. CI/CD Workflows
        elif artifact.category == "ci":
            evidence_results.extend(
                analyze_ci_workflow(
                    content,
                    artifact.relative_path,
                    repo_url,
                    commit_sha,
                    EXTRACTOR_VERSION,
                )
            )

        # 4. Infrastructure & DevOps
        elif artifact.category == "infra":
            if "dockerfile" in rel_lower:
                evidence_results.extend(
                    analyze_dockerfile(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )
            elif "compose" in rel_lower:
                evidence_results.extend(
                    analyze_docker_compose(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )
            elif (
                "kubernetes" in rel_lower
                or "/k8s/" in rel_lower
                or rel_lower.startswith("k8s/")
            ):
                evidence_results.extend(
                    analyze_kubernetes_manifest(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )
            elif rel_lower.endswith((".tf", ".tfvars")):
                evidence_results.extend(
                    analyze_terraform_hcl(
                        content,
                        artifact.relative_path,
                        repo_url,
                        commit_sha,
                        EXTRACTOR_VERSION,
                    )
                )

    return evidence_results
