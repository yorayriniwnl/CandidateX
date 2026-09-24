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
    """State of source family reliability posterior."""

    PRIOR = "prior"
    CALIBRATED = "calibrated"


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
    """Node types in Candidate Evidence Graph (CEG)."""

    CANDIDATE = "Candidate"
    IDENTITY = "Identity"
    SOURCE = "Source"
    ARTIFACT = "Artifact"
    EVIDENCE = "Evidence"
    CAPABILITY = "Capability"
    ROLE_REQUIREMENT = "RoleRequirement"
    CLAIM = "Claim"
    ANALYSIS_RUN = "AnalysisRun"
    DOSSIER_ITEM = "DossierItem"


class GraphEdgeType(str, Enum):
    """Edge types in Candidate Evidence Graph (CEG)."""

    AUTHORED_BY = "AUTHORED_BY"  # Requires artifact-specific authorship evidence.
    ASSOCIATED_WITH = "ASSOCIATED_WITH"  # Repository link does not imply contribution.
    CONTRIBUTES_TO = "CONTRIBUTES_TO"  # Contribution may be repository- or artifact-scoped.
    DERIVED_FROM = "DERIVED_FROM"
    SUPPORTS_CAPABILITY = "SUPPORTS_CAPABILITY"
    CONTRADICTS = "CONTRADICTS"
    CORROBORATES = "CORROBORATES"
    SATISFIES_REQUIREMENT = "SATISFIES_REQUIREMENT"
    GENERATED_QUESTION_FROM = "GENERATED_QUESTION_FROM"
