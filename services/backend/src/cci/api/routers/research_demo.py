"""Explicit synthetic demonstration, independent of real-candidate ingestion."""
from fastapi import APIRouter, HTTPException
from cci.domain.contracts import ScoringConfig
from cci.pipeline.service import pipeline_service
from cci.research.scenarios import DemoRequest, make_scenario, evidence_digest, VERSION
from cci.api.routers.pipeline_router import PipelineRescoreRequest
from cci.graph.builder import build_dossier_graph

router = APIRouter(prefix="/api/v1/research-demo", tags=["Research demonstration"])


@router.post("/rescore")
def rescore_demo(request: PipelineRescoreRequest):
    dossier = pipeline_service.rescore_run(request.run_id, request.weights, request.justification)
    if dossier is None:
        raise HTTPException(404, "Run expired or not found. Run the demonstration again.")
    graph = build_dossier_graph(dossier)
    return {"dossier": dossier, "graph": graph.to_api_response(dossier.candidate_id, dossier.analysis_run_id),
            "graph_snapshot": graph.to_dict()}


@router.post("/run")
def run_demo(request: DemoRequest):
    records, reliability = make_scenario(request)
    scoring_config = ScoringConfig()
    state = pipeline_service.start_pipeline(
        candidate_id=request.candidate_id, role=request.role, jd_text=request.jd_text,
        declared_claims=request.declared_claims,
        custom_evidence=records, evidence_mode="synthetic", scenario=request.scenario,
        scoring_config=scoring_config)
    if state.dossier is None or state.ceg_graph is None:
        raise HTTPException(500, "Demonstration failed; no result has been substituted.")
    return {
        "dossier": state.dossier,
        "graph": state.ceg_graph.to_api_response(request.candidate_id, state.analysis_run_id),
        "graph_snapshot": state.ceg_graph.to_dict(),
        "input": request.model_dump(mode="json"),
        "evidence_digest": evidence_digest(records),
        "scenario_version": VERSION,
        "scoring_config": scoring_config, "reliability": reliability,
        "stages": [vars(stage) for stage in state.stages],
        "benchmark_scope": {
            "headline_reproduced": False,
            "paper": {"candidate_role_evaluations": 28800, "spearman_rho": 0.928,
                      "status": "Manuscript aggregate; original per-seed outputs and exact calibration unavailable"},
            "prototype": {"candidate_role_evaluations": 4800, "spearman_rho_rounded": 0.979,
                          "command": "python research/run_paper_experiments.py",
                          "status": "Separate executable experiment; not the headline benchmark"},
        },
        "storage_notice": "Run registry is process-local. Export JSON to retain the complete snapshot; use one backend worker.",
    }
