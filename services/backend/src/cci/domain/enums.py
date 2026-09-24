"""Paper-aligned canonical enumerations for Candidate Capability Intelligence (CCI)."""

from enum import Enum


class CanonicalRole(str, Enum):
    """The six canonical engineering roles defined by the formal CCI framework."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    FULLSTACK = "fullstack"
    ML_ENGINEER = "ml_engineer"
    DEVOPS_CLOUD = "devops_cloud"
    DATA_ENGINEER = "data_engineer"


class CapabilityKey(str, Enum):
    """The twelve core technical capabilities evaluated across all roles."""

    BACKEND_ENGINEERING = "backend_engineering"
    FRONTEND_ENGINEERING = "frontend_engineering"
    DATABASE_ENGINEERING = "database_engineering"
    DEVOPS_CLOUD = "devops_cloud"
    MACHINE_LEARNING = "machine_learning"
    DATA_ENGINEERING = "data_engineering"
    ALGORITHMS_PROBLEM_SOLVING = "algorithms_problem_solving"
    TESTING_QUALITY = "testing_quality"
    SECURITY = "security"
    SOFTWARE_ARCHITECTURE = "software_architecture"
    COLLABORATION = "collaboration"
    DOCUMENTATION_COMMUNICATION = "documentation_communication"


class RequirementPriority(str, Enum):
    """Priority level for job description requirements."""

    MANDATORY = "mandatory"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice_to_have"
    OPTIONAL = "optional"


class RequirementStatus(str, Enum):
    """Paper-compatible evaluation status for a requirement."""

    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class EvidenceState(str, Enum):
    """Backend-owned descriptive state for role-weighted evidence coverage."""

    UNKNOWN = "UNKNOWN"
    INSUFFICIENT = "INSUFFICIENT"
    SPARSE = "SPARSE"
    MODERATE = "MODERATE"
    SUBSTANTIAL = "SUBSTANTIAL"


class ArtifactAttributionState(str, Enum):
    """How repository history links a declared GitHub account to one artifact path."""

    VERIFIED_SELF_OWNED = "VERIFIED_SELF_OWNED"
    STRONG_ATTRIBUTION = "STRONG_ATTRIBUTION"
    PARTIAL_ATTRIBUTION = "PARTIAL_ATTRIBUTION"
    WEAK_ATTRIBUTION = "WEAK_ATTRIBUTION"
    REPOSITORY_ASSOCIATION_ONLY = "REPOSITORY_ASSOCIATION_ONLY"
    UNATTRIBUTED = "UNATTRIBUTED"
    UNKNOWN = "UNKNOWN"


class AnalysisStatus(str, Enum):
    """Lifecycle status of an end-to-end or stage analysis."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisStage(str, Enum):
    """Explicit pipeline execution stages."""

    PARSING_CV = "PARSING_CV"
    INGESTING_SOURCES = "INGESTING_SOURCES"
    ANALYZING_ARTIFACTS = "ANALYZING_ARTIFACTS"
    BUILDING_EVIDENCE = "BUILDING_EVIDENCE"
    CALIBRATING_RELIABILITY = "CALIBRATING_RELIABILITY"
    ESTIMATING_OWNERSHIP = "ESTIMATING_OWNERSHIP"
    COMPUTING_UNCERTAINTY = "COMPUTING_UNCERTAINTY"
    SCORING = "SCORING"
    PRIORITIZING_PROBES = "PRIORITIZING_PROBES"
    GENERATING_DOSSIER = "GENERATING_DOSSIER"


class SourceFamily(str, Enum):
    """The seven distinct source families analyzed in CCI."""

    RESUME = "resume"
    GITHUB = "github"
    DEPLOYMENT = "deployment"
    DATABASE = "database"
    CODING = "coding"
    CERTIFICATE = "certificate"
    LINKEDIN = "linkedin"


