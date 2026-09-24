"""Statistical evaluation and empirical calibration analytics engine (Fix 21).

Pure functional operations for:
- Inter-rater agreement (mean absolute difference, Pearson correlation, Cohen's kappa)
- Calibration curves and reliability diagrams (ECE, MCE, Brier score)
- Precision, recall, specificity, and F1 score at decision thresholds
- False positive and false negative diagnostic case analysis
- Role-stratified calibration reporting
"""

from collections import defaultdict
from collections.abc import Sequence
import math
from typing import Any

import numpy as np

from cci.calibration.contracts import (
    BinMetric,
    CalibrationCase,
    CalibrationCurveReport,
    ClassificationMetricsReport,
    FalseNegativeCaseAnalysis,
    FalsePositiveCaseAnalysis,
    InterRaterAgreementReport,
    ReliabilityDiagramData,
    RoleStratificationSummary,
)
from cci.domain.enums import CanonicalRole


def _extract_ground_truth(case: CalibrationCase, dimension: str | None = None) -> float | None:
    """Extracts ground-truth capability score from independent evaluations or consensus reviewer ratings."""
    scores: list[float] = []
    # 1. Independent objective evaluations
    for ie in case.independent_evaluations:
        if dimension is None or ie.dimension.lower() == dimension.lower():
            scores.append(ie.ground_truth_score)
    if scores:
        return float(np.mean(scores))

    # 2. Reviewer ratings if independent evaluation not present
    for rr in case.reviewer_ratings:
        if dimension is None or rr.dimension.lower() == dimension.lower():
            scores.append(rr.rating)
    if scores:
        return float(np.mean(scores))

    return None


def _extract_predicted_score(case: CalibrationCase, dimension: str | None = None) -> tuple[float | None, bool]:
    """Extracts predicted capability score and observation status for a dimension."""
    if dimension:
        sig = case.predicted_signals.get(dimension)
        if sig is None:
            # Case-insensitive search
            for k, v in case.predicted_signals.items():
                if k.lower() == dimension.lower():
                    sig = v
                    break
        if sig is not None:
            return sig.predicted_score, sig.is_observed
        return None, False

    # Aggregate over all observed signals if dimension is None
    observed_scores = [
        sig.predicted_score for sig in case.predicted_signals.values() if sig.is_observed
    ]
    if observed_scores:
        return float(np.mean(observed_scores)), True
    return None, False


def compute_inter_rater_agreement(
    cases: Sequence[CalibrationCase],
    dimension: str | None = None,
    binarize_threshold: float = 70.0,
) -> InterRaterAgreementReport:
    """Evaluates inter-rater agreement across multiple independent technical reviewers."""
    target_dim = dimension or "all_dimensions"
    reviewer_pairs: list[tuple[float, float]] = []
    unique_reviewers: set[str] = set()
    total_cases_with_multi_raters = 0

    for case in cases:
        ratings_by_dim: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for rr in case.reviewer_ratings:
            dim_key = rr.dimension.lower()
            if dimension is None or dim_key == dimension.lower():
                ratings_by_dim[dim_key].append((rr.reviewer_id, rr.rating))
                unique_reviewers.add(rr.reviewer_id)

        case_had_pairs = False
        for dim_key, rat_list in ratings_by_dim.items():
            if len(rat_list) >= 2:
                case_had_pairs = True
                for i in range(len(rat_list)):
                    for j in range(i + 1, len(rat_list)):
                        reviewer_pairs.append((rat_list[i][1], rat_list[j][1]))
        if case_had_pairs:
            total_cases_with_multi_raters += 1

    if not reviewer_pairs:
        return InterRaterAgreementReport(
            dimension=target_dim,
            num_cases=len(cases),
            num_reviewers=len(unique_reviewers),
            mean_pairwise_mad=0.0,
            pearson_correlation=None,
            cohens_kappa=None,
            interpretation="Insufficient paired reviewer ratings for agreement computation",
        )

    r1 = np.array([p[0] for p in reviewer_pairs])
    r2 = np.array([p[1] for p in reviewer_pairs])
    mad = float(np.mean(np.abs(r1 - r2)))

    # Pearson correlation
    pearson_r: float | None = None
    if len(reviewer_pairs) >= 2:
        s1 = np.std(r1)
        s2 = np.std(r2)
        if s1 > 1e-6 and s2 > 1e-6:
            corr = np.corrcoef(r1, r2)[0, 1]
            if not np.isnan(corr):
                pearson_r = float(np.clip(corr, -1.0, 1.0))

    # Binarized Cohen's Kappa
    b1 = r1 >= binarize_threshold
    b2 = r2 >= binarize_threshold
    p_o = float(np.mean(b1 == b2))
    p1 = float(np.mean(b1))
    p2 = float(np.mean(b2))
    p_e = (p1 * p2) + ((1.0 - p1) * (1.0 - p2))
    kappa: float | None = None
    if abs(1.0 - p_e) > 1e-6:
        kappa_val = (p_o - p_e) / (1.0 - p_e)
        kappa = float(np.clip(kappa_val, -1.0, 1.0))
    elif abs(p_o - 1.0) < 1e-6:
        kappa = 1.0

    # Qualitative interpretation
    if kappa is not None:
        if kappa >= 0.81:
            interp = "Near-perfect inter-rater agreement (kappa >= 0.81)"
        elif kappa >= 0.61:
            interp = "Substantial inter-rater agreement (0.61 <= kappa < 0.81)"
        elif kappa >= 0.41:
            interp = "Moderate inter-rater agreement (0.41 <= kappa < 0.61)"
        elif kappa >= 0.21:
            interp = "Fair inter-rater agreement (0.21 <= kappa < 0.41)"
        else:
            interp = "Slight or poor inter-rater agreement (kappa < 0.21)"
    else:
        interp = f"Paired MAD = {mad:.2f} across {len(reviewer_pairs)} reviewer evaluations"

    return InterRaterAgreementReport(
        dimension=target_dim,
        num_cases=total_cases_with_multi_raters,
        num_reviewers=len(unique_reviewers),
        mean_pairwise_mad=round(mad, 4),
        pearson_correlation=round(pearson_r, 4) if pearson_r is not None else None,
        cohens_kappa=round(kappa, 4) if kappa is not None else None,
        interpretation=interp,
    )


