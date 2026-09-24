"""Shared paper-aligned Pydantic domain contracts for Candidate Capability Intelligence (CCI).

Frozen interfaces used across all analysis, scoring, extraction, and UI subsystems.
"""

from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_serializer,
    model_validator,
)

from cci.domain.enums import (
    ArtifactAttributionState,
    CanonicalRole,
    CapabilityKey,
    ClaimStatus,
    EvidenceState,
    ReliabilityState,
    RequirementPriority,
    SourceFamily,
)
from cci.domain.coverage_policy import (
    DEFAULT_COVERAGE_SUFFICIENCY_THRESHOLD,
    classify_evidence_state,
)
from cci.versioning import (
    SCORING_MODEL_VERSION,
    VersionFamilies,
    build_reproducibility_metadata,
    get_canonical_version_dict,
)
from cci.domain.evidence_families import normalize_source_cluster
from cci.domain.signal_rules import SIGNAL_RULE_VERSIONS


def _reject_conflicting_score_names(data: Any, legacy_name: str) -> Any:
    if isinstance(data, dict):
        canonical = data.get("technical_signal_strength")
        legacy = data.get(legacy_name)
        if canonical is not None and legacy is not None and canonical != legacy:
            raise ValueError(
                f"technical_signal_strength and {legacy_name} must match"
            )
    return data


# ---------------------------------------------------------------------------
# Scoring Configuration
# ---------------------------------------------------------------------------


