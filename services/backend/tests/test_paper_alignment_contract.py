"""Regression contract between the submitted CCI paper and public implementation.

These tests validate presentation and provenance alignment. They deliberately do not
pretend that the repository supplementary ablation regenerated the paper benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PAPER_MANIFEST = REPO_ROOT / "research" / "paper_benchmark_manifest.json"

CANONICAL_PROBE_TOKENS = (
    "w_k",
    "alpha",
    "1 -",
    "Cov",
    "beta",
    "CIwidth",
    "gamma",
    "Conf",
)

STALE_PROBE_FORMULAS = (
    "w_k \\cdot \\sigma_k \\cdot (1 + \\gamma |D_k|)",
    "w_k · (1 - Cov_k) + α · s_k + β · C_k",
    "w_k \\cdot (1 - \\text{Cov}_k) + \\alpha \\cdot s_k + \\beta \\cdot C_k",
)

DISPLAY_FILES = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "services" / "backend" / "src" / "cci" / "api" / "routers" / "research.py",
    REPO_ROOT / "apps" / "web" / "components" / "ResearchTheoremsExplorer.tsx",
    REPO_ROOT / "apps" / "web" / "components" / "dossier" / "InterviewProbesPanel.tsx",
    REPO_ROOT / "scripts" / "analyze_candidate.py",
    REPO_ROOT / "services" / "backend" / "src" / "cci" / "reports" / "exporter.py",
)


def test_paper_benchmark_manifest_matches_submitted_paper() -> None:
    assert PAPER_MANIFEST.exists(), "paper benchmark provenance manifest is missing"
    data = json.loads(PAPER_MANIFEST.read_text(encoding="utf-8"))

    assert data["benchmark_type"] == "controlled_synthetic_mechanism_validation"
    assert (
        data["provenance"]
        == "reported_in_submitted_paper_not_regenerated_by_repository_ablation_harness"
    )
    assert data["seeds"] == 16
    assert data["candidates_per_seed"] == 300
    assert data["roles"] == [
        "backend",
        "frontend",
        "fullstack",
        "ml_engineer",
        "devops_cloud",
        "data_engineer",
    ]
    assert data["candidate_role_evaluations"] == 28_800
    assert data["primary_results"]["spearman_rho"]["mean"] == 0.928
    assert data["primary_results"]["kendall_tau"]["mean"] == 0.774
    assert data["primary_results"]["ndcg_at_20"]["mean"] == 0.970
    assert data["role_agnostic_spearman_rho"] == 0.849
    assert data["source_dropout_60pct_spearman_rho"] == 0.716
    assert data["candidate_shuffle_spearman_rho"]["mean"] == -0.006
    assert data["generator_regimes"] == 40
    assert data["generator_regime_additional_evaluations"] == 288_000


def test_displayed_probe_formula_matches_paper_equation_11() -> None:
    for path in DISPLAY_FILES:
        text = path.read_text(encoding="utf-8")
        for stale in STALE_PROBE_FORMULAS:
            assert stale not in text, (
                f"stale probe formula remains in {path.relative_to(REPO_ROOT)}"
            )

    backend_impl = (
        REPO_ROOT
        / "services"
        / "backend"
        / "src"
        / "cci"
        / "probes"
        / "priority.py"
    ).read_text(encoding="utf-8")
    for token in CANONICAL_PROBE_TOKENS:
        assert token in backend_impl


def test_research_defaults_use_the_six_paper_roles() -> None:
    paths = (
        REPO_ROOT
        / "services"
        / "backend"
        / "src"
        / "cci"
        / "api"
        / "routers"
        / "research.py",
        REPO_ROOT
        / "apps"
        / "web"
        / "components"
        / "ResearchTheoremsExplorer.tsx",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "Mobile Engineering" not in text
        assert 'role="mobile"' not in text
        assert "role: 'mobile'" not in text
        assert (
            "data_engineer" in text
            or "Data Engineer" in text
            or "Data Engineering" in text
        )


def test_repository_distinguishes_paper_benchmark_from_supplementary_ablation() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    runner = (REPO_ROOT / "research" / "run_paper_experiments.py").read_text(
        encoding="utf-8"
    )
    statistics = (
        REPO_ROOT
        / "services"
        / "backend"
        / "src"
        / "cci"
        / "research"
        / "statistics.py"
    ).read_text(encoding="utf-8")

    assert "28,800 candidate-role evaluations" in readme
    assert "supplementary implementation ablation" in readme.lower()
    assert "not an exact regeneration of the paper benchmark" in readme.lower()

    assert "supplementary implementation ablation" in runner.lower()
    assert "paper_exact_reproduction" in runner
    assert "supplementary implementation ablation" in statistics.lower()
    assert "28,800" in statistics
