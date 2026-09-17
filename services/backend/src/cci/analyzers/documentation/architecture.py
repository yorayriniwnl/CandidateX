"""Architecture and documentation analyzer evaluating READMEs, ADRs, OpenAPI, and layer boundaries."""

import json
import re
from typing import List, Set
import yaml

from cci.domain.contracts import EvidenceInput
from cci.domain.enums import CapabilityKey, SourceFamily


def analyze_readme(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> List[EvidenceInput]:
    """Analyzes README documentation for setup instructions, API docs, and diagrams-as-code."""
    evidence: List[EvidenceInput] = []

    # 1. Setup / Getting Started documentation
    setup_match = re.search(r"^#{1,3}\s+(getting\s+started|installation|setup|quickstart|prerequisites)", content, re.IGNORECASE | re.MULTILINE)
    if setup_match:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path} (Setup Section)",
                target_capability=CapabilityKey.DOCUMENTATION_COMMUNICATION,
                observed_score=78.0,
                is_positive_support=True,
                raw_support_text=f"Explicit environment setup / installation documentation found in {file_path}",
                extractor_version=extractor_version,
            )
        )

    # 2. Diagrams as code (Mermaid / PlantUML) or architecture diagrams
    has_mermaid = "```mermaid" in content.lower()
    has_plantuml = "@startuml" in content.lower()
    has_arch_diagram = re.search(r"!\[.*(architecture|diagram|design|flow).*\]\(.*\)", content, re.IGNORECASE)

    if has_mermaid or has_plantuml or has_arch_diagram:
        diag_type = "Mermaid" if has_mermaid else ("PlantUML" if has_plantuml else "Architecture Diagram Image")
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path} ({diag_type})",
                target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                observed_score=85.0,
                is_positive_support=True,
                raw_support_text=f"Visual architecture diagram ({diag_type}) documented in {file_path}",
                extractor_version=extractor_version,
            )
        )

    return evidence


def analyze_adr(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> List[EvidenceInput]:
    """Analyzes Architecture Decision Records (ADRs)."""
    evidence: List[EvidenceInput] = []
    
    # Check for standard ADR structure: Context, Decision, Consequences
    has_context = bool(re.search(r"^#{1,3}\s+context", content, re.IGNORECASE | re.MULTILINE))
    has_decision = bool(re.search(r"^#{1,3}\s+decision", content, re.IGNORECASE | re.MULTILINE))
    has_consequences = bool(re.search(r"^#{1,3}\s+consequences?", content, re.IGNORECASE | re.MULTILINE))

    if has_context and has_decision:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=file_path,
                target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                observed_score=90.0,
                is_positive_support=True,
                raw_support_text=f"Structured Architecture Decision Record (ADR) adhering to standard decision framework in {file_path}",
                extractor_version=extractor_version,
            )
        )

    return evidence


def analyze_openapi_spec(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> List[EvidenceInput]:
    """Analyzes OpenAPI/Swagger specifications for API documentation rigor."""
    evidence: List[EvidenceInput] = []
    
    try:
        if file_path.endswith((".yaml", ".yml")):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
            
        if isinstance(data, dict) and ("openapi" in data or "swagger" in data):
            paths = data.get("paths", {})
            path_count = len(paths) if isinstance(paths, dict) else 0

            evidence.append(
                EvidenceInput(
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"{file_path} ({path_count} endpoints)",
                    target_capability=CapabilityKey.DOCUMENTATION_COMMUNICATION,
                    observed_score=85.0,
                    is_positive_support=True,
                    raw_support_text=f"Formal OpenAPI specification defining {path_count} API routes in {file_path}",
                    extractor_version=extractor_version,
                )
            )
    except Exception:
        pass

    return evidence


def analyze_layer_boundaries(
    all_relative_paths: List[str],
    repo_url: str,
    commit_sha: str,
    extractor_version: str = "1.0.0",
) -> List[EvidenceInput]:
    """Evaluates modularity and clean architectural layer separation in directory structure."""
    evidence: List[EvidenceInput] = []

    detected_layers: Set[str] = set()
    for path in all_relative_paths:
        parts = path.replace("\\", "/").lower().split("/")
        for part in parts:
            if part in ("domain", "services", "adapters", "repositories", "controllers", "models", "api"):
                detected_layers.add(part)

    # If repository demonstrates at least 3 distinct architectural layers
    if len(detected_layers) >= 3:
        evidence.append(
            EvidenceInput(
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path="repository_structure",
                symbol_or_line="Layer Boundaries",
                target_capability=CapabilityKey.SOFTWARE_ARCHITECTURE,
                observed_score=82.0,
                is_positive_support=True,
                raw_support_text=f"Distinct layered architectural boundaries identified: {', '.join(sorted(detected_layers))}",
                extractor_version=extractor_version,
            )
        )

    return evidence