class ScoringConfig(BaseModel):
    """Versioned scoring hyperparameters and calibration constants."""

    model_config = ConfigDict(frozen=True)

    version: str = Field(
        default=SCORING_MODEL_VERSION, description="Semver identifier for scoring parameter set"
    )
    temperature: float = Field(
        default=1.0,
        ge=0.5,
        description="Softmax temperature T for role weights; values below 0.5 are rejected",
    )
    epsilon: float = Field(
        default=1e-5,
        gt=0.0,
        description="Denominator stabilizer for contradiction diagnostic D_k",
    )
    low_coverage_threshold: float = Field(
        default=DEFAULT_COVERAGE_SUFFICIENCY_THRESHOLD,
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

    # Bounded JD adjustments are added to role-prior logits before a capped softmax.
    jd_max_logit_adjustment: float = Field(
        default=1.5,
        ge=0.0,
        le=2.0,
        description="Maximum JD logit adjustment for any one capability",
    )
    jd_adjustment_saturation: float = Field(
        default=2.0,
        gt=0.0,
        description="Support level at which bounded JD adjustment begins to saturate",
    )
    jd_requirement_group_decay: float = Field(
        default=0.5,
        ge=0.0,
        lt=1.0,
        description="Geometric marginal contribution for distinct JD requirement groups mapped to one capability",
    )
    min_role_weight: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Lower bound for each capability's normalized role weight",
    )
    max_role_weight: float = Field(
        default=0.40,
        gt=0.0,
        le=1.0,
        description="Upper bound for each capability's normalized role weight",
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

    @model_validator(mode="after")
    def validate_role_weight_bounds(self):
        capability_count = len(CapabilityKey)
        if self.min_role_weight > self.max_role_weight:
            raise ValueError("Minimum role weight cannot exceed maximum role weight")
        if self.min_role_weight * capability_count > 1.0:
            raise ValueError("Minimum role weight bounds cannot sum above 1.0")
        if self.max_role_weight * capability_count < 1.0:
            raise ValueError("Maximum role weight bounds cannot sum below 1.0")
        return self


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


class Claim(BaseModel):
    """Canonical candidate claim representation unifying resume ledger, corroboration, and graph nodes."""

    model_config = ConfigDict(frozen=True)

    claim_id: UUID | str = Field(default_factory=uuid4)
    analysis_run_id: UUID | None = None
    candidate_id: UUID | None = None
    claim_type: str = Field(default="skill", min_length=1, description="Categorization: skill, project, experience, education, metric, etc.")
    original_text: str = Field(..., min_length=1, description="Verbatim raw claim text from source document")
    normalized_subject: str = Field(default="", description="Canonicalized entity or topic of the claim")
    structured_value: Any | None = Field(default=None, description="Parsed metric, credential, or structured representation")
    unit: str | None = Field(default=None, description="Unit for quantified metric claims")
    source: SourceFamily | str = Field(default=SourceFamily.RESUME, description="Source family originating this claim")
    section: str | None = Field(default=None, description="Document section, e.g. experience, education, skills")
    source_location: str | None = Field(default=None, description="Location within source: line, bullet index, page, URL")
    source_document_hash: str | None = Field(default=None, description="SHA-256 hash of the originating document")
    status: ClaimStatus = Field(default=ClaimStatus.SELF_REPORTED, description="Current evaluation status in the 10-state taxonomy")
    verification_state: str = Field(default="unverified", description="Operational verification details")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duplicate_count: int = 0
    occurrences: list[dict[str, Any]] = Field(default_factory=list)

    # Corroboration grounding and graph linkage
    target_capability: CapabilityKey | None = None
    technology_keywords: list[str] = Field(default_factory=list)
    claim_reference: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    grounding_evidence_ids: list[UUID] = Field(default_factory=list)
    citation_urls: list[str] = Field(default_factory=list)
    explanation: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def claim_text(self) -> str:
        """Compatibility accessor for legacy claim consumers."""
        return self.original_text

    @model_validator(mode="after")
    def validate_corroboration_evidence(self):
        if self.status in {
            ClaimStatus.SUPPORTED,
            ClaimStatus.STRONGLY_SUPPORTED,
            ClaimStatus.PARTIALLY_SUPPORTED,
            ClaimStatus.CONTRADICTED,
        }:
            if not self.grounding_evidence_ids:
                raise ValueError(
                    f"Corroborated or contradicted claims ({self.status.value}) must reference grounding evidence IDs"
                )
        return self

    def to_dict(self) -> dict[str, Any]:
        """Compatibility dictionary format matching ClaimCorroborationResult."""
        return {
            "claim_id": str(self.claim_id),
            "claim_text": self.original_text,
            "target_capability": self.target_capability.value if self.target_capability else None,
            "status": self.status.value,
            "confidence": self.confidence,
            "grounding_evidence_ids": [str(eid) for eid in self.grounding_evidence_ids],
            "citation_urls": self.citation_urls,
            "explanation": self.explanation,
            "claim_type": self.claim_type,
            "original_text": self.original_text,
            "normalized_subject": self.normalized_subject,
            "structured_value": self.structured_value,
            "unit": self.unit,
            "source": self.source.value if hasattr(self.source, "value") else str(self.source),
            "section": self.section,
            "source_location": self.source_location,
            "source_document_hash": self.source_document_hash,
            "verification_state": self.verification_state,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_corroboration(cls, result: Any, **overrides: Any) -> "Claim":
        """Construct a Claim from a ClaimCorroborationResult or similar mapping."""
        if isinstance(result, Claim):
            return result
        data = {
            "claim_id": getattr(result, "claim_id", uuid4()),
            "original_text": getattr(result, "claim_text", "") or getattr(result, "original_text", ""),
            "target_capability": getattr(result, "target_capability", None),
            "status": getattr(result, "status", ClaimStatus.SELF_REPORTED),
            "confidence": getattr(result, "confidence", 0.0),
            "grounding_evidence_ids": getattr(result, "grounding_evidence_ids", []),
            "citation_urls": getattr(result, "citation_urls", []),
            "explanation": getattr(result, "explanation", ""),
            **overrides,
        }
        return cls(**data)

    @classmethod
    def create_deterministic(
        cls,
        original_text: str,
        claim_type: str = "skill",
        source_document_hash: str | None = None,
        structured_value: Any | None = None,
        normalized_subject: str = "",
        section: str | None = None,
        source_location: str | None = None,
        **overrides: Any,
    ) -> "Claim":
        """Instantiate a Claim with a deterministic UUID based on document hash and semantics."""
        from cci.claims.identity import generate_deterministic_claim_uuid

        semantics = {"normalized_subject": normalized_subject, "structured_value": structured_value} if (normalized_subject or structured_value is not None) else None
        cid = generate_deterministic_claim_uuid(
            source_document_hash=source_document_hash,
            claim_type=claim_type,
            text=original_text,
            structured_semantics=semantics,
        )
        data = {
            "claim_id": cid,
            "original_text": original_text,
            "claim_type": claim_type,
            "source_document_hash": source_document_hash,
            "structured_value": structured_value,
            "normalized_subject": normalized_subject,
            "section": section,
            "source_location": source_location,
            **overrides,
        }
        return cls(**data)


class AcademicRecord(BaseModel):
    """Canonical representation of an educational qualification and institution history."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    institution: str | None = None
    degree: str | None = None
    branch: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    cgpa: float | None = None
    scale: float | None = None
    percentage: float | None = None
    coursework: list[str] = Field(default_factory=list)
    honors: list[str] = Field(default_factory=list)
    source_lines: list[str] = Field(default_factory=list)
    verification_state: str = Field(
        default="unverified",
        description="Attendance verification state; remains unverified without independent evidence",
    )
    status: str = Field(default="self_reported", description="Evaluation status")
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Structured fields are parsed from the resume declaration only.",
            "No institution, transcript, grade, or enrollment verification is implied.",
        ]
    )

    @property
    def raw_claim(self) -> str:
        return " — ".join(self.source_lines) if self.source_lines else ""

    @property
    def degree_text(self) -> str | None:
        return self.degree

    @property
    def years(self) -> list[str]:
        res = []
        if self.start_year is not None:
            res.append(str(self.start_year))
        if self.end_year is not None:
            res.append(str(self.end_year))
        return res

    @property
    def claimed_cgpa(self) -> dict[str, Any] | None:
        if self.cgpa is not None:
            return {"value": self.cgpa, "scale": self.scale}
        return None

    @property
    def claimed_percentage(self) -> float | None:
        return self.percentage

    @property
    def evidence_sources(self) -> list[str]:
        return []

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "raw_claim": self.raw_claim,
            "status": self.status,
            "institution": self.institution,
            "degree": self.degree,
            "degree_text": self.degree,
            "branch": self.branch,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "years": self.years,
            "cgpa": self.cgpa,
            "scale": self.scale,
            "claimed_cgpa": self.claimed_cgpa,
            "percentage": self.percentage,
            "claimed_percentage": self.percentage,
            "coursework": self.coursework,
            "honors": self.honors,
            "source_lines": self.source_lines,
            "verification_state": self.verification_state,
            "evidence_sources": [],
            "limitations": list(self.limitations),
        }


# ---------------------------------------------------------------------------
# Project Entity Contracts (Fix 40)
# ---------------------------------------------------------------------------


class ProjectTraceLink(BaseModel):
    """Traceability link connecting claim -> source -> artifact -> observation."""

    model_config = ConfigDict(frozen=True)

    link_type: str = Field(
        default="trace_hop",
        description="Type of hop: claim_to_source, source_to_artifact, artifact_to_observation",
    )
    claim_id: str | None = None
    source_url: str | None = None
    artifact_path: str | None = None
    evidence_id: str | None = None
    observation_type: str | None = None
    summary: str = ""


class ProjectEntity(BaseModel):
    """First-class traceable representation of a candidate-claimed project (Fix 40)."""

    model_config = ConfigDict(frozen=True)

    project_id: str = Field(description="Deterministic identity for this project entity")
    name: str = Field(description="Project name / title as claimed on resume")
    resume_claim: dict[str, Any] = Field(
        default_factory=dict,
        description="Resume claim details (title, description, source location)",
    )
    repository: dict[str, Any] | None = Field(
        default=None,
        description="Matched repository information (URL, name, is_fork, branch/commit)",
    )
    deployment: dict[str, Any] | None = Field(
        default=None,
        description="Matched live deployment information (URL, status, reachable, protocol)",
    )
    documentation: dict[str, Any] = Field(
        default_factory=dict,
        description="Documentation traces (README presence, architecture docs, license)",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Consolidated technologies claimed or detected",
    )
    db: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Database technologies, schemas, ORMs, and migration files detected",
    )
    backend: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Backend frameworks, APIs, routing files detected",
    )
    frontend: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Frontend frameworks, components, UI templates detected",
    )
    tests: dict[str, Any] = Field(
        default_factory=dict,
        description="Testing framework, test file paths, test assertions count",
    )
    infrastructure: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Infrastructure and DevOps configs (Dockerfile, CI/CD, k8s, docker-compose)",
    )
    candidate_attribution: dict[str, Any] = Field(
        default_factory=dict,
        description="Attribution metrics (ownership score, commit count, author login match)",
    )
    recency: dict[str, Any] = Field(
        default_factory=dict,
        description="Modification timestamps, last active date, recency factor",
    )
    credentials_or_publication_relationship: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Associated credentials, papers, arXiv preprints, or research links",
    )
    quantitative_claims: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Quantified metrics extracted from project claim (users, latency, accuracy, etc.)",
    )
    contradictions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Contradictions, negative evidence, or framework absences related to this project",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Conservative caveats and boundaries on project evaluation",
    )
    trace: list[ProjectTraceLink] = Field(
        default_factory=list,
        description="Traceable links from claim to source to artifact to observation",
    )

    @property
    def title(self) -> str:
        return self.name

    @property
    def description(self) -> str:
        return self.resume_claim.get("description", "")

    @property
    def source_urls(self) -> list[str]:
        urls = []
        if self.repository and self.repository.get("url"):
            urls.append(self.repository["url"])
        if self.deployment and self.deployment.get("url"):
            urls.append(self.deployment["url"])
        return urls

    @property
    def status(self) -> str:
        if self.repository or self.deployment:
            return "linked_sources"
        return "declaration_only"

    @property
    def explanation(self) -> str:
        if self.repository or self.deployment:
            return "Links connect this project to acquisition receipts; impact, performance and contribution claims still require separate verification."
        return "Project is declared on resume without verified repository or deployment sources."

    def to_dict(self) -> dict[str, Any]:
        data = self.model_dump()
        data["title"] = self.title
        data["description"] = self.description
        data["source_urls"] = self.source_urls
        data["status"] = self.status
        data["explanation"] = self.explanation
        return data


# ---------------------------------------------------------------------------
# Quantified Claim Contracts (Fix 41)
# ---------------------------------------------------------------------------


class QuantifiedClaim(BaseModel):
    """Structured representation of an extracted quantitative or numeric claim (Fix 41)."""

    model_config = ConfigDict(frozen=True)

    claim_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Deterministic or unique ID for this quantified claim",
    )
    metric: str = Field(
        ...,
        description="Standardized metric name: accuracy, users, latency, uptime, deployed_projects, tokens, tests, optimization",
    )
    value: Any = Field(
        ...,
        description="Numeric or scaled value (e.g. 95.0, 10000, '10k', '5B', 500, 40)",
    )
    unit: str = Field(
        ...,
        description="Measurement unit: %, users, ms, s, tokens, tests, projects, multiplier",
    )
    context: str = Field(
        ...,
        description="Source sentence or snippet containing the claim",
    )
    source: str = Field(
        default="resume",
        description="Origin of the claim: resume, project_claim, experience, education, portfolio",
    )
    source_location: str | None = Field(
        default=None,
        description="Section and line location of the claim",
    )
    verification_status: str = Field(
        default="unverified",
        description="Status: unverified, supported_by_artifacts, portfolio_mention_only, contradicted, unsupported",
    )
    supporting_artifacts: list[str] = Field(
        default_factory=list,
        description="Paths or URLs to independent technical supporting artifacts (benchmarks, test files, configs)",
    )
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Do not verify a metric merely because the same number appears on a portfolio.",
            "Quantitative claims require independent or technical supporting artifacts (e.g. benchmarks, test files, configs).",
            "Resume metrics are self-reported candidate declarations.",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ---------------------------------------------------------------------------
# Chronology & Timeline Contracts (Fix 42)
# ---------------------------------------------------------------------------


class TimelineEvent(BaseModel):
    """A chronologically positioned candidate event across education, work, repos, deployments, or credentials."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this timeline event",
    )
    category: str = Field(
        ...,
        description="Category: education, work_experience, internship, repository_activity, deployment, credential, publication",
    )
    title: str = Field(..., description="Short descriptive label for the event")
    start_date: str | None = Field(default=None, description="Start date (YYYY, YYYY-MM, or ISO 8601)")
    end_date: str | None = Field(default=None, description="End date (YYYY, YYYY-MM, ISO 8601, or 'present')")
    is_ongoing: bool = Field(default=False, description="True if marked present or ongoing")
    source: str = Field(default="resume", description="Originating document or system")
    source_url: str | None = Field(default=None, description="URL of source if applicable")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional context or parsed tokens")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class TimelineInconsistency(BaseModel):
    """An observed chronological conflict or anomaly (Fix 42)."""

    model_config = ConfigDict(frozen=True)

    inconsistency_id: str = Field(default_factory=lambda: str(uuid4()))
    label: str = Field(
        default="timeline inconsistency requiring review",
        description="Canonical label; never infers dishonesty",
    )
    inconsistency_type: str = Field(
        ...,
        description="Type: inverted_date_range, future_date, expired_before_issue, anachronism, overlapping_commit_predate",
    )
    event_ids: list[str] = Field(default_factory=list, description="IDs of related timeline events")
    explanation: str = Field(
        ...,
        description="Neutral, objective description of the observed date discrepancy",
    )
    severity: str = Field(default="requires_review")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class CandidateTimeline(BaseModel):
    """Full candidate chronology with ordered events and detected inconsistencies (Fix 42)."""

    model_config = ConfigDict(frozen=True)

    events: list[TimelineEvent] = Field(default_factory=list)
    inconsistencies: list[TimelineInconsistency] = Field(default_factory=list)
    earliest_date: str | None = None
    latest_date: str | None = None
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Dates are extracted from candidate declarations and public timestamps.",
            "Inconsistencies are labeled as timeline inconsistency requiring review; do not infer dishonesty.",
            "Timezones, approximate years, and concurrent part-time activities can produce apparent overlaps without intent.",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


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


class NegativeEvidenceScanScope(BaseModel):
    """Pinned boundary within which a contradiction observation was made."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scope_kind: Literal["artifact", "repository", "deployment", "synthetic"]
    repository_scope: str | None = None
    pinned_revision: str | None = None
    artifact_paths: list[str] = Field(default_factory=list)
    category: str | None = None
    scope_version: str | None = None
    deployment_url: str | None = None
    verifier_identity: str | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope_kind in {"artifact", "repository"}:
            if not all(
                (self.repository_scope, self.pinned_revision, self.category, self.scope_version)
            ):
                raise ValueError(
                    "Repository negative evidence scope requires repository, revision, category, and scope version"
                )
            if self.scope_kind == "artifact" and not self.artifact_paths:
                raise ValueError("Artifact negative evidence scope requires artifact paths")
        elif self.scope_kind == "deployment":
            if not (self.deployment_url and self.verifier_identity):
                raise ValueError(
                    "Deployment negative evidence scope requires URL and verifier identity"
                )
        return self


class NegativeEvidenceDetails(BaseModel):
    """Explicit expectation, observation, and completeness of a contradiction."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_reference: str = Field(pattern=r"^cr1:[0-9a-f]{64}$")
    candidate_type: Literal[
        "candidatex.contradiction.coverage_below_claim",
        "candidatex.contradiction.framework_usage_absent",
        "candidatex.contradiction.deployment_project_mismatch",
        "candidatex.contradiction.performance_claim_mismatch",
    ]
    expected_observation: str = Field(min_length=1)
    actual_observation: str = Field(min_length=1)
    scan_scope: NegativeEvidenceScanScope
    required_scan_completeness: float = Field(ge=0.0, le=1.0)
    observed_scan_completeness: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(min_length=1)


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
    technical_signal_strength: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        validation_alias=AliasChoices("technical_signal_strength", "observed_score"),
        description="Heuristic technical signal strength in [0, 100]",
    )
    signal_rule_id: str | None = None
    signal_rule_version: str | None = None
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
    negative_evidence_details: NegativeEvidenceDetails | None = None
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

    @model_validator(mode="before")
    @classmethod
    def reject_conflicting_score_names(cls, data: Any) -> Any:
        return _reject_conflicting_score_names(data, "observed_score")

    @model_validator(mode="after")
    def validate_signal_rule(self):
        if self.signal_rule_id is None and self.signal_rule_version is None:
            if not self.is_positive_support:
                raise ValueError(
                    "Production negative evidence requires a registered signal rule"
                )
        elif self.signal_rule_id is None or self.signal_rule_version is None:
            raise ValueError("Signal rule ID and version must be supplied together")
        elif SIGNAL_RULE_VERSIONS.get(self.signal_rule_id) != self.signal_rule_version:
            raise ValueError("Signal rule ID and version must match the registry")
        if self.is_positive_support:
            if self.negative_evidence_details is not None:
                raise ValueError(
                    "Positive evidence cannot carry negative evidence details"
                )
        elif self.negative_evidence_details is None:
            raise ValueError("Production negative evidence requires negative evidence details")
        elif self.negative_evidence_details.scan_scope.scope_kind == "synthetic":
            raise ValueError(
                "Production negative evidence cannot use synthetic scan scope"
            )
        elif self.signal_rule_id != self.negative_evidence_details.candidate_type:
            raise ValueError("Negative evidence signal rule must match candidate type")
        return self

    @computed_field
    @property
    def negative_evidence_qualification(self) -> Literal["qualified"] | None:
        return "qualified" if not self.is_positive_support else None

    @model_serializer(mode="wrap")
    def serialize_evidence_input(self, handler):
        data = handler(self)
        if self.is_positive_support:
            # Existing positive observation hashes include the serialized input.
            data.pop("negative_evidence_details", None)
            data.pop("negative_evidence_qualification", None)
        return data

    @property
    def observed_score(self) -> float:
        """Compatibility accessor for pre-Fix-11 analyzer consumers."""
        return self.technical_signal_strength


