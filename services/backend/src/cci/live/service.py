from cci.domain.contracts import ScoringConfig
from cci.graph.builder import build_dossier_graph
from cci.live.acquisition import acquire_sources
from cci.live.contracts import LiveAnalysisRequest, MAX_REPOSITORIES, MAX_FILES, MAX_SECONDS
from cci.pipeline.orchestrator import execute_analysis_pipeline


def analyze_resume(request: LiveAnalysisRequest):
    evidence, ownership, sources = acquire_sources(request.github_urls, request.github_identity)
    manifest = request.intake.manifest
    for key in ('linkedin_urls', 'coding_profile_urls', 'credential_urls', 'deployment_urls', 'portfolio_urls', 'project_links'):
        for url in getattr(manifest, key)[:20]:
            sources.append({'url': url, 'status': 'unsupported',
                            'detail': 'Extracted from the resume. This live adapter does not fetch or verify this source.'})
    state = execute_analysis_pipeline(candidate_id=request.intake.candidate_id, role=request.role,
        jd_text=request.jd_text, declared_claims=manifest.claimed_skills, custom_evidence=evidence, evidence_mode='live')
    if state.dossier is None:
        raise RuntimeError('The scoring pipeline could not produce a dossier.')
    limitations = [
        'Resume identity and GitHub account association are candidate declarations, not identity verification.',
        'Public GitHub evidence is fetched live. Static heuristic observations are not proof of mastery or job performance.',
        'Source reliability uses configured priors only; no simulated review outcomes are used.',
        'Verification/depth confidence factors are conservative prototype settings, not empirically calibrated probabilities.',
        'Recent-commit attribution is repository-level; it does not prove authorship of each inspected line.',
        f'Bounded scan: {MAX_REPOSITORIES} repositories, {MAX_FILES} selected text files each, {MAX_SECONDS}s acquisition budget.',
        'The uploaded document and analysis are request-scoped. Download JSON to retain this result; refreshing clears the page.',
    ]
    dossier = state.dossier.model_copy(update={'ownership_assessments': ownership,
        'system_limitations': [*state.dossier.system_limitations, *limitations]})
    graph = build_dossier_graph(dossier)
    return {'intake': request.intake, 'dossier': dossier,
        'graph': graph.to_api_response(candidate_id=dossier.candidate_id, analysis_run_id=dossier.analysis_run_id),
        'graph_snapshot': graph.to_dict(), 'sources': sources, 'scoring_config': ScoringConfig(),
        'storage': 'request_only', 'status': 'partial' if any(s['status'] != 'observed' for s in sources) or not evidence else 'completed'}
