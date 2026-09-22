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
    """Operational/observation state of an evidence source."""

    OBSERVED = "observed"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    UNSUPPORTED = "unsupported"
    PARSE_FAILED = "parse_failed"
    SECURITY_BLOCKED = "security_blocked"
    TOO_LARGE = "too_large"
    TIMEOUT = "timeout"


class ScanDepth(str, Enum):
    """Repository scanning depth classification."""

    DEEP = "deep"
    LIGHT = "light"


class ReliabilityState(str, Enum):
    """State of source family reliability posterior."""

    PRIOR = "prior"
    CALIBRATED = "calibrated"


class ClaimStatus(str, Enum):
    """Corroboration state of a candidate self-claim."""

    CORROBORATED = "corroborated"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class GraphNodeType(str, Enum):
    """Node types in Candidate Evidence Graph (CEG)."""

    CANDIDATE = "Candidate"
    IDENTITY = "Identity"
    SOURCE = "Source"
    ARTIFACT = "Artifact"
    EVIDENCE = "Evidence"
    CAPABILITY = "Capability"
    ROLE_REQUIREMENT = "RoleRequirement"
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
