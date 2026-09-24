"""Database repository layer for Candidate Capability Intelligence (CCI).

Provides type-safe bridge between Pydantic domain contracts and SQLAlchemy models.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from cci.db import models
from cci.db.base import Base
from cci.domain.contracts import (
    CandidateManifest,
    Dossier,
    EvidenceRecord,
    NormalizedRequirement,
    RoleProfile,
    ScoringConfig,
)
from cci.domain.coverage_policy import is_coverage_sufficient
from cci.domain.enums import CanonicalRole
from cci.domain.evidence_families import build_fallback_evidence_family_identity
from cci.scoring.evidence_families import (
    compute_evidence_family_weights,
    family_weight_input_from_record,
)


def init_db(engine: Any) -> None:
    """Initializes all database tables from declarative models."""
    Base.metadata.create_all(bind=engine)


def save_organization(
    session: Session,
    name: str,
    slug: str,
    org_id: UUID | None = None,
    settings: dict[str, Any] | None = None,
) -> models.Organization:
    """Creates or updates an organization record."""
    stmt = select(models.Organization).where(models.Organization.slug == slug)
    existing = session.execute(stmt).scalar_one_or_none()
    if existing:
        return existing

    org = models.Organization(
        id=org_id or uuid4(),
        name=name,
        slug=slug,
        is_active=True,
        settings=settings or {},
    )
    session.add(org)
    session.flush()
    return org


def save_user(
    session: Session,
    organization_id: UUID,
    email: str,
    full_name: str,
    hashed_password: str = "pbkdf2_sha256$insecure_dev_hash",
    role: str = "interviewer",
    user_id: UUID | None = None,
) -> models.User:
    """Creates or returns an existing user."""
    stmt = select(models.User).where(models.User.email == email)
    existing = session.execute(stmt).scalar_one_or_none()
    if existing:
        return existing

    user = models.User(
        id=user_id or uuid4(),
        organization_id=organization_id,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        role=role,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def save_job_description(
    session: Session,
    organization_id: UUID,
    title: str,
    canonical_role: CanonicalRole,
    raw_text: str,
    job_id: UUID | None = None,
    role_profile: RoleProfile | None = None,
    requirements: list[NormalizedRequirement] | None = None,
) -> models.JobDescription:
    """Creates a job description along with its derived role profile and requirements."""
    jd = models.JobDescription(
        id=job_id or uuid4(),
        organization_id=organization_id,
        title=title,
        canonical_role=canonical_role.value
        if hasattr(canonical_role, "value")
        else str(canonical_role),
        raw_text=raw_text,
        is_active=True,
    )
    session.add(jd)
    session.flush()

    if role_profile:
        rp_entity = models.RoleProfileEntity(
            job_description_id=jd.id,
            canonical_role=role_profile.canonical_role.value
            if hasattr(role_profile.canonical_role, "value")
            else str(role_profile.canonical_role),
            raw_importances={
                k.value if hasattr(k, "value") else str(k): v
                for k, v in role_profile.raw_importances.items()
            },
            softmax_weights={
                k.value if hasattr(k, "value") else str(k): v
                for k, v in role_profile.softmax_weights.items()
            },
            temperature_used=role_profile.temperature_used,
            is_overridden=role_profile.is_overridden,
        )
        session.add(rp_entity)

    if requirements:
        for req in requirements:
            req_entity = models.RoleRequirement(
                id=req.requirement_id,
                job_description_id=jd.id,
                source_text=req.source_text,
                normalized_name=req.normalized_name,
                priority=req.priority.value
                if hasattr(req.priority, "value")
                else str(req.priority),
                capability_mappings=[
                    k.value if hasattr(k, "value") else str(k)
                    for k in req.capability_mappings
                ],
                technology_mentions=req.technology_mentions,
                mention_frequency=req.mention_frequency,
                semantic_specificity=req.semantic_specificity,
                mapping_confidence=req.mapping_confidence,
                mapping_method=req.mapping_method,
                ontology_version=req.ontology_version,
            )
            session.add(req_entity)

    session.flush()
    return jd


def save_candidate(
    session: Session,
    organization_id: UUID,
    manifest: CandidateManifest,
    candidate_id: UUID | None = None,
) -> models.Candidate:
    """Persists a candidate entity and its manifest-extracted identities and sources."""
    cid = candidate_id or uuid4()

    # Check if candidate already exists
    existing = session.get(models.Candidate, cid)
    if existing:
        return existing

    candidate = models.Candidate(
        id=cid,
        organization_id=organization_id,
        display_name=manifest.display_name,
        primary_email=manifest.email,
        manifest_data=manifest.model_dump(mode="json"),
        is_active=True,
    )
    session.add(candidate)
    session.flush()

    # Add GitHub identities
    for gh_url in manifest.github_urls:
        username = gh_url.rstrip("/").split("/")[-1]
        ident = models.Identity(
            candidate_id=candidate.id,
            platform="github",
            identifier=username,
            profile_url=gh_url,
            is_verified=False,
        )
        session.add(ident)

    # Add external sources
    all_sources = (
        [("github", u) for u in manifest.github_urls]
        + [("portfolio", u) for u in manifest.portfolio_urls]
        + [("deployment", u) for u in manifest.deployment_urls]
    )

    for fam, url in all_sources:
        src = models.CandidateSource(
            candidate_id=candidate.id,
            source_family=fam,
            source_url=url,
            state="declared",
        )
        session.add(src)

    session.flush()
    return candidate


def save_analysis_run(
    session: Session,
    candidate_id: UUID,
    target_role: CanonicalRole,
    organization_id: UUID,
    run_id: UUID | None = None,
    job_description_id: UUID | None = None,
    status: str = "completed",
    error_message: str | None = None,
    scoring_config: ScoringConfig | None = None,
) -> models.AnalysisRun:
    """Creates or updates an analysis run record."""
    rid = run_id or uuid4()
    existing = session.get(models.AnalysisRun, rid)
    if existing:
        return existing

    now = datetime.now(timezone.utc)
    run = models.AnalysisRun(
        id=rid,
        organization_id=organization_id,
        candidate_id=candidate_id,
        job_description_id=job_description_id,
        target_role=target_role.value
        if hasattr(target_role, "value")
        else str(target_role),
        status=status,
        error_message=error_message,
        config_version=(scoring_config or ScoringConfig()).version,
        started_at=now,
        completed_at=now,
    )
    session.add(run)
    session.flush()
    return run


def save_scoring_config(
    session: Session,
    config: ScoringConfig,
) -> models.ScoringConfigEntity:
    """Persists the active scoring parameter set, including family decay."""
    config_rows = list(
        session.execute(select(models.ScoringConfigEntity)).scalars().all()
    )
    entity = next((row for row in config_rows if row.version == config.version), None)
    if entity is None:
        entity = models.ScoringConfigEntity(version=config.version)
        session.add(entity)

    for row in config_rows:
        row.is_active = row.version == config.version

    entity.temperature = config.temperature
    entity.epsilon = config.epsilon
    entity.low_coverage_threshold = config.low_coverage_threshold
    entity.cluster_artifact_decay = config.cluster_artifact_decay
    entity.evidence_family_decay = config.evidence_family_decay
    entity.probe_alpha = config.probe_alpha
    entity.probe_beta = config.probe_beta
    entity.probe_gamma = config.probe_gamma
    entity.eta_parameters = {
        "jd_max_logit_adjustment": config.jd_max_logit_adjustment,
        "jd_adjustment_saturation": config.jd_adjustment_saturation,
        "jd_requirement_group_decay": config.jd_requirement_group_decay,
        "min_role_weight": config.min_role_weight,
        "max_role_weight": config.max_role_weight,
    }
    entity.lambda_decay = {
        capability.value: value for capability, value in config.lambda_decay.items()
    }
    entity.tau_saturation = {
        capability.value: value for capability, value in config.tau_saturation.items()
    }
    entity.is_active = True
    session.flush()
    return entity


def save_evidence_records(
    session: Session,
    analysis_run_id: UUID,
    evidence_records: list[EvidenceRecord],
    scoring_config: ScoringConfig,
) -> list[models.Evidence]:
    """Persists immutable evidence records and their capability links."""
    weight_inputs = [
        family_weight_input_from_record(record) for record in evidence_records
    ]
    family_weights = compute_evidence_family_weights(
        weight_inputs, decay=scoring_config.evidence_family_decay
    )
    entities: list[models.Evidence] = []
    for ev, weight_input in zip(evidence_records, weight_inputs):
        cf = ev.confidence_factors
        cap_val = (
            ev.target_capability.value
            if hasattr(ev.target_capability, "value")
            else str(ev.target_capability)
        )
        fam_val = (
            ev.source_family.value
            if hasattr(ev.source_family, "value")
            else str(ev.source_family)
        )
        if ev.evidence_family_id is None:
            family_identity = build_fallback_evidence_family_identity(
                source_family=ev.source_family,
                cluster_id=ev.cluster_id or ev.source_locator,
                artifact_path=ev.provenance.get("artifact_path"),
                capability=ev.target_capability,
                observation_type=ev.observation_type,
                fingerprint=ev.fingerprint,
            )
            family_basis = family_identity.basis
        else:
            family_basis = (
                ev.evidence_family_basis
                or ev.provenance.get("evidence_family_basis", {})
            )

        provenance = dict(ev.provenance)
        if ev.artifact_recency is not None:
            provenance["artifact_recency"] = ev.artifact_recency.model_dump(
                mode="json"
            )
        provenance["evidence_family_basis"] = family_basis
        if ev.negative_evidence_details is not None:
            provenance["negative_evidence_details"] = (
                ev.negative_evidence_details.model_dump(mode="json")
            )
        if ev.negative_evidence_qualification is not None:
            provenance["negative_evidence_qualification"] = (
                ev.negative_evidence_qualification
            )

        entity = models.Evidence(
            id=ev.evidence_id,
            analysis_run_id=analysis_run_id,
            artifact_id=ev.artifact_id,
            fingerprint=ev.fingerprint,
            evidence_family_id=weight_input.evidence_family_id,
            observation_type=ev.observation_type,
            source_family=fam_val,
            source_locator=ev.source_locator,
            immutable_revision=ev.immutable_revision,
            target_capability=cap_val,
            support_score=ev.technical_signal_strength,
            is_positive_support=ev.is_positive_support,
            factor_artifact_integrity=cf.artifact_integrity,
            factor_ownership_score=cf.ownership_score,
            factor_recency=cf.recency_factor,
            factor_verification_level=cf.verification_level,
            factor_depth_specificity=cf.depth_specificity,
            factor_source_reliability=cf.source_reliability,
            computed_confidence=ev.confidence,
            cluster_id=ev.cluster_id,
            provenance=provenance,
            analyzer_version=ev.provenance.get("analyzer_version", "1.0.0"),
        )
        session.add(entity)
        session.flush()

        # Link to capability
        link = models.EvidenceCapabilityLink(
            evidence_id=entity.id,
            capability_key=cap_val,
            effective_weight=family_weights[ev.evidence_id],
        )
        session.add(link)
        entities.append(entity)

    session.flush()
    return entities


def save_dossier(
    session: Session,
    dossier: Dossier,
    organization_id: UUID,
    custom_evidence: list[EvidenceRecord] | None = None,
    scoring_config: ScoringConfig | None = None,
) -> models.DossierSnapshot:
    """Persists a complete Dossier snapshot and its relational evaluation components."""
    cfg = scoring_config or ScoringConfig(
        version=dossier.versions.get(
            "scoring_config_version", ScoringConfig().version
        ),
        low_coverage_threshold=dossier.coverage_sufficiency_threshold,
    )
    if cfg.low_coverage_threshold != dossier.coverage_sufficiency_threshold:
        raise ValueError(
            "Dossier coverage threshold must match the active scoring configuration"
        )
    save_scoring_config(session, cfg)

    # Ensure Candidate exists or is attached
    cand = session.get(models.Candidate, dossier.candidate_id)
    if not cand:
        cand = models.Candidate(
            id=dossier.candidate_id,
            organization_id=organization_id,
            display_name=f"Candidate {str(dossier.candidate_id)[:8]}",
            primary_email=None,
            manifest_data={},
            is_active=True,
        )
        session.add(cand)
        session.flush()

    # Ensure AnalysisRun exists
    run = session.get(models.AnalysisRun, dossier.analysis_run_id)
    if not run:
        run = save_analysis_run(
            session=session,
            candidate_id=dossier.candidate_id,
            target_role=dossier.role,
            organization_id=organization_id,
            run_id=dossier.analysis_run_id,
            status="completed",
            scoring_config=cfg,
        )
    else:
        run.config_version = cfg.version

    # 1. Overall Score Entity
    observed_count = sum(
        1 for e in dossier.capability_estimates.values() if e.is_observed
    )
    score_entity = models.AnalysisScoreEntity(
        analysis_run_id=dossier.analysis_run_id,
        rci=dossier.rci,
        coverage=dossier.coverage,
        is_insufficient_evidence=dossier.is_insufficient_evidence,
        observed_capabilities_count=observed_count,
        scoring_config_version=dossier.versions.get("scoring_config_version", ScoringConfig().version),
    )
    session.add(score_entity)

    # 2. Capability Estimates & Uncertainties
    for cap_key, est in dossier.capability_estimates.items():
        ck_str = cap_key.value if hasattr(cap_key, "value") else str(cap_key)
        est_entity = models.CapabilityEstimateEntity(
            analysis_run_id=dossier.analysis_run_id,
            capability_key=ck_str,
            estimate=est.estimate,
            is_observed=est.is_observed,
            effective_evidence_count=est.effective_evidence_count,
            raw_evidence_count=est.raw_evidence_count,
            cluster_count=est.cluster_count,
            standard_error=est.standard_error,
            dispersion=est.dispersion,
            ci_lower=est.ci_lower,
            ci_upper=est.ci_upper,
            coverage_k=est.coverage_k,
        )
        session.add(est_entity)

        ci_w = (
            (est.ci_upper - est.ci_lower)
            if (est.ci_upper is not None and est.ci_lower is not None)
            else 0.0
        )
        unc_entity = models.CapabilityUncertaintyEntity(
            analysis_run_id=dossier.analysis_run_id,
            capability_key=ck_str,
            epistemic_uncertainty=est.standard_error * 1.96,
            ci_width=ci_w,
            is_low_coverage=not is_coverage_sufficient(
                est.coverage_k, threshold=cfg.low_coverage_threshold
            ),
        )
        session.add(unc_entity)

    # 3. Capability Conflicts
    for cap_key, conf in dossier.capability_conflicts.items():
        ck_str = cap_key.value if hasattr(cap_key, "value") else str(cap_key)
        conf_entity = models.CapabilityConflictEntity(
            analysis_run_id=dossier.analysis_run_id,
            capability_key=ck_str,
            positive_support_sum=conf.positive_support_sum,
            negative_support_sum=conf.negative_support_sum,
            contradiction_diagnostic=conf.contradiction_diagnostic,
            has_meaningful_conflict=conf.has_meaningful_conflict,
            triggering_evidence_ids=[str(uid) for uid in conf.triggering_evidence_ids],
        )
        session.add(conf_entity)

    # 4. Interview Probes & Questions
    for probe in dossier.interview_probes:
        ck_str = (
            probe.capability_key.value
            if hasattr(probe.capability_key, "value")
            else str(probe.capability_key)
        )
        probe_entity = models.InterviewProbePriority(
            analysis_run_id=dossier.analysis_run_id,
            capability_key=ck_str,
            rank=probe.rank,
            priority_score=probe.priority_score,
            role_weight=probe.role_weight,
            coverage_gap_term=probe.coverage_gap_term,
            uncertainty_term=probe.uncertainty_term,
            contradiction_term=probe.contradiction_term,
        )
        session.add(probe_entity)
        session.flush()

        # Add corresponding questions
        matching_questions = [
            q
            for q in dossier.interview_questions
            if q.target_capability == probe.capability_key
        ]
        for q in matching_questions:
            q_entity = models.InterviewQuestionEntity(
                id=q.question_id,
                probe_priority_id=probe_entity.id,
                target_capability=ck_str,
                question_text=q.question_text,
                rationale=q.rationale,
                verification_guidance=q.verification_guidance,
                grounding_evidence_ids=[str(e) for e in q.grounding_evidence_ids],
                suggested_followups=q.suggested_followups,
            )
            session.add(q_entity)

    # 5. Optional Evidence Records persistence
    if custom_evidence:
        save_evidence_records(
            session,
            dossier.analysis_run_id,
            custom_evidence,
            scoring_config=cfg,
        )

    # 6. Dossier Snapshot and Items
    snapshot = models.DossierSnapshot(
        id=dossier.dossier_id,
        analysis_run_id=dossier.analysis_run_id,
        rci=dossier.rci,
        coverage=dossier.coverage,
        is_insufficient_evidence=dossier.is_insufficient_evidence,
        summary_payload=dossier.model_dump(mode="json"),
        limitations=dossier.system_limitations,
        version_metadata=dossier.versions,
    )
    session.add(snapshot)
    session.flush()

    # Create structured dossier sections
    sec_order = 0
    # Strengths section
    strong_caps = [
        (k, est)
        for k, est in dossier.capability_estimates.items()
        if est.is_observed and est.estimate is not None and est.estimate >= 70.0
    ]
    if strong_caps:
        strong_md = "\n".join(
            [
                f"- **{k.value}**: Score {est.estimate:.1f}/100 (Coverage: {est.coverage_k * 100:.0f}%)"
                for k, est in strong_caps
            ]
        )
        item = models.DossierItem(
            dossier_snapshot_id=snapshot.id,
            section_type="strong_area",
            title="Demonstrated Technical Strengths",
            body_markdown=strong_md,
            referenced_evidence_ids=[],
            item_order=sec_order,
        )
        session.add(item)
        sec_order += 1

    # Uncertain / Gaps section
    gap_caps = [
        (k, est)
        for k, est in dossier.capability_estimates.items()
        if not est.is_observed
        or not is_coverage_sufficient(
            est.coverage_k, threshold=cfg.low_coverage_threshold
        )
    ]
    if gap_caps:
        gap_md = "\n".join(
            [
                f"- **{k.value}**: Coverage {est.coverage_k * 100:.0f}% (State: {'UNKNOWN' if not est.is_observed else 'Low Coverage'})"
                for k, est in gap_caps
            ]
        )
        item = models.DossierItem(
            dossier_snapshot_id=snapshot.id,
            section_type="uncertain_area",
            title="Uncertainty & Evidence Gaps",
            body_markdown=gap_md,
            referenced_evidence_ids=[],
            item_order=sec_order,
        )
        session.add(item)
        sec_order += 1

    session.flush()
    return snapshot


def get_candidate_by_id(
    session: Session, candidate_id: UUID
) -> models.Candidate | None:
    """Retrieves a candidate by UUID."""
    return session.get(models.Candidate, candidate_id)


def list_candidates(
    session: Session, organization_id: UUID | None = None
) -> list[models.Candidate]:
    """Lists candidates, optionally scoped by organization."""
    stmt = select(models.Candidate)
    if organization_id:
        stmt = stmt.where(models.Candidate.organization_id == organization_id)
    stmt = stmt.order_by(models.Candidate.created_at.desc())
    return list(session.execute(stmt).scalars().all())


def list_jobs(
    session: Session, organization_id: UUID | None = None
) -> list[models.JobDescription]:
    """Lists active job descriptions."""
    stmt = select(models.JobDescription)
    if organization_id:
        stmt = stmt.where(models.JobDescription.organization_id == organization_id)
    stmt = stmt.order_by(models.JobDescription.created_at.desc())
    return list(session.execute(stmt).scalars().all())


def get_dossier_by_candidate_id(session: Session, candidate_id: UUID) -> Dossier | None:
    """Retrieves and reconstructs the latest complete Dossier for a candidate from DB."""
    stmt = (
        select(models.AnalysisRun)
        .where(models.AnalysisRun.candidate_id == candidate_id)
        .where(models.AnalysisRun.status == "completed")
        .order_by(desc(models.AnalysisRun.completed_at))
    )
    run = session.execute(stmt).scalars().first()
    if not run:
        return None

    snap_stmt = select(models.DossierSnapshot).where(
        models.DossierSnapshot.analysis_run_id == run.id
    )
    snapshot = session.execute(snap_stmt).scalars().first()
    if not snapshot or not snapshot.summary_payload:
        return None

    try:
        return Dossier.model_validate(snapshot.summary_payload)
    except Exception:
        return None