class RepositoryAssociation(BaseModel):
    """A declared link between a candidate profile and a repository, not authorship."""

    model_config = ConfigDict(frozen=True)

    repository_url: str
    candidate_identifier: str | None = None
    basis: str = Field(description="How the repository entered the selected source set")
    identity_verified: bool = Field(default=False, description="Whether the GitHub account is human-verified")
    selection_reason: str | None = Field(default=None, description="Role-aware prioritization rationale for repository selection")
    priority_score: float | None = Field(default=None, description="Numeric score from role-aware repository prioritization")
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
    technical_signal_strength: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        validation_alias=AliasChoices("technical_signal_strength", "support_score"),
        description="Heuristic technical signal strength in [0, 100]",
    )
    is_positive_support: bool = True
    negative_evidence_details: NegativeEvidenceDetails | None = None
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

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_provenance(cls, data: Any) -> Any:
        data = _reject_conflicting_score_names(data, "support_score")
        if isinstance(data, dict):
            # Invariant: LLM output is NEVER an evidence source (Fix 44)
            src_fam = str(data.get("source_family", "")).lower()
            src_loc = str(data.get("source_locator", "")).lower()
            if src_fam in ("llm", "ai", "model", "gpt", "claude", "gemini") or any(
                src_loc.startswith(p) for p in ("llm:", "model:", "ai:", "gpt:", "claude:")
            ):
                raise ValueError("LLM output is NEVER an evidence source.")

            provenance = data.get("provenance")
            if provenance is None:
                provenance = {}
            if isinstance(provenance, dict) and not (
                provenance.get("signal_rule_id")
                and provenance.get("signal_rule_version")
            ):
                data = {
                    **data,
                    "provenance": {
                        **provenance,
                        "signal_rule_id": "legacy_unknown",
                        "signal_rule_version": "legacy_unknown",
                    },
                }
        return data

    @model_validator(mode="after")
    def validate_negative_evidence(self):
        details = self.negative_evidence_details
        if self.is_positive_support:
            if details is not None:
                raise ValueError(
                    "Positive evidence cannot carry negative evidence details"
                )
            return self
        if details is None:
            return self
        synthetic = self.provenance.get("synthetic") is True
        if details.scan_scope.scope_kind == "synthetic" and not synthetic:
            raise ValueError("Synthetic negative evidence requires synthetic provenance")
        rule_id = self.provenance.get("signal_rule_id")
        rule_version = self.provenance.get("signal_rule_version")
        if (
            synthetic
            and details.scan_scope.scope_kind == "synthetic"
            and rule_id == "legacy_unknown"
        ):
            return self
        if (
            rule_id != details.candidate_type
            or SIGNAL_RULE_VERSIONS.get(rule_id) != rule_version
        ):
            raise ValueError(
                "Qualified negative evidence requires a matching registered signal rule"
            )
        return self

    @computed_field
    @property
    def negative_evidence_qualification(
        self,
    ) -> Literal["qualified", "legacy_unqualified"] | None:
        if self.is_positive_support:
            return None
        return (
            "qualified"
            if self.negative_evidence_details is not None
            else "legacy_unqualified"
        )

    @computed_field(json_schema_extra={"deprecated": True})
    @property
    def support_score(self) -> float:
        """Deprecated compatibility value for stored rows and API clients."""
        return self.technical_signal_strength

    @property
    def capability(self) -> CapabilityKey:
        """Alias for target_capability."""
        return self.target_capability

    @property
    def candidate_id(self) -> UUID | None:
        """Convenience accessor for candidate_id in provenance."""
        cid = self.provenance.get("candidate_id")
        if isinstance(cid, str):
            try:
                return UUID(cid)
            except ValueError:
                return None
        return cid if isinstance(cid, UUID) else None

    @property
    def rule_id(self) -> str | None:
        """Convenience accessor for rule_id in provenance."""
        return self.provenance.get("signal_rule_id") or self.provenance.get("rule_id")

    @property
    def rule_strength(self) -> float:
        """Convenience accessor for normalized rule strength in [0.0, 1.0]."""
        val = self.provenance.get("rule_strength")
        if val is not None:
            return float(val)
        return float(self.technical_signal_strength / 100.0)

    @property
    def context(self) -> dict[str, Any]:
        """Convenience accessor for provenance context."""
        return self.provenance