class SourceState(str, Enum):
    """Canonical lifecycle state of an evidence source.

    Lifecycle taxonomy:
    - DECLARED: Listed by candidate/manifest; not yet fetched or accessed.
    - DISCOVERED: Discovered via public links or repository references.
    - QUEUED: Staged for network retrieval or analysis.
    - FETCHING: Actively being retrieved.
    - FETCHED: Raw payload retrieved but not yet analyzed.
    - PARSED: Syntactically parsed into AST or structured form.
    - OBSERVED: Static inspection complete; technical observations extracted.
    - CORROBORATED: Corroborated with candidate technical claims.
    - VERIFIED: Formally verified by authoritative third-party issuer.
    - ACCESS_RESTRICTED: Rate-limited, 403, or blocked by security policies.
    - INACCESSIBLE: 404, DNS failure, network unreachable, or timeout.
    - FAILED: Malformed content, corrupted archive, or extraction error.
    - DEFERRED: Bounded out or queued for subsequent analysis pass.
    - NOT_SCANNED: Omitted due to safety, limits, or scan policy.
    """

    DECLARED = "declared"
    DISCOVERED = "discovered"
    QUEUED = "queued"
    FETCHING = "fetching"
    FETCHED = "fetched"
    PARSED = "parsed"
    OBSERVED = "observed"
    CORROBORATED = "corroborated"
    VERIFIED = "verified"
    ACCESS_RESTRICTED = "access_restricted"
    INACCESSIBLE = "inaccessible"
    FAILED = "failed"
    DEFERRED = "deferred"
    NOT_SCANNED = "not_scanned"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_norm = value.lower()
            aliases = {
                "unavailable": "inaccessible",
                "rate_limited": "access_restricted",
                "security_blocked": "access_restricted",
                "unsupported": "inaccessible",
                "parse_failed": "failed",
                "timeout": "inaccessible",
                "too_large": "access_restricted",
            }
            target = aliases.get(val_norm, val_norm)
            for member in cls:
                if member.value == target or member.name.lower() == target:
                    return member
        return super()._missing_(value)


# Backward compatibility aliases
SourceState.UNAVAILABLE = SourceState.INACCESSIBLE
SourceState.RATE_LIMITED = SourceState.ACCESS_RESTRICTED
SourceState.SECURITY_BLOCKED = SourceState.ACCESS_RESTRICTED
SourceState.UNSUPPORTED = SourceState.INACCESSIBLE
SourceState.PARSE_FAILED = SourceState.FAILED
SourceState.TIMEOUT = SourceState.INACCESSIBLE
SourceState.TOO_LARGE = SourceState.ACCESS_RESTRICTED


class ScanDepth(str, Enum):
    """Repository scanning depth classification."""

    DEEP = "deep"
    LIGHT = "light"


class ReliabilityState(str, Enum):
    """Taxonomy of source family reliability belief state.

    Taxonomy:
    - EXPERT_PRIOR: Expert-selected baseline parameters; not empirically calibrated.
    - POSTERIOR_SIMULATED: Updated from synthetic tests or benchmark simulations.
    - EMPIRICALLY_CALIBRATED: Updated from real, consenting measured outcome truth.
    """

    EXPERT_PRIOR = "expert_prior"
    POSTERIOR_SIMULATED = "posterior_simulated"
    EMPIRICALLY_CALIBRATED = "empirically_calibrated"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_norm = value.lower()
            aliases = {
                "prior": "expert_prior",
                "expert_selected": "expert_prior",
                "expert_prior": "expert_prior",
                "expert_priors": "expert_prior",
                "simulated": "posterior_simulated",
                "posterior_simulated": "posterior_simulated",
                "calibrated": "posterior_simulated",
                "empirically_calibrated": "empirically_calibrated",
                "empirical": "empirically_calibrated",
            }
            target = aliases.get(val_norm, val_norm)
            for member in cls:
                if member.value == target or member.name.lower() == target:
                    return member
        return super()._missing_(value)


# Backward compatibility aliases
ReliabilityState.PRIOR = ReliabilityState.EXPERT_PRIOR
ReliabilityState.CALIBRATED = ReliabilityState.POSTERIOR_SIMULATED
ReliabilityState.SIMULATED = ReliabilityState.POSTERIOR_SIMULATED


class ClaimStatus(str, Enum):
    """Canonical corroboration state taxonomy for candidate claims.

    Taxonomy:
    - SELF_REPORTED: Declared by candidate, not yet checked against artifacts.
    - OBSERVED: Directly observed in public/unverified artifact.
    - SUPPORTED: Corroborated by verified evidence.
    - STRONGLY_SUPPORTED: Supported by multiple verified high-confidence evidence sources.
    - ISSUER_VERIFIED: Directly attested by authoritative third-party issuer.
    - PARTIALLY_SUPPORTED: Some aspects verified, but incomplete match or lower confidence.
    - CONTRADICTED: Directly refuted by qualified negative evidence.
    - NOT_OBSERVED: No matching observation in available scope; NEVER treated as false.
    - INACCESSIBLE: Declared source could not be reached or accessed.
    - INSUFFICIENT_EVIDENCE: Observations present but below minimum evidentiary threshold.
    """

    SELF_REPORTED = "self_reported"
    OBSERVED = "observed"
    SUPPORTED = "supported"
    STRONGLY_SUPPORTED = "strongly_supported"
    ISSUER_VERIFIED = "issuer_verified"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    NOT_OBSERVED = "not_observed"
    INACCESSIBLE = "inaccessible"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_norm = value.lower()
            aliases = {
                "corroborated": "supported",
                "partial": "partially_supported",
                "unknown": "not_observed",
            }
            target = aliases.get(val_norm, val_norm)
            for member in cls:
                if member.value == target or member.name.lower() == target:
                    return member
        return super()._missing_(value)


