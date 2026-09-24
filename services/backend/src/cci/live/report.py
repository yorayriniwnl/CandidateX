"""Cross-source explanations: separate declarations, observations, and attribution."""
import re
from datetime import datetime, timezone

from cci.intake.canonicalizer import classify_url
from cci.live.claims import build_academic_records, build_claim_ledger

SKILL_ALIASES = {'nextjs': 'nextjs', 'reactjs': 'react', 'html5': 'html', 'css3': 'css',
    'tailwindcss': 'tailwindcss', 'golang': 'go', 'scikitlearn': 'scikitlearn', 'cicd': 'cicd'}
ATTRIBUTED_STATES = {'WEAK_ATTRIBUTION', 'PARTIAL_ATTRIBUTION', 'STRONG_ATTRIBUTION'}


def normalize_skill(skill):
    value = re.sub(r'[^a-z0-9+#]', '', skill.lower())
    return SKILL_ALIASES.get(value, value)


def text_mentions(text, value):
    return bool(value and re.search(r'(?<![\w])' + re.escape(value) + r'(?![\w])', text, re.I))


def build_report(intake, sources):
    learning = {normalize_skill(s) for s in intake.resume_review.learning_skills}
    skills = []
    for skill in intake.manifest.claimed_skills:
        matches, mentions = [], []
        for source in sources:
            path_attributions = {
                item.get('artifact_path'): item
                for item in source.get('artifact_attributions', [])
                if item.get('artifact_path')
            }
            for technology in source.get('repository_review', {}).get('technologies', []):
                if normalize_skill(technology['name']) == normalize_skill(skill):
                    attribution = path_attributions.get(technology.get('path'), {})
                    attribution_observed = (
                        attribution.get('state') in ATTRIBUTED_STATES
                        and attribution.get('ownership_score', 0) > 0
                    )
                    matches.append({**technology, 'repository_url': source['url'],
                                    'attribution_observed': attribution_observed,
                                    'attribution_state': attribution.get('state', 'UNKNOWN')})
            if source.get('status') == 'observed' and text_mentions(source.get('excerpt', ''), skill):
                mentions.append(source['url'])
        attributed = any(m['attribution_observed'] for m in matches)
        skills.append({'skill': skill, 'learning': normalize_skill(skill) in learning,
            'status': 'repository_support' if attributed else 'repository_only' if matches else 'public_mention_only' if mentions else 'not_observed',
            'evidence': matches[:12], 'evidence_count': len(matches), 'public_mentions': mentions,
            'explanation': ('GitHub path history associates commits on the inspected path with the declared account. Repository attribution and human identity remain unverified; static rules do not establish proficiency.' if attributed else
                            'Technology appears in a repository, but candidate attribution was not established.' if matches else
                            'Public page text mentions this skill; self-published mentions do not establish capability.' if mentions else
                            'No matching technology was observed in the bounded scan. This is not a claim that the candidate lacks the skill.')})

    from cci.credentials.verification import verify_all_credentials
    cert_claims = list(intake.resume_review.sections.get('certifications', []))
    verified_results = verify_all_credentials(
        resume_claims=cert_claims,
        candidate_name=intake.manifest.display_name,
        sources=sources,
        declared_urls=getattr(intake.manifest, 'credential_urls', ()),
    )
    credentials = [r.to_dict() for r in verified_results]

    projects = []
    for project in intake.manifest.project_claims:
        text = f"{project.get('title', '')} {project.get('description', '')}"
        refs = [s['url'] for s in sources if s['url'].removeprefix('https://').removeprefix('http://').lower() in text.lower()]
        projects.append({**project, 'source_urls': refs, 'status': 'linked_sources' if refs else 'declaration_only',
                         'explanation': 'Links connect this project to acquisition receipts; impact, performance and contribution claims still require separate verification.'})
    sections = intake.resume_review.sections
    numeric_claims = [line for lines in sections.values() for line in lines if re.search(r'\d+(?:\.\d+)?\s*%|\b\d+[+-]?\s+(?:users|tests|projects|applications|points)\b', line, re.I)]
    actions = []
    if not any(any(attribution.get('state') in ATTRIBUTED_STATES and attribution.get('ownership_score', 0) > 0
                   for attribution in source.get('artifact_attributions', [])) for source in sources):
        actions.append('Confirm the candidate-declared GitHub account and review path-specific contribution history.')
    if any(s['status'] != 'observed' for s in sources):
        actions.append('Review unavailable or unscanned sources; run again with a smaller selected set where needed.')
    if credentials:
        actions.append('Confirm certificates with their issuer, including recipient, credential ID and dates.')
    actions.append('Use the skill evidence paths and project claims to request a walkthrough of the candidate’s actual contribution.')
    claims = build_claim_ledger(intake)
    academic_records = build_academic_records(intake)
    source_statuses = {}
    source_kinds = {}
    discovered_links = []
    seen_discovered = set()
    for source in sources:
        status = source.get('status', 'unknown')
        kind = source.get('kind') or classify_url(source.get('url', ''))
        source_statuses[status] = source_statuses.get(status, 0) + 1
        source_kinds[kind] = source_kinds.get(kind, 0) + 1
        for discovered in source.get('discovered_links', []):
            url = discovered.get('url')
            if url and url not in seen_discovered:
                seen_discovered.add(url)
                discovered_links.append(discovered)

    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'skills': skills, 'credentials': credentials,
        'projects': projects, 'experience': [{'claim': line, 'status': 'self_reported'} for line in sections.get('experience', [])],
        'education': [{'claim': line, 'status': 'self_reported'} for line in sections.get('education', [])],
        'academic_records': academic_records, 'claims': claims,
        'achievements': [{'claim': line, 'status': 'self_reported'} for line in sections.get('achievements', [])],
        'quantified_claims_to_verify': list(dict.fromkeys(numeric_claims))[:30], 'next_steps': actions,
        'discovered_links': discovered_links,
        'source_coverage': {'by_status': source_statuses, 'by_kind': source_kinds,
                            'discovered_links': len(discovered_links)},
        'coverage': {'supplied_sources': len(sources), 'observed_sources': sum(s['status'] == 'observed' for s in sources),
                     'skills_declared': len(skills), 'skills_with_repository_matches': sum(bool(s['evidence']) for s in skills),
                     'credential_claims': len(credentials)},
        'method': 'Deterministic document extraction, bounded public acquisition, and exact technology matching. Resume claims remain declarations unless separate evidence supports them; public-page link discovery is retained for follow-up analysis. Static rule strengths are uncalibrated policy heuristics and do not establish proficiency.'}
