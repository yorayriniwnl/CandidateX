from cci.domain.contracts import ScoringConfig
from cci.graph.builder import build_dossier_graph
from cci.live.acquisition import acquire_sources
from cci.live.contracts import LiveAnalysisRequest, MAX_REPOSITORIES, MAX_FILES, MAX_SECONDS
from cci.pipeline.orchestrator import execute_analysis_pipeline
from cci.uncertainty.summary import build_analysis_confidence
from concurrent.futures import ThreadPoolExecutor
from cci.live.public_links import acquire_public_links
from cci.live.report import build_report, build_source_health


def analyze_resume(request: LiveAnalysisRequest):
    manifest = request.intake.manifest
    extracted = list(dict.fromkeys(url for key in ('linkedin_urls', 'coding_profile_urls', 'credential_urls',
        'deployment_urls', 'portfolio_urls', 'project_links') for url in getattr(manifest, key)))
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
    state = execute_analysis_pipeline(candidate_id=request.intake.candidate_id, role=request.role,
        jd_text=request.jd_text, declared_claims=manifest.claimed_skills, custom_evidence=evidence, evidence_mode='live')
    if state.dossier is None:
        raise RuntimeError('The scoring pipeline could not produce a dossier.')
    limitations = [
        'Resume identity and GitHub account association are candidate declarations, not identity verification.',
        'Public GitHub evidence is fetched live. Static heuristic observations are not proof of mastery or job performance.',
        'Source reliability uses configured priors only; no simulated review outcomes are used.',
        'Verification/depth confidence factors are conservative correlation-aware heuristics, not empirically calibrated probabilities.',
        'Recent-commit attribution is repository-level; it does not prove authorship of each inspected line.',
        'Public page text, profile metadata and certificate mentions do not increase capability scores. Issuer authentication and employment verification are not automated.',
        'Public links: up to 24 HTML/text/digital PDF pages, 512 KB each, 3 redirects; PDFs up to 5 pages. Login gates, image-only and script-only pages remain unresolved.',
        f'Bounded scan: {MAX_REPOSITORIES} repositories, {MAX_FILES} selected text files each, {MAX_SECONDS}s acquisition budget.',
        'The uploaded document and analysis are request-scoped. Download JSON to retain this result; refreshing clears the page.',
    ]
    dossier = state.dossier.model_copy(update={'ownership_assessments': ownership,
        'system_limitations': [*state.dossier.system_limitations, *limitations]})
    source_health = build_source_health(sources)
    analysis_confidence = build_analysis_confidence(
        capabilities=dossier.capability_estimates,
        evidence_records=dossier.evidence_records,
        role_weights=dossier.role_weights,
        conflicts=dossier.capability_conflicts,
        role_fit=dossier.role_fit,
        source_failures=source_health['failed_sources'],
        source_unscanned=(source_health['not_selected_sources']
                          + source_health['not_scanned_sources']),
    )
    dossier = dossier.model_copy(update={'analysis_confidence': analysis_confidence})
    graph = build_dossier_graph(dossier)
    analysis = build_report(request.intake, sources, source_health=source_health)
    analysis['analysis_confidence'] = analysis_confidence.model_dump(mode='json')
    analysis['role_fit'] = dossier.role_fit.model_dump(mode='json')
    if dossier.role_fit.critical_gaps:
        analysis['next_steps'] = list(dict.fromkeys([
            *analysis['next_steps'],
            'Resolve mandatory role gaps before treating the capability snapshot as role-ready.',
        ]))
    return {'intake': request.intake, 'dossier': dossier,
        'graph': graph.to_api_response(candidate_id=dossier.candidate_id, analysis_run_id=dossier.analysis_run_id),
        'graph_snapshot': graph.to_dict(), 'sources': sources, 'analysis': analysis, 'scoring_config': ScoringConfig(),
        'source_health': source_health, 'storage': 'request_only',
        'status': 'partial' if source_health['is_partial'] or not evidence else 'completed'}
