"""Unit tests for paper ablation study engine."""

from cci.domain.enums import CanonicalRole
from cci.research.ablation import (
    AblationMode,
    run_ablation_evaluation,
)
from cci.research.simulation import generate_synthetic_cohort


def test_ablation_evaluations_run_cleanly():
    """Verify all 5 paper ablation modes execute and compute metrics on simulated cohort."""
    cohort = generate_synthetic_cohort(role=CanonicalRole.BACKEND, count=40, seed=42)

    results = {}
    for mode in AblationMode:
        metrics = run_ablation_evaluation(cohort=cohort, mode=mode, role=CanonicalRole.BACKEND)
        results[mode] = metrics
        assert "rci_mae" in metrics
        assert "rci_rmse" in metrics
        assert "spearman_rho" in metrics
        assert "kendall_tau" in metrics
        assert metrics["sample_count"] > 0
        assert 0.0 <= metrics["rci_mae"] <= 100.0

    # Full CCI ranking correlation is positive and substantial
    full_metrics = results[AblationMode.FULL_CCI]
    assert full_metrics["spearman_rho"] > 0.40
    assert full_metrics["kendall_tau"] > 0.30