# ---------------------------------------------------------------------------
# Source Reliability & Ownership Contracts
# ---------------------------------------------------------------------------


class SourceReliabilitySnapshot(BaseModel):
    """Beta(alpha_s, beta_s) belief state for a source family.

    Formal paper model: r_s = (TP + alpha_s) / (TP + FP + alpha_s + beta_s).
    Priors represent expert-selected baselines unless explicitly updated from
    real-world empirical outcome truth.
    """

    model_config = ConfigDict(frozen=True)

    source_family: SourceFamily
    alpha_prior: float = Field(..., gt=0.0)
    beta_prior: float = Field(..., gt=0.0)
    true_positive_count: int = Field(default=0, ge=0)
    false_positive_count: int = Field(default=0, ge=0)
    posterior_mean: float = Field(
        ..., ge=0.0, le=1.0, description="r_s = (TP + alpha)/(TP + FP + alpha + beta)"
    )
    state: ReliabilityState = Field(default=ReliabilityState.EXPERT_PRIOR)
    version: str = Field(default="1.0.0")
    rationale: str = Field(
        default="Expert-selected baseline prior; uncalibrated against real outcome data.",
        description="Explicit rationale explaining the choice of prior parameters.",
    )
    is_empirically_updated: bool = Field(
        default=False,
        description="True ONLY if updated from external measured real-world truth.",
    )
    empirical_sample_size: int = Field(
        default=0,
        ge=0,
        description="Number of real-world outcome cases used if empirically calibrated.",
    )
    calibration_provenance: str | None = Field(
        default=None,
        description="Provenance reference or dataset identifier when empirically updated.",
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def prior_parameters(self) -> dict[str, float]:
        """Convenience accessor for Beta prior parameters."""
        return {"alpha": self.alpha_prior, "beta": self.beta_prior}

    @property
    def empirically_updated(self) -> bool:
        """Alias for is_empirically_updated."""
        return self.is_empirically_updated

    @property
    def is_expert_prior(self) -> bool:
        """True if in un-updated expert prior state."""
        return self.state == ReliabilityState.EXPERT_PRIOR and not self.is_empirically_updated


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
        ..., description="Canonical role-prior logits plus bounded, diminishing JD adjustments"
    )
    softmax_weights: dict[CapabilityKey, float] = Field(
        ..., description="Normalized role weights; automatically generated profiles apply configured minimum and maximum bounds"
    )
    temperature_used: float = Field(
        default=1.0,
        ge=0.5,
        description="Softmax temperature used to generate this role profile",
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
        description="Deprecated compatibility field for the observed-only capability index",
        json_schema_extra={"deprecated": True},
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
    coverage_sufficiency_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="The active ScoringConfig.low_coverage_threshold for this analysis",
    )

    @computed_field
    @property
    def evidence_state(self) -> EvidenceState:
        return classify_evidence_state(
            self.coverage,
            sufficiency_threshold=self.coverage_sufficiency_threshold,
        )


