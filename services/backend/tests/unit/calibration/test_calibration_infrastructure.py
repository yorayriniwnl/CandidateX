"""Unit tests for empirical calibration infrastructure and analytics (Fix 21)."""

from datetime import datetime, timezone
from uuid import uuid4
import pytest

from cci.calibration import (
    CalibrationCase,
    CalibrationCaseRepository,
    ConsentProvenance,
    IndependentTechnicalEvaluation,
    PredictedSignal,
    ReviewerExpertise,
    ReviewerRating,
    analyze_false_negatives,
    analyze_false_positives,
    compute_calibration_curve,
    compute_inter_rater_agreement,
    compute_precision_recall_metrics,
    generate_reliability_diagram,
    stratify_calibration_by_role,
)
from cci.domain.enums import CanonicalRole


def _create_sample_case(
    subject_id: str = "anon_cand_001",
    role: CanonicalRole = CanonicalRole.BACKEND,
    dimension: str = "backend_engineering",
    predicted_score: float = 85.0,
    ground_truth_score: float = 80.0,
    reviewer_ratings: list[float] | None = None,
    consent_granted: bool = True,
    is_synthetic: bool = False,
    is_observed: bool = True,
) -> CalibrationCase:
    """Helper to construct a validated CalibrationCase fixture."""
    ratings = []
    if reviewer_ratings:
        for idx, r in enumerate(reviewer_ratings):
            ratings.append(
                ReviewerRating(
                    reviewer_id=f"rev_{idx + 1}",
                    expertise=ReviewerExpertise.SENIOR,
                    dimension=dimension,
                    rating=r,
                )
            )

    evals = [
        IndependentTechnicalEvaluation(
            evaluator_id="eval_lead_01",
            benchmark_name="blind_code_review_v1",
            dimension=dimension,
            ground_truth_score=ground_truth_score,
        )
    ]

    pred_signals = {
        dimension: PredictedSignal(
            capability_key=dimension,
            predicted_score=predicted_score,
            is_observed=is_observed,
            contributing_evidence_count=4,
        )
    }

    return CalibrationCase(
        case_id=uuid4(),
        anonymized_subject_id=subject_id,
        role=role,
        reviewer_ratings=ratings,
        independent_evaluations=evals,
        predicted_signals=pred_signals,
        artifact_evidence=[{"file": "api.py", "lines": 120}],
        consent_provenance=ConsentProvenance(
            consent_granted=consent_granted,
            consent_version="v2026.1",
            data_source="industry_eval_pilot",
        ),
        is_synthetic=is_synthetic,
    )


# ---------------------------------------------------------------------------
# Intake & Invariant Tests
# ---------------------------------------------------------------------------


def test_real_cases_require_explicit_consent():
    """Invariant: Real-world candidate data strictly requires consent_granted=True."""
    repo = CalibrationCaseRepository()

    # Case without consent should fail registration
    unconsented_case = _create_sample_case(consent_granted=False, is_synthetic=False)
    with pytest.raises(ValueError, match="consent_granted=True"):
        repo.register_case(unconsented_case)

    # Consented case registers cleanly
    consented_case = _create_sample_case(consent_granted=True, is_synthetic=False)
    registered = repo.register_case(consented_case)
    assert registered.case_id == consented_case.case_id
    assert repo.count(is_synthetic=False) == 1


def test_synthetic_cases_must_be_labeled_synthetic():
    """Invariant: Synthetic benchmark runs must be marked is_synthetic=True and don't bypass real consent."""
    repo = CalibrationCaseRepository()
    synth_case = _create_sample_case(consent_granted=False, is_synthetic=True)
    registered = repo.register_case(synth_case)
    assert registered.is_synthetic is True
    assert repo.count(is_synthetic=True) == 1
    assert repo.count(is_synthetic=False) == 0


def test_strict_anonymization_validation():
    """Invariant: Subject IDs must not leak candidate PII or raw email addresses."""
    repo = CalibrationCaseRepository()
    with pytest.raises(ValueError, match="anonymized"):
        _create_sample_case(subject_id="alice@example.com")


# ---------------------------------------------------------------------------
# Inter-Rater Agreement Tests
# ---------------------------------------------------------------------------


def test_inter_rater_agreement_high_concordance():
    """Verify agreement metrics when multiple reviewers strongly agree."""
    cases = [
        _create_sample_case(
            subject_id=f"anon_{i}",
            reviewer_ratings=[85.0, 88.0],
            ground_truth_score=86.0,
        )
        for i in range(10)
    ]
    report = compute_inter_rater_agreement(cases, dimension="backend_engineering")
    assert report.num_cases == 10
    assert report.num_reviewers == 2
    assert report.mean_pairwise_mad == pytest.approx(3.0, abs=1e-3)
    assert report.cohens_kappa == pytest.approx(1.0, abs=1e-3)  # Both agree all are >= 70
    assert "Substantial" in report.interpretation or "Near-perfect" in report.interpretation


def test_inter_rater_agreement_discordant():
    """Verify agreement metrics when reviewers disagree."""
    cases = [
        _create_sample_case(
            subject_id=f"anon_{i}",
            reviewer_ratings=[90.0 if i % 2 == 0 else 40.0, 45.0 if i % 2 == 0 else 85.0],
        )
        for i in range(10)
    ]
    report = compute_inter_rater_agreement(cases)
    assert report.mean_pairwise_mad == pytest.approx(45.0, abs=1.0)
    assert report.cohens_kappa is not None
    assert report.cohens_kappa < 0.2  # Poor agreement


