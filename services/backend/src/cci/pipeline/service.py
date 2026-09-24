"""Pipeline Service for executing and tracking CCI analysis runs with multi-tenancy (Fix 29)."""

from threading import Lock
from uuid import UUID

from cci.domain.contracts import Dossier, EvidenceRecord, ScoringConfig
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.graph.builder import build_dossier_graph
from cci.pipeline.orchestrator import (
    PipelineExecutionState,
    execute_analysis_pipeline,
    rescore_dossier,
)


class PipelineService:
    """Thread-safe registry for CCI pipeline runs and dossier caching."""

    def __init__(self) -> None:
        self._runs: dict[UUID, PipelineExecutionState] = {}
        self._dossiers_by_id: dict[UUID, Dossier] = {}
        self._lock = Lock()

    def start_pipeline(
        self,
        candidate_id: UUID,
        role: CanonicalRole,
        jd_text: str | None = None,
        cv_text: str | None = None,
        repo_urls: list[str] | None = None,
        declared_claims: list[str] | None = None,
        custom_evidence: list[EvidenceRecord] | None = None,
        expert_weight_overrides: dict[CapabilityKey, float] | None = None,
        evidence_mode: str = "provided",
        scenario: str | None = None,
        scoring_config: ScoringConfig | None = None,
        organization_id: UUID | None = None,
    ) -> PipelineExecutionState:
        """Executes the analysis pipeline and stores execution state bound to tenant."""
        state = execute_analysis_pipeline(
            candidate_id=candidate_id,
            role=role,
            jd_text=jd_text,
            cv_text=cv_text,
            repo_urls=repo_urls,
            declared_claims=declared_claims,
            custom_evidence=custom_evidence,
            expert_weight_overrides=expert_weight_overrides,
            evidence_mode=evidence_mode,
            scenario=scenario,
            scoring_config=scoring_config,
            organization_id=organization_id,
        )

        with self._lock:
            self._runs[state.analysis_run_id] = state
            if state.dossier:
                self._dossiers_by_id[state.dossier.dossier_id] = state.dossier
                try:
                    from cci.api.routers.dossier import register_dossier

                    register_dossier(state.dossier, state.ceg_graph, organization_id=organization_id)
                except ImportError:
                    pass

        return state

    def get_pipeline_state(
        self, run_id: UUID, organization_id: UUID | None = None
    ) -> PipelineExecutionState | None:
        """Retrieves pipeline state by run ID, enforcing organization scoping if provided."""
        with self._lock:
            state = self._runs.get(run_id)
            if state and organization_id is not None:
                if getattr(state, "organization_id", None) is not None and state.organization_id != organization_id:
                    return None
            return state

    def get_dossier(
        self, dossier_id: UUID, organization_id: UUID | None = None
    ) -> Dossier | None:
        """Retrieves Dossier by dossier ID."""
        with self._lock:
            return self._dossiers_by_id.get(dossier_id)

    def rescore_run(
        self,
        run_id: UUID,
        new_weights: dict[CapabilityKey, float],
        justification: str = "Research demonstration weight override",
        organization_id: UUID | None = None,
    ) -> Dossier | None:
        """Functional rescore of an existing pipeline run's dossier."""
        with self._lock:
            state = self._runs.get(run_id)
            if not state or not state.dossier:
                return None

            if organization_id is not None:
                if getattr(state, "organization_id", None) is not None and state.organization_id != organization_id:
                    return None

            rescored = rescore_dossier(state.dossier, new_weights, justification)
            state.ceg_graph = build_dossier_graph(rescored)
            state.dossier = rescored
            self._dossiers_by_id[rescored.dossier_id] = rescored
            try:
                from cci.api.routers.dossier import register_dossier

                register_dossier(rescored, state.ceg_graph, organization_id=getattr(state, "organization_id", None))
            except ImportError:
                pass
            return rescored

    def evict_candidate(self, candidate_id: UUID) -> None:
        """Evicts in-memory pipeline states and dossiers for a deleted candidate."""
        with self._lock:
            to_del_runs = [rid for rid, s in self._runs.items() if s.candidate_id == candidate_id]
            for rid in to_del_runs:
                self._runs.pop(rid, None)
            to_del_dossiers = [did for did, d in self._dossiers_by_id.items() if d.candidate_id == candidate_id]
            for did in to_del_dossiers:
                self._dossiers_by_id.pop(did, None)


pipeline_service = PipelineService()
