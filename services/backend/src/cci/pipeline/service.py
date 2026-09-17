"""Pipeline Service for executing and tracking CCI analysis runs."""

from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID

from cci.domain.contracts import Dossier, EvidenceRecord
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.pipeline.orchestrator import (
    PipelineExecutionState,
    execute_analysis_pipeline,
    rescore_dossier,
)


class PipelineService:
    """Thread-safe registry for CCI pipeline runs and dossier caching."""

    def __init__(self):
        self._runs: Dict[UUID, PipelineExecutionState] = {}
        self._dossiers_by_id: Dict[UUID, Dossier] = {}
        self._lock = Lock()

    def start_pipeline(
        self,
        candidate_id: UUID,
        role: CanonicalRole,
        jd_text: Optional[str] = None,
        cv_text: Optional[str] = None,
        repo_urls: Optional[List[str]] = None,
        declared_claims: Optional[List[str]] = None,
        custom_evidence: Optional[List[EvidenceRecord]] = None,
        expert_weight_overrides: Optional[Dict[CapabilityKey, float]] = None,
    ) -> PipelineExecutionState:
        """Executes the analysis pipeline and stores execution state."""
        state = execute_analysis_pipeline(
            candidate_id=candidate_id,
            role=role,
            jd_text=jd_text,
            cv_text=cv_text,
            repo_urls=repo_urls,
            declared_claims=declared_claims,
            custom_evidence=custom_evidence,
            expert_weight_overrides=expert_weight_overrides,
        )

        with self._lock:
            self._runs[state.analysis_run_id] = state
            if state.dossier:
                self._dossiers_by_id[state.dossier.dossier_id] = state.dossier
                try:
                    from cci.api.routers.dossier import register_dossier
                    register_dossier(state.dossier, state.ceg_graph)
                except ImportError:
                    pass

        return state

    def get_pipeline_state(self, run_id: UUID) -> Optional[PipelineExecutionState]:
        """Retrieves pipeline state by run ID."""
        with self._lock:
            return self._runs.get(run_id)

    def get_dossier(self, dossier_id: UUID) -> Optional[Dossier]:
        """Retrieves Dossier by dossier ID."""
        with self._lock:
            return self._dossiers_by_id.get(dossier_id)

    def rescore_run(
        self,
        run_id: UUID,
        new_weights: Dict[CapabilityKey, float],
    ) -> Optional[Dossier]:
        """Functional rescore of an existing pipeline run's dossier."""
        with self._lock:
            state = self._runs.get(run_id)
            if not state or not state.dossier:
                return None

            rescored = rescore_dossier(state.dossier, new_weights)
            state.dossier = rescored
            self._dossiers_by_id[rescored.dossier_id] = rescored
            try:
                from cci.api.routers.dossier import register_dossier
                register_dossier(rescored, state.ceg_graph)
            except ImportError:
                pass
            return rescored


pipeline_service = PipelineService()
