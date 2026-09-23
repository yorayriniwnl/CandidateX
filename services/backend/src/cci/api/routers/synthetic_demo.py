"""Strict, stateless API for the public synthetic-only demonstration."""
import math
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from cci.domain.contracts import EvidenceRecord, ScoringConfig
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.graph.builder import build_dossier_graph
from cci.pipeline.orchestrator import (
    PipelineExecutionState,
    PipelineStatus,
    execute_analysis_pipeline,
    rescore_dossier,
)
from cci.research.scenarios import DemoRequest, VERSION, evidence_digest, make_scenario

PUBLIC_DEMO_CANDIDATE_ID = UUID("d3333333-3333-4333-8333-333333333333")
SYNTHETIC_OVERRIDE_JUSTIFICATION = "Synthetic demonstration weight override"

router = APIRouter(prefix="/api/v1/synthetic-demo", tags=["Synthetic demonstration"])


class SyntheticDemoControls(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: Literal["consistent", "sparse", "low_ownership", "conflicting", "empty"] = "consistent"
    role: CanonicalRole = CanonicalRole.BACKEND
    excluded_sources: list[SourceFamily] = Field(default_factory=list, max_length=7)
    ownership_multiplier: float = Field(default=1, ge=0, le=1)
    reliability_false_positives: int = Field(default=0, ge=0, le=100)


class SyntheticDemoRescoreRequest(SyntheticDemoControls):
    weights: dict[CapabilityKey, float]

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, weights: dict[CapabilityKey, float]) -> dict[CapabilityKey, float]:
        total = sum(weights.values())
        if (
            not weights
            or any(not math.isfinite(value) or value < 0 for value in weights.values())
            or not math.isfinite(total)
            or total <= 0
        ):
            raise ValueError("Supply finite non-negative weights with a positive total")
        return weights


def build_synthetic_state(
    controls: SyntheticDemoControls,
) -> tuple[PipelineExecutionState, list[EvidenceRecord], dict[SourceFamily, Any]]:
    """Rebuild generated evidence for each request; no run cache is consulted."""
    demo_request = DemoRequest(
        candidate_id=PUBLIC_DEMO_CANDIDATE_ID,
        scenario=controls.scenario,
        role=controls.role,
        jd_text="",
        excluded_sources=controls.excluded_sources,
        ownership_multiplier=controls.ownership_multiplier,
        reliability_false_positives=controls.reliability_false_positives,
    )
    records, reliability = make_scenario(demo_request)
    scoring_config = ScoringConfig()
    state = execute_analysis_pipeline(
        candidate_id=PUBLIC_DEMO_CANDIDATE_ID,
        role=controls.role,
        jd_text="",
        custom_evidence=records,
        evidence_mode="synthetic",
        scenario=controls.scenario,
        scoring_config=scoring_config,
    )
    return state, records, reliability


def _require_complete_state(state: PipelineExecutionState) -> None:
    if (
        state.status is not PipelineStatus.COMPLETED
        or state.dossier is None
        or state.ceg_graph is None
    ):
        raise HTTPException(
            status_code=500,
            detail="Demonstration failed; no result has been substituted.",
        )


@router.post("/run")
def run_synthetic_demo(request: SyntheticDemoControls):
    state, records, reliability = build_synthetic_state(request)
    _require_complete_state(state)
    dossier = state.dossier
    graph = state.ceg_graph
    scoring_config = ScoringConfig()

    return {
        "dossier": dossier,
        "graph": graph.to_api_response(dossier.candidate_id, dossier.analysis_run_id),
        "graph_snapshot": graph.to_dict(),
        "input": request.model_dump(mode="json"),
        "evidence_digest": evidence_digest(records),
        "scenario_version": VERSION,
        "scoring_config": scoring_config,
        "reliability": reliability,
        "stages": [vars(stage) for stage in state.stages],
        "benchmark_scope": {
            "headline_reproduced": False,
            "paper": {
                "candidate_role_evaluations": 28800,
                "spearman_rho": 0.928,
                "status": "Manuscript aggregate; original per-seed outputs and exact calibration unavailable",
            },
            "prototype": {
                "candidate_role_evaluations": 4800,
                "spearman_rho_rounded": 0.979,
                "command": "python research/run_paper_experiments.py",
                "status": "Separate executable experiment; not the headline benchmark",
            },
        },
        "storage_notice": (
            "Synthetic scenarios are regenerated per request; no candidate data is stored and no run state persists."
        ),
    }


@router.post("/rescore")
def rescore_synthetic_demo(request: SyntheticDemoRescoreRequest):
    state, _records, _reliability = build_synthetic_state(request)
    _require_complete_state(state)
    dossier = rescore_dossier(
        state.dossier,
        request.weights,
        justification=SYNTHETIC_OVERRIDE_JUSTIFICATION,
    )
    graph = build_dossier_graph(dossier)
    return {
        "dossier": dossier,
        "graph": graph.to_api_response(dossier.candidate_id, dossier.analysis_run_id),
        "graph_snapshot": graph.to_dict(),
    }
