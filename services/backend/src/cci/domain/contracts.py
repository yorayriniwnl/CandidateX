"""Shared paper-aligned Pydantic domain contracts for Candidate Capability Intelligence (CCI).

Frozen interfaces used across all analysis, scoring, extraction, and UI subsystems.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cci.domain.enums import (
    ArtifactAttributionState,
    CanonicalRole,
    CapabilityKey,
    ReliabilityState,
    RequirementPriority,
    SourceFamily,
)

# ---------------------------------------------------------------------------
# Scoring Configuration
# ---------------------------------------------------------------------------


class ScoringConfig(BaseModel):
    """Versioned scoring hyperparameters and calibration constants."""

    model_config = ConfigDict(frozen=True)

    version: str = Field(
        default="5.0.0", description="Semver identifier for scoring parameter set"
    )
    temperature: float = Field(
        default=1.0, gt=0.0, description="Softmax temperature T for role weights"
    )
    epsilon: float = Field(
        default=1e-5,
        gt=0.0,
        description="Denominator stabilizer for contradiction diagnostic D_k",
    )
    low_coverage_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Minimum coverage to emit candidate estimates; lower coverage also marks the analysis insufficient",
    )
    cluster_artifact_decay: float = Field(
        default=0.5,
        ge=0.0,
        lt=1.0,
        description="Geometric diminishing-return factor for distinct artifacts within one independent source cluster",
    )
    evidence_family_decay: float = Field(
        default=0.5,
        ge=0.0,
        lt=1.0,
        description="Geometric diminishing-return factor for distinct observations within one semantic evidence family",
    )

    # Probe priority weights: I_k = w_k * [alpha*(1-Cov_k) + beta*CIwidth_k + gamma*Conf_k]
    probe_alpha: float = Field(default=0.40, ge=0.0, description="Coverage gap weight")
    probe_beta: float = Field(
        default=0.35, ge=0.0, description="Uncertainty / CI width weight"
    )
    probe_gamma: float = Field(default=0.25, ge=0.0, description="Contradiction weight")

    # Importance parameters: u_k = eta1*m_k + eta2*p_k + eta3*ln(1+f_k) + eta4*s_k
    eta1_mandatory: float = Field(
        default=3.0, ge=0.0, description="Weight for mandatory requirements"
    )
    eta2_preferred: float = Field(
        default=1.5, ge=0.0, description="Weight for preferred requirements"
    )
    eta3_frequency: float = Field(
        default=0.8, ge=0.0, description="Weight for log-frequency of mentions"
    )
    eta4_specificity: float = Field(
        default=1.0, ge=0.0, description="Weight for semantic specificity"
    )

    # Capability-specific recency half-life lambda_k (in year^-1)
    lambda_decay: dict[CapabilityKey, float] = Field(
        default_factory=lambda: {cap: 0.25 for cap in CapabilityKey},
        description="Exponential decay factor lambda_k for recency t_e,k = exp(-lambda_k * delta_t_e)",
    )

    # Capability-specific evidence saturation threshold tau_k
    tau_saturation: dict[CapabilityKey, float] = Field(
        default_factory=lambda: {cap: 5.0 for cap in CapabilityKey},
        description="Evidence saturation capacity tau_k for cluster-aware capability coverage",
    )


# ---------------------------------------------------------------------------
# Candidate & Intake Contracts
# ---------------------------------------------------------------------------


class CandidateManifest(BaseModel):
    """Candidate evidence manifest extracted strictly from supplied materials."""

    model_config = ConfigDict(frozen=True)

    display_name: str = Field(
        ..., min_length=1, description="Candidate name as stated on CV"
    )
    email: str | None = Field(None, description="Candidate contact email")
    github_urls: list[str] = Field(
        default_factory=list, description="Supplied GitHub profiles or repos"
    )
    project_links: list[str] = Field(
        default_factory=list, description="Explicit project links from CV"
    )
    deployment_urls: list[str] = Field(
        default_factory=list, description="Live project/demo URLs from CV"
    )
    portfolio_urls: list[str] = Field(
        default_factory=list, description="Personal portfolio websites"
    )
    coding_profile_urls: list[str] = Field(
        default_factory=list, description="Coding profiles (e.g. LeetCode, Kaggle)"
    )
    credential_urls: list[str] = Field(
        default_factory=list, description="Certifications / credentials"
    )
    linkedin_urls: list[str] = Field(
        default_factory=list, description="Supplied LinkedIn profile URLs"
    )
    claimed_skills: list[str] = Field(
        default_factory=list, description="Self-reported technical skills"
    )
    project_claims: list[dict[str, Any]] = Field(
        default_factory=list, description="Structured project claims from CV"
    )
    experience_claims: list[dict[str, Any]] = Field(
        default_factory=list, description="Structured employment/experience claims"
    )
    manifest_version: str = Field(default="1.0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NormalizedRequirement(BaseModel):
    """Structured requirement produced by JD intake parser."""

    model_config = ConfigDict(frozen=True)

    requirement_id: UUID = Field(default_factory=uuid4)
    source_text: str = Field(
        ..., min_length=1, description="Original verbatim text excerpt from JD"
    )
    normalized_name: str = Field(
        ..., min_length=1, description="Standardized requirement title/skill"
    )
    priority: RequirementPriority = Field(default=RequirementPriority.MANDATORY)
    capability_mappings: list[CapabilityKey] = Field(
        ..., description="Mapped core capabilities; empty when the requirement is unresolved"
    )
    technology_mentions: list[str] = Field(
        default_factory=list, description="Specific libraries, frameworks, tools"
    )
    mention_frequency: int = Field(
        default=1, ge=1, description="Number of times mentioned in JD"
    )
    semantic_specificity: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Specificity score s_k in [0, 1]"
    )
    mapping_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in capability mapping"
    )
    mapping_method: str = Field(
        default="controlled_synonym_map",
        description="Method used: controlled_synonym_map or embedding_llm",
    )
    ontology_version: str = Field(default="1.0.0")


# ---------------------------------------------------------------------------
# Evidence & Observation Contracts
# ---------------------------------------------------------------------------


class EvidenceConfidenceFactors(BaseModel):
    """Five-factor evidence quality, gated by candidate attribution.

    c_e,k = o_e * (a_e * t_e,k * v_e * x_e * r_s(e))^(1/5)
    """

    model_config = ConfigDict(frozen=True)

    artifact_integrity: float = Field(
        ..., ge=0.0, le=1.0, description="a_e: artifact validity / parser confidence"
    )
    ownership_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="o_e: direct attribution gate; caps confidence weight at the path contribution ratio",
    )
    recency_factor: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="t_e,k: time decay factor exp(-lambda * delta_t)",
    )
    verification_level: float = Field(
        ..., ge=0.0, le=1.0, description="v_e: direct operational verification level"
    )
    depth_specificity: float = Field(
        ..., ge=0.0, le=1.0, description="x_e: technical depth / complexity level"
    )
    source_reliability: float = Field(
        ..., ge=0.0, le=1.0, description="r_s: source family posterior mean"
    )

    @property
    def evidence_quality(self) -> float:
        """Five-factor geometric mean excluding attribution, in [0, 1]."""
        product = (
            self.artifact_integrity
            * self.recency_factor
            * self.verification_level
            * self.depth_specificity
            * self.source_reliability
        )
        return float(product ** (1.0 / 5.0))

    @property
    def composite_confidence(self) -> float:
        """Attribution-gated evidence weight: o_e * evidence_quality, not a probability."""
        return float(self.ownership_score * self.evidence_quality)


class EvidenceInput(BaseModel):
    """Raw observation candidate emitted by static/operational analyzers."""

    model_config = ConfigDict(frozen=True)

    source_family: SourceFamily
    source_locator: str = Field(
        ..., description="URL, repo path, or document identifier"
    )
    immutable_revision: str = Field(
        ..., description="Commit SHA, document hash, or fetch timestamp"
    )
    artifact_path: str | None = None
    symbol_or_line: str | None = None
    target_capability: CapabilityKey
    observed_score: float = Field(
        ..., ge=0.0, le=100.0, description="Technical support rating z_e,k in [0, 100]"
    )
    is_positive_support: bool = Field(
        default=True,
        description="True for positive support P, False for negative support N",
    )
    raw_support_text: str = Field(
        ..., description="Verbatim quote, code snippet, or inspection trace"
    )
    extractor_version: str = Field(
        ..., description="Version of the analyzer producing this evidence"
    )
    evidence_family_id: str | None = Field(
        default=None,
        min_length=68,
        max_length=68,
        pattern=r"^ef[01]:[0-9a-f]{64}$",
        description="Versioned semantic family identity for correlated observations",
    )
    observation_type: str = Field(
        default="legacy_unknown",
        min_length=1,
        max_length=100,
        description="Stable analyzer modality name for this observation",
    )
    evidence_family_basis: dict[str, str] = Field(
        default_factory=dict,
        description="Semantic identity basis retained in evidence provenance",
    )
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RepositoryAssociation(BaseModel):
    """A declared link between a candidate profile and a repository, not authorship."""

    model_config = ConfigDict(frozen=True)

    repository_url: str
    candidate_identifier: str | None = None
    basis: str = Field(description="How the repository entered the selected source set")
    identity_verified: bool = Field(default=False, description="Whether the GitHub account is human-verified")
    limitations: list[str] = Field(default_factory=list)


class RepositoryContribution(BaseModel):
    """Account-matched commits in a bounded repository-wide sample."""

    model_config = ConfigDict(frozen=True)

    repository_url: str
    candidate_identifier: str | None = None
    sampled_commit_count: int = Field(..., ge=0)
    candidate_commit_count: int = Field(..., ge=0)
    candidate_commit_ratio: float = Field(..., ge=0.0, le=1.0)
    candidate_commit_shas: list[str] = Field(default_factory=list)
    is_fork: bool = False
    method: str = "recent_repository_commit_author_login"
    limitations: list[str] = Field(default_factory=list)


class ArtifactAttribution(BaseModel):
    """Path-specific Git history; does not verify the human behind a GitHub account."""

    model_config = ConfigDict(frozen=True)

    artifact_path: str | None = None
    revision_sha: str = Field(..., pattern=r"^[a-fA-F0-9]{40}$")
    state: ArtifactAttributionState
    ownership_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Share of sampled commits for this path authored by the declared GitHub account",
    )
    attribution_confidence: float = Field(..., ge=0.0, le=1.0)
    candidate_commit_count: int = Field(..., ge=0)
    sampled_path_commit_count: int = Field(..., ge=0)
    candidate_commit_shas: list[str] = Field(default_factory=list)
    basis: str = "github_path_commit_history"
    limitations: list[str] = Field(default_factory=list)


class ArtifactRecency(BaseModel):
    """Path-specific modification history kept separate from repository activity."""

    model_config = ConfigDict(frozen=True)

    state: Literal["known", "artifact_recency_unknown"]
    last_meaningful_modification_at: datetime | None = None
    last_meaningful_revision_sha: str | None = Field(
        default=None, pattern=r"^[a-fA-F0-9]{40}$"
    )
    candidate_contribution_at: datetime | None = None
    candidate_contribution_revision_sha: str | None = Field(
        default=None, pattern=r"^[a-fA-F0-9]{40}$"
    )
    repository_last_activity: datetime | None = None
    basis: str = "github_path_commit_history"
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_recency_state(self):
        if self.state == "known" and (
            self.last_meaningful_modification_at is None
            or self.last_meaningful_revision_sha is None
        ):
            raise ValueError("Known artifact recency requires a path timestamp and commit SHA")
        if self.state == "artifact_recency_unknown" and (
            self.last_meaningful_modification_at is not None
            or self.last_meaningful_revision_sha is not None
            or self.candidate_contribution_at is not None
            or self.candidate_contribution_revision_sha is not None
        ):
            raise ValueError("Unknown artifact recency cannot carry path-history timestamps")
        if (self.candidate_contribution_at is None) != (
            self.candidate_contribution_revision_sha is None
        ):
            raise ValueError("Candidate contribution time and commit SHA must be supplied together")
        return self


class EvidenceRecord(BaseModel):
    """Immutable registered evidence row with cryptographic fingerprint and confidence factors."""

    model_config = ConfigDict(frozen=True)

    evidence_id: UUID = Field(default_factory=uuid4)
    fingerprint: str = Field(
        ...,
        description="SHA256(normalized_artifact || source_locator || revision || extractor_version)",
    )
    source_family: SourceFamily
    source_locator: str
    immutable_revision: str
    artifact_id: UUID | None = None
    target_capability: CapabilityKey
    support_score: float = Field(..., ge=0.0, le=100.0, description="z_e,k in [0, 100]")
    is_positive_support: bool = True
    confidence_factors: EvidenceConfidenceFactors
    confidence: float = Field(..., ge=0.0, le=1.0, description="Computed c_e,k")
    artifact_attribution: ArtifactAttribution | None = None
    artifact_recency: ArtifactRecency | None = None
    cluster_id: str | None = Field(
        None, description="Cluster grouping for effective count / bootstrap"
    )
    evidence_family_id: str | None = Field(
        default=None,
        min_length=68,
        max_length=68,
        pattern=r"^ef[01]:[0-9a-f]{64}$",
        description="Versioned semantic family identity for correlated observations",
    )
    observation_type: str = Field(
        default="legacy_unknown",
        min_length=1,
        max_length=100,
        description="Stable analyzer modality name for this observation",
    )
    evidence_family_basis: dict[str, str] = Field(
        default_factory=dict,
        description="Semantic identity basis retained in evidence provenance",
    )
    provenance: dict[str, Any] = Field(
        default_factory=dict, description="File, line, commit, and inspection metadata"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Source Reliability & Ownership Contracts
# ---------------------------------------------------------------------------


class SourceReliabilitySnapshot(BaseModel):
    """Beta(alpha_s, beta_s) posterior state for a source family."""

    model_config = ConfigDict(frozen=True)

    source_family: SourceFamily
    alpha_prior: float = Field(..., gt=0.0)
    beta_prior: float = Field(..., gt=0.0)
    true_positive_count: int = Field(default=0, ge=0)
    false_positive_count: int = Field(default=0, ge=0)
    posterior_mean: float = Field(
        ..., ge=0.0, le=1.0, description="r_s = (TP + alpha)/(TP + FP + alpha + beta)"
    )
    state: ReliabilityState = Field(default=ReliabilityState.PRIOR)
    version: str = Field(default="1.0.0")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OwnershipAssessment(BaseModel):
    """Legacy aggregate repository-contribution snapshot; never establishes artifact authorship."""

    model_config = ConfigDict(frozen=True)

    assessment_id: UUID = Field(default_factory=uuid4)
    repository_url: str
    candidate_identifier: str
    ownership_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Legacy aggregate repository-contribution score; not artifact authorship",
    )
    feature_vector: dict[str, float] = Field(
        default_factory=dict,
        description="Features: commit_ratio, pr_ratio, blame_ratio, review_participation, etc.",
    )
    is_fork: bool = False
    is_vendor_or_generated: bool = False
    attribution_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    model_name: str = Field(default="HeuristicOwnershipEstimator")
    model_version: str = Field(default="1.0.0")
    limitations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Capability Estimation, Uncertainty & Conflict Contracts
# ---------------------------------------------------------------------------


class CapabilityEstimate(BaseModel):
    """Candidate capability score, emitted only after sufficient attributed evidence."""

    model_config = ConfigDict(frozen=True)

    capability_key: CapabilityKey
    estimate: float | None = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Candidate q_k in [0, 100], or None if attribution-gated evidence is insufficient (UNKNOWN)",
    )
    is_observed: bool = Field(
        ..., description="True if attribution-gated coverage meets the configured minimum for a candidate estimate"
    )
    effective_evidence_count: float = Field(
        ..., ge=0.0, description="n_eff,k = (sum c)^2 / sum(c^2)"
    )
    raw_evidence_count: int = Field(..., ge=0, description="Total raw evidence records")
    cluster_count: int = Field(
        default=0, ge=0, description="Distinct independent source clusters after artifact deduplication"
    )
    standard_error: float = Field(
        default=0.0, ge=0.0, description="SE_k = s_k / sqrt(max(1, n_eff,k))"
    )
    dispersion: float = Field(
        default=0.0, ge=0.0, description="Weighted evidence variance s_k"
    )
    ci_lower: float | None = Field(
        None, ge=0.0, le=100.0, description="Bootstrap 95% CI lower bound"
    )
    ci_upper: float | None = Field(
        None, ge=0.0, le=100.0, description="Bootstrap 95% CI upper bound"
    )
    coverage_k: float = Field(
        ..., ge=0.0, le=1.0,
        description="Attribution-gated coverage from unique artifacts with within-cluster diminishing returns",
    )


class CapabilityUncertainty(BaseModel):
    """Decomposition of capability uncertainty."""

    model_config = ConfigDict(frozen=True)

    capability_key: CapabilityKey
    epistemic_uncertainty: float = Field(
        ..., ge=0.0, description="Combined uncertainty metric"
    )
    ci_width: float = Field(..., ge=0.0, description="ci_upper - ci_lower")
    is_low_coverage: bool = Field(..., description="True if coverage_k < threshold")


class CapabilityConflict(BaseModel):
    """Contradiction diagnostic D_k between positive and negative evidence."""

    model_config = ConfigDict(frozen=True)

    capability_key: CapabilityKey
    positive_support_sum: float = Field(..., ge=0.0, description="P_k")
    negative_support_sum: float = Field(..., ge=0.0, description="N_k")
    contradiction_diagnostic: float = Field(
        ..., ge=-1.0, le=1.0, description="D_k = (P_k - N_k)/(P_k + N_k + epsilon)"
    )
    has_meaningful_conflict: bool = Field(default=False)
    triggering_evidence_ids: list[UUID] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Role Profile & Overall Analysis Scores
# ---------------------------------------------------------------------------


class RoleProfile(BaseModel):
    """Job-specific role weights w_k derived from JD requirements."""

    model_config = ConfigDict(frozen=True)

    canonical_role: CanonicalRole
    raw_importances: dict[CapabilityKey, float] = Field(
        ..., description="u_k = eta1*m_k + eta2*p_k + eta3*ln(1+f_k) + eta4*s_k"
    )
    softmax_weights: dict[CapabilityKey, float] = Field(
        ..., description="w_k = exp(u_k / T) / sum_j exp(u_j / T) summing to 1.0"
    )
    is_overridden: bool = Field(
        default=False, description="True if manual expert weights applied"
    )
    override_audit: dict[str, Any] | None = None

    @field_validator("softmax_weights")
    @classmethod
    def validate_weights_sum(
        cls, v: dict[CapabilityKey, float]
    ) -> dict[CapabilityKey, float]:
        total = sum(v.values())
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Role weights w_k must sum to 1.0; got {total}")
        return v


class AnalysisScore(BaseModel):
    """Overall Candidate Capability Intelligence assessment."""

    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    role: CanonicalRole
    rci: float | None = Field(
        None,
        ge=0.0,
        le=100.0,
        description="RCI = 100 * sum_{k in obs}(w_k * q_k) / sum_{k in obs}(w_k)",
    )
    coverage: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Coverage(C,J) = sum_k w_k * min(1, sum_e c_e,k / tau_k)",
    )
    is_insufficient_evidence: bool = Field(
        ..., description="True if Coverage < low_coverage_threshold"
    )
    observed_capabilities_count: int = Field(..., ge=0, le=12)
    scoring_config_version: str


# ---------------------------------------------------------------------------
# Interview Probes & Questions
# ---------------------------------------------------------------------------


class ProbePriority(BaseModel):
    """Prioritized technical interview target I_k."""

    model_config = ConfigDict(frozen=True)

    capability_key: CapabilityKey
    rank: int = Field(..., ge=1, le=12)
    priority_score: float = Field(
        ..., description="I_k = w_k * [alpha*(1-Cov_k) + beta*CIwidth_k + gamma*Conf_k]"
    )
    role_weight: float = Field(..., ge=0.0, le=1.0, description="w_k")
    coverage_gap_term: float = Field(..., ge=0.0, le=1.0, description="1 - Cov_k")
    uncertainty_term: float = Field(..., ge=0.0, description="CIwidth_k")
    contradiction_term: float = Field(
        ..., ge=0.0, le=1.0, description="Conf_k derived from D_k"
    )


class InterviewQuestion(BaseModel):
    """Evidence-grounded probe question for the technical interviewer."""

    model_config = ConfigDict(frozen=True)

    question_id: UUID = Field(default_factory=uuid4)
    target_capability: CapabilityKey
    question_text: str = Field(..., min_length=1)
    rationale: str = Field(
        ..., description="Why this probe was prioritized based on evidence or gaps"
    )
    verification_guidance: str = Field(
        ..., description="What technical interviewer should listen/look for"
    )
    grounding_evidence_ids: list[UUID] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Dossier Snapshot
# ---------------------------------------------------------------------------


class Dossier(BaseModel):
    """Complete technical dossier snapshot presented to the interviewer."""

    model_config = ConfigDict(frozen=True)

    dossier_id: UUID = Field(default_factory=uuid4)
    candidate_id: UUID
    analysis_run_id: UUID
    role: CanonicalRole
    rci: float | None = Field(None, ge=0.0, le=100.0)
    coverage: float = Field(..., ge=0.0, le=1.0)
    is_insufficient_evidence: bool
    capability_estimates: dict[CapabilityKey, CapabilityEstimate]
    capability_conflicts: dict[CapabilityKey, CapabilityConflict]
    role_requirements: list[NormalizedRequirement]
    ownership_assessments: list[OwnershipAssessment]
    repository_associations: list[RepositoryAssociation] = Field(default_factory=list)
    repository_contributions: list[RepositoryContribution] = Field(default_factory=list)
    claims_corroboration: list[dict[str, Any]]
    interview_probes: list[ProbePriority]
    interview_questions: list[InterviewQuestion]
    evidence_records: list[EvidenceRecord] = Field(default_factory=list)
    evidence_mode: str = "provided"
    scenario: str | None = None
    role_weights: dict[CapabilityKey, float] = Field(default_factory=dict)
    override_history: list[dict[str, Any]] = Field(default_factory=list)
    system_limitations: list[str] = Field(
        default_factory=lambda: [
            "CCI is employer decision support only; does not make autonomous hire/reject decisions.",
            "Candidate repository code is never executed; insights are static and operational.",
            "Missing evidence represents UNKNOWN capability, not low capability.",
            "Scoring is strictly isolated from protected demographic attributes.",
        ]
    )
    versions: dict[str, str] = Field(
        default_factory=lambda: {
            "platform_version": "0.1.0",
            "scoring_config_version": "5.0.0",
            "ontology_version": "1.0.0",
        }
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
