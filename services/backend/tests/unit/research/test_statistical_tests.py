"""Unit tests for statistical tests and paper reporting."""

import pytest
from cci.research.ablation import AblationMode
from cci.research.statistics import (
    calculate_cliffs_delta,
    compute_wilcoxon_comparison,
    format_latex_ablation_table,
    format_markdown_ablation_table,
    pair_candidate_errors,
)


def test_cliffs_delta_calculation():
    """Verify Cliff's delta effect size calculations."""
    x = [1.0, 2.0, 3.0]
    y = [4.0, 5.0, 6.0]
    # y is strictly greater than x -> delta(y, x) = +1.0, delta(x, y) = -1.0
    delta_pos = calculate_cliffs_delta(y, x)
    delta_neg = calculate_cliffs_delta(x, y)

    assert delta_pos == 1.0
    assert delta_neg == -1.0

    # Identical distributions -> delta = 0.0
    assert calculate_cliffs_delta(x, x) == 0.0


def test_wilcoxon_signed_rank_comparison():
    """Verify Wilcoxon signed-rank paired test on sample error vectors."""
    # Full CCI has lower errors across candidates
    full_errors = [2.1, 3.0, 1.8, 4.2, 2.5, 3.1, 1.9, 2.8, 3.4, 2.2]
    ablated_errors = [5.5, 6.2, 4.9, 7.8, 5.1, 6.4, 4.5, 5.9, 6.8, 5.0]

    comp = compute_wilcoxon_comparison(full_errors, ablated_errors)
    assert comp["p_value"] < 0.01
    assert comp["is_significant"] is True
    assert comp["mean_difference"] > 2.0


def test_paired_errors_align_by_candidate_and_exclude_unmatched_candidates():
    reference = {"candidate-a": 1.0, "candidate-b": 2.0, "candidate-c": 3.0}
    ablation = {"candidate-b": 8.0, "candidate-c": 6.0, "candidate-d": 9.0}

    paired_reference, paired_ablation = pair_candidate_errors(reference, ablation)

    assert paired_reference == [2.0, 3.0]
    assert paired_ablation == [8.0, 6.0]


def test_paper_table_formatting():
    """Verify Markdown and LaTeX table generators produce valid outputs."""
    sample_results = {
        AblationMode.FULL_CCI.value: {"rci_mae": 3.42, "rci_rmse": 4.15, "spearman_rho": 0.88, "kendall_tau": 0.72},
        AblationMode.NO_RECENCY_DECAY.value: {"rci_mae": 6.81, "rci_rmse": 8.12, "spearman_rho": 0.65, "kendall_tau": 0.51},
    }
    sample_stats = {
        AblationMode.NO_RECENCY_DECAY.value: {"is_significant": True, "p_value": 0.0001},
    }

    md_table = format_markdown_ablation_table(sample_results, sample_stats)
    assert "| Evaluation Model |" in md_table
    assert "**FULL_CCI**" in md_table
    assert "Yes (***)" in md_table
    assert "Scoring config 5.1.0" in md_table
    assert "coverage >= 0.35" in md_table
    assert "within-cluster artifact decay is 0.50" in md_table
    assert "evidence family decay is 0.50" in md_table
    assert "| Paired N |" in md_table
    assert "candidates with estimates in both modes" in md_table

    latex_table = format_latex_ablation_table(sample_results, sample_stats)
    assert r"\begin{table}" in latex_table
    assert r"\caption" in latex_table
    assert r"\end{table}" in latex_table
    assert "FULL\\_CCI" in latex_table
    assert "Scoring config 5.1.0" in latex_table
    assert r"\mathrm{Cov}_k \ge 0.35" in latex_table
    assert r"\delta=0.50" in latex_table
    assert r"\gamma=0.50" in latex_table
    assert r"Paired $N$" in latex_table
    latex_lines = latex_table.splitlines()
    footnote_line = next(
        line for line in latex_lines if "Wilcoxon signed-rank test)." in line
    )
    assert footnote_line.endswith(r"\\")
    assert latex_lines.index(footnote_line) < latex_lines.index(r"\bottomrule")
