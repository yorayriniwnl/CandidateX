"""Candidate ownership attribution estimation and 6-factor confidence composition.

FORMAL PAPER MODEL:
c_e,k = (a_e * o_e * t_e,k * v_e * x_e * r_s(e))^(1/6)

INVARIANTS:
1. Candidate ownership attribution is explicitly estimated and capped for forks and vendor code.
2. Zero candidate commits on a fork prevents unearned code ownership attribution.
3. Provenance and feature vectors are fully preserved on every OwnershipAssessment.
"""

from uuid import uuid4

from cci.domain.contracts import EvidenceConfidenceFactors, OwnershipAssessment

MODEL_NAME = "HeuristicOwnershipEstimator"
MODEL_VERSION = "1.0.0"


def estimate_repository_ownership(
    repository_url: str,
    candidate_identifier: str,
    candidate_commits: int = 0,
    total_commits: int = 0,
    candidate_lines: int = 0,
    total_lines: int = 0,
    is_fork: bool = False,
    is_owner: bool = True,
    is_vendor_or_generated: bool = False,
    _candidate_pr_count: int = 0,
    _total_pr_count: int = 0,
) -> OwnershipAssessment:
    """Estimates candidate ownership attribution o_e in [0, 1] with feature vector and audit trail."""
    features: dict[str, float] = {
        "candidate_commits": float(candidate_commits),
        "total_commits": float(total_commits),
        "candidate_lines": float(candidate_lines),
        "total_lines": float(total_lines),
        "is_fork": 1.0 if is_fork else 0.0,
        "is_owner": 1.0 if is_owner else 0.0,
        "is_vendor": 1.0 if is_vendor_or_generated else 0.0,
    }
    limitations: list[str] = []

    # 1. Vendor or auto-generated codebase
    if is_vendor_or_generated:
        score = 0.05
        conf = 0.95
        limitations.append(
            "Vendor library or auto-generated code detected; minimal candidate ownership attributed."
        )
        return OwnershipAssessment(
            assessment_id=uuid4(),
            repository_url=repository_url,
            candidate_identifier=candidate_identifier,
            ownership_score=score,
            feature_vector=features,
            is_fork=is_fork,
            is_vendor_or_generated=True,
            attribution_confidence=conf,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            limitations=limitations,
        )

    # 2. Forked repository
    if is_fork:
        if candidate_commits == 0:
            score = 0.10
            conf = 0.90
            limitations.append(
                "Repository is a fork with zero candidate commits; attribution capped at 0.10."
            )
        else:
            commit_ratio = candidate_commits / max(1, total_commits)
            score = min(0.70, max(0.15, commit_ratio * 0.85))
            conf = 0.85
            limitations.append(
                "Repository is a fork; maximum ownership attribution capped at 0.70."
            )

        return OwnershipAssessment(
            assessment_id=uuid4(),
            repository_url=repository_url,
            candidate_identifier=candidate_identifier,
            ownership_score=score,
            feature_vector=features,
            is_fork=True,
            is_vendor_or_generated=False,
            attribution_confidence=conf,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            limitations=limitations,
        )

    # 3. Solo project / Primary author (original repository)
    if total_commits <= candidate_commits or total_commits == 0:
        score = 0.95
        conf = 0.92
        return OwnershipAssessment(
            assessment_id=uuid4(),
            repository_url=repository_url,
            candidate_identifier=candidate_identifier,
            ownership_score=score,
            feature_vector=features,
            is_fork=False,
            is_vendor_or_generated=False,
            attribution_confidence=conf,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            limitations=limitations,
        )

    # 4. Collaborative multi-contributor project
    commit_ratio = candidate_commits / max(1, total_commits)
    line_ratio = (
        (candidate_lines / max(1, total_lines)) if total_lines > 0 else commit_ratio
    )
    features["commit_ratio"] = commit_ratio
    features["line_ratio"] = line_ratio

    weighted_score = 0.60 * commit_ratio + 0.40 * line_ratio
    if is_owner:
        weighted_score += 0.05

    score = max(0.15, min(0.95, weighted_score))
    conf = 0.88
    limitations.append(
        "Multi-contributor repository; ownership weighted across commit and line proportions."
    )

    return OwnershipAssessment(
        assessment_id=uuid4(),
        repository_url=repository_url,
        candidate_identifier=candidate_identifier,
        ownership_score=score,
        feature_vector=features,
        is_fork=False,
        is_vendor_or_generated=False,
        attribution_confidence=conf,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        limitations=limitations,
    )


def assemble_confidence_factors(
    artifact_integrity: float = 1.0,
    ownership_score: float = 0.90,
    recency_factor: float = 1.0,
    verification_level: float = 1.0,
    depth_specificity: float = 0.80,
    source_reliability: float = 0.833,
) -> EvidenceConfidenceFactors:
    """Builds and validates the 6 multiplicative confidence factors for c_e,k."""
    # Ensure all factors are within valid [0, 1] range
    factors = EvidenceConfidenceFactors(
        artifact_integrity=max(0.0, min(1.0, artifact_integrity)),
        ownership_score=max(0.0, min(1.0, ownership_score)),
        recency_factor=max(0.0, min(1.0, recency_factor)),
        verification_level=max(0.0, min(1.0, verification_level)),
        depth_specificity=max(0.0, min(1.0, depth_specificity)),
        source_reliability=max(0.0, min(1.0, source_reliability)),
    )
    return factors