class ObservedIndexContext(BaseModel):
    """Context needed to interpret an observed-only capability index."""

    model_config = ConfigDict(frozen=True)

    metric_label: Literal["Observed Capability Index"] = "Observed Capability Index"
    basis: Literal["Based only on observed evidence."] = (
        "Based only on observed evidence."
    )
    role_weighted_evidence_coverage: float = Field(..., ge=0.0, le=1.0)
    observed_role_dimensions: int = Field(..., ge=0, le=12)
    total_role_dimensions: int = Field(default=12, ge=1, le=12)
    coverage_sufficiency_threshold: float = Field(..., ge=0.0, le=1.0)
    is_insufficient_evidence: bool
    evidence_state: EvidenceState
    standalone_presentation_allowed: bool
    unique_independent_source_cluster_count: int | None = Field(default=None, ge=0)
    independent_source_cluster_counts_by_capability: dict[
        CapabilityKey, int
    ] = Field(default_factory=dict)
    mean_path_attribution_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0
    )
    path_attribution_sample_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_observed_index_context(self):
        if (
            self.evidence_state == EvidenceState.INSUFFICIENT
        ) != self.is_insufficient_evidence:
            raise ValueError("Evidence state and sufficiency flag must agree")
        if self.evidence_state == EvidenceState.UNKNOWN:
            raise ValueError("Observed index context requires measured coverage")
        if self.is_insufficient_evidence and self.standalone_presentation_allowed:
            raise ValueError(
                "Standalone presentation is not allowed when evidence is insufficient"
            )
        if (self.mean_path_attribution_confidence is None) != (
            self.path_attribution_sample_count == 0
        ):
            raise ValueError(
                "Path attribution mean and sample count must be available together"
            )
        return self


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


