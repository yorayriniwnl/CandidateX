"""End-to-end pipeline orchestration package for Candidate Capability Intelligence (CCI)."""

from cci.domain.enums import AnalysisStage
from cci.pipeline.orchestrator import (
    PipelineExecutionState,
    PipelineStatus,
    execute_analysis_pipeline,
    rescore_dossier,
)
from cci.pipeline.service import PipelineService, pipeline_service

__all__ = [
    "AnalysisStage",
    "PipelineExecutionState",
    "PipelineService",
    "PipelineStatus",
    "execute_analysis_pipeline",
    "pipeline_service",
    "rescore_dossier",
]
