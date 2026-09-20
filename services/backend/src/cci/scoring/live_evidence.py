"""Calibration helpers for evidence extracted from explicitly supplied live sources.

Live analysis can produce many observations from the same repository.  These
helpers keep a dependency declaration, a structural hint, and repeated source
snippets from receiving the same evidentiary weight as independently verified
implementation or test artifacts.
"""

from pathlib import PurePosixPath

from cci.domain.contracts import EvidenceInput


def classify_live_observation(
    observation: EvidenceInput, artifact_path: str | None = None
) -> str:
    """Return a stable evidence kind used for correlation-aware calibration."""

    path = (artifact_path or observation.artifact_path or "").lower().replace("\\", "/")
    text = observation.raw_support_text.lower()
    path_parts = set(PurePosixPath(path).parts)

    if "declared dependency" in text or "dependency" in path:
        return "dependency_declaration"
    if path == "repository_structure":
        return "structural"
    if (
        "test suite" in text
        or "test case" in text
        or "test function" in text
        or "tests" in path_parts
        or "test" in path_parts
        or "spec" in path_parts
        or "fixture" in path_parts
    ):
        return "test_artifact"
    if (
        ".github" in path_parts
        or "docker" in path
        or "kubernetes" in path
        or "terraform" in path
        or "workflow" in path
        or "ci/cd" in text
        or "infrastructure-as-code" in text
    ):
        return "infrastructure"
    if (
        path.endswith((".md", ".mdx", ".rst", ".adoc"))
        or "docs" in path_parts
        or "documented" in text
        or "architecture diagram" in text
        or "openapi specification" in text
    ):
        return "documentation"
    if "live operational" in text or path in {"security_headers", "tls_certificate", "html_dom"}:
        return "live_operation"
    return "source_usage"


_BASE_PROFILES: dict[str, tuple[float, float]] = {
    # Declarations show intent and are useful for discovery, not proof of use.
    "dependency_declaration": (0.25, 0.25),
    "documentation": (0.30, 0.35),
    "structural": (0.40, 0.40),
    # Static implementation patterns are stronger, but still cannot prove runtime use.
    "source_usage": (0.55, 0.50),
    "infrastructure": (0.60, 0.60),
    "test_artifact": (0.70, 0.65),
    "live_operation": (0.85, 0.75),
}


def live_confidence_profile(kind: str, correlation_rank: int) -> tuple[float, float]:
    """Return verification and depth factors after diminishing correlated returns."""

    verification, depth = _BASE_PROFILES.get(kind, _BASE_PROFILES["source_usage"])
    rank = max(1, correlation_rank)
    diminishing_factor = 1.0 / (1.0 + 0.35 * (rank - 1))
    return verification * diminishing_factor, depth * diminishing_factor


def estimate_declared_commit_ownership(
    candidate_commits: int,
    total_commits: int,
    identity_supplied: bool,
    is_fork: bool,
) -> tuple[float, float]:
    """Estimate authorship share and sample confidence from a bounded commit sample.

    The returned ownership score is deliberately shrunk for small samples.  A
    one-commit repository is not allowed to look equivalent to a sustained
    authorship pattern, even when every sampled commit has the candidate login.
    """

    if not identity_supplied or total_commits <= 0 or candidate_commits <= 0:
        return 0.0, 0.0

    sample_confidence = min(1.0, total_commits / (total_commits + 5.0))
    raw_ratio = min(1.0, max(0.0, candidate_commits / total_commits))
    ownership = raw_ratio * (0.5 + 0.5 * sample_confidence)
    ownership = min(0.5 if is_fork else 0.9, ownership)
    return ownership, sample_confidence