# Backward compatibility aliases
ClaimStatus.CORROBORATED = ClaimStatus.SUPPORTED
ClaimStatus.PARTIAL = ClaimStatus.PARTIALLY_SUPPORTED
ClaimStatus.UNKNOWN = ClaimStatus.NOT_OBSERVED


class GraphNodeType(str, Enum):
    """Canonical node types in Candidate Evidence Graph (CEG) ontology.

    Ontology taxonomy:
    - CANDIDATE: The human candidate entity under evaluation.
    - IDENTITY: Digital identity accounts (GitHub, LinkedIn, GitLab, email).
    - ANALYSIS_RUN: Immutable snapshot / analysis evaluation run.
    - CLAIM: Self-reported or extracted claim made by candidate.
    - SKILL: Technical skill or capability declared or evaluated.
    - PROJECT: Software project declared in resume or discovered.
    - REPOSITORY: Source code repository associated with candidate.
    - ARTIFACT: Immutable file or code artifact within a repository.
    - DEPLOYMENT: Live deployed service or production application.
    - CREDENTIAL: Certification, badge, or external qualification.
    - ACADEMIC_RECORD: Multi-line education degree or coursework history.
    - EXPERIENCE_RECORD: Employment or organizational role history.
    - PUBLICATION: Academic paper, technical blog, or RFC.
    - CODING_PROFILE: Public competitive programming or developer profile.
    - SOURCE: Input evidence document, URL, or data provider.
    - ORGANIZATION: Company, university, or credential issuer.
    - CAPABILITY: Evaluated technical competency dimension.
    - OBSERVATION: Atomic static observation extracted from an artifact.
    """

    CANDIDATE = "Candidate"
    IDENTITY = "Identity"
    ANALYSIS_RUN = "AnalysisRun"
    CLAIM = "Claim"
    SKILL = "Skill"
    PROJECT = "Project"
    REPOSITORY = "Repository"
    ARTIFACT = "Artifact"
    DEPLOYMENT = "Deployment"
    CREDENTIAL = "Credential"
    ACADEMIC_RECORD = "AcademicRecord"
    EXPERIENCE_RECORD = "ExperienceRecord"
    PUBLICATION = "Publication"
    CODING_PROFILE = "CodingProfile"
    SOURCE = "Source"
    ORGANIZATION = "Organization"
    CAPABILITY = "Capability"
    OBSERVATION = "Observation"

    # Backward compatibility types
    EVIDENCE = "Evidence"
    ROLE_REQUIREMENT = "RoleRequirement"
    DOSSIER_ITEM = "DossierItem"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_norm = value.lower().replace("_", "")
            aliases = {
                "observation": "Observation",
                "evidence": "Evidence",
                "education": "AcademicRecord",
                "academic": "AcademicRecord",
                "academicrecord": "AcademicRecord",
                "experience": "ExperienceRecord",
                "experiencerecord": "ExperienceRecord",
                "repo": "Repository",
                "repository": "Repository",
                "analysisrun": "AnalysisRun",
                "codingprofile": "CodingProfile",
                "rolerequirement": "RoleRequirement",
                "dossieritem": "DossierItem",
            }
            target = aliases.get(val_norm, None)
            for member in cls:
                if (
                    member.value.lower() == value.lower()
                    or member.name.lower() == value.lower()
                    or member.value.lower().replace("_", "") == val_norm
                    or member.name.lower().replace("_", "") == val_norm
                    or (target and member.value == target)
                ):
                    return member
        return super()._missing_(value)


# Backward compatibility aliases
GraphNodeType.EDUCATION = GraphNodeType.ACADEMIC_RECORD
GraphNodeType.EXPERIENCE = GraphNodeType.EXPERIENCE_RECORD


