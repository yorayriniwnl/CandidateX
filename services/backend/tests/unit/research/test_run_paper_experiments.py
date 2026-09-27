"""Unit tests for the supplementary implementation ablation harness."""

import json
from pathlib import Path

from cci.domain.enums import CanonicalRole
from research.run_paper_experiments import (
    run_full_simulation_study,
    save_publication_artifacts,
)


def test_quick_simulation_study(tmp_path: Path):
    """Verify the small harness run and its provenance-labelled artifacts."""
    results = run_full_simulation_study(
        seeds=[42, 100],
        candidates_per_role=5,
        roles=[CanonicalRole.BACKEND, CanonicalRole.FRONTEND],
    )

    assert "metadata" in results
    assert results["metadata"]["total_candidates"] == 2 * 2 * 5
    assert results["metadata"]["total_evaluations"] == 20
    assert results["metadata"]["evidence_layer"] == "supplementary_implementation_ablation"
    assert results["metadata"]["paper_exact_reproduction"] is False
    assert results["metadata"]["paper_reported_candidate_role_evaluations"] == 28_800
    assert "ablation_summary" in results
    assert "statistical_tests" in results
    assert "per_role_summary" in results

    assert len(results["ablation_summary"]) == 5
    for metrics in results["ablation_summary"].values():
        assert "rci_mae" in metrics
        assert "rci_rmse" in metrics
        assert "spearman_rho" in metrics
        assert "kendall_tau" in metrics

    save_publication_artifacts(results, tmp_path)

    md_file = tmp_path / "table_ablation_study.md"
    tex_file = tmp_path / "table_ablation_study.tex"
    role_file = tmp_path / "role_breakdown.md"
    json_file = tmp_path / "ablation_results.json"

    assert md_file.exists()
    assert tex_file.exists()
    assert role_file.exists()
    assert json_file.exists()

    markdown = md_file.read_text(encoding="utf-8")
    latex = tex_file.read_text(encoding="utf-8")
    role_breakdown = role_file.read_text(encoding="utf-8")

    assert "Supplementary Implementation Ablation" in markdown
    assert "not an exact regeneration of the paper benchmark" in markdown
    assert "supplementary implementation ablation" in latex.lower()
    assert "28,800" in latex
    assert "Supplementary Implementation Ablation" in role_breakdown

    with json_file.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    assert loaded["metadata"]["total_candidates"] == 20
    assert loaded["metadata"]["paper_exact_reproduction"] is False
    assert "FULL_CCI" in loaded["ablation_summary"]
