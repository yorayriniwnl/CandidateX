"""Unit tests for the paper experiment reproduction script."""

import json
from pathlib import Path
import pytest

from cci.domain.enums import CanonicalRole
from research.run_paper_experiments import (
    run_full_simulation_study,
    save_publication_artifacts,
)


def test_quick_simulation_study(tmp_path: Path):
    """Verify that run_full_simulation_study executes cleanly on small cohort and outputs valid artifacts."""
    results = run_full_simulation_study(
        seeds=[42, 100],
        candidates_per_role=5,
        roles=[CanonicalRole.BACKEND, CanonicalRole.FRONTEND],
    )

    assert "metadata" in results
    assert results["metadata"]["total_candidates"] == 2 * 2 * 5  # 20 candidates
    assert results["metadata"]["scoring_config_version"] == "3.0.0"
    assert results["metadata"]["minimum_capability_coverage"] == 0.35
    assert "ablation_summary" in results
    assert "statistical_tests" in results
    assert "per_role_summary" in results

    # Check that all 5 modes exist in ablation summary
    assert len(results["ablation_summary"]) == 5
    for mode_name, metrics in results["ablation_summary"].items():
        assert "rci_mae" in metrics
        assert "rci_rmse" in metrics
        assert "spearman_rho" in metrics
        assert "kendall_tau" in metrics

    # Save artifacts and check file presence
    save_publication_artifacts(results, tmp_path)

    md_file = tmp_path / "table_ablation_study.md"
    tex_file = tmp_path / "table_ablation_study.tex"
    role_file = tmp_path / "role_breakdown.md"
    json_file = tmp_path / "ablation_results.json"

    assert md_file.exists()
    assert tex_file.exists()
    assert role_file.exists()
    assert json_file.exists()
    assert "Scoring config 3.0.0" in md_file.read_text(encoding="utf-8")
    assert "coverage >= 0.35" in md_file.read_text(encoding="utf-8")
    assert "UNKNOWN" in tex_file.read_text(encoding="utf-8")
    assert "Scoring config 3.0.0" in role_file.read_text(encoding="utf-8")

    # Verify JSON content
    with open(json_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["metadata"]["total_candidates"] == 20
    assert "FULL_CCI" in loaded["ablation_summary"]