def compute_calibration_curve(
    cases: Sequence[CalibrationCase],
    num_bins: int = 10,
    dimension: str | None = None,
    score_scale: float = 100.0,
) -> CalibrationCurveReport:
    """Computes calibration curve, Expected Calibration Error (ECE), and Brier score."""
    if num_bins < 2:
        raise ValueError("num_bins must be at least 2")

    target_dim = dimension or "all_dimensions"
    pairs: list[tuple[float, float]] = []  # (predicted, ground_truth) in [0, 1]
    raw_diffs: list[float] = []

    for case in cases:
        pred_score, observed = _extract_predicted_score(case, dimension)
        gt_score = _extract_ground_truth(case, dimension)
        if pred_score is not None and gt_score is not None and observed:
            p_norm = max(0.0, min(1.0, pred_score / score_scale))
            y_norm = max(0.0, min(1.0, gt_score / score_scale))
            pairs.append((p_norm, y_norm))
            raw_diffs.append(abs(pred_score - gt_score))

    if not pairs:
        # Return empty baseline report
        empty_bins = [
            BinMetric(
                bin_index=i,
                bin_lower=round(i / num_bins, 3),
                bin_upper=round((i + 1) / num_bins, 3),
                count=0,
                mean_predicted=0.0,
                empirical_frequency=0.0,
                calibration_gap=0.0,
            )
            for i in range(num_bins)
        ]
        return CalibrationCurveReport(
            dimension=target_dim,
            num_cases=0,
            num_bins=num_bins,
            bins=empty_bins,
            expected_calibration_error=0.0,
            maximum_calibration_error=0.0,
            brier_score=0.0,
            mean_absolute_error=0.0,
            root_mean_squared_error=0.0,
        )

    n_total = len(pairs)
    bin_edges = np.linspace(0.0, 1.0, num_bins + 1)
    bins_data: list[BinMetric] = []
    ece_terms: list[float] = []
    max_gap: float = 0.0

    for b in range(num_bins):
        lower = bin_edges[b]
        upper = bin_edges[b + 1]
        # Include right edge for final bin
        if b == num_bins - 1:
            in_bin = [p for p in pairs if lower <= p[0] <= upper]
        else:
            in_bin = [p for p in pairs if lower <= p[0] < upper]

        count = len(in_bin)
        if count > 0:
            mean_pred = float(np.mean([p[0] for p in in_bin]))
            emp_freq = float(np.mean([p[1] for p in in_bin]))
            gap = abs(mean_pred - emp_freq)
            ece_terms.append(gap * (count / n_total))
            if gap > max_gap:
                max_gap = gap
        else:
            mean_pred = (lower + upper) / 2.0
            emp_freq = 0.0
            gap = 0.0

        bins_data.append(
            BinMetric(
                bin_index=b,
                bin_lower=round(float(lower), 4),
                bin_upper=round(float(upper), 4),
                count=count,
                mean_predicted=round(mean_pred, 4),
                empirical_frequency=round(emp_freq, 4),
                calibration_gap=round(gap, 4),
            )
        )

    ece = float(sum(ece_terms))
    brier = float(np.mean([(p[0] - p[1]) ** 2 for p in pairs]))
    mae = float(np.mean(raw_diffs))
    rmse = float(math.sqrt(np.mean([d**2 for d in raw_diffs])))

    return CalibrationCurveReport(
        dimension=target_dim,
        num_cases=n_total,
        num_bins=num_bins,
        bins=bins_data,
        expected_calibration_error=round(ece, 4),
        maximum_calibration_error=round(max_gap, 4),
        brier_score=round(brier, 4),
        mean_absolute_error=round(mae, 4),
        root_mean_squared_error=round(rmse, 4),
    )


