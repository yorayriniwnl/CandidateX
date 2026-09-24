"""Candidate Capability Intelligence (CCI) Pipeline Orchestrator.

Formal 10-Stage Pipeline Lifecycle:
1. PARSING_CV: Closed-world intake of candidate claims and manifests.
2. INGESTING_SOURCES: Validating and canonicalizing declared source URLs.
3. ANALYZING_ARTIFACTS: Static code, DB, test, DevOps, and deployment inspection.
4. BUILDING_EVIDENCE: Constructing immutable evidence records.
5. CALIBRATING_RELIABILITY: Beta-Binomial source family reliability updates.
6. ESTIMATING_OWNERSHIP: Heuristic authorship attribution.
7. COMPUTING_UNCERTAINTY: Cluster bootstrap CIs and Kish effective counts.
8. SCORING: Formal point estimates q_k and observed-only capability index.
9. PRIORITIZING_PROBES: Contradiction diagnostics D_k and information value ranking I_k.
10. GENERATING_DOSSIER: Heterogeneous CEG graph construction and dossier compilation.

CRITICAL INVARIANTS:
- Employer decision support only (never autonomous hire/reject).
- Candidate code is NEVER executed.
- Missing evidence -> UNKNOWN (never 0.0).
- Purely functional rescore without re-crawling.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from collections.abc import Sequence
from uuid import UUID, uuid4

from cci.contradictions.expectations import ObservableClaimExpectation

from cci.claims.corroborator import ExtractedClaimInput, corroborate_candidate_claims
from cci.contradictions.diagnostic import compute_contradiction_diagnostic
from cci.domain.coverage_policy import is_coverage_sufficient
from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NormalizedRequirement,
    OwnershipAssessment,
    ScoringConfig,
)
from cci.domain.enums import (
    AnalysisStage,
    CanonicalRole,
    CapabilityKey,
    EvidenceMode,
    GraphEdgeType,
    GraphNodeType,
    SourceFamily,
)
from cci.dossier.builder import build_candidate_dossier, generate_interview_questions
from cci.graph.ceg import CandidateEvidenceGraph
from cci.graph.builder import build_dossier_graph
from cci.intake.canonicalizer import normalize_url
from cci.jobs.parser import extract_requirements_from_jd
from cci.probes.priority import compute_probe_priorities
from cci.scoring.capability import (
    compute_capability_score,
)
from cci.scoring.evidence_families import compute_record_family_weights
from cci.scoring.ownership import (
    estimate_repository_ownership,
)
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
    started_at: str | None = None
    completed_at: str | None = None
    details: str | None = None


@dataclass
class PipelineExecutionState:
    analysis_run_id: UUID
    candidate_id: UUID
    role: CanonicalRole
    status: PipelineStatus = PipelineStatus.PENDING
    current_stage: AnalysisStage | None = None
    stages: list[StageProgress] = field(default_factory=list)
    dossier: Dossier | None = None
    ceg_graph: CandidateEvidenceGraph | None = None
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def _init_stage_progress() -> list[StageProgress]:
    stage_labels = [
        (AnalysisStage.PARSING_CV, "1. Parse CV Manifest"),
        (AnalysisStage.INGESTING_SOURCES, "2. Canonicalize Sources"),
        (AnalysisStage.ANALYZING_ARTIFACTS, "3. Static Code & DB Intelligence"),
        (AnalysisStage.BUILDING_EVIDENCE, "4. Build Immutable Evidence"),
        (AnalysisStage.CALIBRATING_RELIABILITY, "5. Source Calibration"),
        (AnalysisStage.ESTIMATING_OWNERSHIP, "6. Ownership Attribution"),
        (AnalysisStage.COMPUTING_UNCERTAINTY, "7. Bootstrap Uncertainty"),
        (AnalysisStage.SCORING, "8. Capability Scoring & Observed Index"),
        (AnalysisStage.PRIORITIZING_PROBES, "9. Information Value & Probes"),
        (AnalysisStage.GENERATING_DOSSIER, "10. Compile CEG & Dossier"),
    ]
    return [StageProgress(stage=st, label=lbl) for st, lbl in stage_labels]


def execute_analysis_pipeline(
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
    analysis_run_id: UUID | None = None,
    observable_expectations: Sequence[ObservableClaimExpectation] = (),
) -> PipelineExecutionState:
    """Executes the complete 10-stage Candidate Capability Intelligence analysis pipeline."""
    mode = EvidenceMode(evidence_mode)
    raw_evidence = list(custom_evidence or [])
    if mode == EvidenceMode.LIVE:
        for ev in raw_evidence:
            if ev.provenance.get("synthetic") is True or getattr(ev, "synthetic", False):
                raise ValueError(
                    f"Synthetic evidence record '{ev.evidence_id}' must never appear in a live candidate analysis run."
                )

    cfg = scoring_config or ScoringConfig()
    run_id = analysis_run_id or uuid4()
    state = PipelineExecutionState(
        analysis_run_id=run_id,
        candidate_id=candidate_id,
        role=role,
        status=PipelineStatus.RUNNING,
        stages=_init_stage_progress(),
    )

    def advance_stage(stage: AnalysisStage, _description: str) -> None:
        state.current_stage = stage
        now_str = datetime.now(timezone.utc).isoformat()
        for sp in state.stages:
            if sp.stage == stage:
                sp.status = "running"
                sp.started_at = now_str
                sp.details = _description
            elif sp.status == "running":
                sp.status = "completed"
                sp.completed_at = now_str

    def complete_current_stage() -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        for sp in state.stages:
            if sp.status == "running":
                sp.status = "completed"
                sp.completed_at = now_str

    try:
        # ----------------------------------------------------------------------
        # Stage 1: PARSING_CV
        # ----------------------------------------------------------------------
        advance_stage(
            AnalysisStage.PARSING_CV, "Extracting candidate manifest and declarations"
        )
        discovered_claims: list[str] = declared_claims or []
        if cv_text and not discovered_claims:
            # Simple sentence splitting for extracted claims from CV text
            lines = [ln.strip() for ln in cv_text.split("\n") if len(ln.strip()) > 15]
            discovered_claims.extend(lines[:5])

        # ----------------------------------------------------------------------
        # Stage 2: INGESTING_SOURCES
        # ----------------------------------------------------------------------
        advance_stage(
            AnalysisStage.INGESTING_SOURCES, "Validating URLs and closed-world boundary"
        )
        valid_repos: list[str] = []
        if repo_urls:
            for u in repo_urls:
                try:
                    norm = normalize_url(u)
                    valid_repos.append(str(norm))
                except Exception:
                    valid_repos.append(u)

        # ----------------------------------------------------------------------
        # Stage 3: ANALYZING_ARTIFACTS
        # ----------------------------------------------------------------------
        advance_stage(
            AnalysisStage.ANALYZING_ARTIFACTS,
            "Static code, DB, and deployment analysis",
        )
        # No source adapter is implied by a URL. Only supplied observations are scored.
        raw_evidence = list(custom_evidence or [])
        family_weights = compute_record_family_weights(
            raw_evidence, decay=cfg.evidence_family_decay
        )
        if not raw_evidence:
            state.stages[2].details = "No registered observations supplied; capabilities remain unknown."
        else:
            state.stages[2].details = f"Scoring {len(raw_evidence)} {evidence_mode} observations; candidate code not executed."

        # ----------------------------------------------------------------------
        # Stage 4: BUILDING_EVIDENCE
        # ----------------------------------------------------------------------
        advance_stage(
            AnalysisStage.BUILDING_EVIDENCE,
            f"Indexed {len(raw_evidence)} immutable records",
        )

        # ----------------------------------------------------------------------
        # Stage 5: CALIBRATING_RELIABILITY
        # ----------------------------------------------------------------------
        advance_stage(
            AnalysisStage.CALIBRATING_RELIABILITY,
            "Using reliability factors attached to supplied observations; demo counts are simulated.",
        )

        # ----------------------------------------------------------------------
        # Stage 6: ESTIMATING_OWNERSHIP
        # ----------------------------------------------------------------------
        advance_stage(
            AnalysisStage.ESTIMATING_OWNERSHIP,
            "Computing ownership attribution vectors",
        )
        ownership_assessments: list[OwnershipAssessment] = []
        for ev in raw_evidence:
            if ev.source_family != SourceFamily.GITHUB:
                continue
            ownership_assessments.append(OwnershipAssessment(
                repository_url=ev.source_locator, candidate_identifier=str(candidate_id),
                ownership_score=ev.confidence_factors.ownership_score,
                model_name="SuppliedEvidenceOwnership",
                limitations=["Simulated attribution" if evidence_mode == "synthetic" else "Attribution supplied with evidence; not independently verified"],
            ))

        # ----------------------------------------------------------------------
        # Stage 7: COMPUTING_UNCERTAINTY
        # ----------------------------------------------------------------------
        advance_stage(
            AnalysisStage.COMPUTING_UNCERTAINTY,
            "Generating cluster bootstrap confidence intervals",
        )
        cap_records: dict[CapabilityKey, list[EvidenceRecord]] = {}
        for ev in raw_evidence:
            cap_records.setdefault(ev.target_capability, []).append(ev)

        capability_estimates: dict[CapabilityKey, CapabilityEstimate] = {}
        for cap in CapabilityKey:
            ci_bounds = cluster_bootstrap_ci(
                raw_evidence,
                cap,
                n_resamples=200,
                seed=42,
                config=cfg,
                family_weights=family_weights,
            )

            estimate = compute_capability_score(
                evidence_records=raw_evidence,
                capability=cap,
                config=cfg,
                ci_bounds=ci_bounds,
                family_weights=family_weights,
            )
            capability_estimates[cap] = estimate

        # ----------------------------------------------------------------------
        # Stage 8: SCORING
        # ----------------------------------------------------------------------
        advance_stage(AnalysisStage.SCORING, "Computing observed-only capability index")
        # Parse JD requirements or use canonical profile
        norm_reqs: list[NormalizedRequirement] = []
        if jd_text:
            extracted_reqs = extract_requirements_from_jd(jd_text)
            norm_reqs = extracted_reqs

        profile = build_role_profile(norm_reqs, role)
        if expert_weight_overrides:
            profile = apply_expert_overrides(
                profile, expert_weight_overrides, justification="Expert adjustment"
            )

        role_weights = profile.softmax_weights
        rci_score = compute_rci(capability_estimates, role_weights)
        coverage_score = compute_evidence_coverage(capability_estimates, role_weights)

        # ----------------------------------------------------------------------
        # Stage 9: PRIORITIZING_PROBES
        # ----------------------------------------------------------------------
        advance_stage(
            AnalysisStage.PRIORITIZING_PROBES,
            "Computing contradiction diagnostics D_k and probe ranking",
        )
        capability_conflicts: dict[CapabilityKey, CapabilityConflict] = {}
        for cap in CapabilityKey:
            capability_conflicts[cap] = compute_contradiction_diagnostic(
                raw_evidence, cap, config=cfg, family_weights=family_weights
            )

        uncertainties = {
            cap: compute_uncertainty_diagnostics(est, config=cfg)
            for cap, est in capability_estimates.items()
        }

        probe_priorities = compute_probe_priorities(
            role_profile=profile,
            capabilities=capability_estimates,
            uncertainties=uncertainties,
            conflicts=capability_conflicts,
        )

        # Only map claims recognized by the controlled ontology; never guess a capability.
        claim_inputs = []
        for claim in discovered_claims:
            for requirement in extract_requirements_from_jd(f"Skill: {claim}" if evidence_mode == "live" else claim):
                if not requirement.technology_mentions:
                    continue
                for cap in requirement.capability_mappings:
                    claim_inputs.append(ExtractedClaimInput(
                        claim_id=uuid4(), claim_text=claim, target_capability=cap,
                        technology_keywords=requirement.technology_mentions if evidence_mode == "live" else []))
        for exp in observable_expectations:
            keywords = [exp.technology] if exp.technology else []
            claim_inputs.append(ExtractedClaimInput(
                claim_id=uuid4(),
                claim_text=exp.claim_text,
                target_capability=exp.target_capability,
                technology_keywords=keywords,
                claim_reference=exp.claim_reference,
            ))
        corroborated_claims = corroborate_candidate_claims(
            claim_inputs,
            raw_evidence,
            strict_technology_match=evidence_mode == "live",
            config=cfg,
            family_weights=family_weights,
        )
        advance_stage(AnalysisStage.GENERATING_DOSSIER, "Link evidence, sources, artifacts, requirements, and interview questions")

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
            is_insufficient_evidence=not is_coverage_sufficient(
                coverage_score, threshold=cfg.low_coverage_threshold
            ),
            coverage_sufficiency_threshold=cfg.low_coverage_threshold,
        )

        dossier_versions = dict(dossier.versions)
        dossier_versions["scoring_config_version"] = cfg.version
        dossier = dossier.model_copy(update={
            "evidence_records": raw_evidence, "evidence_mode": mode.value,
            "scenario": scenario, "role_weights": role_weights,
            "versions": dossier_versions,
            "system_limitations": dossier.system_limitations + [
                "Synthetic observations for method demonstration; no real candidate assessment." if evidence_mode == "synthetic"
                else "Only registered observations are scored; URL and CV text alone do not establish technical capability.",
                "Prototype role weights include canonical-role priors; JD mapping uses a controlled synonym ontology.",
                "Confidence intervals require at least two independent project clusters.",
            ],
        })
        ceg = build_dossier_graph(dossier)
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
    new_weights: dict[CapabilityKey, float],
    justification: str = "Research demonstration weight override",
) -> Dossier:
    """Pure functional rescore of candidate dossier with expert weight overrides.

    CRITICAL INVARIANTS:
    - Avoids re-crawling or re-running static analyzers.
    - Operates strictly over already-observed capability point estimates q_k.
    - Missing or insufficiently attributed evidence remains UNKNOWN.
    """
    cfg = ScoringConfig(
        version=dossier.versions.get("scoring_config_version", ScoringConfig().version),
        low_coverage_threshold=dossier.coverage_sufficiency_threshold,
    )
    profile = build_role_profile(dossier.role_requirements, dossier.role)
    if dossier.role_weights:
        profile = profile.model_copy(update={"softmax_weights": dossier.role_weights})
    overridden_profile = apply_expert_overrides(
        original_profile=profile,
        overridden_weights=new_weights,
        justification=justification,
    )
    role_weights = overridden_profile.softmax_weights

    # Recompute RCI over capabilities with sufficient attributed coverage.
    new_rci = compute_rci(
        capabilities=dossier.capability_estimates,
        role_weights=role_weights,
        config=cfg,
    )
    new_cov = compute_evidence_coverage(
        capabilities=dossier.capability_estimates,
        role_weights=role_weights,
    )

    # Recompute probe priorities
    uncertainties = {
        cap: compute_uncertainty_diagnostics(est, config=cfg)
        for cap, est in dossier.capability_estimates.items()
    }

    new_probes = compute_probe_priorities(
        role_profile=overridden_profile,
        capabilities=dossier.capability_estimates,
        uncertainties=uncertainties,
        conflicts=dossier.capability_conflicts,
    )

    # Re-generate interview questions with updated rankings
    new_questions = generate_interview_questions(
        probes=new_probes,
        capability_conflicts=dossier.capability_conflicts,
        evidence_records=dossier.evidence_records,
    )

    # A new snapshot retains all evidence, limitations and prior override history.
    return dossier.model_copy(update={
        "dossier_id": uuid4(), "generated_at": datetime.now(timezone.utc),
        "rci": new_rci, "coverage": new_cov,
        "is_insufficient_evidence": not is_coverage_sufficient(
            new_cov, threshold=cfg.low_coverage_threshold
        ),
        "role_weights": role_weights, "interview_probes": new_probes,
        "interview_questions": new_questions,
        "override_history": [*dossier.override_history, {
            **(overridden_profile.override_audit or {}),
            "previous_dossier_id": str(dossier.dossier_id),
        }],
    })
