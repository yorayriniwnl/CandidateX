"""Unit tests for statistical tests and paper reporting."""

import pytest
from cci.research.ablation import AblationMode
from cci.research.statistics import (
    calculate_cliffs_delta,
    compute_wilcoxon_comparison,
    format_latex_ablation_table,
    format_markdown_ablation_table,
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

    latex_table = format_latex_ablation_table(sample_results, sample_stats)
    assert r"\begin{table}" in latex_table
    assert r"\caption" in latex_table
    assert r"\end{table}" in latex_table
    assert "FULL\\_CCI" in latex_table