# ---------------------------------------------------------------------------
# Calibration Curve & Reliability Diagram Tests
# ---------------------------------------------------------------------------


def test_well_calibrated_predictions():
    """Verify that predictions matching ground truth yield minimal ECE and MCE."""
    cases = []
    # Generate 20 cases with near-perfect alignment
    for score in range(10, 100, 5):
        cases.append(
            _create_sample_case(
                subject_id=f"cand_{score}",
                predicted_score=float(score),
                ground_truth_score=float(score + 1.0),
            )
        )

    curve = compute_calibration_curve(cases, num_bins=5, dimension="backend_engineering")
    assert curve.num_cases == len(cases)
    assert curve.expected_calibration_error < 0.05
    assert curve.maximum_calibration_error < 0.10
    assert curve.mean_absolute_error == pytest.approx(1.0, abs=1e-3)

    # Reliability diagram generation
    diagram = generate_reliability_diagram(curve)
    assert len(diagram.bin_centers) == 5
    assert "Reliability Diagram" in diagram.ascii_diagram


def test_poorly_calibrated_overconfident_predictions():
    """Verify that systematically overconfident predictions produce high calibration error."""
    cases = [
        _create_sample_case(
            subject_id=f"cand_{i}",
            predicted_score=95.0,
            ground_truth_score=35.0,
        )
        for i in range(15)
    ]
    curve = compute_calibration_curve(cases, num_bins=5)
    assert curve.expected_calibration_error > 0.50
    assert curve.brier_score > 0.30
    assert curve.mean_absolute_error == pytest.approx(60.0, abs=1e-3)


# ---------------------------------------------------------------------------
# Precision, Recall & Error Analysis Tests
# ---------------------------------------------------------------------------


def test_precision_recall_and_confusion_matrix():
    """Verify classification metrics at threshold 70.0."""
    cases = [
        # True Positives (pred >= 70, gt >= 70)
        _create_sample_case("tp1", predicted_score=85.0, ground_truth_score=80.0),
        _create_sample_case("tp2", predicted_score=75.0, ground_truth_score=72.0),
        # False Positive (pred >= 70, gt < 70)
        _create_sample_case("fp1", predicted_score=88.0, ground_truth_score=50.0),
        # True Negative (pred < 70, gt < 70)
        _create_sample_case("tn1", predicted_score=55.0, ground_truth_score=60.0),
        # False Negative (pred < 70, gt >= 70)
        _create_sample_case("fn1", predicted_score=60.0, ground_truth_score=82.0),
    ]

    metrics = compute_precision_recall_metrics(cases, threshold=70.0)
    assert metrics.total_cases == 5
    assert metrics.true_positives == 2
    assert metrics.false_positives == 1
    assert metrics.true_negatives == 1
    assert metrics.false_negatives == 1
    assert metrics.precision == pytest.approx(2.0 / 3.0, abs=1e-3)
    assert metrics.recall == pytest.approx(2.0 / 3.0, abs=1e-3)
    assert metrics.specificity == pytest.approx(1.0 / 2.0, abs=1e-3)
    assert metrics.accuracy == pytest.approx(3.0 / 5.0, abs=1e-3)


def test_false_positive_and_false_negative_diagnostic_analysis():
    """Verify automated extraction of significant discrepancy cases."""
    cases = [
        # Substantial False Positive (pred=92, gt=40)
        _create_sample_case("fp_case", predicted_score=92.0, ground_truth_score=40.0),
        # Substantial False Negative (pred=30, gt=88)
        _create_sample_case("fn_case", predicted_score=30.0, ground_truth_score=88.0),
        # Accurately calibrated case (pred=85, gt=84)
        _create_sample_case("calibrated", predicted_score=85.0, ground_truth_score=84.0),
    ]

    fps = analyze_false_positives(cases, threshold=70.0, margin=15.0)
    assert len(fps) == 1
    assert fps[0].anonymized_subject_id == "fp_case"
    assert fps[0].discrepancy == pytest.approx(52.0, abs=1e-2)
    assert "Overestimation" in fps[0].analysis_notes

    fns = analyze_false_negatives(cases, threshold=70.0, margin=15.0)
    assert len(fns) == 1
    assert fns[0].anonymized_subject_id == "fn_case"
    assert fns[0].discrepancy == pytest.approx(58.0, abs=1e-2)
    assert "Underestimation" in fns[0].analysis_notes


# ---------------------------------------------------------------------------
# Role Stratification Tests
# ---------------------------------------------------------------------------


def test_role_stratification():
    """Verify calibration metrics stratified across candidate roles."""
    cases = [
        _create_sample_case("cand_b1", role=CanonicalRole.BACKEND, predicted_score=80.0, ground_truth_score=82.0),
        _create_sample_case("cand_b2", role=CanonicalRole.BACKEND, predicted_score=75.0, ground_truth_score=70.0),
        _create_sample_case("cand_f1", role=CanonicalRole.FRONTEND, predicted_score=90.0, ground_truth_score=50.0),
    ]

    stratified = stratify_calibration_by_role(cases)
    assert CanonicalRole.BACKEND in stratified
    assert CanonicalRole.FRONTEND in stratified

    backend_summary = stratified[CanonicalRole.BACKEND]
    assert backend_summary.case_count == 2
    assert backend_summary.mean_absolute_error < 5.0
    assert backend_summary.false_positive_count == 0

    frontend_summary = stratified[CanonicalRole.FRONTEND]
    assert frontend_summary.case_count == 1
    assert frontend_summary.mean_absolute_error == pytest.approx(40.0, abs=1e-2)
    assert frontend_summary.false_positive_count == 1
