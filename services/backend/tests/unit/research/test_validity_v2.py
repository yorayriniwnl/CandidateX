"""Small structural checks for the new synthetic validity protocol."""
import numpy as np

from research.run_validity_v2 import run_validation, seed_bootstrap


def test_seed_bootstrap_uses_blocks():
    scores = {11: [1.0, 1.0], 22: [5.0, 5.0]}
    lower, upper = seed_bootstrap(scores, [11, 22], n_resamples=200)
    assert np.isfinite(lower) and np.isfinite(upper)
    assert 1.0 <= lower <= upper <= 5.0


def test_revised_protocol_has_unweighted_baselines_and_source_integrity():
    rows = []
    result = run_validation(seeds=[7, 13], candidates_per_role=2, bootstrap_resamples=50, record_sink=rows.append)
    assert result["protocol"] == "source-aware-v2"
    assert result["archived_v1_metrics_comparable"] is False
    assert result["simulated_instances"] == 2 * 6 * 2
    assert result["invalid_non_github_fork_observations"] == 0
    assert len(rows) == 2 * 6 * 2 * 7
    assert len({(r["seed"], r["role"], r["candidate_index"], r["mode"]) for r in rows}) == len(rows)
    assert all(r["rci_absolute_error"] >= 0 and r["observed_capabilities"] > 0 for r in rows)
    assert "FULL_CCI" in result["results"]
    assert "EQUAL_EVIDENCE" in result["results"]
    assert "MEDIAN_EVIDENCE" in result["results"]
    assert len(result["results"]["FULL_CCI"]["rci_mae_95ci_seed_bootstrap"]) == 2
