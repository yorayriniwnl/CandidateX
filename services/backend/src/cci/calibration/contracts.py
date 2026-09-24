"""Data contracts for real and labeled benchmark empirical calibration infrastructure (Fix 21).

Invariants:
1. Do not fabricate a dataset: infrastructure accepts consenting real evaluation cases.
2. Synthetic cases must remain explicitly labeled `is_synthetic=True`.
3. Anonymization: candidate and project identifiers must be strictly anonymized (no raw emails or PII).
4. Data provenance and consent must be explicitly tracked on intake.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cci.domain.enums import CanonicalRole


class ReviewerExpertise(str, Enum):
    """Domain expertise classification of an independent technical reviewer."""

    STAFF_PLUS = "staff_plus"
    SENIOR = "senior"
    MID = "mid"
    JUNIOR = "junior"
    DOMAIN_EXPERT = "domain_expert"
    EXTERNAL_AUDITOR = "external_auditor"


class ReviewerRating(BaseModel):
    """Independent rating from a qualified technical reviewer."""

    model_config = ConfigDict(frozen=True)

    reviewer_id: str = Field(..., min_length=1)
    expertise: ReviewerExpertise
    dimension: str = Field(..., min_length=1, description="Capability key or technical dimension")
    rating: float = Field(..., ge=0.0, le=100.0, description="Evaluated score in [0.0, 100.0]")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: str | None = None


class IndependentTechnicalEvaluation(BaseModel):
    """External objective ground-truth assessment (e.g. blind code review, standardized test)."""

    model_config = ConfigDict(frozen=True)

    evaluation_id: UUID = Field(default_factory=uuid4)
    evaluator_id: str = Field(..., min_length=1)
    benchmark_name: str = Field(..., min_length=1)
    dimension: str = Field(..., min_length=1)
    ground_truth_score: float = Field(..., ge=0.0, le=100.0)
    evaluation_type: str = Field(
        default="blind_code_review",
        description="Type: blind_code_review, work_sample, standardized_benchmark, live_audit",
    )
    notes: str | None = None


class PredictedSignal(BaseModel):
    """CandidateX predicted capability signal for a case."""

    model_config = ConfigDict(frozen=True)

    capability_key: str = Field(..., min_length=1)
    predicted_score: float = Field(..., ge=0.0, le=100.0)
    predicted_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_observed: bool = True
    contributing_evidence_count: int = Field(default=0, ge=0)


class ConsentProvenance(BaseModel):
    """Consent and provenance tracking for evaluation case data."""

    model_config = ConfigDict(frozen=True)

    consent_granted: bool = Field(..., description="Must be True for real-world candidate data")
    consent_version: str = Field(..., min_length=1)
    data_source: str = Field(..., min_length=1)
    anonymization_method: str = Field(default="sha256_salted_hash")
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    consent_reference_id: str | None = None


class CalibrationCase(BaseModel):
    """Consenting real or labeled benchmark candidate evaluation case for empirical calibration."""

    model_config = ConfigDict(frozen=True)

    case_id: UUID = Field(default_factory=uuid4)
    anonymized_subject_id: str = Field(
        ...,
        min_length=3,
        description="Strictly anonymized candidate or project identifier (never raw email or PII)",
    )
    role: CanonicalRole
    reviewer_ratings: list[ReviewerRating] = Field(default_factory=list)
    artifact_evidence: list[dict[str, Any]] = Field(default_factory=list)
    independent_evaluations: list[IndependentTechnicalEvaluation] = Field(default_factory=list)
    predicted_signals: dict[str, PredictedSignal] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    consent_provenance: ConsentProvenance
    is_synthetic: bool = Field(
        default=False,
        description="Invariant: Synthetic experiments must remain clearly labeled synthetic",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def reviewer_expertise(self) -> dict[str, ReviewerExpertise]:
        """Accessor mapping reviewer_id to expertise."""
        return {r.reviewer_id: r.expertise for r in self.reviewer_ratings}

    @field_validator("anonymized_subject_id")
    @classmethod
    def validate_anonymized_id(cls, v: str) -> str:
        if "@" in v:
            raise ValueError(
                "anonymized_subject_id must not contain an email address or un-anonymized identifier"
            )
        return v


# ---------------------------------------------------------------------------
# Calibration Reporting & Analytics Contracts
# ---------------------------------------------------------------------------


class InterRaterAgreementReport(BaseModel):
    """Statistical agreement analysis across multiple independent technical reviewers."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    num_cases: int
    num_reviewers: int
    mean_pairwise_mad: float = Field(
        ..., description="Mean Absolute Difference between reviewer pairs"
    )
    pearson_correlation: float | None = None
    cohens_kappa: float | None = None
    interpretation: str


class BinMetric(BaseModel):
    """Reliability bin metric for calibration curve and reliability diagram."""

    model_config = ConfigDict(frozen=True)

    bin_index: int
    bin_lower: float
    bin_upper: float
    count: int
    mean_predicted: float
    empirical_frequency: float
    calibration_gap: float


class CalibrationCurveReport(BaseModel):
    """Comprehensive calibration curve analysis comparing predicted signals to ground truth."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    num_cases: int
    num_bins: int
    bins: list[BinMetric]
    expected_calibration_error: float = Field(..., description="Weighted average calibration gap (ECE)")
    maximum_calibration_error: float = Field(..., description="Maximum bin calibration gap (MCE)")
    brier_score: float = Field(..., description="Mean squared difference between predicted and actual")
    mean_absolute_error: float
    root_mean_squared_error: float


class ClassificationMetricsReport(BaseModel):
    """Binary decision support metrics at a specified capability threshold."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    threshold: float
    total_cases: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    specificity: float
    f1_score: float
    accuracy: float


class FalsePositiveCaseAnalysis(BaseModel):
    """Detailed error analysis for an overestimation case."""

    model_config = ConfigDict(frozen=True)

    case_id: UUID
    anonymized_subject_id: str
    role: CanonicalRole
    dimension: str
    predicted_score: float
    ground_truth_score: float
    discrepancy: float
    is_synthetic: bool
    contributing_evidence_count: int
    analysis_notes: str


class FalseNegativeCaseAnalysis(BaseModel):
    """Detailed error analysis for an underestimation case."""

    model_config = ConfigDict(frozen=True)

    case_id: UUID
    anonymized_subject_id: str
    role: CanonicalRole
    dimension: str
    predicted_score: float
    ground_truth_score: float
    discrepancy: float
    is_synthetic: bool
    is_observed: bool
    analysis_notes: str


class ReliabilityDiagramData(BaseModel):
    """Visualization data for plotting reliability curves against the diagonal ideal."""

    model_config = ConfigDict(frozen=True)

    dimension: str
    bin_centers: list[float]
    empirical_accuracies: list[float]
    predicted_confidences: list[float]
    bin_counts: list[int]
    ascii_diagram: str


class RoleStratificationSummary(BaseModel):
    """Stratified calibration performance across candidate roles."""

    model_config = ConfigDict(frozen=True)

    role: CanonicalRole
    case_count: int
    mean_absolute_error: float
    expected_calibration_error: float
    precision: float
    recall: float
    false_positive_count: int
    false_negative_count: int
