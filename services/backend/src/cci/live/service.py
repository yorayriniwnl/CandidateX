from uuid import uuid4

from cci.domain.contracts import RepositoryAssociation, RepositoryContribution, ScoringConfig
from cci.graph.builder import build_dossier_graph
from cci.live.acquisition import acquire_sources
from cci.live.contracts import LiveAnalysisRequest, MAX_REPOSITORIES, MAX_FILES, MAX_SECONDS
from cci.pipeline.orchestrator import execute_analysis_pipeline
from concurrent.futures import ThreadPoolExecutor
from cci.live.public_links import acquire_public_links
from cci.live.report import build_report


def analyze_resume(request: LiveAnalysisRequest):
    analysis_run_id = uuid4()
    scoring_config = ScoringConfig()
    manifest = request.intake.manifest
    from cci.contradictions.expectations import build_observable_claim_expectations
    observable_expectations = build_observable_claim_expectations(request.intake)
    extracted = list(dict.fromkeys(url for key in ('linkedin_urls', 'coding_profile_urls', 'credential_urls',
        'deployment_urls', 'portfolio_urls', 'project_links') for url in getattr(manifest, key)))
    selected = request.external_urls if request.external_urls is not None else extracted
    def _fetch_github_sources():
        try:
            return acquire_sources(
                request.github_urls,
                request.github_identity,
                analysis_run_id,
                observable_expectations=observable_expectations,
            )
        except TypeError:
            return acquire_sources(
                request.github_urls,
                request.github_identity,
                analysis_run_id,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        github = pool.submit(_fetch_github_sources)
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
        jd_text=request.jd_text, declared_claims=manifest.claimed_skills, custom_evidence=evidence,
        evidence_mode='live', scoring_config=scoring_config, analysis_run_id=analysis_run_id,
        observable_expectations=observable_expectations)
    if state.dossier is None:
        raise RuntimeError('The scoring pipeline could not produce a dossier.')
    limitations = [
        'Resume identity and GitHub account association are candidate declarations, not identity verification.',
        'Public GitHub evidence is fetched live. Static heuristic observations do not prove mastery or job performance; rule strengths are not calibrated proficiency ratings.',
        'Source reliability uses configured priors only; no simulated review outcomes are used.',
        'Verification/depth confidence factors are conservative prototype settings, not empirically calibrated probabilities.',
        'Repository association and repository-level contribution are separate from path-specific artifact contribution.',
        'Artifact attribution uses bounded recent path history; failed, deferred, or ambiguous history remains unknown. A matching GitHub account does not verify human identity or line-level authorship.',
        'Public page text, profile metadata and certificate mentions do not increase capability scores. Issuer authentication and employment verification are not automated.',
        'Public links: up to 24 HTML/text/digital PDF pages, 512 KB each, 3 redirects; PDFs up to 5 pages. Login gates, image-only and script-only pages remain unresolved.',
        f'Bounded scan: {MAX_REPOSITORIES} repositories, {MAX_FILES} selected text files each, {MAX_SECONDS}s acquisition budget.',
        'The uploaded document and analysis are request-scoped. Download JSON to retain this result; refreshing clears the page.',
    ]
    associations = [RepositoryAssociation.model_validate(source['repository_association'])
                    for source in sources if source.get('repository_association')]
    contributions = [RepositoryContribution.model_validate(source['repository_contribution'])
                     for source in sources if source.get('repository_contribution')]
    dossier = state.dossier.model_copy(update={'ownership_assessments': ownership,
        'repository_associations': associations, 'repository_contributions': contributions,
        'system_limitations': [*state.dossier.system_limitations, *limitations]})
    graph = build_dossier_graph(dossier)
    return {'intake': request.intake, 'dossier': dossier,
        'graph': graph.to_api_response(candidate_id=dossier.candidate_id, analysis_run_id=dossier.analysis_run_id),
        'graph_snapshot': graph.to_dict(), 'sources': sources, 'analysis': build_report(request.intake, sources), 'scoring_config': scoring_config,
        'storage': 'request_only', 'status': 'partial' if any(s['status'] != 'observed' for s in sources) or not evidence else 'completed'}
