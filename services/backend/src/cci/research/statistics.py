"""Statistics and table formatting for the repository supplementary ablation harness.

These helpers operate on repository implementation diagnostics. Their output must not
be labelled as an exact reproduction of the submitted paper's 28,800 candidate-role
controlled benchmark.
"""

from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

from cci.research.ablation import AblationMode


def calculate_cliffs_delta(x: List[float], y: List[float]) -> float:
    """Compute non-parametric Cliff's delta effect size between two distributions."""
    nx = len(x)
    ny = len(y)
    if nx == 0 or ny == 0:
        return 0.0

    greater = 0
    less = 0
    for x_value in x:
        for y_value in y:
            if x_value > y_value:
                greater += 1
            elif x_value < y_value:
                less += 1

    return float((greater - less) / (nx * ny))


def compute_wilcoxon_comparison(
    full_cci_errors: List[float],
    ablation_errors: List[float],
) -> Dict[str, Any]:
    """Compare paired Full CCI and ablation error vectors with Wilcoxon tests."""
    if len(full_cci_errors) != len(ablation_errors):
        raise ValueError("Paired Wilcoxon test requires equal-length error vectors")

    differences = np.array(ablation_errors) - np.array(full_cci_errors)
    non_zero_differences = differences[differences != 0]

    if len(non_zero_differences) == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "two_sided_p_value": 1.0,
            "is_significant": False,
            "cliffs_delta": 0.0,
            "mean_difference": 0.0,
        }

    one_sided = stats.wilcoxon(differences, alternative="greater")
    two_sided = stats.wilcoxon(differences, alternative="two-sided")

    return {
        "statistic": float(two_sided.statistic),
        "p_value": float(one_sided.pvalue),
        "two_sided_p_value": float(two_sided.pvalue),
        "is_significant": bool(one_sided.pvalue < 0.001),
        "cliffs_delta": round(calculate_cliffs_delta(ablation_errors, full_cci_errors), 4),
        "mean_difference": round(float(np.mean(differences)), 4),
    }


def format_markdown_ablation_table(
    ablation_results: Dict[str, Dict[str, float]],
    statistical_tests: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """Format the supplementary implementation ablation as a Markdown table."""
    lines = [
        "| Evaluation Model | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\\rho$ ↑ | Kendall's $\\tau$ ↑ | Comparison vs Full CCI |",
        "|:-----------------|:---------:|:----------:|:-------------------:|:-----------------:|:-----------------------:|",
    ]

    for mode_name, metrics in ablation_results.items():
        comparison = "Supplementary baseline" if mode_name == AblationMode.FULL_CCI.value else "-"
        if statistical_tests and mode_name in statistical_tests:
            test_result = statistical_tests[mode_name]
            p_value = test_result.get("two_sided_p_value", test_result.get("p_value", 1.0))
            comparison = (
                f"paired Wilcoxon p={p_value:.3e}"
                + (" (significant)" if test_result.get("is_significant") else " (not significant)")
            )

        lines.append(
            f"| **{mode_name}** | {metrics.get('rci_mae', 0.0):.3f} | "
            f"{metrics.get('rci_rmse', 0.0):.3f} | {metrics.get('spearman_rho', 0.0):.3f} | "
            f"{metrics.get('kendall_tau', 0.0):.3f} | {comparison} |"
        )

    return "\n".join(lines)


def format_latex_ablation_table(
    ablation_results: Dict[str, Dict[str, float]],
    statistical_tests: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """Generate a provenance-safe LaTeX table for the supplementary harness."""
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Repository supplementary implementation ablation. This diagnostic is distinct from the submitted paper's 28,800 candidate-role controlled benchmark.}",
        r"\label{tab:supplementary_ablation_study}",
        r"\small",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"\textbf{Model Architecture} & \textbf{MAE $\downarrow$} & \textbf{RMSE $\downarrow$} & \textbf{Spearman $\rho$ $\uparrow$} & \textbf{Kendall $\tau$ $\uparrow$} \\",
        r"\midrule",
    ]

    for mode_name, metrics in ablation_results.items():
        marker = ""
        if statistical_tests and mode_name in statistical_tests:
            if statistical_tests[mode_name].get("is_significant"):
                marker = r"$^{***}$"

        display_name = mode_name.replace("_", r"\_")
        lines.append(
            f"{display_name} & {metrics.get('rci_mae', 0.0):.3f}{marker} & "
            f"{metrics.get('rci_rmse', 0.0):.3f} & {metrics.get('spearman_rho', 0.0):.3f} & "
            f"{metrics.get('kendall_tau', 0.0):.3f} \\\\"
        )

    lines.extend(
        [
            r"\bottomrule",
            r"\multicolumn{5}{l}{\footnotesize Synthetic implementation-ablation evidence only; not real-world hiring validation.}",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )

    return "\n".join(lines)
