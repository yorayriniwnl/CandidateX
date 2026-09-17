"""End-to-end pipeline orchestration package for Candidate Capability Intelligence (CCI)."""

from cci.pipeline.orchestrator import (
    AnalysisStage,
    PipelineExecutionState,
    PipelineStatus,
    execute_analysis_pipeline,
    rescore_dossier,
)
from cci.pipeline.service import PipelineService, pipeline_service

__all__ = [
    "AnalysisStage",
    "PipelineStatus",
    "PipelineExecutionState",
    "execute_analysis_pipeline",
    "rescore_dossier",
    "PipelineService",
    "pipeline_service",
]
