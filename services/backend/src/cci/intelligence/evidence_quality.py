"""Deterministic evidence-quality assessment.

CandidateX static analyzers intentionally emit bounded technical observations rather than
running untrusted candidate code. This module adds context-sensitive confidence factors
to those observations so a package declaration, a README sentence, and an implementation
construct do not all receive the same depth / verification treatment.

The output is descriptive evidence metadata, not a hiring recommendation and not a
replacement for the formal CCI scoring equations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


@dataclass(frozen=True)
class EvidenceQualityAssessment:
    """Context-sensitive confidence metadata for one static observation."""

    depth_specificity: float
    verification_level: float
    quality_band: str
    signal_families: tuple[str, ...]
    context_metrics: dict[str, int | float]
    rationale: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_DEPTH_BASE = {
    "source": 0.52,
    "tests": 0.62,
    "database": 0.60,
    "infra": 0.58,
    "openapi": 0.57,
    "ci": 0.54,
    "manifests": 0.32,
    "docs": 0.30,
    "config": 0.36,
    "repository_structure": 0.46,
    "other": 0.28,
}

_VERIFICATION_BASE = {
    "source": 0.68,
    "tests": 0.74,
    "database": 0.72,
    "infra": 0.70,
    "openapi": 0.72,
    "ci": 0.68,
    "manifests": 0.48,
    "docs": 0.40,
    "config": 0.50,
    "repository_structure": 0.50,
    "other": 0.38,
}

_SIGNAL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "api_contract",
        (
            r"\b(route|endpoint|handler|router|requestmapping|getmapping|postmapping)\b",
            r"\b(openapi|swagger|graphql|grpc)\b",
        ),
    ),
    (
        "validation_contract",
        (
            r"\b(validation|validator|schema|pydantic|zod|serializer)\b",
            r"\b(field_validator|model_validator|constraint|sanitize)\b",
        ),
    ),
    (
        "database_semantics",
        (
            r"\b(transaction|migration|foreign key|index|query|sqlalchemy|repository)\b",
            r"\b(commit|rollback|isolation|unique constraint|upsert)\b",
        ),
    ),
    (
        "concurrency_async",
        (
            r"\b(async|await|goroutine|channel|concurr|semaphore|mutex|worker pool)\b",
            r"\b(queue|celery|background task|event loop)\b",
        ),
    ),
    (
        "failure_handling",
        (
            r"\b(error handling|exception|retry|timeout|fallback|circuit breaker)\b",
            r"\btry\b|\bcatch\b|\bexcept\b|if err != nil",
        ),
    ),
    (
        "testing_quality",
        (
            r"\b(test|pytest|jest|vitest|playwright|cypress|mock|fixture|assert)\b",
            r"\b(property[- ]based|integration test|unit test|e2e)\b",
        ),
    ),
    (
        "security_control",
        (
            r"\b(auth|oauth|jwt|permission|authorization|encryption|csrf|xss|ssrf)\b",
            r"\b(rate limit|secret|hash|sanitize|security)\b",
        ),
    ),
    (
        "delivery_infrastructure",
        (
            r"\b(docker|kubernetes|terraform|helm|deployment|container|ci/cd)\b",
            r"\b(github actions|workflow|healthcheck|readiness|liveness)\b",
        ),
    ),
    (
        "observability",
        (
            r"\b(logging|logger|metric|telemetry|tracing|opentelemetry|prometheus)\b",
            r"\b(health check|structured log|span|monitoring)\b",
        ),
    ),
    (
        "architecture_boundary",
        (
            r"\b(architecture|service layer|domain|adapter|repository pattern|dependency injection)\b",
            r"\b(interface|protocol|controller|use case|boundary)\b",
        ),
    ),
    (
        "algorithmic_structure",
        (
            r"\b(graph|heap|priority queue|dynamic programming|binary search|cache)\b",
            r"\b(complexity|memoiz|traversal|sorting|hash map)\b",
        ),
    ),
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE))


def _signal_families(text: str) -> list[str]:
    observed: list[str] = []
    for family, patterns in _SIGNAL_PATTERNS:
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            observed.append(family)
    return observed


def _quality_band(depth: float, verification: float) -> str:
    combined = (depth + verification) / 2.0
    if combined >= 0.78:
        return "rich_context"
    if combined >= 0.64:
        return "substantive"
    if combined >= 0.48:
        return "moderate"
    return "narrow"


def assess_evidence_quality(
    *,
    artifact_category: str | None,
    artifact_path: str | None,
    raw_support_text: str,
    symbol_or_line: str | None = None,
    context_text: str | None = None,
) -> EvidenceQualityAssessment:
    """Assess static observation depth and verification using deterministic context.

    The function never executes source code and never fetches additional resources.
    context_text should be a bounded slice of an already-inspected immutable artifact.
    Values deliberately remain below 1.0 because static inspection is not runtime proof.
    """

    category = (artifact_category or "other").lower()
    if category not in _DEPTH_BASE:
        category = "other"

    path = artifact_path or ""
    snippet = raw_support_text or ""
    symbol = symbol_or_line or ""
    context = (context_text or "")[:65_536]
    combined = f"{path}\n{symbol}\n{snippet}\n{context}".lower()

    depth = _DEPTH_BASE[category]
    verification = _VERIFICATION_BASE[category]
    rationale: list[str] = [
        f"Artifact category '{category}' sets the deterministic baseline.",
    ]

    families = _signal_families(combined)
    if families:
        depth += min(0.18, 0.028 * len(families))
        rationale.append(
            f"Observed {len(families)} engineering signal family/families."
        )

    nonempty_lines = sum(1 for line in context.splitlines() if line.strip())
    function_like = (
        _count(r"\bdef\s+[A-Za-z_]", context)
        + _count(r"\bfunction\s+[A-Za-z_$]", context)
        + _count(r"\bfunc\s+[A-Za-z_]", context)
        + _count(r"\b(public|private|protected)\s+[\w<>, ?\[\]]+\s+[A-Za-z_]\w*\s*\(", context)
        + _count(r"=>\s*\{", context)
    )
    type_like = (
        _count(r"\bclass\s+[A-Za-z_]", context)
        + _count(r"\binterface\s+[A-Za-z_]", context)
        + _count(r"\btype\s+[A-Za-z_]\w*\s*=", context)
        + _count(r"\bstruct\s+[A-Za-z_]", context)
    )
    branch_like = (
        _count(r"\bif\b", context)
        + _count(r"\bfor\b", context)
        + _count(r"\bwhile\b", context)
        + _count(r"\bswitch\b", context)
        + _count(r"\bmatch\b", context)
        + _count(r"\btry\b", context)
    )
    imports = (
        _count(r"^\s*(?:from\s+\S+\s+import|import\s+\S+)", context)
        + _count(r"^\s*import\s+.*from\s+['\"]", context)
        + _count(r"\brequire\s*\(", context)
    )

    if nonempty_lines >= 40:
        depth += 0.025
    if nonempty_lines >= 120:
        depth += 0.025
    if function_like >= 2:
        depth += 0.04
        rationale.append("Multiple implementation units are present in the inspected context.")
    if type_like >= 1:
        depth += 0.025
    if branch_like >= 4:
        depth += 0.03
    if imports >= 3:
        depth += 0.015

    if symbol and re.search(r"\bline\s+\d+|:[0-9]+\b|\bfunction\b|\bclass\b|\bhandler\b", symbol, re.I):
        verification += 0.07
        rationale.append("Observation preserves a concrete source location or symbol.")
    elif symbol:
        verification += 0.035

    snippet_code_cues = _count(
        r"(@[A-Za-z_]|\bdef\b|\bclass\b|=>|\breturn\b|\bawait\b|\bSELECT\b|\bCREATE\s+TABLE\b|\{.+\})",
        snippet,
    )
    if snippet_code_cues:
        verification += min(0.07, 0.025 + 0.015 * snippet_code_cues)
        depth += min(0.05, 0.015 * snippet_code_cues)
        rationale.append("Support text contains implementation-level syntax rather than metadata alone.")

    if category == "docs":
        depth = min(depth, 0.58)
        verification = min(verification, 0.56)
        rationale.append("Documentation is descriptive evidence and is capped below implementation evidence.")
    elif category == "manifests":
        depth = min(depth, 0.56)
        verification = min(verification, 0.62)
        rationale.append("Dependency declarations show configured technology, not demonstrated usage.")
    elif category == "repository_structure":
        depth = min(depth, 0.66)
        verification = min(verification, 0.64)
        rationale.append("Repository structure supports architectural context but not behavior.")

    depth = round(_clamp(depth, 0.20, 0.94), 3)
    verification = round(_clamp(verification, 0.25, 0.90), 3)

    metrics: dict[str, int | float] = {
        "context_nonempty_lines": nonempty_lines,
        "function_like_units": function_like,
        "type_like_units": type_like,
        "branch_like_constructs": branch_like,
        "import_or_dependency_edges": imports,
        "signal_family_count": len(families),
    }

    return EvidenceQualityAssessment(
        depth_specificity=depth,
        verification_level=verification,
        quality_band=_quality_band(depth, verification),
        signal_families=tuple(families),
        context_metrics=metrics,
        rationale=tuple(rationale),
    )
