"""Research exports load offline experiment dependencies only when requested."""

from importlib import import_module

_MODULES = {
    'AblationMode': 'ablation',
    'evaluate_candidate_ablation': 'ablation',
    'run_ablation_evaluation': 'ablation',
    'SimulatedCandidate': 'simulation',
    'SimulatedObservation': 'simulation',
    'generate_synthetic_cohort': 'simulation',
    'calculate_cliffs_delta': 'statistics',
    'compute_wilcoxon_comparison': 'statistics',
    'format_latex_ablation_table': 'statistics',
    'format_markdown_ablation_table': 'statistics',
}


def __getattr__(name):
    if name not in _MODULES:
        raise AttributeError(name)
    value = getattr(import_module(f'cci.research.{_MODULES[name]}'), name)
    globals()[name] = value
    return value

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
