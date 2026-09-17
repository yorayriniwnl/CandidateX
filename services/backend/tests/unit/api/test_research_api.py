"""Tests for the paper-aligned research and methodology API."""

from fastapi.testclient import TestClient
import pytest

from cci.main import app

client = TestClient(app)


def test_get_all_theorems() -> None:
    response = client.get("/api/v1/research/theorems")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10
    assert [item["id"] for item in data] == list(range(1, 11))

    theorem_8 = next(item for item in data if item["id"] == 8)
    formula = theorem_8["latex_formula"]
    assert "CIwidth" in formula
    assert "Conf" in formula
    assert "w_k" in formula
    assert "s_k" not in formula


def test_paper_benchmark_endpoint_matches_submitted_paper() -> None:
    response = client.get("/api/v1/research/paper-benchmark")
    assert response.status_code == 200
    data = response.json()

    assert data["evidence_layer"] == "paper_reported_controlled_benchmark"
    assert data["deterministic_seeds"] == 16
    assert data["candidate_profiles_per_seed"] == 300
    assert data["candidate_role_evaluations"] == 28800
    assert data["canonical_roles"] == [
        "backend",
        "frontend",
        "fullstack",
        "ml_engineer",
        "devops_cloud",
        "data_engineer",
    ]

    metrics = {metric["name"]: metric for metric in data["metrics"]}
    assert metrics["spearman_rho"] == {"name": "spearman_rho", "mean": 0.928, "std": 0.013}
    assert metrics["kendall_tau"] == {"name": "kendall_tau", "mean": 0.774, "std": 0.019}
    assert metrics["ndcg_at_20"] == {"name": "ndcg_at_20", "mean": 0.97, "std": 0.011}
    assert "real-world hiring" in data["validation_boundary"]


def test_supplementary_ablation_is_not_labeled_as_paper_headline_result() -> None:
    response = client.get("/api/v1/research/ablation-study")
    assert response.status_code == 200
    data = response.json()

    assert data["total_candidates"] == 4800
    assert data["total_seeds"] == 16
    assert data["roles_count"] == 6
    assert data["role_breakdown"] == []
    assert "Supplementary implementation ablation" in data["notes"]
    assert "28,800" in data["notes"]

    models = {item["model_name"]: item for item in data["models"]}
    assert models["FULL_CCI"]["is_baseline"] is True
    assert models["FULL_CCI"]["mae"] == pytest.approx(1.9426)
    assert models["FULL_CCI"]["spearman_rho"] == pytest.approx(0.9434)
    assert models["FULL_CCI"]["spearman_rho"] != pytest.approx(0.928)


def test_calculate_theorem_1_recency_decay() -> None:
    response = client.post(
        "/api/v1/research/calculate",
        json={"theorem_id": 1, "parameters": {"delta_t_months": 12.0, "lambda_rate": 0.05}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert 0.54 < payload["result"] < 0.56
    assert payload["bounds_satisfied"] is True


def test_calculate_theorem_2_six_factor_confidence_and_zero_collapse() -> None:
    normal = client.post(
        "/api/v1/research/calculate",
        json={
            "theorem_id": 2,
            "parameters": {
                "authority": 0.9,
                "ownership": 0.9,
                "recency": 0.9,
                "verifiability": 0.9,
                "complexity": 0.9,
                "reliability": 0.9,
            },
        },
    )
    assert normal.status_code == 200
    assert normal.json()["result"] == pytest.approx(0.9)

    collapsed = client.post(
        "/api/v1/research/calculate",
        json={
            "theorem_id": 2,
            "parameters": {
                "authority": 0.9,
                "ownership": 0.0,
                "recency": 0.9,
                "verifiability": 0.9,
                "complexity": 0.9,
                "reliability": 0.9,
            },
        },
    )
    assert collapsed.status_code == 200
    assert collapsed.json()["result"] == 0.0
    assert collapsed.json()["intermediate_steps"]["zero_collapsed"] is True


def test_calculate_theorem_4_kish_effective_count() -> None:
    response = client.post(
        "/api/v1/research/calculate",
        json={"theorem_id": 4, "parameters": {"confidences": [1.0, 1.0, 1.0, 1.0]}},
    )
    assert response.status_code == 200
    assert response.json()["result"] == 4.0


def test_calculate_theorem_7_contradiction() -> None:
    balanced = client.post(
        "/api/v1/research/calculate",
        json={"theorem_id": 7, "parameters": {"positive_support": 2.0, "negative_support": 2.0}},
    )
    assert balanced.status_code == 200
    assert abs(balanced.json()["result"]) < 0.001


def test_calculate_theorem_8_matches_paper_equation_11() -> None:
    response = client.post(
        "/api/v1/research/calculate",
        json={
            "theorem_id": 8,
            "parameters": {
                "role_weight": 0.2,
                "coverage": 0.5,
                "ci_width": 0.1,
                "conflict": 0.4,
                "alpha": 0.4,
                "beta": 0.35,
                "gamma": 0.25,
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    expected = 0.2 * (0.4 * 0.5 + 0.35 * 0.1 + 0.25 * 0.4)
    assert payload["result"] == pytest.approx(expected, abs=1e-4)
    assert "CIwidth" in payload["formula"]
    assert "gamma*Conf" in payload["formula"]


def test_invalid_confidence_factor_rejected() -> None:
    response = client.post(
        "/api/v1/research/calculate",
        json={
            "theorem_id": 2,
            "parameters": {
                "authority": 1.5,
                "ownership": 0.5,
                "recency": 0.5,
                "verifiability": 0.5,
                "complexity": 0.5,
                "reliability": 0.5,
            },
        },
    )
    assert response.status_code == 400