def _build_observed_index_context(
    *,
    coverage: float,
    coverage_sufficiency_threshold: float,
    index_available: bool,
    capability_estimates: dict[CapabilityKey, CapabilityEstimate],
    evidence_records: list[EvidenceRecord],
) -> ObservedIndexContext:
    evidence_state = classify_evidence_state(
        coverage,
        sufficiency_threshold=coverage_sufficiency_threshold,
    )
    effective_insufficient = evidence_state == EvidenceState.INSUFFICIENT
    observed_capabilities = {
        capability
        for capability, estimate in capability_estimates.items()
        if estimate.is_observed and estimate.estimate is not None
    }

    cluster_counts = {
        capability: capability_estimates[capability].cluster_count
        if capability in capability_estimates
        else 0
        for capability in CapabilityKey
    }
    cluster_keys = set()
    for record in evidence_records:
        if (
            record.target_capability not in observed_capabilities
            or record.confidence <= 0.0
        ):
            continue
        cluster_id = (record.cluster_id or record.source_locator).strip()
        if cluster_id:
            cluster_keys.add(
                normalize_source_cluster(record.source_family, cluster_id)
            )

    attribution_by_path: dict[tuple[str, str], tuple[float, str, float]] = {}
    for record in evidence_records:
        attribution = record.artifact_attribution
        source_locator = record.source_locator.strip()
        if (
            record.target_capability not in observed_capabilities
            or attribution is None
            or not attribution.artifact_path
        ):
            continue
        source_identity = source_locator or (record.cluster_id or "").strip()
        if not source_identity:
            continue
        normalized_path = PurePosixPath(
            attribution.artifact_path.replace("\\", "/")
        ).as_posix()
        if normalized_path in {"", "."}:
            continue
        source_cluster_key = normalize_source_cluster(
            record.source_family, source_identity
        )
        path_key = (source_cluster_key, normalized_path)
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        captured_at = created_at.astimezone(timezone.utc).timestamp()
        captured_key = (
            captured_at,
            attribution.revision_sha,
            attribution.attribution_confidence,
        )
        previous = attribution_by_path.get(path_key)
        if previous is None or captured_key[:2] > previous[:2]:
            attribution_by_path[path_key] = captured_key

    attribution_values = [value[2] for value in attribution_by_path.values()]
    return ObservedIndexContext(
        role_weighted_evidence_coverage=coverage,
        observed_role_dimensions=len(observed_capabilities),
        total_role_dimensions=len(CapabilityKey),
        coverage_sufficiency_threshold=coverage_sufficiency_threshold,
        is_insufficient_evidence=effective_insufficient,
        evidence_state=evidence_state,
        standalone_presentation_allowed=(
            index_available and not effective_insufficient
        ),
        unique_independent_source_cluster_count=len(cluster_keys) or None,
        independent_source_cluster_counts_by_capability=cluster_counts,
        mean_path_attribution_confidence=(
            sum(attribution_values) / len(attribution_values)
            if attribution_values
            else None
        ),
        path_attribution_sample_count=len(attribution_values),
    )


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
    rci: float | None = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Deprecated compatibility field; use observed_capability_index and its context",
        json_schema_extra={"deprecated": True},
    )
    coverage: float = Field(..., ge=0.0, le=1.0)
    coverage_sufficiency_threshold: float = Field(
        default=DEFAULT_COVERAGE_SUFFICIENCY_THRESHOLD, ge=0.0, le=1.0
    )
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
    project_entities: list[ProjectEntity] = Field(default_factory=list)
    quantified_claims: list[QuantifiedClaim] = Field(default_factory=list)
    timeline: CandidateTimeline | None = None
    source_discovery_tree: dict[str, Any] | None = None
    source_inventory: list[dict[str, Any]] = Field(default_factory=list)
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
        default_factory=get_canonical_version_dict,
        description="Version families guaranteeing historical dossier reproducibility",
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field(description="Explicit version families guaranteeing reproducibility")
    @property
    def version_families(self) -> VersionFamilies:
        return VersionFamilies.from_dossier_versions(self.versions)

    @computed_field(description="Audit and reproducibility metadata")
    @property
    def metadata(self) -> dict[str, Any]:
        return build_reproducibility_metadata(self)

    @computed_field(description="Observed-only score over capabilities with sufficient evidence")
    @property
    def observed_capability_index(self) -> float | None:
        return self.rci

    @computed_field
    @property
    def evidence_state(self) -> EvidenceState:
        return classify_evidence_state(
            self.coverage,
            sufficiency_threshold=self.coverage_sufficiency_threshold,
        )

    @computed_field
    @property
    def observed_index_context(self) -> ObservedIndexContext:
        return _build_observed_index_context(
            coverage=self.coverage,
            coverage_sufficiency_threshold=self.coverage_sufficiency_threshold,
            index_available=self.rci is not None,
            capability_estimates=self.capability_estimates,
            evidence_records=self.evidence_records,
        )