def compute_precision_recall_metrics(
    cases: Sequence[CalibrationCase],
    threshold: float = 70.0,
    dimension: str | None = None,
) -> ClassificationMetricsReport:
    """Computes binary precision, recall, specificity, and F1 at a defined competence threshold."""
    target_dim = dimension or "all_dimensions"
    tp = fp = tn = fn = 0

    for case in cases:
        pred_score, observed = _extract_predicted_score(case, dimension)
        gt_score = _extract_ground_truth(case, dimension)
        if pred_score is not None and gt_score is not None and observed:
            pred_pos = pred_score >= threshold
            gt_pos = gt_score >= threshold

            if pred_pos and gt_pos:
                tp += 1
            elif pred_pos and not gt_pos:
                fp += 1
            elif not pred_pos and not gt_pos:
                tn += 1
            else:
                fn += 1

    total = tp + fp + tn + fn
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    f1 = (
        float(2.0 * precision * recall / (precision + recall))
        if (precision + recall) > 0
        else 0.0
    )
    accuracy = float((tp + tn) / total) if total > 0 else 0.0

    return ClassificationMetricsReport(
        dimension=target_dim,
        threshold=threshold,
        total_cases=total,
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        specificity=round(specificity, 4),
        f1_score=round(f1, 4),
        accuracy=round(accuracy, 4),
    )


def analyze_false_positives(
    cases: Sequence[CalibrationCase],
    threshold: float = 70.0,
    margin: float = 15.0,
    dimension: str | None = None,
) -> list[FalsePositiveCaseAnalysis]:
    """Identifies overestimation cases where CandidateX predicted high but ground truth was low."""
    analyses: list[FalsePositiveCaseAnalysis] = []
    target_dim = dimension or "overall"

    for case in cases:
        pred_score, observed = _extract_predicted_score(case, dimension)
        gt_score = _extract_ground_truth(case, dimension)
        if pred_score is not None and gt_score is not None and observed:
            # Overestimation condition: predicted >= threshold but gt <= threshold - margin
            if pred_score >= threshold and gt_score <= (threshold - margin):
                discrepancy = pred_score - gt_score
                evidence_count = len(case.artifact_evidence)
                note = (
                    f"Overestimation of {discrepancy:.1f} points: predicted {pred_score:.1f} "
                    f"vs independent evaluation {gt_score:.1f}. Investigating potential "
                    f"authorial over-attribution or low-specificity rule triggers."
                )
                analyses.append(
                    FalsePositiveCaseAnalysis(
                        case_id=case.case_id,
                        anonymized_subject_id=case.anonymized_subject_id,
                        role=case.role,
                        dimension=target_dim,
                        predicted_score=pred_score,
                        ground_truth_score=gt_score,
                        discrepancy=round(discrepancy, 2),
                        is_synthetic=case.is_synthetic,
                        contributing_evidence_count=evidence_count,
                        analysis_notes=note,
                    )
                )

    analyses.sort(key=lambda a: a.discrepancy, reverse=True)
    return analyses


