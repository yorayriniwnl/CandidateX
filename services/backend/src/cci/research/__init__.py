"""Research, simulation, and ablation reproducibility package."""

from cci.research.ablation import (
    AblationMode,
    evaluate_candidate_ablation,
    run_ablation_evaluation,
)
from cci.research.simulation import (
    SimulatedCandidate,
    SimulatedObservation,
    generate_synthetic_cohort,
)
from cci.research.statistics import (
    calculate_cliffs_delta,
    compute_wilcoxon_comparison,
    format_latex_ablation_table,
    format_markdown_ablation_table,
)

__all__ = [
    "AblationMode",
    "SimulatedCandidate",
    "SimulatedObservation",
    "calculate_cliffs_delta",
    "compute_wilcoxon_comparison",
    "evaluate_candidate_ablation",
    "format_latex_ablation_table",
    "format_markdown_ablation_table",
    "generate_synthetic_cohort",
    "run_ablation_evaluation",
]