class GraphEdgeType(str, Enum):
    """Canonical edge types in Candidate Evidence Graph (CEG) ontology.

    Ontology relationship taxonomy:
    - DECLARES: Candidate declares a claim, skill, project, or identity.
    - DISCOVERED_FROM: Entity discovered from a source or link.
    - CONTAINS: Container entity contains sub-entity (e.g. repo contains artifact).
    - OBSERVED_IN: Observation was made within an artifact or source.
    - SUPPORTS: Observation or evidence supports a claim or capability.
    - CONTRADICTS: Observation or qualified negative evidence refutes a claim or capability.
    - CONTRIBUTES_TO: Candidate contributed to a repository or artifact (does not imply authorship).
    - ATTRIBUTED_TO: Technical artifact or commit attributed to candidate with qualified confidence.
    - DEPLOYED_AS: Project or artifact deployed as a live endpoint/service.
    - ISSUED_BY: Credential or degree issued by an organization.
    - VERIFIES: Third-party authoritative attestation verifies a claim or identity.
    - REFERENCES: Claim, project, or artifact references a technology, source, or dependency.
    - USES_TECHNOLOGY: Project or artifact utilizes a language, framework, or skill.
    - ASSOCIATED_WITH: Candidate associated with an account or repository without authorship implication.
    - DERIVED_FROM: Observation, score, or requirement derived from an upstream entity.
    - AUTHORED_BY: Strict line-level or cryptographic authorship (requires verified evidence).
    """

    DECLARES = "DECLARES"
    DISCOVERED_FROM = "DISCOVERED_FROM"
    CONTAINS = "CONTAINS"
    OBSERVED_IN = "OBSERVED_IN"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    ATTRIBUTED_TO = "ATTRIBUTED_TO"
    DEPLOYED_AS = "DEPLOYED_AS"
    ISSUED_BY = "ISSUED_BY"
    VERIFIES = "VERIFIES"
    REFERENCES = "REFERENCES"
    USES_TECHNOLOGY = "USES_TECHNOLOGY"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    DERIVED_FROM = "DERIVED_FROM"
    AUTHORED_BY = "AUTHORED_BY"

    # Compatibility edge types
    SUPPORTS_CAPABILITY = "SUPPORTS_CAPABILITY"
    CORROBORATES = "CORROBORATES"
    SATISFIES_REQUIREMENT = "SATISFIES_REQUIREMENT"
    GENERATED_QUESTION_FROM = "GENERATED_QUESTION_FROM"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_norm = value.upper().replace("-", "_")
            aliases = {
                "CORROBORATE": "CORROBORATES",
                "SUPPORT": "SUPPORTS",
                "CONTRADICT": "CONTRADICTS",
            }
            target = aliases.get(val_norm, val_norm)
            for member in cls:
                if member.value == target or member.name == target:
                    return member
        return super()._missing_(value)


class EvidenceMode(str, Enum):
    """Canonical data origin mode enforcing unmistakable boundaries between live and synthetic data.

    Taxonomy:
    - LIVE: Real candidate intake, actual acquired artifacts, verified or unverified live sources.
    - SYNTHETIC: Explicit research demonstration scenario.
    - TEST_FIXTURE: Deterministic test fixtures for unit/integration suites.
    - RESEARCH_SIMULATION: Academic/empirical simulation experiments.
    """

    LIVE = "live"
    SYNTHETIC = "synthetic"
    TEST_FIXTURE = "test_fixture"
    RESEARCH_SIMULATION = "research_simulation"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_norm = value.lower().replace("-", "_")
            aliases = {
                "provided": "test_fixture",
                "real": "live",
                "production": "live",
                "simulation": "research_simulation",
                "experiment": "research_simulation",
                "test": "test_fixture",
                "fixture": "test_fixture",
                "demo": "synthetic",
            }
            target = aliases.get(val_norm, val_norm)
            for member in cls:
                if member.value == target or member.name.lower() == target:
                    return member
        return super()._missing_(value)

    @property
    def is_synthetic(self) -> bool:
        """Returns True if this mode represents synthetic or simulated data."""
        return self in (EvidenceMode.SYNTHETIC, EvidenceMode.RESEARCH_SIMULATION)

    @property
    def is_live(self) -> bool:
        """Returns True if this mode represents live real candidate data."""
        return self == EvidenceMode.LIVE


# Backward compatibility aliases
EvidenceMode.PROVIDED = EvidenceMode.TEST_FIXTURE
