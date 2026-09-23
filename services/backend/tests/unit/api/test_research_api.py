"""Unit tests for Research, Theorems, and Formal Math API Router."""

from fastapi.testclient import TestClient
import pytest

from cci.main import app

client = TestClient(app)


def test_get_all_theorems():
    """Verifies that all 10 conference paper theorems are cataloged with complete properties."""
    response = client.get("/api/v1/research/theorems")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 10
    theorem_ids = [t["id"] for t in data]
    assert theorem_ids == list(range(1, 11))

    # Verify Theorem 1 has decay formula
    t1 = next(t for t in data if t["id"] == 1)
    assert "lambda" in t1["latex_formula"] or r"\lambda" in t1["latex_formula"]
    assert "Recency Decay" in t1["name"]

    # Verify Theorem 2 keeps attribution outside the five-factor quality mean.
    t2 = next(t for t in data if t["id"] == 2)
    assert "1/5" in t2["latex_formula"]
    assert "o_e" in t2["latex_formula"]
    assert len(t2["key_properties"]) >= 3

    # Verify Theorem 10 has security invariants
    t10 = next(t for t in data if t["id"] == 10)
    assert "Security" in t10["category"]


def test_get_ablation_study():
    """Verifies Table 1 reproduction benchmark data integrity."""
    response = client.get("/api/v1/research/ablation-study")
    assert response.status_code == 200
    data = response.json()

    assert data["total_candidates"] == 4800
    assert data["total_seeds"] == 16
    assert data["roles_count"] == 6

    # Verify 5 evaluation models
    models = {m["model_name"]: m for m in data["models"]}
    assert "FULL_CCI" in models
    assert "NO_RECENCY_DECAY" in models
    assert "NO_OWNERSHIP_DISCOUNT" in models
    assert "UNIFORM_WEIGHTS" in models
    assert "UNCALIBRATED_SOURCES" in models

    assert models["FULL_CCI"]["is_baseline"] is True
    assert models["FULL_CCI"]["mae"] == 1.256
    assert models["FULL_CCI"]["spearman_rho"] == 0.979
    assert "Scoring config 4.0.0" in data["notes"]
    assert "Minimum capability coverage 0.35" in data["notes"]
    assert "within-cluster artifact decay 0.5" in data["notes"]
    assert "candidates with estimates in both modes" in data["notes"]
    assert "o * (a * t * v * x * r)^(1/5)" in data["notes"]

    # Verify LaTeX and Markdown tables
    assert r"\begin{table}" in data["latex_table"]
    assert "| **FULL_CCI** |" in data["markdown_table"]

    # Verify role breakdown
    assert len(data["role_breakdown"]) == 6


def test_calculate_theorem_1_recency_decay():
    """Verifies live mathematical calculation for Theorem 1."""
    payload = {
        "theorem_id": 1,
        "parameters": {
            "delta_t_months": 12.0,
            "lambda_rate": 0.05,
        },
    }
    response = client.post("/api/v1/research/calculate", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["theorem_id"] == 1
    assert 0.54 < res["result"] < 0.56  # exp(-0.05 * 12) = exp(-0.6) ~= 0.5488
    assert res["bounds_satisfied"] is True


def test_calculate_theorem_2_attribution_gate():
    """Verifies the direct attribution gate and zero-factor collapse for Theorem 2."""
    # All factors positive
    payload_normal = {
        "theorem_id": 2,
        "parameters": {
            "authority": 0.90,
            "ownership": 0.90,
            "recency": 0.90,
            "verifiability": 0.90,
            "complexity": 0.90,
            "reliability": 0.90,
        },
    }
    resp = client.post("/api/v1/research/calculate", json=payload_normal)
    assert resp.status_code == 200
    res = resp.json()
    assert res["result"] == 0.8100
    assert res["bounds_satisfied"] is True
    assert res["intermediate_steps"]["zero_collapsed"] is False
    assert res["intermediate_steps"]["attribution_gate"] == 0.9
    assert res["intermediate_steps"]["evidence_quality"] == pytest.approx(0.9)
    assert res["result"] <= res["intermediate_steps"]["attribution_gate"]

    weak_payload = {
        "theorem_id": 2,
        "parameters": {
            "authority": 0.75,
            "ownership": 0.03,
            "recency": 0.75,
            "verifiability": 0.75,
            "complexity": 0.75,
            "reliability": 0.75,
        },
    }
    weak_result = client.post("/api/v1/research/calculate", json=weak_payload).json()
    assert weak_result["result"] == 0.0225
    assert weak_result["result"] <= 0.03

    # Zero factor collapse
    payload_zero = {
        "theorem_id": 2,
        "parameters": {
            "authority": 0.90,
            "ownership": 0.00,  # Zero ownership
            "recency": 0.90,
            "verifiability": 0.90,
            "complexity": 0.90,
            "reliability": 0.90,
        },
    }
    resp_zero = client.post("/api/v1/research/calculate", json=payload_zero)
    assert resp_zero.status_code == 200
    res_zero = resp_zero.json()
    assert res_zero["result"] == 0.0
    assert res_zero["intermediate_steps"]["zero_collapsed"] is True


def test_calculate_theorem_4_kish_sample_size():
    """Verifies Kish effective sample size calculation."""
    payload = {
        "theorem_id": 4,
        "parameters": {
            "confidences": [1.0, 1.0, 1.0, 1.0],
        },
    }
    resp = client.post("/api/v1/research/calculate", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["result"] == 4.0  # Equal confidences => n_eff = N


def test_calculate_theorem_7_contradiction():
    """Verifies contradiction diagnostic calculation."""
    # Balanced
    resp_balanced = client.post(
        "/api/v1/research/calculate",
        json={"theorem_id": 7, "parameters": {"positive_support": 2.0, "negative_support": 2.0}},
    )
    assert resp_balanced.status_code == 200
    assert abs(resp_balanced.json()["result"]) < 0.001

    # Positive dominance
    resp_pos = client.post(
        "/api/v1/research/calculate",
        json={"theorem_id": 7, "parameters": {"positive_support": 5.0, "negative_support": 0.0}},
    )
    assert resp_pos.status_code == 200
    assert resp_pos.json()["result"] > 0.99


def test_calculate_invalid_parameters():
    """Verifies error handling on out-of-bounds inputs."""
    # Factor > 1.0 in Theorem 2
    bad_factor = {
        "theorem_id": 2,
        "parameters": {"authority": 1.5, "ownership": 0.5, "recency": 0.5, "verifiability": 0.5, "complexity": 0.5, "reliability": 0.5},
    }
    resp = client.post("/api/v1/research/calculate", json=bad_factor)
    assert resp.status_code == 400
