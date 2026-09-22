"""Statistical testing and paper table generation for research evaluations.

FORMAL PAPER REPRODUCIBILITY:
Implements Wilcoxon signed-rank paired tests, effect size estimation (Cliff's delta),
and paper-ready LaTeX / Markdown reporting.
"""

from typing import Any

import numpy as np
from scipy import stats

from cci.domain.contracts import ScoringConfig
from cci.research.ablation import AblationMode


def calculate_cliffs_delta(x: list[float], y: list[float]) -> float:
    """Computes non-parametric Cliff's delta effect size between two distributions."""
    nx = len(x)
    ny = len(y)
    if nx == 0 or ny == 0:
        return 0.0

    greater = 0
    less = 0
    for xi in x:
        for yj in y:
            if xi > yj:
                greater += 1
            elif xi < yj:
                less += 1

    return float((greater - less) / (nx * ny))


def compute_wilcoxon_comparison(
    full_cci_errors: list[float],
    ablation_errors: list[float],
) -> dict[str, Any]:
    """Performs Wilcoxon signed-rank test comparing Full CCI error distribution against an ablation."""
    if len(full_cci_errors) != len(ablation_errors):
        raise ValueError("Paired Wilcoxon test requires equal-length error vectors")

    diffs = np.array(ablation_errors) - np.array(full_cci_errors)
    # Check if there are non-zero differences
    non_zeros = diffs[diffs != 0]

    if len(non_zeros) == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "is_significant": False,
            "cliffs_delta": 0.0,
            "mean_difference": 0.0,
        }

    # One-sided test: Full CCI error is significantly less than ablation error (diffs > 0)
    res_one_sided = stats.wilcoxon(diffs, alternative="greater")
    res_two_sided = stats.wilcoxon(diffs, alternative="two-sided")

    delta = calculate_cliffs_delta(ablation_errors, full_cci_errors)
    mean_diff = float(np.mean(diffs))

    return {
        "statistic": float(res_two_sided.statistic),
        "p_value": float(res_one_sided.pvalue),
        "two_sided_p_value": float(res_two_sided.pvalue),
        "is_significant": bool(res_one_sided.pvalue < 0.001),
        "cliffs_delta": round(delta, 4),
        "mean_difference": round(mean_diff, 4),
    }


def format_markdown_ablation_table(
    ablation_results: dict[str, dict[str, float]],
    statistical_tests: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Generates a formatted Markdown table suitable for documentation and reports."""
    config = ScoringConfig()
    lines = [
        "| Evaluation Model | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\\rho$ ↑ | Kendall's $\\tau$ ↑ | Stat. Sig. ($p < 0.001$) |",
        "|:-----------------|:---------:|:----------:|:-------------------:|:-----------------:|:------------------------:|",
    ]

    for mode_name, metrics in ablation_results.items():
        sig_str = "Baseline" if mode_name == AblationMode.FULL_CCI.value else "-"
        if statistical_tests and mode_name in statistical_tests:
            sig_info = statistical_tests[mode_name]
            sig_str = (
                "Yes (***)"
                if sig_info.get("is_significant")
                else f"p={sig_info.get('p_value', 1.0):.3e}"
            )

        mae_str = f"{metrics.get('rci_mae', 0.0):.3f}"
        rmse_str = f"{metrics.get('rci_rmse', 0.0):.3f}"
        rho_str = f"{metrics.get('spearman_rho', 0.0):.3f}"
        tau_str = f"{metrics.get('kendall_tau', 0.0):.3f}"

        lines.append(
            f"| **{mode_name}** | {mae_str} | {rmse_str} | {rho_str} | {tau_str} | {sig_str} |"
        )

    lines.extend(
        [
            "",
            f"*Scoring config {config.version}; candidate estimates require coverage >= "
            f"{config.low_coverage_threshold:.2f}; lower coverage is UNKNOWN.*",
        ]
    )
    return "\n".join(lines)


def format_latex_ablation_table(
    ablation_results: dict[str, dict[str, float]],
    statistical_tests: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Generates a publication-quality LaTeX table for conference paper submission."""
    config = ScoringConfig()
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Ablation Study Results Across Canonical Engineering Roles ($N=4{,}800$).}",
        r"\label{tab:ablation_study}",
        r"\small",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"\textbf{Model Architecture} & \textbf{MAE $\downarrow$} & \textbf{RMSE $\downarrow$} & \textbf{Spearman $\rho$ $\uparrow$} & \textbf{Kendall $\tau$ $\uparrow$} \\",
        r"\midrule",
    ]

    for mode_name, metrics in ablation_results.items():
        asterisk = ""
        if statistical_tests and mode_name in statistical_tests:
            if statistical_tests[mode_name].get("is_significant"):
                asterisk = r"$^{***}$"

        mae_str = f"{metrics.get('rci_mae', 0.0):.3f}{asterisk}"
        rmse_str = f"{metrics.get('rci_rmse', 0.0):.3f}"
        rho_str = f"{metrics.get('spearman_rho', 0.0):.3f}"
        tau_str = f"{metrics.get('kendall_tau', 0.0):.3f}"

        name_display = mode_name.replace("_", r"\_")
        lines.append(
            f"{name_display} & {mae_str} & {rmse_str} & {rho_str} & {tau_str} \\\\"
        )

    lines.extend(
        [
            r"\multicolumn{5}{l}{\footnotesize $^{***}$Statistically significant degradation vs.\ Full CCI ($p < 0.001$, Wilcoxon signed-rank test).}" + r"\\",
            rf"\multicolumn{{5}}{{l}}{{\footnotesize Scoring config {config.version}; candidate estimates require $\mathrm{{Cov}}_k \ge {config.low_coverage_threshold:.2f}$; lower coverage is UNKNOWN.}}",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )

    return "\n".join(lines)
