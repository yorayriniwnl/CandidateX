from cci.domain.contracts import ScoringConfig
from cci.graph.builder import build_dossier_graph
from cci.live.acquisition import acquire_sources
from cci.live.contracts import LiveAnalysisRequest, MAX_REPOSITORIES, MAX_FILES, MAX_SECONDS
from cci.pipeline.orchestrator import execute_analysis_pipeline
from concurrent.futures import ThreadPoolExecutor
from cci.live.public_links import acquire_public_links
from cci.live.report import build_report


def analyze_resume(request: LiveAnalysisRequest):
    manifest = request.intake.manifest
    extracted = list(dict.fromkeys(url for key in ('linkedin_urls', 'coding_profile_urls', 'credential_urls',
        'deployment_urls', 'portfolio_urls', 'shared_document_urls', 'project_links', 'public_links') for url in getattr(manifest, key, [])))
    selected = request.external_urls if request.external_urls is not None else extracted
    with ThreadPoolExecutor(max_workers=2) as pool:
        github = pool.submit(acquire_sources, request.github_urls, request.github_identity)
        public = pool.submit(acquire_public_links, selected)
        evidence, ownership, sources = github.result()
        sources.extend(public.result())
    for url in extracted:
        if url not in selected:
            sources.append({'url': url, 'status': 'not_selected', 'detail': 'Extracted from the resume but not selected for this run.'})
    for url in manifest.github_urls:
        if url.lower() not in {s['url'].lower() for s in sources}:
            sources.append({'url': url, 'status': 'not_selected', 'detail': 'Extracted GitHub link not selected for this run.'})
    effective_jd = request.jd_text
    if not effective_jd and request.job_id:
        try:
            from cci.db.session import SessionLocal
            from cci.db.models.jobs import JobDescription
            with SessionLocal() as db:
                stored_jd = db.get(JobDescription, request.job_id)
                if stored_jd and stored_jd.raw_text:
                    effective_jd = stored_jd.raw_text
        except Exception:
            pass
    state = execute_analysis_pipeline(candidate_id=request.intake.candidate_id, role=request.role,
        jd_text=effective_jd, declared_claims=manifest.claimed_skills, custom_evidence=evidence, evidence_mode='live')
    if state.dossier is None:
        raise RuntimeError('The scoring pipeline could not produce a dossier.')
    limitations = [
        'Resume identity and GitHub account association are candidate declarations, not identity verification.',
        'Public GitHub evidence is fetched live. Static heuristic observations are not proof of mastery or job performance.',
        'Source reliability uses configured priors only; no simulated review outcomes are used.',
        'Verification/depth confidence factors are conservative prototype settings, not empirically calibrated probabilities.',
        'Recent-commit attribution is repository-level; it does not prove authorship of each inspected line.',
        'Public page text, profile metadata and certificate mentions do not increase capability scores. Issuer authentication and employment verification are not automated.',
        'Public links: up to 24 HTML/text/digital PDF pages, 512 KB each, 3 redirects; PDFs up to 5 pages. Login gates, image-only and script-only pages remain unresolved.',
        f'Bounded scan: {MAX_REPOSITORIES} repositories, {MAX_FILES} selected text files each. Acquisition runs without a tight time ceiling.',
        'The uploaded document and analysis are request-scoped. Download JSON to retain this result; refreshing clears the page.',
    ]
    dossier = state.dossier.model_copy(update={'ownership_assessments': ownership,
        'system_limitations': [*state.dossier.system_limitations, *limitations]})
    graph = build_dossier_graph(dossier)

    # Register in memory for instantaneous lookup
    try:
        from cci.api.routers.dossier import register_dossier
        register_dossier(dossier, graph)
    except Exception:
        pass

    # Persist to relational database for multi-session durability
    try:
        from uuid import UUID
        from cci.db.session import SessionLocal
        import cci.db.repository as repo
        org_id = UUID('00000000-0000-0000-0000-000000000001')
        with SessionLocal() as db:
            repo.save_dossier(db, dossier, org_id, custom_evidence=evidence)
            db.commit()
    except Exception:
        pass

    # Record SaaS quota usage and dispatch webhooks
    try:
        from uuid import UUID
        from cci.billing.service import billing_service
        from cci.webhooks.dispatcher import webhook_dispatcher
        org_id = UUID('00000000-0000-0000-0000-000000000001')
        billing_service.record_analysis_usage(org_id, dossier.candidate_id)
        webhook_dispatcher.dispatch_event(
            org_id,
            "candidate.analyzed",
            {
                "candidate_id": str(dossier.candidate_id),
                "rci": dossier.rci,
                "coverage": dossier.coverage,
                "role": dossier.role.value if hasattr(dossier.role, "value") else str(dossier.role),
                "status": "completed",
            },
        )
    except Exception:
        pass

    return {'intake': request.intake, 'dossier': dossier,
        'graph': graph.to_api_response(candidate_id=dossier.candidate_id, analysis_run_id=dossier.analysis_run_id),
        'graph_snapshot': graph.to_dict(), 'sources': sources, 'analysis': build_report(request.intake, sources), 'scoring_config': ScoringConfig(),
        'storage': 'database_and_memory', 'status': 'partial' if any(s['status'] != 'observed' for s in sources) or not evidence else 'completed'}
