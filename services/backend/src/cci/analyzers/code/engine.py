"""Unified Static Code & Architecture Intelligence Engine."""

import os
from typing import List
from cci.analyzers.code.dependencies import (
    dependencies_to_evidence,
    extract_manifest_dependencies,
)
from cci.analyzers.code.multi_language import (
    analyze_c_cpp_source,
    analyze_go_source,
    analyze_java_source,
    analyze_typescript_javascript,
)
from cci.analyzers.code.python_analyzer import analyze_python_source
from cci.analyzers.documentation.architecture import (
    analyze_adr,
    analyze_layer_boundaries,
    analyze_openapi_spec,
    analyze_readme,
)
from cci.analyzers.repository.indexer import IndexedArtifact
from cci.domain.contracts import EvidenceInput

EXTRACTOR_VERSION = "1.0.0"


def run_code_intelligence(
    workspace_root: str,
    repo_url: str,
    commit_sha: str,
    artifacts: List[IndexedArtifact],
) -> List[EvidenceInput]:
    """Runs static code, dependency, and architecture analysis across indexed artifacts.
    
    INVARIANTS:
    1. Candidate repository code is NEVER executed.
    2. Framework presence is not converted into unearned mastery.
    3. Exact provenance is preserved on every EvidenceInput.
    """
    evidence_results: List[EvidenceInput] = []
    all_paths: List[str] = [a.relative_path for a in artifacts]

    # 1. Structural layer boundary evaluation
    boundary_evidence = analyze_layer_boundaries(all_paths, repo_url, commit_sha, EXTRACTOR_VERSION)
    evidence_results.extend(boundary_evidence)

    # 2. Per-artifact static inspection
    for artifact in artifacts:
        # Skip binary or oversized files
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

        # A. Dependency manifests
        if artifact.category == "manifests":
            deps = extract_manifest_dependencies(artifact.relative_path, content)
            manifest_evidence = dependencies_to_evidence(
                deps, repo_url, artifact.relative_path, commit_sha, EXTRACTOR_VERSION
            )
            evidence_results.extend(manifest_evidence)

        # B. Python AST inspection
        elif rel_lower.endswith(".py"):
            py_evidence = analyze_python_source(
                content, artifact.relative_path, repo_url, commit_sha, EXTRACTOR_VERSION
            )
            evidence_results.extend(py_evidence)

        # C. TypeScript / JavaScript
        elif rel_lower.endswith((".ts", ".tsx", ".js", ".jsx")):
            ts_evidence = analyze_typescript_javascript(
                content, artifact.relative_path, repo_url, commit_sha, EXTRACTOR_VERSION
            )
            evidence_results.extend(ts_evidence)

        # D. Go
        elif rel_lower.endswith(".go"):
            go_evidence = analyze_go_source(
                content, artifact.relative_path, repo_url, commit_sha, EXTRACTOR_VERSION
            )
            evidence_results.extend(go_evidence)

        # E. Java
        elif rel_lower.endswith(".java"):
            java_evidence = analyze_java_source(
                content, artifact.relative_path, repo_url, commit_sha, EXTRACTOR_VERSION
            )
            evidence_results.extend(java_evidence)

        # F. C / C++
        elif rel_lower.endswith((".c", ".cpp", ".cc", ".h", ".hpp")):
            cpp_evidence = analyze_c_cpp_source(
                content, artifact.relative_path, repo_url, commit_sha, EXTRACTOR_VERSION
            )
            evidence_results.extend(cpp_evidence)

        # G. Architecture / Documentation
        if "readme" in rel_lower:
            evidence_results.extend(
                analyze_readme(content, artifact.relative_path, repo_url, commit_sha, EXTRACTOR_VERSION)
            )
        elif "/adr/" in rel_lower or rel_lower.startswith("adr/"):
            evidence_results.extend(
                analyze_adr(content, artifact.relative_path, repo_url, commit_sha, EXTRACTOR_VERSION)
            )
        elif artifact.category == "openapi":
            evidence_results.extend(
                analyze_openapi_spec(content, artifact.relative_path, repo_url, commit_sha, EXTRACTOR_VERSION)
            )

    return evidence_results