def analyze_false_negatives(
    cases: Sequence[CalibrationCase],
    threshold: float = 70.0,
    margin: float = 15.0,
    dimension: str | None = None,
) -> list[FalseNegativeCaseAnalysis]:
    """Identifies underestimation cases where ground truth was high but CandidateX was low or missing."""
    analyses: list[FalseNegativeCaseAnalysis] = []
    target_dim = dimension or "overall"

    for case in cases:
        pred_score, observed = _extract_predicted_score(case, dimension)
        gt_score = _extract_ground_truth(case, dimension)
        if gt_score is not None and gt_score >= threshold:
            # Underestimation condition: either unobserved or predicted significantly below threshold
            if (not observed or pred_score is None) or (pred_score <= (threshold - margin)):
                eff_pred = pred_score if pred_score is not None else 0.0
                discrepancy = gt_score - eff_pred
                if not observed or pred_score is None:
                    note = (
                        f"Underestimation due to unobserved evidence: candidate demonstrated mastery "
                        f"({gt_score:.1f}) in independent evaluation, but no corroborating public "
                        f"artifacts were discovered in repository scope."
                    )
                else:
                    note = (
                        f"Underestimation of {discrepancy:.1f} points: independent evaluation "
                        f"{gt_score:.1f} vs predicted {pred_score:.1f}. Investigating overly "
                        f"conservative heuristic discounts or missing repository linkage."
                    )

                analyses.append(
                    FalseNegativeCaseAnalysis(
                        case_id=case.case_id,
                        anonymized_subject_id=case.anonymized_subject_id,
                        role=case.role,
                        dimension=target_dim,
                        predicted_score=eff_pred,
                        ground_truth_score=gt_score,
                        discrepancy=round(discrepancy, 2),
                        is_synthetic=case.is_synthetic,
                        is_observed=observed,
                        analysis_notes=note,
                    )
                )

    analyses.sort(key=lambda a: a.discrepancy, reverse=True)
    return analyses


def generate_reliability_diagram(curve_report: CalibrationCurveReport) -> ReliabilityDiagramData:
    """Generates structured diagram data and an ASCII reliability curve visualization."""
    bin_centers: list[float] = []
    empirical_accs: list[float] = []
    predicted_confs: list[float] = []
    bin_counts: list[int] = []

    for b in curve_report.bins:
        center = round((b.bin_lower + b.bin_upper) / 2.0, 3)
        bin_centers.append(center)
        empirical_accs.append(b.empirical_frequency)
        predicted_confs.append(b.mean_predicted)
        bin_counts.append(b.count)

    # Construct ASCII diagram (10 rows from 1.0 down to 0.0)
    lines = [
        f"=== Reliability Diagram: {curve_report.dimension} (ECE={curve_report.expected_calibration_error:.4f}, N={curve_report.num_cases}) ===",
        "Empirical Accuracy vs Mean Predicted Confidence",
        "  1.0 |" + " " * 30,
    ]
    # Build text plot matrix
    plot_width = len(curve_report.bins) * 3
    for y_step in range(9, -1, -1):
        y_val = y_step / 10.0
        row_chars = []
        for b in curve_report.bins:
            if b.count == 0:
                row_chars.append(" . ")
            else:
                diff = abs(b.empirical_frequency - y_val)
                ideal_diff = abs(b.mean_predicted - y_val)
                if diff < 0.05:
                    row_chars.append(" * ")
                elif ideal_diff < 0.05:
                    row_chars.append(" - ")
                else:
                    row_chars.append("   ")
        lines.append(f"  {y_val:.1f} |" + "".join(row_chars))

    lines.append("      +" + "-" * (len(curve_report.bins) * 3))
    lines.append(
        "       "
        + "".join([f"{b.bin_lower:.1f}".center(3) for b in curve_report.bins])
    )
    lines.append("Legend: [*] Empirical Accuracy, [-] Ideal Calibration, [.] Empty Bin")

    return ReliabilityDiagramData(
        dimension=curve_report.dimension,
        bin_centers=bin_centers,
        empirical_accuracies=empirical_accs,
        predicted_confidences=predicted_confs,
        bin_counts=bin_counts,
        ascii_diagram="\n".join(lines),
    )


def stratify_calibration_by_role(
    cases: Sequence[CalibrationCase],
    dimension: str | None = None,
    threshold: float = 70.0,
) -> dict[CanonicalRole, RoleStratificationSummary]:
    """Computes calibration metrics, ECE, MAE, and error rates stratified across candidate roles."""
    cases_by_role: dict[CanonicalRole, list[CalibrationCase]] = defaultdict(list)
    for case in cases:
        cases_by_role[case.role].append(case)

    results: dict[CanonicalRole, RoleStratificationSummary] = {}
    for role, role_cases in cases_by_role.items():
        curve = compute_calibration_curve(role_cases, num_bins=5, dimension=dimension)
        metrics = compute_precision_recall_metrics(
            role_cases, threshold=threshold, dimension=dimension
        )
        fps = analyze_false_positives(role_cases, threshold=threshold, dimension=dimension)
        fns = analyze_false_negatives(role_cases, threshold=threshold, dimension=dimension)

        results[role] = RoleStratificationSummary(
            role=role,
            case_count=len(role_cases),
            mean_absolute_error=curve.mean_absolute_error,
            expected_calibration_error=curve.expected_calibration_error,
            precision=metrics.precision,
            recall=metrics.recall,
            false_positive_count=len(fps),
            false_negative_count=len(fns),
        )

    return results
