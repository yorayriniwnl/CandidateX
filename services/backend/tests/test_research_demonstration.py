"""Acceptance checks for the paper demonstration, using the real API and scorer."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from cci.main import app
from cci.domain.enums import CanonicalRole, CapabilityKey, GraphNodeType, SourceFamily
from cci.pipeline.orchestrator import execute_analysis_pipeline, rescore_dossier

client = TestClient(app)


def run_demo(**changes):
    payload = {"candidate_id": str(uuid4()), "scenario": "consistent", "role": "backend", **changes}
    response = client.post("/api/v1/research-demo/run", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_empty_normal_pipeline_does_not_invent_evidence():
    state = execute_analysis_pipeline(uuid4(), CanonicalRole.BACKEND)
    assert state.dossier is not None
    assert state.dossier.rci is None
    assert state.dossier.coverage == 0
    assert state.dossier.ownership_assessments == []


def test_same_evidence_is_repeatable_but_role_and_jd_change_weights():
    candidate = str(uuid4())
    base = run_demo(candidate_id=candidate)
    repeated = run_demo(candidate_id=candidate)
    frontend = run_demo(candidate_id=candidate, role="frontend")
    jd = run_demo(candidate_id=candidate, jd_text="Must have React and TypeScript.")
    assert base["dossier"]["rci"] == repeated["dossier"]["rci"]
    assert base["evidence_digest"] == repeated["evidence_digest"] == frontend["evidence_digest"]
    assert base["dossier"]["rci"] != frontend["dossier"]["rci"]
    assert base["dossier"]["role_weights"] != jd["dossier"]["role_weights"]
    assert jd["dossier"]["role_requirements"]
    assert base["dossier"]["evidence_mode"] == "synthetic"
    assert len(base["dossier"]["evidence_records"]) > 0


def test_missingness_ownership_and_conflict_have_real_effects():
    base = run_demo()
    sparse = run_demo(scenario="sparse")
    low = run_demo(ownership_multiplier=0.05)
    conflict = run_demo(scenario="conflicting")
    empty = run_demo(excluded_sources=[s.value for s in SourceFamily])
    assert sparse["dossier"]["coverage"] < base["dossier"]["coverage"]
    assert low["dossier"]["coverage"] < base["dossier"]["coverage"]
    assert empty["dossier"]["rci"] is None
    assert empty["dossier"]["is_insufficient_evidence"]
    assert all(e["estimate"] is None for e in empty["dossier"]["capability_estimates"].values())
    assert any(c["has_meaningful_conflict"] for c in conflict["dossier"]["capability_conflicts"].values())
    # Sparse project evidence cannot justify a zero-width confidence interval.
    assert all(e["ci_lower"] is None for e in sparse["dossier"]["capability_estimates"].values())


def test_graph_traces_artifacts_and_questions_and_rescore_keeps_snapshot():
    from cci.domain.contracts import Dossier
    from cci.graph.ceg import CandidateEvidenceGraph

    data = run_demo(jd_text="Must have Python and PostgreSQL.")
    types = {n["type"] for n in data["graph"]["nodes"]}
    assert types == {t.value for t in GraphNodeType}
    dossier = Dossier.model_validate(data["dossier"])
    original_json = dossier.model_dump_json()
    rescored = rescore_dossier(dossier, {CapabilityKey.BACKEND_ENGINEERING: 1.0})
    assert dossier.model_dump_json() == original_json
    assert rescored.evidence_records == dossier.evidence_records
    assert rescored.override_history[-1]["previous_dossier_id"] == str(dossier.dossier_id)
    assert rescored.is_insufficient_evidence == (rescored.coverage < 0.35)
    evidence_ids = {e.evidence_id for e in rescored.evidence_records}
    assert any(q.grounding_evidence_ids for q in rescored.interview_questions)
    assert all(set(q.grounding_evidence_ids) <= evidence_ids for q in rescored.interview_questions)
    for node in data["graph"]["nodes"]:
        if node["type"] == "Evidence":
            assert len(node["properties"]["fingerprint"]) == 64
            assert node["properties"]["confidence_factors"]
    graph = CandidateEvidenceGraph.from_dict(data["graph_snapshot"])
    traces = graph.trace_provenance(CapabilityKey.BACKEND_ENGINEERING)
    assert traces and all(t["artifacts"] and t["sources"] for t in traces)


@pytest.mark.parametrize("weights", [{}, {"backend_engineering": -1}, {"backend_engineering": 0}])
def test_invalid_overrides_fail_as_validation_errors(weights):
    data = run_demo()
    response = client.post("/api/v1/pipeline/rescore", json={"run_id": data["dossier"]["analysis_run_id"], "weights": weights})
    assert response.status_code == 422


def test_synthetic_counts_calibrate_reliability_without_external_validation_claim():
    data = run_demo(scenario="sparse", reliability_false_positives=20)
    base = run_demo(scenario="sparse")
    assert data["dossier"]["coverage"] < base["dossier"]["coverage"]
    assert all(s["false_positive_count"] == 20 for s in data["reliability"].values())
    assert data["benchmark_scope"]["headline_reproduced"] is False


def test_method_calculator_uses_paper_probe_equation():
    response = client.post("/api/v1/research/calculate", json={"theorem_id": 8, "parameters": {
        "role_weight": .2, "coverage": .5, "ci_width": .4, "contradiction": .6}})
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(.2 * (.4 * .5 + .35 * .4 + .25 * .6))


def test_synthetic_export_preserves_label():
    data = run_demo()
    response = client.get(f"/api/v1/dossier/{data['dossier']['candidate_id']}/export?format=markdown")
    assert "synthetic" in response.text.lower()


def test_rescore_api_updates_graph_and_retains_original_snapshot():
    data = run_demo()
    run_id = data["dossier"]["analysis_run_id"]
    response = client.post("/api/v1/pipeline/rescore", json={"run_id": run_id, "weights": {"backend_engineering": 1}, "justification": "Focus on backend requirements"})
    assert response.status_code == 200
    revised = response.json()
    assert revised["override_history"][-1]["justification"] == "Focus on backend requirements"
    graph = client.get(f"/api/v1/dossier/{revised['candidate_id']}/graph").json()
    node_ids = {n["id"] for n in graph["nodes"]}
    assert all(q["question_id"] in node_ids for q in revised["interview_questions"])
    assert data["dossier"]["dossier_id"] != revised["dossier_id"]


def test_demo_rescore_returns_graph_from_the_same_snapshot():
    data = run_demo()
    response = client.post("/api/v1/research-demo/rescore", json={"run_id": data["dossier"]["analysis_run_id"], "weights": {"backend_engineering": 1}})
    assert response.status_code == 200
    revised = response.json()
    assert {q["question_id"] for q in revised["dossier"]["interview_questions"]} <= {n["id"] for n in revised["graph"]["nodes"]}


def test_failed_persistent_override_does_not_publish_success(monkeypatch):
    import cci.api.routers.overrides as overrides
    from cci.api.routers.dossier import get_stored_dossier
    data = run_demo()
    from uuid import UUID
    candidate = UUID(data["dossier"]["candidate_id"])
    previous = get_stored_dossier(candidate)
    def unavailable():
        raise RuntimeError("Storage unavailable")
    monkeypatch.setattr(overrides, "SessionLocal", unavailable)
    response = client.post("/api/v1/overrides/recruiter", json={
        "candidate_id": str(candidate), "role_weights": {"backend_engineering": 1},
        "organization_id": str(uuid4()), "justification": "Persist a reviewed override"})
    assert response.status_code == 503
    assert get_stored_dossier(candidate) == previous


def test_unrecognized_jd_does_not_invent_architecture_requirements():
    baseline = run_demo()
    unknown = run_demo(jd_text="Must have synergistic paradigms.")
    assert unknown["dossier"]["role_weights"] == baseline["dossier"]["role_weights"]
    assert unknown["dossier"]["role_requirements"][0]["capability_mappings"] == []


def test_research_role_breakdown_matches_archived_artifact():
    from pathlib import Path
    import json
    artifact = json.loads((Path(__file__).resolve().parents[3] / "research/results/ablation_results.json").read_text())
    response = client.get("/api/v1/research/ablation-study")
    assert response.status_code == 200
    result = response.json()
    assert {r["role"] for r in result["role_breakdown"]} == set(artifact["metadata"]["roles"])
    for row in result["role_breakdown"]:
        assert row["full_cci_mae"] == pytest.approx(artifact["per_role_summary"][row["role"]]["rci_mae"])
        assert row["no_decay_mae"] is None  # No per-role ablation data was archived.


def test_legacy_override_returns_the_confirmed_graph_and_dossier_together():
    data = run_demo()
    response = client.post("/api/v1/overrides/recruiter", json={"candidate_id": data["dossier"]["candidate_id"],
        "role_weights": {"backend_engineering": 1}, "justification": "Backend-focused interview"})
    assert response.status_code == 200
    revised = response.json()
    assert revised["graph"]["analysis_run_id"] == revised["dossier"]["analysis_run_id"]
    assert {q["question_id"] for q in revised["dossier"]["interview_questions"]} <= {n["id"] for n in revised["graph"]["nodes"]}


def test_rescore_recomputes_insufficient_evidence_flag():
    from cci.domain.contracts import EvidenceRecord
    data = run_demo()
    evidence = [EvidenceRecord.model_validate(e) for e in data["dossier"]["evidence_records"] if e["target_capability"] == "backend_engineering"]
    state = execute_analysis_pipeline(uuid4(), CanonicalRole.BACKEND, custom_evidence=evidence)
    assert state.dossier.is_insufficient_evidence
    rescored = rescore_dossier(state.dossier, {CapabilityKey.BACKEND_ENGINEERING: 1})
    assert rescored.coverage == 1
    assert not rescored.is_insufficient_evidence
