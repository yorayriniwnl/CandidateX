"""Empirical calibration infrastructure package (Fix 21).

Provides real evaluation case intake, reviewer agreement analysis, calibration curves,
error diagnostics, and role stratification.
"""

from cci.calibration.contracts import (
    BinMetric,
    CalibrationCase,
    CalibrationCurveReport,
    ClassificationMetricsReport,
    ConsentProvenance,
    FalseNegativeCaseAnalysis,
    FalsePositiveCaseAnalysis,
    IndependentTechnicalEvaluation,
    InterRaterAgreementReport,
    PredictedSignal,
    ReliabilityDiagramData,
    ReviewerExpertise,
    ReviewerRating,
    RoleStratificationSummary,
)
from cci.calibration.evaluator import (
    analyze_false_negatives,
    analyze_false_positives,
    compute_calibration_curve,
    compute_inter_rater_agreement,
    compute_precision_recall_metrics,
    generate_reliability_diagram,
    stratify_calibration_by_role,
)
from cci.calibration.repository import CalibrationCaseRepository

__all__ = [
    "BinMetric",
    "CalibrationCase",
    "CalibrationCaseRepository",
    "CalibrationCurveReport",
    "ClassificationMetricsReport",
    "ConsentProvenance",
    "FalseNegativeCaseAnalysis",
    "FalsePositiveCaseAnalysis",
    "IndependentTechnicalEvaluation",
    "InterRaterAgreementReport",
    "PredictedSignal",
    "ReliabilityDiagramData",
    "ReviewerExpertise",
    "ReviewerRating",
    "RoleStratificationSummary",
    "analyze_false_negatives",
    "analyze_false_positives",
    "compute_calibration_curve",
    "compute_inter_rater_agreement",
    "compute_precision_recall_metrics",
    "generate_reliability_diagram",
    "stratify_calibration_by_role",
]
