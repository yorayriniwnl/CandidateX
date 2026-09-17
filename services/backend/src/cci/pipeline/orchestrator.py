"""Candidate Capability Intelligence (CCI) Pipeline Orchestrator.

Formal 10-Stage Pipeline Lifecycle:
1. PARSING_CV: Closed-world intake of candidate claims and manifests.
2. INGESTING_SOURCES: Validating and canonicalizing declared source URLs.
3. ANALYZING_ARTIFACTS: Static code, DB, test, DevOps, and deployment inspection.
4. BUILDING_EVIDENCE: Constructing immutable evidence records.
5. CALIBRATING_RELIABILITY: Beta-Binomial source family reliability updates.
6. ESTIMATING_OWNERSHIP: Heuristic authorship attribution.
7. COMPUTING_UNCERTAINTY: Cluster bootstrap CIs and Kish effective counts.
8. SCORING: Formal point estimates q_k and Role Capability Index (RCI).
9. PRIORITIZING_PROBES: Contradiction diagnostics D_k and information value ranking I_k.
10. GENERATING_DOSSIER: Heterogeneous CEG graph construction and dossier compilation.

CRITICAL INVARIANTS:
- Employer decision support only (never autonomous hire/reject).
- Candidate code is NEVER executed.
- Missing evidence -> UNKNOWN (never 0.0).
- Purely functional rescore without re-crawling.
- Repository URLs alone never manufacture capability or ownership evidence.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from cci.claims.corroborator import ExtractedClaimInput, corroborate_candidate_claims
from cci.contradictions.diagnostic import compute_contradiction_diagnostic
from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
    EvidenceRecord,
    NormalizedRequirement,
    OwnershipAssessment,
)
from cci.domain.enums import (
    AnalysisStage,
    CanonicalRole,
    CapabilityKey,
    GraphEdgeType,
    GraphNodeType,
)
from cci.dossier.builder import build_candidate_dossier, generate_interview_questions
from cci.graph.ceg import CandidateEvidenceGraph, CEGEdge, CEGNode
from cci.intake.canonicalizer import normalize_url
from cci.jobs.parser import extract_requirements_from_jd
from cci.probes.priority import compute_probe_priorities
from cci.scoring.capability import compute_capability_score
from cci.scoring.rci import compute_evidence_coverage, compute_rci
from cci.scoring.weights import (
    apply_expert_overrides,
    build_role_profile,
)
from cci.uncertainty.bootstrap import cluster_bootstrap_ci
from cci.uncertainty.diagnostics import compute_uncertainty_diagnostics


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StageProgress:
    stage: AnalysisStage
    label: str
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    details: Optional[str] = None


@dataclass
class PipelineExecutionState:
    analysis_run_id: UUID
    candidate_id: UUID
    role: CanonicalRole
    status: PipelineStatus = PipelineStatus.PENDING
    current_stage: Optional[AnalysisStage] = None
    stages: List[StageProgress] = field(default_factory=list)
    dossier: Optional[Dossier] = None
    ceg_graph: Optional[CandidateEvidenceGraph] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _init_stage_progress() -> List[StageProgress]:
    stage_labels = [
        (AnalysisStage.PARSING_CV, "1. Parse CV Manifest"),
        (AnalysisStage.INGESTING_SOURCES, "2. Canonicalize Sources"),
        (AnalysisStage.ANALYZING_ARTIFACTS, "3. Static Code & DB Intelligence"),
        (AnalysisStage.BUILDING_EVIDENCE, "4. Build Immutable Evidence"),
        (AnalysisStage.CALIBRATING_RELIABILITY, "5. Source Calibration"),
        (AnalysisStage.ESTIMATING_OWNERSHIP, "6. Ownership Attribution"),
        (AnalysisStage.COMPUTING_UNCERTAINTY, "7. Bootstrap Uncertainty"),
        (AnalysisStage.SCORING, "8. Capability Scoring & RCI"),
        (AnalysisStage.PRIORITIZING_PROBES, "9. Information Value & Probes"),
        (AnalysisStage.GENERATING_DOSSIER, "10. Compile CEG & Dossier"),
    ]
    return [StageProgress(stage=st, label=lbl) for st, lbl in stage_labels]


def execute_analysis_pipeline(
    candidate_id: UUID,
    role: CanonicalRole,
    jd_text: Optional[str] = None,
    cv_text: Optional[str] = None,
    repo_urls: Optional[List[str]] = None,
    declared_claims: Optional[List[str]] = None,
    custom_evidence: Optional[List[EvidenceRecord]] = None,
    expert_weight_overrides: Optional[Dict[CapabilityKey, float]] = None,
) -> PipelineExecutionState:
    """Execute the 10-stage analysis pipeline over explicitly observed evidence.

    ``repo_urls`` and CV text define the closed-world intake boundary, but they are
    not themselves capability evidence. Until a static analyzer/acquisition layer
    supplies ``custom_evidence``, capability estimates remain UNKNOWN and RCI is
    ``None``. This deliberately fails honest rather than fabricating plausible
    repository findings.
    """
    run_id = uuid4()
    state = PipelineExecutionState(
        analysis_run_id=run_id,
        candidate_id=candidate_id,
        role=role,
        status=PipelineStatus.RUNNING,
        stages=_init_stage_progress(),
    )

    def advance_stage(stage: AnalysisStage, details: Optional[str] = None):
        state.current_stage = stage
        now_str = datetime.now(timezone.utc).isoformat()
        for sp in state.stages:
            if sp.stage == stage:
                sp.status = "running"
                sp.started_at = now_str
                sp.details = details
            elif sp.status == "running":
                sp.status = "completed"
                sp.completed_at = now_str

    def complete_current_stage():
        now_str = datetime.now(timezone.utc).isoformat()
        for sp in state.stages:
            if sp.status == "running":
                sp.status = "completed"
                sp.completed_at = now_str

    try:
        # ----------------------------------------------------------------------
        # Stage 1: PARSING_CV
        # ----------------------------------------------------------------------
        advance_stage(AnalysisStage.PARSING_CV, "Extracting candidate manifest and declarations")
        discovered_claims: List[str] = list(declared_claims or [])
        if cv_text and not discovered_claims:
            lines = [ln.strip() for ln in cv_text.split("\n") if len(ln.strip()) > 15]
            discovered_claims.extend(lines[:5])

        # ----------------------------------------------------------------------
        # Stage 2: INGESTING_SOURCES
        # ----------------------------------------------------------------------
        advance_stage(AnalysisStage.INGESTING_SOURCES, "Validating URLs and closed-world boundary")
        valid_repos: List[str] = []
        if repo_urls:
            for url in repo_urls:
                try:
                    valid_repos.append(normalize_url(url))
                except Exception:
                    # Invalid/unapproved locations are not silently reintroduced.
                    continue

        # ----------------------------------------------------------------------
        # Stage 3: ANALYZING_ARTIFACTS
        # ----------------------------------------------------------------------
        raw_evidence: List[EvidenceRecord] = list(custom_evidence or [])
        if raw_evidence:
            analysis_detail = f"Using {len(raw_evidence)} explicitly supplied static evidence records"
        else:
            analysis_detail = (
                "No extracted analyzer evidence supplied; repository declarations remain unscored"
            )
        advance_stage(AnalysisStage.ANALYZING_ARTIFACTS, analysis_detail)

        # ----------------------------------------------------------------------
        # Stage 4: BUILDING_EVIDENCE
        # ----------------------------------------------------------------------
        advance_stage(AnalysisStage.BUILDING_EVIDENCE, f"Indexed {len(raw_evidence)} immutable records")

        # ----------------------------------------------------------------------
        # Stage 5: CALIBRATING_RELIABILITY
        # ----------------------------------------------------------------------
        advance_stage(
            AnalysisStage.CALIBRATING_RELIABILITY,
            "No source posterior update is inferred beyond observed evidence",
        )

        # ----------------------------------------------------------------------
        # Stage 6: ESTIMATING_OWNERSHIP
        # ----------------------------------------------------------------------
        # Ownership requires real contribution features from the acquisition layer.
        # A repository URL, account ownership, or candidate declaration is not enough.
        ownership_assessments: List[OwnershipAssessment] = []
        advance_stage(
            AnalysisStage.ESTIMATING_OWNERSHIP,
            "No verified contribution vectors supplied; ownership remains unassessed",
        )

        # ----------------------------------------------------------------------
        # Stage 7: COMPUTING_UNCERTAINTY
        # ----------------------------------------------------------------------
        advance_stage(AnalysisStage.COMPUTING_UNCERTAINTY, "Generating cluster bootstrap confidence intervals")
        capability_estimates: Dict[CapabilityKey, CapabilityEstimate] = {}
        for cap in CapabilityKey:
            ci_bounds = cluster_bootstrap_ci(raw_evidence, cap, n_resamples=200, seed=42)
            capability_estimates[cap] = compute_capability_score(
                evidence_records=raw_evidence,
                capability=cap,
                ci_bounds=ci_bounds,
            )

        # ----------------------------------------------------------------------
        # Stage 8: SCORING
        # ----------------------------------------------------------------------
        advance_stage(AnalysisStage.SCORING, "Computing Role Capability Index (RCI)")
        norm_reqs: List[NormalizedRequirement] = []
        if jd_text:
            norm_reqs = extract_requirements_from_jd(jd_text)

        profile = build_role_profile(norm_reqs, role)
        if expert_weight_overrides:
            profile = apply_expert_overrides(
                profile,
                expert_weight_overrides,
                justification="Expert adjustment",
            )

        role_weights = profile.softmax_weights
        rci_score = compute_rci(capability_estimates, role_weights)
        coverage_score = compute_evidence_coverage(capability_estimates, role_weights)

        # ----------------------------------------------------------------------
        # Stage 9: PRIORITIZING_PROBES
        # ----------------------------------------------------------------------
        advance_stage(AnalysisStage.PRIORITIZING_PROBES, "Computing contradiction diagnostics D_k and probe ranking")
        capability_conflicts: Dict[CapabilityKey, CapabilityConflict] = {
            cap: compute_contradiction_diagnostic(raw_evidence, cap)
            for cap in CapabilityKey
        }

        uncertainties = {
            cap: compute_uncertainty_diagnostics(est)
            for cap, est in capability_estimates.items()
        }

        probe_priorities = compute_probe_priorities(
            role_profile=profile,
            capabilities=capability_estimates,
            uncertainties=uncertainties,
            conflicts=capability_conflicts,
        )

        claim_inputs = [
            ExtractedClaimInput(
                claim_id=uuid4(),
                claim_text=claim_text,
                target_capability=CapabilityKey.BACKEND_ENGINEERING,
            )
            for claim_text in discovered_claims
        ]
        corroborated_claims = corroborate_candidate_claims(claim_inputs, raw_evidence)

        # ----------------------------------------------------------------------
        # Stage 10: GENERATING_DOSSIER
        # ----------------------------------------------------------------------
        advance_stage(AnalysisStage.GENERATING_DOSSIER, "Assembling heterogeneous CEG and immutable dossier")
        ceg = CandidateEvidenceGraph()
        for cap in CapabilityKey:
            cap_node_id = f"cap_{cap.value}"
            ceg.add_node(
                CEGNode(
                    node_id=cap_node_id,
                    node_type=GraphNodeType.CAPABILITY,
                    properties={"label": cap.value},
                )
            )

        for evidence in raw_evidence:
            evidence_id = str(evidence.evidence_id)
            cap_node_id = f"cap_{evidence.target_capability.value}"
            ceg.add_node(
                CEGNode(
                    node_id=evidence_id,
                    node_type=GraphNodeType.EVIDENCE,
                    properties={
                        "label": f"ev_{evidence.target_capability.value}",
                        "score": evidence.support_score,
                        "confidence": evidence.confidence,
                        "source_locator": evidence.provenance.get("source_locator", "unknown"),
                        "artifact_path": evidence.provenance.get("artifact_path", "unknown"),
                    },
                )
            )
            ceg.add_edge(
                CEGEdge(
                    edge_id=f"e_{evidence_id}_{cap_node_id}",
                    source_id=evidence_id,
                    target_id=cap_node_id,
                    edge_type=GraphEdgeType.SUPPORTS_CAPABILITY,
                    properties={"weight": evidence.confidence},
                )
            )

        dossier = build_candidate_dossier(
            candidate_id=candidate_id,
            analysis_run_id=run_id,
            role=role,
            capability_estimates=capability_estimates,
            capability_conflicts=capability_conflicts,
            role_requirements=norm_reqs,
            ownership_assessments=ownership_assessments,
            claims_corroboration=corroborated_claims,
            interview_probes=probe_priorities,
            evidence_records=raw_evidence,
            rci=rci_score,
            coverage=coverage_score,
            is_insufficient_evidence=(coverage_score < 0.30),
        )

        complete_current_stage()
        state.status = PipelineStatus.COMPLETED
        state.dossier = dossier
        state.ceg_graph = ceg
        state.updated_at = datetime.now(timezone.utc).isoformat()

    except Exception:
        import traceback

        state.status = PipelineStatus.FAILED
        state.error = traceback.format_exc()
        state.updated_at = datetime.now(timezone.utc).isoformat()

    return state


def rescore_dossier(
    dossier: Dossier,
    new_weights: Dict[CapabilityKey, float],
) -> Dossier:
    """Pure functional rescore of candidate dossier with expert weight overrides.

    CRITICAL INVARIANTS:
    - Avoids re-crawling or re-running static analyzers.
    - Operates strictly over already-observed capability point estimates q_k.
    - Missing evidence remains UNKNOWN and does not penalize observed capabilities.
    """
    profile = build_role_profile(dossier.role_requirements, dossier.role)
    overridden_profile = apply_expert_overrides(
        original_profile=profile,
        overridden_weights=new_weights,
        justification="Functional rescore override",
    )
    role_weights = overridden_profile.softmax_weights

    new_rci = compute_rci(
        capabilities=dossier.capability_estimates,
        role_weights=role_weights,
    )
    new_cov = compute_evidence_coverage(
        capabilities=dossier.capability_estimates,
        role_weights=role_weights,
    )

    uncertainties = {
        cap: compute_uncertainty_diagnostics(est)
        for cap, est in dossier.capability_estimates.items()
    }

    new_probes = compute_probe_priorities(
        role_profile=overridden_profile,
        capabilities=dossier.capability_estimates,
        uncertainties=uncertainties,
        conflicts=dossier.capability_conflicts,
    )

    new_questions = generate_interview_questions(
        probes=new_probes,
        capability_conflicts=dossier.capability_conflicts,
        evidence_records=[],
    )

    return Dossier(
        dossier_id=uuid4(),
        candidate_id=dossier.candidate_id,
        analysis_run_id=dossier.analysis_run_id,
        role=dossier.role,
        rci=new_rci,
        coverage=new_cov,
        is_insufficient_evidence=dossier.is_insufficient_evidence,
        capability_estimates=dossier.capability_estimates,
        capability_conflicts=dossier.capability_conflicts,
        role_requirements=dossier.role_requirements,
        ownership_assessments=dossier.ownership_assessments,
        claims_corroboration=dossier.claims_corroboration,
        interview_probes=new_probes,
        interview_questions=new_questions,
    )
